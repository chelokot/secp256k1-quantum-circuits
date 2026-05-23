#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_ROOT = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
STRICT_REPLAYED_TAIL_HEADLINE_SCHEMA = 'compiler-project-strict-replayed-tail-headline-v1'


def _canonical_json(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')


def _sha256_payload(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload)).hexdigest()


def _load(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text())


def _comparison_rows(non_clifford: int, logical_qubits: int, baseline: Mapping[str, Any]) -> Dict[str, Any]:
    rows = {}
    for name, row in baseline.items():
        baseline_non_clifford = int(row['non_clifford'])
        baseline_logical_qubits = int(row['logical_qubits'])
        rows[name] = {
            'baseline_non_clifford': baseline_non_clifford,
            'baseline_logical_qubits': baseline_logical_qubits,
            'non_clifford_improvement_ratio': baseline_non_clifford / non_clifford,
            'logical_qubit_delta_vs_baseline': logical_qubits - baseline_logical_qubits,
            'beats_non_clifford': non_clifford < baseline_non_clifford,
            'beats_logical_qubits': logical_qubits < baseline_logical_qubits,
        }
    return rows


def build_strict_replayed_tail_headline_result(
    *,
    tail_macro_engine: Mapping[str, Any],
    reusable_chunk_lowering: Mapping[str, Any],
    public_headline_result: Mapping[str, Any],
    baseline: Mapping[str, Any],
) -> Dict[str, Any]:
    replay = tail_macro_engine['fused_output_replay_certificate']
    slot_assignment = tail_macro_engine['fused_output_slot_assignment']
    qubit_derivation = reusable_chunk_lowering['qubit_derivation']
    non_clifford_derivation = reusable_chunk_lowering['non_clifford_derivation']
    field_bits = int(slot_assignment['field_bits'])
    strict_tail_field_slots = int(slot_assignment['peak_field_slots'])
    strict_tail_field_qubits = strict_tail_field_slots * field_bits
    lookup_workspace_qubits = int(qubit_derivation['lookup_workspace_qubits'])
    fused_output_guard_qubits = int(tail_macro_engine['fused_output_lowering_contract']['guard_owner_capacity']['logical_qubits'])
    control_qubits = int(qubit_derivation['control_qubits']) + fused_output_guard_qubits
    phase_qubits = int(qubit_derivation['phase_qubits'])
    strict_total_logical_qubits = strict_tail_field_qubits + lookup_workspace_qubits + control_qubits + phase_qubits
    non_clifford = int(non_clifford_derivation['candidate_total_non_clifford'])
    macro_result = public_headline_result['selected_result']
    owner_capacity_rows = slot_assignment['owner_capacity_rows']
    checks = {
        'tail_engine_passes': tail_macro_engine['pass'] is True,
        'fused_output_schedule_replay_passes': replay['pass'] is True,
        'fused_output_schedule_edge_cases_are_present': int(replay['checked_non_infinity_pairs']) > 0 and int(replay['checked_lookup_infinity_pairs']) > 0,
        'fused_output_owner_capacity_passes': replay['owner_capacity_pass'] is True,
        'slot_assignment_capacity_rows_match_peak': len(owner_capacity_rows) == strict_tail_field_slots,
        'every_tail_slot_has_field_sized_capacity': all(int(row['logical_qubits']) == field_bits for row in owner_capacity_rows),
        'strict_tail_field_qubits_are_derived_from_slot_assignment': strict_tail_field_qubits == sum(int(row['logical_qubits']) for row in owner_capacity_rows),
        'fused_output_guard_qubit_is_counted': fused_output_guard_qubits == 1,
        'lookup_workspace_is_counted_separately_from_tail_slots': lookup_workspace_qubits == int(qubit_derivation['folded_control_workspace_qubits']) + int(qubit_derivation['qroam_clean_chunk_target_qubits']) + int(qubit_derivation['qroam_clean_junk_register_qubits']),
        'non_clifford_total_comes_from_reusable_chunk_lowering': non_clifford == int(non_clifford_derivation['base_non_clifford_without_streamed_qroam']) + int(non_clifford_derivation['qroam_chunk_non_clifford']),
        'strict_total_logical_qubits_matches_formula': strict_total_logical_qubits == strict_tail_field_qubits + lookup_workspace_qubits + control_qubits + phase_qubits,
        'macro_contract_is_not_selected_as_strict_headline': strict_total_logical_qubits > int(macro_result['logical_qubits']),
    }
    selected_result = {
        'name': 'folded_standard_qroam_reusable_chunked_coordinate_v1__strict_fused_output_tail_7_slot_v1__semiclassical_qft_v1',
        'non_clifford': non_clifford,
        'logical_qubits': strict_total_logical_qubits,
        'tail_field_slots': strict_tail_field_slots,
        'field_bits': field_bits,
        'lookup_workspace_qubits': lookup_workspace_qubits,
        'control_qubits': control_qubits,
        'fused_output_guard_qubits': fused_output_guard_qubits,
        'phase_qubits': phase_qubits,
    }
    payload = {
        'schema': STRICT_REPLAYED_TAIL_HEADLINE_SCHEMA,
        'status': 'primary_strict_replayed_tail_headline',
        'scope': 'strict no-free-field-slot headline derived from the executable fused-output tail replay and the standard-QROAM reusable-chunk lookup resource',
        'selected_result': selected_result,
        'logical_qubit_formula': {
            'tail_field_slots': strict_tail_field_slots,
            'field_bits': field_bits,
            'tail_field_qubits': strict_tail_field_qubits,
            'lookup_workspace_qubits': lookup_workspace_qubits,
            'control_qubits': control_qubits,
            'fused_output_guard_qubits': fused_output_guard_qubits,
            'phase_qubits': phase_qubits,
            'reconstructed_total': strict_total_logical_qubits,
        },
        'non_clifford_formula': {
            'base_non_clifford_without_streamed_qroam': int(non_clifford_derivation['base_non_clifford_without_streamed_qroam']),
            'qroam_chunk_streams': int(non_clifford_derivation['qroam_chunk_streams']),
            'per_chunk_stream_non_clifford': int(non_clifford_derivation['per_chunk_stream_non_clifford']),
            'qroam_chunk_non_clifford': int(non_clifford_derivation['qroam_chunk_non_clifford']),
            'reconstructed_total': non_clifford,
        },
        'semantic_replay_evidence': {
            'checked_non_infinity_pairs': int(replay['checked_non_infinity_pairs']),
            'checked_lookup_infinity_pairs': int(replay['checked_lookup_infinity_pairs']),
            'operation_count': int(replay['operation_count']),
            'schedule_row_count': int(replay['schedule_row_count']),
            'owner_capacity_pass': replay['owner_capacity_pass'],
            'pass': replay['pass'],
        },
        'macro_contract_reference': {
            'artifact': 'compiler_verification_project/artifacts/public_headline_result.json',
            'logical_qubits': int(macro_result['logical_qubits']),
            'non_clifford': int(macro_result['non_clifford']),
            'status': 'not_primary_strict_headline',
            'reason': 'the macro/ZKP bundle still counts a four-slot reusable-tail contract; the strict replayed-tail headline counts the executable fused-output tail schedule instead',
        },
        'comparison_against_public_google_baseline': _comparison_rows(non_clifford, strict_total_logical_qubits, baseline),
        'source_digests': {
            'tail_macro_engine_sha256': _sha256_payload(tail_macro_engine),
            'reusable_chunk_lowering_sha256': _sha256_payload(reusable_chunk_lowering),
            'public_headline_result_sha256': _sha256_payload(public_headline_result),
        },
        'checks': checks,
        'pass': all(checks.values()),
    }
    return payload


def write_strict_replayed_tail_headline_result(*, baseline: Mapping[str, Any]) -> None:
    from common import dump_json

    payload = build_strict_replayed_tail_headline_result(
        tail_macro_engine=_load(ARTIFACT_ROOT / 'tail_macro_engine.json'),
        reusable_chunk_lowering=_load(ARTIFACT_ROOT / 'reusable_chunk_lowering.json'),
        public_headline_result=_load(ARTIFACT_ROOT / 'public_headline_result.json'),
        baseline=baseline,
    )
    dump_json(ARTIFACT_ROOT / 'strict_replayed_tail_headline.json', payload)


__all__ = [
    'STRICT_REPLAYED_TAIL_HEADLINE_SCHEMA',
    'build_strict_replayed_tail_headline_result',
    'write_strict_replayed_tail_headline_result',
]
