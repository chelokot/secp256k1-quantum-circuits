from __future__ import annotations

import itertools
import json
import subprocess
import sys
from pathlib import Path

from support import ensure_compiler_project_build_summary


REPO_ROOT = Path(__file__).resolve().parents[1]
COMPILER_SRC = REPO_ROOT / 'compiler_verification_project' / 'src'
if str(COMPILER_SRC) not in sys.path:
    sys.path.insert(0, str(COMPILER_SRC))

from materialized_circuit import MATERIALIZED_CIRCUIT_MANIFEST_SCHEMA, PUBLIC_CANDIDATE_MATERIALIZED_CIRCUIT_MANIFEST_SCHEMA, build_public_candidate_materialized_circuit_manifest, iter_family_operation_stream, resolve_selected_family_names  # noqa: E402


def _frontier() -> dict:
    ensure_compiler_project_build_summary()
    return json.loads((REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'family_frontier.json').read_text())


def _artifact(name: str) -> dict:
    ensure_compiler_project_build_summary()
    return json.loads((REPO_ROOT / 'compiler_verification_project' / 'artifacts' / name).read_text())


def _candidate_input() -> dict:
    ensure_compiler_project_build_summary()
    return json.loads((
        REPO_ROOT
        / 'compiler_verification_project'
        / 'artifacts'
        / 'zkp_attestation_reusable_chunk_candidate'
        / 'zkp_attestation_input.json'
    ).read_text())


def test_materialized_family_aliases_resolve_to_frontier_rows() -> None:
    frontier = _frontier()
    resolved = resolve_selected_family_names(['best-gate', 'best-qubit'], frontier=frontier)
    expected = []
    for family in (frontier['best_gate_family']['name'], frontier['best_qubit_family']['name']):
        if family not in expected:
            expected.append(family)
    assert resolved == expected


def test_materialized_operation_stream_emits_seed_lookup_rows() -> None:
    frontier = _frontier()
    family_name = frontier['best_gate_family']['name']
    preview = list(itertools.islice(iter_family_operation_stream(family_name, frontier=frontier), 16))
    assert preview
    assert all(row['family'] == family_name for row in preview)
    assert all(row['scope'] == 'direct_seed' for row in preview[:8])
    assert all(row['gate'] in {'ccx', 'measurement'} for row in preview)


def test_checked_materialized_manifest_reconstructs_best_qubit_headline() -> None:
    frontier = _frontier()
    family = frontier['best_qubit_family']
    manifest = json.loads(
        (
            REPO_ROOT
            / 'compiler_verification_project'
            / 'artifacts'
            / 'materialized_circuit_manifest.json'
        ).read_text()
    )
    assert manifest['schema'] == MATERIALIZED_CIRCUIT_MANIFEST_SCHEMA
    assert manifest['family'] == family['name']
    assert manifest['gate_totals']['ccx'] == family['full_oracle_non_clifford']
    assert manifest['gate_totals']['measurement'] == family['total_measurements']
    assert all(manifest['reconstruction_checks'].values())
    assert len(manifest['operation_stream_sha256']) == 64
    assert manifest['segment_count'] == len(manifest['segments'])
    assert sum(segment['operation_count'] for segment in manifest['segments']) == manifest['operation_count']
    assert len(manifest['segment_merkle_root_sha256']) == 64


def test_public_candidate_materialized_manifest_reconstructs_current_headline() -> None:
    manifest = _artifact('public_candidate_materialized_circuit_manifest.json')
    reusable = _artifact('reusable_chunk_lowering.json')
    assert manifest['schema'] == PUBLIC_CANDIDATE_MATERIALIZED_CIRCUIT_MANIFEST_SCHEMA
    assert manifest['selected_family_name'] == _candidate_input()['selected_family_name']
    assert manifest['pass'] is True
    assert manifest['public_totals']['non_clifford'] == reusable['non_clifford_derivation']['candidate_total_non_clifford']
    assert manifest['public_totals']['logical_qubits'] == reusable['qubit_derivation']['candidate_total_logical_qubits']
    assert manifest['liveness_binding_row_count'] == manifest['run_length_row_count']
    assert manifest['materialized_liveness']['peak_live_qubits'] == reusable['qubit_derivation']['candidate_total_logical_qubits']
    assert manifest['direct_seed_row_count'] == 2
    assert manifest['lookup_leaf_base_row_count'] == 2 * reusable['stream_plan']['leaf_call_count_total']
    assert manifest['arithmetic_leaf_stage_row_count'] > reusable['stream_plan']['leaf_call_count_total']
    assert manifest['qroam_expansion']['stream_instances'] == reusable['stream_plan']['whole_oracle_chunk_streams']
    assert manifest['qroam_expansion']['non_clifford'] == reusable['non_clifford_derivation']['qroam_chunk_non_clifford']
    assert manifest['qroam_segment_row_count'] == manifest['qroam_expansion']['stream_instances'] * manifest['qroam_expansion']['segments_per_stream']
    assert len(manifest['run_length_rows']) == manifest['run_length_row_count']
    assert len(manifest['materialized_liveness']['rows']) == manifest['liveness_binding_row_count']
    assert manifest['flat_netlist']['operation_count'] == sum(manifest['gate_totals'].values())
    assert manifest['flat_netlist']['gate_totals'] == manifest['gate_totals']
    assert manifest['flat_netlist']['non_clifford_count'] == manifest['public_totals']['non_clifford']
    assert manifest['flat_netlist']['segment_count'] == len(manifest['flat_netlist']['segments'])
    assert manifest['checks']['qroam_liveness_bindings_use_matching_chunk_target'] is True
    assert manifest['checks']['flat_netlist_expands_all_run_length_rows'] is True
    assert manifest['checks']['flat_netlist_gate_totals_match_run_length_rows'] is True
    assert manifest['checks']['flat_netlist_non_clifford_matches_public_candidate'] is True
    assert manifest['checks']['primitive_operand_contracts_cover_all_run_length_rows'] is True
    assert manifest['checks']['primitive_operand_contract_owners_are_known_and_live'] is True
    assert manifest['checks']['flat_netlist_binds_operand_contract_hashes'] is True
    assert manifest['checks']['direct_seed_liveness_excludes_qroam_target_and_chunk'] is True
    assert manifest['checks']['lookup_leaf_liveness_excludes_qroam_target_and_chunk'] is True
    assert manifest['checks']['generated_base_rows_match_public_non_qroam_derivation'] is True
    assert manifest['checks']['arithmetic_rows_exclude_replaced_streamed_qroam_stages'] is True
    assert manifest['checks']['liveness_bindings_have_unique_live_wires'] is True
    assert manifest['checks']['liveness_bindings_recompute_owner_sums_from_wire_catalog'] is True
    assert manifest['checks']['liveness_bindings_recompute_owner_capacity_from_wire_catalog'] is True
    assert manifest['checks']['phase_liveness_uses_phase_load_interval_without_lookup_target'] is True
    assert manifest['materialized_liveness']['preview_head'][0]['total_live_qubits'] < manifest['public_totals']['logical_qubits']
    assert 'arithmetic_leaf_base' not in {row['scope'] for row in manifest['preview_head'] + manifest['preview_tail']}
    first_arithmetic_row = next(row for row in manifest['run_length_rows'] if row['scope'] == 'arithmetic_leaf_stage')
    assert first_arithmetic_row['primitive_operand_contract']['owner_ids'] == ['arithmetic_slot_register_file']
    first_qroam_row = next(row for row in manifest['run_length_rows'] if row['scope'] == 'qroam_chunk_stream')
    assert first_qroam_row['primitive_operand_contract']['owner_ids'] == ['arithmetic_slot_register_file', 'lookup_workspace']
    assert manifest['flat_netlist']['segments'][0]['contributions'][0]['primitive_operand_contract_sha256']


def test_public_candidate_materialized_manifest_rejects_qroam_segment_drift() -> None:
    qroam = _artifact('qroam_primitive_certificate.json')
    qroam['operation_stream']['segments'][0]['ccx'] -= 1
    candidate_input = _candidate_input()
    observed = build_public_candidate_materialized_circuit_manifest(
        reusable_chunk_lowering=_artifact('reusable_chunk_lowering.json'),
        arithmetic_operation_ir=_artifact('arithmetic_operation_ir.json'),
        lookup_lowerings=_artifact('lookup_lowerings.json'),
        qroam_primitive_certificate=qroam,
        phase_shell_lowerings=_artifact('phase_shell_lowerings.json'),
        zkp_attestation_input=candidate_input,
        selected_family_name=candidate_input['selected_family_name'],
    )
    assert observed['checks']['non_clifford_total_matches_public_candidate'] is False
    assert observed['checks']['qroam_rows_sum_to_public_qroam_derivation'] is False
    assert observed['pass'] is False


def test_public_candidate_materialized_manifest_rejects_arithmetic_stage_drift() -> None:
    arithmetic_operation_ir = _artifact('arithmetic_operation_ir.json')
    tail = next(row for row in arithmetic_operation_ir['kernels'] if row['opcode'] == 'complete_a0_all_streamed_tail')
    stage = next(row for row in tail['stages'] if row['category'] != 'streamed_lookup_data_select')
    stage['primitive_counts_total']['ccx'] += 1
    candidate_input = _candidate_input()
    observed = build_public_candidate_materialized_circuit_manifest(
        reusable_chunk_lowering=_artifact('reusable_chunk_lowering.json'),
        arithmetic_operation_ir=arithmetic_operation_ir,
        lookup_lowerings=_artifact('lookup_lowerings.json'),
        qroam_primitive_certificate=_artifact('qroam_primitive_certificate.json'),
        phase_shell_lowerings=_artifact('phase_shell_lowerings.json'),
        zkp_attestation_input=candidate_input,
        selected_family_name=candidate_input['selected_family_name'],
    )
    assert observed['checks']['non_clifford_total_matches_public_candidate'] is False
    assert observed['checks']['generated_base_rows_match_public_non_qroam_derivation'] is False
    assert observed['pass'] is False


def test_public_candidate_materialized_manifest_rejects_lookup_base_drift() -> None:
    lookup_lowerings = _artifact('lookup_lowerings.json')
    family = next(row for row in lookup_lowerings['families'] if row['name'] == 'folded_standard_qroam_streamed_coordinate_v1')
    family['primitive_counts_total']['ccx'] -= 1
    candidate_input = _candidate_input()
    observed = build_public_candidate_materialized_circuit_manifest(
        reusable_chunk_lowering=_artifact('reusable_chunk_lowering.json'),
        arithmetic_operation_ir=_artifact('arithmetic_operation_ir.json'),
        lookup_lowerings=lookup_lowerings,
        qroam_primitive_certificate=_artifact('qroam_primitive_certificate.json'),
        phase_shell_lowerings=_artifact('phase_shell_lowerings.json'),
        zkp_attestation_input=candidate_input,
        selected_family_name=candidate_input['selected_family_name'],
    )
    assert observed['checks']['non_clifford_total_matches_public_candidate'] is False
    assert observed['checks']['generated_base_rows_match_public_non_qroam_derivation'] is False
    assert observed['checks']['generated_base_rows_bind_family_snapshot'] is False
    assert observed['pass'] is False


def test_public_candidate_materialized_manifest_rejects_forged_liveness_owner_sum() -> None:
    reusable = _artifact('reusable_chunk_lowering.json')
    interval = next(row for row in reusable['executable_liveness']['intervals'] if row['interval_id'] == reusable['executable_liveness']['global_peak_interval_id'])
    interval['owner_live_qubits']['lookup_workspace'] -= 1
    candidate_input = _candidate_input()
    observed = build_public_candidate_materialized_circuit_manifest(
        reusable_chunk_lowering=reusable,
        arithmetic_operation_ir=_artifact('arithmetic_operation_ir.json'),
        lookup_lowerings=_artifact('lookup_lowerings.json'),
        qroam_primitive_certificate=_artifact('qroam_primitive_certificate.json'),
        phase_shell_lowerings=_artifact('phase_shell_lowerings.json'),
        zkp_attestation_input=candidate_input,
        selected_family_name=candidate_input['selected_family_name'],
    )
    assert observed['checks']['liveness_bindings_recompute_owner_sums_from_wire_catalog'] is False
    assert observed['pass'] is False


def test_public_candidate_materialized_manifest_rejects_duplicate_live_wire() -> None:
    reusable = _artifact('reusable_chunk_lowering.json')
    interval = next(row for row in reusable['executable_liveness']['intervals'] if row['interval_id'] == reusable['executable_liveness']['global_peak_interval_id'])
    interval['live_wire_ids'].append(interval['live_wire_ids'][0])
    candidate_input = _candidate_input()
    observed = build_public_candidate_materialized_circuit_manifest(
        reusable_chunk_lowering=reusable,
        arithmetic_operation_ir=_artifact('arithmetic_operation_ir.json'),
        lookup_lowerings=_artifact('lookup_lowerings.json'),
        qroam_primitive_certificate=_artifact('qroam_primitive_certificate.json'),
        phase_shell_lowerings=_artifact('phase_shell_lowerings.json'),
        zkp_attestation_input=candidate_input,
        selected_family_name=candidate_input['selected_family_name'],
    )
    assert observed['checks']['liveness_bindings_have_unique_live_wires'] is False
    assert observed['checks']['liveness_bindings_recompute_owner_sums_from_wire_catalog'] is False
    assert observed['pass'] is False


def test_public_candidate_materialized_manifest_rejects_operand_owner_not_live() -> None:
    reusable = _artifact('reusable_chunk_lowering.json')
    interval = next(row for row in reusable['executable_liveness']['intervals'] if row['interval_id'] == 'pc4_lookup_infinity_flag')
    interval['live_wire_ids'] = [wire_id for wire_id in interval['live_wire_ids'] if wire_id != 'folded_lookup_control_workspace']
    interval['owner_live_qubits'].pop('lookup_workspace')
    interval['total_live_qubits'] -= 18
    candidate_input = _candidate_input()
    observed = build_public_candidate_materialized_circuit_manifest(
        reusable_chunk_lowering=reusable,
        arithmetic_operation_ir=_artifact('arithmetic_operation_ir.json'),
        lookup_lowerings=_artifact('lookup_lowerings.json'),
        qroam_primitive_certificate=_artifact('qroam_primitive_certificate.json'),
        phase_shell_lowerings=_artifact('phase_shell_lowerings.json'),
        zkp_attestation_input=candidate_input,
        selected_family_name=candidate_input['selected_family_name'],
    )
    assert observed['checks']['primitive_operand_contract_owners_are_known_and_live'] is False
    assert observed['pass'] is False


def test_materialized_circuit_script_lists_available_families() -> None:
    output = subprocess.check_output(
        [sys.executable, 'compiler_verification_project/scripts/materialize_exact_circuits.py', '--list-families'],
        cwd=REPO_ROOT,
        text=True,
    )
    payload = json.loads(output)
    assert payload['best_gate_family']
    assert payload['best_qubit_family']
    frontier = _frontier()
    expected_family_count = (
        len(frontier['lookup_families'])
        * len(frontier['phase_shell_families'])
        * len(frontier['slot_allocation_families'])
    )
    assert len(payload['available_families']) == expected_family_count
