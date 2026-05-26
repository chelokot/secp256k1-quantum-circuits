#!/usr/bin/env python3

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Mapping, Optional

from derived_resources import minimal_addition_chain
from tail_macro_engine import TAIL_MACRO_OPCODE, build_tail_macro_engine


PrimitiveOperation = List[int | str]
DEFAULT_QROAM_CLEAN_BLOCK_SIZE = 1
SECP256K1_PSEUDO_MERSENNE_SHIFT = 32
SECP256K1_PSEUDO_MERSENNE_LOW_TERM = 977
SECP256K1_CANONICAL_SUBTRACT_PASSES = 2


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


def _modular_step(
    *,
    name: str,
    kind: str,
    bit_count: int,
    repeat_count: int,
    semantic: str,
    measured: bool = True,
) -> Dict[str, Any]:
    primitive_count = int(bit_count) * int(repeat_count)
    return {
        'name': name,
        'kind': kind,
        'bit_count': int(bit_count),
        'repeat_count': int(repeat_count),
        'semantic': semantic,
        'measured': bool(measured),
        'primitive_counts_total': _primitive_counts(
            ccx=primitive_count,
            measurement=primitive_count if measured else 0,
        ),
    }


def _modular_operation_ir(opcode: str, steps: List[Mapping[str, Any]], semantic: str) -> Dict[str, Any]:
    primitive_counts = {
        key: sum(int(step['primitive_counts_total'][key]) for step in steps)
        for key in ('ccx', 'cx', 'x', 'measurement')
    }
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
        _modular_step(
            name='carry_ladder',
            kind='ripple_carry',
            bit_count=int(field_bits) - 1,
            repeat_count=1,
            semantic='compute raw sum carry path',
        ),
        _modular_step(
            name='conditional_subtract_modulus',
            kind='conditional_modulus_correction',
            bit_count=int(field_bits) - 1,
            repeat_count=1,
            semantic='canonicalize raw sum by subtracting p when needed',
        ),
    ]
    sub_steps = [
        _modular_step(
            name='borrow_ladder',
            kind='ripple_borrow',
            bit_count=int(field_bits) - 1,
            repeat_count=1,
            semantic='compute raw difference borrow path',
        ),
        _modular_step(
            name='conditional_add_modulus',
            kind='conditional_modulus_correction',
            bit_count=int(field_bits) - 1,
            repeat_count=1,
            semantic='canonicalize raw difference by adding p when needed',
        ),
    ]
    field_mul_steps = [
        _modular_step(
            name='partial_product_grid',
            kind='schoolbook_partial_products',
            bit_count=int(field_bits) * int(field_bits),
            repeat_count=1,
            semantic='one controlled interaction for each field-bit product',
            measured=False,
        ),
        _modular_step(
            name='controlled_add_path',
            kind='controlled_accumulator_add',
            bit_count=int(field_bits) - 1,
            repeat_count=1,
            semantic='carry path for controlled add half of schoolbook multiplier',
        ),
        _modular_step(
            name='controlled_sub_path',
            kind='controlled_accumulator_subtract',
            bit_count=int(field_bits),
            repeat_count=1,
            semantic='borrow path for controlled subtract half of schoolbook multiplier',
        ),
        _modular_step(
            name='pseudo_mersenne_first_fold',
            kind='pseudo_mersenne_fold',
            bit_count=int(field_bits) + int(shift) - 1,
            repeat_count=1 + low_term_chain_steps,
            semantic='fold high product half via 2^n = 2^shift + low_term',
        ),
        _modular_step(
            name='pseudo_mersenne_second_fold',
            kind='pseudo_mersenne_fold',
            bit_count=second_fold_width - 1,
            repeat_count=1 + low_term_chain_steps,
            semantic='fold residual high component after first fold',
        ),
        _modular_step(
            name='pseudo_mersenne_canonicalize',
            kind='conditional_modulus_correction',
            bit_count=int(field_bits) - 1,
            repeat_count=int(subtract_passes),
            semantic='canonicalize product with bounded subtract-p passes',
        ),
    ]

    def prefixed_steps(prefix: str, steps: List[Mapping[str, Any]]) -> List[Dict[str, Any]]:
        return [
            {
                **step,
                'name': f'{prefix}_{step["name"]}',
                'semantic': f'{prefix.replace("_", " ")}: {step["semantic"]}',
            }
            for step in steps
        ]

    field_double_mul_add_steps = (
        prefixed_steps('first_product', field_mul_steps)
        + prefixed_steps('second_product', field_mul_steps)
        + prefixed_steps('combine_sum', add_steps)
    )
    field_double_mul_sub_steps = (
        prefixed_steps('first_product', field_mul_steps)
        + prefixed_steps('second_product', field_mul_steps)
        + prefixed_steps('combine_difference', sub_steps)
    )
    operations = [
        _modular_operation_ir('field_add', add_steps, 'canonical modular addition'),
        _modular_operation_ir('field_sub', sub_steps, 'canonical modular subtraction'),
        _modular_operation_ir(
            'field_sub_sum',
            [{**step, 'name': f'first_subtract_{step["name"]}'} for step in sub_steps]
            + [{**step, 'name': f'second_subtract_{step["name"]}'} for step in sub_steps],
            'two sequential canonical modular subtractions',
        ),
        _modular_operation_ir(
            'field_triple',
            [{**step, 'name': f'first_add_{step["name"]}'} for step in add_steps]
            + [{**step, 'name': f'second_add_{step["name"]}'} for step in add_steps],
            'two sequential canonical modular additions for 3a',
        ),
        _modular_operation_ir(
            'mul_const',
            [
                {**step, 'name': f'chain_{left}_to_{right}_{step["name"]}'}
                for left, right in zip(chain, chain[1:])
                for step in add_steps
            ],
            'fixed multiplication by 21 through canonical modular additions',
        ),
        _modular_operation_ir('field_mul', field_mul_steps, 'schoolbook multiplication followed by pseudo-Mersenne reduction'),
        _modular_operation_ir(
            'field_double_mul_add',
            field_double_mul_add_steps,
            'two canonical modular multiplications accumulated with one canonical modular addition',
        ),
        _modular_operation_ir(
            'field_double_mul_sub',
            field_double_mul_sub_steps,
            'two canonical modular multiplications accumulated with one canonical modular subtraction',
        ),
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


def _primitive_counts(ccx: int = 0, cx: int = 0, x: int = 0, measurement: int = 0) -> Dict[str, int]:
    return {
        'ccx': int(ccx),
        'cx': int(cx),
        'x': int(x),
        'measurement': int(measurement),
    }


def _primitive_operation(gate: str, *operands: int) -> PrimitiveOperation:
    return [gate, *[int(operand) for operand in operands]]


def _primitive_counts_from_operations(primitive_operations: List[PrimitiveOperation]) -> Dict[str, int]:
    counts = _primitive_counts()
    for operation in primitive_operations:
        counts[str(operation[0])] += 1
    return counts


def materialize_arithmetic_primitive_operations(block: Mapping[str, Any]) -> List[PrimitiveOperation]:
    if 'primitive_operations' in block:
        return list(block['primitive_operations'])
    generator = block['primitive_operation_generator']
    kind = str(generator['kind'])
    if kind == 'repeated_gate':
        count = int(generator['count'])
        return [_primitive_operation(str(generator['gate']), index) for index in range(count)]
    if kind == 'repeated_gate_with_measurement':
        count = int(generator['count'])
        gate = str(generator['gate'])
        measurement_gate = str(generator['measurement_gate'])
        return [
            operation
            for index in range(count)
            for operation in (_primitive_operation(gate, index), _primitive_operation(measurement_gate, index))
        ]
    if kind == 'repeated_ladder_with_measurement':
        gate = str(generator['gate'])
        measurement_gate = str(generator['measurement_gate'])
        bit_count = int(generator['bit_count'])
        repeat_count = int(generator['repeat_count'])
        return [
            operation
            for _ in range(repeat_count)
            for bit_index in range(bit_count)
            for operation in (_primitive_operation(gate, bit_index), _primitive_operation(measurement_gate, bit_index))
        ]
    raise ValueError(f'unknown arithmetic primitive operation generator kind: {kind}')


def _ladder_operations(bit_count: int, include_measurement: bool) -> List[PrimitiveOperation]:
    primitive_operations: List[PrimitiveOperation] = []
    for bit_index in range(bit_count):
        primitive_operations.append(_primitive_operation('ccx', bit_index))
        if include_measurement:
            primitive_operations.append(_primitive_operation('measurement', bit_index))
    return primitive_operations


def _repeat_operations(operations: List[PrimitiveOperation], repeat_count: int) -> List[PrimitiveOperation]:
    return [
        operation
        for _ in range(int(repeat_count))
        for operation in operations
    ]


def _field_modular_add_operations(field_bits: int) -> List[PrimitiveOperation]:
    return (
        _ladder_operations(field_bits - 1, include_measurement=True)
        + _ladder_operations(field_bits - 1, include_measurement=True)
    )


def _field_modular_sub_operations(field_bits: int) -> List[PrimitiveOperation]:
    return (
        _ladder_operations(field_bits - 1, include_measurement=True)
        + _ladder_operations(field_bits - 1, include_measurement=True)
    )


def _field_mul_partial_product_operations(field_bits: int) -> List[PrimitiveOperation]:
    primitive_operations: List[PrimitiveOperation] = []
    for left_bit in range(field_bits):
        for right_bit in range(field_bits):
            primitive_operations.append(_primitive_operation('ccx', left_bit, right_bit))
    return primitive_operations


def _block(
    name: str,
    summary: str,
    instance_count: int,
    notes: List[str],
    primitive_operations: Optional[List[PrimitiveOperation]] = None,
    primitive_operation_generator: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    if primitive_operations is None and primitive_operation_generator is None:
        raise ValueError(f'{name} must provide primitive_operations or primitive_operation_generator')
    if primitive_operations is not None and primitive_operation_generator is not None:
        raise ValueError(f'{name} cannot provide both primitive_operations and primitive_operation_generator')
    if primitive_operations is not None:
        primitive_totals = _primitive_counts_from_operations(primitive_operations)
    else:
        primitive_totals = {
            key: int(primitive_operation_generator['primitive_counts_total'][key])
            for key in ('ccx', 'cx', 'x', 'measurement')
        }
    primitive_counts = {
        key: int(primitive_totals[key] // int(instance_count))
        for key in ('ccx', 'cx', 'x', 'measurement')
    }
    block = {
        'name': name,
        'summary': summary,
        'instance_count': int(instance_count),
        'primitive_counts_per_instance': primitive_counts,
        'primitive_counts_total': primitive_totals,
        'primitive_operation_encoding': ['gate', 'operand_0', 'operand_1'],
        'non_clifford_total': primitive_totals['ccx'],
        'notes': notes,
    }
    if primitive_operations is not None:
        block['primitive_operations'] = primitive_operations
    else:
        block['primitive_operation_generator'] = dict(primitive_operation_generator)
    return block


def _repeated_ladder_block(name: str, summary: str, bit_count: int, repeat_count: int, notes: List[str]) -> Dict[str, Any]:
    operation_count = int(bit_count) * int(repeat_count)
    return _block(
        name=name,
        summary=summary,
        instance_count=operation_count,
        primitive_operation_generator={
            'kind': 'repeated_ladder_with_measurement',
            'gate': 'ccx',
            'measurement_gate': 'measurement',
            'bit_count': int(bit_count),
            'repeat_count': int(repeat_count),
            'primitive_counts_total': _primitive_counts(ccx=operation_count, measurement=operation_count),
        },
        notes=notes,
    )


def _stage(name: str, summary: str, category: str, blocks: List[Dict[str, Any]], notes: List[str]) -> Dict[str, Any]:
    primitive_totals = {
        key: sum(int(block['primitive_counts_total'][key]) for block in blocks)
        for key in ('ccx', 'cx', 'x', 'measurement')
    }
    return {
        'name': name,
        'summary': summary,
        'category': category,
        'blocks': blocks,
        'primitive_counts_total': primitive_totals,
        'non_clifford_total': primitive_totals['ccx'],
        'notes': notes,
    }


def _kernel(opcode: str, summary: str, stages: List[Dict[str, Any]], notes: List[str]) -> Dict[str, Any]:
    primitive_totals = {
        key: sum(int(stage['primitive_counts_total'][key]) for stage in stages)
        for key in ('ccx', 'cx', 'x', 'measurement')
    }
    return {
        'opcode': opcode,
        'summary': summary,
        'stages': stages,
        'primitive_counts_total': primitive_totals,
        'exact_non_clifford_per_kernel': primitive_totals['ccx'],
        'notes': notes,
    }


def _modular_operation(opcode: str, field_bits: int) -> Mapping[str, Any]:
    circuit_ir = build_executable_modular_circuit_ir(
        field_bits=field_bits,
        shift=SECP256K1_PSEUDO_MERSENNE_SHIFT,
        low_term=SECP256K1_PSEUDO_MERSENNE_LOW_TERM,
        subtract_passes=SECP256K1_CANONICAL_SUBTRACT_PASSES,
    )
    return next(operation for operation in circuit_ir['operations'] if operation['opcode'] == opcode)


def _modular_step_block(step: Mapping[str, Any], field_bits: int) -> Dict[str, Any]:
    measured = bool(step['measured'])
    bit_count = int(step['bit_count'])
    repeat_count = int(step['repeat_count'])
    if step['kind'] == 'schoolbook_partial_products':
        return _block(
            name=str(step['name']),
            summary=str(step['semantic']),
            instance_count=bit_count * repeat_count,
            primitive_operations=_field_mul_partial_product_operations(field_bits),
            notes=['Generated directly from the executable modular circuit IR step.'],
        )
    return _block(
        name=str(step['name']),
        summary=str(step['semantic']),
        instance_count=bit_count * repeat_count,
        primitive_operation_generator={
            'kind': 'repeated_ladder_with_measurement' if measured else 'repeated_gate',
            'gate': 'ccx',
            'measurement_gate': 'measurement',
            'bit_count': bit_count,
            'repeat_count': repeat_count,
            'count': bit_count * repeat_count,
            'primitive_counts_total': {
                key: int(step['primitive_counts_total'][key])
                for key in ('ccx', 'cx', 'x', 'measurement')
            },
        },
        notes=['Generated directly from the executable modular circuit IR step.'],
    )


def _modular_grouped_kernel(
    *,
    field_bits: int,
    opcode: str,
    summary: str,
    stage_name: str,
    stage_summary: str,
    stage_category: str,
    notes: List[str],
) -> Dict[str, Any]:
    operation = _modular_operation(opcode, field_bits)
    return _kernel(
        opcode=opcode,
        summary=summary,
        stages=[
            _stage(
                name=stage_name,
                summary=stage_summary,
                category=stage_category,
                blocks=[
                    _modular_step_block(step, field_bits)
                    for step in operation['steps']
                ],
                notes=['This stage is generated from executable_modular_circuit_ir, not hand-written resource totals.'],
            )
        ],
        notes=[
            *notes,
            'Source: executable_modular_circuit_ir emitted by arithmetic_lowering.build_executable_modular_circuit_ir.',
        ],
    )


def _field_add_kernel(field_bits: int) -> Dict[str, Any]:
    return _modular_grouped_kernel(
        field_bits=field_bits,
        opcode='field_add',
        summary='Exact n-bit ripple-carry field-adder kernel over the checked leaf register width.',
        stage_name='carry_resolution',
        stage_summary='Temporary logical-AND carry ladder and canonical subtract-p correction for the field-adder kernel.',
        stage_category='adder',
        notes=[
            'The kernel contributes 2(n-1) non-Clifford operations for a 256-bit canonical field addition.',
        ],
    )


def _field_sub_kernel(field_bits: int) -> Dict[str, Any]:
    return _modular_grouped_kernel(
        field_bits=field_bits,
        opcode='field_sub',
        summary='Exact n-bit ripple-carry field-subtractor kernel over the checked leaf register width.',
        stage_name='borrow_resolution',
        stage_summary='Temporary logical-AND borrow ladder and canonical add-p correction for the field-subtractor kernel.',
        stage_category='subtractor',
        notes=[
            'The kernel contributes 2(n-1) non-Clifford operations for a 256-bit canonical field subtraction.',
        ],
    )


def _field_select_kernel(field_bits: int) -> Dict[str, Any]:
    selector = _block(
        name='bitwise_control_ladder',
        summary='One controlled field-bit select for each nontrivial bit position in the destination register.',
        instance_count=field_bits - 1,
        primitive_operations=_ladder_operations(field_bits - 1, include_measurement=False),
        notes=[
            'The select kernel is treated as a field-width controlled move whose non-Clifford cost matches the field-add kernel at this abstraction layer.',
        ],
    )
    return _kernel(
        opcode='select_field_if_flag',
        summary='Exact field-width conditional-select kernel used by the neutral-entry bypass path.',
        stages=[
            _stage(
                name='controlled_move',
                summary='Bitwise conditional move under the one-bit lookup-infinity flag.',
                category='select',
                blocks=[selector],
                notes=['The controlled move stays within the checked leaf register file and does not introduce a separate lookup-family dependency.'],
            )
        ],
        notes=[
            'The kernel contributes n-1 non-Clifford operations for a 256-bit conditional field select.',
        ],
    )


def _mul_const_kernel(field_bits: int, const_value: int) -> Dict[str, Any]:
    if const_value != 21:
        raise ValueError('the executable modular circuit IR currently exposes only the fixed 3b = 21 multiplier')
    operation = _modular_operation('mul_const', field_bits)
    return _kernel(
        opcode='mul_const',
        summary=f'Exact fixed-constant multiplication kernel for multiplication by {const_value}.',
        stages=[
            _stage(
                name='addition_chain',
                summary=f'Monotone addition-chain realization for multiplication by {const_value}.',
                category='mul_const',
                blocks=[
                    _modular_step_block(step, field_bits)
                    for step in operation['steps']
                ],
                notes=['The checked leaf uses a fixed 3b = 21 multiplier from executable_modular_circuit_ir.'],
            )
        ],
        notes=[
            f'The kernel uses the exact monotone addition chain {minimal_addition_chain(const_value)} for multiplication by {const_value}.',
            'Source: executable_modular_circuit_ir emitted by arithmetic_lowering.build_executable_modular_circuit_ir.',
        ],
    )


def _pseudo_mersenne_reduction_stages(field_bits: int, multiplication_count: int = 1) -> List[Dict[str, Any]]:
    first_fold_width = field_bits + SECP256K1_PSEUDO_MERSENNE_SHIFT
    second_fold_width = (
        SECP256K1_PSEUDO_MERSENNE_SHIFT
        + SECP256K1_PSEUDO_MERSENNE_LOW_TERM.bit_length()
        + 1
    )
    chain_steps = _binary_addition_chain_step_count(SECP256K1_PSEUDO_MERSENNE_LOW_TERM)
    first_shift_add = _repeated_ladder_block(
        name='first_fold_shift_add',
        summary='Add the high product half shifted by 32 bits using 2^256 = 2^32 + 977 mod p.',
        bit_count=first_fold_width - 1,
        repeat_count=multiplication_count,
        notes=[
            'This is the shifted 2^32 contribution in the first pseudo-Mersenne reduction fold.',
        ],
    )
    first_low_term = _repeated_ladder_block(
        name='first_fold_977_chain',
        summary='Add 977 times the high product half with a binary addition-chain multiplier.',
        bit_count=first_fold_width - 1,
        repeat_count=multiplication_count * chain_steps,
        notes=[
            f'The binary addition-chain multiplier for 977 uses {chain_steps} add/sub ladders.',
        ],
    )
    second_shift_add = _repeated_ladder_block(
        name='second_fold_shift_add',
        summary='Fold the residual high carry by adding it shifted by 32 bits.',
        bit_count=second_fold_width - 1,
        repeat_count=multiplication_count,
        notes=[
            'After the first fold, the remaining high component is narrow, so the second fold is not field-width.',
        ],
    )
    second_low_term = _repeated_ladder_block(
        name='second_fold_977_chain',
        summary='Add 977 times the residual high carry using the same binary chain.',
        bit_count=second_fold_width - 1,
        repeat_count=multiplication_count * chain_steps,
        notes=[
            'This finishes the pseudo-Mersenne fold for the small residual high component.',
        ],
    )
    canonical_subtracts = _repeated_ladder_block(
        name='canonical_subtract_p_ladders',
        summary='Two conditional subtract-p passes to return the product to the canonical field interval.',
        bit_count=field_bits - 1,
        repeat_count=multiplication_count * SECP256K1_CANONICAL_SUBTRACT_PASSES,
        notes=[
            'The two passes cover the bounded post-fold interval for p = 2^256 - 2^32 - 977.',
        ],
    )
    return [
        _stage(
            name='pseudo_mersenne_first_fold',
            summary='First pseudo-Mersenne fold of the 512-bit schoolbook product.',
            category='pseudo_mersenne_reduction',
            blocks=[first_shift_add, first_low_term],
            notes=[
                'This stage accounts for the non-free prime-field reduction work missing from a bare low-word multiplication model.',
            ],
        ),
        _stage(
            name='pseudo_mersenne_second_fold',
            summary='Second narrow pseudo-Mersenne fold for the residual high component.',
            category='pseudo_mersenne_reduction',
            blocks=[second_shift_add, second_low_term],
            notes=[
                'The residual high component is narrow because the first fold used the secp256k1 pseudo-Mersenne shape.',
            ],
        ),
        _stage(
            name='pseudo_mersenne_canonicalize',
            summary='Canonical post-reduction subtract-p correction.',
            category='canonical_mod_p_reduction',
            blocks=[canonical_subtracts],
            notes=[
                'This stage makes the field-multiplication contract a canonical mod-p operation rather than arithmetic modulo 2^256.',
            ],
        ),
    ]


def _field_mul_kernel(field_bits: int) -> Dict[str, Any]:
    operation = _modular_operation('field_mul', field_bits)
    stage_name_by_step = {
        'partial_product_grid': 'partial_products',
        'controlled_add_path': 'controlled_add_path',
        'controlled_sub_path': 'controlled_sub_path',
        'pseudo_mersenne_first_fold': 'pseudo_mersenne_first_fold',
        'pseudo_mersenne_second_fold': 'pseudo_mersenne_second_fold',
        'pseudo_mersenne_canonicalize': 'pseudo_mersenne_canonicalize',
    }
    category_by_step = {
        'partial_product_grid': 'schoolbook_grid',
        'controlled_add_path': 'controlled_add',
        'controlled_sub_path': 'controlled_subtract',
        'pseudo_mersenne_first_fold': 'pseudo_mersenne_reduction',
        'pseudo_mersenne_second_fold': 'pseudo_mersenne_reduction',
        'pseudo_mersenne_canonicalize': 'canonical_mod_p_reduction',
    }
    return _kernel(
        opcode='field_mul',
        summary='Exact schoolbook controlled add-subtract field-multiplication kernel with secp256k1 pseudo-Mersenne mod-p reduction.',
        stages=[
            _stage(
                name=stage_name_by_step[str(step['name'])],
                summary=str(step['semantic']),
                category=category_by_step[str(step['name'])],
                blocks=[_modular_step_block(step, field_bits)],
                notes=['Generated directly from executable_modular_circuit_ir.'],
            )
            for step in operation['steps']
        ],
        notes=[
            'The kernel reconstructs the controlled add-subtract schoolbook core plus explicit pseudo-Mersenne reduction and canonical subtract-p correction for secp256k1.',
            'Source: executable_modular_circuit_ir emitted by arithmetic_lowering.build_executable_modular_circuit_ir.',
        ],
    )


def _field_double_mul_kernel(field_bits: int, opcode: str, combine_opcode: str, summary: str) -> Dict[str, Any]:
    operation = _modular_operation(opcode, field_bits)
    stages = []
    for step in operation['steps']:
        step_name = str(step['name'])
        if step_name.startswith('first_product_'):
            category_prefix = 'first_product'
        elif step_name.startswith('second_product_'):
            category_prefix = 'second_product'
        elif step_name.startswith('combine_'):
            category_prefix = 'combine'
        else:
            raise ValueError(f'unexpected {opcode} step name: {step_name}')
        stages.append(_stage(
            name=step_name,
            summary=str(step['semantic']),
            category=f'{category_prefix}_accumulator',
            blocks=[_modular_step_block(step, field_bits)],
            notes=[
                f'Generated directly from executable_modular_circuit_ir for {opcode}.',
                'The scheduled primitive netlist maps this step to the final target accumulator, not to a materialized product field lane.',
            ],
        ))
    return _kernel(
        opcode=opcode,
        summary=summary,
        stages=stages,
        notes=[
            f'This fused kernel has the same primitive count as two field_mul kernels plus one {combine_opcode} kernel.',
            'It exists so the global primitive stream can bind fused output arithmetic without virtual product_0/product_1 field registers.',
            'Source: executable_modular_circuit_ir emitted by arithmetic_lowering.build_executable_modular_circuit_ir.',
        ],
    )


def _standard_qroam_coordinate_stream_cost(field_bits: int, domain_size: int, block_size: int = DEFAULT_QROAM_CLEAN_BLOCK_SIZE) -> Dict[str, int]:
    lookup_compute = (domain_size + block_size - 1) // block_size + (block_size - 1) * field_bits
    measured_uncompute = (domain_size + block_size - 1) // block_size + (block_size - 1)
    junk_register_count = block_size - 1
    junk_register_qubits = junk_register_count * field_bits
    target_register_qubits = field_bits
    return {
        'domain_size': domain_size,
        'block_size': block_size,
        'field_bits': field_bits,
        'target_register_qubits': target_register_qubits,
        'junk_register_count': junk_register_count,
        'junk_register_bitsize': field_bits,
        'junk_register_qubits': junk_register_qubits,
        'peak_qroam_data_qubits': target_register_qubits + junk_register_qubits,
        'lookup_compute_non_clifford': lookup_compute,
        'measured_uncompute_non_clifford': measured_uncompute,
        'total_non_clifford': lookup_compute + measured_uncompute,
    }

def _streamed_lookup_bit_oracle_stage(field_bits: int, bit_source: str, qroam_block_size: int, qroam_domain_size: int) -> Dict[str, Any]:
    cost = _standard_qroam_coordinate_stream_cost(field_bits, domain_size=qroam_domain_size, block_size=qroam_block_size)
    compute_block = _block(
        name=f'streamed_{bit_source}_standard_qroam_compute',
        summary=f'Standard QROAM compute for one selected {bit_source} coordinate stream.',
        instance_count=1,
        primitive_operation_generator={
            'kind': 'repeated_gate',
            'gate': 'ccx',
            'count': cost['lookup_compute_non_clifford'],
            'primitive_counts_total': _primitive_counts(ccx=cost['lookup_compute_non_clifford']),
        },
        notes=[
            f"The block uses the standard QROAM cost N/K + (K - 1)b with N={cost['domain_size']}, K={cost['block_size']}, and b={field_bits}.",
            f"The matching workspace contract must count the {field_bits}-qubit target register plus {cost['junk_register_count']} junk registers of {field_bits} qubits each.",
        ],
    )
    uncompute_block = _block(
        name=f'streamed_{bit_source}_standard_qroam_measured_uncompute',
        summary=f'Measured standard-QROAM cleanup for one selected {bit_source} coordinate stream.',
        instance_count=1,
        primitive_operation_generator={
            'kind': 'repeated_gate_with_measurement',
            'gate': 'ccx',
            'measurement_gate': 'measurement',
            'count': cost['measured_uncompute_non_clifford'],
            'primitive_counts_total': _primitive_counts(
                ccx=cost['measured_uncompute_non_clifford'],
                measurement=cost['measured_uncompute_non_clifford'],
            ),
        },
        notes=[
            f"The measured cleanup uses the standard QROAM adjoint cost N/K + (K - 1) with N={cost['domain_size']} and K={cost['block_size']}.",
            'The cleanup is paired with the same coordinate target and junk registers before the next lookup-controlled arithmetic kernel starts.',
        ],
    )
    return _stage(
        name=f'streamed_{bit_source}_standard_qroam_oracle',
        summary=f'Standard QROAM table-data selection for one {field_bits}-bit streamed {bit_source} coordinate.',
        category='streamed_lookup_data_select',
        blocks=[compute_block, uncompute_block],
        notes=[
            'This stage replaces the rejected bitwise-banked path-select model with a standard QROAM primitive-circuit data stream.',
            'The lookup coordinate target and its QROAMClean junk registers are counted by the lookup workspace contract while the consuming arithmetic kernel runs.',
        ],
    )


def _renamed_field_mul_kernel(
    field_bits: int,
    opcode: str,
    summary: str,
    note: str,
    lookup_bit_source: str | None = None,
    qroam_block_size: int = DEFAULT_QROAM_CLEAN_BLOCK_SIZE,
    qroam_domain_size: int | None = None,
) -> Dict[str, Any]:
    kernel = deepcopy(_field_mul_kernel(field_bits))
    kernel['opcode'] = opcode
    kernel['summary'] = summary
    if lookup_bit_source is not None:
        if qroam_domain_size is None:
            raise ValueError('qroam_domain_size is required for streamed lookup arithmetic kernels')
        kernel['stages'].insert(0, _streamed_lookup_bit_oracle_stage(field_bits, lookup_bit_source, qroam_block_size, qroam_domain_size))
        primitive_totals = {
            key: sum(int(stage['primitive_counts_total'][key]) for stage in kernel['stages'])
            for key in ('ccx', 'cx', 'x', 'measurement')
        }
        kernel['primitive_counts_total'] = primitive_totals
        kernel['exact_non_clifford_per_kernel'] = primitive_totals['ccx']
    kernel['notes'] = [*kernel['notes'], note]
    return kernel


def _field_sub_sum_kernel(field_bits: int) -> Dict[str, Any]:
    return _modular_grouped_kernel(
        field_bits=field_bits,
        opcode='field_sub_sum',
        summary='Exact fused two-subtraction field kernel for a - b - c.',
        stage_name='borrow_resolution_pair',
        stage_summary='Two sequential canonical modular subtractors.',
        stage_category='subtractor',
        notes=[
            'The kernel contributes 4(n-1) non-Clifford operations for a 256-bit field value.',
            'The streamed lookup tail uses this fused opcode for K = H - A - I.',
        ],
    )


def _field_triple_kernel(field_bits: int) -> Dict[str, Any]:
    return _modular_grouped_kernel(
        field_bits=field_bits,
        opcode='field_triple',
        summary='Exact fused two-addition field kernel for multiplication by 3.',
        stage_name='carry_resolution_pair',
        stage_summary='Two sequential canonical modular adders.',
        stage_category='adder',
        notes=[
            'The kernel contributes 4(n-1) non-Clifford operations for a 256-bit field value.',
            'The streamed lookup tail uses this fused opcode for L = 3A.',
        ],
    )


def _complete_a0_streamed_tail_kernel(field_bits: int, qroam_block_size: int, qroam_domain_size: int) -> Dict[str, Any]:
    streamed_i = deepcopy(_renamed_field_mul_kernel(
        field_bits,
        'field_mul_lookup_y',
        'Internal streamed I = Y*y multiplication used by the complete-add tail macro.',
        'This stage is counted inside the macro because I is not materialized as a standalone leaf field value.',
        lookup_bit_source='lookup_y',
        qroam_block_size=qroam_block_size,
        qroam_domain_size=qroam_domain_size,
    )['stages'])
    streamed_yz = deepcopy(_renamed_field_mul_kernel(
        field_bits,
        'field_mul_lookup_y',
        'Internal streamed yZ multiplication used by the complete-add tail macro.',
        'This stage is counted inside the macro because yZ is not materialized as a standalone leaf field value.',
        lookup_bit_source='lookup_y',
        qroam_block_size=qroam_block_size,
        qroam_domain_size=qroam_domain_size,
    )['stages'])
    for stage in streamed_i:
        stage['name'] = f"tail_i_{stage['name']}"
    for stage in streamed_yz:
        stage['name'] = f"tail_yz_{stage['name']}"
    derive_k = _block(
        name='derive_k_modular_subtractors',
        summary='Two canonical field-subtractors for K = H - A - I inside the streamed tail macro.',
        instance_count=4 * (field_bits - 1),
        primitive_operations=_repeat_operations(_field_modular_sub_operations(field_bits), 2),
        notes=[
            'This is the same two-subtraction cost as the standalone field_sub_sum kernel.',
        ],
    )
    derive_l = _block(
        name='derive_l_modular_adders',
        summary='Two canonical field-adders for L = 3A inside the streamed tail macro.',
        instance_count=4 * (field_bits - 1),
        primitive_operations=_repeat_operations(_field_modular_add_operations(field_bits), 2),
        notes=[
            'This is the same two-addition cost as the standalone field_triple kernel.',
        ],
    )
    fixed_f = _block(
        name='fixed_21z_chain',
        summary='Fixed multiplication F = 21Z inside the streamed tail macro.',
        instance_count=12 * (field_bits - 1),
        primitive_operations=_repeat_operations(_field_modular_add_operations(field_bits), 6),
        notes=[
            'The checked field constant is 3b = 21, whose monotone addition chain has six canonical field-add steps.',
        ],
    )
    internal_combines = _block(
        name='three_internal_combine_ladders',
        summary='Three canonical field add/sub combines for E = Y + yZ, M = I + F, and N = I - F.',
        instance_count=6 * (field_bits - 1),
        primitive_operations=_repeat_operations(_field_modular_add_operations(field_bits), 3),
        notes=[
            'These combines are inside the macro boundary because E, M, and N are never standalone counted field wires.',
        ],
    )
    partial_products = _block(
        name='six_partial_product_grids',
        summary='Six schoolbook partial-product grids for KN, EC, NM, CL, ME, and LK.',
        instance_count=6 * field_bits * field_bits,
        primitive_operations=[
            operation
            for _ in range(6)
            for operation in _field_mul_partial_product_operations(field_bits)
        ],
        notes=[
            'The multi-output tail has six field-multiplication products and no materialized intermediate field lane outside the macro boundary.',
        ],
    )
    controlled_add_path = _block(
        name='six_controlled_add_accumulators',
        summary='Six controlled-add accumulator paths, one for each tail multiplication.',
        instance_count=6 * (field_bits - 1),
        primitive_operations=[
            operation
            for _ in range(6)
            for operation in _ladder_operations(field_bits - 1, include_measurement=True)
        ],
        notes=[
            'This block preserves the same controlled add-subtract multiplier cost used by field_mul.',
        ],
    )
    controlled_sub_path = _block(
        name='six_controlled_sub_accumulators',
        summary='Six controlled-subtract accumulator paths, one for each tail multiplication.',
        instance_count=6 * field_bits,
        primitive_operations=[
            operation
            for _ in range(6)
            for operation in _ladder_operations(field_bits, include_measurement=True)
        ],
        notes=[
            'This block preserves the same controlled add-subtract multiplier cost used by field_mul.',
        ],
    )
    output_combine = _block(
        name='three_output_combine_ladders',
        summary='Three canonical field add/sub combine ladders for X3, Y3, and Z3 after the six products.',
        instance_count=6 * (field_bits - 1),
        primitive_operations=_repeat_operations(_field_modular_add_operations(field_bits), 3),
        notes=[
            'The output combines are counted as three ordinary field add/sub kernels.',
        ],
    )
    y3_in_place_guard = _block(
        name='y3_in_place_zero_lift_guard',
        summary='Compute and uncompute the one-bit L == 0 guard used by the reversible Y3-over-C output permutation.',
        instance_count=2 * (field_bits - 1),
        primitive_operations=_repeat_operations(_ladder_operations(field_bits - 1, include_measurement=False), 2),
        notes=[
            'The guard lifts the Y3-over-C affine coefficient from L to 1 on the L == 0 accumulator-infinity branch, making the in-place output row a field permutation.',
        ],
    )
    return _kernel(
        opcode='complete_a0_streamed_tail',
        summary='Exact multi-output complete-add tail kernel from C, H, A, Y, and Z.',
        stages=[
            *streamed_i,
            _stage(
                name='tail_derive_k_l',
                summary='Internal construction of K = H - A - I and L = 3A.',
                category='tail_combine',
                blocks=[derive_k, derive_l],
                notes=['These four add/sub ladders avoid materializing I, K, and L as leaf-owned field wires.'],
            ),
            *streamed_yz,
            _stage(
                name='tail_fixed_21z',
                summary='Internal fixed multiplication F = 21Z.',
                category='mul_const',
                blocks=[fixed_f],
                notes=['This is the same six-addition-chain cost used by the standalone mul_const-by-21 kernel.'],
            ),
            _stage(
                name='tail_internal_combines',
                summary='Internal construction of E, M, and N.',
                category='tail_combine',
                blocks=[internal_combines],
                notes=['These three add/sub kernels avoid materializing E, M, and N as leaf-owned field wires.'],
            ),
            _stage(
                name='tail_partial_products',
                summary='Six schoolbook partial-product grids for the complete-add tail.',
                category='schoolbook_grid',
                blocks=[partial_products],
                notes=['This is the dominant part of the tail macro and corresponds to six field multiplications.'],
            ),
            _stage(
                name='tail_controlled_add_path',
                summary='Controlled-add paths for the six tail multiplications.',
                category='controlled_add',
                blocks=[controlled_add_path],
                notes=['Counted exactly as six field-mul add paths.'],
            ),
            _stage(
                name='tail_controlled_sub_path',
                summary='Controlled-subtract paths for the six tail multiplications.',
                category='controlled_subtract',
                blocks=[controlled_sub_path],
                notes=['Counted exactly as six field-mul subtract paths.'],
            ),
            *[
                {
                    **stage,
                    'name': f'tail_{stage["name"]}',
                    'notes': [
                        *stage['notes'],
                        'Counted for all six internal tail multiplications before the output combine stage.',
                    ],
                }
                for stage in _pseudo_mersenne_reduction_stages(field_bits, multiplication_count=6)
            ],
            _stage(
                name='tail_output_combine',
                summary='Three add/sub combines that write X3, Y3, and Z3.',
                category='tail_combine',
                blocks=[output_combine, y3_in_place_guard],
                notes=['Counted as three field add/sub kernels plus the reversible zero-lift guard required by the seven-slot fused-output schedule.'],
            ),
        ],
        notes=[
            'The macro is a liveness contract, not a free arithmetic operation: its non-Clifford count includes I, K, L, yZ, 21Z, E/M/N, six output multipliers, three output add/sub combines, and the Y3-over-C zero-lift guard.',
        ],
    )


def _complete_a0_fully_streamed_tail_kernel(field_bits: int, qroam_block_size: int, qroam_domain_size: int) -> Dict[str, Any]:
    streamed_a = deepcopy(_renamed_field_mul_kernel(
        field_bits,
        'field_mul_lookup_x',
        'Internal streamed A = X*x multiplication used by the fully streamed complete-add tail macro.',
        'This stage is counted inside the macro because A is not materialized as a standalone leaf field value.',
        lookup_bit_source='lookup_x',
        qroam_block_size=qroam_block_size,
        qroam_domain_size=qroam_domain_size,
    )['stages'])
    streamed_zx = deepcopy(_renamed_field_mul_kernel(
        field_bits,
        'field_mul_lookup_x',
        'Internal streamed Zx = Z*x multiplication used by the fully streamed complete-add tail macro.',
        'This stage is counted inside the macro because Zx is not materialized as a standalone leaf field value.',
        lookup_bit_source='lookup_x',
        qroam_block_size=qroam_block_size,
        qroam_domain_size=qroam_domain_size,
    )['stages'])
    for stage in streamed_a:
        stage['name'] = f"tail_a_{stage['name']}"
    for stage in streamed_zx:
        stage['name'] = f"tail_zx_{stage['name']}"
    derive_c_input = _block(
        name='derive_c_input_modular_adder',
        summary='One canonical field-adder for C input X + Zx inside the fully streamed tail macro.',
        instance_count=2 * (field_bits - 1),
        primitive_operations=_field_modular_add_operations(field_bits),
        notes=[
            'This is the same cost as the standalone field_add kernel, moved inside the macro boundary.',
        ],
    )
    derive_c_fixed = _block(
        name='derive_c_fixed_21_chain',
        summary='Fixed multiplication C = 21(X + Zx) inside the fully streamed tail macro.',
        instance_count=12 * (field_bits - 1),
        primitive_operations=_repeat_operations(_field_modular_add_operations(field_bits), 6),
        notes=[
            'The checked field constant is 3b = 21, whose monotone addition chain has six canonical field-add steps.',
        ],
    )
    streamed_tail = _complete_a0_streamed_tail_kernel(field_bits, qroam_block_size, qroam_domain_size)
    inherited_stages = deepcopy(streamed_tail['stages'])
    for stage in inherited_stages:
        stage['name'] = f"fully_streamed_{stage['name']}"
    return _kernel(
        opcode='complete_a0_fully_streamed_tail',
        summary='Exact multi-output complete-add tail kernel from X, H, Y, and Z with all lookup-x/y products internal.',
        stages=[
            *streamed_a,
            *streamed_zx,
            _stage(
                name='tail_derive_c',
                summary='Internal construction of C = 21(X + Zx).',
                category='tail_combine',
                blocks=[derive_c_input, derive_c_fixed],
                notes=['These add-chain ladders avoid materializing Zx and C as leaf-owned field wires.'],
            ),
            *inherited_stages,
        ],
        notes=[
            'The macro is a liveness contract, not a free arithmetic operation: its non-Clifford count includes A, Zx, C, I, K, L, yZ, 21Z, E/M/N, six output multipliers, and three output add/sub combines.',
        ],
    )


def _complete_a0_all_streamed_tail_kernel(field_bits: int, qroam_block_size: int, qroam_domain_size: int) -> Dict[str, Any]:
    derive_g = _block(
        name='derive_g_modular_adder',
        summary='One canonical field-adder for G = X + Y inside the all-streamed tail macro.',
        instance_count=2 * (field_bits - 1),
        primitive_operations=_field_modular_add_operations(field_bits),
        notes=[
            'This is the same cost as the standalone field_add kernel, moved inside the macro boundary.',
        ],
    )
    streamed_h = deepcopy(_renamed_field_mul_kernel(
        field_bits,
        'field_mul_lookup_sum',
        'Internal streamed H = (X + Y)(x + y) multiplication used by the all-streamed complete-add tail macro.',
        'This stage is counted inside the macro because H is not materialized as a standalone leaf field value.',
        lookup_bit_source='lookup_x_plus_y',
        qroam_block_size=qroam_block_size,
        qroam_domain_size=qroam_domain_size,
    )['stages'])
    for stage in streamed_h:
        stage['name'] = f"tail_h_{stage['name']}"
    inherited_stages = deepcopy(_complete_a0_fully_streamed_tail_kernel(field_bits, qroam_block_size, qroam_domain_size)['stages'])
    for stage in inherited_stages:
        stage['name'] = f"all_streamed_{stage['name']}"
    return _kernel(
        opcode='complete_a0_all_streamed_tail',
        summary='Exact multi-output complete-add tail kernel from X, Y, and Z with all lookup-coordinate products internal.',
        stages=[
            _stage(
                name='tail_derive_g',
                summary='Internal construction of G = X + Y.',
                category='tail_combine',
                blocks=[derive_g],
                notes=['This adder avoids materializing G as a leaf-owned field wire.'],
            ),
            *streamed_h,
            *inherited_stages,
        ],
        notes=[
            'The macro is a liveness contract, not a free arithmetic operation: its non-Clifford count includes G, H, A, Zx, C, I, K, L, yZ, 21Z, E/M/N, six output multipliers, and three output add/sub combines.',
        ],
    )


def _leaf_reconstruction(leaf_opcode_histogram: Mapping[str, int], kernels: List[Dict[str, Any]]) -> Dict[str, Any]:
    kernel_lookup = {kernel['opcode']: kernel for kernel in kernels}
    per_opcode = []
    arithmetic_leaf_non_clifford = 0
    primitive_totals = {'ccx': 0, 'cx': 0, 'x': 0, 'measurement': 0}
    for opcode, count in sorted(leaf_opcode_histogram.items()):
        if opcode not in kernel_lookup or count == 0:
            continue
        kernel = kernel_lookup[opcode]
        kernel_primitive_totals = {
            key: int(kernel['primitive_counts_total'][key]) * int(count)
            for key in ('ccx', 'cx', 'x', 'measurement')
        }
        arithmetic_leaf_non_clifford += kernel_primitive_totals['ccx']
        for key in primitive_totals:
            primitive_totals[key] += kernel_primitive_totals[key]
        per_opcode.append(
            {
                'opcode': opcode,
                'per_leaf_instance_count': int(count),
                'kernel_non_clifford_per_instance': int(kernel['exact_non_clifford_per_kernel']),
                'kernel_non_clifford_total': int(kernel['exact_non_clifford_per_kernel']) * int(count),
                'primitive_totals_total': kernel_primitive_totals,
            }
        )
    return {
        'leaf_opcode_histogram': dict(leaf_opcode_histogram),
        'per_opcode': per_opcode,
        'primitive_totals': primitive_totals,
        'arithmetic_leaf_non_clifford': arithmetic_leaf_non_clifford,
    }


def _tail_macro_engine_from_kernels(field_bits: int, counted_arithmetic_slots: int, kernels: List[Dict[str, Any]]) -> Dict[str, Any]:
    kernel_lookup = {kernel['opcode']: kernel for kernel in kernels}
    selected_tail_kernel = kernel_lookup[TAIL_MACRO_OPCODE]
    return build_tail_macro_engine(
        field_bits=field_bits,
        counted_arithmetic_slots=counted_arithmetic_slots,
        kernel_non_clifford_by_opcode={
            opcode: int(kernel['exact_non_clifford_per_kernel'])
            for opcode, kernel in kernel_lookup.items()
        },
        selected_tail_kernel_non_clifford=int(selected_tail_kernel['exact_non_clifford_per_kernel']),
    )


def arithmetic_lowering_library(
    field_bits: int,
    leaf_opcode_histogram: Mapping[str, int],
    qroam_block_size: int = DEFAULT_QROAM_CLEAN_BLOCK_SIZE,
    qroam_domain_size: int | None = None,
    counted_arithmetic_slots: int = 3,
) -> Dict[str, Any]:
    if qroam_domain_size is None:
        raise ValueError('qroam_domain_size must be supplied by the compiler parameter source')
    kernels = [
        _field_mul_kernel(field_bits),
        _renamed_field_mul_kernel(
            field_bits,
            'field_mul_lookup_x',
            'Exact table-fed x-coordinate field multiplication kernel with no materialized lookup-output field lane.',
            'The streamed lookup coordinate is a table-controlled constant input and is not counted as a leaf field wire.',
            lookup_bit_source='lookup_x',
            qroam_block_size=qroam_block_size,
            qroam_domain_size=qroam_domain_size,
        ),
        _renamed_field_mul_kernel(
            field_bits,
            'field_mul_lookup_y',
            'Exact table-fed y-coordinate field multiplication kernel with no materialized lookup-output field lane.',
            'The streamed lookup coordinate is a table-controlled constant input and is not counted as a leaf field wire.',
            lookup_bit_source='lookup_y',
            qroam_block_size=qroam_block_size,
            qroam_domain_size=qroam_domain_size,
        ),
        _renamed_field_mul_kernel(
            field_bits,
            'field_mul_lookup_sum',
            'Exact table-fed (x+y)-coordinate field multiplication kernel with no materialized lookup-output field lane.',
            'The streamed lookup sum is a table-controlled constant input and is not counted as a leaf field wire.',
            lookup_bit_source='lookup_x_plus_y',
            qroam_block_size=qroam_block_size,
            qroam_domain_size=qroam_domain_size,
        ),
        _field_add_kernel(field_bits),
        _field_sub_kernel(field_bits),
        _field_sub_sum_kernel(field_bits),
        _field_triple_kernel(field_bits),
        _field_double_mul_kernel(
            field_bits,
            'field_double_mul_add',
            'field_add',
            'Exact fused output kernel for a*b + c*d without materialized product field lanes.',
        ),
        _field_double_mul_kernel(
            field_bits,
            'field_double_mul_sub',
            'field_sub',
            'Exact fused output kernel for a*b - c*d without materialized product field lanes.',
        ),
        _complete_a0_streamed_tail_kernel(field_bits, qroam_block_size, qroam_domain_size),
        _complete_a0_fully_streamed_tail_kernel(field_bits, qroam_block_size, qroam_domain_size),
        _complete_a0_all_streamed_tail_kernel(field_bits, qroam_block_size, qroam_domain_size),
        _mul_const_kernel(field_bits, 21),
        _field_select_kernel(field_bits),
    ]
    return {
        'schema': 'compiler-project-arithmetic-lowerings-v2',
        'family': {
            'name': 'litinski_addsub_schoolbook_v1',
            'summary': 'Exact arithmetic-kernel family with generated primitive-operation inventories for schoolbook multiplication, table-fed multiplication, fused add/sub tail kernels, conditional select, and fixed multiplication by 21.',
            'gate_set': 'Clifford + Toffoli-style arithmetic + measurement',
            'field_bits': int(field_bits),
            'standard_qroam_clean_block_size': int(qroam_block_size),
            'exact_scope': 'exact non-Clifford counts and generated primitive-operation inventories for the named arithmetic-kernel family; Clifford micro-counts remain outside the shipped lowering layer',
            'source_references': [
                {
                    'title': 'Quantum schoolbook multiplication with fewer Toffoli gates',
                    'url': 'https://arxiv.org/abs/2410.00899',
                    'reason': 'Provides the controlled add-subtract schoolbook multiplier family and its n^2 + 2n - 1 Toffoli-style cost model.',
                },
                {
                    'title': 'Halving the cost of quantum addition',
                    'url': 'https://arxiv.org/abs/1709.06648',
                    'reason': 'Provides the temporary logical-AND adder family used for the n-1-cost add/sub/select kernels at this layer.',
                },
            ],
            'notes': [
                'Each arithmetic block carries a generated primitive-operation inventory whose totals reconstruct the published per-kernel counts.',
                'The lowering stays at the non-Clifford and measurement layer. It does not publish bit-for-bit Clifford micro-expansions for every 256-bit kernel.',
            ],
        },
        'executable_modular_circuit_ir': build_executable_modular_circuit_ir(
            field_bits=field_bits,
            shift=SECP256K1_PSEUDO_MERSENNE_SHIFT,
            low_term=SECP256K1_PSEUDO_MERSENNE_LOW_TERM,
            subtract_passes=SECP256K1_CANONICAL_SUBTRACT_PASSES,
        ),
        'tail_macro_engine': _tail_macro_engine_from_kernels(field_bits, counted_arithmetic_slots, kernels),
        'kernels': kernels,
        'leaf_reconstruction': _leaf_reconstruction(leaf_opcode_histogram, kernels),
    }


def arithmetic_kernel_summary(arithmetic_lowerings: Mapping[str, Any]) -> Dict[str, Any]:
    family = arithmetic_lowerings['family']
    kernel_lookup = {kernel['opcode']: kernel for kernel in arithmetic_lowerings['kernels']}
    reconstruction = arithmetic_lowerings['leaf_reconstruction']
    chain_stage = next(kernel for kernel in arithmetic_lowerings['kernels'] if kernel['opcode'] == 'mul_const')['stages'][0]
    addition_chain_21 = [1]
    for block in chain_stage['blocks']:
        parts = block['name'].split('_')
        left = parts[1]
        right = parts[3]
        left_value = int(left)
        right_value = int(right)
        if addition_chain_21[-1] != left_value:
            addition_chain_21.append(left_value)
        addition_chain_21.append(right_value)
    return {
        'schema': 'compiler-project-arithmetic-kernels-v3',
        'name': family['name'],
        'summary': family['summary'],
        'gate_set': family['gate_set'],
        'field_mul_non_clifford': kernel_lookup['field_mul']['exact_non_clifford_per_kernel'],
        'field_add_non_clifford': kernel_lookup['field_add']['exact_non_clifford_per_kernel'],
        'field_sub_non_clifford': kernel_lookup['field_sub']['exact_non_clifford_per_kernel'],
        'select_non_clifford': kernel_lookup['select_field_if_flag']['exact_non_clifford_per_kernel'],
        'mul_const_non_clifford': kernel_lookup['mul_const']['exact_non_clifford_per_kernel'],
        'field_mul_lookup_non_clifford': kernel_lookup['field_mul_lookup_x']['exact_non_clifford_per_kernel'],
        'field_sub_sum_non_clifford': kernel_lookup['field_sub_sum']['exact_non_clifford_per_kernel'],
        'field_triple_non_clifford': kernel_lookup['field_triple']['exact_non_clifford_per_kernel'],
        'complete_a0_streamed_tail_non_clifford': kernel_lookup['complete_a0_streamed_tail']['exact_non_clifford_per_kernel'],
        'arithmetic_leaf_non_clifford': reconstruction['arithmetic_leaf_non_clifford'],
        'leaf_opcode_histogram': reconstruction['leaf_opcode_histogram'],
        'exact_scope': family['exact_scope'],
        'notes': family['notes'],
        'addition_chain_21': addition_chain_21,
        'arithmetic_lowering_artifact': 'compiler_verification_project/artifacts/arithmetic_lowerings.json',
    }
