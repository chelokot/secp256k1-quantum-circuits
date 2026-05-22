#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Mapping


PUBLIC_ENGINE_MANIFEST_SCHEMA = 'compiler-project-public-engine-manifest-v1'


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def _sha256_payload(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode('ascii')).hexdigest()


def _stream_hash(rows: List[Mapping[str, Any]], columns: List[str]) -> str:
    digest = hashlib.sha256()
    digest.update(('\t'.join(columns) + '\n').encode('ascii'))
    for row in rows:
        digest.update(('\t'.join(_canonical_json(row[column]) for column in columns) + '\n').encode('ascii'))
    return digest.hexdigest()


def _instruction_rows(instructions: List[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            'row_index': row_index,
            'pc': int(instruction['pc']),
            'op': str(instruction['op']),
            'reads': list(instruction.get('reads', [])),
            'writes': list(instruction.get('writes', [])),
        }
        for row_index, instruction in enumerate(instructions)
    ]


def _wire_rows(wire_catalog: Mapping[str, Mapping[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            'row_index': row_index,
            'wire_id': str(wire_id),
            'owner_id': str(wire['owner_id']),
            'qubits': int(wire['qubits']),
            'role': str(wire['role']),
        }
        for row_index, (wire_id, wire) in enumerate(sorted(wire_catalog.items()))
    ]


def _schedule_rows(events: List[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            'row_index': row_index,
            'event_id': str(event['event_id']),
            'event_type': str(event['event_type']),
            'pc_range': [int(value) for value in event['pc_range']],
            'source_instruction_pcs': [int(value) for value in event['source_instruction_pcs']],
            'source_instruction_ops': [str(value) for value in event['source_instruction_ops']],
            'live_wire_ids': list(event['live_wire_ids']),
        }
        for row_index, event in enumerate(events)
    ]


def _owner_rows(owner_capacity: Mapping[str, Any]) -> List[Dict[str, Any]]:
    return [
        {
            'row_index': row_index,
            'owner_id': str(row['owner_id']),
            'logical_qubits': int(row['logical_qubits']),
            'required_peak_qubits': int(row['required_peak_qubits']),
            'capacity_pass': bool(row['capacity_pass']),
        }
        for row_index, row in enumerate(owner_capacity['rows'])
    ]


def _resource_term_rows(counted_resource_ir: Mapping[str, Any]) -> List[Dict[str, Any]]:
    return [
        {
            'row_index': row_index,
            'term_id': str(term['term_id']),
            'category': str(term['category']),
            'instances': int(term['instances']),
            'per_instance_non_clifford': int(term['per_instance_non_clifford']),
            'total_non_clifford': int(term['total_non_clifford']),
            'source': str(term['source']),
        }
        for row_index, term in enumerate(counted_resource_ir['non_clifford_terms'])
    ]


def build_public_engine_manifest(
    *,
    reusable_chunk_lowering: Mapping[str, Any],
    selected_family_name: str,
) -> Dict[str, Any]:
    executable_resource_engine = reusable_chunk_lowering['executable_resource_engine']
    executable_contract = reusable_chunk_lowering['executable_contract']
    executable_liveness = reusable_chunk_lowering['executable_liveness']
    executable_schedule = executable_liveness['executable_schedule_ir']
    counted_resource_ir = reusable_chunk_lowering['counted_resource_ir']
    counted_resource_engine = reusable_chunk_lowering['counted_resource_engine']
    resource_contract_engine = reusable_chunk_lowering['resource_contract_engine']
    owner_capacity = reusable_chunk_lowering['owner_capacity']

    instruction_rows = _instruction_rows(list(executable_contract['instruction_stream']))
    wire_rows = _wire_rows(executable_liveness['wire_catalog'])
    schedule_rows = _schedule_rows(list(executable_schedule['events']))
    owner_rows = _owner_rows(owner_capacity)
    resource_term_rows = _resource_term_rows(counted_resource_ir)

    instruction_columns = ['row_index', 'pc', 'op', 'reads', 'writes']
    wire_columns = ['row_index', 'wire_id', 'owner_id', 'qubits', 'role']
    schedule_columns = ['row_index', 'event_id', 'event_type', 'pc_range', 'source_instruction_pcs', 'source_instruction_ops', 'live_wire_ids']
    owner_columns = ['row_index', 'owner_id', 'logical_qubits', 'required_peak_qubits', 'capacity_pass']
    term_columns = ['row_index', 'term_id', 'category', 'instances', 'per_instance_non_clifford', 'total_non_clifford', 'source']

    public_totals = {
        'non_clifford': int(executable_resource_engine['public_totals']['non_clifford']),
        'logical_qubits': int(executable_resource_engine['public_totals']['logical_qubits']),
    }
    checks = {
        'executable_resource_engine_passes': executable_resource_engine['pass'] is True,
        'counted_resource_engine_passes': counted_resource_engine['pass'] is True,
        'resource_contract_engine_passes': resource_contract_engine['pass'] is True,
        'public_totals_match_counted_resource_engine': (
            public_totals['non_clifford'] == int(counted_resource_engine['non_clifford_total_from_terms'])
            and public_totals['logical_qubits'] == int(counted_resource_engine['peak_live_qubits_from_intervals'])
        ),
        'public_totals_match_resource_contract_engine': (
            public_totals['logical_qubits'] == int(resource_contract_engine['peak_live_qubits'])
        ),
        'engine_digests_match_bound_documents': (
            executable_resource_engine['counted_resource_ir_sha256'] == counted_resource_engine['counted_resource_ir_sha256']
            and executable_resource_engine['executable_liveness_sha256'] == resource_contract_engine['executable_liveness_sha256']
            and executable_resource_engine['owner_capacity_sha256'] == resource_contract_engine['owner_capacity_sha256']
        ),
        'schedule_rows_bind_instruction_stream': all(
            row['source_instruction_ops'] == [
                instruction_rows_by_pc[pc]['op']
                for pc in row['source_instruction_pcs']
            ]
            for instruction_rows_by_pc in [{row['pc']: row for row in instruction_rows}]
            for row in schedule_rows
        ),
        'wire_rows_cover_liveness_catalog': len(wire_rows) == len(executable_liveness['wire_catalog']),
        'owner_rows_cover_capacity_catalog': len(owner_rows) == len(owner_capacity['rows']),
        'resource_terms_sum_to_public_total': sum(row['total_non_clifford'] for row in resource_term_rows) == public_totals['non_clifford'],
    }
    return {
        'schema': PUBLIC_ENGINE_MANIFEST_SCHEMA,
        'scope': 'current public reusable-chunk executable resource engine manifest',
        'selected_family_name': selected_family_name,
        'source_artifact': 'compiler_verification_project/artifacts/reusable_chunk_lowering.json',
        'engine_source_module': executable_resource_engine['engine_source_module'],
        'public_totals': public_totals,
        'source_digests': {
            'executable_resource_engine_sha256': _sha256_payload(executable_resource_engine),
            'counted_resource_ir_sha256': executable_resource_engine['counted_resource_ir_sha256'],
            'executable_liveness_sha256': executable_resource_engine['executable_liveness_sha256'],
            'owner_capacity_sha256': executable_resource_engine['owner_capacity_sha256'],
            'resource_contract_engine_sha256': executable_resource_engine['resource_contract_engine_sha256'],
        },
        'instruction_stream': {
            'encoding': instruction_columns,
            'row_count': len(instruction_rows),
            'sha256': _stream_hash(instruction_rows, instruction_columns),
            'rows': instruction_rows,
        },
        'wire_catalog_stream': {
            'encoding': wire_columns,
            'row_count': len(wire_rows),
            'sha256': _stream_hash(wire_rows, wire_columns),
            'rows': wire_rows,
        },
        'schedule_stream': {
            'encoding': schedule_columns,
            'row_count': len(schedule_rows),
            'sha256': _stream_hash(schedule_rows, schedule_columns),
            'rows': schedule_rows,
        },
        'owner_capacity_stream': {
            'encoding': owner_columns,
            'row_count': len(owner_rows),
            'sha256': _stream_hash(owner_rows, owner_columns),
            'rows': owner_rows,
        },
        'resource_term_stream': {
            'encoding': term_columns,
            'row_count': len(resource_term_rows),
            'expanded_non_clifford_instances': sum(row['instances'] for row in resource_term_rows),
            'sha256': _stream_hash(resource_term_rows, term_columns),
            'rows': resource_term_rows,
        },
        'fast_no_zkp_contract': {
            'build_target': 'public-engine-manifest',
            'verify_group': 'public_engine_manifest_checks',
            'prover_required': False,
        },
        'checks': checks,
        'pass': all(checks.values()),
    }


__all__ = [
    'PUBLIC_ENGINE_MANIFEST_SCHEMA',
    'build_public_engine_manifest',
]
