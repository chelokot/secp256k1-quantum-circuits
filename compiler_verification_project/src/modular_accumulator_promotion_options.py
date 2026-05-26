#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Mapping

from modular_accumulator_full_adder_liveness import FULL_ADDER_LIVENESS_UNPROMOTED_STATUS
from modular_accumulator_full_adder_reversibility import FULL_ADDER_REVERSIBILITY_UNPROMOTED_STATUS


MODULAR_ACCUMULATOR_PROMOTION_OPTIONS_SCHEMA = 'compiler-project-modular-accumulator-promotion-options-v1'
PROMOTION_OPTIONS_UNPROMOTED_STATUS = 'promotion_options_not_promoted_to_global_resource_contract'
OPTION_CURRENT_SYNTHETIC_SCRATCH = 'current_synthetic_scratch_placeholder'
OPTION_FORWARD_ONLY_CARRY_SAVE = 'forward_only_reversible_carry_save'
OPTION_LOCAL_TWO_BIT_WITNESS = 'local_two_bit_witness_carry_save'
OPTION_LOCAL_ONE_BIT_WITNESS = 'local_one_bit_witness_carry_save'
OPTION_SOURCE_UNCOMPUTE = 'source_uncompute_or_streaming_multiply_add'
STATUS_INVALID_RESOURCE_CONTRACT = 'invalid_not_a_physical_resource_contract'
STATUS_REJECTED_HEADLINE_QUBITS = 'rejected_exceeds_current_qubit_headline'
STATUS_REJECTED_NON_INJECTIVE = 'rejected_non_injective'
STATUS_ONLY_REMAINING_UNPROVEN = 'only_remaining_candidate_not_yet_proven'


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def _sha256_payload(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode('ascii')).hexdigest()


def build_modular_accumulator_promotion_options(
    *,
    primary_strict_result: Mapping[str, Any],
    modular_primitive_wire_audit: Mapping[str, Any],
    modular_accumulator_full_adder_liveness: Mapping[str, Any],
    modular_accumulator_full_adder_reversibility: Mapping[str, Any],
) -> Dict[str, Any]:
    current_qubit_headline = int(primary_strict_result['selected_result']['logical_qubits'])
    current_non_clifford_headline = int(primary_strict_result['selected_result']['non_clifford'])
    synthetic_scratch_wires = int(modular_primitive_wire_audit['arithmetic_scratch_wire_observation_count'])
    abandoned_scratch_wires = int(modular_primitive_wire_audit['arithmetic_scratch_abandoned_garbage_count'])
    first_grid = modular_accumulator_full_adder_liveness['per_grid'][0]
    witness_bits_per_cell = int(modular_accumulator_full_adder_reversibility['minimum_witness_bits_per_cell'])
    local_witness_sequential_bits = int(first_grid['full_adder_cells']) * witness_bits_per_cell
    local_witness_all_grid_bits = int(modular_accumulator_full_adder_reversibility['minimum_witness_bits_total'])
    optimistic_consumed_peak = int(modular_accumulator_full_adder_liveness['optimistic_consumed_lower_bound']['sequential_grid_peak_live_wires'])
    local_witness_sequential_peak_lower_bound = optimistic_consumed_peak + local_witness_sequential_bits
    forward_only_peak = int(modular_accumulator_full_adder_liveness['forward_only']['sequential_grid_peak_live_wires'])
    option_rows = [
        {
            'name': OPTION_CURRENT_SYNTHETIC_SCRATCH,
            'status': STATUS_INVALID_RESOURCE_CONTRACT,
            'peak_live_wire_lower_bound': None,
            'non_clifford_delta_lower_bound': 0,
            'reason': 'scheduled modular primitive rows still contain abandoned arithmetic_scratch targets with no cleanup or counted owner capacity',
            'can_promote': False,
        },
        {
            'name': OPTION_FORWARD_ONLY_CARRY_SAVE,
            'status': STATUS_REJECTED_HEADLINE_QUBITS,
            'peak_live_wire_lower_bound': forward_only_peak,
            'non_clifford_delta_lower_bound': int(modular_accumulator_full_adder_liveness['primitive_counts_total']['ccx']),
            'reason': 'retaining every full-adder input makes the sequential-grid peak far above the current public qubit headline',
            'can_promote': False,
        },
        {
            'name': OPTION_LOCAL_TWO_BIT_WITNESS,
            'status': STATUS_REJECTED_HEADLINE_QUBITS,
            'peak_live_wire_lower_bound': local_witness_sequential_peak_lower_bound,
            'non_clifford_delta_lower_bound': int(modular_accumulator_full_adder_liveness['primitive_counts_total']['ccx']),
            'reason': 'local injective sum/carry embedding needs at least two witness bits per cell, still far above the current public qubit headline',
            'can_promote': False,
        },
        {
            'name': OPTION_LOCAL_ONE_BIT_WITNESS,
            'status': STATUS_REJECTED_NON_INJECTIVE,
            'peak_live_wire_lower_bound': None,
            'non_clifford_delta_lower_bound': None,
            'reason': 'exhaustive search finds no one-bit witness function that separates all full-adder preimages',
            'can_promote': False,
        },
        {
            'name': OPTION_SOURCE_UNCOMPUTE,
            'status': STATUS_ONLY_REMAINING_UNPROVEN,
            'peak_live_wire_lower_bound': None,
            'non_clifford_delta_lower_bound': None,
            'reason': 'must avoid retaining local full-adder inputs or witnesses by giving a concrete reversible source-uncompute or streaming multiply-add schedule',
            'can_promote': False,
        },
    ]
    checks = {
        'primary_strict_result_passes': primary_strict_result['pass'] is True,
        'full_adder_liveness_passes': modular_accumulator_full_adder_liveness['pass'] is True,
        'full_adder_liveness_is_unpromoted': modular_accumulator_full_adder_liveness['promotion_status']['status'] == FULL_ADDER_LIVENESS_UNPROMOTED_STATUS,
        'full_adder_reversibility_passes': modular_accumulator_full_adder_reversibility['pass'] is True,
        'full_adder_reversibility_is_unpromoted': modular_accumulator_full_adder_reversibility['promotion_status']['status'] == FULL_ADDER_REVERSIBILITY_UNPROMOTED_STATUS,
        'synthetic_scratch_placeholder_is_active': synthetic_scratch_wires > 0 and abandoned_scratch_wires == synthetic_scratch_wires,
        'forward_only_option_exceeds_headline_qubits': forward_only_peak > current_qubit_headline,
        'local_two_bit_witness_option_exceeds_headline_qubits': local_witness_sequential_peak_lower_bound > current_qubit_headline,
        'one_bit_witness_option_is_rejected': int(modular_accumulator_full_adder_reversibility['one_bit_witness_exhaustive_search']['collision_free_function_count']) == 0,
        'source_uncompute_or_streaming_is_only_remaining_candidate': [row['name'] for row in option_rows if row['status'] == STATUS_ONLY_REMAINING_UNPROVEN] == [OPTION_SOURCE_UNCOMPUTE],
        'no_option_is_promoted_to_global_contract': all(row['can_promote'] is False for row in option_rows),
    }
    return {
        'schema': MODULAR_ACCUMULATOR_PROMOTION_OPTIONS_SCHEMA,
        'definition': 'Promotion-options audit for replacing synthetic modular-accumulator scratch with a physical reversible primitive schedule. The artifact rejects placeholder scratch, forward-only carry-save, local one-bit witnesses, and local two-bit witnesses under the current headline; source-uncompute or streaming multiply-add remains the required next construction, not a promoted result.',
        'source_digests': {
            'primary_strict_result_sha256': _sha256_payload(primary_strict_result),
            'modular_primitive_wire_audit_sha256': _sha256_payload(modular_primitive_wire_audit),
            'modular_accumulator_full_adder_liveness_sha256': _sha256_payload(modular_accumulator_full_adder_liveness),
            'modular_accumulator_full_adder_reversibility_sha256': _sha256_payload(modular_accumulator_full_adder_reversibility),
        },
        'current_public_headline': {
            'logical_qubits': current_qubit_headline,
            'non_clifford': current_non_clifford_headline,
        },
        'scratch_placeholder': {
            'synthetic_scratch_wire_observations': synthetic_scratch_wires,
            'abandoned_scratch_wire_observations': abandoned_scratch_wires,
        },
        'carry_save_local_bounds': {
            'forward_only_sequential_peak_live_wires': forward_only_peak,
            'optimistic_consumed_sequential_peak_live_wires': optimistic_consumed_peak,
            'minimum_witness_bits_per_cell': witness_bits_per_cell,
            'local_witness_sequential_bits': local_witness_sequential_bits,
            'local_witness_all_grid_bits': local_witness_all_grid_bits,
            'local_witness_sequential_peak_lower_bound': local_witness_sequential_peak_lower_bound,
        },
        'options': option_rows,
        'promotion_status': {
            'status': PROMOTION_OPTIONS_UNPROMOTED_STATUS,
            'required_to_promote': [
                'Construct source-uncompute or streaming multiply-add rows that replace arithmetic_scratch placeholders without local retained-input or witness blow-up.',
                'Assign the resulting wires to counted owners in the global liveness engine.',
                'Recompute public qubits and non-Clifford from the promoted primitive stream before changing the headline.',
            ],
        },
        'checks': checks,
        'pass': all(checks.values()),
    }


__all__ = [
    'MODULAR_ACCUMULATOR_PROMOTION_OPTIONS_SCHEMA',
    'OPTION_CURRENT_SYNTHETIC_SCRATCH',
    'OPTION_FORWARD_ONLY_CARRY_SAVE',
    'OPTION_LOCAL_ONE_BIT_WITNESS',
    'OPTION_LOCAL_TWO_BIT_WITNESS',
    'OPTION_SOURCE_UNCOMPUTE',
    'PROMOTION_OPTIONS_UNPROMOTED_STATUS',
    'STATUS_INVALID_RESOURCE_CONTRACT',
    'STATUS_ONLY_REMAINING_UNPROVEN',
    'STATUS_REJECTED_HEADLINE_QUBITS',
    'STATUS_REJECTED_NON_INJECTIVE',
    'build_modular_accumulator_promotion_options',
]
