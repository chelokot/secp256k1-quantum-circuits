from __future__ import annotations

import json
import sys
from pathlib import Path

from support import ensure_compiler_project_build_summary, ensure_compiler_project_verification_summary

REPO_ROOT = Path(__file__).resolve().parents[1]
COMPILER_SRC = REPO_ROOT / 'compiler_verification_project' / 'src'
if str(COMPILER_SRC) not in sys.path:
    sys.path.insert(0, str(COMPILER_SRC))

from lookup_lowering import lowered_lookup_semantic_summary, materialize_lookup_primitive_operations  # noqa: E402


def _load_lookup_lowerings() -> dict:
    ensure_compiler_project_build_summary()
    ensure_compiler_project_verification_summary()
    path = REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'lookup_lowerings.json'
    return json.loads(path.read_text())


def test_lookup_lowering_stage_inventory_reconstructs_family_totals() -> None:
    lookup_lowerings = _load_lookup_lowerings()
    for family in lookup_lowerings['families']:
        reconstructed_family_counts = {'ccx': 0, 'cx': 0, 'x': 0, 'measurement': 0}
        assert family['direct_lookup_non_clifford'] == sum(stage['non_clifford_total'] for stage in family['stages'])
        assert family['per_leaf_lookup_non_clifford'] == family['direct_lookup_non_clifford']
        assert family['extra_lookup_workspace_qubits'] == max(stage['total_workspace_qubits'] for stage in family['stages'])
        for stage in family['stages']:
            reconstructed_stage_counts = {'ccx': 0, 'cx': 0, 'x': 0, 'measurement': 0}
            for block in stage['blocks']:
                reconstructed_block_counts = {'ccx': 0, 'cx': 0, 'x': 0, 'measurement': 0}
                for operation in materialize_lookup_primitive_operations(block['primitive_operation_generator']):
                    reconstructed_block_counts[operation[0]] += 1
                assert reconstructed_block_counts == block['primitive_counts_total']
                for key in reconstructed_stage_counts:
                    reconstructed_stage_counts[key] += reconstructed_block_counts[key]
            assert reconstructed_stage_counts == stage['primitive_counts_total']
            for key in reconstructed_family_counts:
                reconstructed_family_counts[key] += reconstructed_stage_counts[key]
        assert reconstructed_family_counts == family['primitive_counts_total']


def test_lookup_lowering_semantics_match_contract() -> None:
    summary = lowered_lookup_semantic_summary()
    for family in summary['families']:
        assert family['canonical_full_exhaustive_pass'] == family['canonical_full_exhaustive_total']
        assert family['multibase_edge_pass'] == family['multibase_edge_total']


def test_banked_lookup_family_sits_between_linear_and_full_unary_extremes() -> None:
    lookup_lowerings = _load_lookup_lowerings()
    family_lookup = {family['name']: family for family in lookup_lowerings['families']}
    linear_family = family_lookup['folded_linear_scan_tmpand_v1']
    banked_family = family_lookup['folded_banked_unary_qrom_measured_uncompute_v1']
    hierarchical_family = family_lookup['folded_hierarchical_banked_unary_qrom_measured_uncompute_v1']
    bitwise_family = family_lookup['folded_bitwise_banked_unary_qrom_measured_uncompute_v1']
    unary_family = family_lookup['folded_unary_qrom_measured_uncompute_v1']
    assert linear_family['extra_lookup_workspace_qubits'] < banked_family['extra_lookup_workspace_qubits'] < unary_family['extra_lookup_workspace_qubits']
    assert banked_family['per_leaf_lookup_non_clifford'] < linear_family['per_leaf_lookup_non_clifford']
    assert linear_family['extra_lookup_workspace_qubits'] < hierarchical_family['extra_lookup_workspace_qubits'] < banked_family['extra_lookup_workspace_qubits']
    assert hierarchical_family['per_leaf_lookup_non_clifford'] < banked_family['per_leaf_lookup_non_clifford']
    assert linear_family['extra_lookup_workspace_qubits'] < bitwise_family['extra_lookup_workspace_qubits'] < hierarchical_family['extra_lookup_workspace_qubits']
    assert bitwise_family['per_leaf_lookup_non_clifford'] < hierarchical_family['per_leaf_lookup_non_clifford']
