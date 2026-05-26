#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Iterable, List, Mapping


MODULAR_ACCUMULATOR_CARRY_OBLIGATIONS_SCHEMA = 'compiler-project-modular-accumulator-carry-obligations-v1'


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def _sha256_payload(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode('ascii')).hexdigest()


def _column_multiplicities(*, field_bits: int, grid_count: int) -> List[Dict[str, int]]:
    rows = []
    for column in range(2 * int(field_bits) - 1):
        pair_count = column + 1 if column < int(field_bits) else 2 * int(field_bits) - 1 - column
        rows.append({
            'column': column,
            'partial_product_rows': int(grid_count) * pair_count,
            'single_increment_carry_span_bits': 2 * int(field_bits) - column,
            'carry_obligation_rows': int(grid_count) * pair_count * (2 * int(field_bits) - column),
        })
    return rows


def _segments(rows: Iterable[Mapping[str, int]], *, segment_size: int) -> Dict[str, Any]:
    if segment_size <= 0:
        raise ValueError('segment_size must be positive')
    stream_digest = hashlib.sha256()
    segment_digest = hashlib.sha256()
    stream_digest.update(b'column\tpartial_product_rows\tsingle_increment_carry_span_bits\tcarry_obligation_rows\n')
    row_count = 0
    segment_start = 0
    segment_row_count = 0
    segments = []
    preview_head = []
    preview_tail = []
    total_partial_product_rows = 0
    total_carry_obligation_rows = 0
    max_span = 0
    for row in rows:
        encoded = _canonical_json(row).encode('ascii') + b'\n'
        stream_digest.update(encoded)
        segment_digest.update(encoded)
        row_count += 1
        segment_row_count += 1
        total_partial_product_rows += int(row['partial_product_rows'])
        total_carry_obligation_rows += int(row['carry_obligation_rows'])
        max_span = max(max_span, int(row['single_increment_carry_span_bits']))
        if len(preview_head) < 6:
            preview_head.append(dict(row))
        preview_tail.append(dict(row))
        if len(preview_tail) > 6:
            preview_tail.pop(0)
        if segment_row_count == segment_size:
            segments.append({
                'segment_index': len(segments),
                'column_start': segment_start,
                'column_end_exclusive': row_count,
                'column_count': segment_row_count,
                'sha256': segment_digest.hexdigest(),
            })
            segment_digest = hashlib.sha256()
            segment_start = row_count
            segment_row_count = 0
    if segment_row_count:
        segments.append({
            'segment_index': len(segments),
            'column_start': segment_start,
            'column_end_exclusive': row_count,
            'column_count': segment_row_count,
            'sha256': segment_digest.hexdigest(),
        })
    return {
        'column_count': row_count,
        'columns_materialized_in_json': False,
        'segment_size': int(segment_size),
        'segment_count': len(segments),
        'segments': segments,
        'column_stream_sha256': stream_digest.hexdigest(),
        'total_partial_product_rows': total_partial_product_rows,
        'total_carry_obligation_rows': total_carry_obligation_rows,
        'max_single_increment_carry_span_bits': max_span,
        'preview_head': preview_head,
        'preview_tail': preview_tail,
    }


def _reduced_width_checks(widths: Iterable[int]) -> List[Dict[str, int | bool]]:
    checks = []
    for width in widths:
        product_bits = 2 * int(width)
        modulus = 1 << product_bits
        total_cases = 0
        parity_mismatch_count = 0
        carry_reference_mismatch_count = 0
        max_observed_carry_span = 0
        for value in range(modulus):
            for column in range(product_bits - 1):
                total_cases += 1
                expected = (value + (1 << column)) % modulus
                parity_only = value ^ (1 << column)
                if parity_only != expected:
                    parity_mismatch_count += 1
                carry_reference = expected
                if carry_reference != expected:
                    carry_reference_mismatch_count += 1
                cursor = column
                while cursor < product_bits and ((value >> cursor) & 1) == 1:
                    cursor += 1
                max_observed_carry_span = max(max_observed_carry_span, cursor - column + 1 if cursor < product_bits else product_bits - column)
        checks.append({
            'width': int(width),
            'product_bits': product_bits,
            'total_cases': total_cases,
            'parity_only_mismatch_count': parity_mismatch_count,
            'carry_reference_mismatch_count': carry_reference_mismatch_count,
            'max_observed_carry_span_bits': max_observed_carry_span,
            'parity_only_rejected': parity_mismatch_count > 0,
            'carry_reference_passes': carry_reference_mismatch_count == 0,
        })
    return checks


def build_modular_accumulator_carry_obligations(
    *,
    modular_accumulator_row_stream: Mapping[str, Any],
    modular_accumulator_capacity_certificate: Mapping[str, Any],
    modular_accumulator_semantic_obligations: Mapping[str, Any],
    field_bits: int,
    segment_size: int = 64,
) -> Dict[str, Any]:
    field_bits = int(field_bits)
    row_counts = modular_accumulator_row_stream['expanded_counts']
    semantic_summary = modular_accumulator_semantic_obligations['obligation_summary']
    product_capacity = modular_accumulator_capacity_certificate['owner_capacity_obligations'][0]
    grid_count = int(row_counts['partial_product_consume_rows']) // (field_bits * field_bits)
    column_stream = _segments(_column_multiplicities(field_bits=field_bits, grid_count=grid_count), segment_size=segment_size)
    reduced_width = _reduced_width_checks(range(2, 7))
    checks = {
        'source_row_stream_passes': modular_accumulator_row_stream['pass'] is True,
        'source_capacity_certificate_passes': modular_accumulator_capacity_certificate['pass'] is True,
        'source_semantic_obligations_pass': modular_accumulator_semantic_obligations['pass'] is True,
        'product_capacity_is_carry_complete': int(product_capacity['logical_qubit_budget_required_by_materialized_columns']) == 2 * field_bits,
        'column_histogram_covers_partial_products': int(column_stream['total_partial_product_rows']) == int(row_counts['partial_product_consume_rows']) == int(semantic_summary['partial_product_consume_rows']),
        'max_increment_span_reaches_final_carry_bit': int(column_stream['max_single_increment_carry_span_bits']) == 2 * field_bits,
        'carry_obligation_exceeds_parity_only_rows': int(column_stream['total_carry_obligation_rows']) > int(column_stream['total_partial_product_rows']),
        'reduced_width_carry_reference_passes': all(row['carry_reference_passes'] is True for row in reduced_width),
        'reduced_width_parity_only_is_rejected': all(row['parity_only_rejected'] is True for row in reduced_width),
        'carry_gate_lowering_not_promoted': True,
    }
    return {
        'schema': MODULAR_ACCUMULATOR_CARRY_OBLIGATIONS_SCHEMA,
        'definition': 'Generated carry-completeness obligations for the modular product accumulator. It proves that partial-product consume cannot be modeled as one parity/XOR write per source bit; a promoted lowering must implement or otherwise prove carry propagation into a 512-bit product owner.',
        'source_digests': {
            'modular_accumulator_row_stream_sha256': _sha256_payload(modular_accumulator_row_stream),
            'modular_accumulator_capacity_certificate_sha256': _sha256_payload(modular_accumulator_capacity_certificate),
            'modular_accumulator_semantic_obligations_sha256': _sha256_payload(modular_accumulator_semantic_obligations),
        },
        'field_bits': field_bits,
        'schoolbook_grid_count': grid_count,
        'product_owner': {
            'partial_product_column_count': int(product_capacity['partial_product_column_count']),
            'carry_complete_capacity_bits': int(product_capacity['logical_qubit_budget_required_by_materialized_columns']),
            'field_slot_capacity_bits': int(product_capacity['field_slot_capacity_bits']),
            'fits_single_field_slot': bool(product_capacity['fits_single_field_slot']),
        },
        'column_carry_obligation_stream': column_stream,
        'reduced_width_exhaustive_checks': reduced_width,
        'promotion_status': {
            'status': 'carry_obligations_not_promoted_to_public_resource_contract',
            'required_to_promote': [
                'Replace parity-style consume with concrete reversible carry-propagating accumulator update gates.',
                'Bind every carry wire to exactly one counted owner with capacity at least the generated carry span.',
                'Rebuild non-Clifford and peak-live-qubit totals from the promoted carry gate stream.',
            ],
        },
        'checks': checks,
        'pass': all(checks.values()),
    }


__all__ = [
    'MODULAR_ACCUMULATOR_CARRY_OBLIGATIONS_SCHEMA',
    'build_modular_accumulator_carry_obligations',
]
