#!/usr/bin/env python3
"""Rebuild and verify the optimized secp256k1 kickmix package.

This file is intentionally self-contained and standard-library-only so that the
main reproducibility path is easy to inspect.  The exact machine-checked layer is
an ISA-level point-add leaf plus deterministic challenge generation.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List

from common import (
    SECP_B,
    SECP_G,
    SECP_N,
    SECP_P,
    affine_to_proj,
    add_affine,
    complete_projective_add_a0,
    deterministic_scalars,
    dump_json,
    hex_or_inf,
    load_json,
    mul_fixed_window,
    precompute_window_tables,
    proj_to_affine,
    sha256_bytes,
    sha256_path,
)

TOY_CURVES = [
    {'name': 'toy61_b2', 'p': 61, 'b': 2, 'order': 61, 'generator': (1, 8)},
    {'name': 'toy127_b11', 'p': 109, 'b': 11, 'order': 127, 'generator': (1, 11)},
]


def specialize_family_netlist(netlist_obj: Dict[str, Any], b3_value: int) -> Dict[str, Any]:
    out = json.loads(json.dumps(netlist_obj))
    for ins in out['instructions']:
        if ins['op'] == 'mul_const' and ins['const'] == 'b3':
            ins['const'] = b3_value
    return out


def exec_netlist(netlist: List[Dict[str, Any]], p: int, q_proj, table_entry, key: int):
    """Execute the optimized ISA netlist on computational-basis inputs.

    The optimized leaf is intentionally branch-free in its hot path.  The only
    conditional behavior is the exact no-op semantics for the canonical `k = 0`
    table entry, implemented with explicit select instructions.
    """
    env: Dict[str, Any] = {
        'Q.X': q_proj[0] % p,
        'Q.Y': q_proj[1] % p,
        'Q.Z': q_proj[2] % p,
        'k': key,
        'T.x': {key: 0 if table_entry is None else table_entry[0] % p},
        'T.y': {key: 0 if table_entry is None else table_entry[1] % p},
        'T.meta': {key: 1 if table_entry is None else 0},
    }
    for ins in netlist:
        op = ins['op']
        dst = ins.get('dst')
        if op == 'load_input':
            env[dst] = env[ins['src']]
        elif op == 'lookup_affine_x':
            env[dst] = env['T.x'][env['k']] % p
        elif op == 'lookup_affine_y':
            env[dst] = env['T.y'][env['k']] % p
        elif op == 'lookup_meta':
            env[dst] = env['T.meta'][env['k']]
        elif op == 'bool_from_flag':
            bit = ins['src']['bit']
            env[dst] = int((env['meta'] >> bit) & 1)
        elif op == 'field_mul':
            a, b = ins['src']
            env[dst] = (env[a] * env[b]) % p
        elif op == 'field_add':
            a, b = ins['src']
            env[dst] = (env[a] + env[b]) % p
        elif op == 'field_sub':
            a, b = ins['src']
            env[dst] = (env[a] - env[b]) % p
        elif op == 'mul_const':
            c = ins['const']
            env[dst] = (int(c) * env[ins['src']]) % p
        elif op == 'select_field_if_flag':
            old_src, new_src = ins['src']
            env[dst] = env[old_src] if env[ins['flag']] else env[new_src]
        elif op == 'mbuc_clear_bool':
            env[dst] = 0
        else:
            raise ValueError(f'Unsupported optimized opcode: {op}')
    return (env['qx'] % p, env['qy'] % p, env['qz'] % p)


def make_audit_cases(netlist_sha: str):
    specs = [
        ('random', 12288),
        ('doubling', 1024),
        ('inverse', 1024),
        ('accumulator_infinity', 1024),
        ('lookup_infinity', 1024),
    ]
    cases = []
    base_seed = bytes.fromhex(netlist_sha)
    for name, count in specs:
        vals = deterministic_scalars(base_seed + name.encode(), count * 2, SECP_N)
        if name == 'random':
            for i in range(count):
                cases.append((name, vals[2 * i], vals[2 * i + 1]))
        elif name == 'doubling':
            for i in range(count):
                a = vals[i]
                cases.append((name, a, a))
        elif name == 'inverse':
            for i in range(count):
                a = vals[i]
                cases.append((name, a, (-a) % SECP_N))
        elif name == 'accumulator_infinity':
            for i in range(count):
                cases.append((name, 0, vals[i]))
        elif name == 'lookup_infinity':
            for i in range(count):
                cases.append((name, vals[i], 0))
    return cases


def run_audit(package_dir: Path) -> Dict[str, Any]:
    secp_path = package_dir / 'out' / 'optimized_pointadd_secp256k1.json'
    netlist_obj = load_json(secp_path)
    netlist_sha = sha256_path(secp_path)
    cases = make_audit_cases(netlist_sha)
    tables = precompute_window_tables(SECP_G, SECP_P, SECP_B, width=8, bits=256)
    out_csv = package_dir / 'out' / 'optimized_pointadd_audit_16384.csv'
    summary: Dict[str, Any] = {'total': 0, 'pass': 0, 'categories': {}}
    with out_csv.open('w', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow([
            'case_id', 'category', 'a_scalar_hex', 'b_scalar_hex',
            'acc_before_x', 'acc_before_y', 'lookup_x', 'lookup_y',
            'expected_x', 'expected_y', 'leaf_x', 'leaf_y', 'fallback_x', 'fallback_y', 'status',
        ])
        for idx, (category, a, b) in enumerate(cases):
            pa = mul_fixed_window(a, tables, SECP_P, SECP_B, width=8, order=SECP_N)
            qa = mul_fixed_window(b, tables, SECP_P, SECP_B, width=8, order=SECP_N)
            qp = affine_to_proj(pa, SECP_P)
            key = 0 if qa is None else 1
            got_aff = proj_to_affine(exec_netlist(netlist_obj['instructions'], SECP_P, qp, qa, key), SECP_P)
            ref_aff = add_affine(pa, qa, SECP_P, SECP_B)
            ref2_aff = proj_to_affine(complete_projective_add_a0(qp, affine_to_proj(qa, SECP_P), SECP_P, SECP_B), SECP_P)
            ok = got_aff == ref_aff == ref2_aff
            summary['total'] += 1
            summary['pass'] += int(ok)
            summary['categories'].setdefault(category, {'total': 0, 'pass': 0})
            summary['categories'][category]['total'] += 1
            summary['categories'][category]['pass'] += int(ok)
            writer.writerow([
                idx, category, format(a, '064x'), format(b, '064x'),
                *hex_or_inf(pa), *hex_or_inf(qa), *hex_or_inf(ref_aff), *hex_or_inf(got_aff), *hex_or_inf(ref2_aff),
                'PASS' if ok else 'FAIL',
            ])
    return {
        'sha256': sha256_path(out_csv),
        'summary': summary,
        'csv': out_csv.name,
        'netlist_sha256': netlist_sha,
    }


def run_toy(package_dir: Path) -> Dict[str, Any]:
    family_path = package_dir / 'out' / 'optimized_pointadd_family.json'
    family = load_json(family_path)
    out_csv = package_dir / 'out' / 'toy_curve_exhaustive_19850.csv'
    summary: Dict[str, Any] = {'total': 0, 'pass': 0, 'curves': {}}
    with out_csv.open('w', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow([
            'curve', 'field_p', 'curve_b', 'group_order', 'a_scalar', 'b_scalar',
            'acc_before_x', 'acc_before_y', 'lookup_x', 'lookup_y',
            'expected_x', 'expected_y', 'leaf_x', 'leaf_y', 'status',
        ])
        for curve in TOY_CURVES:
            p, b, order = curve['p'], curve['b'], curve['order']
            cname = curve['name']
            gen = curve['generator']
            width = 4
            bits = max(1, order.bit_length())
            tables = precompute_window_tables(gen, p, b, width=width, bits=bits)
            nl = specialize_family_netlist(family, 3 * b)['instructions']
            curve_total = 0
            curve_pass = 0
            for a in range(order):
                pa = mul_fixed_window(a, tables, p, b, width=width, order=order)
                qp = affine_to_proj(pa, p)
                for bb in range(order):
                    qa = mul_fixed_window(bb, tables, p, b, width=width, order=order)
                    key = 0 if qa is None else 1
                    got_aff = proj_to_affine(exec_netlist(nl, p, qp, qa, key), p)
                    ref_aff = add_affine(pa, qa, p, b)
                    ok = got_aff == ref_aff
                    summary['total'] += 1
                    summary['pass'] += int(ok)
                    curve_total += 1
                    curve_pass += int(ok)
                    writer.writerow([
                        cname, p, b, order, a, bb,
                        *hex_or_inf(pa), *hex_or_inf(qa), *hex_or_inf(ref_aff), *hex_or_inf(got_aff),
                        'PASS' if ok else 'FAIL',
                    ])
            summary['curves'][cname] = {'total': curve_total, 'pass': curve_pass, 'order': order, 'p': p, 'b': b}
    return {'sha256': sha256_path(out_csv), 'summary': summary, 'csv': out_csv.name}


def main() -> None:
    parser = argparse.ArgumentParser(description='Rebuild and verify the optimized secp256k1 kickmix package.')
    parser.add_argument('--package-dir', default='artifacts/optimized', help='Path to the optimized package root containing out/ and figures/.')
    parser.add_argument('--mode', choices=['audit', 'toy', 'all'], default='all')
    args = parser.parse_args()

    package_dir = Path(args.package_dir).resolve()
    overall: Dict[str, Any] = {}
    if args.mode in ('audit', 'all'):
        overall['audit'] = run_audit(package_dir)
    if args.mode in ('toy', 'all'):
        overall['toy'] = run_toy(package_dir)
    out_path = package_dir / 'out' / 'verifier_rebuild_summary.json'
    dump_json(out_path, overall)
    print(json.dumps(overall, indent=2))


if __name__ == '__main__':
    main()
