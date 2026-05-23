#!/usr/bin/env python3

from __future__ import annotations

from collections import Counter, deque
from typing import Any, Dict, Mapping, Sequence

from tail_macro_reversibility import (
    TOY_CURVES,
    Point,
    _add_points,
    _boundary_case,
    _canonical_projective,
    _projective_to_affine,
    _subgroup_points,
    _tail_map,
)


TAIL_MACRO_OPCODE = 'complete_a0_all_streamed_tail'
QUANTUM_INPUTS = ('X', 'Y', 'Z')
TABLE_CONSTANTS = ('lookup_x', 'lookup_y', 'lookup_x_plus_y')
QUANTUM_OUTPUTS = ('X3', 'Y3', 'Z3')
TAIL_MACRO_FORMULA: Sequence[tuple[str, Sequence[str]]] = (
    ('G', ('X', 'Y')),
    ('H', ('G', 'lookup_x_plus_y')),
    ('A', ('X', 'lookup_x')),
    ('Zx', ('Z', 'lookup_x')),
    ('C', ('X', 'Zx')),
    ('I', ('Y', 'lookup_y')),
    ('K', ('H', 'A', 'I')),
    ('L', ('A',)),
    ('yZ', ('lookup_y', 'Z')),
    ('E', ('Y', 'yZ')),
    ('F', ('Z',)),
    ('M', ('I', 'F')),
    ('N', ('I', 'F')),
    ('KN', ('K', 'N')),
    ('EC', ('E', 'C')),
    ('NM', ('N', 'M')),
    ('CL', ('C', 'L')),
    ('ME', ('M', 'E')),
    ('LK', ('L', 'K')),
    ('X3', ('KN', 'EC')),
    ('Y3', ('NM', 'CL')),
    ('Z3', ('ME', 'LK')),
)
TAIL_MACRO_FIELD_OPERATION_STREAM: Sequence[Mapping[str, Any]] = (
    {'target': 'G', 'formula_target': 'G', 'opcode': 'field_add', 'sources': ('X', 'Y')},
    {'target': 'H', 'formula_target': 'H', 'opcode': 'field_mul_lookup_sum', 'sources': ('G', 'lookup_x_plus_y')},
    {'target': 'A', 'formula_target': 'A', 'opcode': 'field_mul_lookup_x', 'sources': ('X', 'lookup_x')},
    {'target': 'Zx', 'formula_target': 'Zx', 'opcode': 'field_mul_lookup_x', 'sources': ('Z', 'lookup_x')},
    {'target': 'C_input', 'formula_target': 'C', 'opcode': 'field_add', 'sources': ('X', 'Zx')},
    {'target': 'C', 'formula_target': 'C', 'opcode': 'mul_const', 'sources': ('C_input',), 'constant': 21},
    {'target': 'I', 'formula_target': 'I', 'opcode': 'field_mul_lookup_y', 'sources': ('Y', 'lookup_y')},
    {'target': 'K', 'formula_target': 'K', 'opcode': 'field_sub_sum', 'sources': ('H', 'A', 'I')},
    {'target': 'L', 'formula_target': 'L', 'opcode': 'field_triple', 'sources': ('A',), 'constant': 3},
    {'target': 'yZ', 'formula_target': 'yZ', 'opcode': 'field_mul_lookup_y', 'sources': ('Z', 'lookup_y')},
    {'target': 'E', 'formula_target': 'E', 'opcode': 'field_add', 'sources': ('Y', 'yZ')},
    {'target': 'F', 'formula_target': 'F', 'opcode': 'mul_const', 'sources': ('Z',), 'constant': 21},
    {'target': 'M', 'formula_target': 'M', 'opcode': 'field_add', 'sources': ('I', 'F')},
    {'target': 'N', 'formula_target': 'N', 'opcode': 'field_sub', 'sources': ('I', 'F')},
    {'target': 'KN', 'formula_target': 'KN', 'opcode': 'field_mul', 'sources': ('K', 'N')},
    {'target': 'EC', 'formula_target': 'EC', 'opcode': 'field_mul', 'sources': ('E', 'C')},
    {'target': 'NM', 'formula_target': 'NM', 'opcode': 'field_mul', 'sources': ('N', 'M')},
    {'target': 'CL', 'formula_target': 'CL', 'opcode': 'field_mul', 'sources': ('C', 'L')},
    {'target': 'ME', 'formula_target': 'ME', 'opcode': 'field_mul', 'sources': ('M', 'E')},
    {'target': 'LK', 'formula_target': 'LK', 'opcode': 'field_mul', 'sources': ('L', 'K')},
    {'target': 'X3', 'formula_target': 'X3', 'opcode': 'field_sub', 'sources': ('KN', 'EC')},
    {'target': 'Y3', 'formula_target': 'Y3', 'opcode': 'field_add', 'sources': ('NM', 'CL')},
    {'target': 'Z3', 'formula_target': 'Z3', 'opcode': 'field_add', 'sources': ('ME', 'LK')},
)


def _last_uses(formula: Sequence[tuple[str, Sequence[str]]]) -> Dict[str, int]:
    last: Dict[str, int] = {value: -1 for value in QUANTUM_INPUTS}
    for index, (target, sources) in enumerate(formula):
        for source in sources:
            if source not in TABLE_CONSTANTS:
                last[source] = index
        last.setdefault(target, index)
    return last


def _formula_rows() -> list[Dict[str, Any]]:
    last = _last_uses(TAIL_MACRO_FORMULA)
    rows = []
    for index, (target, sources) in enumerate(TAIL_MACRO_FORMULA):
        rows.append({
            'index': index,
            'target': target,
            'sources': list(sources),
            'quantum_sources': [source for source in sources if source not in TABLE_CONSTANTS],
            'table_constant_sources': [source for source in sources if source in TABLE_CONSTANTS],
            'last_quantum_source_uses': {
                source: last[source]
                for source in sources
                if source not in TABLE_CONSTANTS and last[source] == index
            },
        })
    return rows


def _field_operation_rows(kernel_non_clifford_by_opcode: Mapping[str, Any]) -> list[Dict[str, Any]]:
    rows = []
    for index, operation in enumerate(TAIL_MACRO_FIELD_OPERATION_STREAM):
        opcode = str(operation['opcode'])
        rows.append({
            'index': index,
            'target': str(operation['target']),
            'formula_target': str(operation['formula_target']),
            'opcode': opcode,
            'sources': list(operation['sources']),
            'constant': operation.get('constant'),
            'non_clifford': int(kernel_non_clifford_by_opcode[opcode]),
        })
    return rows


def _one_compute_liveness(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    last: Dict[str, int] = {value: -1 for value in QUANTUM_INPUTS}
    for index, row in enumerate(rows):
        for source in row['sources']:
            if source not in TABLE_CONSTANTS:
                last[str(source)] = index
        last.setdefault(str(row['target']), index)
    live = set(QUANTUM_INPUTS)
    trace = [{
        'step': 'initial',
        'target': None,
        'live_field_values': sorted(live),
        'live_field_value_count': len(live),
    }]
    peak_count = len(live)
    peak_step = 'initial'
    peak_live = sorted(live)
    for index, row in enumerate(rows):
        target = str(row['target'])
        live.add(target)
        expired = []
        for source in row['sources']:
            source_name = str(source)
            if source_name not in TABLE_CONSTANTS and last[source_name] == index and source_name not in QUANTUM_OUTPUTS:
                live.discard(source_name)
                expired.append(source_name)
        trace_row = {
            'step': index,
            'target': target,
            'opcode': str(row['opcode']),
            'sources': list(row['sources']),
            'expired_after_step': sorted(expired),
            'live_field_values': sorted(live),
            'live_field_value_count': len(live),
        }
        trace.append(trace_row)
        if len(live) > peak_count:
            peak_count = len(live)
            peak_step = f'{index}:{target}'
            peak_live = sorted(live)
    return {
        'schedule_model': 'single_assignment_expanded_field_operation_stream',
        'peak_live_field_values': peak_count,
        'peak_step': peak_step,
        'peak_live_values': peak_live,
        'rows': trace,
    }


def _expanded_slot_schedule(rows: Sequence[Mapping[str, Any]], counted_arithmetic_slots: int, field_bits: int) -> Dict[str, Any]:
    last: Dict[str, int] = {value: -1 for value in QUANTUM_INPUTS}
    for index, row in enumerate(rows):
        for source in row['sources']:
            if source not in TABLE_CONSTANTS:
                last[str(source)] = index
        last.setdefault(str(row['target']), index)
    slot_by_value = {value: index for index, value in enumerate(QUANTUM_INPUTS)}
    rows_out = []
    peak_slot_count = len(slot_by_value)
    peak_step = 'initial'
    for index, row in enumerate(rows):
        sources = [str(source) for source in row['sources']]
        live_before = dict(sorted(slot_by_value.items()))
        occupied = set(slot_by_value.values())
        target_slot = 0
        while target_slot in occupied:
            target_slot += 1
        target = str(row['target'])
        slot_by_value[target] = target_slot
        live_during = dict(sorted(slot_by_value.items()))
        if len(live_during) > peak_slot_count:
            peak_slot_count = len(live_during)
            peak_step = f'{index}:{target}'
        expired = []
        for source in sources:
            if source not in TABLE_CONSTANTS and last[source] == index and source not in QUANTUM_OUTPUTS:
                expired.append(source)
                del slot_by_value[source]
        rows_out.append({
            'index': index,
            'opcode': str(row['opcode']),
            'target': target,
            'target_slot': target_slot,
            'sources': sources,
            'constant': row.get('constant'),
            'source_slots': {
                source: live_during[source]
                for source in sources
                if source not in TABLE_CONSTANTS
            },
            'live_before': live_before,
            'live_during': live_during,
            'expired_after_step': sorted(expired),
            'live_after': dict(sorted(slot_by_value.items())),
        })
    additional_slots = max(0, int(peak_slot_count) - int(counted_arithmetic_slots))
    return {
        'schedule_model': 'single_assignment_expanded_field_register_file',
        'status': 'executable_capacity_fallback_not_reversible_cleanup_proof',
        'field_bits': int(field_bits),
        'counted_arithmetic_slots': int(counted_arithmetic_slots),
        'peak_field_slots': int(peak_slot_count),
        'peak_step': peak_step,
        'additional_field_slots_over_counted_leaf': additional_slots,
        'additional_logical_qubits_over_counted_leaf': additional_slots * int(field_bits),
        'slot_owners': [
            {
                'slot': slot,
                'owner': (
                    f'leaf_arithmetic_slot_{slot}'
                    if slot < int(counted_arithmetic_slots)
                    else f'tail_macro_internal_slot_{slot - int(counted_arithmetic_slots)}'
                ),
                'logical_qubits': int(field_bits),
                'counted_in_current_leaf_budget': slot < int(counted_arithmetic_slots),
            }
            for slot in range(int(peak_slot_count))
        ],
        'rows': rows_out,
        'final_live_values': dict(sorted(slot_by_value.items())),
        'notes': [
            'This is the strict expanded-capacity schedule for the current field-operation stream.',
            'It proves the number of field-sized lanes required if the tail is implemented as single-assignment field kernels.',
            'It is not a reversible cleanup or in-place three-slot proof; using it as the public primitive-circuit contract requires counting the additional tail_macro_internal_slot owners.',
        ],
    }


def _destructive_candidate_schedule(rows: Sequence[Mapping[str, Any]], counted_arithmetic_slots: int, field_bits: int) -> Dict[str, Any]:
    last: Dict[str, int] = {value: -1 for value in QUANTUM_INPUTS}
    for index, row in enumerate(rows):
        for source in row['sources']:
            if source not in TABLE_CONSTANTS:
                last[str(source)] = index
        last.setdefault(str(row['target']), index)
    slot_by_value = {value: index for index, value in enumerate(QUANTUM_INPUTS)}
    rows_out = []
    peak_slot_count = len(slot_by_value)
    peak_step = 'initial'
    overwritten_rows = 0
    for index, row in enumerate(rows):
        sources = [str(source) for source in row['sources']]
        target = str(row['target'])
        live_before = dict(sorted(slot_by_value.items()))
        expiring_sources = [
            source
            for source in sources
            if source not in TABLE_CONSTANTS and last[source] == index and source not in QUANTUM_OUTPUTS
        ]
        overwritten_source = None
        if expiring_sources:
            overwritten_source = max(expiring_sources, key=lambda source: slot_by_value[source])
            target_slot = slot_by_value[overwritten_source]
            del slot_by_value[overwritten_source]
            overwritten_rows += 1
        else:
            occupied = set(slot_by_value.values())
            target_slot = 0
            while target_slot in occupied:
                target_slot += 1
        slot_by_value[target] = target_slot
        live_during_capacity = dict(sorted(slot_by_value.items()))
        if len(live_during_capacity) > peak_slot_count:
            peak_slot_count = len(live_during_capacity)
            peak_step = f'{index}:{target}'
        expired = []
        for source in expiring_sources:
            if source != overwritten_source:
                expired.append(source)
                del slot_by_value[source]
        rows_out.append({
            'index': index,
            'opcode': str(row['opcode']),
            'target': target,
            'target_slot': target_slot,
            'sources': sources,
            'constant': row.get('constant'),
            'source_slots_before_operation': {
                source: live_before[source]
                for source in sources
                if source not in TABLE_CONSTANTS
            },
            'overwritten_source': overwritten_source,
            'overwritten_source_slot': None if overwritten_source is None else target_slot,
            'live_before': live_before,
            'live_during_capacity': live_during_capacity,
            'expired_after_step': sorted(expired),
            'live_after': dict(sorted(slot_by_value.items())),
            'proof_obligation': (
                'prove reversible/in-place implementation can consume overwritten source and write target in the same field lane without losing required information'
                if overwritten_source is not None
                else 'ordinary single-assignment target allocation'
            ),
        })
    additional_slots = max(0, int(peak_slot_count) - int(counted_arithmetic_slots))
    return {
        'schedule_model': 'destructive_last_use_overwrite_candidate',
        'status': 'optimizer_candidate_not_a_reversible_proof',
        'field_bits': int(field_bits),
        'counted_arithmetic_slots': int(counted_arithmetic_slots),
        'peak_field_slots': int(peak_slot_count),
        'peak_step': peak_step,
        'overwritten_row_count': overwritten_rows,
        'additional_field_slots_over_counted_leaf': additional_slots,
        'additional_logical_qubits_over_counted_leaf': additional_slots * int(field_bits),
        'rows': rows_out,
        'final_live_values': dict(sorted(slot_by_value.items())),
        'proxy_metrics': {
            'peak_field_slots': int(peak_slot_count),
            'overwritten_row_count': overwritten_rows,
            'field_slot_improvement_vs_strict_single_assignment': None,
        },
        'notes': [
            'This optimizer candidate reuses the physical slot of a last-use source for the operation target.',
            'It is a search/proxy signal for in-place schedule development, not a public resource contract.',
            'Every overwritten row remains invalid until a reversible or valid-subspace permutation implementation is supplied for that opcode and boundary state.',
        ],
    }


def _operation_value(
    *,
    opcode: str,
    sources: Sequence[str],
    values: Mapping[str, int],
    modulus: int,
    curve_b: int,
    lookup_x: int,
    lookup_y: int,
    constant: Any,
) -> int:
    source_values = {
        'lookup_x': lookup_x % modulus,
        'lookup_y': lookup_y % modulus,
        'lookup_x_plus_y': (lookup_x + lookup_y) % modulus,
    }
    resolved = [
        source_values[source] if source in source_values else int(values[source])
        for source in sources
    ]
    if opcode == 'field_add':
        return sum(resolved) % modulus
    if opcode == 'field_sub':
        return (resolved[0] - resolved[1]) % modulus
    if opcode == 'field_sub_sum':
        return (resolved[0] - resolved[1] - resolved[2]) % modulus
    if opcode == 'field_triple':
        return (3 * resolved[0]) % modulus
    if opcode == 'mul_const':
        multiplier = 3 * int(curve_b) if constant is None or int(constant) == 21 else int(constant)
        return (multiplier * resolved[0]) % modulus
    if opcode in {'field_mul', 'field_mul_lookup_x', 'field_mul_lookup_y'}:
        return (resolved[0] * resolved[1]) % modulus
    if opcode == 'field_mul_lookup_sum':
        return (resolved[0] * resolved[1]) % modulus
    raise ValueError(f'unsupported tail macro field opcode: {opcode}')


def _operation_trace_values(curve: Mapping[str, Any], lookup: Point, accumulator: Point, rows: Sequence[Mapping[str, Any]]) -> list[Dict[str, Any]]:
    modulus = int(curve['p'])
    curve_b = int(curve['b'])
    lookup_x, lookup_y = lookup if lookup is not None else (0, 0)
    accum_x, accum_y, accum_z = _canonical_projective(accumulator)
    values: Dict[str, int] = {
        'X': accum_x,
        'Y': accum_y,
        'Z': accum_z,
    }
    trace = []
    for row in rows:
        sources = [str(source) for source in row['sources']]
        before = dict(values)
        target_value = _operation_value(
            opcode=str(row['opcode']),
            sources=sources,
            values=values,
            modulus=modulus,
            curve_b=curve_b,
            lookup_x=lookup_x,
            lookup_y=lookup_y,
            constant=row.get('constant'),
        )
        values[str(row['target'])] = target_value
        trace.append({
            'index': int(row['index']),
            'target': str(row['target']),
            'opcode': str(row['opcode']),
            'sources': sources,
            'before': before,
            'target_value': target_value,
            'lookup': None if lookup is None else {'x': lookup_x, 'y': lookup_y},
        })
    return trace


def _overwrite_rule(row: Mapping[str, Any], modulus: int) -> Dict[str, Any]:
    opcode = str(row['opcode'])
    sources = [str(source) for source in row['sources']]
    overwritten = str(row['overwritten_source'])
    if opcode in {'field_add', 'field_sub', 'field_sub_sum'}:
        return {
            'kind': 'affine_unit_coefficient',
            'symbolic_inverse_exists_over_field': True,
        }
    if opcode == 'field_triple':
        return {
            'kind': 'constant_multiply',
            'constant': 3,
            'symbolic_inverse_exists_over_field': 3 % int(modulus) != 0,
        }
    if opcode == 'mul_const':
        constant = int(row.get('constant') or 0)
        return {
            'kind': 'constant_multiply',
            'constant': constant,
            'symbolic_inverse_exists_over_field': constant % int(modulus) != 0,
        }
    if opcode in {'field_mul_lookup_x', 'field_mul_lookup_y', 'field_mul_lookup_sum'}:
        lookup_source = next(source for source in sources if source in TABLE_CONSTANTS)
        return {
            'kind': 'lookup_constant_multiply',
            'constant_source': lookup_source,
            'symbolic_inverse_exists_over_field': None,
        }
    if opcode == 'field_mul':
        multiplier_source = next(source for source in sources if source != overwritten)
        return {
            'kind': 'variable_multiply',
            'multiplier_source': multiplier_source,
            'symbolic_inverse_exists_over_field': None,
        }
    raise ValueError(f'unsupported overwrite opcode: {opcode}')


def _overwrite_local_inverse_certificate(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    overwritten_rows = [row for row in rows if row.get('overwritten_source') is not None]
    proof_by_index = {
        int(row['index']): {
            'index': int(row['index']),
            'opcode': str(row['opcode']),
            'target': str(row['target']),
            'overwritten_source': str(row['overwritten_source']),
            'rule': _overwrite_rule(row, int(TOY_CURVES[0]['p'])),
            'checked_domain': 'toy canonical accumulator subgroup x non-infinity lookup subgroup',
            'domain_rows_checked': 0,
            'per_curve': [],
            'failure_examples': [],
        }
        for row in overwritten_rows
    }
    row_by_index = {int(row['index']): row for row in overwritten_rows}
    total_domain_rows = 0
    for curve in TOY_CURVES:
        modulus = int(curve['p'])
        points = _subgroup_points(modulus, curve['generator'], int(curve['order']))
        curve_failures = {int(row['index']): [] for row in overwritten_rows}
        domain_rows_for_curve = (len(points) - 1) * len(points)
        for lookup in points:
            if lookup is None:
                continue
            for accumulator in points:
                trace = {
                    int(item['index']): item
                    for item in _operation_trace_values(curve, lookup, accumulator, rows)
                }
                total_domain_rows += len(overwritten_rows)
                for row in overwritten_rows:
                    row_index = int(row['index'])
                    rule = _overwrite_rule(row, modulus)
                    trace_row = trace[row_index]
                    proof_by_index[row_index]['domain_rows_checked'] += 1
                    if rule['kind'] == 'lookup_constant_multiply':
                        lookup_values = {
                            'lookup_x': lookup[0] % modulus,
                            'lookup_y': lookup[1] % modulus,
                            'lookup_x_plus_y': (lookup[0] + lookup[1]) % modulus,
                        }
                        condition_pass = lookup_values[str(rule['constant_source'])] != 0
                    elif rule['kind'] == 'variable_multiply':
                        condition_pass = int(trace_row['before'][str(rule['multiplier_source'])]) % modulus != 0
                    else:
                        condition_pass = bool(rule['symbolic_inverse_exists_over_field'])
                    if not condition_pass and len(curve_failures[row_index]) < 3:
                        curve_failures[row_index].append({
                            'lookup': list(lookup),
                            'accumulator': None if accumulator is None else list(accumulator),
                            'before': {
                                key: value
                                for key, value in trace_row['before'].items()
                                if key in set(trace_row['sources']) | {str(rule.get('multiplier_source', ''))}
                            },
                            'target_value': trace_row['target_value'],
                        })
        for row_index in sorted(row_by_index):
            failures = curve_failures[row_index]
            proof_by_index[row_index]['per_curve'].append({
                'curve': curve['name'],
                'domain_rows_checked': domain_rows_for_curve,
                'pass': not failures,
                'failure_examples': failures,
            })
            if failures and len(proof_by_index[row_index]['failure_examples']) < 4:
                proof_by_index[row_index]['failure_examples'].append({
                    'curve': curve['name'],
                    'examples': failures,
                })
    proof_rows = []
    for row_index in sorted(proof_by_index):
        proof_row = proof_by_index[row_index]
        proof_row['pass'] = not proof_row['failure_examples']
        if not proof_row['pass']:
            rule = proof_row['rule']
            if rule['kind'] == 'lookup_constant_multiply':
                proof_row['failure_reason'] = f"{rule['constant_source']} can be zero on the checked boundary domain"
            elif rule['kind'] == 'variable_multiply':
                proof_row['failure_reason'] = f"{rule['multiplier_source']} can be zero on the checked boundary domain"
            else:
                proof_row['failure_reason'] = 'overwrite rule is not locally invertible on the checked boundary domain'
        proof_rows.append(proof_row)
    passing_rows = sum(1 for row in proof_rows if row['pass'])
    return {
        'schema': 'compiler-project-tail-overwrite-local-inverse-certificate-v1',
        'status': 'toy_boundary_local_inverse_check_not_full_reversible_proof',
        'overwrite_row_count': len(overwritten_rows),
        'passing_row_count': passing_rows,
        'failing_row_count': len(overwritten_rows) - passing_rows,
        'total_domain_rows_checked': total_domain_rows,
        'rows': proof_rows,
        'pass': passing_rows == len(overwritten_rows),
        'notes': [
            'Each row checks whether the overwritten field value can be recovered from the target and the other fixed live inputs on the checked toy boundary domain.',
            'Passing this certificate is still not a complete reversible circuit proof; it is a local invertibility screen for the destructive-overwrite optimizer candidate.',
            'Failing rows identify concrete zero-multiplier or non-injective cases that must be avoided by a different schedule or a stronger valid-subspace argument.',
        ],
    }


def _expiring_source_choices(row: Mapping[str, Any]) -> list[str]:
    live_after = set(str(value) for value in row['live_after'])
    choices = [
        str(source)
        for source in row['sources']
        if source not in TABLE_CONSTANTS and str(source) not in live_after
    ]
    overwritten = row.get('overwritten_source')
    if overwritten is not None and str(overwritten) not in choices:
        choices.append(str(overwritten))
    return sorted(choices)


def _overwrite_choice_screen_from_operand_screen(
    rows: Sequence[Mapping[str, Any]],
    operand_screen: Mapping[str, Any],
) -> Dict[str, Any]:
    expiring_choice_keys = {
        (int(row['index']), overwritten_source)
        for row in rows
        for overwritten_source in _expiring_source_choices(row)
    }
    choices = [
        dict(choice)
        for choice in operand_screen['choices']
        if (int(choice['index']), str(choice['overwritten_source'])) in expiring_choice_keys
    ]
    passing_choices = sum(1 for choice in choices if choice['pass'])
    failing_choices = len(choices) - passing_choices
    failing_indices = sorted({int(choice['index']) for choice in choices if not choice['pass']})
    return {
        'schema': 'compiler-project-tail-overwrite-choice-screen-v1',
        'status': 'toy_boundary_expiring_source_choice_screen_not_full_reversible_proof',
        'choice_count': len(choices),
        'passing_choice_count': passing_choices,
        'failing_choice_count': failing_choices,
        'failing_row_indices': failing_indices,
        'choices': choices,
        'pass': failing_choices == 0,
        'derived_from': operand_screen['schema'],
        'notes': [
            'This screen filters the all-operand overwrite screen down to the expiring source choices for the fixed formula order.',
            'It distinguishes a bad overwrite-source choice from a true local non-invertibility blocker in the current formula order.',
        ],
    }


def _overwrite_operand_screen(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    choices = []
    for row in rows:
        for overwritten_source in sorted(str(source) for source in row['sources'] if source not in TABLE_CONSTANTS):
            rule_row = dict(row)
            rule_row['overwritten_source'] = overwritten_source
            choices.append({
                'index': int(row['index']),
                'opcode': str(row['opcode']),
                'target': str(row['target']),
                'sources': [str(source) for source in row['sources']],
                'constant': row.get('constant'),
                'overwritten_source': overwritten_source,
                'rule': _overwrite_rule(rule_row, int(TOY_CURVES[0]['p'])),
                'domain_rows_checked': 0,
                'failure_examples': [],
            })
    for curve in TOY_CURVES:
        modulus = int(curve['p'])
        points = _subgroup_points(modulus, curve['generator'], int(curve['order']))
        for lookup in points:
            if lookup is None:
                continue
            for accumulator in points:
                trace = {
                    int(item['index']): item
                    for item in _operation_trace_values(curve, lookup, accumulator, rows)
                }
                for choice in choices:
                    choice['domain_rows_checked'] += 1
                    if choice['failure_examples']:
                        continue
                    rule = _overwrite_rule(choice, modulus)
                    trace_row = trace[int(choice['index'])]
                    if rule['kind'] == 'lookup_constant_multiply':
                        lookup_values = {
                            'lookup_x': lookup[0] % modulus,
                            'lookup_y': lookup[1] % modulus,
                            'lookup_x_plus_y': (lookup[0] + lookup[1]) % modulus,
                        }
                        condition_pass = lookup_values[str(rule['constant_source'])] != 0
                    elif rule['kind'] == 'variable_multiply':
                        condition_pass = int(trace_row['before'][str(rule['multiplier_source'])]) % modulus != 0
                    else:
                        condition_pass = bool(rule['symbolic_inverse_exists_over_field'])
                    if not condition_pass:
                        choice['failure_examples'].append({
                            'curve': curve['name'],
                            'lookup': list(lookup),
                            'accumulator': None if accumulator is None else list(accumulator),
                            'reason': (
                                f"{rule['constant_source']} can be zero on the checked boundary domain"
                                if rule['kind'] == 'lookup_constant_multiply'
                                else f"{rule['multiplier_source']} can be zero on the checked boundary domain"
                                if rule['kind'] == 'variable_multiply'
                                else 'overwrite rule is not locally invertible on the checked boundary domain'
                            ),
                        })
    for choice in choices:
        choice['pass'] = not choice['failure_examples']
        if choice['failure_examples']:
            choice['failure_reason'] = choice['failure_examples'][0]['reason']
    passing_choices = sum(1 for choice in choices if choice['pass'])
    failing_choices = len(choices) - passing_choices
    failing_indices = sorted({int(choice['index']) for choice in choices if not choice['pass']})
    return {
        'schema': 'compiler-project-tail-overwrite-operand-screen-v1',
        'status': 'toy_boundary_operand_choice_screen_not_full_reversible_proof',
        'choice_count': len(choices),
        'passing_choice_count': passing_choices,
        'failing_choice_count': failing_choices,
        'failing_row_indices': failing_indices,
        'choices': choices,
        'pass': failing_choices == 0,
        'notes': [
            'This screen checks every quantum operand as a potential overwrite source, independent of the fixed formula order.',
            'The reordered schedule search uses only operand choices that pass this screen.',
        ],
    }


def _reconstruct_reordered_schedule(
    terminal: tuple[int, frozenset[str]],
    previous: Mapping[tuple[int, frozenset[str]], tuple[tuple[int, frozenset[str]] | None, Mapping[str, Any] | None]],
) -> list[Dict[str, Any]]:
    rows = []
    state = terminal
    while previous[state][0] is not None:
        parent, action = previous[state]
        assert action is not None
        rows.append(dict(action))
        assert parent is not None
        state = parent
    rows.reverse()
    for schedule_index, row in enumerate(rows):
        row['schedule_index'] = schedule_index
    return rows


def _reordered_local_inverse_schedule(
    rows: Sequence[Mapping[str, Any]],
    *,
    operand_screen: Mapping[str, Any],
    counted_arithmetic_slots: int,
    field_bits: int,
    max_peak_field_slots: int,
) -> Dict[str, Any]:
    operation_count = len(rows)
    producer_by_value = {
        str(row['target']): int(row['index'])
        for row in rows
    }
    dependencies_by_index = []
    for row in rows:
        dependencies = []
        for source in row['sources']:
            source_name = str(source)
            if source_name in TABLE_CONSTANTS:
                continue
            if source_name in producer_by_value:
                dependencies.append(producer_by_value[source_name])
        dependencies_by_index.append(tuple(dependencies))
    overwrite_allowed = {
        (int(choice['index']), str(choice['overwritten_source']))
        for choice in operand_screen['choices']
        if choice['pass'] is True
    }
    initial_state = (0, frozenset(QUANTUM_INPUTS))
    queue = deque([(initial_state, len(QUANTUM_INPUTS))])
    previous: Dict[tuple[int, frozenset[str]], tuple[tuple[int, frozenset[str]] | None, Mapping[str, Any] | None]] = {
        initial_state: (None, None)
    }
    best_peak_by_state = {initial_state: len(QUANTUM_INPUTS)}
    terminal = None
    terminal_peak = None
    while queue:
        (completed_mask, live_values), peak_so_far = queue.popleft()
        if all(output in live_values for output in QUANTUM_OUTPUTS):
            terminal = (completed_mask, live_values)
            terminal_peak = peak_so_far
            break
        for operation_index, row in enumerate(rows):
            operation_bit = 1 << operation_index
            if completed_mask & operation_bit:
                continue
            if any(not (completed_mask & (1 << dependency)) for dependency in dependencies_by_index[operation_index]):
                continue
            sources = [str(source) for source in row['sources'] if source not in TABLE_CONSTANTS]
            if any(source not in live_values for source in sources):
                continue
            next_completed_mask = completed_mask | operation_bit
            remaining_operation_indices = [
                index
                for index in range(operation_count)
                if not (next_completed_mask & (1 << index))
            ]
            needed_after = set(QUANTUM_OUTPUTS)
            for remaining_index in remaining_operation_indices:
                for source in rows[remaining_index]['sources']:
                    source_name = str(source)
                    if source_name not in TABLE_CONSTANTS:
                        needed_after.add(source_name)
            expiring_sources = [
                source
                for source in sources
                if source not in needed_after
            ]
            overwrite_options: list[str | None] = [None]
            overwrite_options.extend(
                source
                for source in expiring_sources
                if (operation_index, source) in overwrite_allowed
            )
            for overwritten_source in overwrite_options:
                live_during = set(live_values)
                if overwritten_source is not None:
                    live_during.remove(overwritten_source)
                live_during.add(str(row['target']))
                peak = max(int(peak_so_far), len(live_during))
                if peak > int(max_peak_field_slots):
                    continue
                live_after = set(live_during)
                for value in list(live_after):
                    if value not in needed_after and value != str(row['target']) and value not in QUANTUM_OUTPUTS:
                        live_after.remove(value)
                next_state = (next_completed_mask, frozenset(live_after))
                if peak >= best_peak_by_state.get(next_state, 10**9):
                    continue
                best_peak_by_state[next_state] = peak
                previous[next_state] = (
                    (completed_mask, live_values),
                    {
                        'operation_index': operation_index,
                        'opcode': str(row['opcode']),
                        'target': str(row['target']),
                        'sources': [str(source) for source in row['sources']],
                        'overwritten_source': overwritten_source,
                        'overwrite_local_inverse_screen': (
                            None
                            if overwritten_source is None
                            else 'passed_operand_screen'
                        ),
                        'live_field_values_before_step': sorted(live_values),
                        'live_field_values_during_step': sorted(live_during),
                        'live_field_value_count_during_step': len(live_during),
                        'live_field_values_after_step': sorted(live_after),
                        'live_field_value_count_after_step': len(live_after),
                        'peak_field_slots_so_far': peak,
                    },
                )
                queue.append((next_state, peak))
    solution_rows = None if terminal is None else _reconstruct_reordered_schedule(terminal, previous)
    peak_field_slots = None if terminal_peak is None else int(terminal_peak)
    additional_slots = None if peak_field_slots is None else max(0, peak_field_slots - int(counted_arithmetic_slots))
    return {
        'schedule_model': 'reordered_dag_local_inverse_overwrite_search',
        'status': (
            'solution_found_not_full_reversible_circuit_proof'
            if terminal is not None
            else 'no_solution_with_current_budget'
        ),
        'field_bits': int(field_bits),
        'counted_arithmetic_slots': int(counted_arithmetic_slots),
        'max_peak_field_slots_searched': int(max_peak_field_slots),
        'solution_found': terminal is not None,
        'states_visited': len(previous),
        'peak_field_slots': peak_field_slots,
        'additional_field_slots_over_counted_leaf': additional_slots,
        'additional_logical_qubits_over_counted_leaf': None if additional_slots is None else additional_slots * int(field_bits),
        'overwritten_row_count': 0 if solution_rows is None else sum(1 for row in solution_rows if row['overwritten_source'] is not None),
        'invalid_overwrite_count': 0,
        'terminal_live_values': None if terminal is None else sorted(terminal[1]),
        'rows': solution_rows,
        'notes': [
            'This search reorders the expanded tail operation DAG and allows an overwrite only when the chosen operand passed the toy-boundary local inverse screen.',
            'A solution is stronger than the fixed-order destructive candidate, but it is still a schedule-level certificate rather than a Clifford-complete reversible circuit implementation.',
        ],
    }


def _reordered_slot_assignment(
    schedule_rows: Sequence[Mapping[str, Any]] | None,
    *,
    counted_arithmetic_slots: int,
    field_bits: int,
) -> Dict[str, Any]:
    if schedule_rows is None:
        return {
            'schema': 'compiler-project-tail-reordered-slot-assignment-v1',
            'status': 'no_schedule',
            'pass': False,
        }
    slot_by_value = {value: index for index, value in enumerate(QUANTUM_INPUTS)}
    rows_out = []
    peak_slot_count = len(slot_by_value)
    for row in schedule_rows:
        live_before = dict(sorted(slot_by_value.items()))
        overwritten_source = row['overwritten_source']
        if overwritten_source is None:
            occupied = set(slot_by_value.values())
            target_slot = 0
            while target_slot in occupied:
                target_slot += 1
        else:
            target_slot = slot_by_value[str(overwritten_source)]
            del slot_by_value[str(overwritten_source)]
        target = str(row['target'])
        slot_by_value[target] = target_slot
        live_during = dict(sorted(slot_by_value.items()))
        peak_slot_count = max(peak_slot_count, len(live_during))
        expected_live_after = set(str(value) for value in row['live_field_values_after_step'])
        for value in list(slot_by_value):
            if value not in expected_live_after:
                del slot_by_value[value]
        rows_out.append({
            'schedule_index': int(row['schedule_index']),
            'operation_index': int(row['operation_index']),
            'target': target,
            'target_slot': target_slot,
            'overwritten_source': overwritten_source,
            'source_slots_before_operation': {
                source: live_before[source]
                for source in row['sources']
                if source not in TABLE_CONSTANTS
            },
            'live_before': live_before,
            'live_during': live_during,
            'live_after': dict(sorted(slot_by_value.items())),
            'owner_id': f'tail_reordered_slot_{target_slot}',
        })
    owner_capacity_rows = [
        {
            'slot': slot,
            'owner_id': f'tail_reordered_slot_{slot}',
            'logical_qubits': int(field_bits),
            'capacity_field_values': 1,
            'counted_in_current_leaf_budget': slot < int(counted_arithmetic_slots),
        }
        for slot in range(peak_slot_count)
    ]
    additional_slots = max(0, peak_slot_count - int(counted_arithmetic_slots))
    return {
        'schema': 'compiler-project-tail-reordered-slot-assignment-v1',
        'status': 'slot_assignment_generated_for_reordered_schedule',
        'field_bits': int(field_bits),
        'counted_arithmetic_slots': int(counted_arithmetic_slots),
        'peak_field_slots': int(peak_slot_count),
        'additional_field_slots_over_counted_leaf': additional_slots,
        'additional_logical_qubits_over_counted_leaf': additional_slots * int(field_bits),
        'owner_capacity_rows': owner_capacity_rows,
        'rows': rows_out,
        'final_live_values': dict(sorted(slot_by_value.items())),
        'pass': (
            peak_slot_count == max(int(row['live_field_value_count_during_step']) for row in schedule_rows)
            and sorted(slot_by_value) == list(QUANTUM_OUTPUTS)
        ),
    }


def _reordered_schedule_replay_certificate(
    operation_rows: Sequence[Mapping[str, Any]],
    schedule: Mapping[str, Any],
    operand_screen: Mapping[str, Any],
    slot_assignment: Mapping[str, Any],
) -> Dict[str, Any]:
    operation_by_index = {
        int(row['index']): row
        for row in operation_rows
    }
    passing_overwrite_choices = {
        (int(choice['index']), str(choice['overwritten_source']))
        for choice in operand_screen['choices']
        if choice['pass'] is True
    }
    category_totals = {
        'ordinary': 0,
        'doubling': 0,
        'inverse': 0,
        'accumulator_infinity': 0,
        'lookup_infinity': 0,
    }
    replay_failures = []
    semantic_failures = []
    checked_non_infinity_pairs = 0
    checked_lookup_infinity_pairs = 0
    for curve in TOY_CURVES:
        modulus = int(curve['p'])
        curve_b = int(curve['b'])
        points = _subgroup_points(modulus, curve['generator'], int(curve['order']))
        for lookup in points:
            for accumulator in points:
                category_totals[_boundary_case(accumulator, lookup, modulus)] += 1
                input_triple = _canonical_projective(accumulator)
                if lookup is None:
                    checked_lookup_infinity_pairs += 1
                    output_triple = input_triple
                    output_affine = _projective_to_affine(output_triple, modulus)
                    expected_affine = _add_points(accumulator, lookup, modulus)
                    if output_affine != expected_affine and len(semantic_failures) < 4:
                        semantic_failures.append({
                            'curve': curve['name'],
                            'lookup_affine': None,
                            'accumulator_affine': None if accumulator is None else list(accumulator),
                            'output_projective': list(output_triple),
                            'output_affine': None if output_affine is None else list(output_affine),
                            'expected_affine': None if expected_affine is None else list(expected_affine),
                        })
                    continue
                checked_non_infinity_pairs += 1
                values: Dict[str, int] = {
                    'X': input_triple[0],
                    'Y': input_triple[1],
                    'Z': input_triple[2],
                }
                live_values = set(QUANTUM_INPUTS)
                for row in schedule['rows']:
                    operation = operation_by_index[int(row['operation_index'])]
                    if sorted(live_values) != row['live_field_values_before_step'] and len(replay_failures) < 4:
                        replay_failures.append({
                            'curve': curve['name'],
                            'schedule_index': row['schedule_index'],
                            'failure': 'live_before_mismatch',
                            'expected': row['live_field_values_before_step'],
                            'observed': sorted(live_values),
                        })
                    sources = [str(source) for source in operation['sources']]
                    missing_sources = [
                        source
                        for source in sources
                        if source not in TABLE_CONSTANTS and source not in live_values
                    ]
                    overwritten_source = row['overwritten_source']
                    if (
                        overwritten_source is not None
                        and (int(row['operation_index']), str(overwritten_source)) not in passing_overwrite_choices
                        and len(replay_failures) < 4
                    ):
                        replay_failures.append({
                            'curve': curve['name'],
                            'schedule_index': row['schedule_index'],
                            'failure': 'overwrite_choice_not_screened',
                            'operation_index': int(row['operation_index']),
                            'overwritten_source': overwritten_source,
                        })
                    if missing_sources and len(replay_failures) < 4:
                        replay_failures.append({
                            'curve': curve['name'],
                            'schedule_index': row['schedule_index'],
                            'failure': 'missing_live_sources',
                            'missing_sources': missing_sources,
                        })
                    target_value = _operation_value(
                        opcode=str(operation['opcode']),
                        sources=sources,
                        values=values,
                        modulus=modulus,
                        curve_b=curve_b,
                        lookup_x=lookup[0],
                        lookup_y=lookup[1],
                        constant=operation.get('constant'),
                    )
                    if overwritten_source is not None:
                        live_values.remove(str(overwritten_source))
                        del values[str(overwritten_source)]
                    target = str(operation['target'])
                    live_values.add(target)
                    values[target] = target_value
                    expected_during = set(str(value) for value in row['live_field_values_during_step'])
                    if live_values != expected_during and len(replay_failures) < 4:
                        replay_failures.append({
                            'curve': curve['name'],
                            'schedule_index': row['schedule_index'],
                            'failure': 'live_during_mismatch',
                            'expected': sorted(expected_during),
                            'observed': sorted(live_values),
                        })
                    expected_after = set(str(value) for value in row['live_field_values_after_step'])
                    for value in list(live_values):
                        if value not in expected_after:
                            live_values.remove(value)
                            del values[value]
                    if live_values != expected_after and len(replay_failures) < 4:
                        replay_failures.append({
                            'curve': curve['name'],
                            'schedule_index': row['schedule_index'],
                            'failure': 'live_after_mismatch',
                            'expected': sorted(expected_after),
                            'observed': sorted(live_values),
                        })
                output_triple = (values['X3'] % modulus, values['Y3'] % modulus, values['Z3'] % modulus)
                reference_triple = _tail_map(modulus, curve_b, lookup[0], lookup[1], *input_triple)
                output_affine = _projective_to_affine(output_triple, modulus)
                expected_affine = _add_points(accumulator, lookup, modulus)
                if (
                    output_triple != reference_triple
                    or output_affine != expected_affine
                ) and len(semantic_failures) < 4:
                    semantic_failures.append({
                        'curve': curve['name'],
                        'lookup_affine': list(lookup),
                        'accumulator_affine': None if accumulator is None else list(accumulator),
                        'input_projective': list(input_triple),
                        'output_projective': list(output_triple),
                        'reference_projective': list(reference_triple),
                        'output_affine': None if output_affine is None else list(output_affine),
                        'expected_affine': None if expected_affine is None else list(expected_affine),
                    })
    schedule_peak = int(schedule['peak_field_slots'])
    slot_peak = int(slot_assignment['peak_field_slots'])
    owner_capacity_pass = (
        slot_assignment['pass'] is True
        and slot_peak == schedule_peak
        and all(int(row['logical_qubits']) >= int(schedule['field_bits']) for row in slot_assignment['owner_capacity_rows'])
    )
    return {
        'schema': 'compiler-project-tail-reordered-schedule-replay-certificate-v1',
        'status': 'toy_boundary_reordered_schedule_executable_replay',
        'checked_non_infinity_pairs': checked_non_infinity_pairs,
        'checked_lookup_infinity_pairs': checked_lookup_infinity_pairs,
        'category_totals': category_totals,
        'operation_count': len(operation_rows),
        'schedule_row_count': len(schedule['rows']),
        'semantic_failures': semantic_failures,
        'replay_failures': replay_failures,
        'owner_capacity_pass': owner_capacity_pass,
        'pass': not semantic_failures and not replay_failures and owner_capacity_pass,
        'notes': [
            'Non-infinity lookup cases execute the reordered schedule exactly and compare X3/Y3/Z3 with the canonical tail formula and affine point-add boundary.',
            'Lookup-infinity cases are checked as the external boundary no-op used by the streamed leaf contract; the reordered arithmetic schedule is not executed for that case.',
            'Owner capacity is derived from the generated slot assignment for the executable schedule, not from a manually selected tracked-register list.',
        ],
    }


def _allowed_overwrite_schedule(
    rows: Sequence[Mapping[str, Any]],
    *,
    allowed_overwrite_indices: set[int],
    counted_arithmetic_slots: int,
    field_bits: int,
) -> Dict[str, Any]:
    last: Dict[str, int] = {value: -1 for value in QUANTUM_INPUTS}
    for index, row in enumerate(rows):
        for source in row['sources']:
            if source not in TABLE_CONSTANTS:
                last[str(source)] = index
        last.setdefault(str(row['target']), index)
    slot_by_value = {value: index for index, value in enumerate(QUANTUM_INPUTS)}
    rows_out = []
    peak_slot_count = len(slot_by_value)
    peak_step = 'initial'
    overwritten_rows = 0
    for index, row in enumerate(rows):
        sources = [str(source) for source in row['sources']]
        target = str(row['target'])
        live_before = dict(sorted(slot_by_value.items()))
        expiring_sources = [
            source
            for source in sources
            if source not in TABLE_CONSTANTS and last[source] == index and source not in QUANTUM_OUTPUTS
        ]
        overwritten_source = None
        if index in allowed_overwrite_indices and expiring_sources:
            overwritten_source = max(expiring_sources, key=lambda source: slot_by_value[source])
            target_slot = slot_by_value[overwritten_source]
            del slot_by_value[overwritten_source]
            overwritten_rows += 1
        else:
            occupied = set(slot_by_value.values())
            target_slot = 0
            while target_slot in occupied:
                target_slot += 1
        slot_by_value[target] = target_slot
        live_during_capacity = dict(sorted(slot_by_value.items()))
        if len(live_during_capacity) > peak_slot_count:
            peak_slot_count = len(live_during_capacity)
            peak_step = f'{index}:{target}'
        expired = []
        for source in expiring_sources:
            if source != overwritten_source:
                expired.append(source)
                del slot_by_value[source]
        rows_out.append({
            'index': index,
            'opcode': str(row['opcode']),
            'target': target,
            'target_slot': target_slot,
            'sources': sources,
            'overwritten_source': overwritten_source,
            'live_before': live_before,
            'live_during_capacity': live_during_capacity,
            'expired_after_step': sorted(expired),
            'live_after': dict(sorted(slot_by_value.items())),
        })
    additional_slots = max(0, int(peak_slot_count) - int(counted_arithmetic_slots))
    return {
        'schedule_model': 'local_inverse_pass_only_overwrite_candidate',
        'status': 'screened_optimizer_candidate_not_public_contract',
        'field_bits': int(field_bits),
        'counted_arithmetic_slots': int(counted_arithmetic_slots),
        'peak_field_slots': int(peak_slot_count),
        'peak_step': peak_step,
        'allowed_overwrite_indices': sorted(int(index) for index in allowed_overwrite_indices),
        'overwritten_row_count': overwritten_rows,
        'additional_field_slots_over_counted_leaf': additional_slots,
        'additional_logical_qubits_over_counted_leaf': additional_slots * int(field_bits),
        'rows': rows_out,
        'final_live_values': dict(sorted(slot_by_value.items())),
        'notes': [
            'This schedule reuses slots only for destructive rows that passed the local inverse screen.',
            'It is a search diagnostic: it shows whether the currently screened reversible subset is enough to recover the eight-field-slot proxy.',
        ],
    }


def _component_names(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    names = set(QUANTUM_INPUTS)
    for row in rows:
        names.add(str(row['target']))
        for source in row['sources']:
            if source not in TABLE_CONSTANTS:
                names.add(str(source))
    return sorted(names)


def build_tail_macro_engine(
    *,
    field_bits: int,
    counted_arithmetic_slots: int,
    kernel_non_clifford_by_opcode: Mapping[str, Any],
    selected_tail_kernel_non_clifford: int,
) -> Dict[str, Any]:
    operation_rows = _field_operation_rows(kernel_non_clifford_by_opcode)
    opcode_histogram = dict(sorted(Counter(row['opcode'] for row in operation_rows).items()))
    non_clifford_by_opcode = {
        opcode: int(kernel_non_clifford_by_opcode[opcode]) * int(count)
        for opcode, count in opcode_histogram.items()
    }
    non_clifford_total = sum(non_clifford_by_opcode.values())
    liveness = _one_compute_liveness(operation_rows)
    expanded_slot_schedule = _expanded_slot_schedule(operation_rows, counted_arithmetic_slots, field_bits)
    destructive_candidate_schedule = _destructive_candidate_schedule(operation_rows, counted_arithmetic_slots, field_bits)
    destructive_candidate_schedule['proxy_metrics']['field_slot_improvement_vs_strict_single_assignment'] = (
        int(expanded_slot_schedule['peak_field_slots'])
        - int(destructive_candidate_schedule['peak_field_slots'])
    )
    overwrite_certificate = _overwrite_local_inverse_certificate(destructive_candidate_schedule['rows'])
    destructive_candidate_schedule['local_inverse_certificate'] = overwrite_certificate
    operand_overwrite_screen = _overwrite_operand_screen(operation_rows)
    overwrite_choice_screen = _overwrite_choice_screen_from_operand_screen(
        destructive_candidate_schedule['rows'],
        operand_overwrite_screen,
    )
    destructive_candidate_schedule['overwrite_choice_screen'] = overwrite_choice_screen
    reordered_local_inverse_schedule = _reordered_local_inverse_schedule(
        operation_rows,
        operand_screen=operand_overwrite_screen,
        counted_arithmetic_slots=int(counted_arithmetic_slots),
        field_bits=int(field_bits),
        max_peak_field_slots=int(destructive_candidate_schedule['peak_field_slots']),
    )
    reordered_slot_assignment = _reordered_slot_assignment(
        reordered_local_inverse_schedule['rows'],
        counted_arithmetic_slots=int(counted_arithmetic_slots),
        field_bits=int(field_bits),
    )
    reordered_replay_certificate = _reordered_schedule_replay_certificate(
        operation_rows,
        reordered_local_inverse_schedule,
        operand_overwrite_screen,
        reordered_slot_assignment,
    )
    locally_invertible_indices = {
        int(row['index'])
        for row in overwrite_certificate['rows']
        if row['pass'] is True
    }
    local_inverse_pass_only_schedule = _allowed_overwrite_schedule(
        operation_rows,
        allowed_overwrite_indices=locally_invertible_indices,
        counted_arithmetic_slots=int(counted_arithmetic_slots),
        field_bits=int(field_bits),
    )
    counted_slots = int(counted_arithmetic_slots)
    live_after_peak_fields = int(liveness['peak_live_field_values'])
    strict_peak_fields = int(expanded_slot_schedule['peak_field_slots'])
    checks = {
        'formula_targets_match_engine_targets': (
            [target for target, _sources in TAIL_MACRO_FORMULA]
            == [row['target'] for row in _formula_rows()]
        ),
        'expanded_operation_stream_covers_formula_targets': (
            sorted(set(row['formula_target'] for row in operation_rows))
            == sorted(target for target, _sources in TAIL_MACRO_FORMULA)
        ),
        'non_clifford_total_matches_selected_tail_kernel': (
            int(non_clifford_total) == int(selected_tail_kernel_non_clifford)
        ),
        'counted_slots_cover_expanded_single_assignment_peak': strict_peak_fields <= counted_slots,
    }
    required_checks = {
        key: value
        for key, value in checks.items()
        if key != 'counted_slots_cover_expanded_single_assignment_peak'
    }
    return {
        'schema': 'compiler-project-tail-macro-engine-v1',
        'opcode': TAIL_MACRO_OPCODE,
        'field_bits': int(field_bits),
        'counted_arithmetic_slots': counted_slots,
        'quantum_inputs': list(QUANTUM_INPUTS),
        'table_constant_sources': list(TABLE_CONSTANTS),
        'quantum_outputs': list(QUANTUM_OUTPUTS),
        'formula_rows': _formula_rows(),
        'expanded_field_operation_stream': operation_rows,
        'expanded_field_value_universe': _component_names(operation_rows),
        'opcode_histogram': opcode_histogram,
        'non_clifford_by_opcode': non_clifford_by_opcode,
        'non_clifford_total': int(non_clifford_total),
        'selected_tail_kernel_non_clifford': int(selected_tail_kernel_non_clifford),
        'single_assignment_liveness': liveness,
        'expanded_slot_schedule': expanded_slot_schedule,
        'destructive_candidate_schedule': destructive_candidate_schedule,
        'slot_gap': {
            'expanded_single_assignment_peak_field_values': strict_peak_fields,
            'expanded_live_after_peak_field_values': live_after_peak_fields,
            'counted_arithmetic_slots': counted_slots,
            'additional_field_slots_needed_without_in_place_schedule': max(0, strict_peak_fields - counted_slots),
            'additional_logical_qubits_needed_without_in_place_schedule': max(0, strict_peak_fields - counted_slots) * int(field_bits),
            'fallback_schedule_additional_logical_qubits': int(expanded_slot_schedule['additional_logical_qubits_over_counted_leaf']),
            'destructive_candidate_peak_field_values': int(destructive_candidate_schedule['peak_field_slots']),
            'destructive_candidate_additional_logical_qubits': int(destructive_candidate_schedule['additional_logical_qubits_over_counted_leaf']),
            'destructive_candidate_overwrite_rows_locally_invertible': bool(overwrite_certificate['pass']),
            'local_inverse_pass_only_peak_field_values': int(local_inverse_pass_only_schedule['peak_field_slots']),
            'overwrite_choice_screen_pass': bool(overwrite_choice_screen['pass']),
            'operand_overwrite_screen_pass': bool(operand_overwrite_screen['pass']),
            'reordered_local_inverse_peak_field_values': reordered_local_inverse_schedule['peak_field_slots'],
            'reordered_local_inverse_solution_found': bool(reordered_local_inverse_schedule['solution_found']),
            'reordered_slot_assignment_peak_field_values': reordered_slot_assignment['peak_field_slots'],
            'reordered_replay_pass': bool(reordered_replay_certificate['pass']),
        },
        'local_inverse_pass_only_schedule': local_inverse_pass_only_schedule,
        'operand_overwrite_screen': operand_overwrite_screen,
        'reordered_local_inverse_schedule': reordered_local_inverse_schedule,
        'reordered_slot_assignment': reordered_slot_assignment,
        'reordered_replay_certificate': reordered_replay_certificate,
        'checks': checks,
        'pass': all(value is True for value in required_checks.values()),
        'completion_status': (
            'tail_cost_bound_to_expanded_field_operation_stream_but_in_place_schedule_unproven'
            if not checks['counted_slots_cover_expanded_single_assignment_peak']
            else 'tail_cost_and_counted_slots_bound_to_expanded_field_operation_stream'
        ),
    }


__all__ = [
    'QUANTUM_INPUTS',
    'QUANTUM_OUTPUTS',
    'TABLE_CONSTANTS',
    'TAIL_MACRO_FIELD_OPERATION_STREAM',
    'TAIL_MACRO_FORMULA',
    'TAIL_MACRO_OPCODE',
    'build_tail_macro_engine',
]
