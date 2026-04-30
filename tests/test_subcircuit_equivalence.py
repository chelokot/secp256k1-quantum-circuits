from __future__ import annotations

import json
from pathlib import Path

from support import ensure_compiler_project_build_summary, ensure_compiler_project_verification_summary


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_equivalence() -> dict:
    ensure_compiler_project_build_summary()
    ensure_compiler_project_verification_summary()
    path = REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'subcircuit_equivalence.json'
    return json.loads(path.read_text())


def test_subcircuit_equivalence_arithmetic_trace_passes() -> None:
    equivalence = _load_equivalence()
    arithmetic = equivalence['arithmetic_opcode_equivalence']
    for row in arithmetic['per_pc']:
        assert row['pass'] == row['total'], row['pc']
    for row in arithmetic['per_opcode']:
        assert row['pass'] == row['total'], row['opcode']
    assert arithmetic['cleanup_zero_after_clear']['pass'] == arithmetic['cleanup_zero_after_clear']['total']
    assert arithmetic['infinity_select_keeps_original_accumulator']['pass'] == arithmetic['infinity_select_keeps_original_accumulator']['total']
    assert arithmetic['bool_flag_value_partition']['flag_one_cases'] > 0
    assert arithmetic['bool_flag_value_partition']['flag_zero_cases'] > 0


def test_subcircuit_equivalence_leaf_interfaces_cover_edge_cases() -> None:
    equivalence = _load_equivalence()
    interfaces = equivalence['leaf_interface_equivalence']
    for name in ('lookup_fed_leaf', 'interface_borrowed_leaf'):
        summary = interfaces[name]['summary']
        assert summary['pass'] == summary['total'], name
        for category in ('random', 'doubling', 'inverse', 'accumulator_infinity', 'lookup_infinity'):
            assert summary['categories'][category]['total'] > 0, (name, category)
            assert summary['categories'][category]['pass'] == summary['categories'][category]['total'], (name, category)


def test_subcircuit_equivalence_reduced_width_witnesses_pass() -> None:
    equivalence = _load_equivalence()
    widths = equivalence['arithmetic_opcode_equivalence']['reduced_width_family_shape_witnesses']['widths']
    assert [row['field_bits'] for row in widths] == [3, 4, 5, 6]
    for row in widths:
        for opcode in ('field_add', 'field_sub', 'field_mul', 'mul_const', 'select_field_if_flag'):
            assert row[opcode]['pass'] == row[opcode]['total'], (row['field_bits'], opcode)


def test_subcircuit_equivalence_lookup_cleanup_and_composition_pass() -> None:
    equivalence = _load_equivalence()
    for family in equivalence['lookup_family_equivalence']['families']:
        assert family['direct_lookup_non_clifford'] == family['stage_reconstructed_non_clifford']
        assert family['workspace_qubits'] == family['stage_reconstructed_workspace_qubits']
        assert family['canonical_full_exhaustive_pass'] == family['canonical_full_exhaustive_total']
        assert family['multibase_edge_pass'] == family['multibase_edge_total']
    cleanup = equivalence['cleanup_window_equivalence']
    assert cleanup['trace_extract_pass'] == cleanup['trace_extract_total']
    assert cleanup['trace_clear_pass'] == cleanup['trace_clear_total']
    assert cleanup['trace_cleanup_zero_pass'] == cleanup['trace_cleanup_zero_total']
    assert cleanup['imported_cleanup_audit']['pass'] == cleanup['imported_cleanup_audit']['total']
    for family in equivalence['whole_oracle_composition_equivalence']['families']:
        assert family['generated_full_oracle_non_clifford'] == family['frontier_full_oracle_non_clifford'] == family['inventory_full_oracle_non_clifford']
        assert family['generated_total_logical_qubits'] == family['frontier_total_logical_qubits'] == family['inventory_total_logical_qubits']
