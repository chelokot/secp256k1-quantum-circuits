#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_ROOT = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
PRIMARY_STRICT_RESULT_SCHEMA = 'compiler-project-primary-strict-result-v1'


def _canonical_json(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')


def _sha256_payload(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload)).hexdigest()


def _load(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text())


def build_primary_strict_result(
    *,
    strict_replayed_tail_headline: Mapping[str, Any],
    public_headline_result: Mapping[str, Any],
    engine_completion_audit: Mapping[str, Any],
    public_candidate_materialized_circuit_manifest: Mapping[str, Any],
    hybrid_bridge_search: Mapping[str, Any],
) -> Dict[str, Any]:
    selected = strict_replayed_tail_headline['selected_result']
    legacy_selected = public_headline_result['selected_result']
    engine_totals = engine_completion_audit['public_totals']
    flat_netlist = engine_completion_audit['materialized_flat_netlist']
    strict_overlay = public_candidate_materialized_circuit_manifest['strict_replayed_tail_capacity_overlay']
    hybrid_current = next(row for row in hybrid_bridge_search['candidate_rows'] if row['name'] == 'current_strict_projective_seven_slot')
    strict_non_clifford = int(selected['non_clifford'])
    strict_logical_qubits = int(selected['logical_qubits'])
    checks = {
        'strict_headline_passes': strict_replayed_tail_headline['pass'] is True,
        'strict_headline_is_current_primary_resource_result': strict_replayed_tail_headline['status'] == 'primary_strict_replayed_tail_headline',
        'strict_headline_totals_match_hybrid_search_current_row': strict_non_clifford == int(hybrid_current['non_clifford']) and strict_logical_qubits == int(hybrid_current['logical_qubits']),
        'strict_headline_fits_current_gate_goal': strict_non_clifford < int(hybrid_bridge_search['target']['non_clifford_exclusive']),
        'strict_headline_does_not_fit_current_qubit_goal': strict_logical_qubits >= int(hybrid_bridge_search['target']['logical_qubits_exclusive']),
        'legacy_macro_wrapper_is_demoted': strict_replayed_tail_headline['macro_contract_reference']['status'] == 'not_primary_strict_headline',
        'legacy_macro_wrapper_has_lower_qubit_count_than_strict_result': int(legacy_selected['logical_qubits']) < strict_logical_qubits,
        'legacy_macro_wrapper_is_not_current_strict_flat_netlist': int(engine_totals['logical_qubits']) == int(flat_netlist['peak_live_qubits']) == int(legacy_selected['logical_qubits']),
        'strict_capacity_overlay_binds_selected_result': (
            strict_overlay['pass'] is True
            and int(strict_overlay['flat_operation_stream']['non_clifford_count']) == strict_non_clifford
            and int(strict_overlay['strict_capacity_terms']['reconstructed_logical_qubits']) == strict_logical_qubits
            and strict_overlay['claim_boundary']['full_operation_index_liveness_rewrite_binds_strict_qubits'] is False
        ),
        'strict_result_is_not_marked_clifford_complete': engine_completion_audit['clifford_complete_goal_achieved'] is False,
    }
    payload = {
        'schema': PRIMARY_STRICT_RESULT_SCHEMA,
        'role': 'single current public resource headline',
        'status': 'primary_strict_result_with_explicit_unclosed_flattening_and_zkp_boundaries',
        'selected_result': dict(selected),
        'source_artifact': 'compiler_verification_project/artifacts/strict_replayed_tail_headline.json',
        'resource_claim_level': {
            'strict_resource_headline': 'current_primary',
            'clifford_complete_flat_netlist': 'not_yet_achieved',
            'zkp_binds_this_strict_result': 'not_yet_achieved',
        },
        'closed_evidence': {
            'strict_replayed_tail_headline': {
                'path': 'compiler_verification_project/artifacts/strict_replayed_tail_headline.json',
                'sha256': _sha256_payload(strict_replayed_tail_headline),
                'status': strict_replayed_tail_headline['status'],
                'pass': strict_replayed_tail_headline['pass'],
            },
            'hybrid_bridge_search_current_row': {
                'path': 'compiler_verification_project/artifacts/hybrid_bridge_search.json',
                'sha256': _sha256_payload(hybrid_bridge_search),
                'row': dict(hybrid_current),
            },
        },
        'legacy_wrapper_reference': {
            'path': 'compiler_verification_project/artifacts/public_headline_result.json',
            'sha256': _sha256_payload(public_headline_result),
            'selected_result': dict(legacy_selected),
            'status': 'legacy_macro_zkp_wrapper_not_primary_resource_headline',
            'reason': 'the wrapper and materialized flat-netlist audit still bind the old macro contract totals, not the strict seven-slot replayed-tail totals',
        },
        'flat_netlist_status': {
            'current_materialized_flat_netlist_path': 'compiler_verification_project/artifacts/public_candidate_materialized_circuit_manifest.json',
            'current_materialized_flat_netlist_binds_selected_strict_result': False,
            'current_materialized_flat_netlist_binds_legacy_wrapper': True,
            'strict_capacity_overlay_binds_selected_result': True,
            'strict_capacity_overlay_is_full_liveness_rewrite': False,
            'operation_count': int(flat_netlist['operation_count']),
            'non_clifford_count': int(flat_netlist['non_clifford_count']),
            'peak_live_qubits': int(flat_netlist['peak_live_qubits']),
            'strict_capacity_peak_qubits': int(strict_overlay['strict_capacity_terms']['reconstructed_logical_qubits']),
            'operation_stream_sha256': flat_netlist['operation_stream_sha256'],
            'segment_merkle_root_sha256': flat_netlist['segment_merkle_root_sha256'],
        },
        'remaining_completion_requirements': [
            'materialize the strict seven-slot replayed-tail family as the flat primitive stream counted by the same engine',
            'make the ZKP guest/input bind the primary strict result artifact instead of the legacy macro wrapper',
            'keep public presentation generated from this artifact or from strict_replayed_tail_headline.json, never from hand-copied headline numbers',
        ],
        'source_digests': {
            'strict_replayed_tail_headline_sha256': _sha256_payload(strict_replayed_tail_headline),
            'public_headline_result_sha256': _sha256_payload(public_headline_result),
            'engine_completion_audit_sha256': _sha256_payload(engine_completion_audit),
            'public_candidate_materialized_circuit_manifest_sha256': _sha256_payload(public_candidate_materialized_circuit_manifest),
            'hybrid_bridge_search_sha256': _sha256_payload(hybrid_bridge_search),
        },
        'checks': checks,
        'pass': all(checks.values()),
    }
    return payload


def write_primary_strict_result() -> None:
    from common import dump_json

    payload = build_primary_strict_result(
        strict_replayed_tail_headline=_load(ARTIFACT_ROOT / 'strict_replayed_tail_headline.json'),
        public_headline_result=_load(ARTIFACT_ROOT / 'public_headline_result.json'),
        engine_completion_audit=_load(ARTIFACT_ROOT / 'engine_completion_audit.json'),
        public_candidate_materialized_circuit_manifest=_load(ARTIFACT_ROOT / 'public_candidate_materialized_circuit_manifest.json'),
        hybrid_bridge_search=_load(ARTIFACT_ROOT / 'hybrid_bridge_search.json'),
    )
    dump_json(ARTIFACT_ROOT / 'primary_strict_result.json', payload)


__all__ = [
    'PRIMARY_STRICT_RESULT_SCHEMA',
    'build_primary_strict_result',
    'write_primary_strict_result',
]
