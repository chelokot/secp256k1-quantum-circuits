#!/usr/bin/env python3
"""Extended verification and publication-readiness checks.

The core verifier in `src/verifier.py` proves the arithmetic leaf on secp256k1 and
two toy curves. This module adds stronger, slower checks:
1. lookup-contract audit
2. scaffold schedule audit
3. coherent cleanup audit
4. extended toy-family verification
5. projection sensitivity and claim-boundary reports
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from common import (
    SECP_B,
    SECP_G,
    SECP_N,
    SECP_P,
    affine_to_proj,
    add_affine,
    artifact_circuits_path,
    artifact_extended_verification_path,
    artifact_lookup_path,
    artifact_projection_path,
    deterministic_scalars,
    dump_json,
    hex_or_inf,
    load_json,
    mul_affine,
    mul_fixed_window,
    precompute_window_tables,
    proj_to_affine,
    sha256_bytes,
    sha256_path,
)
from lookup_research import contract_parameter_checks, load_lookup_folded_contract, run_lookup_folding_audit
from verifier import exec_netlist, exec_netlist_with_trace, make_audit_cases, specialize_family_netlist


PointAffine = Optional[Tuple[int, int]]

CURATED_EXTENDED_TOY_CURVES = [
    {"name": "toy61_b2", "p": 61, "b": 2, "order": 61, "generator": (1, 8)},
    {"name": "toy127_b11", "p": 109, "b": 11, "order": 127, "generator": (1, 11)},
    {"name": "toy181_b3", "p": 163, "b": 3, "order": 181, "generator": (1, 2)},
    {"name": "toy241_b29", "p": 211, "b": 29, "order": 241, "generator": (1, 36)},
]

def is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    limit = int(math.isqrt(n))
    f = 3
    while f <= limit:
        if n % f == 0:
            return False
        f += 2
    return True


def is_on_curve(point: PointAffine, p: int, b: int) -> bool:
    if point is None:
        return True
    x, y = point
    return (y * y - (x * x * x + b)) % p == 0


def point_order(point: PointAffine, p: int, b: int, max_steps: int) -> int:
    if point is None:
        return 1
    acc = None
    for i in range(1, max_steps + 1):
        acc = add_affine(acc, point, p, b)
        if acc is None:
            return i
    raise ValueError("point order search exceeded bound")


def minimal_hex_or_inf(point: PointAffine) -> Tuple[str, str]:
    if point is None:
        return ("INF", "INF")
    x, y = point
    return (format(x, "x"), format(y, "x"))


def window_bases(base: PointAffine, p: int, b: int, width: int, windows: int) -> List[PointAffine]:
    arr: List[PointAffine] = [None] * windows
    arr[0] = base
    for i in range(1, windows):
        q = arr[i - 1]
        for _ in range(width):
            q = add_affine(q, q, p, b)
        arr[i] = q
    return arr


def window_digit_u16(value: int, idx: int) -> int:
    return (value >> (16 * idx)) & 0xFFFF


def compute_window_lookup(base_windows: List[PointAffine], idx: int, digit: int, p: int, b: int) -> PointAffine:
    if digit == 0:
        return None
    return mul_affine(digit, base_windows[idx], p, b, order=None)


def verify_curve_metadata(curve: Dict[str, Any]) -> Dict[str, Any]:
    p, b, order, gen = curve["p"], curve["b"], curve["order"], curve["generator"]
    actual_order = point_order(gen, p, b, order)
    return {
        "curve": curve["name"],
        "generator_on_curve": is_on_curve(gen, p, b),
        "group_order_is_prime": is_prime(order),
        "generator_order_matches_claim": actual_order == order,
        "actual_generator_order": actual_order,
    }


def run_lookup_contract(
    repo_root: Path,
    progress: Callable[[int, int], None] | None = None,
) -> Dict[str, Any]:
    package_root = repo_root / "artifacts"
    contract = load_lookup_folded_contract(repo_root)
    parameter_results = contract_parameter_checks(contract)
    audit = run_lookup_folding_audit(repo_root)
    if progress is not None:
        progress(1, 1)

    parameter_total = len(parameter_results)
    parameter_pass = sum(int(ok) for ok in parameter_results.values())
    full_exhaustive = {
        "base_id": audit["summary"]["full_exhaustive_base"],
        "total": audit["summary"]["full_exhaustive_cases"],
        "pass": audit["summary"]["full_exhaustive_pass"],
    }
    multibase = {
        "base_count": len(audit["summary"]["bases"]),
        "total": audit["summary"]["direct_semantic_samples"],
        "pass": audit["summary"]["direct_semantic_pass"],
    }

    out_json = artifact_extended_verification_path(package_root, "lookup_contract_summary.json")
    result = {
        "contract_sha256": sha256_path(artifact_lookup_path(package_root, "lookup_signed_fold_contract.json")),
        "lookup_research_summary_sha256": sha256_path(artifact_lookup_path(package_root, "lookup_signed_fold_summary.json")),
        "summary": {
            "parameter_checks": {
                "total": parameter_total,
                "pass": parameter_pass,
                "checks": parameter_results,
            },
            "canonical_full_exhaustive": full_exhaustive,
            "multibase_direct_samples": multibase,
            "total": parameter_total + full_exhaustive["total"] + multibase["total"],
            "pass": parameter_pass + full_exhaustive["pass"] + multibase["pass"],
        },
        "artifacts": {
            "contract": "artifacts/lookup/lookup_signed_fold_contract.json",
            "lookup_research_summary": "artifacts/lookup/lookup_signed_fold_summary.json",
            "full_exhaustive_csv": f"artifacts/lookup/{audit['full_exhaustive_csv']}",
            "multibase_sample_csv": f"artifacts/lookup/{audit['multibase_sample_csv']}",
        },
        "notes": [
            "This summary validates the checked-in folded lookup contract fields and then points at the exhaustive and sampled semantic audits generated under artifacts/lookup/.",
            "The lookup contract is exact at the arithmetic interface layer, and the compiler project lowers named lookup families below that contract. The repository still does not ship a bit-for-bit primitive qRAM or QROM realization.",
        ],
    }
    dump_json(out_json, result)
    result["sha256"] = sha256_path(out_json)
    return result


def run_coherent_cleanup(
    repo_root: Path,
    progress: Callable[[int, int], None] | None = None,
) -> Dict[str, Any]:
    package_root = repo_root / "artifacts"
    leaf_path = artifact_circuits_path(package_root, "optimized_pointadd_secp256k1.json")
    leaf = load_json(leaf_path)
    leaf_sha = sha256_path(leaf_path)
    cases = make_audit_cases(leaf_sha)
    tables = precompute_window_tables(SECP_G, SECP_P, SECP_B, width=8, bits=256)
    trace_pcs = {6, 35, 36}
    out_csv = artifact_extended_verification_path(package_root, "coherent_cleanup_audit_16384.csv")
    summary: Dict[str, Any] = {"total": 0, "pass": 0, "categories": {}}

    with out_csv.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "case_id",
            "category",
            "a_scalar_hex",
            "b_scalar_hex",
            "lookup_meta_bit",
            "flag_after_extract",
            "flag_before_cleanup",
            "flag_after_cleanup",
            "meta_before_cleanup",
            "meta_after_cleanup",
            "pre_cleanup_x",
            "pre_cleanup_y",
            "pre_cleanup_z",
            "post_cleanup_x",
            "post_cleanup_y",
            "post_cleanup_z",
            "expected_x",
            "expected_y",
            "final_x",
            "final_y",
            "status",
        ])
        for idx, (category, a_scalar, b_scalar) in enumerate(cases):
            accumulator = mul_fixed_window(a_scalar, tables, SECP_P, SECP_B, width=8, order=SECP_N)
            lookup = mul_fixed_window(b_scalar, tables, SECP_P, SECP_B, width=8, order=SECP_N)
            accumulator_proj = affine_to_proj(accumulator, SECP_P)
            key = 0 if lookup is None else 1
            final_proj, trace = exec_netlist_with_trace(leaf["instructions"], SECP_P, accumulator_proj, lookup, key, trace_pcs)
            final_aff = proj_to_affine(final_proj, SECP_P)
            expected_aff = add_affine(accumulator, lookup, SECP_P, SECP_B)

            meta_bit = 1 if lookup is None else 0
            extract_state = trace[6]
            pre_cleanup_state = trace[35]
            post_cleanup_state = trace[36]
            pre_cleanup_proj = (
                pre_cleanup_state["qx"] % SECP_P,
                pre_cleanup_state["qy"] % SECP_P,
                pre_cleanup_state["qz"] % SECP_P,
            )
            post_cleanup_proj = (
                post_cleanup_state["qx"] % SECP_P,
                post_cleanup_state["qy"] % SECP_P,
                post_cleanup_state["qz"] % SECP_P,
            )

            ok = (
                final_aff == expected_aff
                and extract_state["f_lookup_inf"] == meta_bit
                and pre_cleanup_state["f_lookup_inf"] == meta_bit
                and post_cleanup_state["f_lookup_inf"] == 0
                and pre_cleanup_state["meta"] == meta_bit
                and post_cleanup_state["meta"] == meta_bit
                and pre_cleanup_proj == post_cleanup_proj == final_proj
            )
            summary["total"] += 1
            summary["pass"] += int(ok)
            summary["categories"].setdefault(category, {"total": 0, "pass": 0})
            summary["categories"][category]["total"] += 1
            summary["categories"][category]["pass"] += int(ok)
            if progress is not None and (summary["total"] % 256 == 0 or summary["total"] == len(cases)):
                progress(summary["total"], len(cases))
            writer.writerow([
                idx,
                category,
                format(a_scalar, "064x"),
                format(b_scalar, "064x"),
                meta_bit,
                extract_state["f_lookup_inf"],
                pre_cleanup_state["f_lookup_inf"],
                post_cleanup_state["f_lookup_inf"],
                pre_cleanup_state["meta"],
                post_cleanup_state["meta"],
                format(pre_cleanup_proj[0], "064x"),
                format(pre_cleanup_proj[1], "064x"),
                format(pre_cleanup_proj[2], "064x"),
                format(post_cleanup_proj[0], "064x"),
                format(post_cleanup_proj[1], "064x"),
                format(post_cleanup_proj[2], "064x"),
                *hex_or_inf(expected_aff),
                *hex_or_inf(final_aff),
                "PASS" if ok else "FAIL",
            ])

    out_json = artifact_extended_verification_path(package_root, "coherent_cleanup_summary.json")
    result = {
        "csv_sha256": sha256_path(out_csv),
        "csv": out_csv.name,
        "leaf_sha256": leaf_sha,
        "summary": summary,
        "notes": [
            "This audit checks the shipped one-bit cleanup pair exactly at the ISA boundary: the metadata flag is extracted into f_lookup_inf, used by the neutral-entry select path, and uncomputed by applying the same flag source again.",
            "The audit verifies that the cleanup step clears the control slot, leaves the selected projective output unchanged, and preserves the loaded metadata bit. It does not claim a primitive-gate lowering of that pair.",
        ],
    }
    dump_json(out_json, result)
    result["sha256"] = sha256_path(out_json)
    return result


def run_scaffold_schedule(
    repo_root: Path,
    case_count: int = 256,
    progress: Callable[[int, int], None] | None = None,
) -> Dict[str, Any]:
    package_root = repo_root / "artifacts"
    scaffold = load_json(artifact_circuits_path(package_root, "ecdlp_scaffold_optimized.json"))
    leaf = load_json(artifact_circuits_path(package_root, "optimized_pointadd_secp256k1.json"))
    leaf_sha = sha256_path(artifact_circuits_path(package_root, "optimized_pointadd_secp256k1.json"))
    scaffold_sha = sha256_path(artifact_circuits_path(package_root, "ecdlp_scaffold_optimized.json"))
    seed = bytes.fromhex(sha256_bytes(bytes.fromhex(leaf_sha) + bytes.fromhex(scaffold_sha)))
    stream = deterministic_scalars(seed + b"scaffold", case_count * 3, SECP_N)
    g_tables = precompute_window_tables(SECP_G, SECP_P, SECP_B, width=8, bits=256)
    g_window_bases = window_bases(SECP_G, SECP_P, SECP_B, 16, 16)

    out_csv = artifact_extended_verification_path(package_root, f"scaffold_schedule_audit_{case_count}.csv")
    summary = {"total": 0, "pass": 0, "seed_zero_cases": 0, "tail_nonzero_cases": 0, "phase_b_base_variants": 0}
    unique_h = set()

    with out_csv.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "case_id", "phase_b_base_scalar_hex", "a_scalar_hex", "b_scalar_hex",
            "seed_x", "seed_y", "expected_x", "expected_y", "actual_x", "actual_y",
            "tail13", "tail14", "tail15", "status",
        ])

        for i in range(case_count):
            h_scalar = stream[3 * i]
            a_scalar = stream[3 * i + 1]
            b_scalar = stream[3 * i + 2]
            unique_h.add(h_scalar)
            h_point = mul_fixed_window(h_scalar, g_tables, SECP_P, SECP_B, width=8, order=SECP_N)
            h_window_bases = window_bases(h_point, SECP_P, SECP_B, 16, 16)

            seed_digit = window_digit_u16(a_scalar, 0)
            acc = compute_window_lookup(g_window_bases, 0, seed_digit, SECP_P, SECP_B)
            summary["seed_zero_cases"] += int(seed_digit == 0)

            for entry in scaffold["retained_window_additions"]:
                phase = entry["phase_register"]
                idx = entry["window_index_within_register"]
                if phase == "phase_a":
                    digit = window_digit_u16(a_scalar, idx)
                    lookup = compute_window_lookup(g_window_bases, idx, digit, SECP_P, SECP_B)
                else:
                    digit = window_digit_u16(b_scalar, idx)
                    lookup = compute_window_lookup(h_window_bases, idx, digit, SECP_P, SECP_B)
                acc_proj = affine_to_proj(acc, SECP_P)
                got_proj = exec_netlist(leaf["instructions"], SECP_P, acc_proj, lookup, 0 if lookup is None else 1)
                acc = proj_to_affine(got_proj, SECP_P)

            tail_digits = [window_digit_u16(b_scalar, idx) for idx in (13, 14, 15)]
            if any(tail_digits):
                summary["tail_nonzero_cases"] += 1
            for idx, digit in zip((13, 14, 15), tail_digits):
                lookup = compute_window_lookup(h_window_bases, idx, digit, SECP_P, SECP_B)
                acc = add_affine(acc, lookup, SECP_P, SECP_B)

            expected = add_affine(
                mul_affine(a_scalar, SECP_G, SECP_P, SECP_B, order=SECP_N),
                mul_affine(b_scalar, h_point, SECP_P, SECP_B, order=SECP_N),
                SECP_P,
                SECP_B,
            )
            ok = acc == expected and is_on_curve(acc, SECP_P, SECP_B) and is_on_curve(expected, SECP_P, SECP_B)
            summary["total"] += 1
            summary["pass"] += int(ok)
            if progress is not None:
                progress(i + 1, case_count)
            writer.writerow([i, format(h_scalar, "064x"), format(a_scalar, "064x"), format(b_scalar, "064x"), *hex_or_inf(compute_window_lookup(g_window_bases, 0, seed_digit, SECP_P, SECP_B)), *hex_or_inf(expected), *hex_or_inf(acc), *[str(x) for x in tail_digits], "PASS" if ok else "FAIL"])

    summary["phase_b_base_variants"] = len(unique_h)
    out_json = artifact_extended_verification_path(package_root, "scaffold_schedule_summary.json")
    result = {
        "sha256": sha256_path(out_csv),
        "csv": out_csv.name,
        "leaf_sha256": leaf_sha,
        "scaffold_sha256": scaffold_sha,
        "summary": summary,
        "notes": [
            "This check executes the published retained-window schedule as written: one direct seed, 28 retained optimized leaf calls, and 3 classical tail elisions.",
            "It does not claim to reconstruct Google's private call ordering; it checks that the published schedule metadata is internally coherent and semantically complete.",
        ],
    }
    dump_json(out_json, result)
    return result


def run_extended_toy_family(
    repo_root: Path,
    progress: Callable[[int, int], None] | None = None,
) -> Dict[str, Any]:
    package_root = repo_root / "artifacts"
    family = load_json(artifact_circuits_path(package_root, "optimized_pointadd_family.json"))
    out_csv = artifact_extended_verification_path(package_root, "toy_curve_family_extended_110692.csv")
    summary: Dict[str, Any] = {"total": 0, "pass": 0, "curves": {}, "metadata_checks": {}}
    total_cases = sum(curve["order"] * curve["order"] for curve in CURATED_EXTENDED_TOY_CURVES)
    completed_cases = 0

    with out_csv.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["curve", "field_p", "curve_b", "group_order", "a_scalar", "b_scalar", "expected_x", "expected_y", "leaf_x", "leaf_y", "status"])
        for curve in CURATED_EXTENDED_TOY_CURVES:
            p, b, order = curve["p"], curve["b"], curve["order"]
            gen = curve["generator"]
            cname = curve["name"]
            width = 4
            bits = max(1, order.bit_length())
            tables = precompute_window_tables(gen, p, b, width=width, bits=bits)
            nl = specialize_family_netlist(family, 3 * b)["instructions"]
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
                    ok = got_aff == ref_aff and is_on_curve(got_aff, p, b)
                    summary["total"] += 1
                    summary["pass"] += int(ok)
                    curve_total += 1
                    curve_pass += int(ok)
                    completed_cases += 1
                    if progress is not None:
                        progress(completed_cases, total_cases)
                    writer.writerow([cname, p, b, order, a, bb, *minimal_hex_or_inf(ref_aff), *minimal_hex_or_inf(got_aff), "PASS" if ok else "FAIL"])
            summary["curves"][cname] = {"total": curve_total, "pass": curve_pass, "order": order, "p": p, "b": b}
            summary["metadata_checks"][cname] = verify_curve_metadata(curve)

    out_json = artifact_extended_verification_path(package_root, "toy_curve_family_extended_summary.json")
    result = {
        "sha256": sha256_path(out_csv),
        "csv": out_csv.name,
        "summary": summary,
        "notes": [
            "The quick verifier exhausts two toy curves. The extended verifier exhausts four prime-order j=0 curves spanning orders 61, 127, 181, and 241.",
            "This is still a finite-model family check, not a proof over all prime fields.",
        ],
    }
    dump_json(out_json, result)
    return result


def run_projection_sensitivity(repo_root: Path) -> Dict[str, Any]:
    package_root = repo_root / "artifacts"
    projection = load_json(artifact_projection_path(package_root, "resource_projection.json"))
    low_q = projection["public_google_baseline"]["low_qubit"]
    low_g = projection["public_google_baseline"]["low_gate"]
    opt2 = projection["optimized_ecdlp_projection"]["lookup_model_2channel"]["total_non_clifford"]
    opt3 = projection["optimized_ecdlp_projection"]["lookup_model_3channel"]["total_non_clifford"]
    optq = projection["optimized_ecdlp_projection"]["logical_qubits_total"]

    additive_overheads = [0, 1_000_000, 2_000_000, 4_000_000, 8_000_000, 16_000_000, 32_000_000]
    multiplicative_overheads = [1.0, 1.1, 1.25, 1.5, 1.75, 2.0]
    qubit_overheads = [0, 16, 32, 64, 96, 128, 192]

    scenarios = []
    for add_nc in additive_overheads:
        for mult in multiplicative_overheads:
            for add_q in qubit_overheads:
                nc2 = int(round(opt2 * mult + add_nc))
                nc3 = int(round(opt3 * mult + add_nc))
                qq = optq + add_q
                scenarios.append({
                    "extra_non_clifford": add_nc,
                    "multiplier": mult,
                    "extra_qubits": add_q,
                    "beats_low_gate_2lookup": nc2 < low_g["non_clifford"] and qq < low_g["logical_qubits"],
                    "beats_low_qubit_2lookup": nc2 < low_q["non_clifford"] and qq < low_q["logical_qubits"],
                    "beats_low_gate_3lookup": nc3 < low_g["non_clifford"] and qq < low_g["logical_qubits"],
                    "beats_low_qubit_3lookup": nc3 < low_q["non_clifford"] and qq < low_q["logical_qubits"],
                })

    result = {
        "base": {
            "optimized_qubits": optq,
            "optimized_nc_2lookup": opt2,
            "optimized_nc_3lookup": opt3,
            "google_low_qubit": low_q,
            "google_low_gate": low_g,
        },
        "headroom": {
            "non_clifford_margin_vs_low_qubit_2lookup": low_q["non_clifford"] - opt2,
            "non_clifford_margin_vs_low_gate_2lookup": low_g["non_clifford"] - opt2,
            "non_clifford_margin_vs_low_qubit_3lookup": low_q["non_clifford"] - opt3,
            "non_clifford_margin_vs_low_gate_3lookup": low_g["non_clifford"] - opt3,
            "qubit_margin_vs_low_qubit": low_q["logical_qubits"] - optq,
            "qubit_margin_vs_low_gate": low_g["logical_qubits"] - optq,
            "break_even_multiplier_vs_low_gate_2lookup": low_g["non_clifford"] / opt2,
            "break_even_multiplier_vs_low_qubit_2lookup": low_q["non_clifford"] / opt2,
            "break_even_multiplier_vs_low_gate_3lookup": low_g["non_clifford"] / opt3,
            "break_even_multiplier_vs_low_qubit_3lookup": low_q["non_clifford"] / opt3,
        },
        "scenario_grid": scenarios,
        "notes": [
            "This file is not a proof. It is a robustness check against hostile reinterpretations of the backend model.",
            "If an objection can be modeled as additive or multiplicative backend overhead, these margins show how much room the optimized projection still has before losing the public-baseline win.",
        ],
    }
    out_json = artifact_projection_path(package_root, "projection_sensitivity.json")
    dump_json(out_json, result)
    return result


def run_meta_analysis(repo_root: Path) -> Dict[str, Any]:
    package_root = repo_root / "artifacts"
    opt = load_json(artifact_circuits_path(package_root, "optimized_pointadd_secp256k1.json"))
    proj = load_json(artifact_projection_path(package_root, "resource_projection.json"))
    from collections import Counter
    opt_ops = Counter(ins["op"] for ins in opt["instructions"])
    google_baseline = proj["public_google_baseline"]
    low_qubit = google_baseline["low_qubit"]
    low_gate = google_baseline["low_gate"]
    optimized_leaf_projection = proj["optimized_leaf_projection"]
    optimized_projection = proj["optimized_ecdlp_projection"]
    result = {
        "google_baseline_estimates": {
            "source": google_baseline["source"],
            "window_size": google_baseline["window_size"],
            "retained_window_additions": google_baseline["retained_window_additions"],
            "low_qubit": low_qubit,
            "low_gate": low_gate,
        },
        "optimized_leaf": {"instruction_count": len(opt["instructions"]), "register_count": len(opt["arithmetic_slots"]), "operation_mix": dict(opt_ops)},
        "optimized_vs_google_estimates": {
            "optimized_leaf_logical_qubits": optimized_leaf_projection["scratch_logical_qubits"],
            "optimized_leaf_modeled_non_clifford_excluding_lookup": optimized_leaf_projection["modeled_non_clifford_excluding_lookup"],
            "vs_low_qubit_non_clifford_factor": low_qubit["non_clifford"] / optimized_projection["lookup_model_2channel"]["total_non_clifford"],
            "vs_low_gate_non_clifford_factor": low_gate["non_clifford"] / optimized_projection["lookup_model_2channel"]["total_non_clifford"],
            "vs_low_qubit_logical_qubit_factor": low_qubit["logical_qubits"] / optimized_projection["logical_qubits_total"],
            "vs_low_gate_logical_qubit_factor": low_gate["logical_qubits"] / optimized_projection["logical_qubits_total"],
        },
        "resource_projection_headline": proj["improvement_vs_google"],
        "main_reason_codes": [
            {"code": "COMPLETE_MIXED_J0", "description": "The optimized leaf uses a secp256k1-specialized complete mixed j=0 formula with a narrow, branch-free hot path."},
            {"code": "WORKING_WIDTH_CONTROL", "description": "The optimized arithmetic schedule keeps the working state compact at 12 arithmetic slots while preserving exact ISA-level basis-state semantics."},
            {"code": "WINDOW_RETENTION_DISCIPLINE", "description": "The repository keeps the public retained-window structure explicit instead of hiding schedule changes inside headline totals."},
            {"code": "BOUNDARY_HONESTY", "description": "The mainline resource win is reported as a backend projection against cited rounded Google estimates, while exact checked artifacts extend through ISA arithmetic, the folded lookup contract, and the compiler project's explicit lookup-lowering layer."},
        ],
        "notes": [
            "This file compares the primary optimized artifact against cited rounded Google estimates stored in the projection file.",
            "The Google numbers are published resource estimates, not machine-readable ISA schedules.",
        ],
    }
    out_json = artifact_projection_path(package_root, "meta_analysis.json")
    dump_json(out_json, result)
    return result


def run_claim_boundary_matrix(repo_root: Path) -> Dict[str, Any]:
    package_root = repo_root / "artifacts"
    projection = load_json(artifact_projection_path(package_root, "resource_projection.json"))
    result = {
        "layers": [
            {
                "layer": "optimized_leaf_arithmetic",
                "status": "exact_machine_checked",
                "evidence": ["optimized_pointadd_secp256k1.json", "optimized_pointadd_audit_16384.csv", "toy_curve_exhaustive_19850.csv", "toy_curve_family_extended_110692.csv"],
                "notes": "Arithmetic semantics of Q <- Q + L are exact on basis-state inputs at the kickmix ISA level.",
            },
            {
                "layer": "lookup_table_contract",
                "status": "exact_contract_semantics_machine_checked_not_flattened",
                "evidence": ["lookup_signed_fold_contract.json", "lookup_signed_fold_summary.json", "lookup_contract_summary.json"],
                "notes": "The repo validates the checked-in folded contract parameters and audits its semantics exhaustively for one secp256k1 base plus deterministic multibase samples, but does not ship a primitive-gate qRAM implementation.",
            },
            {
                "layer": "retained_window_scaffold",
                "status": "hierarchical_schedule_tested",
                "evidence": ["ecdlp_scaffold_optimized.json", "scaffold_schedule_audit_256.csv"],
                "notes": "The schedule is exact metadata plus sampled end-to-end replay, not a flat gate list for the whole Shor stack.",
            },
            {
                "layer": "mbuc_cleanup",
                "status": "exact_isa_coherent_pair_machine_checked_not_flattened",
                "evidence": ["optimized_pointadd_secp256k1.json", "coherent_cleanup_audit_16384.csv", "coherent_cleanup_summary.json"],
                "notes": "The shipped one-bit cleanup pair is exact and machine-checked at the ISA boundary: the same metadata bit that sets the neutral-entry control is applied again to uncompute it after selection. The repository still does not ship a primitive-gate lowering of that pair.",
            },
            {
                "layer": "backend_resource_projection",
                "status": "modeled_not_theorem_proved",
                "evidence": ["resource_projection.json", "projection_sensitivity.json"],
                "notes": f"Public baseline comparison uses rounded Google estimates of {projection['public_google_baseline']['low_qubit']['logical_qubits']}/{projection['public_google_baseline']['low_qubit']['non_clifford']} and {projection['public_google_baseline']['low_gate']['logical_qubits']}/{projection['public_google_baseline']['low_gate']['non_clifford']}.",
            },
        ]
    }
    out_json = artifact_projection_path(package_root, "claim_boundary_matrix.json")
    dump_json(out_json, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run extended verification and publication-readiness checks.")
    parser.add_argument("--repo-root", default=".", help="Repository root.")
    parser.add_argument("--mode", choices=["lookup", "cleanup", "scaffold", "toy_extended", "sensitivity", "meta", "boundaries", "all"], default="all", help="Verification mode.")
    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()

    overall: Dict[str, Any] = {}
    if args.mode in ("lookup", "all"):
        overall["lookup_contract"] = run_lookup_contract(repo_root)
    if args.mode in ("cleanup", "all"):
        overall["coherent_cleanup"] = run_coherent_cleanup(repo_root)
    if args.mode in ("scaffold", "all"):
        overall["scaffold_schedule"] = run_scaffold_schedule(repo_root)
    if args.mode in ("toy_extended", "all"):
        overall["toy_extended"] = run_extended_toy_family(repo_root)
    if args.mode in ("sensitivity", "all"):
        overall["projection_sensitivity"] = run_projection_sensitivity(repo_root)
    if args.mode in ("meta", "all"):
        overall["meta_analysis"] = run_meta_analysis(repo_root)
    if args.mode in ("boundaries", "all"):
        overall["claim_boundaries"] = run_claim_boundary_matrix(repo_root)

    out_path = repo_root / "results" / "extended_verification_summary.json"
    dump_json(out_path, overall)
    print(json.dumps(overall, indent=2))


if __name__ == "__main__":
    main()
