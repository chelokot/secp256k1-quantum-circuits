#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Iterator, List, Mapping

from modular_accumulator_full_adder_contract import (
    FULL_ADDER_CONTRACT_UNPROMOTED_STATUS,
    FULL_ADDER_PRIMITIVE_COUNTS_PER_CELL,
)


MODULAR_ACCUMULATOR_FULL_ADDER_STREAM_SCHEMA = 'compiler-project-modular-accumulator-full-adder-stream-v1'
FULL_ADDER_STREAM_UNPROMOTED_STATUS = 'full_adder_stream_not_promoted_to_global_resource_contract'
STREAM_COLUMNS = [
    'operation_index',
    'grid_index',
    'layer_index',
    'column_index',
    'cell_index',
    'gate',
    'controls',
    'target',
    'cell_input_wires',
    'sum_wire',
    'carry_wire',
]


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def _sha256_payload(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode('ascii')).hexdigest()


def _empty_counts() -> Dict[str, int]:
    return {key: 0 for key in FULL_ADDER_PRIMITIVE_COUNTS_PER_CELL}


def _initial_columns(*, grid_index: int, field_bits: int) -> List[List[str]]:
    columns = [[] for _ in range(2 * int(field_bits))]
    for left_bit in range(int(field_bits)):
        for right_bit in range(int(field_bits)):
            columns[left_bit + right_bit].append(
                f'carry_save:g{int(grid_index)}:partial_product.left[{left_bit}].right[{right_bit}]'
            )
    return columns


def _trim_columns(columns: List[List[str]]) -> List[List[str]]:
    while len(columns) > 1 and not columns[-1]:
        columns.pop()
    return columns


def _cell_output_wire(*, grid_index: int, layer_index: int, column_index: int, cell_index: int, name: str) -> str:
    return f'carry_save:g{grid_index}:layer[{layer_index}].column[{column_index}].cell[{cell_index}].{name}'


def iter_full_adder_stream_rows(
    *,
    field_bits: int,
    grid_count: int,
    gate_sequence: List[Mapping[str, Any]],
) -> Iterator[Dict[str, Any]]:
    operation_index = 0
    for grid_index in range(int(grid_count)):
        columns = _initial_columns(grid_index=grid_index, field_bits=int(field_bits))
        layer_index = 0
        while max(len(column) for column in columns) > 2:
            next_columns = [[] for _ in range(len(columns) + 1)]
            for column_index, column_bits in enumerate(columns):
                cursor = 0
                cell_index = 0
                while cursor + 2 < len(column_bits):
                    inputs = column_bits[cursor:cursor + 3]
                    sum_wire = _cell_output_wire(
                        grid_index=grid_index,
                        layer_index=layer_index,
                        column_index=column_index,
                        cell_index=cell_index,
                        name='sum',
                    )
                    carry_wire = _cell_output_wire(
                        grid_index=grid_index,
                        layer_index=layer_index,
                        column_index=column_index,
                        cell_index=cell_index,
                        name='carry',
                    )
                    local_wires = {
                        'a': inputs[0],
                        'b': inputs[1],
                        'c': inputs[2],
                        'sum': sum_wire,
                        'carry': carry_wire,
                    }
                    for gate in gate_sequence:
                        controls = [local_wires[str(control)] for control in gate['controls']]
                        target = local_wires[str(gate['target'])]
                        yield {
                            'operation_index': operation_index,
                            'grid_index': grid_index,
                            'layer_index': layer_index,
                            'column_index': column_index,
                            'cell_index': cell_index,
                            'gate': str(gate['gate']),
                            'controls': controls,
                            'target': target,
                            'cell_input_wires': list(inputs),
                            'sum_wire': sum_wire,
                            'carry_wire': carry_wire,
                        }
                        operation_index += 1
                    next_columns[column_index].append(sum_wire)
                    next_columns[column_index + 1].append(carry_wire)
                    cursor += 3
                    cell_index += 1
                next_columns[column_index].extend(column_bits[cursor:])
            columns = _trim_columns(next_columns)
            layer_index += 1


def _single_grid_layer_summary(*, field_bits: int) -> Dict[str, Any]:
    columns = _initial_columns(grid_index=0, field_bits=int(field_bits))
    layers = []
    layer_index = 0
    total_cells = 0
    while max(len(column) for column in columns) > 2:
        next_columns = [[] for _ in range(len(columns) + 1)]
        layer_cells = 0
        for column_index, column_bits in enumerate(columns):
            cursor = 0
            while cursor + 2 < len(column_bits):
                sum_wire = _cell_output_wire(
                    grid_index=0,
                    layer_index=layer_index,
                    column_index=column_index,
                    cell_index=layer_cells,
                    name='sum',
                )
                carry_wire = _cell_output_wire(
                    grid_index=0,
                    layer_index=layer_index,
                    column_index=column_index,
                    cell_index=layer_cells,
                    name='carry',
                )
                next_columns[column_index].append(sum_wire)
                next_columns[column_index + 1].append(carry_wire)
                cursor += 3
                layer_cells += 1
            next_columns[column_index].extend(column_bits[cursor:])
        columns = _trim_columns(next_columns)
        layers.append({
            'layer_index': layer_index,
            'full_adder_count': layer_cells,
            'column_count_after_layer': len(columns),
            'max_column_height_after_layer': max(len(column) for column in columns),
            'live_column_bits_after_layer': sum(len(column) for column in columns),
        })
        total_cells += layer_cells
        layer_index += 1
    return {
        'layer_count': len(layers),
        'full_adder_count': total_cells,
        'final_column_count': len(columns),
        'final_live_column_bits': sum(len(column) for column in columns),
        'final_max_column_height': max(len(column) for column in columns),
        'final_carry_propagate_bits': 2 * int(field_bits),
        'layers': layers,
    }


def _encoded_row(row: Mapping[str, Any]) -> str:
    return '\t'.join((
        str(row['operation_index']),
        str(row['grid_index']),
        str(row['layer_index']),
        str(row['column_index']),
        str(row['cell_index']),
        str(row['gate']),
        ','.join(str(control) for control in row['controls']),
        str(row['target']),
        ','.join(str(wire) for wire in row['cell_input_wires']),
        str(row['sum_wire']),
        str(row['carry_wire']),
    )) + '\n'


def build_modular_accumulator_full_adder_stream(
    *,
    modular_accumulator_carry_save_candidate: Mapping[str, Any],
    modular_accumulator_full_adder_contract: Mapping[str, Any],
    segment_size: int = 16384,
) -> Dict[str, Any]:
    if segment_size <= 0:
        raise ValueError('segment_size must be positive')
    field_bits = int(modular_accumulator_carry_save_candidate['field_bits'])
    grid_count = int(modular_accumulator_carry_save_candidate['schoolbook_grid_count'])
    gate_sequence = list(modular_accumulator_full_adder_contract['cell_contract']['gate_sequence'])
    single_grid = _single_grid_layer_summary(field_bits=field_bits)
    stream_digest = hashlib.sha256()
    stream_digest.update(('\t'.join(STREAM_COLUMNS) + '\n').encode('ascii'))
    segment_digest = hashlib.sha256()
    segment_counts = _empty_counts()
    total_counts = _empty_counts()
    segments = []
    preview_head = []
    preview_tail = []
    operation_count = 0
    segment_start = 0
    segment_count = 0

    for row in iter_full_adder_stream_rows(
        field_bits=field_bits,
        grid_count=grid_count,
        gate_sequence=gate_sequence,
    ):
        encoded = _encoded_row(row).encode('ascii')
        stream_digest.update(encoded)
        segment_digest.update(encoded)
        gate = str(row['gate'])
        total_counts[gate] += 1
        segment_counts[gate] += 1
        if len(preview_head) < 6:
            preview_head.append({column: row[column] for column in STREAM_COLUMNS})
        preview_tail.append({column: row[column] for column in STREAM_COLUMNS})
        if len(preview_tail) > 6:
            preview_tail.pop(0)
        operation_count += 1
        segment_count += 1
        if segment_count == segment_size:
            segments.append({
                'segment_index': len(segments),
                'operation_start': segment_start,
                'operation_end_exclusive': operation_count,
                'operation_count': segment_count,
                'primitive_counts_total': segment_counts,
                'non_clifford_count': int(segment_counts['ccx']),
                'sha256': segment_digest.hexdigest(),
            })
            segment_digest = hashlib.sha256()
            segment_start = operation_count
            segment_count = 0
            segment_counts = _empty_counts()

    if segment_count:
        segments.append({
            'segment_index': len(segments),
            'operation_start': segment_start,
            'operation_end_exclusive': operation_count,
            'operation_count': segment_count,
            'primitive_counts_total': segment_counts,
            'non_clifford_count': int(segment_counts['ccx']),
            'sha256': segment_digest.hexdigest(),
        })

    cell_count = operation_count // len(gate_sequence)
    expected_cells = int(modular_accumulator_full_adder_contract['candidate_totals']['full_adder_cell_count'])
    expected_counts = {
        key: int(value)
        for key, value in modular_accumulator_full_adder_contract['candidate_totals']['embedded_full_adder_primitive_counts'].items()
    }
    retained_input_bits = cell_count * int(modular_accumulator_full_adder_contract['cell_contract']['retained_input_bits_per_cell'])
    output_bits = cell_count * int(modular_accumulator_full_adder_contract['cell_contract']['output_bits_per_cell'])
    checks = {
        'source_carry_save_candidate_passes': modular_accumulator_carry_save_candidate['pass'] is True,
        'source_full_adder_contract_passes': modular_accumulator_full_adder_contract['pass'] is True,
        'source_full_adder_contract_is_unpromoted': modular_accumulator_full_adder_contract['promotion_status']['status'] == FULL_ADDER_CONTRACT_UNPROMOTED_STATUS,
        'single_grid_layer_summary_matches_candidate': single_grid['layers'] == modular_accumulator_carry_save_candidate['single_grid']['layers'],
        'streamed_cell_count_matches_contract': cell_count == expected_cells,
        'streamed_operation_count_is_whole_cells': operation_count == cell_count * len(gate_sequence),
        'streamed_primitive_counts_match_contract': total_counts == expected_counts,
        'streamed_operation_count_matches_primitive_counts': operation_count == sum(total_counts.values()),
        'all_grid_final_carry_bits_match_candidate': grid_count * int(single_grid['final_carry_propagate_bits']) == int(modular_accumulator_carry_save_candidate['all_grids']['final_carry_propagate_bits']),
        'retained_input_obligations_remain_explicit': retained_input_bits == int(modular_accumulator_full_adder_contract['candidate_totals']['retained_input_obligation_bits']),
        'output_obligations_match_contract': output_bits == int(modular_accumulator_full_adder_contract['candidate_totals']['output_obligation_bits']),
        'stream_not_promoted_to_global_resource_contract': True,
    }
    return {
        'schema': MODULAR_ACCUMULATOR_FULL_ADDER_STREAM_SCHEMA,
        'definition': 'Exact streamed primitive expansion of every carry-save full-adder cell. The stream names symbolic input, sum, and carry wires and hashes every emitted CX/CCX row; retained inputs remain explicit obligations and this stream is not yet promoted into the global liveness/resource contract.',
        'source_digests': {
            'modular_accumulator_carry_save_candidate_sha256': _sha256_payload(modular_accumulator_carry_save_candidate),
            'modular_accumulator_full_adder_contract_sha256': _sha256_payload(modular_accumulator_full_adder_contract),
        },
        'stream_columns': STREAM_COLUMNS,
        'cell_gate_sequence': gate_sequence,
        'field_bits': field_bits,
        'schoolbook_grid_count': grid_count,
        'segment_size': int(segment_size),
        'segment_count': len(segments),
        'operation_count': operation_count,
        'full_adder_cell_count': cell_count,
        'operation_stream_sha256': stream_digest.hexdigest(),
        'primitive_counts_total': total_counts,
        'non_clifford_count': int(total_counts['ccx']),
        'retained_input_obligation_bits': retained_input_bits,
        'output_obligation_bits': output_bits,
        'single_grid': single_grid,
        'segments': segments,
        'preview_head': preview_head,
        'preview_tail': preview_tail,
        'promotion_status': {
            'status': FULL_ADDER_STREAM_UNPROMOTED_STATUS,
            'required_to_promote': [
                'Assign every cell input, sum output, and carry output wire to counted owners in the global liveness engine.',
                'Prove uncompute/cleanup for retained input wires or keep them in the peak-live resource total.',
                'Splice this stream into scheduled_modular_primitive_netlist and replace synthetic arithmetic_scratch targets.',
                'Recompute public non-Clifford and peak-live-qubit totals from the combined global primitive stream.',
            ],
        },
        'checks': checks,
        'pass': all(checks.values()),
    }


__all__ = [
    'FULL_ADDER_STREAM_UNPROMOTED_STATUS',
    'MODULAR_ACCUMULATOR_FULL_ADDER_STREAM_SCHEMA',
    'build_modular_accumulator_full_adder_stream',
    'iter_full_adder_stream_rows',
]
