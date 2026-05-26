#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Mapping


MODULAR_MULTIPLIER_LIFECYCLE_SCHEMA = 'compiler-project-modular-multiplier-lifecycle-v1'


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def _sha256_payload(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode('ascii')).hexdigest()


def build_modular_multiplier_lifecycle(
    *,
    scheduled_modular_primitive_netlist: Mapping[str, Any],
    modular_primitive_wire_audit: Mapping[str, Any],
    field_bits: int,
) -> Dict[str, Any]:
    scratch_observations = int(modular_primitive_wire_audit['arithmetic_scratch_wire_observation_count'])
    scratch_unique = int(modular_primitive_wire_audit['arithmetic_scratch_unique_wire_count'])
    scratch_single_use = int(modular_primitive_wire_audit['arithmetic_scratch_single_use_wire_count'])
    scratch_cleanup = int(modular_primitive_wire_audit['arithmetic_scratch_cleanup_observation_count'])
    scratch_abandoned = int(modular_primitive_wire_audit['arithmetic_scratch_abandoned_garbage_count'])
    partial_product_prefixes = [
        row
        for row in modular_primitive_wire_audit['top_synthetic_scratch_prefixes']
        if str(row['scratch_prefix']).endswith('partial_product_grid')
    ]
    partial_product_observations = sum(int(row['observation_count']) for row in partial_product_prefixes)
    non_partial_product_observations = scratch_observations - partial_product_observations
    streamed_candidate = {
        'model': 'serial_temporary_and_consume_cleanup',
        'status': 'candidate_not_promoted_to_public_resource_contract',
        'temporary_and_compute_events': scratch_observations,
        'required_consume_events': scratch_observations,
        'required_cleanup_events': scratch_observations,
        'peak_temporary_and_wires_if_serialized': 1 if scratch_observations else 0,
        'additional_measurements_for_measured_cleanup': scratch_observations,
        'non_clifford_delta_unproven_until_consume_cleanup_lowering_exists': None,
        'notes': [
            'This is a generated target lifecycle for closing the current gap, not a claimed public lowering.',
            'Promotion requires replacing each producer-only scratch target with a compute-consume-cleanup sequence that updates a counted accumulator wire and returns the temporary AND wire to zero.',
        ],
    }
    checks = {
        'wire_audit_binds_current_scheduled_netlist': (
            modular_primitive_wire_audit['source_digests']['scheduled_modular_primitive_netlist_sha256']
            == _sha256_payload(scheduled_modular_primitive_netlist)
        ),
        'current_scratch_is_single_use_ccx_target_only': (
            modular_primitive_wire_audit['checks']['synthetic_scratch_wires_are_single_use_ccx_targets'] is True
            and scratch_observations == scratch_unique == scratch_single_use
        ),
        'current_scratch_has_no_cleanup_or_counted_capacity': (
            modular_primitive_wire_audit['checks']['synthetic_scratch_wires_have_cleanup_or_counted_capacity'] is False
            and scratch_cleanup == 0
            and scratch_abandoned == scratch_observations
        ),
        'streamed_candidate_covers_every_current_scratch_target': (
            streamed_candidate['temporary_and_compute_events']
            == streamed_candidate['required_consume_events']
            == streamed_candidate['required_cleanup_events']
            == scratch_observations
        ),
        'streamed_candidate_peak_is_serial_constant': streamed_candidate['peak_temporary_and_wires_if_serialized'] <= 1,
        'not_promoted_until_consume_cleanup_lowering_exists': streamed_candidate['status'] != 'promoted_public_resource_contract',
    }
    return {
        'schema': MODULAR_MULTIPLIER_LIFECYCLE_SCHEMA,
        'definition': 'Generated lifecycle audit for modular-multiplier temporary-AND scratch targets. It distinguishes the current abandoned scratch placeholders from the compute-consume-cleanup lifecycle required by a physical primitive lowering.',
        'source_digests': {
            'scheduled_modular_primitive_netlist_sha256': _sha256_payload(scheduled_modular_primitive_netlist),
            'modular_primitive_wire_audit_sha256': _sha256_payload(modular_primitive_wire_audit),
        },
        'field_bits': int(field_bits),
        'current_stream': {
            'operation_count': int(scheduled_modular_primitive_netlist['operation_count']),
            'non_clifford_count': int(scheduled_modular_primitive_netlist['non_clifford_count']),
            'scratch_observation_count': scratch_observations,
            'scratch_unique_wire_count': scratch_unique,
            'scratch_single_use_wire_count': scratch_single_use,
            'scratch_cleanup_observation_count': scratch_cleanup,
            'scratch_abandoned_garbage_count': scratch_abandoned,
            'partial_product_scratch_observation_count': partial_product_observations,
            'non_partial_product_scratch_observation_count': non_partial_product_observations,
            'physical_lifecycle_status': 'invalid_abandoned_temporary_and_targets',
        },
        'streamed_lifecycle_candidate': streamed_candidate,
        'checks': checks,
        'pass': all(checks.values()),
        'promotion_blockers': [
            {
                'name': 'consume_cleanup_lowering_missing',
                'active': True,
                'required_to_close': 'Generate primitive rows that consume each temporary AND into a counted accumulator update and then cleanup or measure-uncompute the temporary wire before reuse.',
            },
            {
                'name': 'candidate_cost_not_public',
                'active': True,
                'required_to_close': 'Bind the consume and cleanup rows into scheduled_modular_primitive_netlist, recompute non-Clifford/measurement totals, and only then update public resource claims.',
            },
        ],
    }


__all__ = [
    'MODULAR_MULTIPLIER_LIFECYCLE_SCHEMA',
    'build_modular_multiplier_lifecycle',
]
