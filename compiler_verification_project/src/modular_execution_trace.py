#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Mapping, Optional


MODULAR_EXECUTION_TRACE_SCHEMA = 'compiler-project-modular-execution-trace-v1'
PRIMITIVE_KEYS = ('ccx', 'cx', 'x', 'measurement')
MODULAR_TRACE_COLUMNS = [
    'global_suboperation_index',
    'schedule_index',
    'tail_operation_index',
    'target',
    'kind',
    'modular_opcode',
    'semantic_role',
    'sources',
    'target_slot',
    'owner_id',
    'overwritten_source',
    'non_clifford',
    'operation_count',
]


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def _sha256_payload(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode('ascii')).hexdigest()


def _stream_hash(rows: List[Mapping[str, Any]]) -> str:
    digest = hashlib.sha256()
    digest.update(('\t'.join(MODULAR_TRACE_COLUMNS) + '\n').encode('ascii'))
    for row in rows:
        digest.update(('\t'.join(_canonical_json(row[column]) for column in MODULAR_TRACE_COLUMNS) + '\n').encode('ascii'))
    return digest.hexdigest()


def _modular_opcode_index(modular_arithmetic_certificate: Mapping[str, Any]) -> Dict[str, Mapping[str, Any]]:
    return {
        str(row['opcode']): row
        for row in modular_arithmetic_certificate['modular_primitive_stream_certificate']['opcodes']
    }


def _primitive_counts_for_opcode(opcode_index: Mapping[str, Mapping[str, Any]], opcode: str) -> Dict[str, int]:
    row = opcode_index[opcode]
    return {
        key: int(row['primitive_counts_total'][key])
        for key in PRIMITIVE_KEYS
    }


def _kernel_cost(opcode_index: Mapping[str, Mapping[str, Any]], opcode: str) -> int:
    return int(opcode_index[opcode]['non_clifford_total'])


def _lookup_stream_cost(row: Mapping[str, Any], opcode_index: Mapping[str, Mapping[str, Any]]) -> int:
    return int(row['non_clifford']) - _kernel_cost(opcode_index, 'field_mul')


def _step_rows_for_opcode(opcode_index: Mapping[str, Mapping[str, Any]], opcode: str) -> List[Dict[str, Any]]:
    opcode_row = opcode_index[opcode]
    return [
        {
            'step': str(step['step']),
            'kind': str(step['kind']),
            'operation_count': int(step['operation_count']),
            'primitive_counts_total': {
                key: int(step['primitive_counts_total'][key])
                for key in PRIMITIVE_KEYS
            },
        }
        for step in opcode_row['steps']
    ]


def _make_modular_suboperation(
    *,
    opcode_index: Mapping[str, Mapping[str, Any]],
    kind: str,
    modular_opcode: str,
    semantic_role: str,
    sources: List[str],
    target: str,
    target_slot: Optional[int],
    owner_id: str,
    overwritten_source: Optional[str],
    schedule_row: Mapping[str, Any],
    global_suboperation_index: int,
) -> Dict[str, Any]:
    opcode_row = opcode_index[modular_opcode]
    return {
        'global_suboperation_index': global_suboperation_index,
        'schedule_index': int(schedule_row['schedule_index']),
        'tail_operation_index': int(schedule_row['operation_index']),
        'target': target,
        'kind': kind,
        'modular_opcode': modular_opcode,
        'semantic_role': semantic_role,
        'sources': sources,
        'target_slot': target_slot,
        'owner_id': owner_id,
        'overwritten_source': overwritten_source,
        'non_clifford': int(opcode_row['non_clifford_total']),
        'operation_count': int(opcode_row['operation_count']),
        'primitive_counts_total': _primitive_counts_for_opcode(opcode_index, modular_opcode),
        'primitive_stream_sha256': str(opcode_row['operation_stream_sha256']),
        'step_rows': _step_rows_for_opcode(opcode_index, modular_opcode),
    }


def _make_lookup_suboperation(
    *,
    opcode_index: Mapping[str, Mapping[str, Any]],
    row: Mapping[str, Any],
    schedule_row: Mapping[str, Any],
    global_suboperation_index: int,
) -> Dict[str, Any]:
    non_clifford = _lookup_stream_cost(row, opcode_index)
    return {
        'global_suboperation_index': global_suboperation_index,
        'schedule_index': int(schedule_row['schedule_index']),
        'tail_operation_index': int(schedule_row['operation_index']),
        'target': str(row['target']),
        'kind': 'lookup_interface_stream',
        'modular_opcode': None,
        'semantic_role': 'stream table-controlled lookup coordinate into field multiplication',
        'sources': [source for source in row['sources'] if str(source).startswith('lookup_')],
        'target_slot': None,
        'owner_id': 'lookup_workspace',
        'overwritten_source': None,
        'non_clifford': non_clifford,
        'operation_count': non_clifford,
        'primitive_counts_total': {'ccx': non_clifford, 'cx': 0, 'x': 0, 'measurement': 0},
        'primitive_stream_sha256': None,
        'step_rows': [],
    }


def _make_guard_suboperation(
    *,
    row: Mapping[str, Any],
    schedule_row: Mapping[str, Any],
    global_suboperation_index: int,
    guard_owner: Mapping[str, Any],
) -> Dict[str, Any]:
    non_clifford = int(row['in_place_guard_non_clifford'])
    return {
        'global_suboperation_index': global_suboperation_index,
        'schedule_index': int(schedule_row['schedule_index']),
        'tail_operation_index': int(schedule_row['operation_index']),
        'target': str(row['target']),
        'kind': 'zero_lift_guard_compute_uncompute',
        'modular_opcode': None,
        'semantic_role': 'compute and uncompute the L == 0 guard for the Y3-over-C zero-lift permutation',
        'sources': ['L'],
        'target_slot': None,
        'owner_id': str(guard_owner['owner_id']),
        'overwritten_source': str(schedule_row['overwritten_source']) if schedule_row.get('overwritten_source') is not None else None,
        'non_clifford': non_clifford,
        'operation_count': non_clifford,
        'primitive_counts_total': {'ccx': non_clifford, 'cx': 0, 'x': 0, 'measurement': 0},
        'primitive_stream_sha256': None,
        'step_rows': [],
    }


def _decompose_tail_operation(
    *,
    row: Mapping[str, Any],
    schedule_row: Mapping[str, Any],
    opcode_index: Mapping[str, Mapping[str, Any]],
    guard_owner: Mapping[str, Any],
    start_index: int,
) -> List[Dict[str, Any]]:
    opcode = str(row['opcode'])
    target = str(row['target'])
    owner_id = str(schedule_row['owner_id'])
    overwritten_source = str(schedule_row['overwritten_source']) if schedule_row.get('overwritten_source') is not None else None
    target_slot = int(schedule_row['target_slot'])
    suboperations: List[Dict[str, Any]] = []

    def append_modular(kind: str, modular_opcode: str, semantic_role: str, sources: List[str], sub_target: str = target) -> None:
        suboperations.append(_make_modular_suboperation(
            opcode_index=opcode_index,
            kind=kind,
            modular_opcode=modular_opcode,
            semantic_role=semantic_role,
            sources=sources,
            target=sub_target,
            target_slot=target_slot,
            owner_id=owner_id,
            overwritten_source=overwritten_source,
            schedule_row=schedule_row,
            global_suboperation_index=start_index + len(suboperations),
        ))

    if opcode in {'field_add', 'field_sub', 'field_sub_sum', 'field_triple', 'mul_const'}:
        append_modular('modular_field_operation', opcode, f'execute {opcode} for tail row', [str(source) for source in row['sources']])
    elif opcode in {'field_mul_lookup_x', 'field_mul_lookup_y', 'field_mul_lookup_sum'}:
        suboperations.append(_make_lookup_suboperation(
            opcode_index=opcode_index,
            row=row,
            schedule_row=schedule_row,
            global_suboperation_index=start_index + len(suboperations),
        ))
        append_modular('modular_field_operation', 'field_mul', f'execute {opcode} after streamed lookup source', [str(source) for source in row['sources']])
    elif opcode == 'field_double_mul_add':
        append_modular('fused_output_accumulator', 'field_double_mul_add', 'fused output a*b + c*d without materialized product field lanes', [str(source) for source in row['sources']])
    elif opcode == 'field_double_mul_sub':
        append_modular('fused_output_accumulator', 'field_double_mul_sub', 'fused output a*b - c*d without materialized product field lanes', [str(source) for source in row['sources']])
    else:
        raise ValueError(f'unsupported tail opcode for modular execution trace: {opcode}')

    if int(row.get('in_place_guard_non_clifford', 0)) > 0:
        suboperations.append(_make_guard_suboperation(
            row=row,
            schedule_row=schedule_row,
            global_suboperation_index=start_index + len(suboperations),
            guard_owner=guard_owner,
        ))
    return suboperations


def build_modular_execution_trace(
    *,
    tail_macro_engine: Mapping[str, Any],
    modular_arithmetic_certificate: Mapping[str, Any],
    public_candidate_materialized_circuit_manifest: Mapping[str, Any],
) -> Dict[str, Any]:
    opcode_index = _modular_opcode_index(modular_arithmetic_certificate)
    stream_by_index = {
        int(row['index']): row
        for row in tail_macro_engine['fused_output_field_operation_stream']
    }
    schedule_rows = sorted(
        tail_macro_engine['fused_output_slot_assignment']['rows'],
        key=lambda row: int(row['schedule_index']),
    )
    reversible_contract_by_schedule = {
        int(row['schedule_index']): row
        for row in tail_macro_engine['fused_output_reversible_schedule_contract']['rows']
    }
    guard_owner = tail_macro_engine['fused_output_lowering_contract']['guard_owner_capacity']
    trace_rows = []
    suboperation_rows = []
    global_suboperation_index = 0
    for schedule_row in schedule_rows:
        operation_index = int(schedule_row['operation_index'])
        row = stream_by_index[operation_index]
        reversible_contract = reversible_contract_by_schedule[int(schedule_row['schedule_index'])]
        suboperations = _decompose_tail_operation(
            row=row,
            schedule_row=schedule_row,
            opcode_index=opcode_index,
            guard_owner=guard_owner,
            start_index=global_suboperation_index,
        )
        reconstructed_non_clifford = sum(int(suboperation['non_clifford']) for suboperation in suboperations)
        global_suboperation_index += len(suboperations)
        suboperation_rows.extend(suboperations)
        trace_rows.append({
            'schedule_index': int(schedule_row['schedule_index']),
            'tail_operation_index': operation_index,
            'opcode': str(row['opcode']),
            'target': str(row['target']),
            'sources': [str(source) for source in row['sources']],
            'target_slot': int(schedule_row['target_slot']),
            'owner_id': str(schedule_row['owner_id']),
            'overwritten_source': str(schedule_row['overwritten_source']) if schedule_row.get('overwritten_source') is not None else None,
            'live_before': dict(schedule_row['live_before']),
            'live_during': dict(schedule_row['live_during']),
            'live_after': dict(schedule_row['live_after']),
            'reversible_contract_kind': str(reversible_contract['contract_kind']),
            'reversible_contract_pass': bool(reversible_contract['reversible_field_operation_contract_pass']),
            'tail_row_non_clifford': int(row['non_clifford']),
            'reconstructed_non_clifford': reconstructed_non_clifford,
            'cost_matches_tail_row': reconstructed_non_clifford == int(row['non_clifford']),
            'suboperation_start': int(suboperations[0]['global_suboperation_index']),
            'suboperation_end_exclusive': int(suboperations[-1]['global_suboperation_index']) + 1,
            'suboperations': suboperations,
        })
    modular_suboperations = [
        row
        for row in suboperation_rows
        if row['modular_opcode'] is not None
    ]
    modular_opcode_histogram: Dict[str, int] = {}
    for row in modular_suboperations:
        opcode = str(row['modular_opcode'])
        modular_opcode_histogram[opcode] = modular_opcode_histogram.get(opcode, 0) + 1
    reconstructed_non_clifford = sum(int(row['reconstructed_non_clifford']) for row in trace_rows)
    scheduled_tail_non_clifford = sum(int(row['tail_row_non_clifford']) for row in trace_rows)
    source_digests = {
        'tail_macro_engine_sha256': _sha256_payload(tail_macro_engine),
        'modular_arithmetic_certificate_sha256': _sha256_payload(modular_arithmetic_certificate),
        'public_candidate_materialized_circuit_manifest_sha256': _sha256_payload(public_candidate_materialized_circuit_manifest),
    }
    stream_sha256 = _stream_hash(suboperation_rows)
    engine_integration = public_candidate_materialized_circuit_manifest['modular_arithmetic_engine_integration']
    checks = {
        'tail_schedule_rows_cover_fused_output_stream': sorted(stream_by_index) == sorted(int(row['operation_index']) for row in schedule_rows),
        'every_tail_row_reconstructs_non_clifford': all(row['cost_matches_tail_row'] is True for row in trace_rows),
        'all_reversible_contract_rows_pass': all(row['reversible_contract_pass'] is True for row in trace_rows),
        'slot_liveness_stays_within_seven_field_slots': all(len(row['live_during']) <= 7 and len(row['live_after']) <= 7 for row in trace_rows),
        'all_non_lookup_sources_are_live_before_use': all(
            source.startswith('lookup_') or source in row['live_before']
            for row in trace_rows
            for source in row['sources']
        ),
        'modular_stream_certificate_passes': modular_arithmetic_certificate['modular_primitive_stream_certificate']['pass'] is True,
        'modular_suboperations_bind_known_primitive_streams': all(
            row['primitive_stream_sha256'] == opcode_index[str(row['modular_opcode'])]['operation_stream_sha256']
            for row in modular_suboperations
        ),
        'public_engine_modular_integration_passes': engine_integration['pass'] is True,
        'public_engine_arithmetic_rows_cover_trace_liveness': int(engine_integration['strict_liveness_projection']['rows_checked']) == int(public_candidate_materialized_circuit_manifest['arithmetic_leaf_block_row_count']),
        'scheduled_tail_rows_sum_selected_tail_non_clifford': scheduled_tail_non_clifford == int(tail_macro_engine['selected_tail_kernel_non_clifford']),
        'trace_reconstructs_selected_tail_non_clifford': reconstructed_non_clifford == int(tail_macro_engine['selected_tail_kernel_non_clifford']),
        'zero_lift_guard_is_explicit_and_counted': sum(1 for row in suboperation_rows if row['kind'] == 'zero_lift_guard_compute_uncompute') == 1 and any(int(row['non_clifford']) == int(guard_owner['non_clifford']) for row in suboperation_rows if row['kind'] == 'zero_lift_guard_compute_uncompute'),
    }
    return {
        'schema': MODULAR_EXECUTION_TRACE_SCHEMA,
        'status': 'selected_tail_schedule_decomposed_into_modular_execution_trace',
        'source_digests': source_digests,
        'trace_encoding': MODULAR_TRACE_COLUMNS,
        'trace_stream_sha256': stream_sha256,
        'tail_schedule_row_count': len(trace_rows),
        'suboperation_count': len(suboperation_rows),
        'modular_suboperation_count': len(modular_suboperations),
        'modular_opcode_histogram': {
            key: int(value)
            for key, value in sorted(modular_opcode_histogram.items())
        },
        'scheduled_tail_non_clifford': scheduled_tail_non_clifford,
        'reconstructed_non_clifford': reconstructed_non_clifford,
        'selected_tail_kernel_non_clifford': int(tail_macro_engine['selected_tail_kernel_non_clifford']),
        'trace_rows': trace_rows,
        'suboperation_preview_head': suboperation_rows[:8],
        'suboperation_preview_tail': suboperation_rows[-8:],
        'checks': checks,
        'pass': all(checks.values()),
        'boundary': [
            'This trace gives one scheduled tail-level modular execution trace with explicit slots, source liveness, reversible overwrite contracts, modular primitive stream bindings, lookup stream rows, and the zero-lift guard row.',
            'The scheduled_modular_primitive_netlist artifact expands this compact trace into a deterministic primitive-row stream with segment hashes and derived CCX/measurement totals.',
        ],
    }


__all__ = ['MODULAR_EXECUTION_TRACE_SCHEMA', 'build_modular_execution_trace']
