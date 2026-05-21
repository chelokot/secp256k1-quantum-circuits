#!/usr/bin/env python3

from __future__ import annotations

from collections import deque
from typing import Any, Dict, Iterable, List, Optional, Sequence


TAIL_MACRO_OPCODE = 'complete_a0_all_streamed_tail'
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
QUANTUM_INPUTS = ('X', 'Y', 'Z')
TABLE_CONSTANTS = ('lookup_x', 'lookup_y', 'lookup_x_plus_y')
QUANTUM_OUTPUTS = ('X3', 'Y3', 'Z3')


def _last_uses(formula: Sequence[tuple[str, Sequence[str]]]) -> Dict[str, int]:
    last: Dict[str, int] = {value: -1 for value in QUANTUM_INPUTS}
    for index, (target, sources) in enumerate(formula):
        for source in sources:
            if source not in TABLE_CONSTANTS:
                last[source] = index
        last.setdefault(target, index)
    return last


def _source_rows(formula: Sequence[tuple[str, Sequence[str]]]) -> List[Dict[str, Any]]:
    last = _last_uses(formula)
    rows = []
    for index, (target, sources) in enumerate(formula):
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


def _one_compute_liveness(formula: Sequence[tuple[str, Sequence[str]]]) -> Dict[str, Any]:
    last = _last_uses(formula)
    live = set(QUANTUM_INPUTS)
    rows = [{
        'step': 'initial',
        'target': None,
        'live_field_values': sorted(live),
        'live_field_value_count': len(live),
    }]
    peak_count = len(live)
    peak_step = 'initial'
    peak_live = sorted(live)
    for index, (target, sources) in enumerate(formula):
        live.add(target)
        expired = []
        for source in sources:
            if source not in TABLE_CONSTANTS and last[source] == index and source not in QUANTUM_OUTPUTS:
                live.discard(source)
                expired.append(source)
        row = {
            'step': index,
            'target': target,
            'sources': list(sources),
            'expired_after_step': sorted(expired),
            'live_field_values': sorted(live),
            'live_field_value_count': len(live),
        }
        rows.append(row)
        if len(live) > peak_count:
            peak_count = len(live)
            peak_step = f'{index}:{target}'
            peak_live = sorted(live)
    return {
        'schedule_model': 'single_assignment_no_recompute_formula_dag',
        'description': 'Each named formula value is computed once in source order and remains live until its last formula use.',
        'peak_live_field_values': peak_count,
        'peak_step': peak_step,
        'peak_live_values': peak_live,
        'rows': rows,
    }


def _component_names(formula: Iterable[tuple[str, Sequence[str]]]) -> List[str]:
    names = set(QUANTUM_INPUTS)
    for target, sources in formula:
        names.add(target)
        for source in sources:
            if source not in TABLE_CONSTANTS:
                names.add(source)
    return sorted(names)


def _reconstruct_pebble_schedule(
    terminal_state: frozenset[str],
    previous: Dict[frozenset[str], Optional[frozenset[str]]],
    action: Dict[frozenset[str], Dict[str, Any]],
) -> List[Dict[str, Any]]:
    rows = []
    current: Optional[frozenset[str]] = terminal_state
    while current is not None and previous[current] is not None:
        row = dict(action[current])
        row['live_field_values_after_step'] = sorted(current)
        row['live_field_value_count_after_step'] = len(current)
        rows.append(row)
        current = previous[current]
    rows.reverse()
    for index, row in enumerate(rows):
        row['index'] = index
    return rows


def _non_destructive_recompute_search(
    formula: Sequence[tuple[str, Sequence[str]]],
    minimum_budget: int,
    maximum_budget: int,
) -> Dict[str, Any]:
    producers = {
        target: tuple(source for source in sources if source not in TABLE_CONSTANTS)
        for target, sources in formula
    }
    initial_state = frozenset(QUANTUM_INPUTS)
    goal_outputs = frozenset(QUANTUM_OUTPUTS)
    budget_rows = []
    first_solution: Optional[Dict[str, Any]] = None
    for budget in range(minimum_budget, maximum_budget + 1):
        queue = deque([initial_state])
        previous: Dict[frozenset[str], Optional[frozenset[str]]] = {initial_state: None}
        action: Dict[frozenset[str], Dict[str, Any]] = {}
        terminal_state: Optional[frozenset[str]] = None
        while queue:
            state = queue.popleft()
            if goal_outputs.issubset(state):
                terminal_state = state
                break
            for target, dependencies in producers.items():
                if target in state or len(state) >= budget:
                    continue
                if not all(dependency in state for dependency in dependencies):
                    continue
                next_state = frozenset((*state, target))
                if next_state in previous:
                    continue
                previous[next_state] = state
                action[next_state] = {
                    'operation': 'compute',
                    'target': target,
                    'dependencies': list(dependencies),
                }
                queue.append(next_state)
            for node in sorted(state):
                if node in QUANTUM_OUTPUTS:
                    continue
                next_state = frozenset(value for value in state if value != node)
                if next_state in previous:
                    continue
                previous[next_state] = state
                action[next_state] = {
                    'operation': 'drop',
                    'target': node,
                    'dependencies': [],
                }
                queue.append(next_state)
        row = {
            'field_value_budget': budget,
            'solution_found': terminal_state is not None,
            'states_visited': len(previous),
        }
        if terminal_state is not None:
            schedule = _reconstruct_pebble_schedule(terminal_state, previous, action)
            row['step_count'] = len(schedule)
            row['peak_live_field_values'] = max(
                [len(initial_state)] + [int(step['live_field_value_count_after_step']) for step in schedule]
            )
            first_solution = {
                'minimum_peak_field_values': budget,
                'terminal_live_field_values': sorted(terminal_state),
                'schedule': schedule,
            }
            budget_rows.append(row)
            break
        budget_rows.append(row)
    return {
        'schedule_model': 'black_pebble_non_destructive_recompute_formula_dag',
        'description': 'A field value can be computed when all quantum dependencies are live, and non-output values may be dropped and later recomputed. No operation may overwrite a dependency in place.',
        'initial_live_field_values': list(QUANTUM_INPUTS),
        'goal_outputs': list(QUANTUM_OUTPUTS),
        'budget_rows': budget_rows,
        'first_solution': first_solution,
        'status': (
            'non_destructive_recompute_still_exceeds_counted_slots'
            if first_solution is None or int(first_solution['minimum_peak_field_values']) > minimum_budget
            else 'non_destructive_recompute_fits_counted_slots'
        ),
    }


def build_tail_macro_liveness(field_bits: int, counted_arithmetic_slots: int) -> Dict[str, Any]:
    formula = list(TAIL_MACRO_FORMULA)
    one_compute = _one_compute_liveness(formula)
    recompute_search = _non_destructive_recompute_search(
        formula,
        minimum_budget=int(counted_arithmetic_slots),
        maximum_budget=int(one_compute['peak_live_field_values']),
    )
    peak_fields = int(one_compute['peak_live_field_values'])
    counted_fields = int(counted_arithmetic_slots)
    additional_fields = max(0, peak_fields - counted_fields)
    return {
        'schema': 'compiler-project-tail-macro-liveness-v1',
        'opcode': TAIL_MACRO_OPCODE,
        'field_bits': int(field_bits),
        'counted_arithmetic_slots': counted_fields,
        'source_boundary': {
            'formula_source': 'src/verifier.py complete_a0_all_streamed_tail branch',
            'lowering_source': 'compiler_verification_project/src/arithmetic_lowering.py _complete_a0_all_streamed_tail_kernel',
        },
        'quantum_inputs': list(QUANTUM_INPUTS),
        'table_constant_sources': list(TABLE_CONSTANTS),
        'quantum_outputs': list(QUANTUM_OUTPUTS),
        'formula_rows': _source_rows(formula),
        'field_value_universe': _component_names(formula),
        'one_compute_liveness': one_compute,
        'non_destructive_recompute_search': recompute_search,
        'gap_analysis': {
            'one_compute_peak_field_values': peak_fields,
            'non_destructive_recompute_minimum_peak_field_values': int(recompute_search['first_solution']['minimum_peak_field_values']) if recompute_search['first_solution'] else None,
            'counted_arithmetic_slots': counted_fields,
            'additional_field_slots_needed_without_recompute_or_destructive_schedule': additional_fields,
            'additional_logical_qubits_needed_without_recompute_or_destructive_schedule': additional_fields * int(field_bits),
            'status': (
                'current_three_slot_claim_requires_a_destructive_or_recompute_schedule'
                if additional_fields
                else 'single_assignment_formula_dag_fits_counted_slots'
            ),
        },
        'pass': True,
        'notes': [
            'This diagnostic is intentionally not a proof of the three-slot macro. It is a generated lower-bound pressure test for the current formula DAG.',
            'The single-assignment formula DAG peaks above the counted three arithmetic slots, and the non-destructive recompute pebble search also fails below that peak.',
            'The current headline therefore requires a separately generated destructive/in-place macro schedule or a different resource point.',
            'The artifact exists to prevent the macro-liveness gap from being hidden inside prose while the full scheduled primitive macro is being developed.',
        ],
    }


__all__ = ['build_tail_macro_liveness']
