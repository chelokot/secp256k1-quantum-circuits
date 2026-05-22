#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Mapping


RESOURCE_IR_ENGINE_SCHEMA = 'compiler-project-counted-resource-ir-engine-v1'
RESOURCE_CONTRACT_ENGINE_SCHEMA = 'compiler-project-resource-contract-engine-v1'


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def _sha256_payload(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode('ascii')).hexdigest()


def evaluate_counted_resource_ir(counted_resource_ir: Mapping[str, Any]) -> Dict[str, Any]:
    wire_catalog = counted_resource_ir['wire_catalog']
    intervals = counted_resource_ir['liveness_intervals']
    terms = counted_resource_ir['non_clifford_terms']
    term_total = 0
    malformed_terms = []
    for term in terms:
        instances = int(term['instances'])
        per_instance = int(term['per_instance_non_clifford'])
        total = int(term['total_non_clifford'])
        if instances * per_instance != total:
            malformed_terms.append(str(term['term_id']))
        term_total += total

    unknown_live_wires = []
    duplicate_live_wires = []
    interval_sum_mismatches = []
    owner_peak: Dict[str, int] = {}
    peak_live_qubits = 0
    peak_interval_id = None
    for interval in intervals:
        live_wire_ids = list(interval['live_wire_ids'])
        duplicated = sorted({wire_id for wire_id in live_wire_ids if live_wire_ids.count(wire_id) > 1})
        duplicate_live_wires.extend(f"{interval['interval_id']}:{wire_id}" for wire_id in duplicated)
        owner_totals: Dict[str, int] = {}
        for wire_id in live_wire_ids:
            wire = wire_catalog.get(wire_id)
            if wire is None:
                unknown_live_wires.append(f"{interval['interval_id']}:{wire_id}")
                continue
            owner_id = str(wire['owner_id'])
            owner_totals[owner_id] = owner_totals.get(owner_id, 0) + int(wire['qubits'])
        expected_total = sum(owner_totals.values())
        observed_owner_totals = {key: int(value) for key, value in interval['owner_live_qubits'].items()}
        observed_total = int(interval['total_live_qubits'])
        if owner_totals != observed_owner_totals or expected_total != observed_total:
            interval_sum_mismatches.append(str(interval['interval_id']))
        for owner_id, qubits in owner_totals.items():
            owner_peak[owner_id] = max(owner_peak.get(owner_id, 0), qubits)
        if expected_total > peak_live_qubits:
            peak_live_qubits = expected_total
            peak_interval_id = str(interval['interval_id'])

    checks = {
        'term_products_match_totals': not malformed_terms,
        'term_sum_matches_declared_total': term_total == int(counted_resource_ir['recomputed_total_non_clifford']),
        'all_live_wires_exist_in_catalog': not unknown_live_wires,
        'intervals_do_not_double_count_wires': not duplicate_live_wires,
        'interval_owner_sums_match_wire_catalog': not interval_sum_mismatches,
        'peak_matches_declared_peak': peak_live_qubits == int(counted_resource_ir['recomputed_peak_live_qubits']),
        'peak_interval_matches_declared_peak_interval': peak_interval_id == counted_resource_ir['peak_interval_id'],
    }
    return {
        'schema': RESOURCE_IR_ENGINE_SCHEMA,
        'input_schema': counted_resource_ir['schema'],
        'counted_resource_ir_sha256': _sha256_payload(counted_resource_ir),
        'term_count': len(terms),
        'wire_count': len(wire_catalog),
        'interval_count': len(intervals),
        'non_clifford_total_from_terms': term_total,
        'peak_live_qubits_from_intervals': peak_live_qubits,
        'peak_interval_id_from_intervals': peak_interval_id,
        'owner_peak_live_qubits_from_intervals': dict(sorted(owner_peak.items())),
        'malformed_term_ids': malformed_terms,
        'unknown_live_wire_refs': unknown_live_wires,
        'duplicate_live_wire_refs': duplicate_live_wires,
        'interval_sum_mismatches': interval_sum_mismatches,
        'checks': checks,
        'pass': all(checks.values()),
    }


def _counted_interval_rows(counted_resource_ir: Mapping[str, Any]) -> List[Dict[str, Any]]:
    return [
        {
            'interval_id': str(interval['interval_id']),
            'live_wire_ids': list(interval['live_wire_ids']),
            'owner_live_qubits': {key: int(value) for key, value in interval['owner_live_qubits'].items()},
            'total_live_qubits': int(interval['total_live_qubits']),
        }
        for interval in counted_resource_ir['liveness_intervals']
    ]


def _executable_interval_rows(executable_liveness: Mapping[str, Any]) -> List[Dict[str, Any]]:
    return [
        {
            'interval_id': str(interval['interval_id']),
            'live_wire_ids': list(interval['live_wire_ids']),
            'owner_live_qubits': {key: int(value) for key, value in interval['owner_live_qubits'].items()},
            'total_live_qubits': int(interval['total_live_qubits']),
        }
        for interval in executable_liveness['intervals']
    ]


def _owner_rows(owner_capacity: Mapping[str, Any]) -> List[Dict[str, Any]]:
    return [
        {
            'owner_id': str(row['owner_id']),
            'logical_qubits': int(row['logical_qubits']),
            'required_peak_qubits': int(row['required_peak_qubits']),
            'capacity_pass': bool(row['capacity_pass']),
        }
        for row in owner_capacity['rows']
    ]


def evaluate_resource_contract(
    *,
    counted_resource_ir: Mapping[str, Any],
    counted_resource_engine: Mapping[str, Any],
    executable_liveness: Mapping[str, Any],
    owner_capacity: Mapping[str, Any],
) -> Dict[str, Any]:
    counted_engine_expected = evaluate_counted_resource_ir(counted_resource_ir)
    executable_wire_catalog = executable_liveness['wire_catalog']
    executable_intervals = _executable_interval_rows(executable_liveness)
    counted_intervals = _counted_interval_rows(counted_resource_ir)
    owner_capacity_rows = _owner_rows(owner_capacity)
    owner_capacity_by_id = {row['owner_id']: row['logical_qubits'] for row in owner_capacity_rows}
    owner_required_by_id = {row['owner_id']: row['required_peak_qubits'] for row in owner_capacity_rows}
    engine_owner_peaks = {
        key: int(value)
        for key, value in counted_engine_expected['owner_peak_live_qubits_from_intervals'].items()
    }
    executable_owner_peaks = {
        key: int(value)
        for key, value in executable_liveness['owner_peak_live_qubits'].items()
    }
    executable_owner_capacity = {
        key: int(value)
        for key, value in executable_liveness['owner_capacity_qubits'].items()
    }
    over_capacity = sorted(
        owner_id
        for owner_id, peak in engine_owner_peaks.items()
        if owner_capacity_by_id.get(owner_id, -1) < peak
    )
    missing_capacity = sorted(
        owner_id for owner_id in engine_owner_peaks
        if owner_id not in owner_capacity_by_id
    )
    stale_required_rows = sorted(
        owner_id
        for owner_id, peak in engine_owner_peaks.items()
        if owner_required_by_id.get(owner_id) != peak
    )
    checks = {
        'counted_engine_matches_recomputed_engine': counted_resource_engine == counted_engine_expected,
        'counted_wire_catalog_matches_executable_liveness': counted_resource_ir['wire_catalog'] == executable_wire_catalog,
        'counted_intervals_match_executable_liveness': counted_intervals == executable_intervals,
        'counted_peak_matches_executable_peak': (
            int(counted_engine_expected['peak_live_qubits_from_intervals'])
            == int(executable_liveness['global_peak_live_qubits'])
        ),
        'owner_peaks_match_executable_liveness': engine_owner_peaks == executable_owner_peaks,
        'owner_capacity_matches_executable_liveness': owner_capacity_by_id == executable_owner_capacity,
        'owner_required_rows_match_engine_peaks': not stale_required_rows,
        'owner_capacity_covers_engine_peaks': not over_capacity and not missing_capacity,
        'owner_capacity_totals_match_engine_peak': (
            int(owner_capacity['required_global_peak_qubits'])
            == int(owner_capacity['capacity_global_peak_qubits'])
            == int(counted_engine_expected['peak_live_qubits_from_intervals'])
        ),
    }
    return {
        'schema': RESOURCE_CONTRACT_ENGINE_SCHEMA,
        'counted_resource_ir_sha256': counted_engine_expected['counted_resource_ir_sha256'],
        'executable_liveness_sha256': _sha256_payload(executable_liveness),
        'owner_capacity_sha256': _sha256_payload(owner_capacity),
        'wire_count': counted_engine_expected['wire_count'],
        'interval_count': counted_engine_expected['interval_count'],
        'peak_live_qubits': counted_engine_expected['peak_live_qubits_from_intervals'],
        'peak_interval_id': counted_engine_expected['peak_interval_id_from_intervals'],
        'owner_peak_live_qubits': dict(sorted(engine_owner_peaks.items())),
        'owner_capacity_qubits': dict(sorted(owner_capacity_by_id.items())),
        'over_capacity_owners': over_capacity,
        'missing_capacity_owners': missing_capacity,
        'stale_required_owner_rows': stale_required_rows,
        'checks': checks,
        'pass': all(checks.values()),
    }


__all__ = [
    'RESOURCE_CONTRACT_ENGINE_SCHEMA',
    'RESOURCE_IR_ENGINE_SCHEMA',
    'evaluate_counted_resource_ir',
    'evaluate_resource_contract',
]
