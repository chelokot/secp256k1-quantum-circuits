#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Mapping

from arithmetic_lowering import materialize_arithmetic_primitive_operations


ARITHMETIC_OPERATION_IR_SCHEMA = 'compiler-project-arithmetic-operation-ir-v1'
ARITHMETIC_OPERATION_STREAM_ENCODING = [
    'kernel',
    'stage',
    'block',
    'operation_index',
    'gate',
    'operand_0',
    'operand_1',
    'operand_2',
]
PRIMITIVE_KEYS = ('ccx', 'cx', 'x', 'measurement')
LEAF_EXACT_OPERATION_STREAM_SEGMENT_SIZE = 1_000_000


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(',', ':'))


def _merkle_root(hashes: List[str]) -> str:
    if not hashes:
        return hashlib.sha256(b'').hexdigest()
    level = list(hashes)
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [
            hashlib.sha256((level[index] + level[index + 1]).encode('ascii')).hexdigest()
            for index in range(0, len(level), 2)
        ]
    return level[0]


def _empty_counts() -> Dict[str, int]:
    return {key: 0 for key in PRIMITIVE_KEYS}


def _add_counts(left: Dict[str, int], right: Mapping[str, Any]) -> None:
    for key in PRIMITIVE_KEYS:
        left[key] += int(right.get(key, 0))


def _encoded_operation(
    *,
    kernel: str,
    stage: str,
    block: str,
    operation_index: int,
    operation: List[Any],
) -> str:
    operands = [int(value) for value in operation[1:]]
    row = [
        kernel,
        stage,
        block,
        int(operation_index),
        str(operation[0]),
        operands[0] if len(operands) > 0 else '',
        operands[1] if len(operands) > 1 else '',
        operands[2] if len(operands) > 2 else '',
    ]
    return '\t'.join(str(value) for value in row) + '\n'


def _encoded_leaf_exact_operation(
    *,
    operation_index: int,
    leaf_instance_index: int,
    kernel: str,
    stage: str,
    block: str,
    block_operation_index: int,
    operation: List[Any],
) -> str:
    operands = [int(value) for value in operation[1:]]
    row = [
        int(operation_index),
        int(leaf_instance_index),
        kernel,
        stage,
        block,
        int(block_operation_index),
        str(operation[0]),
        operands[0] if len(operands) > 0 else '',
        operands[1] if len(operands) > 1 else '',
        operands[2] if len(operands) > 2 else '',
    ]
    return '\t'.join(str(value) for value in row) + '\n'


def _operation_profile(operations: List[List[Any]]) -> Dict[str, Any]:
    counts = _empty_counts()
    gate_arities: Dict[str, List[int]] = {}
    max_operand_index = -1
    negative_operand_count = 0
    too_wide_operand_rows = 0
    for operation in operations:
        gate = str(operation[0])
        counts[gate] += 1
        operands = [int(value) for value in operation[1:]]
        gate_arities.setdefault(gate, [])
        if len(operands) not in gate_arities[gate]:
            gate_arities[gate].append(len(operands))
        if any(value < 0 for value in operands):
            negative_operand_count += 1
        if len(operands) > 3:
            too_wide_operand_rows += 1
        if operands:
            max_operand_index = max(max_operand_index, max(operands))
    return {
        'primitive_counts_total': counts,
        'gate_arities': {key: sorted(value) for key, value in sorted(gate_arities.items())},
        'max_operand_index': max_operand_index,
        'operand_slots_required': max_operand_index + 1 if max_operand_index >= 0 else 0,
        'negative_operand_count': negative_operand_count,
        'too_wide_operand_rows': too_wide_operand_rows,
    }


def _generator_operand_contract(block: Mapping[str, Any], operation_count: int, profile: Mapping[str, Any]) -> Dict[str, Any] | None:
    generator = block.get('primitive_operation_generator')
    if generator is None:
        return None
    kind = str(generator['kind'])
    if kind == 'repeated_ladder_with_measurement':
        bit_count = int(generator['bit_count'])
        repeat_count = int(generator['repeat_count'])
        expected_operation_count = 2 * bit_count * repeat_count
        expected_operand_slots = bit_count
        return {
            'kind': kind,
            'operand_domain': 'ladder_bit_index',
            'bit_count': bit_count,
            'repeat_count': repeat_count,
            'expected_operation_count': expected_operation_count,
            'expected_operand_slots_required': expected_operand_slots,
            'observed_operation_count': operation_count,
            'observed_operand_slots_required': int(profile['operand_slots_required']),
            'pass': (
                operation_count == expected_operation_count
                and int(profile['operand_slots_required']) == expected_operand_slots
                and int(profile['negative_operand_count']) == 0
                and profile['gate_arities'] == {'ccx': [1], 'measurement': [1]}
            ),
        }
    if kind == 'repeated_gate':
        count = int(generator['count'])
        return {
            'kind': kind,
            'operand_domain': 'generator_event_index',
            'count': count,
            'expected_operation_count': count,
            'expected_operand_slots_required': count,
            'observed_operation_count': operation_count,
            'observed_operand_slots_required': int(profile['operand_slots_required']),
            'pass': (
                operation_count == count
                and int(profile['operand_slots_required']) == count
                and int(profile['negative_operand_count']) == 0
            ),
        }
    if kind == 'repeated_gate_with_measurement':
        count = int(generator['count'])
        return {
            'kind': kind,
            'operand_domain': 'generator_event_index',
            'count': count,
            'expected_operation_count': 2 * count,
            'expected_operand_slots_required': count,
            'observed_operation_count': operation_count,
            'observed_operand_slots_required': int(profile['operand_slots_required']),
            'pass': (
                operation_count == 2 * count
                and int(profile['operand_slots_required']) == count
                and int(profile['negative_operand_count']) == 0
                and profile['gate_arities'] == {'ccx': [1], 'measurement': [1]}
            ),
        }
    return {
        'kind': kind,
        'operand_domain': 'unknown',
        'pass': False,
    }


def _block_ir(
    *,
    kernel: str,
    stage: str,
    block: Mapping[str, Any],
    operation_start: int,
) -> Dict[str, Any]:
    operations = materialize_arithmetic_primitive_operations(block)
    stream_hash = hashlib.sha256()
    stream_hash.update(('\t'.join(ARITHMETIC_OPERATION_STREAM_ENCODING) + '\n').encode())
    for offset, operation in enumerate(operations):
        stream_hash.update(
            _encoded_operation(
                kernel=kernel,
                stage=stage,
                block=str(block['name']),
                operation_index=operation_start + offset,
                operation=operation,
            ).encode()
        )
    profile = _operation_profile(operations)
    generator_contract = _generator_operand_contract(block, len(operations), profile)
    return {
        'kernel': kernel,
        'stage': stage,
        'block': str(block['name']),
        'operation_start': operation_start,
        'operation_end_exclusive': operation_start + len(operations),
        'operation_count': len(operations),
        'operation_stream_sha256': stream_hash.hexdigest(),
        'primitive_counts_total': profile['primitive_counts_total'],
        'declared_primitive_counts_total': {
            key: int(block['primitive_counts_total'][key])
            for key in PRIMITIVE_KEYS
        },
        'operand_profile': {
            'gate_arities': profile['gate_arities'],
            'max_operand_index': profile['max_operand_index'],
            'operand_slots_required': profile['operand_slots_required'],
            'negative_operand_count': profile['negative_operand_count'],
            'too_wide_operand_rows': profile['too_wide_operand_rows'],
        },
        'source_contract': {
            'summary': block['summary'],
            'instance_count': int(block['instance_count']),
            'has_expanded_operations': 'primitive_operations' in block,
            'has_generator': 'primitive_operation_generator' in block,
            'generator_operand_contract': generator_contract,
        },
    }


def _stage_ir(kernel: str, stage: Mapping[str, Any], operation_start: int) -> Dict[str, Any]:
    blocks = []
    counts = _empty_counts()
    operation_cursor = operation_start
    block_digest_hash = hashlib.sha256()
    for block in stage['blocks']:
        block_row = _block_ir(
            kernel=kernel,
            stage=str(stage['name']),
            block=block,
            operation_start=operation_cursor,
        )
        blocks.append(block_row)
        operation_cursor = int(block_row['operation_end_exclusive'])
        _add_counts(counts, block_row['primitive_counts_total'])
        block_digest_hash.update(_canonical_json({
            'block': block_row['block'],
            'operation_start': block_row['operation_start'],
            'operation_end_exclusive': block_row['operation_end_exclusive'],
            'operation_stream_sha256': block_row['operation_stream_sha256'],
            'primitive_counts_total': block_row['primitive_counts_total'],
        }).encode())
    return {
        'kernel': kernel,
        'stage': str(stage['name']),
        'category': str(stage['category']),
        'operation_start': operation_start,
        'operation_end_exclusive': operation_cursor,
        'operation_count': operation_cursor - operation_start,
        'block_count': len(blocks),
        'block_digest_sha256': block_digest_hash.hexdigest(),
        'primitive_counts_total': counts,
        'declared_primitive_counts_total': {
            key: int(stage['primitive_counts_total'][key])
            for key in PRIMITIVE_KEYS
        },
        'blocks': blocks,
    }


def _kernel_ir(kernel: Mapping[str, Any]) -> Dict[str, Any]:
    stages = []
    counts = _empty_counts()
    operation_cursor = 0
    stage_digest_hash = hashlib.sha256()
    for stage in kernel['stages']:
        stage_row = _stage_ir(str(kernel['opcode']), stage, operation_cursor)
        stages.append(stage_row)
        operation_cursor = int(stage_row['operation_end_exclusive'])
        _add_counts(counts, stage_row['primitive_counts_total'])
        stage_digest_hash.update(_canonical_json({
            'stage': stage_row['stage'],
            'operation_start': stage_row['operation_start'],
            'operation_end_exclusive': stage_row['operation_end_exclusive'],
            'block_digest_sha256': stage_row['block_digest_sha256'],
            'primitive_counts_total': stage_row['primitive_counts_total'],
        }).encode())
    return {
        'opcode': str(kernel['opcode']),
        'summary': str(kernel['summary']),
        'operation_count': operation_cursor,
        'stage_count': len(stages),
        'block_count': sum(int(stage['block_count']) for stage in stages),
        'stage_digest_sha256': stage_digest_hash.hexdigest(),
        'primitive_counts_total': counts,
        'declared_primitive_counts_total': {
            key: int(kernel['primitive_counts_total'][key])
            for key in PRIMITIVE_KEYS
        },
        'exact_non_clifford_per_kernel': int(kernel['exact_non_clifford_per_kernel']),
        'stages': stages,
    }


def _leaf_arithmetic_summary(
    *,
    leaf_opcode_histogram: Mapping[str, int],
    kernel_rows: List[Mapping[str, Any]],
) -> Dict[str, Any]:
    kernel_lookup = {row['opcode']: row for row in kernel_rows}
    rows = []
    totals = _empty_counts()
    digest_hash = hashlib.sha256()
    non_arithmetic_opcodes = []
    for opcode, count in sorted(leaf_opcode_histogram.items()):
        if int(count) == 0:
            continue
        if opcode not in kernel_lookup:
            non_arithmetic_opcodes.append(opcode)
            continue
        kernel = kernel_lookup[opcode]
        primitive_counts_total = {
            key: int(kernel['primitive_counts_total'][key]) * int(count)
            for key in PRIMITIVE_KEYS
        }
        for key in PRIMITIVE_KEYS:
            totals[key] += primitive_counts_total[key]
        row = {
            'opcode': opcode,
            'leaf_instance_count': int(count),
            'kernel_stage_digest_sha256': kernel['stage_digest_sha256'],
            'kernel_operation_count': int(kernel['operation_count']),
            'kernel_non_clifford_per_instance': int(kernel['exact_non_clifford_per_kernel']),
            'primitive_counts_total': primitive_counts_total,
        }
        rows.append(row)
        digest_hash.update(_canonical_json(row).encode())
    return {
        'leaf_opcode_histogram': {key: int(value) for key, value in sorted(leaf_opcode_histogram.items())},
        'covered_opcode_count': len(rows),
        'non_arithmetic_leaf_opcodes': non_arithmetic_opcodes,
        'operation_stream_sha256': digest_hash.hexdigest(),
        'primitive_counts_total': totals,
        'non_clifford_total': totals['ccx'],
        'rows': rows,
    }


def _leaf_exact_operation_stream(
    *,
    arithmetic_lowerings: Mapping[str, Any],
    leaf_opcode_histogram: Mapping[str, int],
) -> Dict[str, Any]:
    columns = [
        'operation_index',
        'leaf_instance_index',
        'kernel',
        'stage',
        'block',
        'block_operation_index',
        'gate',
        'operand_0',
        'operand_1',
        'operand_2',
    ]
    kernel_lookup = {
        str(kernel['opcode']): kernel
        for kernel in arithmetic_lowerings['kernels']
    }
    operation_count = 0
    gate_totals = _empty_counts()
    segment_start = 0
    segment_count = 0
    segment_gate_totals = _empty_counts()
    segment_digest = hashlib.sha256()
    segment_digest.update(('\t'.join(columns) + '\n').encode('ascii'))
    segments: List[Dict[str, Any]] = []
    preview_head: List[Dict[str, Any]] = []
    preview_tail: List[Dict[str, Any]] = []

    def flush_segment() -> None:
        nonlocal segment_start, segment_count, segment_gate_totals, segment_digest
        if segment_count == 0:
            return
        segments.append({
            'segment_index': len(segments),
            'operation_start': segment_start,
            'operation_end_exclusive': segment_start + segment_count,
            'operation_count': segment_count,
            'gate_totals': segment_gate_totals,
            'non_clifford_count': int(segment_gate_totals['ccx']),
            'sha256': segment_digest.hexdigest(),
        })
        segment_start += segment_count
        segment_count = 0
        segment_gate_totals = _empty_counts()
        segment_digest = hashlib.sha256()
        segment_digest.update(('\t'.join(columns) + '\n').encode('ascii'))

    for opcode, leaf_instance_count in sorted(leaf_opcode_histogram.items()):
        if int(leaf_instance_count) == 0 or opcode not in kernel_lookup:
            continue
        kernel = kernel_lookup[opcode]
        for leaf_instance_index in range(int(leaf_instance_count)):
            for stage in kernel['stages']:
                for block in stage['blocks']:
                    operations = materialize_arithmetic_primitive_operations(block)
                    for block_operation_index, operation in enumerate(operations):
                        gate = str(operation[0])
                        encoded = _encoded_leaf_exact_operation(
                            operation_index=operation_count,
                            leaf_instance_index=leaf_instance_index,
                            kernel=opcode,
                            stage=str(stage['name']),
                            block=str(block['name']),
                            block_operation_index=block_operation_index,
                            operation=operation,
                        )
                        segment_digest.update(encoded.encode('ascii'))
                        gate_totals[gate] += 1
                        segment_gate_totals[gate] += 1
                        compact = {
                            'operation_index': operation_count,
                            'leaf_instance_index': leaf_instance_index,
                            'kernel': opcode,
                            'stage': str(stage['name']),
                            'block': str(block['name']),
                            'block_operation_index': block_operation_index,
                            'gate': gate,
                            'operands': [int(value) for value in operation[1:]],
                        }
                        if len(preview_head) < 6:
                            preview_head.append(compact)
                        preview_tail.append(compact)
                        if len(preview_tail) > 6:
                            preview_tail.pop(0)
                        operation_count += 1
                        segment_count += 1
                        if segment_count == LEAF_EXACT_OPERATION_STREAM_SEGMENT_SIZE:
                            flush_segment()
    flush_segment()
    checks = {
        'segment_rows_cover_operation_count': sum(int(segment['operation_count']) for segment in segments) == operation_count,
        'segment_gate_totals_cover_stream': {
            gate: sum(int(segment['gate_totals'][gate]) for segment in segments) == int(gate_totals[gate])
            for gate in PRIMITIVE_KEYS
        },
    }
    return {
        'schema': 'compiler-project-selected-leaf-exact-arithmetic-operation-stream-v1',
        'definition': 'Exact primitive operation stream for arithmetic opcodes selected by the leaf opcode histogram. Rows are generated from arithmetic_lowerings primitive operations and segmented without checking every row into JSON.',
        'operation_columns': columns,
        'operation_rows_materialized_in_json': False,
        'segment_size': LEAF_EXACT_OPERATION_STREAM_SEGMENT_SIZE,
        'operation_count': operation_count,
        'segment_count': len(segments),
        'segment_merkle_root_sha256': _merkle_root([segment['sha256'] for segment in segments]),
        'gate_totals': gate_totals,
        'non_clifford_count': int(gate_totals['ccx']),
        'segments': segments,
        'preview_head': preview_head,
        'preview_tail': preview_tail,
        'checks': checks,
        'pass': (
            checks['segment_rows_cover_operation_count'] is True
            and all(checks['segment_gate_totals_cover_stream'].values())
        ),
    }


def build_arithmetic_operation_ir(
    *,
    arithmetic_lowerings: Mapping[str, Any],
    leaf_opcode_histogram: Mapping[str, int],
) -> Dict[str, Any]:
    kernels = [_kernel_ir(kernel) for kernel in arithmetic_lowerings['kernels']]
    leaf_summary = _leaf_arithmetic_summary(
        leaf_opcode_histogram=leaf_opcode_histogram,
        kernel_rows=kernels,
    )
    leaf_exact_stream = _leaf_exact_operation_stream(
        arithmetic_lowerings=arithmetic_lowerings,
        leaf_opcode_histogram=leaf_opcode_histogram,
    )
    block_rows = [
        block
        for kernel in kernels
        for stage in kernel['stages']
        for block in stage['blocks']
    ]
    stage_rows = [
        stage
        for kernel in kernels
        for stage in kernel['stages']
    ]
    modular_circuit_ir = arithmetic_lowerings['executable_modular_circuit_ir']
    tail_macro_engine = arithmetic_lowerings['tail_macro_engine']
    modular_opcodes = set(modular_circuit_ir['non_clifford_by_opcode'])
    kernel_by_opcode = {kernel['opcode']: kernel for kernel in kernels}
    checks = {
        'kernel_totals_match_materialized_block_streams': all(
            kernel['primitive_counts_total'] == kernel['declared_primitive_counts_total']
            and kernel['primitive_counts_total']['ccx'] == int(kernel['exact_non_clifford_per_kernel'])
            for kernel in kernels
        ),
        'stage_totals_match_materialized_block_streams': all(
            stage['primitive_counts_total'] == stage['declared_primitive_counts_total']
            for stage in stage_rows
        ),
        'block_totals_match_materialized_operations': all(
            block['primitive_counts_total'] == block['declared_primitive_counts_total']
            for block in block_rows
        ),
        'operation_rows_have_nonnegative_operands': all(
            int(block['operand_profile']['negative_operand_count']) == 0
            for block in block_rows
        ),
        'operation_rows_fit_fixed_stream_encoding': all(
            int(block['operand_profile']['too_wide_operand_rows']) == 0
            for block in block_rows
        ),
        'generator_operand_contracts_pass': all(
            block['source_contract']['generator_operand_contract'] is None
            or block['source_contract']['generator_operand_contract']['pass'] is True
            for block in block_rows
        ),
        'repeated_ladder_generators_use_bit_index_operands': all(
            block['source_contract']['generator_operand_contract'] is None
            or block['source_contract']['generator_operand_contract']['kind'] != 'repeated_ladder_with_measurement'
            or block['source_contract']['generator_operand_contract']['operand_domain'] == 'ladder_bit_index'
            for block in block_rows
        ),
        'non_qroam_generated_ladders_use_typed_ladder_generator': all(
            block['source_contract']['generator_operand_contract'] is None
            or block['source_contract']['generator_operand_contract']['kind'] == 'repeated_ladder_with_measurement'
            or 'qroam' in block['block']
            for block in block_rows
        ),
        'leaf_arithmetic_total_matches_lowering_reconstruction': (
            leaf_summary['primitive_counts_total']
            == arithmetic_lowerings['leaf_reconstruction']['primitive_totals']
            and leaf_summary['non_clifford_total']
            == int(arithmetic_lowerings['leaf_reconstruction']['arithmetic_leaf_non_clifford'])
        ),
        'selected_leaf_exact_stream_matches_leaf_summary': (
            leaf_exact_stream['pass'] is True
            and leaf_exact_stream['gate_totals'] == leaf_summary['primitive_counts_total']
            and int(leaf_exact_stream['non_clifford_count']) == int(leaf_summary['non_clifford_total'])
        ),
        'leaf_arithmetic_opcodes_are_covered': (
            sorted(row['opcode'] for row in leaf_summary['rows'])
            == sorted(row['opcode'] for row in arithmetic_lowerings['leaf_reconstruction']['per_opcode'])
        ),
        'modular_kernels_derive_from_executable_modular_circuit_ir': all(
            opcode in kernel_by_opcode
            and int(kernel_by_opcode[opcode]['exact_non_clifford_per_kernel']) == int(modular_circuit_ir['non_clifford_by_opcode'][opcode])
            and kernel_by_opcode[opcode]['primitive_counts_total']['ccx'] == int(modular_circuit_ir['non_clifford_by_opcode'][opcode])
            for opcode in modular_opcodes
        ),
        'tail_macro_kernel_derives_from_tail_macro_engine': (
            tail_macro_engine['pass'] is True
            and tail_macro_engine['opcode'] in kernel_by_opcode
            and int(kernel_by_opcode[tail_macro_engine['opcode']]['exact_non_clifford_per_kernel'])
            == int(tail_macro_engine['non_clifford_total'])
            and kernel_by_opcode[tail_macro_engine['opcode']]['primitive_counts_total']['ccx']
            == int(tail_macro_engine['non_clifford_total'])
        ),
    }
    return {
        'schema': ARITHMETIC_OPERATION_IR_SCHEMA,
        'purpose': 'Compact typed operation-stream IR for arithmetic lowerings: block/stage/kernel counts are derived from canonical primitive operation streams and digests, not copied totals.',
        'source_artifacts': {
            'arithmetic_lowerings': 'compiler_verification_project/artifacts/arithmetic_lowerings.json',
        },
        'stream_encoding': ARITHMETIC_OPERATION_STREAM_ENCODING,
        'family': arithmetic_lowerings['family'],
        'executable_modular_circuit_ir': {
            'schema': modular_circuit_ir['schema'],
            'field_bits': int(modular_circuit_ir['field_bits']),
            'operation_count': len(modular_circuit_ir['operations']),
            'non_clifford_by_opcode': dict(modular_circuit_ir['non_clifford_by_opcode']),
        },
        'tail_macro_engine': {
            'schema': tail_macro_engine['schema'],
            'opcode': tail_macro_engine['opcode'],
            'expanded_field_operation_count': len(tail_macro_engine['expanded_field_operation_stream']),
            'expanded_single_assignment_peak_field_values': tail_macro_engine['slot_gap']['expanded_single_assignment_peak_field_values'],
            'counted_arithmetic_slots': tail_macro_engine['counted_arithmetic_slots'],
            'fallback_schedule_peak_field_slots': tail_macro_engine['expanded_slot_schedule']['peak_field_slots'],
            'fallback_schedule_additional_logical_qubits': tail_macro_engine['expanded_slot_schedule']['additional_logical_qubits_over_counted_leaf'],
            'destructive_candidate_peak_field_slots': tail_macro_engine['destructive_candidate_schedule']['peak_field_slots'],
            'destructive_candidate_status': tail_macro_engine['destructive_candidate_schedule']['status'],
            'opcode_histogram': dict(tail_macro_engine['opcode_histogram']),
            'non_clifford_total': int(tail_macro_engine['non_clifford_total']),
            'completion_status': tail_macro_engine['completion_status'],
        },
        'summary': {
            'kernel_count': len(kernels),
            'stage_count': len(stage_rows),
            'block_count': len(block_rows),
            'kernel_operation_count_total': sum(int(kernel['operation_count']) for kernel in kernels),
            'max_block_operand_slots_required': max(
                int(block['operand_profile']['operand_slots_required'])
                for block in block_rows
            ),
            'generated_ladder_max_operand_slots_required': max(
                (
                    int(block['operand_profile']['operand_slots_required'])
                    for block in block_rows
                    if (
                        block['source_contract']['generator_operand_contract'] is not None
                        and block['source_contract']['generator_operand_contract']['kind'] == 'repeated_ladder_with_measurement'
                    )
                ),
                default=0,
            ),
        },
        'leaf_arithmetic_summary': leaf_summary,
        'selected_leaf_exact_operation_stream': leaf_exact_stream,
        'kernels': kernels,
        'checks': checks,
        'pass': all(checks.values()),
        'boundary': [
            'This is a compact arithmetic primitive-operation IR and digest layer; it is still not a Clifford-complete reversible arithmetic netlist.',
            'It removes another handwritten-total path by making block, stage, kernel, and selected-leaf arithmetic totals reconstruct from canonical operation streams.',
            'The selected tail macro is now bound to tail_macro_engine: a single expanded field-operation stream owns the formula, opcode histogram, tail-kernel non-Clifford total, and explicit slot-gap status.',
        ],
    }


__all__ = [
    'ARITHMETIC_OPERATION_IR_SCHEMA',
    'build_arithmetic_operation_ir',
]
