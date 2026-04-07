#!/usr/bin/env python3
"""Additional research experiments and literature-facing artifacts.

This module extends the repository without changing the core exactness claims.
Everything here is deliberately explicit about whether it is:
- exact and audited on the current ISA-level artifact,
- a deterministic benchmark generator, or
- a heuristic projection inspired by the literature.

The default research pass adds four kinds of outputs:
1. objective cost-breakdown artifacts showing where the modeled budget sits,
2. deterministic challenge-ladder benchmarks over small secp256k1-family curves,
3. machine-readable literature/reference matrices, and
4. publication-facing summaries tying the above together.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from common import (
    SECP_B,
    add_affine,
    affine_to_proj,
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
from verifier import exec_netlist, specialize_family_netlist
from lookup_research import (
    build_lookup_folded_contract,
    build_lookup_folded_projection,
    build_lookup_folded_scaffold,
    run_lookup_folding_audit,
)

PointAffine = Optional[Tuple[int, int]]


def is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    f = 3
    limit = int(math.isqrt(n))
    while f <= limit:
        if n % f == 0:
            return False
        f += 2
    return True


def factor_trial(n: int) -> List[Tuple[int, int]]:
    out: List[Tuple[int, int]] = []
    if n % 2 == 0:
        e = 0
        while n % 2 == 0:
            n //= 2
            e += 1
        out.append((2, e))
    d = 3
    while d * d <= n:
        if n % d == 0:
            e = 0
            while n % d == 0:
                n //= d
                e += 1
            out.append((d, e))
        d += 2
    if n > 1:
        out.append((n, 1))
    return out


def largest_prime_factor(n: int) -> int:
    return max(p for p, _ in factor_trial(n))


def legendre_symbol(a: int, p: int) -> int:
    if a % p == 0:
        return 0
    ls = pow(a % p, (p - 1) // 2, p)
    if ls == p - 1:
        return -1
    return ls


def sqrt_p3mod4(rhs: int, p: int) -> Optional[int]:
    rhs %= p
    if rhs == 0:
        return 0
    if p % 4 != 3:
        raise ValueError("sqrt_p3mod4 requires p ≡ 3 mod 4")
    if legendre_symbol(rhs, p) != 1:
        return None
    return pow(rhs, (p + 1) // 4, p)


def count_points_a0_b7(p: int, b: int = 7) -> int:
    total = 1  # point at infinity
    for x in range(p):
        rhs = (x * x * x + b) % p
        ls = legendre_symbol(rhs, p)
        if ls == 0:
            total += 1
        elif ls == 1:
            total += 2
    return total


def point_order(point: PointAffine, p: int, b: int, max_steps: int) -> int:
    if point is None:
        return 1
    acc = None
    for i in range(1, max_steps + 1):
        acc = add_affine(acc, point, p, b)
        if acc is None:
            return i
    raise ValueError("point order search exceeded bound")


def deterministic_point_in_subgroup(p: int, b: int, subgroup_order: int, cofactor: int, label: str) -> PointAffine:
    """Find a deterministic nonzero point of exact prime order on y^2 = x^3 + 7.

    The search is intentionally simple and reproducible.  We hash a label to an
    x-start value, scan for curve points, and project them into the subgroup by
    multiplying by the cofactor.
    """
    seed = hashlib.sha256(label.encode()).digest()
    start = int.from_bytes(seed[:8], 'big') % p
    for offset in range(p):
        x = (start + offset) % p
        rhs = (x * x * x + b) % p
        y = sqrt_p3mod4(rhs, p)
        if y is None:
            continue
        candidate = (x, y)
        g = mul_affine(cofactor, candidate, p, b)
        if g is None:
            continue
        if mul_affine(subgroup_order, g, p, b) is None and point_order(g, p, b, subgroup_order) == subgroup_order:
            return g
    raise RuntimeError(f"failed to find subgroup point for p={p}, order={subgroup_order}")


def find_curve_fast(bits: int, b: int = 7, subgroup_min_bits: Optional[int] = None, search_limit: int = 300_000) -> Dict[str, Any]:
    """Deterministically build a small benchmark curve in the secp256k1 family.

    We search primes p ≡ 3 (mod 4) near the target bit size and keep the first one
    whose group order has a sufficiently large prime factor.  This is fast enough
    for benchmark sizes and makes the ladder reproducible from source.
    """
    if subgroup_min_bits is None:
        subgroup_min_bits = max(5, bits - 1)
    start = (1 << (bits - 1)) + 1
    if start % 2 == 0:
        start += 1
    p = start
    tries = 0
    while tries < search_limit:
        if p % 4 == 3 and is_prime(p):
            group_order = count_points_a0_b7(p, b)
            subgroup_order = largest_prime_factor(group_order)
            if subgroup_order.bit_length() >= subgroup_min_bits:
                cofactor = group_order // subgroup_order
                generator = deterministic_point_in_subgroup(p, b, subgroup_order, cofactor, f"secp-family-{bits}")
                return {
                    "field_bits": bits,
                    "p": p,
                    "b": b,
                    "group_order": group_order,
                    "subgroup_order": subgroup_order,
                    "subgroup_bits": subgroup_order.bit_length(),
                    "cofactor": cofactor,
                    "generator": generator,
                }
        p += 2
        tries += 1
    raise RuntimeError(f"failed to find benchmark curve for {bits} bits")


def compute_dominant_cost_breakdown(repo_root: Path) -> Dict[str, Any]:
    """Compute the modeled arithmetic-vs-lookup split correctly.

    Important correction:
    The optimized leaf projection stores the arithmetic cost **per retained
    windowed point-add leaf**, not for the whole 28-call scaffold.  Earlier
    research-pass artifacts accidentally subtracted this per-leaf number from the
    whole-circuit total and therefore overstated the lookup share.  This function
    fixes that by multiplying the arithmetic leaf cost by the retained window
    count before forming whole-circuit shares.
    """
    projection = load_json(repo_root / "artifacts" / "out" / "resource_projection.json")
    windows = int(projection["optimized_ecdlp_projection"]["retained_window_additions"])
    per_leaf_arith = int(projection["optimized_leaf_projection"]["modeled_non_clifford_excluding_lookup"])
    total2 = int(projection["optimized_ecdlp_projection"]["lookup_model_2channel"]["total_non_clifford"])
    total3 = int(projection["optimized_ecdlp_projection"]["lookup_model_3channel"]["total_non_clifford"])
    total_arith = windows * per_leaf_arith
    lookup2 = total2 - total_arith
    lookup3 = total3 - total_arith

    if lookup2 < 0 or lookup3 < 0:
        raise ValueError("resource projection is inconsistent: lookup contribution became negative")

    goals = [30_000_000, 29_000_000, 25_000_000, 20_000_000]
    target_table = []
    for goal in goals:
        target_table.append({
            "goal_total_non_clifford": goal,
            "required_lookup_reduction_fraction_2lookup_without_other_changes": (total2 - goal) / lookup2,
            "required_lookup_reduction_fraction_3lookup_without_other_changes": (total3 - goal) / lookup3,
            "lookup_only_feasible_2lookup": goal >= total_arith,
            "lookup_only_feasible_3lookup": goal >= total_arith,
        })

    result = {
        "baseline": {
            "retained_window_additions": windows,
            "modeled_non_clifford_per_leaf_arithmetic_only": per_leaf_arith,
            "modeled_non_clifford_total_arithmetic_only": total_arith,
            "total_non_clifford_2lookup": total2,
            "total_non_clifford_3lookup": total3,
        },
        "breakdown": {
            "lookup_non_clifford_2lookup": lookup2,
            "lookup_non_clifford_3lookup": lookup3,
            "lookup_share_fraction_2lookup": lookup2 / total2,
            "lookup_share_fraction_3lookup": lookup3 / total3,
            "arithmetic_share_fraction_2lookup": total_arith / total2,
            "arithmetic_share_fraction_3lookup": total_arith / total3,
        },
        "ceilings": {
            "perfect_arithmetic_elimination_total_2lookup": lookup2,
            "perfect_arithmetic_elimination_total_3lookup": lookup3,
            "max_total_reduction_fraction_from_arithmetic_only_2lookup": total_arith / total2,
            "max_total_reduction_fraction_from_arithmetic_only_3lookup": total_arith / total3,
        },
        "lookup_reduction_targets": target_table,
        "main_takeaway": {
            "summary": "Under the current explicit backend model, arithmetic still dominates the optimized mainline total, while lookup remains a meaningful secondary frontier.",
            "verdict": "A clean next step is to improve the lookup contract without rewriting the arithmetic leaf; however, another dramatic overall drop would eventually require arithmetic-backend or schedule changes too.",
        },
        "notes": [
            "This file is derived only from repository artifacts already present in the tree.",
            "It corrects an earlier internal research-pass bug where the per-leaf arithmetic budget was accidentally treated as the whole-circuit arithmetic budget.",
        ],
    }
    out_path = repo_root / "artifacts" / "out" / "dominant_cost_breakdown.json"
    dump_json(out_path, result)
    return result


def compute_literature_projection_scenarios(repo_root: Path) -> Dict[str, Any]:
    breakdown = load_json(repo_root / "artifacts" / "out" / "dominant_cost_breakdown.json")
    projection = load_json(repo_root / "artifacts" / "out" / "resource_projection.json")
    folded = load_json(repo_root / "artifacts" / "out" / "lookup_folded_projection.json")
    google = projection["public_google_baseline"]
    total_arith = int(breakdown["baseline"]["modeled_non_clifford_total_arithmetic_only"])
    total2 = int(breakdown["baseline"]["total_non_clifford_2lookup"])
    total3 = int(breakdown["baseline"]["total_non_clifford_3lookup"])
    lookup2 = int(breakdown["breakdown"]["lookup_non_clifford_2lookup"])
    lookup3 = int(breakdown["breakdown"]["lookup_non_clifford_3lookup"])

    def gains(total: int) -> Dict[str, float]:
        return {
            "vs_google_low_qubit": google["low_qubit"]["non_clifford"] / total,
            "vs_google_low_gate": google["low_gate"]["non_clifford"] / total,
        }

    scenarios: List[Dict[str, Any]] = []

    exact_ceiling_2 = total2 - total_arith
    exact_ceiling_3 = total3 - total_arith
    scenarios.append({
        "name": "exact_arithmetic_elimination_ceiling",
        "status": "upper_bound_from_current_repo_model",
        "assumptions": [
            "All currently modeled non-lookup arithmetic cost disappears.",
            "Lookup costs are unchanged.",
        ],
        "projected_total_non_clifford_2lookup": exact_ceiling_2,
        "projected_total_non_clifford_3lookup": exact_ceiling_3,
        "gains": {
            "lookup2": gains(exact_ceiling_2),
            "lookup3": gains(exact_ceiling_3),
        },
    })

    litinski_cases = []
    for mul_share in (0.75, 0.85, 0.95):
        for mul_saving in (0.15, 0.20, 0.25, 0.30):
            saved = total_arith * mul_share * mul_saving
            litinski_cases.append({
                "multiplier_share_of_total_arithmetic_budget": mul_share,
                "multiplier_saving_fraction": mul_saving,
                "projected_total_non_clifford_2lookup": int(round(total2 - saved)),
                "projected_total_non_clifford_3lookup": int(round(total3 - saved)),
                "total_reduction_fraction_2lookup": saved / total2,
                "total_reduction_fraction_3lookup": saved / total3,
            })
    scenarios.append({
        "name": "litinski_style_multiplier_swap_band",
        "status": "heuristic_translation",
        "assumptions": [
            "A large fraction of the current arithmetic budget is multiplier-dominated.",
            "A schoolbook-multiplier improvement affects only that arithmetic fraction, not the lookup budget.",
            "This is a model-level translation, not an audited rewrite of the repository's exact leaf.",
        ],
        "cases": litinski_cases,
        "envelope": {
            "best_total_reduction_fraction_2lookup": max(case["total_reduction_fraction_2lookup"] for case in litinski_cases),
            "best_total_reduction_fraction_3lookup": max(case["total_reduction_fraction_3lookup"] for case in litinski_cases),
            "best_projected_total_non_clifford_2lookup": min(case["projected_total_non_clifford_2lookup"] for case in litinski_cases),
            "best_projected_total_non_clifford_3lookup": min(case["projected_total_non_clifford_3lookup"] for case in litinski_cases),
        },
    })

    lookup_frontiers = []
    for frac in (0.01, 0.03, 0.05, 0.10, 0.20, 0.30, 1.0 / 3.0, 0.50):
        projected2 = int(round(total2 - lookup2 * frac))
        projected3 = int(round(total3 - lookup3 * frac))
        lookup_frontiers.append({
            "lookup_reduction_fraction": frac,
            "projected_total_non_clifford_2lookup": projected2,
            "projected_total_non_clifford_3lookup": projected3,
            "gains": {
                "lookup2": gains(projected2),
                "lookup3": gains(projected3),
            },
        })
    scenarios.append({
        "name": "lookup_layer_reduction_frontier",
        "status": "model_projection",
        "assumptions": [
            "Only the modeled lookup contribution is reduced.",
            "Arithmetic cost and logical-qubit headline remain unchanged.",
        ],
        "cases": lookup_frontiers,
    })

    scenarios.append({
        "name": "signed_lookup_folding_contract_projection",
        "status": "exact_contract_plus_modeled_backend_projection",
        "assumptions": folded["assumptions"],
        "pad_sweep": folded["pad_sweep"],
        "base_case_pad0": folded["base_case_pad0"],
    })

    result = {
        "baseline_headline": {
            "logical_qubits": projection["optimized_ecdlp_projection"]["logical_qubits_total"],
            "total_non_clifford_2lookup": total2,
            "total_non_clifford_3lookup": total3,
        },
        "scenarios": scenarios,
        "takeaways": [
            "Correcting the cost model shows that arithmetic, not lookup, dominates the current modeled total.",
            "The signed two's-complement lookup-folding optimization is now merged into the mainline and gives a clean exact lookup-contract improvement of about 5.9% in the 2-channel line and about 8.4% in the conservative 3-channel line versus the previous unfolded lookup reference at zero extra pad.",
            "Another dramatic overall improvement would likely require arithmetic-backend substitution or combined lookup-plus-arithmetic changes rather than lookup work alone.",
        ],
        "notes": [
            "These scenario files complement the mainline projection rather than replacing the repository's exact ISA-level artifact boundary.",
            "The signed lookup-folding scenario is stronger than a pure heuristic because the signed-fold contract itself is explicitly encoded and audited over the full 16-bit domain for one secp256k1 window base.",
        ],
    }
    out_path = repo_root / "artifacts" / "out" / "literature_projection_scenarios.json"
    dump_json(out_path, result)
    return result


def build_challenge_ladder(repo_root: Path, bit_sizes: Iterable[int] = (6, 8, 10, 12, 14, 16, 18)) -> Dict[str, Any]:
    ladder_curves = []
    for bits in bit_sizes:
        curve = find_curve_fast(bits, b=SECP_B, subgroup_min_bits=max(5, bits - 1))
        order = curve["subgroup_order"]
        scalar = int.from_bytes(hashlib.sha256(f"challenge-{bits}".encode()).digest()[:16], 'big') % order
        if scalar == 0:
            scalar = 1
        challenge = mul_affine(scalar, curve["generator"], curve["p"], curve["b"], order=order)
        curve["challenge_scalar"] = scalar
        curve["challenge_point"] = challenge
        ladder_curves.append(curve)

    serializable = {
        "family": "y^2 = x^3 + 7 over prime fields with p ≡ 3 (mod 4)",
        "purpose": "Deterministic secp256k1-family regression ladder for tiny exact and near-exact end-to-end checks.",
        "curves": [
            {
                **{k: v for k, v in curve.items() if k not in ("generator", "challenge_point")},
                "generator": {"x": curve["generator"][0], "y": curve["generator"][1]},
                "challenge_point": {"x": curve["challenge_point"][0], "y": curve["challenge_point"][1]},
            }
            for curve in ladder_curves
        ],
        "notes": [
            "This ladder is self-generated inside the repository and is not copied from an external benchmark suite.",
            "It is intended for regression testing, transparency, and external reimplementation paths rather than for headline quantum resource claims.",
        ],
    }
    out_dir = repo_root / "benchmarks" / "challenge_ladder"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "challenge_ladder.json"
    dump_json(out_path, serializable)
    return serializable


def run_challenge_ladder_audit(repo_root: Path, max_random_scalars_per_curve: int = 128) -> Dict[str, Any]:
    ladder = load_json(repo_root / "benchmarks" / "challenge_ladder" / "challenge_ladder.json")
    family = load_json(repo_root / "artifacts" / "out" / "optimized_pointadd_family.json")
    out_dir = repo_root / "benchmarks" / "challenge_ladder"
    out_csv = out_dir / "challenge_ladder_audit.csv"

    total = 0
    passed = 0
    curves_summary: Dict[str, Any] = {}
    seed_material = sha256_bytes(json.dumps(ladder, sort_keys=True).encode())

    with out_csv.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "curve_bits",
            "field_p",
            "subgroup_order",
            "width",
            "scalar",
            "challenge_scalar",
            "accumulated_x",
            "accumulated_y",
            "direct_mul_x",
            "direct_mul_y",
            "challenge_point_x",
            "challenge_point_y",
            "status",
        ])

        for curve_obj in ladder["curves"]:
            p = int(curve_obj["p"])
            b = int(curve_obj["b"])
            order = int(curve_obj["subgroup_order"])
            field_bits = int(curve_obj["field_bits"])
            generator = (int(curve_obj["generator"]["x"]), int(curve_obj["generator"]["y"]))
            challenge_scalar = int(curve_obj["challenge_scalar"])
            challenge_point = (int(curve_obj["challenge_point"]["x"]), int(curve_obj["challenge_point"]["y"]))
            width = 4
            bits = max(1, order.bit_length())
            chunks = (bits + width - 1) // width
            tables = precompute_window_tables(generator, p, b, width=width, bits=bits)
            netlist = specialize_family_netlist(family, 3 * b)["instructions"]

            seed = bytes.fromhex(seed_material) + field_bits.to_bytes(2, "big")
            scalars = [0, 1, 2, order - 1, order // 2, challenge_scalar]
            scalars.extend(deterministic_scalars(seed, max_random_scalars_per_curve, order))
            scalars = list(dict.fromkeys([value % order for value in scalars]))

            local_total = 0
            local_pass = 0
            for scalar in scalars:
                qp = (0, 1, 0)
                x = scalar
                for pos in range(chunks):
                    digit = x & ((1 << width) - 1)
                    entry = None if digit == 0 else tables[pos][digit]
                    key = 0 if digit == 0 else 1
                    qp = exec_netlist(netlist, p, qp, entry, key)
                    x >>= width
                got = proj_to_affine(qp, p)
                ref = mul_fixed_window(scalar, tables, p, b, width=width, order=order)
                ref2 = mul_affine(scalar, generator, p, b, order=order)
                ok = got == ref == ref2
                total += 1
                passed += int(ok)
                local_total += 1
                local_pass += int(ok)
                writer.writerow([
                    field_bits,
                    p,
                    order,
                    width,
                    scalar,
                    challenge_scalar,
                    *hex_or_inf(got),
                    *hex_or_inf(ref),
                    *hex_or_inf(challenge_point),
                    "PASS" if ok else "FAIL",
                ])

            curves_summary[f"bits_{field_bits}"] = {
                "field_bits": field_bits,
                "field_p": p,
                "subgroup_order": order,
                "generator": {"x": generator[0], "y": generator[1]},
                "challenge_scalar": challenge_scalar,
                "challenge_point": {"x": challenge_point[0], "y": challenge_point[1]},
                "tested_scalars": local_total,
                "pass": local_pass,
                "width": width,
            }

    summary = {
        "sha256": sha256_path(out_csv),
        "csv": out_csv.name,
        "summary": {
            "total": total,
            "pass": passed,
            "curve_count": len(curves_summary),
            "curves": curves_summary,
        },
        "notes": [
            "This audit is an end-to-end scalar-accumulation replay over a deterministic family of tiny y^2 = x^3 + 7 benchmark curves.",
            "It strengthens the external reproducibility story without pretending to be a full Shor-period-finding proof.",
        ],
    }
    dump_json(out_dir / "challenge_ladder_summary.json", summary)
    return summary


def build_literature_matrix(repo_root: Path) -> Dict[str, Any]:
    matrix = {
        "entries": [
            {
                "id": "roetteler_2017",
                "year": 2017,
                "layer": "logical_prime_field_baseline",
                "title": "Quantum resource estimates for computing elliptic curve discrete logarithms",
                "headline": "Explicit Toffoli-network baseline with up to 9n + 2⌈log2 n⌉ + 10 qubits and simulated controlled point-add cores.",
                "direct_mergeability": "historical_baseline_only",
                "repo_action": "Keep as the oldest rigorous prime-field anchor for comparisons and sanity checks.",
            },
            {
                "id": "gidney_2019_windowed_qrom",
                "year": 2019,
                "layer": "windowed_lookup_theory",
                "title": "Windowed quantum arithmetic",
                "headline": "QROM/QROAM-style windowed arithmetic with explicit lookup/unlookup tradeoffs and table-lookup cost scaling.",
                "direct_mergeability": "conceptual_lookup_foundation",
                "repo_action": "Use as a primary conceptual baseline for evaluating lookup-table reshaping and signed-domain folding.",
            },
            {
                "id": "haner_2022_space_time_lookup",
                "year": 2022,
                "layer": "windowed_lookup_theory",
                "title": "Space-time optimized table lookup for quantum circuits",
                "headline": "Systematic lookup space-time tradeoffs relevant once the repository lowers more of the lookup layer explicitly.",
                "direct_mergeability": "future_lookup_backend_path",
                "repo_action": "Track as the next backend-model refinement once current folded-lookup contracts are stable.",
            },
            {
                "id": "gouzien_2023",
                "year": 2023,
                "layer": "cat_qubit_physical_architecture",
                "title": "Performance Analysis of a Repetition Cat Code Architecture: Computing 256-bit Elliptic Curve Logarithm in 9 Hours with 126133 Cat Qubits",
                "headline": "Alternative physical architecture reference point with very different hardware assumptions.",
                "direct_mergeability": "physical_reference_point_only",
                "repo_action": "Keep as a reference against the Cain-style neutral-atom extrapolation.",
            },
            {
                "id": "qualtran_2024",
                "year": 2024,
                "layer": "tooling_ir_and_resource_analysis",
                "title": "Expressing and Analyzing Quantum Algorithms with Qualtran",
                "headline": "Open-source library for representing, testing, and tabulating resource requirements of quantum algorithms.",
                "direct_mergeability": "future_tooling_path",
                "repo_action": "Document as an external reimplementation target rather than importing it into the current standard-library verifier.",
            },
            {
                "id": "low_zhu_2024_lookup_architecture",
                "year": 2024,
                "layer": "windowed_lookup_theory",
                "title": "A Unified Architecture for Quantum Lookup Tables",
                "headline": "Parameterized QROM/SELECT-SWAP style lookup architecture with explicit qubit–T-count tradeoffs.",
                "direct_mergeability": "future_lookup_backend_path",
                "repo_action": "Use to bound how much more the repository can squeeze from lookup realization once it goes below the current ISA layer.",
            },
            {
                "id": "litinski_2024",
                "year": 2024,
                "layer": "arithmetic_multiplier_backend",
                "title": "Quantum schoolbook multiplication with fewer Toffoli gates",
                "headline": "Controlled add-subtract multipliers asymptotically halve controlled-adder Toffoli cost.",
                "direct_mergeability": "heuristic_possible",
                "repo_action": "Still one of the highest-value next branches because the corrected cost model shows arithmetic dominates the current total.",
            },
            {
                "id": "khattar_gidney_2025",
                "year": 2025,
                "layer": "windowed_lookup_theory",
                "title": "The rise of conditionally clean ancillae for optimizing quantum circuits",
                "headline": "Unary-iteration and skew-tree tricks that can change lookup and control overhead once the lookup layer is lowered more explicitly.",
                "direct_mergeability": "future_lookup_backend_path",
                "repo_action": "Document as a follow-on if the repository chooses to primitive-lower lookup address decoding and table access.",
            },
            {
                "id": "qrisp_2025",
                "year": 2025,
                "layer": "external_compilable_ecc_stack",
                "title": "End-to-end compilable implementation of quantum elliptic curve logarithm in Qrisp",
                "headline": "One of the first fully compilable implementations of EC arithmetic in Qrisp.",
                "direct_mergeability": "external_reimplementation_path",
                "repo_action": "Reference as a separate compilation route; do not dilute the repository's transparent verifier with framework-specific imports.",
            },
            {
                "id": "luongo_2025",
                "year": 2025,
                "layer": "windowed_lookup_optimizations",
                "title": "Optimized circuits for windowed modular arithmetic with applications to quantum attacks against RSA",
                "headline": "Four lookup/unlookup improvements yielding modest but real logical savings on windowed arithmetic workloads.",
                "direct_mergeability": "conceptually_relevant_but_not_drop_in",
                "repo_action": "Use as a sanity check that lookup work often yields single-digit-percent total wins unless paired with larger architectural changes; this aligns with the new signed-fold branch.",
            },
            {
                "id": "papa_2025",
                "year": 2025,
                "layer": "formal_validation",
                "title": "Validation of Quantum Elliptic Curve Point Addition Circuits",
                "headline": "Shows why EC point-add circuits need aggressive validation and ancilla-cleanup scrutiny.",
                "direct_mergeability": "philosophical_and_methodological",
                "repo_action": "Strengthen red-teaming and cleanup-oriented verification rather than claiming cleanup is solved.",
            },
            {
                "id": "dallaire_demers_2025",
                "year": 2025,
                "layer": "benchmarking",
                "title": "Brace for impact: ECDLP challenges for quantum cryptanalysis",
                "headline": "Argues for precise ECDLP benchmark suites instead of sparse toy examples.",
                "direct_mergeability": "direct_benchmark_inspiration",
                "repo_action": "Keep the deterministic secp-family challenge ladder and extend it over time.",
            },
            {
                "id": "gu_2025",
                "year": 2025,
                "layer": "architecture_sensitive_2d_lattice",
                "title": "Resource analysis of Shor's elliptic curve algorithm with an improved quantum adder on a two-dimensional lattice",
                "headline": "Architecture-aware P-256 resource estimates using improved adders and dynamic-circuit assumptions.",
                "direct_mergeability": "separate_architecture_branch",
                "repo_action": "Track as an alternative physical/logical coupling branch; do not merge into the current baseline headline.",
            },
            {
                "id": "google_babbush_2026",
                "year": 2026,
                "layer": "public_prime_field_baseline",
                "title": "Securing Elliptic Curve Cryptocurrencies against Quantum Vulnerabilities: Resource Estimates and Mitigations",
                "headline": "Public appendix envelope of <1200 / <90M or <1450 / <70M plus ZK proof of existence without releasing the hidden circuit.",
                "direct_mergeability": "already_integrated",
                "repo_action": "Remain the main public secp256k1 comparison baseline.",
            },
            {
                "id": "cain_2026",
                "year": 2026,
                "layer": "neutral_atom_physical_architecture",
                "title": "Shor's algorithm is possible with as few as 10,000 reconfigurable atomic qubits",
                "headline": "Approximate physical architecture estimates for ECC-256 / P-256 with 10,000 to 26,000 physical qubits and day-scale runtimes under aggressive parallelism assumptions.",
                "direct_mergeability": "already_integrated_as_approx_transfer",
                "repo_action": "Keep as the primary physical-stack integration in the repo.",
            },
            {
                "id": "luo_2026",
                "year": 2026,
                "layer": "low_qubit_inversion_branch",
                "title": "Space-Efficient Quantum Algorithm for Elliptic Curve Discrete Logarithms with Resource Estimation",
                "headline": "3n + 4 floor(log2 n) modular inversion and 5n + 4 floor(log2 n) ECDLP qubit scaling; 1333 logical qubits quoted for a 256-bit prime-field curve.",
                "direct_mergeability": "candidate_alt_branch_not_mainline",
                "repo_action": "Good candidate for a future ultra-low-qubit branch, but not a drop-in improvement to the current mixed-formula mainline.",
            },
            {
                "id": "qcec_repo",
                "year": 2026,
                "layer": "equivalence_checking_tooling",
                "title": "MQT QCEC repository",
                "headline": "Open-source quantum circuit equivalence checker with partial-equivalence handling for ancilla and garbage qubits.",
                "direct_mergeability": "future_flattening_path",
                "repo_action": "Document as the right external checker once circuit fragments are lowered to OpenQASM / primitive gates.",
            },
        ],
        "notes": [
            "This matrix is intentionally selective: it includes only works that materially affect how this repository should be interpreted, tested, or extended.",
            "The corrected cost model changes the optimization story: arithmetic papers remain highly relevant, while lookup papers now guide a meaningful but bounded secondary frontier.",
        ],
    }
    out_path = repo_root / "results" / "literature_matrix.json"
    dump_json(out_path, matrix)
    return matrix


def build_physical_stack_reference(repo_root: Path) -> Dict[str, Any]:
    result = {
        "entries": [
            {
                "id": "google_2026_superconducting",
                "layer": "logical_to_physical_reference",
                "headline": "Public whitepaper states that the cited ECDLP-256 estimates can execute in minutes on superconducting architectures with fewer than half a million physical qubits under its assumptions.",
                "status_in_repo": "baseline_context_only",
            },
            {
                "id": "cain_2026_neutral_atom",
                "layer": "physical_architecture_integration",
                "headline": "Approximate transfer already integrated in results/cain_2026_integration_summary.json.",
                "status_in_repo": "integrated",
            },
            {
                "id": "gouzien_2023_cat_qubit",
                "layer": "alternative_physical_architecture_reference",
                "headline": "Reports 9 hours with 126,133 cat qubits for a 256-bit elliptic-curve logarithm under cat-code assumptions.",
                "status_in_repo": "reference_only",
            },
        ],
        "notes": [
            "These points live at different abstraction layers and should not be collapsed into a single apples-to-apples headline without major caveats.",
            "The repository's strongest exact claim remains at the kickmix ISA arithmetic layer, not at the physical architecture layer.",
        ],
    }
    out_path = repo_root / "results" / "physical_stack_reference_points.json"
    dump_json(out_path, result)
    return result


def run_research_pass(repo_root: Path) -> Dict[str, Any]:
    dominant = compute_dominant_cost_breakdown(repo_root)
    lookup_contract = build_lookup_folded_contract(repo_root)
    lookup_scaffold = build_lookup_folded_scaffold(repo_root, lookup_contract)
    lookup_audit = run_lookup_folding_audit(repo_root)
    lookup_projection = build_lookup_folded_projection(repo_root)
    literature_scenarios = compute_literature_projection_scenarios(repo_root)
    ladder = build_challenge_ladder(repo_root)
    ladder_audit = run_challenge_ladder_audit(repo_root)
    literature_matrix = build_literature_matrix(repo_root)
    physical_refs = build_physical_stack_reference(repo_root)

    base_pad0 = lookup_projection["base_case_pad0"]
    result = {
        "dominant_cost_breakdown": {
            "lookup_share_fraction_2lookup": dominant["breakdown"]["lookup_share_fraction_2lookup"],
            "lookup_share_fraction_3lookup": dominant["breakdown"]["lookup_share_fraction_3lookup"],
            "arithmetic_share_fraction_2lookup": dominant["breakdown"]["arithmetic_share_fraction_2lookup"],
            "arithmetic_share_fraction_3lookup": dominant["breakdown"]["arithmetic_share_fraction_3lookup"],
            "max_total_reduction_fraction_from_arithmetic_only_2lookup": dominant["ceilings"]["max_total_reduction_fraction_from_arithmetic_only_2lookup"],
            "max_total_reduction_fraction_from_arithmetic_only_3lookup": dominant["ceilings"]["max_total_reduction_fraction_from_arithmetic_only_3lookup"],
        },
        "lookup_folding": {
            "contract_sha256": sha256_path(repo_root / "artifacts" / "out" / "lookup_signed_fold_contract.json"),
            "folded_scaffold_sha256": sha256_path(repo_root / "artifacts" / "out" / "ecdlp_scaffold_lookup_folded.json"),
            "exhaustive_cases": lookup_audit["summary"]["full_exhaustive_cases"],
            "exhaustive_pass": lookup_audit["summary"]["full_exhaustive_pass"],
            "multibase_samples": lookup_audit["summary"]["direct_semantic_samples"],
            "multibase_pass": lookup_audit["summary"]["direct_semantic_pass"],
            "pad0_total_non_clifford_2channel_folded": base_pad0["total_non_clifford_2channel_folded"],
            "pad0_total_non_clifford_3channel_folded_conservative": base_pad0["total_non_clifford_3channel_folded_conservative"],
            "pad0_improvement_fraction_vs_unfolded_reference_2channel": base_pad0["improvement_fraction_vs_unfolded_reference_2channel"],
            "pad0_improvement_fraction_vs_unfolded_reference_3channel_conservative": base_pad0["improvement_fraction_vs_unfolded_reference_3channel_conservative"],
        },
        "challenge_ladder": {
            "curve_count": len(ladder["curves"]),
            "max_field_bits": max(curve["field_bits"] for curve in ladder["curves"]),
            "audit_total": ladder_audit["summary"]["total"],
            "audit_pass": ladder_audit["summary"]["pass"],
            "sha256": ladder_audit["sha256"],
        },
        "literature_matrix": {
            "entry_count": len(literature_matrix["entries"]),
        },
        "physical_stack_reference": {
            "entry_count": len(physical_refs["entries"]),
        },
    }
    out_path = repo_root / "results" / "research_pass_summary.json"
    dump_json(out_path, result)
    return result
