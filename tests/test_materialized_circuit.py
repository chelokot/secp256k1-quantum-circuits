from __future__ import annotations

import itertools
import json
import subprocess
import sys
import gzip
from pathlib import Path

from support import ensure_compiler_project_build_summary


REPO_ROOT = Path(__file__).resolve().parents[1]
COMPILER_SRC = REPO_ROOT / 'compiler_verification_project' / 'src'
if str(COMPILER_SRC) not in sys.path:
    sys.path.insert(0, str(COMPILER_SRC))

from materialized_circuit import MATERIALIZED_CIRCUIT_MANIFEST_SCHEMA, PRIMITIVE_GATE_ARITY, PUBLIC_CANDIDATE_MATERIALIZED_CIRCUIT_MANIFEST_SCHEMA, build_public_candidate_materialized_circuit_manifest, iter_family_operation_stream, iter_public_candidate_flat_netlist, resolve_selected_family_names  # noqa: E402


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


def _compiler_parameters() -> dict:
    return _artifact('compiler_parameters.json')


def _public_family_name() -> str:
    return _compiler_parameters()['public_headline_policy']['selected_public_family_name']


def _build_public_candidate_materialized(
    *,
    reusable: dict | None = None,
    arithmetic_operation_ir: dict | None = None,
    lookup_lowerings: dict | None = None,
    qroam_primitive: dict | None = None,
    phase_shell: dict | None = None,
    compiler_parameters: dict | None = None,
) -> dict:
    resolved_compiler_parameters = compiler_parameters or _compiler_parameters()
    return build_public_candidate_materialized_circuit_manifest(
        reusable_chunk_lowering=reusable or _artifact('reusable_chunk_lowering.json'),
        arithmetic_operation_ir=arithmetic_operation_ir or _artifact('arithmetic_operation_ir.json'),
        lookup_lowerings=lookup_lowerings or _artifact('lookup_lowerings.json'),
        qroam_primitive_certificate=qroam_primitive or _artifact('qroam_primitive_certificate.json'),
        phase_shell_lowerings=phase_shell or _artifact('phase_shell_lowerings.json'),
        compiler_parameters=resolved_compiler_parameters,
        selected_family_name=resolved_compiler_parameters['public_headline_policy']['selected_public_family_name'],
        include_materialized_flat_netlist=False,
        strict_replayed_tail_headline=_artifact('strict_replayed_tail_headline.json'),
        tail_macro_engine=_artifact('tail_macro_engine.json'),
    )


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
    assert manifest['selected_family_name'] == _public_family_name()
    assert manifest['pass'] is True
    assert manifest['public_totals']['source'] == 'public_candidate_materialized.materialized_flat_netlist.non_clifford_count + materialized_flat_netlist.peak_live_qubits'
    assert manifest['public_totals']['non_clifford'] == reusable['non_clifford_derivation']['candidate_total_non_clifford']
    assert manifest['public_totals']['logical_qubits'] == reusable['qubit_derivation']['candidate_total_logical_qubits']
    assert manifest['liveness_binding_row_count'] == manifest['run_length_row_count']
    assert manifest['materialized_liveness']['peak_live_qubits'] == reusable['qubit_derivation']['candidate_total_logical_qubits']
    lookup_lowerings = _artifact('lookup_lowerings.json')
    lookup_family = next(row for row in lookup_lowerings['families'] if row['name'] == 'folded_standard_qroam_streamed_coordinate_v1')
    lookup_rows_per_call = sum(
        1
        for stage in lookup_family['stages']
        for block in stage.get('blocks', [])
        for count in block['primitive_counts_total'].values()
        if int(count) > 0
    )
    assert manifest['direct_seed_row_count'] == lookup_rows_per_call
    assert manifest['lookup_leaf_base_row_count'] == lookup_rows_per_call * reusable['stream_plan']['leaf_call_count_total']
    assert manifest['arithmetic_leaf_block_row_count'] > reusable['stream_plan']['leaf_call_count_total']
    assert manifest['qroam_expansion']['stream_instances'] == reusable['stream_plan']['whole_oracle_chunk_streams']
    assert manifest['qroam_expansion']['non_clifford'] == reusable['non_clifford_derivation']['qroam_chunk_non_clifford']
    assert manifest['qroam_segment_row_count'] == manifest['qroam_expansion']['stream_instances'] * manifest['qroam_expansion']['segments_per_stream']
    assert len(manifest['run_length_rows']) == manifest['run_length_row_count']
    assert len(manifest['materialized_liveness']['rows']) == manifest['liveness_binding_row_count']
    assert manifest['flat_netlist']['operation_count'] == sum(manifest['gate_totals'].values())
    assert manifest['flat_netlist']['gate_totals'] == manifest['gate_totals']
    assert manifest['flat_netlist']['non_clifford_count'] == manifest['public_totals']['non_clifford']
    assert manifest['flat_netlist']['segment_count'] == len(manifest['flat_netlist']['segments'])
    assert manifest['materialized_flat_netlist']['schema'] == 'compiler-project-public-candidate-materialized-flat-netlist-v1'
    assert manifest['materialized_flat_netlist']['exact_operation_stream_materialized'] is True
    assert manifest['materialized_flat_netlist']['operation_count'] == manifest['flat_netlist']['operation_count']
    assert manifest['materialized_flat_netlist']['gate_totals'] == manifest['gate_totals']
    assert manifest['materialized_flat_netlist']['non_clifford_count'] == manifest['public_totals']['non_clifford']
    assert manifest['materialized_flat_netlist']['peak_live_qubits'] == manifest['public_totals']['logical_qubits']
    assert manifest['materialized_flat_netlist']['segment_count'] == len(manifest['materialized_flat_netlist']['segments'])
    assert len(manifest['materialized_flat_netlist']['operation_stream_sha256']) == 64
    assert len(manifest['materialized_flat_netlist']['segment_merkle_root_sha256']) == 64
    assert manifest['checks']['qroam_liveness_bindings_use_matching_chunk_target'] is True
    assert manifest['checks']['flat_netlist_expands_all_run_length_rows'] is True
    assert manifest['checks']['flat_netlist_gate_totals_match_run_length_rows'] is True
    assert manifest['checks']['flat_netlist_non_clifford_matches_public_candidate'] is True
    assert manifest['checks']['materialized_flat_netlist_stream_is_exact'] is True
    assert manifest['checks']['materialized_flat_netlist_counts_match_index_netlist'] is True
    assert manifest['checks']['materialized_flat_netlist_segments_cover_stream'] is True
    assert manifest['checks']['materialized_flat_netlist_preview_rows_are_concrete'] is True
    assert manifest['checks']['primitive_operand_contracts_cover_all_run_length_rows'] is True
    assert manifest['checks']['primitive_operand_contract_owners_are_known_and_live'] is True
    assert manifest['checks']['primitive_operand_domains_bind_counted_live_parent_wires'] is True
    assert manifest['checks']['primitive_operand_rows_bind_source_operation_blocks'] is True
    assert manifest['checks']['flat_netlist_binds_operand_contract_hashes'] is True
    assert manifest['checks']['flat_execution_probe_operations_bind_segment_contributions'] is True
    assert manifest['checks']['flat_execution_probe_operand_indices_within_domains'] is True
    assert manifest['checks']['flat_execution_probe_operand_owners_are_live_and_within_capacity'] is True
    assert manifest['checks']['flat_execution_probe_reduced_schoolbook_grid_executes'] is True
    assert manifest['checks']['flat_execution_probe_qroam_target_width_matches_segments'] is True
    assert manifest['checks']['flat_execution_probe_arithmetic_two_operand_domains_match_rows'] is True
    assert manifest['checks']['strict_primitive_completeness_report_is_current'] is True
    assert manifest['checks']['operand_parent_binding_report_is_current'] is True
    assert manifest['checks']['operand_source_binding_report_is_current'] is True
    assert manifest['checks']['direct_seed_liveness_excludes_qroam_target_and_chunk'] is True
    assert manifest['checks']['lookup_leaf_liveness_excludes_qroam_target_and_chunk'] is True
    assert manifest['checks']['generated_base_rows_match_public_non_qroam_derivation'] is True
    assert manifest['checks']['arithmetic_rows_exclude_replaced_streamed_qroam_stages'] is True
    assert manifest['checks']['liveness_bindings_have_unique_live_wires'] is True
    assert manifest['checks']['liveness_bindings_recompute_owner_sums_from_wire_catalog'] is True
    assert manifest['checks']['liveness_bindings_recompute_owner_capacity_from_wire_catalog'] is True
    assert manifest['checks']['phase_liveness_uses_phase_load_interval_without_lookup_target'] is True
    assert manifest['checks']['strict_replayed_tail_capacity_overlay_is_bound'] is True
    overlay = manifest['strict_replayed_tail_capacity_overlay']
    strict_headline = _artifact('strict_replayed_tail_headline.json')
    assert overlay['pass'] is True
    assert overlay['flat_operation_stream']['non_clifford_count'] == strict_headline['selected_result']['non_clifford']
    assert overlay['strict_capacity_terms']['reconstructed_logical_qubits'] == strict_headline['selected_result']['logical_qubits']
    assert overlay['claim_boundary']['flat_operation_stream_binds_non_clifford'] is True
    assert overlay['claim_boundary']['strict_replayed_tail_capacity_binds_logical_qubits'] is True
    assert overlay['claim_boundary']['full_operation_index_liveness_rewrite_binds_strict_qubits'] is False
    assert manifest['checks']['strict_replayed_tail_liveness_projection_is_bound'] is True
    projection = manifest['strict_replayed_tail_liveness_projection']
    assert projection['pass'] is True
    assert projection['row_count'] == manifest['liveness_binding_row_count']
    assert projection['peak_live_qubits'] == strict_headline['selected_result']['logical_qubits']
    assert projection['claim_boundary']['run_length_rows_bind_strict_tail_liveness'] is True
    assert projection['claim_boundary']['operation_index_rows_can_inherit_projected_liveness'] is True
    assert projection['claim_boundary']['materialized_flat_netlist_segment_hashes_include_projected_liveness'] is False
    assert all(row['total_live_qubits'] == projection['peak_live_qubits'] for row in projection['rows'] if row['scope'] == 'arithmetic_leaf_block')
    assert manifest['materialized_liveness']['preview_head'][0]['total_live_qubits'] < manifest['public_totals']['logical_qubits']
    assert 'arithmetic_leaf_base' not in {row['scope'] for row in manifest['preview_head'] + manifest['preview_tail']}
    first_arithmetic_row = next(row for row in manifest['run_length_rows'] if row['scope'] == 'arithmetic_leaf_block')
    assert first_arithmetic_row['primitive_operand_contract']['owner_ids'] == ['arithmetic_slot_register_file']
    assert first_arithmetic_row['arithmetic_block']
    first_qroam_row = next(row for row in manifest['run_length_rows'] if row['scope'] == 'qroam_chunk_stream')
    assert first_qroam_row['primitive_operand_contract']['owner_ids'] == ['arithmetic_slot_register_file', 'lookup_workspace']
    assert manifest['flat_netlist']['segments'][0]['contributions'][0]['primitive_operand_contract_sha256']
    probe = manifest['flat_execution_probe']
    assert probe['schema'] == 'compiler-project-flat-netlist-execution-probe-v1'
    assert probe['probe_count'] >= 15
    assert all(probe['checks'].values())
    assert any(row['applies'] is True and row['pass'] is True for row in probe['reduced_arithmetic_probes'])
    strict_completeness = manifest['strict_primitive_completeness']
    assert strict_completeness['schema'] == 'compiler-project-strict-primitive-completeness-report-v1'
    assert strict_completeness['rows_checked'] == manifest['run_length_row_count']
    assert strict_completeness['clifford_complete'] is True
    assert strict_completeness['incomplete_row_count'] == 0
    assert strict_completeness['incomplete_by_scope_gate'] == {}
    parent_binding = manifest['operand_parent_binding']
    assert parent_binding['schema'] == 'compiler-project-operand-parent-binding-report-v1'
    assert parent_binding['pass'] is True
    assert parent_binding['failure_count'] == 0
    assert parent_binding['domains_checked'] == sum(len(row['primitive_operand_contract']['operand_domains']) for row in manifest['run_length_rows'])
    source_binding = manifest['operand_source_binding']
    assert source_binding['schema'] == 'compiler-project-operand-source-binding-report-v1'
    assert source_binding['pass'] is True
    assert source_binding['failure_count'] == 0
    assert source_binding['rows_checked'] == manifest['run_length_row_count']
    assert set(source_binding['rows_by_source_kind']) == {
        'arithmetic_operation_ir',
        'lookup_lowering_block',
        'phase_shell_lowering',
        'qroam_primitive_certificate',
    }
    assert all(
        len(row['primitive_operand_contract']['operand_domains']) == PRIMITIVE_GATE_ARITY[row['gate']]
        for row in manifest['run_length_rows']
    )


def test_public_candidate_flat_netlist_iterator_emits_concrete_operand_wires() -> None:
    manifest = _artifact('public_candidate_materialized_circuit_manifest.json')
    arithmetic_row = next(
        row
        for row in manifest['run_length_rows']
        if row['scope'] == 'arithmetic_leaf_block'
        and any(str(domain['domain_id']).endswith(':left_field_bits') for domain in row['primitive_operand_contract']['operand_domains'])
        and any(str(domain['domain_id']).endswith(':right_field_bits') for domain in row['primitive_operand_contract']['operand_domains'])
    )
    start = sum(int(row['total_count']) for row in manifest['run_length_rows'][:int(arithmetic_row['row_index'])])
    operations = list(iter_public_candidate_flat_netlist(
        manifest['run_length_rows'],
        manifest['materialized_liveness']['rows'],
        start=start,
        stop=start + 6,
    ))
    assert [operation['operation_index'] for operation in operations] == list(range(start, start + 6))
    assert [tuple(wire['operand_index'] for wire in operation['operand_wires'][:2]) for operation in operations] == [
        (0, 0),
        (0, 1),
        (0, 2),
        (0, 3),
        (0, 4),
        (0, 5),
    ]
    assert all(len(operation['operand_wires']) == 3 for operation in operations)
    assert all(
        len({(wire['parent_wire_id'], wire['parent_bit_index']) for wire in operation['operand_wires']}) == 3
        for operation in operations
    )
    assert all(operation['primitive_operand_contract_sha256'] == arithmetic_row['primitive_operand_contract_sha256'] for operation in operations)
    assert all(operation['liveness']['total_live_qubits'] == manifest['public_totals']['logical_qubits'] for operation in operations)


def test_public_candidate_flat_netlist_iterator_emits_qroam_three_operands() -> None:
    manifest = _artifact('public_candidate_materialized_circuit_manifest.json')
    qroam_row = next(row for row in manifest['run_length_rows'] if row['scope'] == 'qroam_chunk_stream')
    start = sum(int(row['total_count']) for row in manifest['run_length_rows'][:int(qroam_row['row_index'])])
    operations = list(iter_public_candidate_flat_netlist(
        manifest['run_length_rows'],
        manifest['materialized_liveness']['rows'],
        start=start,
        stop=start + 3,
    ))
    assert all(len(operation['operand_wires']) == 3 for operation in operations)
    assert [wire['role'] for wire in operations[0]['operand_wires']] == [
        'qroam_selection_control',
        'qroam_target_or_unary_step',
        'qroam_chunk_consumer_register',
    ]
    assert all(operation['liveness']['total_live_qubits'] == manifest['public_totals']['logical_qubits'] for operation in operations)


def test_public_candidate_materialized_manifest_rejects_forged_operand_parent_owner() -> None:
    reusable = _artifact('reusable_chunk_lowering.json')
    reusable['executable_liveness']['wire_catalog']['qchunk']['owner_id'] = 'lookup_workspace'
    observed = _build_public_candidate_materialized(
        reusable=reusable,
        arithmetic_operation_ir=_artifact('arithmetic_operation_ir.json'),
        lookup_lowerings=_artifact('lookup_lowerings.json'),
        qroam_primitive=_artifact('qroam_primitive_certificate.json'),
        phase_shell=_artifact('phase_shell_lowerings.json'),
    )
    assert observed['checks']['primitive_operand_domains_bind_counted_live_parent_wires'] is False
    assert observed['checks']['operand_parent_binding_report_is_current'] is False
    assert observed['operand_parent_binding']['failure_count'] > 0
    assert observed['pass'] is False


def test_public_candidate_materialized_manifest_rejects_qroam_domain_width_drift() -> None:
    qroam = _artifact('qroam_primitive_certificate.json')
    qroam['operation_stream']['segments'][0]['end_address_exclusive'] -= 1
    observed = _build_public_candidate_materialized(
        reusable=_artifact('reusable_chunk_lowering.json'),
        arithmetic_operation_ir=_artifact('arithmetic_operation_ir.json'),
        lookup_lowerings=_artifact('lookup_lowerings.json'),
        qroam_primitive=qroam,
        phase_shell=_artifact('phase_shell_lowerings.json'),
    )
    assert observed['checks']['flat_execution_probe_qroam_target_width_matches_segments'] is False
    assert observed['pass'] is False


def test_public_candidate_materialized_manifest_rejects_qroam_segment_drift() -> None:
    qroam = _artifact('qroam_primitive_certificate.json')
    qroam['operation_stream']['segments'][0]['ccx'] -= 1
    observed = _build_public_candidate_materialized(
        reusable=_artifact('reusable_chunk_lowering.json'),
        arithmetic_operation_ir=_artifact('arithmetic_operation_ir.json'),
        lookup_lowerings=_artifact('lookup_lowerings.json'),
        qroam_primitive=qroam,
        phase_shell=_artifact('phase_shell_lowerings.json'),
    )
    assert observed['checks']['non_clifford_total_matches_public_candidate'] is False
    assert observed['checks']['qroam_rows_sum_to_public_qroam_derivation'] is False
    assert observed['pass'] is False


def test_public_candidate_materialized_manifest_rejects_arithmetic_stage_drift() -> None:
    arithmetic_operation_ir = _artifact('arithmetic_operation_ir.json')
    tail = next(row for row in arithmetic_operation_ir['kernels'] if row['opcode'] == 'complete_a0_all_streamed_tail')
    stage = next(row for row in tail['stages'] if row['category'] != 'streamed_lookup_data_select')
    stage['blocks'][0]['primitive_counts_total']['ccx'] += 1
    observed = _build_public_candidate_materialized(
        reusable=_artifact('reusable_chunk_lowering.json'),
        arithmetic_operation_ir=arithmetic_operation_ir,
        lookup_lowerings=_artifact('lookup_lowerings.json'),
        qroam_primitive=_artifact('qroam_primitive_certificate.json'),
        phase_shell=_artifact('phase_shell_lowerings.json'),
    )
    assert observed['checks']['primitive_operand_rows_bind_source_operation_blocks'] is False
    assert observed['checks']['operand_source_binding_report_is_current'] is False
    assert observed['operand_source_binding']['failure_count'] > 0
    assert observed['pass'] is False


def test_public_candidate_materialized_manifest_rejects_lookup_base_drift() -> None:
    lookup_lowerings = _artifact('lookup_lowerings.json')
    family = next(row for row in lookup_lowerings['families'] if row['name'] == 'folded_standard_qroam_streamed_coordinate_v1')
    family['primitive_counts_total']['ccx'] -= 1
    observed = _build_public_candidate_materialized(
        reusable=_artifact('reusable_chunk_lowering.json'),
        arithmetic_operation_ir=_artifact('arithmetic_operation_ir.json'),
        lookup_lowerings=lookup_lowerings,
        qroam_primitive=_artifact('qroam_primitive_certificate.json'),
        phase_shell=_artifact('phase_shell_lowerings.json'),
    )
    assert observed['checks']['primitive_operand_rows_bind_source_operation_blocks'] is False
    assert observed['checks']['operand_source_binding_report_is_current'] is False
    assert observed['operand_source_binding']['failure_count'] > 0
    assert observed['pass'] is False


def test_public_candidate_materialized_manifest_rejects_lookup_block_stream_drift() -> None:
    lookup_lowerings = _artifact('lookup_lowerings.json')
    family = next(row for row in lookup_lowerings['families'] if row['name'] == 'folded_standard_qroam_streamed_coordinate_v1')
    block = family['stages'][0]['blocks'][0]
    block['primitive_operation_stream']['operation_count'] += 1
    observed = _build_public_candidate_materialized(
        reusable=_artifact('reusable_chunk_lowering.json'),
        arithmetic_operation_ir=_artifact('arithmetic_operation_ir.json'),
        lookup_lowerings=lookup_lowerings,
        qroam_primitive=_artifact('qroam_primitive_certificate.json'),
        phase_shell=_artifact('phase_shell_lowerings.json'),
    )
    assert observed['checks']['primitive_operand_rows_bind_source_operation_blocks'] is False
    assert observed['checks']['operand_source_binding_report_is_current'] is False
    assert observed['operand_source_binding']['failure_count'] > 0
    assert observed['pass'] is False


def test_public_candidate_materialized_manifest_rejects_forged_liveness_owner_sum() -> None:
    reusable = _artifact('reusable_chunk_lowering.json')
    interval = next(row for row in reusable['executable_liveness']['intervals'] if row['interval_id'] == reusable['executable_liveness']['global_peak_interval_id'])
    interval['owner_live_qubits']['lookup_workspace'] -= 1
    observed = _build_public_candidate_materialized(
        reusable=reusable,
        arithmetic_operation_ir=_artifact('arithmetic_operation_ir.json'),
        lookup_lowerings=_artifact('lookup_lowerings.json'),
        qroam_primitive=_artifact('qroam_primitive_certificate.json'),
        phase_shell=_artifact('phase_shell_lowerings.json'),
    )
    assert observed['checks']['liveness_bindings_recompute_owner_sums_from_wire_catalog'] is False
    assert observed['pass'] is False


def test_public_candidate_materialized_manifest_rejects_duplicate_live_wire() -> None:
    reusable = _artifact('reusable_chunk_lowering.json')
    interval = next(row for row in reusable['executable_liveness']['intervals'] if row['interval_id'] == reusable['executable_liveness']['global_peak_interval_id'])
    interval['live_wire_ids'].append(interval['live_wire_ids'][0])
    observed = _build_public_candidate_materialized(
        reusable=reusable,
        arithmetic_operation_ir=_artifact('arithmetic_operation_ir.json'),
        lookup_lowerings=_artifact('lookup_lowerings.json'),
        qroam_primitive=_artifact('qroam_primitive_certificate.json'),
        phase_shell=_artifact('phase_shell_lowerings.json'),
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
    observed = _build_public_candidate_materialized(
        reusable=reusable,
        arithmetic_operation_ir=_artifact('arithmetic_operation_ir.json'),
        lookup_lowerings=_artifact('lookup_lowerings.json'),
        qroam_primitive=_artifact('qroam_primitive_certificate.json'),
        phase_shell=_artifact('phase_shell_lowerings.json'),
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


def test_materialized_circuit_script_exports_public_candidate_flat_netlist_slice(tmp_path: Path) -> None:
    output_dir = tmp_path / 'flat-export'
    output = subprocess.check_output(
        [
            sys.executable,
            'compiler_verification_project/scripts/materialize_exact_circuits.py',
            '--public-candidate-flat-netlist',
            '--slice-start',
            '0',
            '--slice-count',
            '5',
            '--output-dir',
            str(output_dir),
        ],
        cwd=REPO_ROOT,
        text=True,
    )
    payload = json.loads(output)
    export = payload['public_candidate_flat_netlist']
    assert export['schema'] == 'compiler-project-public-candidate-flat-netlist-export-v1'
    assert export['row_count'] == 5
    exported_path = Path(export['path'])
    if not exported_path.is_absolute():
        exported_path = REPO_ROOT / exported_path
    with gzip.open(exported_path, 'rt', encoding='utf-8') as handle:
        lines = handle.readlines()
    assert len(lines) == 6
    assert lines[0].startswith('operation_index\trun_length_row_index\trow_instance_ordinal')
    assert lines[1].startswith('0\t0\t0\tdirect_seed_base')
