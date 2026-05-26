from __future__ import annotations

import json
import sys
from pathlib import Path

from support import ensure_compiler_project_build_summary


REPO_ROOT = Path(__file__).resolve().parents[1]
COMPILER_SRC = REPO_ROOT / 'compiler_verification_project' / 'src'
if str(COMPILER_SRC) not in sys.path:
    sys.path.insert(0, str(COMPILER_SRC))

from engine_completion_audit import ENGINE_COMPLETION_AUDIT_SCHEMA, build_engine_completion_audit  # noqa: E402
from public_engine_contract import (  # noqa: E402
    CANONICAL_MATERIALIZED_FLAT_NETLIST,
    PUBLIC_ENGINE_CANONICAL_TOTALS_SOURCE,
    PUBLIC_TOTALS_DERIVE_FROM_CANONICAL_CHECK,
)


def _load(name: str) -> dict:
    ensure_compiler_project_build_summary()
    return json.loads((REPO_ROOT / 'compiler_verification_project' / 'artifacts' / name).read_text())


def _build_audit(
    *,
    public_engine: dict | None = None,
    public_candidate: dict | None = None,
    arithmetic_operand_replay: dict | None = None,
    arithmetic_ir: dict | None = None,
    qroam_primitive: dict | None = None,
    qroam_table_cnot: dict | None = None,
    lookup_lowerings: dict | None = None,
    zkp_input: dict | None = None,
) -> dict:
    return build_engine_completion_audit(
        public_engine_manifest=public_engine or _load('public_engine_manifest.json'),
        public_candidate_materialized_circuit_manifest=public_candidate or _load('public_candidate_materialized_circuit_manifest.json'),
        arithmetic_operand_replay_audit=arithmetic_operand_replay or _load('arithmetic_operand_replay_audit.json'),
        reusable_chunk_lowering=_load('reusable_chunk_lowering.json'),
        arithmetic_operation_ir=arithmetic_ir or _load('arithmetic_operation_ir.json'),
        lookup_lowerings=lookup_lowerings or _load('lookup_lowerings.json'),
        qroam_primitive_certificate=qroam_primitive or _load('qroam_primitive_certificate.json'),
        qroam_table_cnot_materialization=qroam_table_cnot or _load('qroam_table_cnot_materialization.json'),
        phase_shell_lowerings=_load('phase_shell_lowerings.json'),
        release_corpus_preflight=_load('release_corpus_preflight.json'),
        streamed_lookup_tail_leaf_equivalence=_load('streamed_lookup_tail_leaf_equivalence.json'),
        modular_arithmetic_certificate=_load('modular_arithmetic_certificate.json'),
        modular_execution_trace=_load('modular_execution_trace.json'),
        scheduled_modular_primitive_netlist=_load('scheduled_modular_primitive_netlist.json'),
        tail_macro_engine=_load('tail_macro_engine.json'),
        tail_macro_liveness=_load('tail_macro_liveness.json'),
        tail_macro_reversibility=_load('tail_macro_reversibility.json'),
        tail_macro_schedule_search=_load('tail_macro_schedule_search.json'),
        compiler_parameters=_load('compiler_parameters.json'),
        zkp_attestation_input=zkp_input or _load('zkp_attestation_reusable_chunk_candidate/zkp_attestation_input.json'),
    )


def test_engine_completion_audit_reconstructs_checked_artifact() -> None:
    expected = _load('engine_completion_audit.json')
    observed = _build_audit()
    materialized = _load('public_candidate_materialized_circuit_manifest.json')[CANONICAL_MATERIALIZED_FLAT_NETLIST]
    assert observed == expected
    assert expected['schema'] == ENGINE_COMPLETION_AUDIT_SCHEMA
    assert expected['pass'] is True
    assert expected['clifford_complete_goal_achieved'] is False
    assert expected['public_totals']['source'] == PUBLIC_ENGINE_CANONICAL_TOTALS_SOURCE
    assert expected['public_totals']['non_clifford'] == materialized['non_clifford_count']
    assert expected['public_totals']['logical_qubits'] == materialized['peak_live_qubits']
    assert expected['public_totals']['operation_count'] == materialized['operation_count']
    assert len(expected['remaining_macro_boundaries']) > 0
    remaining = {row['name']: row for row in expected['remaining_macro_boundaries']}
    assert set(remaining) == {'modular_arithmetic_clifford_expansion'}
    assert 'single_engine_zkp_input_derivation' not in remaining
    covered = {row['name']: row for row in expected['covered_boundaries']}
    assert covered['arithmetic_operand_replay']['status'] == 'exact_source_operands_replayed_to_counted_flat_netlist_wires'
    assert covered['qroam_bit_level_netlist_expansion']['status'] == 'indexed_table_cnot_rows_in_canonical_physical_flat_stream_with_iterator_export'
    assert covered['canonical_engine_zkp_input_authority']['status'] == 'public_engine_manifest_and_scheduled_physical_boundary_bound_by_candidate_input_and_guest'
    assert covered['tail_reversible_field_schedule_contract']['status'] == 'seven_slot_field_operation_schedule_bound_to_reversible_contract'
    assert remaining['modular_arithmetic_clifford_expansion']['evidence_metrics']['source_bound_run_length_rows'] == expected['source_binding_summary']['rows_by_source_kind']['arithmetic_operation_ir']
    assert remaining['modular_arithmetic_clifford_expansion']['status'] == 'scheduled_modular_primitive_stream_bound_to_zkp_physical_boundary_not_full_clifford_decomposition'
    assert remaining['modular_arithmetic_clifford_expansion']['evidence_metrics']['local_modular_primitive_stream_pass'] is True
    assert len(remaining['modular_arithmetic_clifford_expansion']['evidence_metrics']['local_modular_primitive_stream_sha256']) == 64
    assert remaining['modular_arithmetic_clifford_expansion']['evidence_metrics']['modular_engine_integration_pass'] is True
    assert remaining['modular_arithmetic_clifford_expansion']['evidence_metrics']['modular_execution_trace_pass'] is True
    assert remaining['modular_arithmetic_clifford_expansion']['evidence_metrics']['scheduled_modular_primitive_netlist_pass'] is True
    assert remaining['modular_arithmetic_clifford_expansion']['evidence_metrics']['scheduled_modular_global_splice_pass'] is True
    assert expected['checks']['arithmetic_rows_are_operation_ir_bound'] is True
    assert expected['checks']['zkp_input_binds_canonical_engine_without_compact_strict_claim'] is True
    qroam_table_cnot = _load('qroam_table_cnot_materialization.json')
    physical = _load('public_candidate_materialized_circuit_manifest.json')['canonical_physical_flat_netlist']
    assert physical['gate_totals']['cx'] == qroam_table_cnot['totals']['full_oracle_emitted_clifford_cx']
    assert physical['pass'] is True
    assert all(expected['checks'].values())


def test_engine_completion_audit_rejects_public_total_drift() -> None:
    public_engine = _load('public_engine_manifest.json')
    public_engine['public_totals']['non_clifford'] -= 1
    observed = _build_audit(public_engine=public_engine)
    assert observed['checks'][PUBLIC_TOTALS_DERIVE_FROM_CANONICAL_CHECK] is False
    assert observed['pass'] is False


def test_engine_completion_audit_rejects_forged_source_binding() -> None:
    public_candidate = _load('public_candidate_materialized_circuit_manifest.json')
    public_candidate['operand_source_binding']['rows_by_source_kind']['lookup_lowering_block'] = 0
    observed = _build_audit(public_candidate=public_candidate)
    assert observed['checks']['source_binding_covers_every_run_length_row'] is False
    assert observed['pass'] is False


def test_engine_completion_audit_rejects_forged_qroam_cost() -> None:
    qroam_primitive = _load('qroam_primitive_certificate.json')
    qroam_primitive['qroamclean_cost_model']['per_stream_non_clifford'] -= 1
    observed = _build_audit(qroam_primitive=qroam_primitive)
    assert observed['checks']['qroam_rows_bind_standard_qroam_primitive_costs'] is False
    assert observed['pass'] is False


def test_engine_completion_audit_rejects_forged_qroam_row_index_contract() -> None:
    qroam_table_cnot = _load('qroam_table_cnot_materialization.json')
    qroam_table_cnot['checks']['row_decoder_samples_are_exact_table_cnot_rows'] = False
    observed = _build_audit(qroam_table_cnot=qroam_table_cnot)
    assert observed['checks']['qroam_table_cnot_extension_binds_counted_liveness'] is False
    assert observed['pass'] is False


def test_engine_completion_audit_rejects_forged_zkp_engine_claim_summary() -> None:
    zkp_input = _load('zkp_attestation_reusable_chunk_candidate/zkp_attestation_input.json')
    zkp_input['claim_summary']['expected_total_logical_qubits'] -= 1
    observed = _build_audit(zkp_input=zkp_input)
    assert observed['checks']['zkp_input_binds_canonical_engine_without_compact_strict_claim'] is False
    assert observed['pass'] is False


def test_engine_completion_audit_rejects_extra_primary_strict_claim_authority() -> None:
    zkp_input = _load('zkp_attestation_reusable_chunk_candidate/zkp_attestation_input.json')
    zkp_input['primary_strict_claim_sha256'] = '00' * 32
    observed = _build_audit(zkp_input=zkp_input)
    assert observed['checks']['zkp_input_binds_canonical_engine_without_compact_strict_claim'] is False
    assert observed['pass'] is False


def test_engine_completion_audit_rejects_lookup_block_stream_drift() -> None:
    lookup_lowerings = _load('lookup_lowerings.json')
    block = lookup_lowerings['families'][0]['stages'][0]['blocks'][0]
    block['primitive_operation_stream']['operation_count'] += 1
    observed = _build_audit(lookup_lowerings=lookup_lowerings)
    assert observed['checks']['lookup_rows_are_per_block_source_bound'] is False
    assert observed['pass'] is False


def test_engine_completion_audit_rejects_arithmetic_operand_replay_drift() -> None:
    arithmetic_operand_replay = _load('arithmetic_operand_replay_audit.json')
    arithmetic_operand_replay['rows_with_failures'] = 1
    arithmetic_operand_replay['pass'] = False
    observed = _build_audit(arithmetic_operand_replay=arithmetic_operand_replay)
    assert observed['checks']['arithmetic_rows_are_operation_ir_bound'] is False
    assert observed['pass'] is False


def test_engine_completion_audit_rejects_false_completion_claim() -> None:
    audit = _load('engine_completion_audit.json')
    assert audit['clifford_complete_goal_achieved'] is False
    assert audit['checks']['public_claim_not_marked_full_clifford_complete_until_macro_boundaries_flattened'] is True
