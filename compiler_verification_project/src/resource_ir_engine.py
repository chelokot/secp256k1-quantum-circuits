#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Mapping


RESOURCE_IR_ENGINE_SCHEMA = 'compiler-project-counted-resource-ir-engine-v1'


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


__all__ = ['RESOURCE_IR_ENGINE_SCHEMA', 'evaluate_counted_resource_ir']
