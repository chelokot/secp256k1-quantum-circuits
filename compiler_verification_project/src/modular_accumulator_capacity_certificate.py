#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Mapping

from arithmetic_lowering import SECP256K1_PSEUDO_MERSENNE_SHIFT


MODULAR_ACCUMULATOR_CAPACITY_CERTIFICATE_SCHEMA = 'compiler-project-modular-accumulator-capacity-certificate-v2'


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def _sha256_payload(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode('ascii')).hexdigest()


def build_modular_accumulator_capacity_certificate(
    *,
    modular_accumulator_row_stream: Mapping[str, Any],
    field_bits: int,
) -> Dict[str, Any]:
    row_stream = modular_accumulator_row_stream['row_stream']
    expanded = modular_accumulator_row_stream['expanded_counts']
    owner_counts = row_stream['capacity_owner_counts']
    field_bits = int(field_bits)
    partial_product_column_count = 2 * field_bits - 1
    carry_complete_product_capacity_bits = 2 * field_bits
    high_shifted_column_max = field_bits - 2 + SECP256K1_PSEUDO_MERSENNE_SHIFT
    overflowing_shift_column_count = max(0, high_shifted_column_max - (field_bits - 1))
    temporary_rows = int(expanded['temporary_cleanup_rows'])
    guard_rows = int(expanded['zero_lift_guard_rows'])
    owner_capacity_obligations = [
        {
            'owner_id': 'streamed_product_accumulator_column_space',
            'observed_rows': int(owner_counts['streamed_product_accumulator_column_space']),
            'partial_product_column_count': partial_product_column_count,
            'logical_qubit_budget_required_by_materialized_columns': carry_complete_product_capacity_bits,
            'field_slot_capacity_bits': field_bits,
            'fits_single_field_slot': False,
            'status': 'requires_streaming_or_dedicated_product_column_owner_before_promotion',
        },
        {
            'owner_id': 'streamed_modular_accumulator_field_lane',
            'observed_rows': int(owner_counts['streamed_modular_accumulator_field_lane']),
            'logical_qubit_budget_required_by_direct_shifted_columns': high_shifted_column_max + 1,
            'field_slot_capacity_bits': field_bits,
            'overflowing_shift_column_count': overflowing_shift_column_count,
            'fits_single_field_slot_without_second_fold': False,
            'status': 'requires_second_fold_or_overflow_column_owner_before_promotion',
        },
        {
            'owner_id': 'temporary_and_target_wire',
            'observed_rows': int(owner_counts['temporary_and_target_wire']),
            'obligation_order_peak_logical_qubits': temporary_rows,
            'serialized_candidate_peak_logical_qubits': 1 if temporary_rows else 0,
            'capacity_status': 'serialized_peak_unpromoted_until_compute_consume_cleanup_rows_are_adjacent_in_the_primitive_schedule',
        },
        {
            'owner_id': 'guard_ladder_predicate_workspace',
            'observed_rows': int(owner_counts['guard_ladder_predicate_workspace']),
            'obligation_order_peak_logical_qubits': guard_rows,
            'serialized_candidate_peak_logical_qubits': 1 if guard_rows else 0,
            'capacity_status': 'serialized_peak_unpromoted_until_guard_cleanup_rows_are_primitive_scheduled',
        },
    ]
    checks = {
        'source_row_stream_passes': modular_accumulator_row_stream['pass'] is True,
        'owner_counts_cover_all_rows': sum(int(value) for value in owner_counts.values()) == int(row_stream['row_count']),
        'product_column_owner_includes_final_carry_bit_and_exceeds_single_field_slot': (
            partial_product_column_count == int(row_stream['max_source_column']) + 1
            and carry_complete_product_capacity_bits == partial_product_column_count + 1
            and carry_complete_product_capacity_bits > field_bits
        ),
        'field_fold_overflow_columns_are_explicit': overflowing_shift_column_count == 31,
        'temporary_owner_capacity_is_not_free_in_obligation_order': temporary_rows == int(owner_counts['temporary_and_target_wire']),
        'serialized_temporary_peak_is_unpromoted': temporary_rows > 1,
        'capacity_certificate_not_promoted_to_public_resource_contract': True,
    }
    return {
        'schema': MODULAR_ACCUMULATOR_CAPACITY_CERTIFICATE_SCHEMA,
        'definition': 'Generated owner-capacity certificate for the modular accumulator row-stream obligations. It distinguishes materialized obligation-order capacity from unpromoted serialized candidates so temporary, product-column, final-carry, guard, and fold-overflow wires cannot be treated as free public resources.',
        'source_digests': {
            'modular_accumulator_row_stream_sha256': _sha256_payload(modular_accumulator_row_stream),
        },
        'field_bits': field_bits,
        'row_stream_summary': {
            'row_count': int(row_stream['row_count']),
            'operation_stream_sha256': str(row_stream['operation_stream_sha256']),
            'capacity_owner_counts': {
                key: int(value)
                for key, value in sorted(owner_counts.items())
            },
            'max_source_column': int(row_stream['max_source_column']),
            'max_destination_column': int(row_stream['max_destination_column']),
        },
        'owner_capacity_obligations': owner_capacity_obligations,
        'promotion_status': {
            'status': 'capacity_certificate_not_promoted_to_public_resource_contract',
            'required_to_promote': [
                'Replace obligation-order temporary rows with adjacent compute-consume-cleanup primitive rows or count the full obligation-order temporary peak.',
                'Lower product-column accumulation so the 511 product columns plus final carry bit are either streamed with proven non-concurrency or counted explicitly.',
                'Lower pseudo-Mersenne overflow columns through a second-fold primitive schedule or count the overflow owner explicitly.',
                'Recompute public peak liveness from the promoted primitive schedule rather than from this capacity certificate.',
            ],
        },
        'checks': checks,
        'pass': all(checks.values()),
    }


__all__ = [
    'MODULAR_ACCUMULATOR_CAPACITY_CERTIFICATE_SCHEMA',
    'build_modular_accumulator_capacity_certificate',
]
