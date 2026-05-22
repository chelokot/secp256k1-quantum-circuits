#!/usr/bin/env python3

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence

from arithmetic_lowering import (
    SECP256K1_CANONICAL_SUBTRACT_PASSES,
    SECP256K1_PSEUDO_MERSENNE_LOW_TERM,
    SECP256K1_PSEUDO_MERSENNE_SHIFT,
)
from common import SECP_P
from derived_resources import minimal_addition_chain


def pseudo_mersenne_modulus(field_bits: int, shift: int, low_term: int) -> int:
    return (1 << int(field_bits)) - (1 << int(shift)) - int(low_term)


def pseudo_mersenne_reduce(value: int, *, field_bits: int, shift: int, low_term: int, subtract_passes: int) -> Dict[str, Any]:
    mask = (1 << int(field_bits)) - 1
    modulus = pseudo_mersenne_modulus(field_bits, shift, low_term)
    high = int(value) >> int(field_bits)
    first_fold = (int(value) & mask) + (high << int(shift)) + high * int(low_term)
    residual = first_fold >> int(field_bits)
    second_fold = (first_fold & mask) + (residual << int(shift)) + residual * int(low_term)
    canonical = second_fold
    subtract_trace = []
    for _ in range(int(subtract_passes)):
        did_subtract = canonical >= modulus
        if did_subtract:
            canonical -= modulus
        subtract_trace.append({
            'did_subtract': did_subtract,
            'value_after_pass': canonical,
        })
    return {
        'input': int(value),
        'modulus': modulus,
        'first_high': high,
        'first_fold': first_fold,
        'second_high': residual,
        'second_fold': second_fold,
        'subtract_trace': subtract_trace,
        'canonical': canonical,
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


def _count_profile(ccx: int = 0, measurement: int = 0) -> Dict[str, int]:
    return {
        'ccx': int(ccx),
        'cx': 0,
        'x': 0,
        'measurement': int(measurement),
    }


def _sum_profiles(rows: Sequence[Mapping[str, int]]) -> Dict[str, int]:
    return {
        key: sum(int(row[key]) for row in rows)
        for key in ('ccx', 'cx', 'x', 'measurement')
    }


def _step(
    *,
    name: str,
    kind: str,
    bit_count: int,
    repeat_count: int,
    semantic: str,
    measured: bool = True,
) -> Dict[str, Any]:
    primitive_count = int(bit_count) * int(repeat_count)
    primitive_counts = _count_profile(
        ccx=primitive_count,
        measurement=primitive_count if measured else 0,
    )
    return {
        'name': name,
        'kind': kind,
        'bit_count': int(bit_count),
        'repeat_count': int(repeat_count),
        'semantic': semantic,
        'measured': bool(measured),
        'primitive_counts_total': primitive_counts,
    }


def _operation_ir(opcode: str, steps: Sequence[Mapping[str, Any]], semantic: str) -> Dict[str, Any]:
    primitive_counts = _sum_profiles([step['primitive_counts_total'] for step in steps])
    return {
        'opcode': opcode,
        'semantic': semantic,
        'steps': list(steps),
        'primitive_counts_total': primitive_counts,
        'non_clifford_total': primitive_counts['ccx'],
    }


def build_executable_modular_circuit_ir(*, field_bits: int, shift: int, low_term: int, subtract_passes: int) -> Dict[str, Any]:
    chain = minimal_addition_chain(21)
    low_term_chain_steps = _binary_addition_chain_step_count(low_term)
    second_fold_width = int(shift) + int(low_term).bit_length() + 1
    add_steps = [
        _step(
            name='carry_ladder',
            kind='ripple_carry',
            bit_count=int(field_bits) - 1,
            repeat_count=1,
            semantic='compute raw sum carry path',
        ),
        _step(
            name='conditional_subtract_modulus',
            kind='conditional_modulus_correction',
            bit_count=int(field_bits) - 1,
            repeat_count=1,
            semantic='canonicalize raw sum by subtracting p when needed',
        ),
    ]
    sub_steps = [
        _step(
            name='borrow_ladder',
            kind='ripple_borrow',
            bit_count=int(field_bits) - 1,
            repeat_count=1,
            semantic='compute raw difference borrow path',
        ),
        _step(
            name='conditional_add_modulus',
            kind='conditional_modulus_correction',
            bit_count=int(field_bits) - 1,
            repeat_count=1,
            semantic='canonicalize raw difference by adding p when needed',
        ),
    ]
    field_mul_steps = [
        _step(
            name='partial_product_grid',
            kind='schoolbook_partial_products',
            bit_count=int(field_bits) * int(field_bits),
            repeat_count=1,
            semantic='one controlled interaction for each field-bit product',
            measured=False,
        ),
        _step(
            name='controlled_add_path',
            kind='controlled_accumulator_add',
            bit_count=int(field_bits) - 1,
            repeat_count=1,
            semantic='carry path for controlled add half of schoolbook multiplier',
        ),
        _step(
            name='controlled_sub_path',
            kind='controlled_accumulator_subtract',
            bit_count=int(field_bits),
            repeat_count=1,
            semantic='borrow path for controlled subtract half of schoolbook multiplier',
        ),
        _step(
            name='pseudo_mersenne_first_fold',
            kind='pseudo_mersenne_fold',
            bit_count=int(field_bits) + int(shift) - 1,
            repeat_count=1 + low_term_chain_steps,
            semantic='fold high product half via 2^n = 2^shift + low_term',
        ),
        _step(
            name='pseudo_mersenne_second_fold',
            kind='pseudo_mersenne_fold',
            bit_count=second_fold_width - 1,
            repeat_count=1 + low_term_chain_steps,
            semantic='fold residual high component after first fold',
        ),
        _step(
            name='pseudo_mersenne_canonicalize',
            kind='conditional_modulus_correction',
            bit_count=int(field_bits) - 1,
            repeat_count=int(subtract_passes),
            semantic='canonicalize product with bounded subtract-p passes',
        ),
    ]
    operations = [
        _operation_ir('field_add', add_steps, 'canonical modular addition'),
        _operation_ir('field_sub', sub_steps, 'canonical modular subtraction'),
        _operation_ir(
            'field_sub_sum',
            [{**step, 'name': f'first_subtract_{step["name"]}'} for step in sub_steps]
            + [{**step, 'name': f'second_subtract_{step["name"]}'} for step in sub_steps],
            'two sequential canonical modular subtractions',
        ),
        _operation_ir(
            'field_triple',
            [{**step, 'name': f'first_add_{step["name"]}'} for step in add_steps]
            + [{**step, 'name': f'second_add_{step["name"]}'} for step in add_steps],
            'two sequential canonical modular additions for 3a',
        ),
        _operation_ir(
            'mul_const',
            [
                {**step, 'name': f'chain_{left}_to_{right}_{step["name"]}'}
                for left, right in zip(chain, chain[1:])
                for step in add_steps
            ],
            'fixed multiplication by 21 through canonical modular additions',
        ),
        _operation_ir('field_mul', field_mul_steps, 'schoolbook multiplication followed by pseudo-Mersenne reduction'),
    ]
    return {
        'schema': 'compiler-project-executable-modular-circuit-ir-v1',
        'field_bits': int(field_bits),
        'pseudo_mersenne': {
            'shift': int(shift),
            'low_term': int(low_term),
            'canonical_subtract_passes': int(subtract_passes),
            'low_term_chain_steps': low_term_chain_steps,
            'second_fold_width': second_fold_width,
        },
        'mul_const_21_addition_chain': chain,
        'operations': operations,
        'non_clifford_by_opcode': {
            operation['opcode']: int(operation['non_clifford_total'])
            for operation in operations
        },
    }


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
    circuit_ir = build_executable_modular_circuit_ir(
        field_bits=field_bits,
        shift=SECP256K1_PSEUDO_MERSENNE_SHIFT,
        low_term=SECP256K1_PSEUDO_MERSENNE_LOW_TERM,
        subtract_passes=SECP256K1_CANONICAL_SUBTRACT_PASSES,
    )
    circuit_ir_counts = _circuit_ir_count_certificate(circuit_ir, arithmetic_lowerings)
    reduced_width_cases = [
        _exhaustive_case(field_bits=5, shift=2, low_term=5),
        _exhaustive_case(field_bits=6, shift=3, low_term=3),
    ]
    checks = {
        'secp256k1_modulus_matches_common_constant': secp_modulus == SECP_P,
        'opcode_counts_match_modular_operation_contracts': bool(opcode_counts['opcode_counts_match']),
        'executable_circuit_ir_counts_match_arithmetic_lowering': bool(circuit_ir_counts['counts_match_arithmetic_lowerings']),
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
        'opcode_count_certificate': opcode_counts,
        'field_mul_stage_count_certificate': stage_counts,
        'reduced_width_exhaustive_cases': reduced_width_cases,
        'checks': checks,
        'pass': all(checks.values()),
        'boundary': [
            'This certificate executes the same modular-circuit IR on reduced-width pseudo-Mersenne analogues and binds the 256-bit IR counts back to arithmetic_lowerings.json.',
            'It is not yet a Clifford-complete reversible netlist for every arithmetic opcode.',
        ],
    }


__all__ = [
    'build_executable_modular_circuit_ir',
    'build_modular_arithmetic_certificate',
    'pseudo_mersenne_reduce',
]
