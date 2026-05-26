from __future__ import annotations

import json
import sys
from pathlib import Path

from support import ensure_compiler_project_build_summary


REPO_ROOT = Path(__file__).resolve().parents[1]
COMPILER_SRC = REPO_ROOT / 'compiler_verification_project' / 'src'
if str(COMPILER_SRC) not in sys.path:
    sys.path.insert(0, str(COMPILER_SRC))

from public_engine_manifest import PUBLIC_ENGINE_MANIFEST_SCHEMA, build_public_engine_manifest  # noqa: E402
from public_engine_contract import CANONICAL_MATERIALIZED_FLAT_NETLIST, PUBLIC_ENGINE_CANONICAL_TOTALS_SOURCE, PUBLIC_TOTALS_DERIVE_FROM_CANONICAL_CHECK, PUBLIC_TOTALS_MATCH_CANONICAL_ENGINE_CHECK, STRICT_REPLAYED_TAIL_MATERIALIZED_FLAT_NETLIST  # noqa: E402
from proof_corpus_profiles import GOOGLE_COMPARABLE_CASE_COUNT  # noqa: E402


def _load(name: str) -> dict:
    ensure_compiler_project_build_summary()
    return json.loads((REPO_ROOT / 'compiler_verification_project' / 'artifacts' / name).read_text())


def _build_manifest(
    *,
    reusable: dict | None = None,
    tail_candidate: dict | None = None,
    streamed_equivalence: dict | None = None,
    release_preflight: dict | None = None,
    compiler_parameters: dict | None = None,
    arithmetic_operation_ir: dict | None = None,
    qroam_primitive: dict | None = None,
    qroam_table_cnot: dict | None = None,
    phase_shell: dict | None = None,
    public_candidate_materialized: dict | None = None,
    modular_execution_trace: dict | None = None,
    scheduled_modular_primitive_netlist: dict | None = None,
) -> dict:
    resolved_compiler_parameters = compiler_parameters or _load('compiler_parameters.json')
    return build_public_engine_manifest(
        reusable_chunk_lowering=reusable or _load('reusable_chunk_lowering.json'),
        reusable_chunk_tail_candidate=tail_candidate or _load('reusable_chunk_tail_candidate.json'),
        streamed_lookup_tail_leaf_equivalence=streamed_equivalence or _load('streamed_lookup_tail_leaf_equivalence.json'),
        release_corpus_preflight=release_preflight or _load('release_corpus_preflight.json'),
        compiler_parameters=resolved_compiler_parameters,
        arithmetic_operation_ir=arithmetic_operation_ir or _load('arithmetic_operation_ir.json'),
        qroam_primitive_certificate=qroam_primitive or _load('qroam_primitive_certificate.json'),
        qroam_table_cnot_materialization=qroam_table_cnot or _load('qroam_table_cnot_materialization.json'),
        phase_shell_lowerings=phase_shell or _load('phase_shell_lowerings.json'),
        public_candidate_materialized_circuit_manifest=public_candidate_materialized or _load('public_candidate_materialized_circuit_manifest.json'),
        modular_execution_trace=modular_execution_trace or _load('modular_execution_trace.json'),
        scheduled_modular_primitive_netlist=scheduled_modular_primitive_netlist or _load('scheduled_modular_primitive_netlist.json'),
        selected_family_name=resolved_compiler_parameters['public_headline_policy']['selected_public_family_name'],
    )


def test_public_engine_manifest_reconstructs_checked_artifact() -> None:
    reusable = _load('reusable_chunk_lowering.json')
    expected = _load('public_engine_manifest.json')
    observed = _build_manifest(reusable=reusable)
    assert observed == expected
    assert expected['schema'] == PUBLIC_ENGINE_MANIFEST_SCHEMA
    assert expected['pass'] is True
    assert expected['public_totals']['source'] == PUBLIC_ENGINE_CANONICAL_TOTALS_SOURCE
    assert expected['public_totals']['non_clifford'] == reusable['executable_resource_engine']['public_totals']['non_clifford']
    assert expected['public_totals']['logical_qubits'] == _load('strict_replayed_tail_headline.json')['selected_result']['logical_qubits']
    assert expected['legacy_wrapper_totals']['logical_qubits'] == reusable['executable_resource_engine']['public_totals']['logical_qubits']
    strict_owner_rows = expected['strict_public_owner_capacity_stream']['rows']
    strict_owner_qubits = {row['owner_id']: row['logical_qubits'] for row in strict_owner_rows}
    assert sum(strict_owner_qubits.values()) == expected['public_totals']['logical_qubits']
    assert strict_owner_qubits['lookup_workspace'] == 173
    assert strict_owner_qubits['control_slot_register_file'] == 2
    assert len([owner_id for owner_id in strict_owner_qubits if owner_id.startswith('tail_reordered_slot_')]) == 7
    assert expected['fast_no_zkp_contract']['prover_required'] is False
    assert expected['semantic_boundary_evidence']['release_corpus_preflight']['case_count'] == GOOGLE_COMPARABLE_CASE_COUNT
    assert expected['semantic_boundary_evidence']['compiler_parameters']['selected_public_family_name'] == expected['selected_family_name']
    assert set(expected['semantic_boundary_evidence']['required_categories']).issubset(
        expected['semantic_boundary_evidence']['release_corpus_preflight']['category_counts']
    )
    assert expected['primitive_operation_evidence']['qroam_primitive_certificate']['whole_oracle_non_clifford'] == reusable['non_clifford_derivation']['qroam_chunk_non_clifford']
    qroam_table_cnot = _load('qroam_table_cnot_materialization.json')
    arithmetic_ir = _load('arithmetic_operation_ir.json')
    assert expected['source_digests']['qroam_table_cnot_materialization_sha256'] == expected['primitive_operation_evidence']['qroam_table_cnot_materialization']['sha256']
    assert expected['primitive_operation_evidence']['qroam_table_cnot_materialization']['full_oracle_emitted_clifford_cx'] == qroam_table_cnot['totals']['full_oracle_emitted_clifford_cx']
    assert expected['primitive_operation_evidence']['qroam_table_cnot_materialization']['segment_count'] == reusable['stream_plan']['whole_oracle_chunk_streams'] * expected['primitive_operation_evidence']['qroam_primitive_certificate']['segment_count']
    assert expected['primitive_operation_evidence']['phase_shell']['phase_register_bits'] == expected['primitive_operation_evidence']['phase_shell']['hadamard_count']
    assert expected['primitive_operation_evidence']['public_candidate_materialized_circuit_manifest']['non_clifford'] == reusable['non_clifford_derivation']['candidate_total_non_clifford']
    assert expected['primitive_operation_evidence']['public_candidate_materialized_circuit_manifest']['peak_live_qubits'] == expected['public_totals']['logical_qubits']
    assert expected['primitive_operation_evidence']['public_candidate_materialized_circuit_manifest']['flat_operation_count'] > expected['primitive_operation_evidence']['public_candidate_materialized_circuit_manifest']['run_length_row_count']
    assert expected['primitive_operation_evidence']['public_candidate_materialized_circuit_manifest']['flat_segment_count'] > 1
    assert len(expected['primitive_operation_evidence']['public_candidate_materialized_circuit_manifest']['flat_segment_merkle_root_sha256']) == 64
    modular_trace = expected['primitive_operation_evidence']['public_candidate_materialized_circuit_manifest']['modular_execution_trace']
    assert expected['checks']['modular_execution_trace_is_bound'] is True
    assert modular_trace['pass'] is True
    assert modular_trace['reconstructed_non_clifford'] == expected['primitive_operation_evidence']['arithmetic_operation_ir']['tail_kernel_non_clifford_per_instance']
    assert modular_trace['modular_opcode_histogram']['field_mul'] == 11
    scheduled_modular_netlist = expected['primitive_operation_evidence']['public_candidate_materialized_circuit_manifest']['scheduled_modular_primitive_netlist']
    assert expected['checks']['scheduled_modular_primitive_netlist_is_bound'] is True
    assert scheduled_modular_netlist['pass'] is True
    assert scheduled_modular_netlist['non_clifford_count'] == 1192378
    assert scheduled_modular_netlist['primitive_counts_total']['measurement'] == 77756
    scheduled_splice = expected['primitive_operation_evidence']['public_candidate_materialized_circuit_manifest']['scheduled_modular_global_splice']
    assert expected['checks']['scheduled_modular_primitive_netlist_splices_global_public_rows'] is True
    assert scheduled_splice['pass'] is True
    assert scheduled_splice['leaf_call_count'] == 31
    assert scheduled_splice['scheduled_non_clifford_count'] == 36963718
    exact_arithmetic = expected['primitive_operation_evidence']['arithmetic_operation_ir']['selected_leaf_exact_operation_stream']
    assert exact_arithmetic['pass'] is True
    assert exact_arithmetic['non_clifford_count'] == arithmetic_ir['leaf_arithmetic_summary']['non_clifford_total']
    assert len(exact_arithmetic['segment_merkle_root_sha256']) == 64
    qroam_table_extension = expected['primitive_operation_evidence']['public_candidate_materialized_circuit_manifest']['qroam_table_cnot_flat_extension']
    assert qroam_table_extension['pass'] is True
    assert qroam_table_extension['operation_count'] == qroam_table_cnot['totals']['full_oracle_emitted_clifford_cx']
    assert qroam_table_extension['non_clifford_count'] == 0
    materialized_flat = expected['primitive_operation_evidence']['public_candidate_materialized_circuit_manifest']['materialized_flat_netlist']
    assert materialized_flat['exact_operation_stream_materialized'] is True
    assert materialized_flat['operation_count'] == expected['primitive_operation_evidence']['public_candidate_materialized_circuit_manifest']['flat_operation_count']
    assert materialized_flat['non_clifford_count'] == reusable['non_clifford_derivation']['candidate_total_non_clifford']
    assert materialized_flat['peak_live_qubits'] == reusable['qubit_derivation']['candidate_total_logical_qubits']
    assert len(materialized_flat['operation_stream_sha256']) == 64
    assert len(materialized_flat['segment_merkle_root_sha256']) == 64
    strict_flat = expected['primitive_operation_evidence']['public_candidate_materialized_circuit_manifest'][STRICT_REPLAYED_TAIL_MATERIALIZED_FLAT_NETLIST]
    canonical_flat = expected['primitive_operation_evidence']['public_candidate_materialized_circuit_manifest'][CANONICAL_MATERIALIZED_FLAT_NETLIST]
    assert strict_flat['exact_operation_stream_materialized'] is True
    assert strict_flat['operation_count'] == materialized_flat['operation_count']
    assert strict_flat['non_clifford_count'] == expected['public_totals']['non_clifford']
    assert strict_flat['peak_live_qubits'] == expected['public_totals']['logical_qubits']
    assert len(strict_flat['operation_stream_sha256']) == 64
    assert len(strict_flat['segment_merkle_root_sha256']) == 64
    assert canonical_flat['operation_stream_sha256'] == strict_flat['operation_stream_sha256']
    assert canonical_flat['peak_live_qubits'] == expected['public_totals']['logical_qubits']
    physical_flat = expected['primitive_operation_evidence']['public_candidate_materialized_circuit_manifest']['canonical_physical_flat_netlist']
    assert physical_flat['schema'] == 'compiler-project-canonical-physical-flat-netlist-v1'
    assert physical_flat['exact_virtual_operation_stream_materialized'] is True
    assert physical_flat['operation_count'] == canonical_flat['operation_count'] + qroam_table_extension['operation_count']
    assert physical_flat['gate_totals']['cx'] == qroam_table_extension['operation_count']
    assert physical_flat['non_clifford_count'] == expected['public_totals']['non_clifford']
    assert physical_flat['peak_live_qubits'] == expected['public_totals']['logical_qubits']
    assert physical_flat['qroam_table_cnot_splice_count'] == qroam_table_extension['segment_count']
    flat_probe = expected['primitive_operation_evidence']['public_candidate_materialized_circuit_manifest']['flat_execution_probe']
    assert flat_probe['probe_count'] >= 15
    assert len(flat_probe['probe_stream_sha256']) == 64
    assert all(flat_probe['checks'].values())


def test_public_engine_manifest_rejects_engine_total_drift() -> None:
    reusable = _load('reusable_chunk_lowering.json')
    reusable['executable_resource_engine']['public_totals']['logical_qubits'] += 1
    observed = _build_manifest(reusable=reusable)
    assert observed['checks']['legacy_wrapper_totals_match_executable_resource_engine_snapshot'] is False
    assert observed['checks']['legacy_wrapper_totals_match_counted_resource_engine'] is True
    assert observed['checks']['legacy_wrapper_totals_match_resource_contract_engine'] is True
    assert observed['pass'] is False


def test_public_engine_manifest_rejects_semantic_boundary_drift() -> None:
    release_preflight = _load('release_corpus_preflight.json')
    release_preflight['category_counts']['lookup_infinity'] = 0
    observed = _build_manifest(release_preflight=release_preflight)
    assert observed['checks']['release_corpus_preflight_covers_required_categories'] is False
    assert observed['pass'] is False


def test_public_engine_manifest_rejects_compiler_parameter_family_drift() -> None:
    compiler_parameters = _load('compiler_parameters.json')
    compiler_parameters['public_headline_policy']['selected_public_family_name'] = 'wrong_family'
    observed = _build_manifest(compiler_parameters=compiler_parameters)
    assert observed['checks']['compiler_parameters_bind_selected_public_family'] is False
    assert observed['pass'] is False


def test_public_engine_manifest_rejects_qroam_primitive_drift() -> None:
    qroam_primitive = _load('qroam_primitive_certificate.json')
    qroam_primitive['traversed_counts']['per_stream_non_clifford'] += 1
    observed = _build_manifest(qroam_primitive=qroam_primitive)
    assert observed['checks']['qroam_primitive_stream_binds_stream_terms'] is False
    assert observed['pass'] is False


def test_public_engine_manifest_rejects_qroam_table_cnot_drift() -> None:
    qroam_table_cnot = _load('qroam_table_cnot_materialization.json')
    qroam_table_cnot['totals']['full_oracle_potential_target_bit_sites'] += 1
    observed = _build_manifest(qroam_table_cnot=qroam_table_cnot)
    assert observed['checks']['qroam_table_cnot_materialization_binds_target_bit_sites'] is False
    assert observed['pass'] is False


def test_public_engine_manifest_rejects_arithmetic_operation_drift() -> None:
    arithmetic_operation_ir = _load('arithmetic_operation_ir.json')
    arithmetic_operation_ir['leaf_arithmetic_summary']['rows'][0]['primitive_counts_total']['ccx'] += 1
    observed = _build_manifest(arithmetic_operation_ir=arithmetic_operation_ir)
    assert observed['checks']['arithmetic_operation_ir_binds_tail_opcode'] is False
    assert observed['pass'] is False


def test_public_engine_manifest_rejects_phase_shell_drift() -> None:
    phase_shell = _load('phase_shell_lowerings.json')
    for row in phase_shell['families']:
        if row['name'] == 'semiclassical_qft_v1':
            row['hadamard_count'] -= 1
    observed = _build_manifest(phase_shell=phase_shell)
    assert observed['checks']['phase_shell_primitive_counts_bind_public_family'] is False
    assert observed['pass'] is False


def test_public_engine_manifest_rejects_public_candidate_materialized_drift() -> None:
    public_candidate_materialized = _load('public_candidate_materialized_circuit_manifest.json')
    public_candidate_materialized['public_totals']['non_clifford'] -= 1
    observed = _build_manifest(public_candidate_materialized=public_candidate_materialized)
    assert observed['checks']['public_candidate_materialized_stream_binds_engine_totals'] is False
    assert observed['pass'] is False


def test_public_engine_manifest_rejects_canonical_physical_flat_drift() -> None:
    public_candidate_materialized = _load('public_candidate_materialized_circuit_manifest.json')
    public_candidate_materialized['canonical_physical_flat_netlist']['gate_totals']['cx'] -= 1
    observed = _build_manifest(public_candidate_materialized=public_candidate_materialized)
    assert observed['checks']['public_candidate_materialized_stream_binds_engine_totals'] is False
    assert observed['pass'] is False


def test_public_engine_manifest_derives_totals_from_flat_materialized_engine() -> None:
    public_candidate_materialized = _load('public_candidate_materialized_circuit_manifest.json')
    public_candidate_materialized[CANONICAL_MATERIALIZED_FLAT_NETLIST]['non_clifford_count'] -= 1
    observed = _build_manifest(public_candidate_materialized=public_candidate_materialized)
    assert observed['public_totals']['non_clifford'] == public_candidate_materialized[CANONICAL_MATERIALIZED_FLAT_NETLIST]['non_clifford_count']
    assert observed['checks'][PUBLIC_TOTALS_MATCH_CANONICAL_ENGINE_CHECK] is False
    assert observed['checks']['resource_terms_sum_to_public_total'] is False
    assert observed['checks']['public_candidate_materialized_stream_binds_engine_totals'] is False
    assert observed['pass'] is False


def test_public_engine_manifest_rejects_missing_full_materialized_netlist() -> None:
    public_candidate_materialized = _load('public_candidate_materialized_circuit_manifest.json')
    public_candidate_materialized[CANONICAL_MATERIALIZED_FLAT_NETLIST]['exact_operation_stream_materialized'] = False
    public_candidate_materialized['checks'][PUBLIC_TOTALS_DERIVE_FROM_CANONICAL_CHECK] = False
    observed = _build_manifest(public_candidate_materialized=public_candidate_materialized)
    assert observed['checks'][PUBLIC_TOTALS_MATCH_CANONICAL_ENGINE_CHECK] is False
    assert observed['checks']['public_candidate_materialized_stream_binds_engine_totals'] is False
    assert observed['pass'] is False


def test_public_engine_manifest_rejects_flat_execution_probe_drift() -> None:
    public_candidate_materialized = _load('public_candidate_materialized_circuit_manifest.json')
    public_candidate_materialized['flat_execution_probe']['checks']['probe_operand_indices_within_domains'] = False
    observed = _build_manifest(public_candidate_materialized=public_candidate_materialized)
    assert observed['checks']['public_candidate_materialized_stream_binds_engine_totals'] is False
    assert observed['pass'] is False


def test_public_engine_manifest_binds_strict_primitive_completeness_report() -> None:
    public_candidate_materialized = _load('public_candidate_materialized_circuit_manifest.json')
    observed = _build_manifest(public_candidate_materialized=public_candidate_materialized)
    strict_report = observed['primitive_operation_evidence']['public_candidate_materialized_circuit_manifest']['strict_primitive_completeness']
    assert observed['checks']['strict_primitive_completeness_report_is_bound'] is True
    assert strict_report['clifford_complete'] is True
    assert strict_report['rows_checked'] == public_candidate_materialized['run_length_row_count']
    assert strict_report['incomplete_row_count'] == 0


def test_public_engine_manifest_binds_operand_parent_binding_report() -> None:
    public_candidate_materialized = _load('public_candidate_materialized_circuit_manifest.json')
    observed = _build_manifest(public_candidate_materialized=public_candidate_materialized)
    parent_report = observed['primitive_operation_evidence']['public_candidate_materialized_circuit_manifest']['operand_parent_binding']
    assert observed['checks']['operand_parent_binding_report_is_bound'] is True
    assert parent_report['pass'] is True
    assert parent_report['rows_checked'] == public_candidate_materialized['run_length_row_count']
    assert parent_report['failure_count'] == 0


def test_public_engine_manifest_binds_operand_source_binding_report() -> None:
    public_candidate_materialized = _load('public_candidate_materialized_circuit_manifest.json')
    observed = _build_manifest(public_candidate_materialized=public_candidate_materialized)
    source_report = observed['primitive_operation_evidence']['public_candidate_materialized_circuit_manifest']['operand_source_binding']
    assert observed['checks']['operand_source_binding_report_is_bound'] is True
    assert source_report['pass'] is True
    assert source_report['rows_checked'] == public_candidate_materialized['run_length_row_count']
    assert source_report['failure_count'] == 0
    assert set(source_report['rows_by_source_kind']) == {
        'arithmetic_operation_ir',
        'lookup_lowering_block',
        'phase_shell_lowering',
        'qroam_primitive_certificate',
    }


def test_public_engine_manifest_rejects_operand_parent_binding_drift() -> None:
    public_candidate_materialized = _load('public_candidate_materialized_circuit_manifest.json')
    public_candidate_materialized['operand_parent_binding']['pass'] = False
    public_candidate_materialized['operand_parent_binding']['failure_count'] = 1
    observed = _build_manifest(public_candidate_materialized=public_candidate_materialized)
    assert observed['checks']['operand_parent_binding_report_is_bound'] is False
    assert observed['pass'] is False


def test_public_engine_manifest_rejects_operand_source_binding_drift() -> None:
    public_candidate_materialized = _load('public_candidate_materialized_circuit_manifest.json')
    public_candidate_materialized['operand_source_binding']['pass'] = False
    public_candidate_materialized['operand_source_binding']['failure_count'] = 1
    observed = _build_manifest(public_candidate_materialized=public_candidate_materialized)
    assert observed['checks']['operand_source_binding_report_is_bound'] is False
    assert observed['pass'] is False


def test_public_engine_manifest_rejects_strict_primitive_completeness_drift() -> None:
    public_candidate_materialized = _load('public_candidate_materialized_circuit_manifest.json')
    public_candidate_materialized['strict_primitive_completeness']['clifford_complete'] = False
    public_candidate_materialized['strict_primitive_completeness']['incomplete_row_count'] = 1
    public_candidate_materialized['strict_primitive_completeness']['incomplete_by_scope_gate'] = {
        'qroam_chunk_stream:ccx': 1,
    }
    observed = _build_manifest(public_candidate_materialized=public_candidate_materialized)
    assert observed['checks']['strict_primitive_completeness_report_is_bound'] is False
    assert observed['pass'] is False
