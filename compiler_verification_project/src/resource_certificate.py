#!/usr/bin/env python3

from __future__ import annotations

from typing import Any, Dict, Mapping

from resource_ledger import qroam_clean_stream_cost


def build_resource_liveness_certificate(
    *,
    frontier: Mapping[str, Any],
    streamed_lookup_tail_slot_allocation: Mapping[str, Any],
    arithmetic_lowerings: Mapping[str, Any],
    streamed_lookup_resource: Mapping[str, Any],
    logical_resource_ledger: Mapping[str, Any],
    field_bits: int,
) -> Dict[str, Any]:
    selected = frontier['best_qubit_family']
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
    qroam_target_plus_junk = int(qroam_workspace['qroam_clean_target_plus_junk_qubits'])
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
    }
    return {
        'schema': 'compiler-project-resource-liveness-certificate-v1',
        'selected_family': selected['name'],
        'field_bits': int(field_bits),
        'source_artifacts': {
            'family_frontier': 'compiler_verification_project/artifacts/family_frontier.json',
            'streamed_lookup_tail_leaf_slot_allocation': 'compiler_verification_project/artifacts/streamed_lookup_tail_leaf_slot_allocation.json',
            'arithmetic_lowerings': 'compiler_verification_project/artifacts/arithmetic_lowerings.json',
            'streamed_lookup_table_multiplier_resource': 'compiler_verification_project/artifacts/streamed_lookup_table_multiplier_resource.json',
            'logical_resource_ledger': 'compiler_verification_project/artifacts/logical_resource_ledger.json',
        },
        'headline_totals': {
            'full_oracle_non_clifford': int(selected['full_oracle_non_clifford']),
            'total_logical_qubits': int(selected['total_logical_qubits']),
            'arithmetic_leaf_non_clifford': int(selected['arithmetic_leaf_non_clifford']),
            'per_leaf_lookup_non_clifford': int(selected['per_leaf_lookup_non_clifford']),
            'leaf_call_count_total': int(qroam_model['leaf_call_count_total']),
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
        'global_peak_owners': owner_rows,
        'global_peak_live_qubits': owner_total,
        'checks': checks,
        'pass': all(checks.values()),
        'notes': [
            'This certificate is the compact resource object bound by the ZKP input: it ties the executable leaf liveness, QROAM workspace, arithmetic lowering inventory, and global owner ledger to the selected headline.',
            'It is intentionally smaller than the full primitive-operation artifacts, but all numeric capacity checks are derived from checked artifacts rather than prose-only accounting.',
        ],
    }


__all__ = ['build_resource_liveness_certificate']
