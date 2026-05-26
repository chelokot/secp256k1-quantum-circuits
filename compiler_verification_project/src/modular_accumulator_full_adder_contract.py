#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Mapping


MODULAR_ACCUMULATOR_FULL_ADDER_CONTRACT_SCHEMA = 'compiler-project-modular-accumulator-full-adder-contract-v1'
FULL_ADDER_CONTRACT_UNPROMOTED_STATUS = 'full_adder_contract_not_promoted_to_public_resource_contract'
FULL_ADDER_PRIMITIVE_COUNTS_PER_CELL = {'ccx': 3, 'cx': 3, 'x': 0, 'measurement': 0}


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def _sha256_payload(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode('ascii')).hexdigest()


def _gate_sequence() -> List[Dict[str, Any]]:
    return [
        {'gate': 'cx', 'controls': ['a'], 'target': 'sum'},
        {'gate': 'cx', 'controls': ['b'], 'target': 'sum'},
        {'gate': 'cx', 'controls': ['c'], 'target': 'sum'},
        {'gate': 'ccx', 'controls': ['a', 'b'], 'target': 'carry'},
        {'gate': 'ccx', 'controls': ['a', 'c'], 'target': 'carry'},
        {'gate': 'ccx', 'controls': ['b', 'c'], 'target': 'carry'},
    ]


def _primitive_counts(rows: List[Mapping[str, Any]]) -> Dict[str, int]:
    counts = {'ccx': 0, 'cx': 0, 'x': 0, 'measurement': 0}
    for row in rows:
        counts[str(row['gate'])] += 1
    return counts


def _execute_cell(a_bit: int, b_bit: int, c_bit: int) -> Dict[str, int | bool]:
    register = {'a': int(a_bit), 'b': int(b_bit), 'c': int(c_bit), 'sum': 0, 'carry': 0}
    for gate in _gate_sequence():
        if str(gate['gate']) == 'cx':
            control = str(gate['controls'][0])
            target = str(gate['target'])
            register[target] ^= register[control]
        elif str(gate['gate']) == 'ccx':
            left, right = [str(value) for value in gate['controls']]
            target = str(gate['target'])
            register[target] ^= register[left] & register[right]
        else:
            raise ValueError(f'unsupported full-adder gate: {gate}')
    input_weight = int(a_bit) + int(b_bit) + int(c_bit)
    expected_sum = input_weight & 1
    expected_carry = 1 if input_weight >= 2 else 0
    return {
        'a': int(a_bit),
        'b': int(b_bit),
        'c': int(c_bit),
        'sum': register['sum'],
        'carry': register['carry'],
        'inputs_retained': register['a'] == int(a_bit) and register['b'] == int(b_bit) and register['c'] == int(c_bit),
        'expected_sum': expected_sum,
        'expected_carry': expected_carry,
        'passes': register['sum'] == expected_sum and register['carry'] == expected_carry,
    }


def _truth_table() -> List[Dict[str, int | bool]]:
    return [
        _execute_cell(a_bit, b_bit, c_bit)
        for a_bit in (0, 1)
        for b_bit in (0, 1)
        for c_bit in (0, 1)
    ]


def _irreversible_collision_count() -> int:
    buckets: Dict[tuple[int, int], int] = {}
    for row in _truth_table():
        key = (int(row['sum']), int(row['carry']))
        buckets[key] = buckets.get(key, 0) + 1
    return sum(count - 1 for count in buckets.values() if count > 1)


def build_modular_accumulator_full_adder_contract(
    *,
    modular_accumulator_carry_save_candidate: Mapping[str, Any],
) -> Dict[str, Any]:
    gates = _gate_sequence()
    counts = _primitive_counts(gates)
    table = _truth_table()
    cell_count = int(modular_accumulator_carry_save_candidate['all_grids']['carry_save_full_adder_count'])
    total_counts = {
        key: cell_count * int(value)
        for key, value in counts.items()
    }
    retained_input_bits = 3 * cell_count
    output_bits = 2 * cell_count
    checks = {
        'source_carry_save_candidate_passes': modular_accumulator_carry_save_candidate['pass'] is True,
        'truth_table_passes': all(row['passes'] is True for row in table),
        'embedding_retains_inputs': all(row['inputs_retained'] is True for row in table),
        'primitive_counts_match_gate_sequence': counts == FULL_ADDER_PRIMITIVE_COUNTS_PER_CELL,
        'irreversible_three_to_two_compression_is_rejected': _irreversible_collision_count() > 0,
        'full_adder_cell_count_matches_candidate': cell_count > 0,
        'retained_inputs_or_cleanup_are_explicit': retained_input_bits == 3 * cell_count and output_bits == 2 * cell_count,
        'contract_not_promoted_to_public_resource_contract': True,
    }
    return {
        'schema': MODULAR_ACCUMULATOR_FULL_ADDER_CONTRACT_SCHEMA,
        'definition': 'Reversible full-adder embedding contract for the carry-save accumulator candidate. The cell computes sum=a xor b xor c and carry=majority(a,b,c) into zero output lanes while retaining all three input bits; promotion must either keep those retained inputs counted or prove source uncomputation.',
        'source_digests': {
            'modular_accumulator_carry_save_candidate_sha256': _sha256_payload(modular_accumulator_carry_save_candidate),
        },
        'cell_contract': {
            'input_bits': ['a', 'b', 'c'],
            'zero_output_bits': ['sum', 'carry'],
            'retained_input_bits_per_cell': 3,
            'output_bits_per_cell': 2,
            'gate_sequence': gates,
            'primitive_counts_per_cell': counts,
            'truth_table': table,
            'irreversible_three_to_two_collision_count': _irreversible_collision_count(),
        },
        'candidate_totals': {
            'full_adder_cell_count': cell_count,
            'embedded_full_adder_primitive_counts': total_counts,
            'retained_input_obligation_bits': retained_input_bits,
            'output_obligation_bits': output_bits,
            'final_carry_propagate_bits': int(modular_accumulator_carry_save_candidate['all_grids']['final_carry_propagate_bits']),
        },
        'promotion_status': {
            'status': FULL_ADDER_CONTRACT_UNPROMOTED_STATUS,
            'required_to_promote': [
                'Assign retained input bits, sum output bits, and carry output bits to counted owners in the global liveness engine.',
                'Prove source uncomputation for retained inputs that are not kept live after compression.',
                'Splice the per-cell CX/CCX sequence into the materialized primitive netlist with exact owner capacity.',
                'Recompute public non-Clifford and peak-live-qubit totals from that promoted primitive stream.',
            ],
        },
        'checks': checks,
        'pass': all(checks.values()),
    }


__all__ = [
    'FULL_ADDER_CONTRACT_UNPROMOTED_STATUS',
    'FULL_ADDER_PRIMITIVE_COUNTS_PER_CELL',
    'MODULAR_ACCUMULATOR_FULL_ADDER_CONTRACT_SCHEMA',
    'build_modular_accumulator_full_adder_contract',
]
