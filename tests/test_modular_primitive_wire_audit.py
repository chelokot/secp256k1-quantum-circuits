from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
COMPILER_SRC = REPO_ROOT / 'compiler_verification_project' / 'src'
ROOT_SRC = REPO_ROOT / 'src'
if str(COMPILER_SRC) not in sys.path:
    sys.path.insert(0, str(COMPILER_SRC))
if str(ROOT_SRC) not in sys.path:
    sys.path.insert(0, str(ROOT_SRC))

from modular_primitive_wire_audit import MODULAR_PRIMITIVE_WIRE_AUDIT_SCHEMA, build_modular_primitive_wire_audit  # noqa: E402


ARTIFACT_DIR = REPO_ROOT / 'compiler_verification_project' / 'artifacts'


def _load(name: str) -> dict:
    return json.loads((ARTIFACT_DIR / name).read_text())


def _build() -> dict:
    return build_modular_primitive_wire_audit(
        modular_execution_trace=_load('modular_execution_trace.json'),
        modular_arithmetic_certificate=_load('modular_arithmetic_certificate.json'),
        arithmetic_lowerings=_load('arithmetic_lowerings.json'),
        reusable_chunk_lowering=_load('reusable_chunk_lowering.json'),
        scheduled_modular_primitive_netlist=_load('scheduled_modular_primitive_netlist.json'),
    )


def test_modular_primitive_wire_audit_reconstructs_checked_artifact() -> None:
    assert _load('modular_primitive_wire_audit.json') == _build()


def test_modular_primitive_wire_audit_names_current_scratch_gap() -> None:
    audit = _load('modular_primitive_wire_audit.json')
    scheduled = _load('scheduled_modular_primitive_netlist.json')
    trace = _load('modular_execution_trace.json')
    assert audit['schema'] == MODULAR_PRIMITIVE_WIRE_AUDIT_SCHEMA
    assert audit['operation_count'] == scheduled['operation_count']
    assert audit['gate_counts'] == scheduled['primitive_counts_total']
    assert all(
        '.product_' not in str(suboperation['target'])
        for row in trace['trace_rows']
        for suboperation in row['suboperations']
    )
    assert audit['checks']['raw_field_operand_liveness_is_not_claimed_complete'] is True
    assert audit['checks']['field_operand_wires_are_live_or_classified'] is True
    assert audit['checks']['no_blocking_field_liveness_gaps'] is True
    assert audit['checks']['lookup_virtual_field_operands_are_classified'] is True
    assert audit['checks']['no_unresolved_virtual_field_operands'] is True
    assert audit['checks']['no_unclassified_non_lookup_operand_wires'] is True
    assert audit['checks']['synthetic_scratch_wires_are_single_use_ccx_targets'] is True
    assert audit['checks']['synthetic_scratch_wires_have_cleanup_or_counted_capacity'] is False
    assert audit['checks']['no_synthetic_arithmetic_scratch_wires_without_owner_capacity'] is False
    assert audit['pass'] is False
    assert audit['field_wire_missing_liveness_count'] > 0
    assert audit['field_wire_classified_missing_liveness_count'] == audit['field_wire_missing_liveness_count']
    assert audit['field_wire_blocking_missing_liveness_count'] == 0
    assert audit['overwritten_source_field_observation_count'] > 0
    assert audit['lookup_virtual_field_observation_count'] > 0
    assert audit['unresolved_virtual_field_observation_count'] == 0
    assert audit['arithmetic_scratch_wire_observation_count'] > 0
    assert audit['arithmetic_scratch_unique_wire_count'] > 0
    assert audit['arithmetic_scratch_single_use_wire_count'] == audit['arithmetic_scratch_wire_observation_count']
    assert audit['arithmetic_scratch_reused_wire_count'] == 0
    assert audit['arithmetic_scratch_ccx_target_observation_count'] == audit['arithmetic_scratch_wire_observation_count']
    assert audit['arithmetic_scratch_non_ccx_target_observation_count'] == 0
    assert audit['arithmetic_scratch_cleanup_observation_count'] == 0
    assert audit['arithmetic_scratch_abandoned_garbage_count'] == audit['arithmetic_scratch_wire_observation_count']
    assert audit['arithmetic_scratch_gate_counts'] == {'ccx': audit['arithmetic_scratch_wire_observation_count']}
    assert set(audit['lookup_virtual_field_names']) == {'lookup_x', 'lookup_y', 'lookup_x_plus_y'}
    assert {'C', 'X', 'Y'}.issubset(set(audit['overwritten_source_field_names']))
    assert audit['unresolved_virtual_field_names'] == {}
    assert audit['unresolved_virtual_field_roles'] == {}
    assert audit['unresolved_virtual_field_names_by_role'] == {}
    assert audit['sample_missing_liveness']
    assert audit['sample_lookup_virtual']
    assert audit['sample_unresolved_virtual_field'] == []
    assert audit['sample_synthetic_scratch']
