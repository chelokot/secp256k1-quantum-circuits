#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Mapping

from scheduled_modular_primitive_netlist import iter_scheduled_modular_primitive_rows


MODULAR_PRIMITIVE_WIRE_AUDIT_SCHEMA = 'compiler-project-modular-primitive-wire-audit-v1'


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def _sha256_payload(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode('ascii')).hexdigest()


def _empty_gate_counts() -> Dict[str, int]:
    return {'ccx': 0, 'cx': 0, 'x': 0, 'measurement': 0}


def _field_wire_name(wire_id: str) -> str | None:
    if not wire_id.startswith('field:') or '.bit[' not in wire_id:
        return None
    return wire_id[len('field:'):wire_id.index('.bit[')]


def _scratch_prefix(wire_id: str) -> str | None:
    if not wire_id.startswith('arithmetic_scratch:') or '.bit[' not in wire_id:
        return None
    return wire_id[:wire_id.index('.bit[')]


def build_modular_primitive_wire_audit(
    *,
    modular_execution_trace: Mapping[str, Any],
    modular_arithmetic_certificate: Mapping[str, Any],
    arithmetic_lowerings: Mapping[str, Any],
    reusable_chunk_lowering: Mapping[str, Any],
    scheduled_modular_primitive_netlist: Mapping[str, Any],
) -> Dict[str, Any]:
    live_during_by_suboperation = {
        int(suboperation['global_suboperation_index']): {
            str(name): int(slot)
            for name, slot in trace_row['live_during'].items()
        }
        for trace_row in modular_execution_trace['trace_rows']
        for suboperation in trace_row['suboperations']
    }
    suboperation_owner_by_index = {
        int(suboperation['global_suboperation_index']): str(suboperation['owner_id'])
        for trace_row in modular_execution_trace['trace_rows']
        for suboperation in trace_row['suboperations']
    }
    operation_count = 0
    gate_counts = _empty_gate_counts()
    field_wire_observation_count = 0
    field_wire_missing_liveness_count = 0
    lookup_workspace_wire_observation_count = 0
    non_lookup_unclassified_wire_count = 0
    arithmetic_scratch_wire_observation_count = 0
    arithmetic_scratch_unique_ids: set[str] = set()
    arithmetic_scratch_prefixes: Dict[str, int] = {}
    observed_suboperation_owners: Dict[str, int] = {}
    sample_missing_liveness = []
    sample_synthetic_scratch = []
    sample_unclassified = []

    for row in iter_scheduled_modular_primitive_rows(
        modular_execution_trace=modular_execution_trace,
        modular_arithmetic_certificate=modular_arithmetic_certificate,
        arithmetic_lowerings=arithmetic_lowerings,
        reusable_chunk_lowering=reusable_chunk_lowering,
    ):
        operation_count += 1
        gate = str(row['gate'])
        gate_counts[gate] += 1
        suboperation_index = int(row['suboperation_index'])
        if suboperation_index >= 0:
            owner = suboperation_owner_by_index[suboperation_index]
            observed_suboperation_owners[owner] = observed_suboperation_owners.get(owner, 0) + 1
        live_during = live_during_by_suboperation.get(suboperation_index, {})
        for wire_id in [str(wire) for wire in row['operand_wires']]:
            field_name = _field_wire_name(wire_id)
            if field_name is not None:
                field_wire_observation_count += 1
                if field_name not in live_during:
                    field_wire_missing_liveness_count += 1
                    if len(sample_missing_liveness) < 16:
                        sample_missing_liveness.append({
                            'operation_index': int(row['operation_index']),
                            'suboperation_index': suboperation_index,
                            'wire_id': wire_id,
                            'field_name': field_name,
                            'live_during': dict(live_during),
                        })
                continue
            if wire_id.startswith('lookup_workspace:'):
                lookup_workspace_wire_observation_count += 1
                continue
            scratch_prefix = _scratch_prefix(wire_id)
            if scratch_prefix is not None:
                arithmetic_scratch_wire_observation_count += 1
                arithmetic_scratch_unique_ids.add(wire_id)
                arithmetic_scratch_prefixes[scratch_prefix] = arithmetic_scratch_prefixes.get(scratch_prefix, 0) + 1
                if len(sample_synthetic_scratch) < 16:
                    sample_synthetic_scratch.append({
                        'operation_index': int(row['operation_index']),
                        'suboperation_index': suboperation_index,
                        'gate': gate,
                        'target': str(row['target']),
                        'block': str(row['block']),
                        'wire_id': wire_id,
                    })
                continue
            non_lookup_unclassified_wire_count += 1
            if len(sample_unclassified) < 16:
                sample_unclassified.append({
                    'operation_index': int(row['operation_index']),
                    'suboperation_index': suboperation_index,
                    'wire_id': wire_id,
                })

    top_scratch_prefixes = [
        {'scratch_prefix': prefix, 'observation_count': int(count)}
        for prefix, count in sorted(
            arithmetic_scratch_prefixes.items(),
            key=lambda item: (-item[1], item[0]),
        )[:16]
    ]
    checks = {
        'scheduled_modular_primitive_netlist_passes': scheduled_modular_primitive_netlist['pass'] is True,
        'scanned_operation_count_matches_scheduled_netlist': operation_count == int(scheduled_modular_primitive_netlist['operation_count']),
        'scanned_gate_counts_match_scheduled_netlist': gate_counts == {
            key: int(scheduled_modular_primitive_netlist['primitive_counts_total'][key])
            for key in gate_counts
        },
        'field_operand_wires_are_live_in_trace': field_wire_missing_liveness_count == 0,
        'qroam_operand_wires_are_explicit_lookup_workspace_wires': lookup_workspace_wire_observation_count > 0,
        'no_unclassified_non_lookup_operand_wires': non_lookup_unclassified_wire_count == 0,
        'no_synthetic_arithmetic_scratch_wires_without_owner_capacity': arithmetic_scratch_wire_observation_count == 0,
    }
    return {
        'schema': MODULAR_PRIMITIVE_WIRE_AUDIT_SCHEMA,
        'definition': 'Wire-level audit of the scheduled modular primitive iterator. It separates field wires backed by trace liveness from lookup-workspace wires and synthetic arithmetic scratch wires that still need a counted owner/reuse proof before the modular primitive stream can be called fully physical.',
        'source_digests': {
            'modular_execution_trace_sha256': _sha256_payload(modular_execution_trace),
            'modular_arithmetic_certificate_sha256': _sha256_payload(modular_arithmetic_certificate),
            'arithmetic_lowerings_sha256': _sha256_payload(arithmetic_lowerings),
            'reusable_chunk_lowering_sha256': _sha256_payload(reusable_chunk_lowering),
            'scheduled_modular_primitive_netlist_sha256': _sha256_payload(scheduled_modular_primitive_netlist),
        },
        'operation_count': operation_count,
        'gate_counts': gate_counts,
        'field_wire_observation_count': field_wire_observation_count,
        'field_wire_missing_liveness_count': field_wire_missing_liveness_count,
        'lookup_workspace_wire_observation_count': lookup_workspace_wire_observation_count,
        'arithmetic_scratch_wire_observation_count': arithmetic_scratch_wire_observation_count,
        'arithmetic_scratch_unique_wire_count': len(arithmetic_scratch_unique_ids),
        'non_lookup_unclassified_wire_count': non_lookup_unclassified_wire_count,
        'observed_suboperation_owner_counts': {
            key: int(value)
            for key, value in sorted(observed_suboperation_owners.items())
        },
        'top_synthetic_scratch_prefixes': top_scratch_prefixes,
        'sample_missing_liveness': sample_missing_liveness,
        'sample_synthetic_scratch': sample_synthetic_scratch,
        'sample_unclassified': sample_unclassified,
        'checks': checks,
        'pass': all(checks.values()),
        'completion_blockers': [
            {
                'name': 'field_operand_liveness_binding',
                'active': field_wire_missing_liveness_count > 0,
                'required_to_close': 'Bind every field:* operand used by the modular primitive iterator to the scheduled trace liveness map, or replace virtual lookup/internal-product field operands with a wire-level streaming circuit whose wires have counted owners.',
            },
            {
                'name': 'synthetic_arithmetic_scratch_owner_capacity',
                'active': arithmetic_scratch_wire_observation_count > 0,
                'required_to_close': 'Replace arithmetic_scratch:* operand wires with a primitive lowering that assigns every scratch/control/target wire to counted field slots or to an explicit counted scratch owner with a liveness/reuse proof.',
            },
            {
                'name': 'modular_multiplier_physical_wire_semantics',
                'active': arithmetic_scratch_wire_observation_count > 0,
                'required_to_close': 'Give the modular multiplication primitive a reversible wire-level circuit instead of treating the schoolbook partial-product grid as independent synthetic scratch targets.',
            },
        ],
    }


__all__ = [
    'MODULAR_PRIMITIVE_WIRE_AUDIT_SCHEMA',
    'build_modular_primitive_wire_audit',
]
