#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Mapping

from resource_ir_engine import evaluate_counted_resource_ir


HEADLINE_RESOURCE_MANIFEST_SCHEMA = 'compiler-project-headline-resource-manifest-v1'
TERM_STREAM_ENCODING = [
    'row_index',
    'term_id',
    'category',
    'instance_index',
    'per_instance_non_clifford',
    'source',
]
LIVENESS_STREAM_ENCODING = [
    'row_index',
    'interval_id',
    'live_wire_ids',
    'owner_live_qubits',
    'total_live_qubits',
]


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def _sha256_payload(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode('ascii')).hexdigest()


def _term_rows(counted_resource_ir: Mapping[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for term in counted_resource_ir['non_clifford_terms']:
        for instance_index in range(int(term['instances'])):
            rows.append({
                'row_index': len(rows),
                'term_id': str(term['term_id']),
                'category': str(term['category']),
                'instance_index': instance_index,
                'per_instance_non_clifford': int(term['per_instance_non_clifford']),
                'source': str(term['source']),
            })
    return rows


def _liveness_rows(counted_resource_ir: Mapping[str, Any]) -> List[Dict[str, Any]]:
    return [
        {
            'row_index': index,
            'interval_id': str(interval['interval_id']),
            'live_wire_ids': list(interval['live_wire_ids']),
            'owner_live_qubits': {
                owner_id: int(qubits)
                for owner_id, qubits in sorted(interval['owner_live_qubits'].items())
            },
            'total_live_qubits': int(interval['total_live_qubits']),
        }
        for index, interval in enumerate(counted_resource_ir['liveness_intervals'])
    ]


def _stream_hash(rows: List[Mapping[str, Any]], columns: List[str]) -> str:
    digest = hashlib.sha256()
    digest.update(('\t'.join(columns) + '\n').encode('ascii'))
    for row in rows:
        digest.update(('\t'.join(_canonical_json(row[column]) for column in columns) + '\n').encode('ascii'))
    return digest.hexdigest()


def build_headline_resource_manifest(
    *,
    reusable_chunk_lowering: Mapping[str, Any],
    selected_family_name: str,
) -> Dict[str, Any]:
    counted_resource_ir = reusable_chunk_lowering['counted_resource_ir']
    engine = evaluate_counted_resource_ir(counted_resource_ir)
    terms = _term_rows(counted_resource_ir)
    liveness = _liveness_rows(counted_resource_ir)
    non_clifford_from_rows = sum(int(row['per_instance_non_clifford']) for row in terms)
    peak_liveness_from_rows = max(int(row['total_live_qubits']) for row in liveness)
    qroam_term_rows = [row for row in terms if row['category'] == 'qroam_chunk_stream']
    checks = {
        'counted_resource_ir_engine_passes': engine['pass'] is True,
        'term_rows_sum_to_public_total': (
            non_clifford_from_rows
            == int(counted_resource_ir['recomputed_total_non_clifford'])
            == int(reusable_chunk_lowering['non_clifford_derivation']['candidate_total_non_clifford'])
        ),
        'liveness_rows_peak_to_public_qubits': (
            peak_liveness_from_rows
            == int(counted_resource_ir['recomputed_peak_live_qubits'])
            == int(reusable_chunk_lowering['qubit_derivation']['candidate_total_logical_qubits'])
        ),
        'qroam_rows_expand_stream_plan_instances': (
            len(qroam_term_rows)
            == int(reusable_chunk_lowering['stream_plan']['whole_oracle_chunk_streams'])
        ),
        'qroam_rows_sum_to_qroam_derivation': (
            sum(int(row['per_instance_non_clifford']) for row in qroam_term_rows)
            == int(reusable_chunk_lowering['non_clifford_derivation']['qroam_chunk_non_clifford'])
        ),
        'source_resource_contract_passes': reusable_chunk_lowering['resource_contract_engine']['pass'] is True,
    }
    return {
        'schema': HEADLINE_RESOURCE_MANIFEST_SCHEMA,
        'scope': 'current public reusable-chunk headline resource stream manifest',
        'selected_family_name': selected_family_name,
        'source_artifact': 'compiler_verification_project/artifacts/reusable_chunk_lowering.json',
        'source_counted_resource_ir_sha256': _sha256_payload(counted_resource_ir),
        'term_stream_encoding': TERM_STREAM_ENCODING,
        'term_stream_sha256': _stream_hash(terms, TERM_STREAM_ENCODING),
        'term_row_count': len(terms),
        'term_rows': terms,
        'liveness_stream_encoding': LIVENESS_STREAM_ENCODING,
        'liveness_stream_sha256': _stream_hash(liveness, LIVENESS_STREAM_ENCODING),
        'liveness_row_count': len(liveness),
        'liveness_rows': liveness,
        'engine': engine,
        'public_totals': {
            'non_clifford': non_clifford_from_rows,
            'logical_qubits': peak_liveness_from_rows,
        },
        'checks': checks,
        'pass': all(checks.values()),
        'boundary': [
            'This is the materialized counted-resource stream for the current public headline, not a Clifford-complete per-gate netlist.',
            'It prevents stale materialized-manifest evidence from silently referring to the superseded three-slot frontier family.',
        ],
    }


__all__ = [
    'HEADLINE_RESOURCE_MANIFEST_SCHEMA',
    'build_headline_resource_manifest',
]
