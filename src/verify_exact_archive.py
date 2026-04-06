#!/usr/bin/env python3
"""Replay verifier for the archived exact kickmix package.

This verifier is intentionally separate from the optimized rebuild path.
The exact archived package contains a machine-readable netlist and a full secp256k1
transcript, but it does not contain the original challenge generator used to emit
`pointadd_audit_9024.csv`.  So the reproducible check here is a transcript replay:
we recompute the points from the archived scalars, re-execute the exact ISA netlist,
and verify the scaffold/oracle linkage and proof manifest hashes.
"""

from __future__ import annotations

import argparse
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
    dump_json,
    iter_csv_dicts,
    load_json,
    mul_affine,
    mul_fixed_window,
    parse_point_from_row,
    precompute_window_tables,
    proj_to_affine,
    sha256_path,
)


def jacobian_to_affine(point, p: int):
    x, y, z = [v % p for v in point]
    if z == 0:
        return None
    z2 = (z * z) % p
    z3 = (z2 * z) % p
    return ((x * pow(z2, -1, p)) % p, (y * pow(z3, -1, p)) % p)


def execute_exact_netlist(netlist: List[Dict[str, Any]], p: int, q_proj, lookup_point, lookup_is_infinity: bool):
    env: Dict[str, Any] = {
        'Q.X': q_proj[0] % p,
        'Q.Y': q_proj[1] % p,
        'Q.Z': q_proj[2] % p,
        'k': 0 if lookup_is_infinity else 1,
        'T.x': {0: 0 if lookup_point is None else lookup_point[0] % p, 1: 0 if lookup_point is None else lookup_point[0] % p},
        'T.y': {0: 0 if lookup_point is None else lookup_point[1] % p, 1: 0 if lookup_point is None else lookup_point[1] % p},
        'T.meta': {0: 1 if lookup_is_infinity else 0, 1: 1 if lookup_is_infinity else 0},
    }

    for ins in netlist:
        op = ins['op']
        if op == 'copy_field':
            env[ins['dst']] = env[ins['src']]
        elif op == 'lookup_affine_x':
            env[ins['dst']] = env['T.x'][env['k']] % p
        elif op == 'lookup_affine_y':
            env[ins['dst']] = env['T.y'][env['k']] % p
        elif op == 'lookup_meta':
            env[ins['dst']] = env['T.meta'][env['k']]
        elif op == 'bool_from_flag':
            src = ins['src']
            env[ins['dst']] = int((env[src['flags']] >> src['bit']) & 1)
        elif op == 'field_is_zero':
            env[ins['dst']] = int(env[ins['src']] % p == 0)
        elif op == 'bool_and':
            a, b = ins['src']
            env[ins['dst']] = int(bool(env[a]) and bool(env[b]))
        elif op == 'bool_not_and':
            a, b = ins['src']
            env[ins['dst']] = int(bool(env[a]) and not bool(env[b]))
        elif op == 'bool_or':
            a, b = ins['src']
            env[ins['dst']] = int(bool(env[a]) or bool(env[b]))
        elif op == 'bool_not':
            env[ins['dst']] = int(not bool(env[ins['src']]))
        elif op == 'field_square':
            env[ins['dst']] = (env[ins['src']] * env[ins['src']]) % p
        elif op == 'field_mul':
            a, b = ins['src']
            env[ins['dst']] = (env[a] * env[b]) % p
        elif op == 'field_sub':
            a, b = ins['src']
            env[ins['dst']] = (env[a] - env[b]) % p
        elif op == 'field_double':
            env[ins['dst']] = (2 * env[ins['src']]) % p
        elif op == 'field_const_mul':
            src = ins['src']['src']
            k = ins['src']['k']
            env[ins['dst']] = (k * env[src]) % p
        elif op == 'set_jacobian_from_affine':
            xsrc, ysrc = ins['src']
            xdst, ydst, zdst = ins['dst']
            env[xdst] = env[xsrc] % p
            env[ydst] = env[ysrc] % p
            env[zdst] = 1
        elif op == 'set_infinity':
            xdst, ydst, zdst = ins['dst']
            env[xdst], env[ydst], env[zdst] = 0, 1, 0
        elif op == 'select_jacobian':
            guard = bool(env[ins['src']['guard']])
            chosen = ins['src']['on_true'] if guard else ins['src']['on_false']
            for dst_name, src_name in zip(ins['dst'], chosen):
                env[dst_name] = env[src_name]
        elif op == 'mbuc_clear':
            env[ins['dst']] = 0
        else:
            raise ValueError(f'Unsupported exact opcode: {op}')

    return (env['Q.X'] % p, env['Q.Y'] % p, env['Q.Z'] % p)


def verify_manifest(repo_root: Path) -> Dict[str, Any]:
    package_root = repo_root / 'artifacts' / 'exact_kickmix'
    manifest = load_json(package_root / 'out' / 'proof_manifest.json')
    checks = {}
    for entry in ('pointadd_netlist', 'ecdlp_scaffold', 'pointadd_audit', 'toy_exhaustive'):
        record = manifest[entry]
        path = package_root / 'out' / record['file']
        checks[entry] = {
            'expected': record['sha256'],
            'actual': sha256_path(path),
            'match': record['sha256'] == sha256_path(path),
        }
    return checks


def verify_scaffold(repo_root: Path) -> Dict[str, Any]:
    package_root = repo_root / 'artifacts' / 'exact_kickmix'
    scaffold = load_json(package_root / 'out' / 'ecdlp_scaffold_exact_sample.json')
    netlist_hash = sha256_path(package_root / 'out' / 'pointadd_exact_kickmix.json')
    instructions = scaffold['instructions']
    call_ops = [ins for ins in instructions if ins['op'] == 'call_pointadd_oracle']
    all_match = all(ins['oracle_hash'] == netlist_hash for ins in call_ops)
    expected_window_calls = 28
    return {
        'window_count': scaffold['window_count'],
        'call_count': len(call_ops),
        'expected_call_count': expected_window_calls,
        'oracle_hash_matches_netlist': all_match,
        'scaffold_sha256': sha256_path(package_root / 'out' / 'ecdlp_scaffold_exact_sample.json'),
    }


def replay_exact_audit(repo_root: Path) -> Dict[str, Any]:
    package_root = repo_root / 'artifacts' / 'exact_kickmix'
    csv_path = package_root / 'out' / 'pointadd_audit_9024.csv'
    netlist = load_json(package_root / 'out' / 'pointadd_exact_kickmix.json')['instructions']

    total = 0
    passed = 0
    sample_failures = []
    g_tables = precompute_window_tables(SECP_G, SECP_P, SECP_B, width=8, bits=256)

    for row in iter_csv_dicts(csv_path):
        total += 1
        q_scalar = int(row['q_scalar'], 16)
        base_scalar = int(row['base_scalar'], 16)
        signed_key = int(row['signed_key'])

        q_point = mul_fixed_window(q_scalar, g_tables, SECP_P, SECP_B, width=8, order=SECP_N)
        base_point = mul_fixed_window(base_scalar, g_tables, SECP_P, SECP_B, width=8, order=SECP_N)
        lookup_point = mul_affine(signed_key, base_point, SECP_P, SECP_B)
        q_proj = affine_to_proj(q_point, SECP_P)
        got_aff = jacobian_to_affine(execute_exact_netlist(netlist, SECP_P, q_proj, lookup_point, lookup_point is None), SECP_P)
        expected_aff = add_affine(q_point, lookup_point, SECP_P, SECP_B)

        row_q = parse_point_from_row(row['input_q_x'], row['input_q_y'])
        row_base = parse_point_from_row(row['base_x'], row['base_y'])
        row_expected = parse_point_from_row(row['expected_x'], row['expected_y'])
        row_actual = parse_point_from_row(row['actual_x'], row['actual_y'])

        ok = (
            q_point == row_q and
            base_point == row_base and
            expected_aff == row_expected and
            got_aff == row_actual and
            got_aff == expected_aff and
            row['pass'] == 'True'
        )
        if ok:
            passed += 1
        elif len(sample_failures) < 10:
            sample_failures.append({
                'case': row['case'],
                'q_scalar': row['q_scalar'],
                'base_scalar': row['base_scalar'],
                'signed_key': row['signed_key'],
            })

    return {
        'total_rows': total,
        'passed_rows': passed,
        'failed_rows': total - passed,
        'csv_sha256': sha256_path(csv_path),
        'sample_failures': sample_failures,
    }


def verify_toy_summary(repo_root: Path) -> Dict[str, Any]:
    package_root = repo_root / 'artifacts' / 'exact_kickmix'
    toy = load_json(package_root / 'out' / 'toy_curve_exhaustive.json')
    return {
        'cases_exhaustively_checked': toy['cases_exhaustively_checked'],
        'failure_count': toy['failure_count'],
        'result': toy['result'],
        'sha256': sha256_path(package_root / 'out' / 'toy_curve_exhaustive.json'),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description='Replay verifier for the archived exact kickmix package.')
    parser.add_argument('--repo-root', default='.', help='Repository root containing artifacts/exact_kickmix/.')
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    result = {
        'manifest': verify_manifest(repo_root),
        'scaffold': verify_scaffold(repo_root),
        'audit_replay': replay_exact_audit(repo_root),
        'toy_summary': verify_toy_summary(repo_root),
    }
    out_path = repo_root / 'results' / 'exact_archive_verification_summary.json'
    dump_json(out_path, result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
