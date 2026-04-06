#!/usr/bin/env python3
"""Lookup-focused research helpers for the secp256k1 audit repository.

This module studies one concrete lookup-layer optimization that can be integrated
without touching the exact arithmetic leaf: **signed two's-complement table
folding**.

The public Google appendix models each windowed point addition as using lookups
addressed by a w-bit two's-complement register k and quotes a 3 * 2^w lookup
term for each merged point addition.  For secp256k1, negation is free at the
elliptic-curve level in the sense that

    [−d]U = (x([d]U), −y([d]U)).

So a signed 16-bit lookup table can be folded from 2^16 entries to 2^15 entries
per coordinate by splitting out the unique exceptional address 0x8000 = −2^15,
looking up only magnitudes 0..32767, and applying a post-lookup sign fix to the
Y coordinate when needed.

What is exact here:
- the signed-word decomposition itself,
- the algebraic contract mapping raw 16-bit words to folded magnitude/sign data,
- the resulting semantic point lookup, audited exhaustively over the full 16-bit
  domain for one relevant secp256k1 window base and sampled across additional
  secp256k1 bases,
- the machine-readable folded scaffold metadata.

What remains modeled:
- the translation from "half-sized table" into backend non-Clifford totals,
- any tiny preprocessing / sign-fix overhead below the repository's ISA layer,
- primitive-gate / physical-layout realization of the folded lookup machinery.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from common import (
    SECP_B,
    SECP_G,
    SECP_P,
    add_affine,
    deterministic_scalars,
    dump_json,
    hex_or_inf,
    mul_affine,
    neg_affine,
    sha256_bytes,
    sha256_path,
)

PointAffine = Optional[Tuple[int, int]]

WORD_BITS = 16
WORD_SIZE = 1 << WORD_BITS
HALF_SIZE = 1 << (WORD_BITS - 1)
FULL_EXHAUSTIVE_BASE_ID = "g_window_0"
EXTRA_BASE_SAMPLE_CASES = 4096
EDGE_KEYS = [0x0000, 0x0001, 0x0002, 0x7FFF, 0x8000, 0x8001, 0xFFFE, 0xFFFF]


def window_bases(base: PointAffine, p: int, b: int, width: int, windows: int) -> List[PointAffine]:
    arr: List[PointAffine] = [None] * windows
    arr[0] = base
    for i in range(1, windows):
        q = arr[i - 1]
        for _ in range(width):
            q = add_affine(q, q, p, b)
        arr[i] = q
    return arr


def signed_i16(word: int) -> int:
    w = word & 0xFFFF
    return w - 0x10000 if w & 0x8000 else w


def fold_signed_i16(word: int) -> Dict[str, Any]:
    w = word & 0xFFFF
    sval = signed_i16(w)
    is_min = w == 0x8000
    is_zero = w == 0
    is_negative = sval < 0
    if is_min:
        magnitude = None
    else:
        magnitude = abs(sval)
        if magnitude >= HALF_SIZE:
            raise ValueError(f"magnitude overflow for word {w:#06x}")
    return {
        "word": w,
        "signed_value": sval,
        "is_zero": is_zero,
        "is_negative": is_negative,
        "is_min": is_min,
        "folded_magnitude": magnitude,
        "meta_from_word": 1 if is_zero else 0,
        "requires_special_constant": is_min,
    }


def build_positive_table(base: PointAffine, p: int, b: int, max_magnitude: int = HALF_SIZE - 1) -> Tuple[List[PointAffine], PointAffine]:
    arr: List[PointAffine] = [None] * (max_magnitude + 1)
    arr[0] = None
    if max_magnitude >= 1:
        arr[1] = base
        for i in range(2, max_magnitude + 1):
            arr[i] = add_affine(arr[i - 1], base, p, b)
    special_pos = add_affine(arr[max_magnitude], base, p, b)
    return arr, special_pos


def folded_lookup_point_from_cache(word: int, cache: List[PointAffine], special_neg: PointAffine, p: int) -> PointAffine:
    fold = fold_signed_i16(word)
    if fold["is_min"]:
        return special_neg
    magnitude = int(fold["folded_magnitude"])
    point = cache[magnitude]
    if point is None:
        return None
    if fold["is_negative"]:
        return neg_affine(point, p)
    return point


def edge_and_sample_words(seed: bytes, sample_count: int) -> List[int]:
    words = EDGE_KEYS.copy()
    words.extend(deterministic_scalars(seed, sample_count, WORD_SIZE))
    deduped = []
    seen = set()
    for w in words:
        w &= 0xFFFF
        if w in seen:
            continue
        seen.add(w)
        deduped.append(w)
    return deduped


def build_lookup_base_set() -> List[Dict[str, Any]]:
    g_windows = window_bases(SECP_G, SECP_P, SECP_B, 16, 16)
    base_specs = [
        {"id": "g_window_0", "kind": "window_base", "window_index": 0, "point": g_windows[0], "mode": "full_exhaustive"},
        {"id": "g_window_5", "kind": "window_base", "window_index": 5, "point": g_windows[5], "mode": "sampled"},
        {"id": "g_window_10", "kind": "window_base", "window_index": 10, "point": g_windows[10], "mode": "sampled"},
        {"id": "g_window_15", "kind": "window_base", "window_index": 15, "point": g_windows[15], "mode": "sampled"},
    ]
    return base_specs


def build_lookup_folded_contract(repo_root: Path) -> Dict[str, Any]:
    contract = {
        "schema": "signed-folded-lookup-v1",
        "curve": "secp256k1",
        "window_size_bits": WORD_BITS,
        "input_representation": "16-bit two's complement",
        "motivation": "Exploit the exact secp256k1 identity [−d]U = (x([d]U), −y([d]U)) to halve the lookup-table domain per coordinate.",
        "folding": {
            "full_signed_domain_size": WORD_SIZE,
            "folded_positive_table_entries_per_coordinate": HALF_SIZE,
            "special_case_word_hex": "0x8000",
            "special_case_signed_value": -HALF_SIZE,
            "zero_word_hex": "0x0000",
            "meta_lookup_replacement": "derive infinity/no-op directly from the folded word instead of querying a separate metadata table",
            "negative_path": "lookup positive magnitude then negate Y",
        },
        "algorithm": [
            "Interpret the raw 16-bit window word as a signed two's-complement integer d.",
            "If the raw word is 0x8000, bypass the folded table and use the dedicated precomputed point [−2^15]U.",
            "Else let m = |d|, look up [m]U from a table indexed only by magnitudes 0..32767.",
            "If d < 0 and d != −2^15, negate the looked-up Y coordinate.",
            "If d = 0, return the point at infinity and skip the arithmetic leaf via the existing no-op path.",
        ],
        "table_shape": {
            "x_coordinate_table_entries": HALF_SIZE,
            "y_coordinate_table_entries": HALF_SIZE,
            "separate_metadata_table_needed": False,
            "per_window_special_constant_points": 1,
        },
        "notes": [
            "This contract changes only the lookup layer. The arithmetic leaf remains the same exact machine-readable secp256k1 netlist already archived in the repository.",
            "The backend-resource implication of halving the lookup domain is modeled separately in lookup_folded_projection.json.",
        ],
    }
    out_path = repo_root / "artifacts" / "out" / "lookup_signed_fold_contract.json"
    dump_json(out_path, contract)
    return contract


def build_lookup_folded_scaffold(repo_root: Path, contract: Dict[str, Any]) -> Dict[str, Any]:
    scaffold_path = repo_root / "artifacts" / "out" / "ecdlp_scaffold_optimized.json"
    scaffold = json.loads(scaffold_path.read_text())
    result = {
        "schema": "kickmix-hierarchical-scaffold-lookup-folded-v1",
        "base_scaffold_sha256": sha256_path(scaffold_path),
        "base_scaffold_name": scaffold_path.name,
        "lookup_contract_sha256": sha256_path(repo_root / "artifacts" / "out" / "lookup_signed_fold_contract.json"),
        "curve": scaffold["curve"],
        "window_size": scaffold["window_size"],
        "retained_window_additions": scaffold["retained_window_additions"],
        "lookup_encoding": {
            "address_representation": "16-bit two's complement",
            "folded_positive_domain_size": HALF_SIZE,
            "negative_symmetry_exploited": True,
            "special_case": {
                "word_hex": "0x8000",
                "action": "dedicated constant-point injection per window base",
            },
            "zero_case": {
                "word_hex": "0x0000",
                "action": "derive no-op / infinity directly from the folded word",
            },
        },
        "notes": [
            "This artifact does not rewrite the arithmetic leaf. It rewrites only the lookup contract consumed by that leaf.",
            "All retained-window metadata from the published scaffold remains unchanged.",
        ],
    }
    out_path = repo_root / "artifacts" / "out" / "ecdlp_scaffold_lookup_folded.json"
    dump_json(out_path, result)
    return result


def run_lookup_folding_audit(repo_root: Path) -> Dict[str, Any]:
    out_dir = repo_root / "artifacts" / "out"
    full_csv = out_dir / "lookup_signed_fold_exhaustive_g.csv"
    sample_csv = out_dir / "lookup_signed_fold_multibase_sampled.csv"

    bases = build_lookup_base_set()
    seed_material = sha256_bytes((sha256_path(repo_root / "artifacts" / "out" / "optimized_pointadd_secp256k1.json") + sha256_path(repo_root / "artifacts" / "out" / "ecdlp_scaffold_optimized.json")).encode())

    summary: Dict[str, Any] = {
        "word_domain_size": WORD_SIZE,
        "folded_table_entries_per_coordinate": HALF_SIZE,
        "full_exhaustive_base": FULL_EXHAUSTIVE_BASE_ID,
        "full_exhaustive_cases": 0,
        "full_exhaustive_pass": 0,
        "direct_semantic_samples": 0,
        "direct_semantic_pass": 0,
        "bases": {},
        "notes": [
            "The full secp256k1 exhaustive CSV covers every 16-bit raw window word for the canonical G-based window-0 table.",
            "Additional secp256k1 window bases are checked on deterministic edge-and-random samples using an independent direct scalar-multiplication path.",
            "This verifies the signed-word folding contract; it does not claim a primitive-gate realization of the folded lookup machinery.",
        ],
    }

    # Full exhaustive pass for the canonical base.
    full_base = next(spec for spec in bases if spec["id"] == FULL_EXHAUSTIVE_BASE_ID)
    cache, special_pos = build_positive_table(full_base["point"], SECP_P, SECP_B)
    special_neg = neg_affine(special_pos, SECP_P)
    with full_csv.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "word_hex", "signed_value", "is_zero", "is_negative", "is_min",
            "folded_magnitude", "expected_x", "expected_y", "folded_x", "folded_y", "status",
        ])
        for word in range(WORD_SIZE):
            fold = fold_signed_i16(word)
            signed_value = fold["signed_value"]
            if fold["is_min"]:
                expected = special_neg
            else:
                mag = int(fold["folded_magnitude"])
                expected = cache[mag]
                if expected is not None and signed_value < 0:
                    expected = neg_affine(expected, SECP_P)
            got = folded_lookup_point_from_cache(word, cache, special_neg, SECP_P)
            ok = got == expected
            summary["full_exhaustive_cases"] += 1
            summary["full_exhaustive_pass"] += int(ok)
            writer.writerow([
                f"0x{word:04x}",
                signed_value,
                int(fold["is_zero"]),
                int(fold["is_negative"]),
                int(fold["is_min"]),
                "SPECIAL" if fold["folded_magnitude"] is None else int(fold["folded_magnitude"]),
                *hex_or_inf(expected),
                *hex_or_inf(got),
                "PASS" if ok else "FAIL",
            ])
    summary["bases"][FULL_EXHAUSTIVE_BASE_ID] = {
        "mode": "full_exhaustive",
        "cases": WORD_SIZE,
        "pass": summary["full_exhaustive_pass"],
        "kind": full_base["kind"],
        "window_index": full_base.get("window_index"),
        "special_neg_point": {"x": special_neg[0], "y": special_neg[1]} if special_neg is not None else None,
    }

    # Direct semantic samples on multiple bases.
    with sample_csv.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "base_id", "kind", "window_index", "word_hex", "signed_value",
            "direct_x", "direct_y", "folded_x", "folded_y", "status",
        ])
        for spec in bases:
            cache, special_pos = build_positive_table(spec["point"], SECP_P, SECP_B)
            special_neg = neg_affine(special_pos, SECP_P)
            sample_seed = bytes.fromhex(seed_material) + spec["id"].encode()
            words = edge_and_sample_words(sample_seed, EXTRA_BASE_SAMPLE_CASES)
            local_total = 0
            local_pass = 0
            for word in words:
                direct = mul_affine(signed_i16(word), spec["point"], SECP_P, SECP_B)
                got = folded_lookup_point_from_cache(word, cache, special_neg, SECP_P)
                ok = direct == got
                summary["direct_semantic_samples"] += 1
                summary["direct_semantic_pass"] += int(ok)
                local_total += 1
                local_pass += int(ok)
                writer.writerow([
                    spec["id"],
                    spec["kind"],
                    spec.get("window_index", ""),
                    f"0x{word:04x}",
                    signed_i16(word),
                    *hex_or_inf(direct),
                    *hex_or_inf(got),
                    "PASS" if ok else "FAIL",
                ])
            if spec["id"] == FULL_EXHAUSTIVE_BASE_ID:
                summary["bases"][spec["id"]]["direct_sample_cases"] = local_total
                summary["bases"][spec["id"]]["direct_sample_pass"] = local_pass
            else:
                summary["bases"][spec["id"]] = {
                    "mode": "sampled_direct_semantics",
                    "cases": local_total,
                    "pass": local_pass,
                    "kind": spec["kind"],
                    "window_index": spec.get("window_index"),
                }

    result = {
        "schema": "lookup-signed-fold-audit-v1",
        "contract_sha256": sha256_path(out_dir / "lookup_signed_fold_contract.json"),
        "full_exhaustive_csv": full_csv.name,
        "full_exhaustive_sha256": sha256_path(full_csv),
        "multibase_sample_csv": sample_csv.name,
        "multibase_sample_sha256": sha256_path(sample_csv),
        "summary": summary,
    }
    dump_json(out_dir / "lookup_signed_fold_summary.json", result)
    return result


def build_lookup_folded_projection(repo_root: Path, small_pad_values: Iterable[int] = (0, 256, 512, 1024, 2048, 4096)) -> Dict[str, Any]:
    projection_path = repo_root / "artifacts" / "out" / "resource_projection.json"
    projection = json.loads(projection_path.read_text())
    windows = int(projection["optimized_ecdlp_projection"]["retained_window_additions"])
    per_leaf_arith = int(projection["optimized_leaf_projection"]["modeled_non_clifford_excluding_lookup"])
    lookup2 = int(projection["optimized_ecdlp_projection"]["lookup_model_2channel"]["per_window_lookup_cost"])
    lookup3 = int(projection["optimized_ecdlp_projection"]["lookup_model_3channel"]["per_window_lookup_cost"])
    google_low_q = projection["public_google_baseline"]["low_qubit"]["non_clifford"]
    google_low_g = projection["public_google_baseline"]["low_gate"]["non_clifford"]

    folded_lookup2 = lookup2 // 2
    folded_lookup3_conservative = lookup3 // 2
    folded_lookup3_meta_elided = lookup2 // 2

    rows = []
    for pad in small_pad_values:
        total2 = windows * (per_leaf_arith + folded_lookup2 + pad)
        total3c = windows * (per_leaf_arith + folded_lookup3_conservative + pad)
        total3m = windows * (per_leaf_arith + folded_lookup3_meta_elided + pad)
        rows.append({
            "per_window_small_overhead_pad": pad,
            "total_non_clifford_2channel_folded": total2,
            "total_non_clifford_3channel_folded_conservative": total3c,
            "total_non_clifford_3channel_folded_meta_elided": total3m,
            "improvement_fraction_vs_current_2channel": 1.0 - total2 / projection["optimized_ecdlp_projection"]["lookup_model_2channel"]["total_non_clifford"],
            "improvement_fraction_vs_current_3channel_conservative": 1.0 - total3c / projection["optimized_ecdlp_projection"]["lookup_model_3channel"]["total_non_clifford"],
            "gain_vs_google_low_qubit_2channel": google_low_q / total2,
            "gain_vs_google_low_gate_2channel": google_low_g / total2,
        })

    result = {
        "schema": "lookup-folded-projection-v1",
        "base_projection_sha256": sha256_path(projection_path),
        "assumptions": [
            "The exact arithmetic leaf cost is unchanged from the repository's published optimized leaf.",
            "Each signed 16-bit coordinate table is folded from 65536 entries to 32768 entries plus one special constant for 0x8000.",
            "The separate metadata lookup is derived from the raw word instead of looked up from a table.",
            "Small classical-preprocessing / sign-fix overhead below the ISA layer is not exactly lowered here, so a per-window additive pad sweep is included.",
        ],
        "current_per_window": {
            "arithmetic_non_clifford": per_leaf_arith,
            "lookup_2channel": lookup2,
            "lookup_3channel": lookup3,
        },
        "folded_per_window": {
            "lookup_2channel": folded_lookup2,
            "lookup_3channel_conservative": folded_lookup3_conservative,
            "lookup_3channel_meta_elided": folded_lookup3_meta_elided,
        },
        "base_case_pad0": rows[0],
        "pad_sweep": rows,
        "logical_qubit_comment": "The current repository does not primitive-lower the 16-bit sign/magnitude preprocessing. A small ancilla increase is plausible but expected to be negligible against the ~880 logical-qubit headline.",
        "notes": [
            "The strongest high-confidence consequence of the folded lookup contract is a 2x reduction in the per-coordinate table domain, not a change to the arithmetic leaf itself.",
            "Under the repository's existing lookup-counting model this translates to a modest but real total non-Clifford reduction, not another dramatic 2x overall speedup.",
        ],
    }
    out_path = repo_root / "artifacts" / "out" / "lookup_folded_projection.json"
    dump_json(out_path, result)
    return result
