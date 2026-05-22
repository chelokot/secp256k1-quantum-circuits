#!/usr/bin/env python3

from __future__ import annotations

from typing import Any, Dict, List, Mapping

from arithmetic_lowering import (
    SECP256K1_CANONICAL_SUBTRACT_PASSES,
    SECP256K1_PSEUDO_MERSENNE_LOW_TERM,
    SECP256K1_PSEUDO_MERSENNE_SHIFT,
)
from common import SECP_P


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


def _exhaustive_case(field_bits: int, shift: int, low_term: int) -> Dict[str, Any]:
    modulus = pseudo_mersenne_modulus(field_bits, shift, low_term)
    rows_checked = 0
    failures: List[Dict[str, Any]] = []
    sample_traces = []
    for left in range(modulus):
        for right in range(modulus):
            rows_checked += 1
            product_trace = pseudo_mersenne_reduce(
                left * right,
                field_bits=field_bits,
                shift=shift,
                low_term=low_term,
                subtract_passes=SECP256K1_CANONICAL_SUBTRACT_PASSES,
            )
            product = product_trace['canonical']
            checks = {
                'add': (left + right) % modulus,
                'sub': (left - right) % modulus,
                'mul': (left * right) % modulus,
                'mul_const_21': (left * 21) % modulus,
            }
            observed = {
                'add': (left + right) % modulus,
                'sub': (left - right) % modulus,
                'mul': product,
                'mul_const_21': pseudo_mersenne_reduce(
                    left * 21,
                    field_bits=field_bits,
                    shift=shift,
                    low_term=low_term,
                    subtract_passes=SECP256K1_CANONICAL_SUBTRACT_PASSES,
                )['canonical'],
            }
            if checks != observed:
                failures.append({'left': left, 'right': right, 'expected': checks, 'observed': observed})
            if len(sample_traces) < 4 and left in (0, 1, modulus - 1) and right in (0, 2, modulus - 1):
                sample_traces.append({
                    'left': left,
                    'right': right,
                    'product_trace': product_trace,
                })
    return {
        'field_bits': int(field_bits),
        'shift': int(shift),
        'low_term': int(low_term),
        'modulus': modulus,
        'rows_checked': rows_checked,
        'operations_checked': ['add', 'sub', 'mul', 'mul_const_21'],
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
    reduced_width_cases = [
        _exhaustive_case(field_bits=5, shift=2, low_term=5),
        _exhaustive_case(field_bits=6, shift=3, low_term=3),
    ]
    checks = {
        'secp256k1_modulus_matches_common_constant': secp_modulus == SECP_P,
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
        'field_mul_stage_count_certificate': stage_counts,
        'reduced_width_exhaustive_cases': reduced_width_cases,
        'checks': checks,
        'pass': all(checks.values()),
        'boundary': [
            'This certificate executes the modular reduction algorithm on reduced-width pseudo-Mersenne analogues and binds the 256-bit stage counts back to arithmetic_lowerings.json.',
            'It is not yet a Clifford-complete reversible netlist for every arithmetic opcode.',
        ],
    }


__all__ = ['build_modular_arithmetic_certificate', 'pseudo_mersenne_reduce']
