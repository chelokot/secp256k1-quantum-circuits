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


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(',', ':'))


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
        'leaf_arithmetic_total_matches_lowering_reconstruction': (
            leaf_summary['primitive_counts_total']
            == arithmetic_lowerings['leaf_reconstruction']['primitive_totals']
            and leaf_summary['non_clifford_total']
            == int(arithmetic_lowerings['leaf_reconstruction']['arithmetic_leaf_non_clifford'])
        ),
        'leaf_arithmetic_opcodes_are_covered': (
            sorted(row['opcode'] for row in leaf_summary['rows'])
            == sorted(row['opcode'] for row in arithmetic_lowerings['leaf_reconstruction']['per_opcode'])
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
        'summary': {
            'kernel_count': len(kernels),
            'stage_count': len(stage_rows),
            'block_count': len(block_rows),
            'kernel_operation_count_total': sum(int(kernel['operation_count']) for kernel in kernels),
            'max_block_operand_slots_required': max(
                int(block['operand_profile']['operand_slots_required'])
                for block in block_rows
            ),
        },
        'leaf_arithmetic_summary': leaf_summary,
        'kernels': kernels,
        'checks': checks,
        'pass': all(checks.values()),
        'boundary': [
            'This is a compact arithmetic primitive-operation IR and digest layer; it is still not a Clifford-complete reversible arithmetic netlist.',
            'It removes another handwritten-total path by making block, stage, kernel, and selected-leaf arithmetic totals reconstruct from canonical operation streams.',
        ],
    }


__all__ = [
    'ARITHMETIC_OPERATION_IR_SCHEMA',
    'build_arithmetic_operation_ir',
]
