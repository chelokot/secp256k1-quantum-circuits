#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from common import SECP_B, SECP_G, SECP_N, SECP_P, affine_to_proj, deterministic_scalars, mul_fixed_window, precompute_window_tables, proj_to_affine, sha256_path  # noqa: E402
from leaf_schedule_optimizer import find_low_live_body_order, optimize_leaf_netlist  # noqa: E402
from verifier import exec_netlist, specialize_family_netlist  # noqa: E402


def test_schedule_optimizer_finds_the_eight_slot_body_order() -> None:
    leaf = json.loads((REPO_ROOT / 'artifacts' / 'circuits' / 'optimized_pointadd_secp256k1.json').read_text())
    order = find_low_live_body_order(leaf, 8)
    assert len(order) == 26
    assert set(order) == set(range(5, 31))


def test_schedule_optimizer_matches_checked_in_symbolic_and_specialized_leafs() -> None:
    slot_names = ['qx', 'qy', 'qz', 'lx', 'ly', 't0', 't1', 't2']
    family = json.loads((REPO_ROOT / 'artifacts' / 'circuits' / 'optimized_pointadd_family.json').read_text())
    optimized_family = optimize_leaf_netlist(family, slot_names)
    specialized_family = specialize_family_netlist(optimized_family, 21)
    secp_leaf = json.loads((REPO_ROOT / 'artifacts' / 'circuits' / 'optimized_pointadd_secp256k1.json').read_text())
    assert optimized_family['arithmetic_slots'] == slot_names
    assert specialized_family['arithmetic_slots'] == secp_leaf['arithmetic_slots']
    tables = precompute_window_tables(SECP_G, SECP_P, SECP_B, width=8, bits=256)
    seed = bytes.fromhex(sha256_path(REPO_ROOT / 'artifacts' / 'circuits' / 'optimized_pointadd_secp256k1.json'))
    scalars = deterministic_scalars(seed + b'leaf-schedule-optimizer-test', 24, SECP_N)
    for case_index in range(12):
        accumulator = mul_fixed_window(scalars[2 * case_index], tables, SECP_P, SECP_B, width=8, order=SECP_N)
        lookup = mul_fixed_window(scalars[2 * case_index + 1], tables, SECP_P, SECP_B, width=8, order=SECP_N)
        proj = affine_to_proj(accumulator, SECP_P)
        got = proj_to_affine(exec_netlist(secp_leaf['instructions'], SECP_P, proj, lookup, 1), SECP_P)
        optimized = proj_to_affine(exec_netlist(specialized_family['instructions'], SECP_P, proj, lookup, 1), SECP_P)
        assert optimized == got
