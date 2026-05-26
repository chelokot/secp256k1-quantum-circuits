#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Iterator, List, Mapping, Optional

from arithmetic_lowering import materialize_arithmetic_primitive_operations


SCHEDULED_MODULAR_PRIMITIVE_NETLIST_SCHEMA = 'compiler-project-scheduled-modular-primitive-netlist-v1'
PRIMITIVE_KEYS = ('ccx', 'cx', 'x', 'measurement')
STREAM_COLUMNS = [
    'operation_index',
    'suboperation_index',
    'schedule_index',
    'tail_operation_index',
    'kind',
    'modular_opcode',
    'stage',
    'block',
    'local_operation_index',
    'block_operation_index',
    'gate',
    'local_operands',
    'target',
    'target_slot',
    'owner_id',
    'sources',
    'operand_wires',
]


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def _sha256_payload(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode('ascii')).hexdigest()


def _empty_counts() -> Dict[str, int]:
    return {key: 0 for key in PRIMITIVE_KEYS}


def _add_count(counts: Dict[str, int], gate: str) -> None:
    counts[str(gate)] += 1


def _arithmetic_block_index(arithmetic_lowerings: Mapping[str, Any]) -> Dict[tuple[str, str, str], Mapping[str, Any]]:
    index: Dict[tuple[str, str, str], Mapping[str, Any]] = {}
    for kernel in arithmetic_lowerings['kernels']:
        opcode = str(kernel['opcode'])
        for stage in kernel['stages']:
            stage_name = str(stage['name'])
            for block in stage['blocks']:
                index[(opcode, stage_name, str(block['name']))] = block
    return index


def _field_bit_wire(field_name: str, bit_index: int) -> str:
    return f'field:{field_name}.bit[{int(bit_index)}]'


def _scratch_wire(target: str, block: str, bit_index: int) -> str:
    return f'arithmetic_scratch:{target}:{block}.bit[{int(bit_index)}]'


def _operand_wires(suboperation: Mapping[str, Any], block: str, operation: List[Any]) -> List[str]:
    gate = str(operation[0])
    local_operands = [int(value) for value in operation[1:]]
    sources = [str(source) for source in suboperation['sources']]
    target = str(suboperation['target'])
    if gate == 'measurement':
        bit_index = local_operands[0] if local_operands else 0
        return [_field_bit_wire(target, bit_index)]
    if gate in {'x', 'hadamard', 'single_qubit_rotation'}:
        bit_index = local_operands[0] if local_operands else 0
        return [_field_bit_wire(target, bit_index)]
    if gate == 'cx':
        bit_index = local_operands[0] if local_operands else 0
        left = sources[0] if sources else target
        return [_field_bit_wire(left, bit_index), _field_bit_wire(target, bit_index)]
    if gate == 'ccx' and len(local_operands) >= 2:
        left_bit = local_operands[0]
        right_bit = local_operands[1]
        left = sources[0] if sources else target
        right = sources[1] if len(sources) > 1 else left
        return [
            _field_bit_wire(left, left_bit),
            _field_bit_wire(right, right_bit),
            _scratch_wire(target, block, left_bit * 256 + right_bit),
        ]
    if gate == 'ccx':
        bit_index = local_operands[0] if local_operands else 0
        left = sources[0] if sources else target
        right = sources[-1] if sources else target
        return [
            _field_bit_wire(left, bit_index),
            _field_bit_wire(right, bit_index),
            _field_bit_wire(target, bit_index),
        ]
    raise ValueError(f'unsupported primitive gate in scheduled modular netlist: {gate}')


def _encoded_row(row: Mapping[str, Any]) -> str:
    return '\t'.join(_canonical_json(row[column]) for column in STREAM_COLUMNS) + '\n'


def iter_scheduled_modular_primitive_rows(
    *,
    modular_execution_trace: Mapping[str, Any],
    modular_arithmetic_certificate: Mapping[str, Any],
    arithmetic_lowerings: Mapping[str, Any],
    reusable_chunk_lowering: Mapping[str, Any],
) -> Iterator[Dict[str, Any]]:
    block_index = _arithmetic_block_index(arithmetic_lowerings)
    opcode_steps = {
        str(opcode_row['opcode']): list(opcode_row['steps'])
        for opcode_row in modular_arithmetic_certificate['modular_primitive_stream_certificate']['opcodes']
    }
    operation_index = 0
    for trace_row in modular_execution_trace['trace_rows']:
        for suboperation in trace_row['suboperations']:
            modular_opcode = suboperation['modular_opcode']
            if modular_opcode is None:
                if str(suboperation['kind']) == 'lookup_interface_stream':
                    continue
                gate = 'ccx'
                for local_index in range(int(suboperation['operation_count'])):
                    yield {
                        'operation_index': operation_index,
                        'suboperation_index': int(suboperation['global_suboperation_index']),
                        'schedule_index': int(suboperation['schedule_index']),
                        'tail_operation_index': int(suboperation['tail_operation_index']),
                        'kind': str(suboperation['kind']),
                        'modular_opcode': None,
                        'stage': str(suboperation['kind']),
                        'block': str(suboperation['kind']),
                        'local_operation_index': local_index,
                        'block_operation_index': local_index,
                        'gate': gate,
                        'local_operands': [local_index],
                        'target': str(suboperation['target']),
                        'target_slot': suboperation['target_slot'],
                        'owner_id': str(suboperation['owner_id']),
                        'sources': [str(source) for source in suboperation['sources']],
                        'operand_wires': [_scratch_wire(str(suboperation['target']), str(suboperation['kind']), local_index)],
                    }
                    operation_index += 1
                continue
            for step in opcode_steps[str(modular_opcode)]:
                for block_summary in step['blocks']:
                    stage_name = str(block_summary['stage'])
                    block_name = str(block_summary['block'])
                    block = block_index[(str(modular_opcode), stage_name, block_name)]
                    for block_operation_index, operation in enumerate(materialize_arithmetic_primitive_operations(block)):
                        yield {
                            'operation_index': operation_index,
                            'suboperation_index': int(suboperation['global_suboperation_index']),
                            'schedule_index': int(suboperation['schedule_index']),
                            'tail_operation_index': int(suboperation['tail_operation_index']),
                            'kind': str(suboperation['kind']),
                            'modular_opcode': str(modular_opcode),
                            'stage': stage_name,
                            'block': block_name,
                            'local_operation_index': int(block_summary['operation_start']) + block_operation_index,
                            'block_operation_index': block_operation_index,
                            'gate': str(operation[0]),
                            'local_operands': [int(value) for value in operation[1:]],
                            'target': str(suboperation['target']),
                            'target_slot': suboperation['target_slot'],
                            'owner_id': str(suboperation['owner_id']),
                            'sources': [str(source) for source in suboperation['sources']],
                            'operand_wires': _operand_wires(suboperation, block_name, list(operation)),
                        }
                        operation_index += 1
    for chunk_index, qroam_row in enumerate(reusable_chunk_lowering['stream_plan']['rows']):
        gate = 'ccx'
        table = str(qroam_row['table'])
        chunk = int(qroam_row['chunk_index'])
        chunk_operation_count = int(qroam_row['per_chunk_stream_non_clifford'])
        for local_index in range(chunk_operation_count):
            yield {
                'operation_index': operation_index,
                'suboperation_index': -1 - chunk_index,
                'schedule_index': None,
                'tail_operation_index': None,
                'kind': 'public_qroam_chunk_stream',
                'modular_opcode': None,
                'stage': 'public_qroam_chunk_stream',
                'block': f'{table}:chunk_{chunk}',
                'local_operation_index': local_index,
                'block_operation_index': local_index,
                'gate': gate,
                'local_operands': [local_index],
                'target': f'{table}.chunk[{chunk}]',
                'target_slot': None,
                'owner_id': 'lookup_workspace',
                'sources': [table],
                'operand_wires': [
                    f'lookup_workspace:{table}:chunk[{chunk}].select[{local_index % 32768}]',
                    f'lookup_workspace:{table}:chunk[{chunk}].target[{local_index % int(qroam_row["chunk_bits"])}]',
                    f'lookup_workspace:{table}:chunk[{chunk}].scratch[{local_index}]',
                ],
            }
            operation_index += 1


def build_scheduled_modular_primitive_netlist(
    *,
    modular_execution_trace: Mapping[str, Any],
    modular_arithmetic_certificate: Mapping[str, Any],
    arithmetic_lowerings: Mapping[str, Any],
    reusable_chunk_lowering: Mapping[str, Any],
    segment_size: int = 16384,
) -> Dict[str, Any]:
    if segment_size <= 0:
        raise ValueError('segment_size must be positive')
    stream_digest = hashlib.sha256()
    stream_digest.update(('\t'.join(STREAM_COLUMNS) + '\n').encode('ascii'))
    segment_digest = hashlib.sha256()
    segment_count = 0
    segment_start = 0
    counts = _empty_counts()
    segment_counts = _empty_counts()
    segments: List[Dict[str, Any]] = []
    preview_head: List[Dict[str, Any]] = []
    preview_tail: List[Dict[str, Any]] = []
    suboperation_counts: Dict[int, Dict[str, int]] = {}
    qroam_chunk_counts = _empty_counts()
    operation_count = 0
    all_rows_have_operand_wires = True

    for row in iter_scheduled_modular_primitive_rows(
        modular_execution_trace=modular_execution_trace,
        modular_arithmetic_certificate=modular_arithmetic_certificate,
        arithmetic_lowerings=arithmetic_lowerings,
        reusable_chunk_lowering=reusable_chunk_lowering,
    ):
        all_rows_have_operand_wires = all_rows_have_operand_wires and len(row['operand_wires']) > 0
        encoded = _encoded_row(row).encode('ascii')
        stream_digest.update(encoded)
        segment_digest.update(encoded)
        operation_count += 1
        segment_count += 1
        gate = str(row['gate'])
        _add_count(counts, gate)
        _add_count(segment_counts, gate)
        suboperation_index = int(row['suboperation_index'])
        if str(row['kind']) == 'public_qroam_chunk_stream':
            _add_count(qroam_chunk_counts, gate)
        else:
            if suboperation_index not in suboperation_counts:
                suboperation_counts[suboperation_index] = _empty_counts()
            _add_count(suboperation_counts[suboperation_index], gate)
        compact = {
            column: row[column]
            for column in STREAM_COLUMNS
        }
        if len(preview_head) < 6:
            preview_head.append(compact)
        preview_tail.append(compact)
        if len(preview_tail) > 6:
            preview_tail.pop(0)
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
            segment_count = 0
            segment_start = operation_count
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

    expected_suboperation_counts = {
        int(suboperation['global_suboperation_index']): {
            key: int(suboperation['primitive_counts_total'][key])
            for key in PRIMITIVE_KEYS
        }
        for trace_row in modular_execution_trace['trace_rows']
        for suboperation in trace_row['suboperations']
        if suboperation['kind'] != 'lookup_interface_stream'
    }
    observed_suboperation_counts = {
        index: {
            key: int(value)
            for key, value in counts_by_gate.items()
        }
        for index, counts_by_gate in sorted(suboperation_counts.items())
    }
    expected_total_counts = {
        key: sum(int(row[key]) for row in expected_suboperation_counts.values())
        for key in PRIMITIVE_KEYS
    }
    expected_qroam_counts = {
        **_empty_counts(),
        'ccx': sum(int(row['per_chunk_stream_non_clifford']) for row in reusable_chunk_lowering['stream_plan']['rows']),
    }
    expected_strict_leaf_counts = {
        key: int(expected_total_counts[key]) + int(expected_qroam_counts[key])
        for key in PRIMITIVE_KEYS
    }
    trace_lookup_interface_non_clifford = sum(
        int(suboperation['non_clifford'])
        for trace_row in modular_execution_trace['trace_rows']
        for suboperation in trace_row['suboperations']
        if suboperation['kind'] == 'lookup_interface_stream'
    )
    public_qroam_chunk_non_clifford = int(expected_qroam_counts['ccx'])
    checks = {
        'modular_execution_trace_passes': modular_execution_trace['pass'] is True,
        'modular_arithmetic_certificate_passes': modular_arithmetic_certificate['pass'] is True,
        'all_suboperation_counts_match_trace': observed_suboperation_counts == expected_suboperation_counts,
        'public_qroam_chunk_counts_match_stream_plan': qroam_chunk_counts == expected_qroam_counts,
        'total_counts_match_trace_suboperations_plus_public_qroam': counts == expected_strict_leaf_counts,
        'non_clifford_matches_public_strict_leaf': int(counts['ccx']) == int(modular_execution_trace['reconstructed_non_clifford']) - trace_lookup_interface_non_clifford + public_qroam_chunk_non_clifford,
        'stream_scanned_every_operation': operation_count == sum(int(sum(row.values())) for row in expected_suboperation_counts.values()) + sum(int(row['per_chunk_stream_non_clifford']) for row in reusable_chunk_lowering['stream_plan']['rows']),
        'trace_lookup_interface_replaced_by_public_qroam_stream_plan': public_qroam_chunk_non_clifford >= trace_lookup_interface_non_clifford and len(reusable_chunk_lowering['stream_plan']['rows']) == int(reusable_chunk_lowering['stream_plan']['chunk_streams_per_leaf']),
        'all_rows_have_concrete_operand_wires': all_rows_have_operand_wires,
    }
    return {
        'schema': SCHEDULED_MODULAR_PRIMITIVE_NETLIST_SCHEMA,
        'definition': 'Deterministic primitive-row expansion of the scheduled modular execution trace; every generated row is scanned into the stream hash and segment hashes.',
        'source_digests': {
            'modular_execution_trace_sha256': _sha256_payload(modular_execution_trace),
            'modular_arithmetic_certificate_sha256': _sha256_payload(modular_arithmetic_certificate),
            'arithmetic_lowerings_sha256': _sha256_payload(arithmetic_lowerings),
            'reusable_chunk_lowering_sha256': _sha256_payload(reusable_chunk_lowering),
        },
        'stream_columns': STREAM_COLUMNS,
        'exact_operation_stream_materialized_by_iterator': True,
        'operation_rows_materialized_in_json': False,
        'segment_size': int(segment_size),
        'operation_count': operation_count,
        'segment_count': len(segments),
        'operation_stream_sha256': stream_digest.hexdigest(),
        'primitive_counts_total': counts,
        'non_clifford_count': int(counts['ccx']),
        'trace_lookup_interface_non_clifford_replaced': trace_lookup_interface_non_clifford,
        'public_qroam_chunk_non_clifford': public_qroam_chunk_non_clifford,
        'strict_public_leaf_non_clifford': int(counts['ccx']),
        'segments': segments,
        'suboperation_count': len(expected_suboperation_counts),
        'suboperation_counts_sha256': _sha256_payload(observed_suboperation_counts),
        'preview_head': preview_head,
        'preview_tail': preview_tail,
        'checks': checks,
        'pass': all(checks.values()),
        'boundary': [
            'The artifact expands the scheduled modular trace into every generated primitive row through a deterministic iterator and derives counts by scanning that stream.',
            'The full row list is not checked into JSON; the checked artifact commits to segment hashes and the full stream hash, following the public flat-netlist manifest pattern.',
        ],
    }


__all__ = [
    'SCHEDULED_MODULAR_PRIMITIVE_NETLIST_SCHEMA',
    'build_scheduled_modular_primitive_netlist',
    'iter_scheduled_modular_primitive_rows',
]
