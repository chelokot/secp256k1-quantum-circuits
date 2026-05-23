#!/usr/bin/env python3

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Mapping, Sequence


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
        },
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
