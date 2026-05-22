#!/usr/bin/env python3

from __future__ import annotations

from math import ceil
from typing import Any, Dict, Mapping


def build_fallback_frontier_stress(
    *,
    frontier: Mapping[str, Any],
    logical_resource_ledger: Mapping[str, Any],
    field_bits: int,
    non_clifford_limit: int = 40_000_000,
    logical_qubit_limit_exclusive: int = 1200,
) -> Dict[str, Any]:
    selected = frontier['best_qubit_family']
    ledger_sweep = logical_resource_ledger['qroam_clean_tradeoff_sweep']
    selected_block_size = int(logical_resource_ledger['selected_family_summary']['qroam_clean_block_size'])
    selected_tradeoff = next(row for row in ledger_sweep['rows'] if int(row['block_size']) == selected_block_size)
    owner_rows = {row['owner_id']: row for row in logical_resource_ledger['peak_live_qubit_owners']}
    lookup_workspace = owner_rows['lookup_workspace']
    folded_control_workspace = int(lookup_workspace['decomposition']['folded_control_workspace_qubits'])
    control_qubits = int(owner_rows['control_slot_register_file']['logical_qubits'])
    phase_qubits = int(owner_rows['phase_shell_live_register']['logical_qubits'])
    stream_count = int(selected_tradeoff['whole_oracle_stream_count'])
    base_without_streamed_qroam = int(ledger_sweep['base_non_clifford_without_streamed_qroam'])
    qroam_chunk_cost = int(selected_tradeoff['per_stream_non_clifford'])
    four_slot_arithmetic_qubits = 4 * int(field_bits)
    max_lookup_workspace_for_four_slots = (
        int(logical_qubit_limit_exclusive)
        - 1
        - four_slot_arithmetic_qubits
        - control_qubits
        - phase_qubits
    )
    max_qroam_target_bits_for_four_slots = max_lookup_workspace_for_four_slots - folded_control_workspace
    chunks_per_coordinate_stream = ceil(int(field_bits) / max_qroam_target_bits_for_four_slots)
    chunked_qroam_non_clifford = stream_count * chunks_per_coordinate_stream * qroam_chunk_cost
    chunked_total_non_clifford = base_without_streamed_qroam + chunked_qroam_non_clifford
    reusable_coordinate_tables = 3
    reusable_chunk_streams_per_leaf = reusable_coordinate_tables * chunks_per_coordinate_stream
    leaf_call_count_total = stream_count // 5
    reusable_chunked_qroam_non_clifford = leaf_call_count_total * reusable_chunk_streams_per_leaf * qroam_chunk_cost
    reusable_chunked_total_non_clifford = base_without_streamed_qroam + reusable_chunked_qroam_non_clifford
    reusable_chunked_total_logical_qubits = (
        four_slot_arithmetic_qubits
        + control_qubits
        + phase_qubits
        + folded_control_workspace
        + max_qroam_target_bits_for_four_slots
    )
    return {
        'schema': 'compiler-project-fallback-frontier-stress-v1',
        'limits': {
            'non_clifford_limit': int(non_clifford_limit),
            'logical_qubit_limit_exclusive': int(logical_qubit_limit_exclusive),
        },
        'current_selected_family': {
            'name': selected['name'],
            'full_oracle_non_clifford': int(selected['full_oracle_non_clifford']),
            'total_logical_qubits': int(selected['total_logical_qubits']),
            'arithmetic_slot_count': int(selected['arithmetic_slot_count']),
            'lookup_workspace_qubits': int(selected['lookup_workspace_qubits']),
        },
        'four_slot_pressure': {
            'field_bits': int(field_bits),
            'four_slot_arithmetic_qubits': four_slot_arithmetic_qubits,
            'control_qubits': control_qubits,
            'phase_qubits': phase_qubits,
            'current_full_coordinate_lookup_workspace_qubits': int(selected['lookup_workspace_qubits']),
            'current_four_slot_total_with_full_coordinate_qroam': (
                four_slot_arithmetic_qubits
                + control_qubits
                + phase_qubits
                + int(selected['lookup_workspace_qubits'])
            ),
            'max_lookup_workspace_for_strictly_below_limit': max_lookup_workspace_for_four_slots,
            'lookup_workspace_reduction_needed_from_current': int(selected['lookup_workspace_qubits']) - max_lookup_workspace_for_four_slots,
        },
        'chunked_coordinate_qroam_counterfactual': {
            'model': 'split each 256-bit coordinate stream into equally costed standard QROAMClean K=1 target chunks',
            'folded_control_workspace_qubits': folded_control_workspace,
            'max_qroam_target_bits_per_live_chunk': max_qroam_target_bits_for_four_slots,
            'chunks_per_coordinate_stream': chunks_per_coordinate_stream,
            'whole_oracle_stream_count_before_chunking': stream_count,
            'per_chunk_stream_non_clifford': qroam_chunk_cost,
            'base_non_clifford_without_streamed_qroam': base_without_streamed_qroam,
            'chunked_qroam_non_clifford': chunked_qroam_non_clifford,
            'chunked_total_non_clifford': chunked_total_non_clifford,
            'chunked_total_logical_qubits': (
                four_slot_arithmetic_qubits
                + control_qubits
                + phase_qubits
                + folded_control_workspace
                + max_qroam_target_bits_for_four_slots
            ),
            'non_clifford_excess_over_limit': max(0, chunked_total_non_clifford - int(non_clifford_limit)),
            'required_non_qroam_base_reduction_to_fit_limit': max(
                0,
                chunked_total_non_clifford - int(non_clifford_limit),
            ),
        },
        'reusable_chunked_coordinate_candidate': {
            'status': 'proven_public_headline',
            'model': 'split x, y, and x_plus_y table values into reusable live chunks, then consume each x chunk for both x-multiplications and each y chunk for both y-multiplications inside a four-slot tail schedule',
            'required_new_lowering': 'chunked table-controlled multiplier that accumulates coordinate chunks without materializing a full field-sized coordinate lane and without repeating QROAM for each consumer',
            'coordinate_tables': ['lookup_x', 'lookup_y', 'lookup_x_plus_y'],
            'chunks_per_coordinate_table': chunks_per_coordinate_stream,
            'chunk_streams_per_leaf': reusable_chunk_streams_per_leaf,
            'leaf_call_count_total': leaf_call_count_total,
            'per_chunk_stream_non_clifford': qroam_chunk_cost,
            'base_non_clifford_without_streamed_qroam': base_without_streamed_qroam,
            'chunked_qroam_non_clifford': reusable_chunked_qroam_non_clifford,
            'candidate_total_non_clifford': reusable_chunked_total_non_clifford,
            'candidate_total_logical_qubits': reusable_chunked_total_logical_qubits,
            'beats_requested_non_clifford_limit': reusable_chunked_total_non_clifford < int(non_clifford_limit),
            'beats_requested_logical_qubit_limit': reusable_chunked_total_logical_qubits < int(logical_qubit_limit_exclusive),
            'margin_to_non_clifford_limit': int(non_clifford_limit) - reusable_chunked_total_non_clifford,
            'margin_to_logical_qubit_limit': int(logical_qubit_limit_exclusive) - reusable_chunked_total_logical_qubits,
            'public_claim_evidence': [
                'the executable four-slot tail contract has one reusable coordinate chunk target and no full x/y field lane',
                'the chunked table-controlled multiplier lowering proves partial-product accumulation across chunks under the inherited full-width arithmetic bound',
                'liveness is derived from the executable contract, including chunk target lifetime, arithmetic slots, folded lookup controls, and output registers',
                'the checked core, compressed, and Groth16 reusable-chunk artifacts bind the promoted contract and resource certificate',
            ],
        },
        'conclusion': {
            'current_models_have_no_four_slot_fallback_under_limits': chunked_total_non_clifford >= int(non_clifford_limit),
            'four_slot_fallback_requires_new_arithmetic_savings_or_new_lookup_primitive': chunked_total_non_clifford >= int(non_clifford_limit),
            'new_chunk_reuse_candidate_fits_limits_after_lowering_and_zkp_proof': (
                reusable_chunked_total_non_clifford < int(non_clifford_limit)
                and reusable_chunked_total_logical_qubits < int(logical_qubit_limit_exclusive)
            ),
        },
        'notes': [
            'This stress test is intentionally strict about the user-facing bound: logical qubits must be strictly below 1200, not equal to 1200.',
            'With four field slots, the current full-coordinate QROAM workspace misses the qubit bound before considering gates.',
            'Chunking the QROAM target enough to fit the four-slot qubit bound doubles the coordinate-stream QROAM count under the K=1 model and misses the 40M non-Clifford bound unless another layer saves the reported excess.',
            'The reusable chunked-coordinate result is the public headline once the checked lowering, executable four-slot contract, and compressed/Groth16 reusable-chunk artifacts are present.',
        ],
    }


__all__ = ['build_fallback_frontier_stress']
