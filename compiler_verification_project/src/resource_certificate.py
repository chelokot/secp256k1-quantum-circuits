#!/usr/bin/env python3

from __future__ import annotations

from typing import Any, Dict, List, Mapping

from resource_ledger import qroam_clean_stream_cost


def _primitive_zero() -> Dict[str, int]:
    return {'ccx': 0, 'cx': 0, 'x': 0, 'measurement': 0}


def _add_counts(left: Dict[str, int], right: Mapping[str, Any]) -> None:
    for key in ('ccx', 'cx', 'x', 'measurement'):
        left[key] += int(right.get(key, 0))


def _selected_family(ft_ir_compositions: Mapping[str, Any], family_name: str) -> Mapping[str, Any]:
    for family in ft_ir_compositions['families']:
        if family['name'] == family_name:
            return family
    raise KeyError(f'FT IR family not found: {family_name}')


def _source_artifact_lookup(family: Mapping[str, Any]) -> Dict[str, str]:
    return {
        node['id']: str(node['metadata']['source_artifact'])
        for node in family['graph']['nodes']
        if 'source_artifact' in node['metadata']
    }


def _certificate_leaf_sigma(family: Mapping[str, Any]) -> List[Dict[str, Any]]:
    source_lookup = _source_artifact_lookup(family)
    rows: List[Dict[str, Any]] = []
    for entry in family['leaf_sigma']:
        profile = entry['resource_profile']
        semantics = profile['resource_semantics']
        row = {
            'leaf_id': entry['leaf_id'],
            'category': entry['category'],
            'source_artifact': source_lookup.get(entry['leaf_id'], ''),
            'path_multiplicity': int(entry['path_multiplicity']),
            'resource_semantics': semantics,
        }
        if semantics == 'additive_primitive':
            row.update({
                'base_instance_count': int(profile['base_instance_count']),
                'primitive_counts_per_instance': {
                    key: int(profile['primitive_counts_per_instance'].get(key, 0))
                    for key in ('ccx', 'cx', 'x', 'measurement')
                },
                'primitive_counts_total': {
                    key: int(entry['primitive_counts_total'].get(key, 0))
                    for key in ('ccx', 'cx', 'x', 'measurement')
                },
            })
        elif semantics == 'peak_live_qubits':
            row.update({
                'logical_qubits': int(profile['logical_qubits']),
                'logical_qubits_total': int(entry['logical_qubits_total']),
            })
        else:
            row.update({
                'count': int(profile['count']),
                'count_total': int(entry['count_total']),
            })
        rows.append(row)
    return rows


def _reconstruct_leaf_sigma(rows: List[Mapping[str, Any]]) -> Dict[str, Any]:
    primitive_totals = _primitive_zero()
    logical_qubits_total = 0
    phase_shell_hadamards = 0
    phase_shell_measurements = 0
    phase_shell_rotations = 0
    phase_shell_rotation_depth = 0
    for row in rows:
        multiplicity = int(row['path_multiplicity'])
        semantics = row['resource_semantics']
        if semantics == 'additive_primitive':
            per_instance = row['primitive_counts_per_instance']
            base_instance_count = int(row['base_instance_count'])
            reconstructed = {
                key: multiplicity * base_instance_count * int(per_instance.get(key, 0))
                for key in ('ccx', 'cx', 'x', 'measurement')
            }
            if reconstructed != row['primitive_counts_total']:
                raise ValueError(f'primitive row does not reconstruct: {row["leaf_id"]}')
            _add_counts(primitive_totals, reconstructed)
        elif semantics == 'peak_live_qubits':
            logical_total = multiplicity * int(row['logical_qubits'])
            if logical_total != int(row['logical_qubits_total']):
                raise ValueError(f'live-qubit row does not reconstruct: {row["leaf_id"]}')
            logical_qubits_total += logical_total
        elif semantics == 'additive_phase_hadamards':
            phase_shell_hadamards += multiplicity * int(row['count'])
        elif semantics == 'additive_phase_measurements':
            phase_shell_measurements += multiplicity * int(row['count'])
        elif semantics == 'additive_phase_rotations':
            phase_shell_rotations += multiplicity * int(row['count'])
        elif semantics == 'additive_phase_rotation_depth':
            phase_shell_rotation_depth += multiplicity * int(row['count'])
        else:
            raise ValueError(f'unknown leaf-sigma semantics: {semantics}')
    return {
        'full_oracle_non_clifford': primitive_totals['ccx'],
        'primitive_totals': primitive_totals,
        'total_logical_qubits': logical_qubits_total,
        'phase_shell_hadamards': phase_shell_hadamards,
        'phase_shell_measurements': phase_shell_measurements,
        'phase_shell_rotations': phase_shell_rotations,
        'phase_shell_rotation_depth': phase_shell_rotation_depth,
    }


def build_resource_liveness_certificate(
    *,
    frontier: Mapping[str, Any],
    streamed_lookup_tail_slot_allocation: Mapping[str, Any],
    arithmetic_lowerings: Mapping[str, Any],
    streamed_lookup_resource: Mapping[str, Any],
    logical_resource_ledger: Mapping[str, Any],
    ft_ir_compositions: Mapping[str, Any],
    materialized_circuit_manifest: Mapping[str, Any],
    field_bits: int,
) -> Dict[str, Any]:
    selected = frontier['best_qubit_family']
    selected_ft_ir = _selected_family(ft_ir_compositions, selected['name'])
    leaf_sigma = _certificate_leaf_sigma(selected_ft_ir)
    leaf_sigma_reconstruction = _reconstruct_leaf_sigma(leaf_sigma)
    leaf_reconstruction = arithmetic_lowerings['leaf_reconstruction']
    kernel_lookup = {kernel['opcode']: kernel for kernel in arithmetic_lowerings['kernels']}
    tail_kernel = kernel_lookup['complete_a0_all_streamed_tail']
    qroam_model = streamed_lookup_resource['streamed_data_selection_model']
    qroam_workspace = streamed_lookup_resource['workspace_contract']
    qroam_cost = qroam_clean_stream_cost(
        int(qroam_model['folded_coordinate_domain_size']),
        int(qroam_model['qroam_target_bitsize']),
        int(qroam_model['qroam_block_size']),
    )
    owner_rows = logical_resource_ledger['peak_live_qubit_owners']
    owner_total = sum(int(owner['logical_qubits']) for owner in owner_rows)
    leaf_peak_arithmetic_slots = max(
        int(row['arithmetic_slots_needed_during_write'])
        for row in streamed_lookup_tail_slot_allocation['per_pc']
    )
    leaf_peak_control_slots = max(
        int(row['control_slots_needed_during_write'])
        for row in streamed_lookup_tail_slot_allocation['per_pc']
    )
    tail_leaf_sigma_rows = [
        row for row in leaf_sigma
        if row['resource_semantics'] == 'additive_primitive'
        and str(row['leaf_id']).startswith('arithmetic_opcode__complete_a0_all_streamed_tail__')
    ]
    tail_leaf_sigma_non_clifford = sum(
        int(row['primitive_counts_total']['ccx'])
        for row in tail_leaf_sigma_rows
    )
    leaf_call_count_total = int(qroam_model['leaf_call_count_total'])
    tail_macro_expected_non_clifford = int(tail_kernel['exact_non_clifford_per_kernel']) * leaf_call_count_total
    qroam_target_plus_junk = int(qroam_workspace['qroam_clean_target_plus_junk_qubits'])
    materialized_checks = materialized_circuit_manifest['reconstruction_checks']
    materialized_segment_count = int(materialized_circuit_manifest['segment_count'])
    materialized_segment_total = sum(
        int(segment['operation_count'])
        for segment in materialized_circuit_manifest['segments']
    )
    checks = {
        'selected_family_matches_frontier_best_qubit': selected['name'] == logical_resource_ledger['selected_family'],
        'leaf_peak_arithmetic_slots_derived_from_per_pc': leaf_peak_arithmetic_slots == int(selected['arithmetic_slot_count']),
        'leaf_peak_control_slots_derived_from_per_pc': leaf_peak_control_slots == int(selected['control_slot_count']),
        'leaf_arithmetic_qubits_match_field_width': int(selected['arithmetic_slot_count']) * int(field_bits) == int(
            streamed_lookup_tail_slot_allocation['allocator_summary']['arithmetic_bits']
        ),
        'owner_total_matches_selected_family': owner_total == int(selected['total_logical_qubits']),
        'owner_decompositions_are_numeric': all(
            int(owner['logical_qubits']) == int(owner['decomposition_total'])
            for owner in owner_rows
        ),
        'qroam_cost_matches_workspace_block_size': int(qroam_cost['target_plus_junk_qubits']) == qroam_target_plus_junk,
        'qroam_cost_matches_non_clifford_model': int(qroam_cost['per_stream_non_clifford']) == int(
            qroam_model['per_kernel_non_clifford']
        ),
        'qroam_workspace_is_counted_not_borrowed': (
            int(qroam_workspace['coordinate_field_lanes_materialized']) == 0
            and int(qroam_workspace['coordinate_field_lane_qubits_materialized']) == 0
            and int(qroam_workspace['standard_qroam_local_workspace_qubits']) == qroam_target_plus_junk
        ),
        'arithmetic_leaf_non_clifford_matches_lowering_reconstruction': int(
            leaf_reconstruction['arithmetic_leaf_non_clifford']
        ) == int(selected['arithmetic_leaf_non_clifford']),
        'tail_macro_has_explicit_internal_stage_inventory': (
            tail_kernel['opcode'] == 'complete_a0_all_streamed_tail'
            and int(tail_kernel['exact_non_clifford_per_kernel']) > 0
            and all('non_clifford_total' in stage for stage in tail_kernel['stages'])
        ),
        'ft_ir_leaf_sigma_reconstructs_selected_headline': (
            leaf_sigma_reconstruction['full_oracle_non_clifford'] == int(selected['full_oracle_non_clifford'])
            and leaf_sigma_reconstruction['total_logical_qubits'] == int(selected['total_logical_qubits'])
        ),
        'ft_ir_leaf_sigma_matches_generated_inventory': (
            leaf_sigma_reconstruction == selected_ft_ir['generated_block_inventory_reconstruction']
        ),
        'tail_macro_expanded_into_primitive_leaf_sigma_rows': (
            len(tail_leaf_sigma_rows) >= len(tail_kernel['stages'])
            and tail_leaf_sigma_non_clifford == tail_macro_expected_non_clifford
        ),
        'leaf_sigma_contains_no_macro_resource_tokens': all(
            row['resource_semantics'] in {
                'additive_primitive',
                'peak_live_qubits',
                'additive_phase_hadamards',
                'additive_phase_measurements',
                'additive_phase_rotations',
                'additive_phase_rotation_depth',
            }
            for row in leaf_sigma
        ),
        'materialized_operation_stream_reconstructs_selected_headline': (
            materialized_circuit_manifest['family'] == selected['name']
            and int(materialized_circuit_manifest['gate_totals']['ccx']) == int(selected['full_oracle_non_clifford'])
            and int(materialized_circuit_manifest['gate_totals']['measurement']) == int(selected['total_measurements'])
            and all(bool(value) for value in materialized_checks.values())
        ),
        'materialized_operation_stream_segments_cover_stream': (
            materialized_segment_count == len(materialized_circuit_manifest['segments'])
            and materialized_segment_total == int(materialized_circuit_manifest['operation_count'])
            and len(str(materialized_circuit_manifest['segment_merkle_root_sha256'])) == 64
        ),
    }
    return {
        'schema': 'compiler-project-resource-liveness-certificate-v2',
        'selected_family': selected['name'],
        'field_bits': int(field_bits),
        'source_artifacts': {
            'family_frontier': 'compiler_verification_project/artifacts/family_frontier.json',
            'streamed_lookup_tail_leaf_slot_allocation': 'compiler_verification_project/artifacts/streamed_lookup_tail_leaf_slot_allocation.json',
            'arithmetic_lowerings': 'compiler_verification_project/artifacts/arithmetic_lowerings.json',
            'streamed_lookup_table_multiplier_resource': 'compiler_verification_project/artifacts/streamed_lookup_table_multiplier_resource.json',
            'logical_resource_ledger': 'compiler_verification_project/artifacts/logical_resource_ledger.json',
            'ft_ir_compositions': 'compiler_verification_project/artifacts/ft_ir_compositions.json',
            'materialized_circuit_manifest': 'compiler_verification_project/artifacts/materialized_circuit_manifest.json',
        },
        'headline_totals': {
            'full_oracle_non_clifford': int(selected['full_oracle_non_clifford']),
            'total_logical_qubits': int(selected['total_logical_qubits']),
            'arithmetic_leaf_non_clifford': int(selected['arithmetic_leaf_non_clifford']),
            'per_leaf_lookup_non_clifford': int(selected['per_leaf_lookup_non_clifford']),
            'leaf_call_count_total': int(qroam_model['leaf_call_count_total']),
        },
        'primitive_oracle_ir': {
            'source_schema': ft_ir_compositions['schema'],
            'selected_family': selected_ft_ir['name'],
            'graph_summary': selected_ft_ir['graph']['summary'],
            'leaf_sigma_count': len(leaf_sigma),
            'leaf_sigma': leaf_sigma,
            'reconstruction_from_leaf_sigma': leaf_sigma_reconstruction,
            'generated_block_inventory_reconstruction': selected_ft_ir['generated_block_inventory_reconstruction'],
            'frontier_reconstruction': selected_ft_ir['frontier_reconstruction'],
            'tail_macro_rows': {
                'row_count': len(tail_leaf_sigma_rows),
                'whole_oracle_non_clifford': tail_leaf_sigma_non_clifford,
                'per_leaf_non_clifford': int(tail_kernel['exact_non_clifford_per_kernel']),
                'leaf_call_count_total': leaf_call_count_total,
            },
        },
        'flat_leaf_liveness': {
            'arithmetic_slots_from_schedule': leaf_peak_arithmetic_slots,
            'control_slots_from_schedule': leaf_peak_control_slots,
            'arithmetic_qubits_from_schedule': leaf_peak_arithmetic_slots * int(field_bits),
            'control_qubits_from_schedule': leaf_peak_control_slots,
            'borrowed_field_lanes': int(
                streamed_lookup_tail_slot_allocation['allocator_summary']['exact_borrowed_field_slot_count']
            ),
            'instruction_count': len(streamed_lookup_tail_slot_allocation['per_pc']),
            'per_pc': [
                {
                    'pc': int(row['pc']),
                    'opcode': row['opcode'],
                    'arithmetic_slots_needed_during_write': int(row['arithmetic_slots_needed_during_write']),
                    'control_slots_needed_during_write': int(row['control_slots_needed_during_write']),
                }
                for row in streamed_lookup_tail_slot_allocation['per_pc']
            ],
        },
        'qroam_workspace': {
            **qroam_cost,
            'folded_control_workspace_qubits': int(qroam_workspace['folded_control_workspace_qubits']),
            'lookup_workspace_qubits': int(qroam_workspace['lookup_workspace_qubits']),
            'coordinate_field_lanes_materialized': int(qroam_workspace['coordinate_field_lanes_materialized']),
            'coordinate_field_lane_qubits_materialized': int(qroam_workspace['coordinate_field_lane_qubits_materialized']),
            'whole_oracle_stream_count': int(streamed_lookup_resource['capacity_check']['whole_oracle_stream_count']),
        },
        'macro_lowering_inventory': {
            'opcode': tail_kernel['opcode'],
            'exact_non_clifford_per_kernel': int(tail_kernel['exact_non_clifford_per_kernel']),
            'stage_count': len(tail_kernel['stages']),
            'stages': [
                {
                    'name': stage['name'],
                    'category': stage['category'],
                    'non_clifford_total': int(stage['non_clifford_total']),
                    'block_count': len(stage['blocks']),
                }
                for stage in tail_kernel['stages']
            ],
        },
        'materialized_operation_stream': {
            'family': materialized_circuit_manifest['family'],
            'stream_encoding': materialized_circuit_manifest['stream_encoding'],
            'operation_stream_sha256': materialized_circuit_manifest['operation_stream_sha256'],
            'operation_count': int(materialized_circuit_manifest['operation_count']),
            'segment_size': int(materialized_circuit_manifest['segment_size']),
            'segment_count': materialized_segment_count,
            'segment_merkle_root_sha256': materialized_circuit_manifest['segment_merkle_root_sha256'],
            'gate_totals': materialized_circuit_manifest['gate_totals'],
            'reconstruction_checks': materialized_circuit_manifest['reconstruction_checks'],
        },
        'global_peak_owners': owner_rows,
        'global_peak_live_qubits': owner_total,
        'checks': checks,
        'pass': all(checks.values()),
        'notes': [
            'This certificate is the resource object bound by the ZKP input: it ties the executable leaf liveness, QROAM workspace, arithmetic lowering inventory, selected-family FT-IR leaf sigma, and global owner ledger to the selected headline.',
            'The primitive_oracle_ir section is intentionally a leaf-sigma certificate rather than a giant gate-list dump: every row carries multiplicity, primitive counts, and live-qubit totals that reconstruct the checked headline inside the SP1 guest.',
            'The materialized_operation_stream section binds the full generated operation stream by a whole-stream digest plus a segmented Merkle root, so large-stream drift can be audited without checking in the full TSV.',
        ],
    }


__all__ = ['build_resource_liveness_certificate']
