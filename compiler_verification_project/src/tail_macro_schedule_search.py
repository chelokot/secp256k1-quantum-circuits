#!/usr/bin/env python3

from __future__ import annotations

from collections import deque
from itertools import combinations
from typing import Any, Dict, FrozenSet, List, Mapping, Sequence, Tuple

from tail_macro_liveness import QUANTUM_INPUTS, QUANTUM_OUTPUTS, TABLE_CONSTANTS, TAIL_MACRO_FORMULA, TAIL_MACRO_OPCODE
from tail_macro_reversibility import TOY_CURVES, Point, _canonical_projective, _subgroup_points


FormulaValues = Dict[str, int]


def _formula_values(curve: Mapping[str, Any], lookup: Tuple[int, int], accumulator: Point) -> FormulaValues:
    modulus = int(curve['p'])
    curve_b = int(curve['b'])
    lookup_x, lookup_y = lookup
    lookup_x_plus_y = (lookup_x + lookup_y) % modulus
    accum_x, accum_y, accum_z = _canonical_projective(accumulator)
    values = {
        'X': accum_x,
        'Y': accum_y,
        'Z': accum_z,
    }
    for target, _sources in TAIL_MACRO_FORMULA:
        if target == 'G':
            values[target] = (values['X'] + values['Y']) % modulus
        elif target == 'H':
            values[target] = (values['G'] * lookup_x_plus_y) % modulus
        elif target == 'A':
            values[target] = (values['X'] * lookup_x) % modulus
        elif target == 'Zx':
            values[target] = (values['Z'] * lookup_x) % modulus
        elif target == 'C':
            values[target] = (3 * curve_b * (values['X'] + values['Zx'])) % modulus
        elif target == 'I':
            values[target] = (values['Y'] * lookup_y) % modulus
        elif target == 'K':
            values[target] = (values['H'] - values['A'] - values['I']) % modulus
        elif target == 'L':
            values[target] = (3 * values['A']) % modulus
        elif target == 'yZ':
            values[target] = (lookup_y * values['Z']) % modulus
        elif target == 'E':
            values[target] = (values['Y'] + values['yZ']) % modulus
        elif target == 'F':
            values[target] = (3 * curve_b * values['Z']) % modulus
        elif target == 'M':
            values[target] = (values['I'] + values['F']) % modulus
        elif target == 'N':
            values[target] = (values['I'] - values['F']) % modulus
        elif target == 'KN':
            values[target] = (values['K'] * values['N']) % modulus
        elif target == 'EC':
            values[target] = (values['E'] * values['C']) % modulus
        elif target == 'NM':
            values[target] = (values['N'] * values['M']) % modulus
        elif target == 'CL':
            values[target] = (values['C'] * values['L']) % modulus
        elif target == 'ME':
            values[target] = (values['M'] * values['E']) % modulus
        elif target == 'LK':
            values[target] = (values['L'] * values['K']) % modulus
        elif target == 'X3':
            values[target] = (values['KN'] - values['EC']) % modulus
        elif target == 'Y3':
            values[target] = (values['NM'] + values['CL']) % modulus
        elif target == 'Z3':
            values[target] = (values['ME'] + values['LK']) % modulus
        else:
            raise ValueError(f'unknown tail macro formula target: {target}')
    return values


def _injective_on_domain(live_values: Sequence[str], value_rows: Sequence[FormulaValues]) -> bool:
    seen = set()
    ordered_values = tuple(sorted(live_values))
    for row in value_rows:
        tuple_value = tuple(row[value] for value in ordered_values)
        if tuple_value in seen:
            return False
        seen.add(tuple_value)
    return True


def _reconstruct_schedule(
    terminal: FrozenSet[str],
    previous: Mapping[FrozenSet[str], FrozenSet[str] | None],
    actions: Mapping[FrozenSet[str], Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    rows = []
    state = terminal
    while previous[state] is not None:
        row = dict(actions[state])
        row['live_field_values_after_step'] = sorted(state)
        row['live_field_value_count_after_step'] = len(state)
        rows.append(row)
        parent = previous[state]
        assert parent is not None
        state = parent
    rows.reverse()
    for index, row in enumerate(rows):
        row['index'] = index
    return rows


def _search_curve(curve: Mapping[str, Any], budget: int) -> Dict[str, Any]:
    lookup = curve['generator']
    value_rows = [
        _formula_values(curve, lookup, accumulator)
        for accumulator in _subgroup_points(int(curve['p']), curve['generator'], int(curve['order']))
    ]
    producers = {
        target: tuple(source for source in sources if source not in TABLE_CONSTANTS)
        for target, sources in TAIL_MACRO_FORMULA
    }
    initial_state = frozenset(QUANTUM_INPUTS)
    goal_outputs = set(QUANTUM_OUTPUTS)
    queue = deque([initial_state])
    previous: Dict[FrozenSet[str], FrozenSet[str] | None] = {initial_state: None}
    actions: Dict[FrozenSet[str], Mapping[str, Any]] = {}
    terminal = None
    while queue:
        state = queue.popleft()
        if goal_outputs.issubset(state):
            terminal = state
            break
        for target, dependencies in producers.items():
            if target in state or not all(dependency in state for dependency in dependencies):
                continue
            candidates = set(state)
            candidates.add(target)
            max_keep = min(int(budget), len(candidates))
            for keep_count in range(1, max_keep + 1):
                for kept_tuple in combinations(sorted(candidates), keep_count):
                    kept = frozenset(kept_tuple)
                    if target not in kept or kept in previous:
                        continue
                    if not _injective_on_domain(kept_tuple, value_rows):
                        continue
                    previous[kept] = state
                    actions[kept] = {
                        'operation': 'compute_then_keep_injective_subset',
                        'target': target,
                        'dependencies': list(dependencies),
                        'dropped_field_values': sorted(candidates - set(kept)),
                    }
                    queue.append(kept)
    return {
        'curve': curve['name'],
        'lookup_point_policy': 'generator_point_as_nonzero_lookup_entry',
        'field_value_budget': int(budget),
        'canonical_accumulator_domain_size': int(curve['order']),
        'solution_found': terminal is not None,
        'states_visited': len(previous),
        'terminal_live_field_values': None if terminal is None else sorted(terminal),
        'schedule': None if terminal is None else _reconstruct_schedule(terminal, previous, actions),
    }


def build_tail_macro_schedule_search(counted_arithmetic_slots: int) -> Dict[str, Any]:
    rows = [_search_curve(curve, int(counted_arithmetic_slots)) for curve in TOY_CURVES]
    return {
        'schema': 'compiler-project-tail-macro-schedule-search-v1',
        'opcode': TAIL_MACRO_OPCODE,
        'schedule_model': 'formula_dag_compute_then_keep_injective_subset',
        'field_value_budget': int(counted_arithmetic_slots),
        'rows': rows,
        'any_checked_curve_has_solution': any(bool(row['solution_found']) for row in rows),
        'all_checked_curves_exhausted_without_solution': all(not bool(row['solution_found']) for row in rows),
        'notes': [
            'This search is more permissive than non-destructive pebbling: after a formula value is computed, old live values may be dropped whenever the remaining live tuple is still injective over the canonical accumulator domain.',
            'The checked three-slot budget still finds no schedule for the current formula DAG on any curated toy generator lookup.',
            'This does not prove that no different formula or no explicit permutation-extension implementation can realize a three-field-register tail.',
        ],
    }


__all__ = ['build_tail_macro_schedule_search']
