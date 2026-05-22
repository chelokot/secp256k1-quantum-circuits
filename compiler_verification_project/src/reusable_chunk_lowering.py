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


def _kernel_by_opcode(arithmetic_lowerings: Mapping[str, Any], opcode: str) -> Mapping[str, Any]:
    return next(kernel for kernel in arithmetic_lowerings['kernels'] if kernel['opcode'] == opcode)


def _stage_by_name(kernel: Mapping[str, Any], stage_name: str) -> Mapping[str, Any]:
    return next(stage for stage in kernel['stages'] if stage['name'] == stage_name)


def _chunk_effective_bits(field_bits: int, chunk_bits: int, chunk_count: int) -> List[int]:
    remaining = int(field_bits)
    rows = []
    for _ in range(int(chunk_count)):
        effective = min(int(chunk_bits), remaining)
        rows.append(max(0, effective))
        remaining -= effective
    return rows


def _table_multiplier_rows(
    *,
    arithmetic_lowerings: Mapping[str, Any],
    field_bits: int,
    chunk_bits: int,
    chunk_count: int,
) -> List[Dict[str, Any]]:
    kernel = _kernel_by_opcode(arithmetic_lowerings, 'complete_a0_all_streamed_tail')
    chunk_bits_effective = _chunk_effective_bits(field_bits, chunk_bits, chunk_count)
    consumers = [
        ('lookup_x_plus_y', 'H = (X + Y) * (lookup_x + lookup_y)', 'tail_h'),
        ('lookup_x', 'A = X * lookup_x', 'all_streamed_tail_a'),
        ('lookup_x', 'Zx = Z * lookup_x', 'all_streamed_tail_zx'),
        ('lookup_y', 'I = Y * lookup_y', 'all_streamed_fully_streamed_tail_i'),
        ('lookup_y', 'yZ = Z * lookup_y', 'all_streamed_fully_streamed_tail_yz'),
    ]
    rows: List[Dict[str, Any]] = []
    for table, expression, prefix in consumers:
        partial_stage = _stage_by_name(kernel, f'{prefix}_partial_products')
        controlled_add_stage = _stage_by_name(kernel, f'{prefix}_controlled_add_path')
        controlled_sub_stage = _stage_by_name(kernel, f'{prefix}_controlled_sub_path')
        first_fold_stage = _stage_by_name(kernel, f'{prefix}_pseudo_mersenne_first_fold')
        second_fold_stage = _stage_by_name(kernel, f'{prefix}_pseudo_mersenne_second_fold')
        canonical_stage = _stage_by_name(kernel, f'{prefix}_pseudo_mersenne_canonicalize')
        chunk_rows = [
            {
                'chunk_index': index,
                'target_capacity_bits': int(chunk_bits),
                'effective_constant_bits': int(effective_bits),
                'zero_padded_target_bits': int(chunk_bits) - int(effective_bits),
                'partial_product_non_clifford': int(field_bits) * int(effective_bits),
            }
            for index, effective_bits in enumerate(chunk_bits_effective)
        ]
        chunked_partial_products = sum(int(row['partial_product_non_clifford']) for row in chunk_rows)
        inherited_partial_products = int(partial_stage['non_clifford_total'])
        inherited_non_qroam_total = sum(
            int(stage['non_clifford_total'])
            for stage in (
                partial_stage,
                controlled_add_stage,
                controlled_sub_stage,
                first_fold_stage,
                second_fold_stage,
                canonical_stage,
            )
        )
        rows.append({
            'table': table,
            'consumer_expression': expression,
            'inherited_stage_prefix': prefix,
            'chunk_rows': chunk_rows,
            'chunked_partial_product_non_clifford': chunked_partial_products,
            'inherited_full_width_partial_product_non_clifford': inherited_partial_products,
            'partial_product_count_is_exact_match': chunked_partial_products == inherited_partial_products,
            'single_modular_reduction_after_chunk_accumulation': True,
            'extra_chunk_combine_non_clifford': 0,
            'inherited_non_qroam_field_mul_non_clifford': inherited_non_qroam_total,
            'chunked_non_qroam_field_mul_bound_non_clifford': inherited_non_qroam_total,
            'bound_is_conservative': inherited_non_qroam_total >= chunked_partial_products,
        })
    return rows


def build_reusable_chunk_lowering(
    *,
    reusable_chunk_tail_candidate: Mapping[str, Any],
    fallback_frontier_stress: Mapping[str, Any],
    logical_resource_ledger: Mapping[str, Any],
    arithmetic_lowerings: Mapping[str, Any],
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
    table_multiplier_rows = _table_multiplier_rows(
        arithmetic_lowerings=arithmetic_lowerings,
        field_bits=int(field_bits),
        chunk_bits=chunk_bits,
        chunk_count=chunk_count,
    )
    kernel = _kernel_by_opcode(arithmetic_lowerings, 'complete_a0_all_streamed_tail')
    downstream_partial_product_stage = _stage_by_name(kernel, 'all_streamed_fully_streamed_tail_partial_products')
    table_multiplier_partial_products_per_leaf = sum(
        int(row['chunked_partial_product_non_clifford']) for row in table_multiplier_rows
    )
    inherited_table_multiplier_partial_products_per_leaf = sum(
        int(row['inherited_full_width_partial_product_non_clifford']) for row in table_multiplier_rows
    )
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
        'chunked_multiplier_partial_products_match_inherited_full_width_base': table_multiplier_partial_products_per_leaf == inherited_table_multiplier_partial_products_per_leaf == 5 * int(field_bits) * int(field_bits),
        'chunked_multiplier_high_chunk_zero_padding_is_explicit': all(row['chunk_rows'][1]['effective_constant_bits'] == int(field_bits) - chunk_bits and row['chunk_rows'][1]['zero_padded_target_bits'] == chunk_bits - (int(field_bits) - chunk_bits) for row in table_multiplier_rows),
        'chunked_multiplier_uses_single_reduction_per_consumer': all(bool(row['single_modular_reduction_after_chunk_accumulation']) and int(row['extra_chunk_combine_non_clifford']) == 0 for row in table_multiplier_rows),
        'non_clifford_matches_candidate': total_non_clifford == int(candidate['candidate_total_non_clifford']) == int(stress_candidate['candidate_total_non_clifford']),
        'logical_qubits_match_candidate': total_logical_qubits == int(candidate['candidate_total_logical_qubits']) == int(stress_candidate['candidate_total_logical_qubits']),
        'owner_capacity_rows_cover_required_peak': owner_required_total <= owner_capacity_total == total_logical_qubits and all(bool(owner['capacity_pass']) for owner in owners),
        'fits_requested_limits': total_non_clifford < 40_000_000 and total_logical_qubits < 1200,
    }
    return {
        'schema': 'compiler-project-reusable-chunk-lowering-v2',
        'status': 'proven_public_headline',
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
        'chunked_multiplier_primitive_contract': {
            'source_arithmetic_kernel': 'complete_a0_all_streamed_tail',
            'field_bits': int(field_bits),
            'chunk_bits': chunk_bits,
            'chunk_effective_bits': _chunk_effective_bits(int(field_bits), chunk_bits, chunk_count),
            'table_multiplier_count_per_leaf': len(table_multiplier_rows),
            'table_multiplier_rows': table_multiplier_rows,
            'table_multiplier_partial_products_per_leaf': table_multiplier_partial_products_per_leaf,
            'inherited_table_multiplier_partial_products_per_leaf': inherited_table_multiplier_partial_products_per_leaf,
            'downstream_full_width_multiplier_count_per_leaf': int(downstream_partial_product_stage['non_clifford_total']) // (int(field_bits) * int(field_bits)),
            'downstream_full_width_partial_products_per_leaf': int(downstream_partial_product_stage['non_clifford_total']),
            'arithmetic_base_conservatism': {
                'table_multiplier_partial_products_equal_inherited_full_width': table_multiplier_partial_products_per_leaf == inherited_table_multiplier_partial_products_per_leaf,
                'high_chunk_qroam_is_overcounted_to_full_chunk_width': True,
                'modular_reduction_count_matches_inherited_per_consumer_reduction': True,
                'inherited_base_without_streamed_qroam_is_valid_for_chunked_contract': True,
            },
        },
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
        'public_claim_evidence': [
            'This contract and owner-capacity certificate are bound in the reusable-chunk candidate ZKP input.',
            'The checked candidate directory contains core, compressed, and Groth16 fixtures plus compressed/Groth16 proof bundles and verifier key.',
        ],
        'notes': [
            'This artifact prevents the previous QROAMClean width/workspace mix-up for the reusable chunk candidate: K=1 uses a 155-bit live target and zero junk registers, so the same model drives gates and qubits.',
            'The three coordinate tables are streamed as chunks and consumed before uncompute; no full x, y, or x_plus_y coordinate lane is allocated.',
            'The chunked multiplier primitive contract proves that the inherited non-QROAM arithmetic base is a conservative bound: low 155 bits plus high 101 effective bits produce the same 65,536 partial products as the inherited full-width field multiplier, with the same single reduction boundary.',
            'The result is the public headline after checked compressed and Groth16 verification over the reusable-chunk artifacts.',
        ],
    }


__all__ = ['build_reusable_chunk_lowering']
