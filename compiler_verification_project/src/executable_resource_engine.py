#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Mapping

from resource_ir_engine import evaluate_counted_resource_ir, evaluate_resource_contract


EXECUTABLE_RESOURCE_ENGINE_SCHEMA = 'compiler-project-executable-resource-engine-v1'


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def _sha256_payload(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode('ascii')).hexdigest()


def owner_capacity_row(owner_id: str, logical_qubits: int, source: str, required: Mapping[str, int]) -> Dict[str, Any]:
    required_peak = sum(int(value) for value in required.values())
    return {
        'owner_id': owner_id,
        'logical_qubits': int(logical_qubits),
        'source': source,
        'required_live_wires': {key: int(value) for key, value in required.items()},
        'required_peak_qubits': required_peak,
        'capacity_margin_qubits': int(logical_qubits) - required_peak,
        'capacity_pass': int(logical_qubits) >= required_peak,
    }


def owned_wire(wire_id: str, owner_id: str, qubits: int, role: str) -> Dict[str, Any]:
    return {
        'wire_id': wire_id,
        'owner_id': owner_id,
        'qubits': int(qubits),
        'role': role,
    }


def schedule_event(
    *,
    event_id: str,
    pc_range: List[int],
    source_instruction_pcs: List[int],
    source_instruction_ops: List[str],
    event_type: str,
    label: str,
    live_wire_ids: List[str],
    stream_table: str | None = None,
    stream_chunk_index: int | None = None,
) -> Dict[str, Any]:
    event: Dict[str, Any] = {
        'event_id': event_id,
        'pc_range': [int(value) for value in pc_range],
        'source_instruction_pcs': [int(value) for value in source_instruction_pcs],
        'source_instruction_ops': [str(value) for value in source_instruction_ops],
        'event_type': event_type,
        'label': label,
        'live_wire_ids': list(live_wire_ids),
    }
    if stream_table is not None:
        event['stream_table'] = stream_table
    if stream_chunk_index is not None:
        event['stream_chunk_index'] = int(stream_chunk_index)
    return event


def _interval(interval_id: str, label: str, live_wire_ids: List[str], wire_catalog: Mapping[str, Dict[str, Any]]) -> Dict[str, Any]:
    owner_peaks: Dict[str, int] = {}
    for wire_id in live_wire_ids:
        wire = wire_catalog[wire_id]
        owner_peaks[wire['owner_id']] = owner_peaks.get(wire['owner_id'], 0) + int(wire['qubits'])
    return {
        'interval_id': interval_id,
        'label': label,
        'live_wire_ids': live_wire_ids,
        'owner_live_qubits': owner_peaks,
        'total_live_qubits': sum(owner_peaks.values()),
    }


def _interval_from_schedule_event(event: Mapping[str, Any], wire_catalog: Mapping[str, Dict[str, Any]]) -> Dict[str, Any]:
    return _interval(
        str(event['event_id']),
        str(event['label']),
        [str(wire_id) for wire_id in event['live_wire_ids']],
        wire_catalog,
    )


def _owner_peak(intervals: List[Dict[str, Any]], wire_catalog: Mapping[str, Dict[str, Any]]) -> Dict[str, int]:
    owner_ids = sorted({wire_catalog[wire_id]['owner_id'] for interval in intervals for wire_id in interval['live_wire_ids']})
    return {
        owner_id: max(int(interval['owner_live_qubits'].get(owner_id, 0)) for interval in intervals)
        for owner_id in owner_ids
    }


def build_reusable_chunk_executable_liveness(
    *,
    executable_leaf: Mapping[str, Any],
    stream_rows: List[Dict[str, Any]],
    owners: List[Dict[str, Any]],
    field_bits: int,
    folded_control_qubits: int,
    control_qubits: int,
    phase_qubits: int,
) -> Dict[str, Any]:
    arithmetic_owner = 'arithmetic_slot_register_file'
    lookup_owner = 'lookup_workspace'
    control_owner = 'control_slot_register_file'
    phase_owner = 'phase_shell_live_register'
    wire_catalog: Dict[str, Dict[str, Any]] = {}
    duplicate_wire_definitions: List[str] = []

    def register_wire(wire: Dict[str, Any]) -> str:
        wire_id = str(wire['wire_id'])
        previous = wire_catalog.get(wire_id)
        if previous is not None and previous != wire:
            duplicate_wire_definitions.append(wire_id)
        wire_catalog[wire_id] = wire
        return wire_id

    arithmetic_wires = [
        register_wire(owned_wire(slot, arithmetic_owner, field_bits, 'field_arithmetic_slot'))
        for slot in executable_leaf['arithmetic_slots']
    ]
    carried_wires = [
        slot
        for slot in executable_leaf['arithmetic_slots']
        if slot != executable_leaf['chunk_contract']['reusable_chunk_slot']
    ]
    control_wires = [
        register_wire(owned_wire(slot, control_owner, 1, 'leaf_control_flag'))
        for slot in executable_leaf['control_slots']
    ]
    folded_lookup_wire = register_wire(
        owned_wire(
            'folded_lookup_control_workspace',
            lookup_owner,
            folded_control_qubits,
            'folded_lookup_decode_control_workspace',
        )
    )
    phase_wire = register_wire(owned_wire('semiclassical_qft_live_phase_bit', phase_owner, phase_qubits, 'live_phase_bit'))
    instruction_by_pc = {
        int(instruction['pc']): instruction
        for instruction in executable_leaf['instructions']
    }
    tail_instruction = executable_leaf['instructions'][-1]

    def source_ops(source_pcs: List[int]) -> List[str]:
        return [str(instruction_by_pc[pc]['op']) for pc in source_pcs]

    events: List[Dict[str, Any]] = [
        schedule_event(
            event_id='pc0_2_load_carried_inputs',
            pc_range=[0, 2],
            source_instruction_pcs=[0, 1, 2],
            source_instruction_ops=source_ops([0, 1, 2]),
            event_type='load_carried_inputs',
            label='load Q.X/Q.Y/Q.Z into carried field slots',
            live_wire_ids=carried_wires + [phase_wire],
        ),
        schedule_event(
            event_id='pc3_lookup_meta',
            pc_range=[3, 3],
            source_instruction_pcs=[3],
            source_instruction_ops=source_ops([3]),
            event_type='lookup_metadata',
            label='lookup metadata and folded lookup controls',
            live_wire_ids=carried_wires + [folded_lookup_wire, phase_wire],
        ),
        schedule_event(
            event_id='pc4_lookup_infinity_flag',
            pc_range=[4, 4],
            source_instruction_pcs=[4],
            source_instruction_ops=source_ops([4]),
            event_type='lookup_infinity_flag',
            label='derive lookup-infinity flag from metadata',
            live_wire_ids=carried_wires + [folded_lookup_wire] + control_wires + [phase_wire],
        ),
    ]
    for index, row in enumerate(stream_rows):
        target_wire = register_wire(
            owned_wire(
                f"qroam_chunk_target__{row['table']}__chunk_{row['chunk_index']}",
                lookup_owner,
                int(row['live_target_qubits']),
                'standard_qroamclean_k1_chunk_target',
            )
        )
        junk_qubits = int(row['junk_register_qubits'])
        junk_wires = []
        if junk_qubits:
            junk_wires.append(
                register_wire(
                    owned_wire(
                        f"qroam_chunk_junk__{row['table']}__chunk_{row['chunk_index']}",
                        lookup_owner,
                        junk_qubits,
                        'standard_qroamclean_junk_registers',
                    )
                )
            )
        events.append(
            schedule_event(
                event_id=f"pc5_stream_{index:02d}_{row['table']}_chunk_{row['chunk_index']}",
                pc_range=[5, 5],
                source_instruction_pcs=[int(tail_instruction['pc'])],
                source_instruction_ops=[str(tail_instruction['op'])],
                event_type='qroam_chunk_load_consume_uncompute',
                label=f"load, consume, and uncompute {row['table']} chunk {row['chunk_index']}",
                live_wire_ids=arithmetic_wires + [folded_lookup_wire, target_wire] + junk_wires + control_wires + [phase_wire],
                stream_table=str(row['table']),
                stream_chunk_index=int(row['chunk_index']),
            )
        )
    schedule_wire_ids = sorted({wire_id for event in events for wire_id in event['live_wire_ids']})
    event_ids = [str(event['event_id']) for event in events]
    source_instruction_pcs = [
        int(pc)
        for event in events
        for pc in event['source_instruction_pcs']
    ]
    qroam_events = [
        event for event in events
        if event['event_type'] == 'qroam_chunk_load_consume_uncompute'
    ]
    executable_schedule_ir = {
        'schema': 'compiler-project-reusable-chunk-executable-schedule-ir-v1',
        'derivation': 'ordered executable schedule events are the source for reusable-chunk liveness intervals',
        'source_leaf_instruction_stream': executable_leaf['instructions'],
        'wire_catalog': wire_catalog,
        'event_count': len(events),
        'events': events,
        'checks': {
            'event_ids_are_unique': len(event_ids) == len(set(event_ids)),
            'all_event_wires_exist_in_catalog': all(wire_id in wire_catalog for wire_id in schedule_wire_ids),
            'source_instruction_pcs_exist': all(pc in instruction_by_pc for pc in source_instruction_pcs),
            'source_instruction_ops_match_leaf': all(
                [str(instruction_by_pc[int(pc)]['op']) for pc in event['source_instruction_pcs']] == event['source_instruction_ops']
                for event in events
            ),
            'qroam_stream_events_match_stream_rows': len(qroam_events) == len(stream_rows),
            'qroam_events_source_tail_instruction': all(
                event['source_instruction_pcs'] == [int(tail_instruction['pc'])]
                and event['source_instruction_ops'] == [str(tail_instruction['op'])]
                and str(tail_instruction['op']) == 'complete_a0_reusable_chunk_tail'
                for event in qroam_events
            ),
            'qchunk_live_during_each_qroam_stream_event': all(
                executable_leaf['chunk_contract']['reusable_chunk_slot'] in event['live_wire_ids']
                for event in qroam_events
            ),
            'no_full_coordinate_lane_wire_is_scheduled': not any(
                wire_id in ('lookup_x', 'lookup_y', 'lookup_x_plus_y')
                for wire_id in schedule_wire_ids
            ),
        },
    }
    executable_schedule_ir['pass'] = all(executable_schedule_ir['checks'].values())
    intervals = [
        _interval_from_schedule_event(event, wire_catalog)
        for event in executable_schedule_ir['events']
    ]
    owner_capacity = {owner['owner_id']: int(owner['logical_qubits']) for owner in owners}
    owner_peak = _owner_peak(intervals, wire_catalog)
    all_wire_ids = [wire_id for interval in intervals for wire_id in interval['live_wire_ids']]
    duplicate_owner_wires = sorted(set(duplicate_wire_definitions))
    unknown_owner_wires = sorted(
        wire_id for wire_id in set(all_wire_ids)
        if wire_catalog[wire_id]['owner_id'] not in owner_capacity
    )
    over_capacity_owners = sorted(
        owner_id for owner_id, peak in owner_peak.items()
        if peak > owner_capacity[owner_id]
    )
    peak_interval = max(intervals, key=lambda interval: int(interval['total_live_qubits']))
    checks = {
        'every_wire_has_exactly_one_owner': not duplicate_owner_wires,
        'every_owner_is_declared': not unknown_owner_wires,
        'owner_peaks_fit_capacity': not over_capacity_owners,
        'global_peak_equals_sum_of_interval_liveness': int(peak_interval['total_live_qubits']) == max(int(interval['total_live_qubits']) for interval in intervals),
        'qroam_target_and_qchunk_are_concurrently_live': any(
            executable_leaf['chunk_contract']['reusable_chunk_slot'] in interval['live_wire_ids']
            and any(str(wire_id).startswith('qroam_chunk_target__') for wire_id in interval['live_wire_ids'])
            for interval in intervals
        ),
        'no_full_coordinate_lane_wire_is_live': not any(
            wire_id in ('lookup_x', 'lookup_y', 'lookup_x_plus_y')
            for wire_id in set(all_wire_ids)
        ),
    }
    return {
        'schema': 'compiler-project-reusable-chunk-executable-liveness-v1',
        'derivation': 'interval liveness derived from executable reusable-chunk schedule IR and declared counted owners',
        'wire_catalog': wire_catalog,
        'source_schedule_schema': executable_schedule_ir['schema'],
        'source_schedule_event_count': executable_schedule_ir['event_count'],
        'intervals': intervals,
        'owner_peak_live_qubits': owner_peak,
        'owner_capacity_qubits': owner_capacity,
        'global_peak_interval_id': peak_interval['interval_id'],
        'global_peak_live_qubits': int(peak_interval['total_live_qubits']),
        'duplicate_owner_wires': duplicate_owner_wires,
        'unknown_owner_wires': unknown_owner_wires,
        'over_capacity_owners': over_capacity_owners,
        'checks': checks,
        'pass': all(checks.values()),
        'executable_schedule_ir': executable_schedule_ir,
    }


def build_counted_resource_ir(
    *,
    stream_rows: List[Dict[str, Any]],
    executable_liveness: Mapping[str, Any],
    base_without_streamed_qroam: int,
    leaf_call_count_total: int,
    total_non_clifford: int,
    total_logical_qubits: int,
) -> Dict[str, Any]:
    non_clifford_terms = [
        {
            'term_id': 'base_without_streamed_qroam',
            'category': 'arithmetic_control_and_phase_base',
            'instances': 1,
            'per_instance_non_clifford': int(base_without_streamed_qroam),
            'total_non_clifford': int(base_without_streamed_qroam),
            'source': 'logical_resource_ledger.qroam_clean_tradeoff_sweep.base_non_clifford_without_streamed_qroam',
        }
    ]
    for row in stream_rows:
        non_clifford_terms.append({
            'term_id': f"qroam_stream__{row['table']}__chunk_{row['chunk_index']}",
            'category': 'qroam_chunk_stream',
            'table': row['table'],
            'chunk_index': int(row['chunk_index']),
            'instances': int(leaf_call_count_total),
            'per_instance_non_clifford': int(row['per_chunk_stream_non_clifford']),
            'total_non_clifford': int(leaf_call_count_total) * int(row['per_chunk_stream_non_clifford']),
            'source': 'stream_plan.rows',
        })
    interval_rows = [
        {
            'interval_id': interval['interval_id'],
            'live_wire_ids': list(interval['live_wire_ids']),
            'owner_live_qubits': dict(interval['owner_live_qubits']),
            'total_live_qubits': int(interval['total_live_qubits']),
        }
        for interval in executable_liveness['intervals']
    ]
    recomputed_total_non_clifford = sum(int(term['total_non_clifford']) for term in non_clifford_terms)
    peak_interval = max(interval_rows, key=lambda interval: int(interval['total_live_qubits']))
    qroam_terms = [term for term in non_clifford_terms if term['category'] == 'qroam_chunk_stream']
    checks = {
        'non_clifford_terms_sum_to_candidate': recomputed_total_non_clifford == int(total_non_clifford),
        'qroam_terms_match_stream_rows': len(qroam_terms) == len(stream_rows),
        'each_qroam_term_reuses_leaf_call_count': all(int(term['instances']) == int(leaf_call_count_total) for term in qroam_terms),
        'liveness_intervals_match_executable_liveness_peak': int(peak_interval['total_live_qubits']) == int(executable_liveness['global_peak_live_qubits']) == int(total_logical_qubits),
    }
    return {
        'schema': 'compiler-project-reusable-chunk-counted-resource-ir-v1',
        'derivation': 'single counted IR consumed by integrity checks and the SP1 guest for reusable-chunk headline non-Clifford and live-qubit totals',
        'non_clifford_terms': non_clifford_terms,
        'wire_catalog': dict(executable_liveness['wire_catalog']),
        'liveness_intervals': interval_rows,
        'recomputed_total_non_clifford': recomputed_total_non_clifford,
        'recomputed_peak_live_qubits': int(peak_interval['total_live_qubits']),
        'peak_interval_id': peak_interval['interval_id'],
        'checks': checks,
        'pass': all(checks.values()),
    }


def build_reusable_chunk_resource_engine(
    *,
    executable_leaf: Mapping[str, Any],
    stream_rows: List[Dict[str, Any]],
    owners: List[Dict[str, Any]],
    field_bits: int,
    folded_control_qubits: int,
    control_qubits: int,
    phase_qubits: int,
    base_without_streamed_qroam: int,
    leaf_call_count_total: int,
    total_non_clifford: int,
    total_logical_qubits: int,
) -> Dict[str, Any]:
    executable_liveness = build_reusable_chunk_executable_liveness(
        executable_leaf=executable_leaf,
        stream_rows=stream_rows,
        owners=owners,
        field_bits=int(field_bits),
        folded_control_qubits=int(folded_control_qubits),
        control_qubits=int(control_qubits),
        phase_qubits=int(phase_qubits),
    )
    counted_resource_ir = build_counted_resource_ir(
        stream_rows=stream_rows,
        executable_liveness=executable_liveness,
        base_without_streamed_qroam=int(base_without_streamed_qroam),
        leaf_call_count_total=int(leaf_call_count_total),
        total_non_clifford=int(total_non_clifford),
        total_logical_qubits=int(total_logical_qubits),
    )
    counted_resource_engine = evaluate_counted_resource_ir(counted_resource_ir)
    owner_required_total = sum(int(owner['required_peak_qubits']) for owner in owners)
    owner_capacity_total = sum(int(owner['logical_qubits']) for owner in owners)
    owner_capacity = {
        'rows': owners,
        'required_global_peak_qubits': owner_required_total,
        'capacity_global_peak_qubits': owner_capacity_total,
    }
    resource_contract_engine = evaluate_resource_contract(
        counted_resource_ir=counted_resource_ir,
        counted_resource_engine=counted_resource_engine,
        executable_liveness=executable_liveness,
        owner_capacity=owner_capacity,
    )
    checks = {
        'executable_liveness_pass': executable_liveness['pass'] is True,
        'counted_resource_ir_pass': counted_resource_ir['pass'] is True,
        'counted_resource_engine_pass': counted_resource_engine['pass'] is True,
        'resource_contract_engine_pass': resource_contract_engine['pass'] is True,
        'non_clifford_total_matches_counted_engine': int(counted_resource_engine['non_clifford_total_from_terms']) == int(total_non_clifford),
        'logical_qubit_total_matches_contract_engine': int(resource_contract_engine['peak_live_qubits']) == int(total_logical_qubits),
        'owner_capacity_total_matches_contract_engine': owner_capacity_total == int(resource_contract_engine['peak_live_qubits']),
    }
    return {
        'schema': EXECUTABLE_RESOURCE_ENGINE_SCHEMA,
        'engine_source_module': 'compiler_verification_project/src/executable_resource_engine.py',
        'input_contract': {
            'field_bits': int(field_bits),
            'stream_row_count': len(stream_rows),
            'owner_count': len(owners),
            'leaf_call_count_total': int(leaf_call_count_total),
        },
        'public_totals': {
            'non_clifford': int(total_non_clifford),
            'logical_qubits': int(total_logical_qubits),
        },
        'counted_resource_ir_sha256': counted_resource_engine['counted_resource_ir_sha256'],
        'executable_liveness_sha256': resource_contract_engine['executable_liveness_sha256'],
        'owner_capacity_sha256': resource_contract_engine['owner_capacity_sha256'],
        'resource_contract_engine_sha256': _sha256_payload(resource_contract_engine),
        'executable_liveness': executable_liveness,
        'counted_resource_ir': counted_resource_ir,
        'counted_resource_engine': counted_resource_engine,
        'owner_capacity': owner_capacity,
        'resource_contract_engine': resource_contract_engine,
        'checks': checks,
        'pass': all(checks.values()),
    }


__all__ = [
    'EXECUTABLE_RESOURCE_ENGINE_SCHEMA',
    'build_counted_resource_ir',
    'build_reusable_chunk_executable_liveness',
    'build_reusable_chunk_resource_engine',
    'owner_capacity_row',
    'owned_wire',
    'schedule_event',
]
