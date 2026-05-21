#!/usr/bin/env python3

from __future__ import annotations

from typing import Any, Dict, List, Mapping

from resource_ledger import qroam_clean_stream_cost


def _owner(owner_id: str, logical_qubits: int, source: str, required: Mapping[str, int]) -> Dict[str, Any]:
    required_peak = sum(int(value) for value in required.values())
    return {
        'owner_id': owner_id,
        'logical_qubits': int(logical_qubits),
        'source': source,
        'required_live_wires': {key: int(value) for key, value in required.items()},
        'required_peak_qubits': required_peak,
        'capacity_margin_qubits': int(logical_qubits) - required_peak,
        'capacity_pass': int(logical_qubits) >= required_peak,
    }


def build_reusable_chunk_lowering(
    *,
    reusable_chunk_tail_candidate: Mapping[str, Any],
    fallback_frontier_stress: Mapping[str, Any],
    logical_resource_ledger: Mapping[str, Any],
    field_bits: int,
) -> Dict[str, Any]:
    candidate = reusable_chunk_tail_candidate['production_resource_candidate']
    executable_leaf = reusable_chunk_tail_candidate['executable_leaf_contract']
    stress_candidate = fallback_frontier_stress['reusable_chunked_coordinate_candidate']
    stress_chunking = fallback_frontier_stress['chunked_coordinate_qroam_counterfactual']
    ledger_sweep = logical_resource_ledger['qroam_clean_tradeoff_sweep']
    selected_owner_rows = {row['owner_id']: row for row in logical_resource_ledger['peak_live_qubit_owners']}
    lookup_workspace = selected_owner_rows['lookup_workspace']
    folded_control_qubits = int(lookup_workspace['decomposition']['folded_control_workspace_qubits'])
    control_qubits = int(selected_owner_rows['control_slot_register_file']['logical_qubits'])
    phase_qubits = int(selected_owner_rows['phase_shell_live_register']['logical_qubits'])
    chunk_bits = int(candidate['chunk_bits'])
    chunk_count = int(candidate['chunk_count'])
    leaf_call_count_total = int(candidate['leaf_call_count_total'])
    qroam_cost = qroam_clean_stream_cost(
        int(logical_resource_ledger['qroam_clean_tradeoff_sweep']['selected_row']['domain_size']),
        chunk_bits,
        1,
    )
    table_names = list(executable_leaf['lookup_constant_sources'])
    consumer_plan = reusable_chunk_tail_candidate['semantic_model']['consumer_plan']
    stream_rows: List[Dict[str, Any]] = []
    for table_name in table_names:
        consumers = list(consumer_plan[table_name])
        for chunk_index in range(chunk_count):
            stream_rows.append({
                'table': table_name,
                'chunk_index': chunk_index,
                'chunk_bits': chunk_bits,
                'consumers_before_uncompute': consumers,
                'consumer_count': len(consumers),
                'qroam_clean_block_size': 1,
                'qroam_compute_non_clifford': int(qroam_cost['lookup_compute_non_clifford']),
                'measured_uncompute_non_clifford': int(qroam_cost['measured_uncompute_non_clifford']),
                'per_chunk_stream_non_clifford': int(qroam_cost['per_stream_non_clifford']),
                'live_target_qubits': int(qroam_cost['target_register_qubits']),
                'junk_register_qubits': int(qroam_cost['junk_register_qubits']),
                'full_coordinate_lane_materialized': 0,
            })
    chunk_streams_per_leaf = len(stream_rows)
    whole_oracle_chunk_streams = leaf_call_count_total * chunk_streams_per_leaf
    qroam_non_clifford = whole_oracle_chunk_streams * int(qroam_cost['per_stream_non_clifford'])
    base_without_streamed_qroam = int(ledger_sweep['base_non_clifford_without_streamed_qroam'])
    total_non_clifford = base_without_streamed_qroam + qroam_non_clifford
    arithmetic_slot_count = len(executable_leaf['arithmetic_slots'])
    arithmetic_qubits = arithmetic_slot_count * int(field_bits)
    lookup_workspace_qubits = folded_control_qubits + int(qroam_cost['target_plus_junk_qubits'])
    total_logical_qubits = arithmetic_qubits + control_qubits + phase_qubits + lookup_workspace_qubits
    owners = [
        _owner(
            'arithmetic_slot_register_file',
            arithmetic_qubits,
            'compiler_verification_project/artifacts/reusable_chunk_tail_candidate.json',
            {slot: int(field_bits) for slot in executable_leaf['arithmetic_slots']},
        ),
        _owner(
            'lookup_workspace',
            lookup_workspace_qubits,
            'compiler_verification_project/artifacts/reusable_chunk_lowering.json',
            {
                'folded_control_workspace_qubits': folded_control_qubits,
                'qroam_clean_chunk_target_qubits': int(qroam_cost['target_register_qubits']),
                'qroam_clean_junk_register_qubits': int(qroam_cost['junk_register_qubits']),
            },
        ),
        _owner(
            'control_slot_register_file',
            control_qubits,
            'compiler_verification_project/artifacts/reusable_chunk_tail_candidate.json',
            {slot: 1 for slot in executable_leaf['control_slots']},
        ),
        _owner(
            'phase_shell_live_register',
            phase_qubits,
            'compiler_verification_project/artifacts/phase_shell_lowerings.json',
            {'semiclassical_qft_live_phase_bit': phase_qubits},
        ),
    ]
    owner_required_total = sum(int(owner['required_peak_qubits']) for owner in owners)
    owner_capacity_total = sum(int(owner['logical_qubits']) for owner in owners)
    checks = {
        'executable_leaf_uses_four_arithmetic_slots': arithmetic_slot_count == 4,
        'executable_leaf_has_reusable_chunk_scratch': executable_leaf['chunk_contract']['reusable_chunk_slot'] in executable_leaf['arithmetic_slots'],
        'no_full_coordinate_lanes_materialized': int(executable_leaf['chunk_contract']['full_coordinate_lanes_materialized']) == 0 and all(int(row['full_coordinate_lane_materialized']) == 0 for row in stream_rows),
        'chunk_width_matches_strict_qubit_pressure': chunk_bits == int(stress_chunking['max_qroam_target_bits_per_live_chunk']),
        'stream_count_derived_from_tables_and_chunks': chunk_streams_per_leaf == len(table_names) * chunk_count == int(candidate['chunk_streams_per_leaf']),
        'whole_oracle_stream_count_derived_from_leaf_calls': whole_oracle_chunk_streams == leaf_call_count_total * chunk_streams_per_leaf,
        'per_stream_cost_matches_standard_qroamclean_k1': int(qroam_cost['per_stream_non_clifford']) == int(stress_candidate['per_chunk_stream_non_clifford']),
        'non_clifford_matches_candidate': total_non_clifford == int(candidate['candidate_total_non_clifford']) == int(stress_candidate['candidate_total_non_clifford']),
        'logical_qubits_match_candidate': total_logical_qubits == int(candidate['candidate_total_logical_qubits']) == int(stress_candidate['candidate_total_logical_qubits']),
        'owner_capacity_rows_cover_required_peak': owner_required_total <= owner_capacity_total == total_logical_qubits and all(bool(owner['capacity_pass']) for owner in owners),
        'fits_requested_limits': total_non_clifford < 40_000_000 and total_logical_qubits < 1200,
    }
    return {
        'schema': 'compiler-project-reusable-chunk-lowering-v1',
        'status': 'candidate_lowering_contract_unproven_not_headline',
        'source_artifacts': {
            'reusable_chunk_tail_candidate': 'compiler_verification_project/artifacts/reusable_chunk_tail_candidate.json',
            'fallback_frontier_stress': 'compiler_verification_project/artifacts/fallback_frontier_stress.json',
            'logical_resource_ledger': 'compiler_verification_project/artifacts/logical_resource_ledger.json',
        },
        'executable_contract': {
            'variant': executable_leaf['variant'],
            'opcode': executable_leaf['instructions'][-1]['op'],
            'arithmetic_slots': list(executable_leaf['arithmetic_slots']),
            'control_slots': list(executable_leaf['control_slots']),
            'chunk_contract': dict(executable_leaf['chunk_contract']),
            'lookup_constant_sources': table_names,
        },
        'stream_plan': {
            'coordinate_table_count': len(table_names),
            'coordinate_tables': table_names,
            'chunk_bits': chunk_bits,
            'chunk_count': chunk_count,
            'chunk_streams_per_leaf': chunk_streams_per_leaf,
            'leaf_call_count_total': leaf_call_count_total,
            'whole_oracle_chunk_streams': whole_oracle_chunk_streams,
            'rows': stream_rows,
        },
        'standard_qroamclean_k1_model': qroam_cost,
        'non_clifford_derivation': {
            'base_non_clifford_without_streamed_qroam': base_without_streamed_qroam,
            'qroam_chunk_streams': whole_oracle_chunk_streams,
            'per_chunk_stream_non_clifford': int(qroam_cost['per_stream_non_clifford']),
            'qroam_chunk_non_clifford': qroam_non_clifford,
            'candidate_total_non_clifford': total_non_clifford,
        },
        'qubit_derivation': {
            'field_bits': int(field_bits),
            'arithmetic_slot_count': arithmetic_slot_count,
            'arithmetic_slot_qubits': arithmetic_qubits,
            'folded_control_workspace_qubits': folded_control_qubits,
            'qroam_clean_chunk_target_qubits': int(qroam_cost['target_register_qubits']),
            'qroam_clean_junk_register_qubits': int(qroam_cost['junk_register_qubits']),
            'lookup_workspace_qubits': lookup_workspace_qubits,
            'control_qubits': control_qubits,
            'phase_qubits': phase_qubits,
            'candidate_total_logical_qubits': total_logical_qubits,
        },
        'owner_capacity': {
            'rows': owners,
            'required_global_peak_qubits': owner_required_total,
            'capacity_global_peak_qubits': owner_capacity_total,
        },
        'checks': checks,
        'pass': all(checks.values()),
        'remaining_proof_obligations': [
            'Replace the inherited field-multiplication arithmetic base with generated chunked multiplier primitive blocks, or prove the inherited base is a conservative upper bound for this chunked contract.',
            'Bind this contract and its owner-capacity certificate in the ZKP before changing public headline values.',
            'Promote the candidate only after compressed and Groth16 verification pass from checked-in branch artifacts.',
        ],
        'notes': [
            'This artifact prevents the previous QROAMClean width/workspace mix-up for the reusable chunk candidate: K=1 uses a 155-bit live target and zero junk registers, so the same model drives gates and qubits.',
            'The three coordinate tables are streamed as chunks and consumed before uncompute; no full x, y, or x_plus_y coordinate lane is allocated.',
            'The result remains non-headline because the primitive chunked multiplier lowering and ZKP binding are not complete.',
        ],
    }


__all__ = ['build_reusable_chunk_lowering']
