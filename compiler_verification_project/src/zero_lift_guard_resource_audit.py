#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Mapping


ZERO_LIFT_GUARD_RESOURCE_AUDIT_SCHEMA = 'compiler-project-zero-lift-guard-resource-audit-v1'
ZERO_LIFT_GUARD_RESOURCE_GAP_STATUS = 'zero_lift_guard_capacity_gap_not_promoted_to_public_contract'


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def _sha256_payload(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode('ascii')).hexdigest()


def build_zero_lift_guard_resource_audit(
    *,
    tail_macro_engine: Mapping[str, Any],
) -> Dict[str, Any]:
    field_bits = int(tail_macro_engine['field_bits'])
    guard_capacity = tail_macro_engine['fused_output_lowering_contract']['guard_owner_capacity']
    current_guard_logical_qubits = int(guard_capacity['logical_qubits'])
    current_guard_non_clifford = int(guard_capacity['non_clifford'])
    clean_ladder_compute_ccx = field_bits - 1
    clean_ladder_uncompute_ccx = field_bits - 1
    clean_ladder_total_ccx = clean_ladder_compute_ccx + clean_ladder_uncompute_ccx
    clean_ladder_prefix_ancilla_bits = field_bits - 2
    clean_ladder_predicate_output_bits = 1
    clean_ladder_peak_predicate_bits = clean_ladder_prefix_ancilla_bits + clean_ladder_predicate_output_bits
    missing_capacity_bits = max(0, clean_ladder_peak_predicate_bits - current_guard_logical_qubits)
    checks = {
        'tail_macro_engine_passes': tail_macro_engine['pass'] is True,
        'current_guard_non_clifford_matches_clean_ladder_ccx': current_guard_non_clifford == clean_ladder_total_ccx,
        'current_guard_capacity_is_only_predicate_output_bit': current_guard_logical_qubits == clean_ladder_predicate_output_bits,
        'clean_ladder_requires_prefix_ancilla_capacity': clean_ladder_prefix_ancilla_bits > 0,
        'current_guard_capacity_does_not_cover_clean_ladder': current_guard_logical_qubits < clean_ladder_peak_predicate_bits,
        'capacity_gap_is_explicit': missing_capacity_bits == clean_ladder_prefix_ancilla_bits,
    }
    return {
        'schema': ZERO_LIFT_GUARD_RESOURCE_AUDIT_SCHEMA,
        'definition': 'Resource audit for the L == 0 zero-lift guard used by the fused-output Y3-over-C in-place permutation. It separates the counted 510-CCX predicate compute/uncompute cost from the missing predicate-ladder workspace capacity.',
        'source_digests': {
            'tail_macro_engine_sha256': _sha256_payload(tail_macro_engine),
        },
        'field_bits': field_bits,
        'current_guard_owner_capacity': {
            'owner_id': str(guard_capacity['owner_id']),
            'logical_qubits': current_guard_logical_qubits,
            'non_clifford': current_guard_non_clifford,
            'construction': str(guard_capacity['construction']),
        },
        'standard_clean_ladder_requirement': {
            'control_register': 'L',
            'negative_control_bits': field_bits,
            'compute_ccx': clean_ladder_compute_ccx,
            'uncompute_ccx': clean_ladder_uncompute_ccx,
            'total_ccx': clean_ladder_total_ccx,
            'prefix_ancilla_bits': clean_ladder_prefix_ancilla_bits,
            'predicate_output_bits': clean_ladder_predicate_output_bits,
            'peak_predicate_workspace_bits': clean_ladder_peak_predicate_bits,
            'clifford_x_for_negative_controls_counted_as_non_clifford': False,
        },
        'capacity_gap': {
            'current_logical_qubits': current_guard_logical_qubits,
            'minimum_clean_ladder_logical_qubits': clean_ladder_peak_predicate_bits,
            'missing_logical_qubits_under_clean_ladder': missing_capacity_bits,
            'corrected_public_qubit_delta_if_no_aliasing_proof': missing_capacity_bits,
        },
        'promotion_status': {
            'status': ZERO_LIFT_GUARD_RESOURCE_GAP_STATUS,
            'required_to_promote': [
                'Either provide an executable no-extra-ancilla or already-counted-alias construction for the L == 0 predicate, or count the clean-ladder prefix ancilla capacity.',
                'Expose every zero-lift guard predicate wire in the scheduled primitive stream liveness owner model.',
                'Recompute public peak logical qubits from the promoted primitive stream before claiming a Clifford-complete headline.',
            ],
        },
        'checks': checks,
        'pass': all(checks.values()),
    }


__all__ = [
    'ZERO_LIFT_GUARD_RESOURCE_AUDIT_SCHEMA',
    'ZERO_LIFT_GUARD_RESOURCE_GAP_STATUS',
    'build_zero_lift_guard_resource_audit',
]
