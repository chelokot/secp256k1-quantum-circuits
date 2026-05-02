#!/usr/bin/env python3

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Mapping

from derived_resources import minimal_addition_chain


PrimitiveOperation = List[int | str]


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


def _ladder_operations(bit_count: int, include_measurement: bool) -> List[PrimitiveOperation]:
    primitive_operations: List[PrimitiveOperation] = []
    for bit_index in range(bit_count):
        primitive_operations.append(_primitive_operation('ccx', bit_index))
        if include_measurement:
            primitive_operations.append(_primitive_operation('measurement', bit_index))
    return primitive_operations


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
    primitive_operations: List[PrimitiveOperation],
    notes: List[str],
) -> Dict[str, Any]:
    primitive_totals = _primitive_counts_from_operations(primitive_operations)
    primitive_counts = {
        key: int(primitive_totals[key] // int(instance_count))
        for key in ('ccx', 'cx', 'x', 'measurement')
    }
    return {
        'name': name,
        'summary': summary,
        'instance_count': int(instance_count),
        'primitive_counts_per_instance': primitive_counts,
        'primitive_counts_total': primitive_totals,
        'primitive_operation_encoding': ['gate', 'operand_0', 'operand_1'],
        'primitive_operations': primitive_operations,
        'non_clifford_total': primitive_totals['ccx'],
        'notes': notes,
    }


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


def _field_add_kernel(field_bits: int) -> Dict[str, Any]:
    ladder = _block(
        name='temporary_and_carry_ladder',
        summary='One temporary logical-AND edge per carry transition in the ripple-carry adder.',
        instance_count=field_bits - 1,
        primitive_operations=_ladder_operations(field_bits - 1, include_measurement=True),
        notes=[
            'This stage follows the temporary logical-AND carry pattern used for n-bit addition.',
            'The local measurement-reset path is counted inside the same stage inventory.',
        ],
    )
    return _kernel(
        opcode='field_add',
        summary='Exact n-bit ripple-carry field-adder kernel over the checked leaf register width.',
        stages=[
            _stage(
                name='carry_resolution',
                summary='Temporary logical-AND carry ladder for the field-adder kernel.',
                category='adder',
                blocks=[ladder],
                notes=['The adder kernel is counted as a single carry-resolution stage because the repository only prices non-Clifford work at this layer.'],
            )
        ],
        notes=[
            'The kernel contributes n-1 non-Clifford operations for a 256-bit field addition.',
        ],
    )


def _field_sub_kernel(field_bits: int) -> Dict[str, Any]:
    ladder = _block(
        name='temporary_and_borrow_ladder',
        summary='One temporary logical-AND edge per borrow transition in the ripple-carry subtractor.',
        instance_count=field_bits - 1,
        primitive_operations=_ladder_operations(field_bits - 1, include_measurement=True),
        notes=[
            'The subtractor reuses the same n-1 temporary logical-AND structure as the adder, interpreted as a borrow ladder.',
        ],
    )
    return _kernel(
        opcode='field_sub',
        summary='Exact n-bit ripple-carry field-subtractor kernel over the checked leaf register width.',
        stages=[
            _stage(
                name='borrow_resolution',
                summary='Temporary logical-AND borrow ladder for the field-subtractor kernel.',
                category='subtractor',
                blocks=[ladder],
                notes=['The subtractor kernel is counted as a single borrow-resolution stage at the non-Clifford layer.'],
            )
        ],
        notes=[
            'The kernel contributes n-1 non-Clifford operations for a 256-bit field subtraction.',
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
    chain = minimal_addition_chain(const_value)
    blocks = []
    for left, right in zip(chain, chain[1:]):
        blocks.append(
            _block(
                name=f'chain_step_{left}_to_{right}',
                summary=f'One field-add kernel step in the monotone addition chain {left} -> {right}.',
                instance_count=1,
                primitive_operations=_ladder_operations(field_bits - 1, include_measurement=True),
                notes=[
                    'Each chain step reuses the checked field-add kernel cost over the same 256-bit register width.',
                ],
            )
        )
    return _kernel(
        opcode='mul_const',
        summary=f'Exact fixed-constant multiplication kernel for multiplication by {const_value}.',
        stages=[
            _stage(
                name='addition_chain',
                summary=f'Monotone addition-chain realization for multiplication by {const_value}.',
                category='mul_const',
                blocks=blocks,
                notes=['The checked leaf uses a fixed 3b = 21 multiplier, so the addition chain is exact and machine-readable.'],
            )
        ],
        notes=[
            f'The kernel uses the exact monotone addition chain {chain} for multiplication by {const_value}.',
        ],
    )


def _field_mul_kernel(field_bits: int) -> Dict[str, Any]:
    partial_products = _block(
        name='partial_product_grid',
        summary='One schoolbook partial-product interaction for each pair of field bits.',
        instance_count=field_bits * field_bits,
        primitive_operations=_field_mul_partial_product_operations(field_bits),
        notes=[
            'This stage records the n^2 schoolbook bit-product interactions in the controlled add-subtract multiplier family.',
        ],
    )
    controlled_add_path = _block(
        name='controlled_add_accumulator',
        summary='Carry-resolution path for the controlled-add half of the schoolbook multiplier.',
        instance_count=field_bits - 1,
        primitive_operations=_ladder_operations(field_bits - 1, include_measurement=True),
        notes=[
            'This stage accounts for the n-1 carry transitions in the add half of the controlled add-subtract multiplier.',
        ],
    )
    controlled_sub_path = _block(
        name='controlled_sub_accumulator',
        summary='Borrow-resolution path for the controlled-subtract half of the schoolbook multiplier.',
        instance_count=field_bits,
        primitive_operations=_ladder_operations(field_bits, include_measurement=True),
        notes=[
            'This stage accounts for the residual n borrow transitions in the subtract half of the controlled add-subtract multiplier.',
        ],
    )
    return _kernel(
        opcode='field_mul',
        summary='Exact schoolbook controlled add-subtract field-multiplication kernel over the checked 256-bit field width.',
        stages=[
            _stage(
                name='partial_products',
                summary='Schoolbook partial-product grid.',
                category='schoolbook_grid',
                blocks=[partial_products],
                notes=['The partial-product stage is the dominant n^2 contribution in the multiplier family.'],
            ),
            _stage(
                name='controlled_add_path',
                summary='Carry-resolution path for the controlled-add contribution.',
                category='controlled_add',
                blocks=[controlled_add_path],
                notes=['The add path follows the same temporary logical-AND interpretation used by the field-adder kernel.'],
            ),
            _stage(
                name='controlled_sub_path',
                summary='Borrow-resolution path for the controlled-subtract contribution.',
                category='controlled_subtract',
                blocks=[controlled_sub_path],
                notes=['The subtract path carries the final linear correction term in the Litinski-style controlled add-subtract multiplier.'],
            ),
        ],
        notes=[
            'The kernel reconstructs n^2 + 2n - 1 non-Clifford operations as an explicit partial-product grid plus add/sub correction paths.',
        ],
    )


def _standard_qroam_coordinate_stream_cost(field_bits: int, domain_size: int = 32768, block_size: int = 16) -> Dict[str, int]:
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


def _streamed_lookup_bit_oracle_stage(field_bits: int, bit_source: str) -> Dict[str, Any]:
    cost = _standard_qroam_coordinate_stream_cost(field_bits)
    compute_operations = [
        _primitive_operation('ccx', index)
        for index in range(cost['lookup_compute_non_clifford'])
    ]
    uncompute_operations = [
        operation
        for index in range(cost['measured_uncompute_non_clifford'])
        for operation in (_primitive_operation('ccx', index), _primitive_operation('measurement', index))
    ]
    compute_block = _block(
        name=f'streamed_{bit_source}_standard_qroam_compute',
        summary=f'Standard QROAM compute for one selected {bit_source} coordinate stream.',
        instance_count=1,
        primitive_operations=compute_operations,
        notes=[
            f"The block uses the standard QROAM cost N/K + (K - 1)b with N={cost['domain_size']}, K={cost['block_size']}, and b={field_bits}.",
            f"The matching workspace contract must count the {field_bits}-qubit target register plus {cost['junk_register_count']} junk registers of {field_bits} qubits each.",
        ],
    )
    uncompute_block = _block(
        name=f'streamed_{bit_source}_standard_qroam_measured_uncompute',
        summary=f'Measured standard-QROAM cleanup for one selected {bit_source} coordinate stream.',
        instance_count=1,
        primitive_operations=uncompute_operations,
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
) -> Dict[str, Any]:
    kernel = deepcopy(_field_mul_kernel(field_bits))
    kernel['opcode'] = opcode
    kernel['summary'] = summary
    if lookup_bit_source is not None:
        kernel['stages'].insert(0, _streamed_lookup_bit_oracle_stage(field_bits, lookup_bit_source))
        primitive_totals = {
            key: sum(int(stage['primitive_counts_total'][key]) for stage in kernel['stages'])
            for key in ('ccx', 'cx', 'x', 'measurement')
        }
        kernel['primitive_counts_total'] = primitive_totals
        kernel['exact_non_clifford_per_kernel'] = primitive_totals['ccx']
    kernel['notes'] = [*kernel['notes'], note]
    return kernel


def _field_sub_sum_kernel(field_bits: int) -> Dict[str, Any]:
    two_subtractors = _block(
        name='two_borrow_ladders',
        summary='Two 256-bit borrow ladders for a - b - c inside one field register.',
        instance_count=2 * (field_bits - 1),
        primitive_operations=_ladder_operations(field_bits - 1, include_measurement=True)
        + _ladder_operations(field_bits - 1, include_measurement=True),
        notes=[
            'The streamed lookup tail uses this fused opcode for K = H - A - I.',
            'It is counted as exactly two field-subtractor kernels over the same field width.',
        ],
    )
    return _kernel(
        opcode='field_sub_sum',
        summary='Exact fused two-subtraction field kernel for a - b - c.',
        stages=[
            _stage(
                name='borrow_resolution_pair',
                summary='Two sequential temporary logical-AND borrow ladders.',
                category='subtractor',
                blocks=[two_subtractors],
                notes=['The fused instruction is a scheduling contract; its non-Clifford count is the sum of two ordinary subtractor kernels.'],
            )
        ],
        notes=[
            'The kernel contributes 2(n-1) non-Clifford operations for a 256-bit field value.',
        ],
    )


def _field_triple_kernel(field_bits: int) -> Dict[str, Any]:
    two_adders = _block(
        name='two_carry_ladders',
        summary='Two 256-bit carry ladders for 3a = a + a + a inside one field register.',
        instance_count=2 * (field_bits - 1),
        primitive_operations=_ladder_operations(field_bits - 1, include_measurement=True)
        + _ladder_operations(field_bits - 1, include_measurement=True),
        notes=[
            'The streamed lookup tail uses this fused opcode for L = 3A.',
            'It is counted as exactly two field-adder kernels over the same field width.',
        ],
    )
    return _kernel(
        opcode='field_triple',
        summary='Exact fused two-addition field kernel for multiplication by 3.',
        stages=[
            _stage(
                name='carry_resolution_pair',
                summary='Two sequential temporary logical-AND carry ladders.',
                category='adder',
                blocks=[two_adders],
                notes=['The fused instruction is a scheduling contract; its non-Clifford count is the sum of two ordinary adder kernels.'],
            )
        ],
        notes=[
            'The kernel contributes 2(n-1) non-Clifford operations for a 256-bit field value.',
        ],
    )


def _complete_a0_streamed_tail_kernel(field_bits: int) -> Dict[str, Any]:
    streamed_yz = deepcopy(_renamed_field_mul_kernel(
        field_bits,
        'field_mul_lookup_y',
        'Internal streamed yZ multiplication used by the complete-add tail macro.',
        'This stage is counted inside the macro because yZ is not materialized as a standalone leaf field value.',
        lookup_bit_source='lookup_y',
    )['stages'])
    fixed_f = _block(
        name='fixed_21z_chain',
        summary='Fixed multiplication F = 21Z inside the streamed tail macro.',
        instance_count=6 * (field_bits - 1),
        primitive_operations=[
            operation
            for _ in range(6)
            for operation in _ladder_operations(field_bits - 1, include_measurement=True)
        ],
        notes=[
            'The checked field constant is 3b = 21, whose monotone addition chain has six field-add steps.',
        ],
    )
    internal_combines = _block(
        name='three_internal_combine_ladders',
        summary='Three field add/sub combines for E = Y + yZ, M = I + F, and N = I - F.',
        instance_count=3 * (field_bits - 1),
        primitive_operations=[
            operation
            for _ in range(3)
            for operation in _ladder_operations(field_bits - 1, include_measurement=True)
        ],
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
        summary='Three field add/sub combine ladders for X3, Y3, and Z3 after the six products.',
        instance_count=3 * (field_bits - 1),
        primitive_operations=[
            operation
            for _ in range(3)
            for operation in _ladder_operations(field_bits - 1, include_measurement=True)
        ],
        notes=[
            'The output combines are counted as three ordinary field add/sub kernels.',
        ],
    )
    return _kernel(
        opcode='complete_a0_streamed_tail',
        summary='Exact multi-output complete-add tail kernel from C, K, L, I, Y, and Z.',
        stages=[
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
            _stage(
                name='tail_output_combine',
                summary='Three add/sub combines that write X3, Y3, and Z3.',
                category='tail_combine',
                blocks=[output_combine],
                notes=['Counted exactly as three field add/sub kernels.'],
            ),
        ],
        notes=[
            'The macro is a liveness contract, not a free arithmetic operation: its non-Clifford count includes yZ, 21Z, E/M/N, six output multipliers, and three output add/sub combines.',
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


def arithmetic_lowering_library(field_bits: int, leaf_opcode_histogram: Mapping[str, int]) -> Dict[str, Any]:
    kernels = [
        _field_mul_kernel(field_bits),
        _renamed_field_mul_kernel(
            field_bits,
            'field_mul_lookup_x',
            'Exact table-fed x-coordinate field multiplication kernel with no materialized lookup-output field lane.',
            'The streamed lookup coordinate is a table-controlled constant input and is not counted as a leaf field wire.',
            lookup_bit_source='lookup_x',
        ),
        _renamed_field_mul_kernel(
            field_bits,
            'field_mul_lookup_y',
            'Exact table-fed y-coordinate field multiplication kernel with no materialized lookup-output field lane.',
            'The streamed lookup coordinate is a table-controlled constant input and is not counted as a leaf field wire.',
            lookup_bit_source='lookup_y',
        ),
        _renamed_field_mul_kernel(
            field_bits,
            'field_mul_lookup_sum',
            'Exact table-fed (x+y)-coordinate field multiplication kernel with no materialized lookup-output field lane.',
            'The streamed lookup sum is a table-controlled constant input and is not counted as a leaf field wire.',
            lookup_bit_source='lookup_x_plus_y',
        ),
        _field_add_kernel(field_bits),
        _field_sub_kernel(field_bits),
        _field_sub_sum_kernel(field_bits),
        _field_triple_kernel(field_bits),
        _complete_a0_streamed_tail_kernel(field_bits),
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
        _, _, left, _, right = block['name'].split('_')
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
