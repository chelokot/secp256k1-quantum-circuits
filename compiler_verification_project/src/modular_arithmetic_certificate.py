#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Mapping

from arithmetic_lowering import (
    SECP256K1_CANONICAL_SUBTRACT_PASSES,
    SECP256K1_PSEUDO_MERSENNE_LOW_TERM,
    SECP256K1_PSEUDO_MERSENNE_SHIFT,
    build_executable_modular_circuit_ir,
    materialize_arithmetic_primitive_operations,
    pseudo_mersenne_modulus,
    pseudo_mersenne_reduce,
)
from common import SECP_P
from derived_resources import minimal_addition_chain

PRIMITIVE_KEYS = ('ccx', 'cx', 'x', 'measurement')
MODULAR_PRIMITIVE_STREAM_ENCODING = [
    'opcode',
    'step',
    'stage',
    'block',
    'operation_index',
    'block_operation_index',
    'gate',
    'operand_0',
    'operand_1',
    'operand_2',
]


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def _empty_counts() -> Dict[str, int]:
    return {key: 0 for key in PRIMITIVE_KEYS}


def _add_counts(left: Dict[str, int], right: Mapping[str, Any]) -> None:
    for key in PRIMITIVE_KEYS:
        left[key] += int(right.get(key, 0))


def _operation_counts(operations: List[List[Any]]) -> Dict[str, int]:
    counts = _empty_counts()
    for operation in operations:
        counts[str(operation[0])] += 1
    return counts


def _encoded_modular_primitive_row(
    *,
    opcode: str,
    step: str,
    stage: str,
    block: str,
    operation_index: int,
    block_operation_index: int,
    operation: List[Any],
) -> str:
    operands = [int(value) for value in operation[1:]]
    row = [
        opcode,
        step,
        stage,
        block,
        int(operation_index),
        int(block_operation_index),
        str(operation[0]),
        operands[0] if len(operands) > 0 else '',
        operands[1] if len(operands) > 1 else '',
        operands[2] if len(operands) > 2 else '',
    ]
    return '\t'.join(str(value) for value in row) + '\n'


def _compact_operation_row(
    *,
    opcode: str,
    step: str,
    stage: str,
    block: str,
    operation_index: int,
    block_operation_index: int,
    operation: List[Any],
) -> Dict[str, Any]:
    return {
        'opcode': opcode,
        'step': step,
        'stage': stage,
        'block': block,
        'operation_index': int(operation_index),
        'block_operation_index': int(block_operation_index),
        'gate': str(operation[0]),
        'operands': [int(value) for value in operation[1:]],
    }


def _stage_by_name(kernel: Mapping[str, Any]) -> Dict[str, Mapping[str, Any]]:
    return {str(stage['name']): stage for stage in kernel['stages']}


def _blocks_for_modular_step(kernel: Mapping[str, Any], opcode: str, step_name: str) -> List[Mapping[str, Any]]:
    if opcode == 'field_mul':
        stage_name = {
            'partial_product_grid': 'partial_products',
            'controlled_add_path': 'controlled_add_path',
            'controlled_sub_path': 'controlled_sub_path',
            'pseudo_mersenne_first_fold': 'pseudo_mersenne_first_fold',
            'pseudo_mersenne_second_fold': 'pseudo_mersenne_second_fold',
            'pseudo_mersenne_canonicalize': 'pseudo_mersenne_canonicalize',
        }[step_name]
        return list(_stage_by_name(kernel)[stage_name]['blocks'])
    return [
        block
        for stage in kernel['stages']
        for block in stage['blocks']
        if str(block['name']) == step_name
    ]


def _stage_name_for_block(kernel: Mapping[str, Any], block_name: str) -> str:
    for stage in kernel['stages']:
        if any(str(block['name']) == block_name for block in stage['blocks']):
            return str(stage['name'])
    raise ValueError(f'block {block_name} not found in kernel {kernel["opcode"]}')


def build_modular_primitive_stream_certificate(
    *,
    arithmetic_lowerings: Mapping[str, Any],
    circuit_ir: Mapping[str, Any],
) -> Dict[str, Any]:
    kernel_by_opcode = {
        str(kernel['opcode']): kernel
        for kernel in arithmetic_lowerings['kernels']
    }
    opcode_rows = []
    total_counts = _empty_counts()
    total_operation_count = 0
    stream_root = hashlib.sha256()
    stream_root.update(('\t'.join(MODULAR_PRIMITIVE_STREAM_ENCODING) + '\n').encode('ascii'))
    failures: List[Dict[str, Any]] = []
    for operation in circuit_ir['operations']:
        opcode = str(operation['opcode'])
        kernel = kernel_by_opcode.get(opcode)
        if kernel is None:
            failures.append({'opcode': opcode, 'reason': 'no_lowering_kernel'})
            continue
        opcode_hash = hashlib.sha256()
        opcode_hash.update(('\t'.join(MODULAR_PRIMITIVE_STREAM_ENCODING) + '\n').encode('ascii'))
        opcode_counts = _empty_counts()
        opcode_operation_index = 0
        step_rows = []
        preview_head: List[Dict[str, Any]] = []
        preview_tail: List[Dict[str, Any]] = []
        for step in operation['steps']:
            step_name = str(step['name'])
            blocks = _blocks_for_modular_step(kernel, opcode, step_name)
            step_counts = _empty_counts()
            step_start = opcode_operation_index
            block_rows = []
            if not blocks:
                failures.append({'opcode': opcode, 'step': step_name, 'reason': 'no_lowering_blocks'})
            for block in blocks:
                block_name = str(block['name'])
                stage_name = _stage_name_for_block(kernel, block_name)
                block_operations = materialize_arithmetic_primitive_operations(block)
                block_counts = _operation_counts(block_operations)
                block_start = opcode_operation_index
                for block_operation_index, primitive_operation in enumerate(block_operations):
                    encoded = _encoded_modular_primitive_row(
                        opcode=opcode,
                        step=step_name,
                        stage=stage_name,
                        block=block_name,
                        operation_index=opcode_operation_index,
                        block_operation_index=block_operation_index,
                        operation=primitive_operation,
                    )
                    opcode_hash.update(encoded.encode('ascii'))
                    stream_root.update(encoded.encode('ascii'))
                    compact = _compact_operation_row(
                        opcode=opcode,
                        step=step_name,
                        stage=stage_name,
                        block=block_name,
                        operation_index=opcode_operation_index,
                        block_operation_index=block_operation_index,
                        operation=primitive_operation,
                    )
                    if len(preview_head) < 4:
                        preview_head.append(compact)
                    preview_tail.append(compact)
                    if len(preview_tail) > 4:
                        preview_tail.pop(0)
                    opcode_operation_index += 1
                _add_counts(step_counts, block_counts)
                block_rows.append({
                    'stage': stage_name,
                    'block': block_name,
                    'operation_start': block_start,
                    'operation_end_exclusive': opcode_operation_index,
                    'operation_count': len(block_operations),
                    'primitive_counts_total': block_counts,
                    'declared_primitive_counts_total': {
                        key: int(block['primitive_counts_total'][key])
                        for key in PRIMITIVE_KEYS
                    },
                    'counts_match_declared_block': block_counts == {
                        key: int(block['primitive_counts_total'][key])
                        for key in PRIMITIVE_KEYS
                    },
                })
            _add_counts(opcode_counts, step_counts)
            expected_step_counts = {
                key: int(step['primitive_counts_total'][key])
                for key in PRIMITIVE_KEYS
            }
            step_rows.append({
                'step': step_name,
                'kind': str(step['kind']),
                'bit_count': int(step['bit_count']),
                'repeat_count': int(step['repeat_count']),
                'operation_start': step_start,
                'operation_end_exclusive': opcode_operation_index,
                'operation_count': opcode_operation_index - step_start,
                'primitive_counts_total': step_counts,
                'expected_primitive_counts_total': expected_step_counts,
                'counts_match_executable_ir_step': step_counts == expected_step_counts,
                'blocks': block_rows,
            })
        expected_opcode_counts = {
            key: int(operation['primitive_counts_total'][key])
            for key in PRIMITIVE_KEYS
        }
        lowering_counts = {
            key: int(kernel['primitive_counts_total'][key])
            for key in PRIMITIVE_KEYS
        }
        _add_counts(total_counts, opcode_counts)
        total_operation_count += opcode_operation_index
        opcode_rows.append({
            'opcode': opcode,
            'operation_count': opcode_operation_index,
            'primitive_counts_total': opcode_counts,
            'expected_primitive_counts_total': expected_opcode_counts,
            'lowering_primitive_counts_total': lowering_counts,
            'non_clifford_total': int(opcode_counts['ccx']),
            'operation_stream_sha256': opcode_hash.hexdigest(),
            'step_count': len(step_rows),
            'steps': step_rows,
            'preview_head': preview_head,
            'preview_tail': preview_tail,
            'counts_match_executable_ir_opcode': opcode_counts == expected_opcode_counts,
            'counts_match_lowering_kernel': opcode_counts == lowering_counts,
        })
    expected_total_counts = _empty_counts()
    for operation in circuit_ir['operations']:
        _add_counts(expected_total_counts, operation['primitive_counts_total'])
    checks = {
        'all_ir_opcodes_have_lowering_kernels': all(str(operation['opcode']) in kernel_by_opcode for operation in circuit_ir['operations']),
        'all_steps_have_lowering_blocks': not failures,
        'all_block_streams_match_declared_counts': all(
            block['counts_match_declared_block']
            for opcode_row in opcode_rows
            for step_row in opcode_row['steps']
            for block in step_row['blocks']
        ),
        'all_step_streams_match_executable_ir': all(
            step_row['counts_match_executable_ir_step']
            for opcode_row in opcode_rows
            for step_row in opcode_row['steps']
        ),
        'all_opcode_streams_match_executable_ir': all(row['counts_match_executable_ir_opcode'] for row in opcode_rows),
        'all_opcode_streams_match_lowering_kernels': all(row['counts_match_lowering_kernel'] for row in opcode_rows),
        'total_stream_counts_match_executable_ir': total_counts == expected_total_counts,
    }
    return {
        'schema': 'compiler-project-modular-primitive-stream-certificate-v1',
        'scope': 'local primitive Clifford/CCX operation streams for executable modular arithmetic opcodes',
        'operation_encoding': MODULAR_PRIMITIVE_STREAM_ENCODING,
        'operation_rows_materialized_in_json': False,
        'field_bits': int(circuit_ir['field_bits']),
        'opcode_count': len(opcode_rows),
        'operation_count': total_operation_count,
        'primitive_counts_total': total_counts,
        'non_clifford_total': int(total_counts['ccx']),
        'operation_stream_sha256': stream_root.hexdigest(),
        'opcodes': opcode_rows,
        'failures': failures[:8],
        'checks': checks,
        'pass': all(checks.values()),
        'notes': [
            'Rows are generated by materializing the arithmetic lowering blocks selected by executable_modular_circuit_ir, then hashing the local primitive stream.',
            'This certificate removes formula-only modular stage counting, but it is still a local kernel stream: operands are local bit indices, not yet allocated in one global Clifford-complete point-add schedule.',
        ],
    }


def _binary_addition_chain_step_count(constant: int) -> int:
    return int(constant).bit_length() + int(constant).bit_count() - 2


def _stage_ccx(arithmetic_lowerings: Mapping[str, Any], opcode: str, stage_name: str) -> int:
    kernel = next(row for row in arithmetic_lowerings['kernels'] if row['opcode'] == opcode)
    stage = next(row for row in kernel['stages'] if row['name'] == stage_name)
    return int(stage['primitive_counts_total']['ccx'])


def _field_mul_kernel(arithmetic_lowerings: Mapping[str, Any]) -> Mapping[str, Any]:
    return next(row for row in arithmetic_lowerings['kernels'] if row['opcode'] == 'field_mul')


def _kernel(arithmetic_lowerings: Mapping[str, Any], opcode: str) -> Mapping[str, Any]:
    return next(row for row in arithmetic_lowerings['kernels'] if row['opcode'] == opcode)


def _stage_count_certificate(arithmetic_lowerings: Mapping[str, Any], field_bits: int) -> Dict[str, Any]:
    chain_steps = _binary_addition_chain_step_count(SECP256K1_PSEUDO_MERSENNE_LOW_TERM)
    second_fold_width = (
        SECP256K1_PSEUDO_MERSENNE_SHIFT
        + SECP256K1_PSEUDO_MERSENNE_LOW_TERM.bit_length()
        + 1
    )
    expected = {
        'partial_products': int(field_bits) * int(field_bits),
        'controlled_add_path': int(field_bits) - 1,
        'controlled_sub_path': int(field_bits),
        'pseudo_mersenne_first_fold': (int(field_bits) + SECP256K1_PSEUDO_MERSENNE_SHIFT - 1) * (1 + chain_steps),
        'pseudo_mersenne_second_fold': (second_fold_width - 1) * (1 + chain_steps),
        'pseudo_mersenne_canonicalize': (int(field_bits) - 1) * SECP256K1_CANONICAL_SUBTRACT_PASSES,
    }
    observed = {
        stage_name: _stage_ccx(arithmetic_lowerings, 'field_mul', stage_name)
        for stage_name in expected
    }
    expected_total = sum(expected.values())
    observed_total = int(_field_mul_kernel(arithmetic_lowerings)['exact_non_clifford_per_kernel'])
    return {
        'chain_steps_for_low_term': chain_steps,
        'second_fold_width': second_fold_width,
        'expected_stage_ccx': expected,
        'observed_stage_ccx': observed,
        'expected_total_ccx': expected_total,
        'observed_total_ccx': observed_total,
        'stage_counts_match': observed == expected and observed_total == expected_total,
    }


def _opcode_count_certificate(arithmetic_lowerings: Mapping[str, Any], field_bits: int) -> Dict[str, Any]:
    modular_add = 2 * (int(field_bits) - 1)
    modular_sub = 2 * (int(field_bits) - 1)
    chain = minimal_addition_chain(21)
    expected = {
        'field_add': modular_add,
        'field_sub': modular_sub,
        'field_sub_sum': 2 * modular_sub,
        'field_triple': 2 * modular_add,
        'mul_const': (len(chain) - 1) * modular_add,
        'field_mul': _stage_count_certificate(arithmetic_lowerings, field_bits)['expected_total_ccx'],
    }
    expected['field_double_mul_add'] = 2 * expected['field_mul'] + expected['field_add']
    expected['field_double_mul_sub'] = 2 * expected['field_mul'] + expected['field_sub']
    observed = {
        opcode: int(_kernel(arithmetic_lowerings, opcode)['exact_non_clifford_per_kernel'])
        for opcode in expected
    }
    return {
        'field_bits': int(field_bits),
        'modular_add_correction_policy': 'carry ladder plus conditional subtract-p correction',
        'modular_sub_correction_policy': 'borrow ladder plus conditional add-p correction',
        'mul_const_21_addition_chain': chain,
        'expected_non_clifford_per_opcode': expected,
        'observed_non_clifford_per_opcode': observed,
        'opcode_counts_match': observed == expected,
    }


def _circuit_ir_count_certificate(ir: Mapping[str, Any], arithmetic_lowerings: Mapping[str, Any]) -> Dict[str, Any]:
    expected = dict(ir['non_clifford_by_opcode'])
    observed = {
        opcode: int(_kernel(arithmetic_lowerings, opcode)['exact_non_clifford_per_kernel'])
        for opcode in expected
    }
    return {
        'ir_schema': ir['schema'],
        'expected_non_clifford_per_opcode': expected,
        'observed_non_clifford_per_opcode': observed,
        'counts_match_arithmetic_lowerings': observed == expected,
    }


def _modular_add_trace(left: int, right: int, modulus: int) -> Dict[str, Any]:
    raw = int(left) + int(right)
    corrected = raw - int(modulus) if raw >= int(modulus) else raw
    return {
        'raw_sum': raw,
        'did_subtract_modulus': raw >= int(modulus),
        'canonical': corrected,
    }


def _modular_sub_trace(left: int, right: int, modulus: int) -> Dict[str, Any]:
    raw = int(left) - int(right)
    corrected = raw + int(modulus) if raw < 0 else raw
    return {
        'raw_difference': raw,
        'did_add_modulus': raw < 0,
        'canonical': corrected,
    }


def _mul_const_trace(value: int, constant: int, modulus: int) -> Dict[str, Any]:
    chain = minimal_addition_chain(constant)
    values = {1: int(value) % int(modulus)}
    steps = []
    for previous, current in zip(chain, chain[1:]):
        delta = current - previous
        left = values[previous]
        right = values[delta] if delta in values else (delta * int(value)) % int(modulus)
        trace = _modular_add_trace(left, right, modulus)
        values[current] = trace['canonical']
        steps.append({
            'from': previous,
            'to': current,
            'delta': delta,
            'left': left,
            'right': right,
            'add_trace': trace,
        })
    return {
        'constant': int(constant),
        'addition_chain': chain,
        'steps': steps,
        'canonical': values[int(constant)],
    }


def _execute_modular_circuit(ir: Mapping[str, Any], opcode: str, left: int, right: int, modulus: int) -> Dict[str, Any]:
    operation = next(row for row in ir['operations'] if row['opcode'] == opcode)
    if opcode == 'field_add':
        trace = _modular_add_trace(left, right, modulus)
        canonical = trace['canonical']
    elif opcode == 'field_sub':
        trace = _modular_sub_trace(left, right, modulus)
        canonical = trace['canonical']
    elif opcode == 'field_sub_sum':
        first = _modular_sub_trace(left, right, modulus)
        second = _modular_sub_trace(first['canonical'], right, modulus)
        trace = {'first_subtract': first, 'second_subtract': second}
        canonical = second['canonical']
    elif opcode == 'field_triple':
        first = _modular_add_trace(left, left, modulus)
        second = _modular_add_trace(first['canonical'], left, modulus)
        trace = {'first_add': first, 'second_add': second}
        canonical = second['canonical']
    elif opcode == 'mul_const':
        trace = _mul_const_trace(left, 21, modulus)
        canonical = trace['canonical']
    elif opcode == 'field_mul':
        trace = pseudo_mersenne_reduce(
            left * right,
            field_bits=int(ir['field_bits']),
            shift=int(ir['pseudo_mersenne']['shift']),
            low_term=int(ir['pseudo_mersenne']['low_term']),
            subtract_passes=int(ir['pseudo_mersenne']['canonical_subtract_passes']),
        )
        canonical = trace['canonical']
    else:
        raise ValueError(f'unknown modular circuit opcode: {opcode}')
    return {
        'opcode': opcode,
        'semantic': operation['semantic'],
        'step_names': [step['name'] for step in operation['steps']],
        'non_clifford_total': int(operation['non_clifford_total']),
        'trace': trace,
        'canonical': canonical,
    }


def _exhaustive_case(field_bits: int, shift: int, low_term: int) -> Dict[str, Any]:
    modulus = pseudo_mersenne_modulus(field_bits, shift, low_term)
    ir = build_executable_modular_circuit_ir(
        field_bits=field_bits,
        shift=shift,
        low_term=low_term,
        subtract_passes=SECP256K1_CANONICAL_SUBTRACT_PASSES,
    )
    rows_checked = 0
    failures: List[Dict[str, Any]] = []
    sample_traces = []
    for left in range(modulus):
        for right in range(modulus):
            rows_checked += 1
            checks = {
                'add': (left + right) % modulus,
                'sub': (left - right) % modulus,
                'sub_sum': (left - right - right) % modulus,
                'triple': (3 * left) % modulus,
                'mul': (left * right) % modulus,
                'mul_const_21': (left * 21) % modulus,
            }
            add_execution = _execute_modular_circuit(ir, 'field_add', left, right, modulus)
            sub_execution = _execute_modular_circuit(ir, 'field_sub', left, right, modulus)
            sub_sum_execution = _execute_modular_circuit(ir, 'field_sub_sum', left, right, modulus)
            triple_execution = _execute_modular_circuit(ir, 'field_triple', left, right, modulus)
            product_execution = _execute_modular_circuit(ir, 'field_mul', left, right, modulus)
            const_execution = _execute_modular_circuit(ir, 'mul_const', left, right, modulus)
            observed = {
                'add': add_execution['canonical'],
                'sub': sub_execution['canonical'],
                'sub_sum': sub_sum_execution['canonical'],
                'triple': triple_execution['canonical'],
                'mul': product_execution['canonical'],
                'mul_const_21': const_execution['canonical'],
            }
            if checks != observed:
                failures.append({'left': left, 'right': right, 'expected': checks, 'observed': observed})
            if len(sample_traces) < 4 and left in (0, 1, modulus - 1) and right in (0, 2, modulus - 1):
                sample_traces.append({
                    'left': left,
                    'right': right,
                    'add_execution': add_execution,
                    'sub_execution': sub_execution,
                    'sub_sum_execution': sub_sum_execution,
                    'triple_execution': triple_execution,
                    'product_execution': product_execution,
                    'mul_const_21_execution': const_execution,
                })
    return {
        'field_bits': int(field_bits),
        'shift': int(shift),
        'low_term': int(low_term),
        'modulus': modulus,
        'rows_checked': rows_checked,
        'operations_checked': ['add', 'sub', 'sub_sum', 'triple', 'mul', 'mul_const_21'],
        'circuit_ir': ir,
        'sample_traces': sample_traces,
        'failures': failures[:8],
        'pass': not failures,
    }


def build_modular_arithmetic_certificate(*, arithmetic_lowerings: Mapping[str, Any], field_bits: int) -> Dict[str, Any]:
    secp_modulus = pseudo_mersenne_modulus(
        field_bits,
        SECP256K1_PSEUDO_MERSENNE_SHIFT,
        SECP256K1_PSEUDO_MERSENNE_LOW_TERM,
    )
    stage_counts = _stage_count_certificate(arithmetic_lowerings, field_bits)
    opcode_counts = _opcode_count_certificate(arithmetic_lowerings, field_bits)
    expected_circuit_ir = build_executable_modular_circuit_ir(
        field_bits=field_bits,
        shift=SECP256K1_PSEUDO_MERSENNE_SHIFT,
        low_term=SECP256K1_PSEUDO_MERSENNE_LOW_TERM,
        subtract_passes=SECP256K1_CANONICAL_SUBTRACT_PASSES,
    )
    circuit_ir = arithmetic_lowerings['executable_modular_circuit_ir']
    circuit_ir_counts = _circuit_ir_count_certificate(circuit_ir, arithmetic_lowerings)
    primitive_stream_certificate = build_modular_primitive_stream_certificate(
        arithmetic_lowerings=arithmetic_lowerings,
        circuit_ir=circuit_ir,
    )
    reduced_width_cases = [
        _exhaustive_case(field_bits=5, shift=2, low_term=5),
        _exhaustive_case(field_bits=6, shift=3, low_term=3),
    ]
    checks = {
        'secp256k1_modulus_matches_common_constant': secp_modulus == SECP_P,
        'arithmetic_lowering_embeds_current_executable_modular_circuit_ir': circuit_ir == expected_circuit_ir,
        'opcode_counts_match_modular_operation_contracts': bool(opcode_counts['opcode_counts_match']),
        'executable_circuit_ir_counts_match_arithmetic_lowering': bool(circuit_ir_counts['counts_match_arithmetic_lowerings']),
        'primitive_stream_certificate_matches_executable_modular_circuit_ir': primitive_stream_certificate['pass'] is True,
        'field_mul_stage_counts_match_arithmetic_lowering': bool(stage_counts['stage_counts_match']),
        'reduced_width_cases_exhaustive_pass': all(row['pass'] for row in reduced_width_cases),
    }
    return {
        'schema': 'compiler-project-modular-arithmetic-certificate-v1',
        'purpose': 'Executable reduced-width certificate for the pseudo-Mersenne modular arithmetic schedule used by the counted field_mul lowering.',
        'secp256k1_parameters': {
            'field_bits': int(field_bits),
            'modulus_hex': format(SECP_P, '064x'),
            'pseudo_mersenne_identity': '2^256 = 2^32 + 977 mod p',
            'shift': SECP256K1_PSEUDO_MERSENNE_SHIFT,
            'low_term': SECP256K1_PSEUDO_MERSENNE_LOW_TERM,
            'canonical_subtract_passes': SECP256K1_CANONICAL_SUBTRACT_PASSES,
        },
        'executable_modular_circuit_ir': circuit_ir,
        'executable_circuit_ir_count_certificate': circuit_ir_counts,
        'modular_primitive_stream_certificate': primitive_stream_certificate,
        'opcode_count_certificate': opcode_counts,
        'field_mul_stage_count_certificate': stage_counts,
        'reduced_width_exhaustive_cases': reduced_width_cases,
        'checks': checks,
        'pass': all(checks.values()),
        'boundary': [
            'The arithmetic lowering embeds the executable modular-circuit IR used to generate the modular arithmetic kernels; this certificate consumes that same IR for reduced-width semantic execution, 256-bit count binding, and local primitive stream hashing.',
            'Remaining work is to allocate these local modular primitive streams into one global Clifford-complete point-add schedule with concrete wire owners and liveness.',
        ],
    }


__all__ = [
    'build_executable_modular_circuit_ir',
    'build_modular_arithmetic_certificate',
    'build_modular_primitive_stream_certificate',
    'pseudo_mersenne_reduce',
]
