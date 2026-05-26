#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Mapping


MODULAR_ACCUMULATOR_SEMANTIC_OBLIGATIONS_SCHEMA = 'compiler-project-modular-accumulator-semantic-obligations-v2'


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def _sha256_payload(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode('ascii')).hexdigest()


def _owner_map(certificate: Mapping[str, Any]) -> Dict[str, Mapping[str, Any]]:
    return {
        str(row['owner_id']): row
        for row in certificate['owner_capacity_obligations']
    }


def build_modular_accumulator_semantic_obligations(
    *,
    modular_accumulator_row_stream: Mapping[str, Any],
    modular_accumulator_capacity_certificate: Mapping[str, Any],
    modular_accumulator_scratch_schedule: Mapping[str, Any],
    field_bits: int,
) -> Dict[str, Any]:
    field_bits = int(field_bits)
    expanded_counts = modular_accumulator_row_stream['expanded_counts']
    row_stream = modular_accumulator_row_stream['row_stream']
    role_counts = row_stream['role_counts']
    capacity_owners = _owner_map(modular_accumulator_capacity_certificate)
    schedule_stream = modular_accumulator_scratch_schedule['schedule_stream']
    partial_product_rows = int(expanded_counts['partial_product_consume_rows'])
    guard_rows = int(expanded_counts['zero_lift_guard_rows'])
    fold_rows = int(expanded_counts['pseudo_mersenne_fold_rows'])
    temporary_rows = int(expanded_counts['temporary_cleanup_rows'])
    low_fold_rows = int(role_counts['pseudo_mersenne_low_column_fold'])
    high_fold_rows = int(role_counts['pseudo_mersenne_high_column_fold'])
    consume_events = int(schedule_stream['phase_counts']['consume_into_counted_owner'])
    cleanup_events = int(schedule_stream['phase_counts']['cleanup_or_measure_uncompute'])
    product_capacity = capacity_owners['streamed_product_accumulator_column_space']
    fold_capacity = capacity_owners['streamed_modular_accumulator_field_lane']
    temporary_capacity = capacity_owners['temporary_and_target_wire']
    guard_capacity = capacity_owners['guard_ladder_predicate_workspace']
    obligation_classes = [
        {
            'name': 'partial_product_column_consume',
            'row_count': partial_product_rows,
            'route_kind': 'partial_product_column_to_streamed_modular_accumulator',
            'source_rows': 'modular_accumulator_row_stream.role_counts.partial_product_accumulator_consume',
            'required_semantics': 'reversible_update_product_column_from_single_temporary_and_then_uncompute_temporary',
            'required_owner': 'streamed_product_accumulator_column_space',
            'required_logical_qubit_capacity': int(product_capacity['logical_qubit_budget_required_by_materialized_columns']),
            'single_field_slot_shortcut_allowed': bool(product_capacity['fits_single_field_slot']),
            'semantic_gate_lowering_proven': False,
        },
        {
            'name': 'zero_lift_guard_consume',
            'row_count': guard_rows,
            'route_kind': 'zero_lift_guard_predicate_ladder',
            'source_rows': 'modular_accumulator_row_stream.expanded_counts.zero_lift_guard_rows',
            'required_semantics': 'reversible_update_guard_ladder_from_single_temporary_and_then_uncompute_temporary',
            'required_owner': 'guard_ladder_predicate_workspace',
            'required_serialized_peak_logical_qubits': int(guard_capacity['serialized_candidate_peak_logical_qubits']),
            'semantic_gate_lowering_proven': False,
        },
        {
            'name': 'pseudo_mersenne_low_column_fold',
            'row_count': low_fold_rows,
            'route_kind': 'pseudo_mersenne_fold',
            'source_rows': 'modular_accumulator_row_stream.role_counts.pseudo_mersenne_low_column_fold',
            'required_semantics': 'reversible_fold_low_shifted_product_column_into_field_lane',
            'required_owner': 'streamed_modular_accumulator_field_lane',
            'semantic_gate_lowering_proven': False,
        },
        {
            'name': 'pseudo_mersenne_high_column_fold',
            'row_count': high_fold_rows,
            'route_kind': 'pseudo_mersenne_fold',
            'source_rows': 'modular_accumulator_row_stream.role_counts.pseudo_mersenne_high_column_fold',
            'required_semantics': 'reversible_fold_high_shifted_product_column_with_second_fold_or_explicit_overflow_owner',
            'required_owner': 'streamed_modular_accumulator_field_lane',
            'overflowing_shift_column_count': int(fold_capacity['overflowing_shift_column_count']),
            'fits_single_field_slot_without_second_fold': bool(fold_capacity['fits_single_field_slot_without_second_fold']),
            'semantic_gate_lowering_proven': False,
        },
        {
            'name': 'temporary_cleanup_uncompute',
            'row_count': temporary_rows,
            'route_kind': 'adjacent_compute_consume_cleanup_triplet',
            'source_rows': 'modular_accumulator_scratch_schedule.phase_counts.cleanup_or_measure_uncompute',
            'required_semantics': 'cleanup_must_return_each_scratch_target_to_zero_after_counted_owner_update',
            'required_owner': 'temporary_and_target_wire',
            'obligation_order_peak_logical_qubits': int(temporary_capacity['obligation_order_peak_logical_qubits']),
            'serialized_candidate_peak_logical_qubits': int(temporary_capacity['serialized_candidate_peak_logical_qubits']),
            'semantic_gate_lowering_proven': False,
        },
    ]
    class_row_total = sum(int(row['row_count']) for row in obligation_classes)
    checks = {
        'source_row_stream_passes': modular_accumulator_row_stream['pass'] is True,
        'source_capacity_certificate_passes': modular_accumulator_capacity_certificate['pass'] is True,
        'source_scratch_schedule_passes': modular_accumulator_scratch_schedule['pass'] is True,
        'consume_events_cover_product_and_guard_rows': consume_events == partial_product_rows + guard_rows,
        'cleanup_events_cover_temporary_rows': cleanup_events == temporary_rows,
        'fold_classes_cover_all_fold_rows': low_fold_rows + high_fold_rows == fold_rows,
        'obligation_classes_cover_every_row_stream_row': class_row_total == int(row_stream['row_count']),
        'product_consume_rejects_single_field_slot_shortcut': obligation_classes[0]['single_field_slot_shortcut_allowed'] is False and obligation_classes[0]['required_logical_qubit_capacity'] == 2 * field_bits,
        'high_fold_overflow_is_explicit': obligation_classes[3]['overflowing_shift_column_count'] == 31 and obligation_classes[3]['fits_single_field_slot_without_second_fold'] is False,
        'temporary_cleanup_remains_semantically_unpromoted': obligation_classes[4]['serialized_candidate_peak_logical_qubits'] == 1 and all(row['semantic_gate_lowering_proven'] is False for row in obligation_classes),
    }
    return {
        'schema': MODULAR_ACCUMULATOR_SEMANTIC_OBLIGATIONS_SCHEMA,
        'definition': 'Generated semantic-obligation boundary for promoting the modular accumulator scratch schedule. It enumerates the reversible consume, fold, and cleanup semantics still required before the serialized liveness schedule can become the public physical resource contract.',
        'source_digests': {
            'modular_accumulator_row_stream_sha256': _sha256_payload(modular_accumulator_row_stream),
            'modular_accumulator_capacity_certificate_sha256': _sha256_payload(modular_accumulator_capacity_certificate),
            'modular_accumulator_scratch_schedule_sha256': _sha256_payload(modular_accumulator_scratch_schedule),
        },
        'field_bits': field_bits,
        'obligation_summary': {
            'row_stream_row_count': int(row_stream['row_count']),
            'consume_event_count': consume_events,
            'cleanup_event_count': cleanup_events,
            'partial_product_consume_rows': partial_product_rows,
            'zero_lift_guard_consume_rows': guard_rows,
            'pseudo_mersenne_fold_rows': fold_rows,
            'temporary_cleanup_rows': temporary_rows,
            'partial_product_column_count': int(product_capacity['partial_product_column_count']),
            'product_column_capacity_bits': int(product_capacity['logical_qubit_budget_required_by_materialized_columns']),
            'fold_overflow_column_count': int(fold_capacity['overflowing_shift_column_count']),
            'serialized_temporary_peak_logical_qubits': int(temporary_capacity['serialized_candidate_peak_logical_qubits']),
            'semantic_gate_lowering_proven': False,
        },
        'obligation_classes': obligation_classes,
        'promotion_status': {
            'status': 'semantic_obligations_not_promoted_to_public_resource_contract',
            'required_to_promote': [
                'Replace partial_product_column_consume obligations with concrete reversible product-column update gates.',
                'Replace zero_lift_guard_consume obligations with concrete reversible guard-ladder update gates.',
                'Replace pseudo-Mersenne fold obligations with concrete low/high column fold gates that either prove second-fold cleanup or count overflow capacity.',
                'Replace temporary_cleanup_uncompute obligations with concrete cleanup or measurement-uncompute gates whose side effects are included in the primitive stream.',
                'Rebuild public non-Clifford and peak-live-qubit totals from the promoted primitive gate stream.',
            ],
        },
        'checks': checks,
        'pass': all(checks.values()),
    }


__all__ = [
    'MODULAR_ACCUMULATOR_SEMANTIC_OBLIGATIONS_SCHEMA',
    'build_modular_accumulator_semantic_obligations',
]
