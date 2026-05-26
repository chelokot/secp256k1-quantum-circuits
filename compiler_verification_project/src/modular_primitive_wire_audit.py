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


def _is_lookup_virtual_field(field_name: str) -> bool:
    return field_name in {'lookup_x', 'lookup_y', 'lookup_x_plus_y'}


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
    suboperation_overwrite_by_index = {
        int(suboperation['global_suboperation_index']): {
            'overwritten_source': None if suboperation.get('overwritten_source') is None else str(suboperation['overwritten_source']),
            'target': str(suboperation['target']),
            'target_slot': None if suboperation.get('target_slot') is None else int(suboperation['target_slot']),
            'owner_id': str(suboperation['owner_id']),
        }
        for trace_row in modular_execution_trace['trace_rows']
        for suboperation in trace_row['suboperations']
    }
    operation_count = 0
    gate_counts = _empty_gate_counts()
    field_wire_observation_count = 0
    trace_live_field_wire_observation_count = 0
    field_wire_missing_liveness_count = 0
    overwritten_source_field_observation_count = 0
    lookup_virtual_field_observation_count = 0
    unresolved_virtual_field_observation_count = 0
    lookup_workspace_wire_observation_count = 0
    non_lookup_unclassified_wire_count = 0
    arithmetic_scratch_wire_observation_count = 0
    arithmetic_scratch_unique_ids: set[str] = set()
    arithmetic_scratch_prefixes: Dict[str, int] = {}
    observed_suboperation_owners: Dict[str, int] = {}
    missing_field_names: Dict[str, int] = {}
    overwritten_source_field_names: Dict[str, int] = {}
    lookup_virtual_field_names: Dict[str, int] = {}
    unresolved_virtual_field_names: Dict[str, int] = {}
    unresolved_virtual_field_roles: Dict[str, int] = {}
    unresolved_virtual_field_names_by_role: Dict[str, Dict[str, int]] = {}
    sample_missing_liveness = []
    sample_lookup_virtual = []
    sample_unresolved_virtual_field = []
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
                if field_name in live_during:
                    trace_live_field_wire_observation_count += 1
                    continue
                field_wire_missing_liveness_count += 1
                missing_field_names[field_name] = missing_field_names.get(field_name, 0) + 1
                sample = {
                    'operation_index': int(row['operation_index']),
                    'suboperation_index': suboperation_index,
                    'wire_id': wire_id,
                    'field_name': field_name,
                    'target': str(row['target']),
                    'kind': str(row['kind']),
                    'modular_opcode': None if row['modular_opcode'] is None else str(row['modular_opcode']),
                    'block': str(row['block']),
                    'live_during': dict(live_during),
                }
                if len(sample_missing_liveness) < 16:
                    sample_missing_liveness.append(dict(sample))
                if _is_lookup_virtual_field(field_name):
                    lookup_virtual_field_observation_count += 1
                    lookup_virtual_field_names[field_name] = lookup_virtual_field_names.get(field_name, 0) + 1
                    if len(sample_lookup_virtual) < 16:
                        sample_lookup_virtual.append(dict(sample))
                    continue
                overwrite = suboperation_overwrite_by_index.get(suboperation_index, {})
                if (
                    field_name == overwrite.get('overwritten_source')
                    and overwrite.get('target_slot') is not None
                    and overwrite.get('owner_id') == str(row['owner_id'])
                ):
                    overwritten_source_field_observation_count += 1
                    overwritten_source_field_names[field_name] = overwritten_source_field_names.get(field_name, 0) + 1
                    continue
                unresolved_virtual_field_observation_count += 1
                unresolved_virtual_field_names[field_name] = unresolved_virtual_field_names.get(field_name, 0) + 1
                source_names = {str(source) for source in row['sources']}
                if field_name == str(row['target']):
                    unresolved_role = 'target_field_wire_without_trace_liveness'
                elif field_name in source_names:
                    unresolved_role = 'source_field_wire_without_trace_liveness'
                else:
                    unresolved_role = 'implicit_field_wire_without_trace_liveness'
                unresolved_virtual_field_roles[unresolved_role] = unresolved_virtual_field_roles.get(unresolved_role, 0) + 1
                names_for_role = unresolved_virtual_field_names_by_role.setdefault(unresolved_role, {})
                names_for_role[field_name] = names_for_role.get(field_name, 0) + 1
                if len(sample_unresolved_virtual_field) < 16:
                    sample['unresolved_role'] = unresolved_role
                    sample_unresolved_virtual_field.append(dict(sample))
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
        'lookup_virtual_field_operands_are_classified': (
            lookup_virtual_field_observation_count > 0
            and set(lookup_virtual_field_names).issubset({'lookup_x', 'lookup_y', 'lookup_x_plus_y'})
            and int(reusable_chunk_lowering['stream_plan']['chunk_streams_per_leaf']) > 0
        ),
        'no_unresolved_virtual_field_operands': unresolved_virtual_field_observation_count == 0,
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
        'trace_live_field_wire_observation_count': trace_live_field_wire_observation_count,
        'field_wire_missing_liveness_count': field_wire_missing_liveness_count,
        'overwritten_source_field_observation_count': overwritten_source_field_observation_count,
        'lookup_virtual_field_observation_count': lookup_virtual_field_observation_count,
        'unresolved_virtual_field_observation_count': unresolved_virtual_field_observation_count,
        'lookup_workspace_wire_observation_count': lookup_workspace_wire_observation_count,
        'arithmetic_scratch_wire_observation_count': arithmetic_scratch_wire_observation_count,
        'arithmetic_scratch_unique_wire_count': len(arithmetic_scratch_unique_ids),
        'non_lookup_unclassified_wire_count': non_lookup_unclassified_wire_count,
        'observed_suboperation_owner_counts': {
            key: int(value)
            for key, value in sorted(observed_suboperation_owners.items())
        },
        'missing_field_names': {
            key: int(value)
            for key, value in sorted(missing_field_names.items(), key=lambda item: (-item[1], item[0]))
        },
        'overwritten_source_field_names': {
            key: int(value)
            for key, value in sorted(overwritten_source_field_names.items(), key=lambda item: (-item[1], item[0]))
        },
        'lookup_virtual_field_names': {
            key: int(value)
            for key, value in sorted(lookup_virtual_field_names.items(), key=lambda item: (-item[1], item[0]))
        },
        'unresolved_virtual_field_names': {
            key: int(value)
            for key, value in sorted(unresolved_virtual_field_names.items(), key=lambda item: (-item[1], item[0]))
        },
        'unresolved_virtual_field_roles': {
            key: int(value)
            for key, value in sorted(unresolved_virtual_field_roles.items(), key=lambda item: (-item[1], item[0]))
        },
        'unresolved_virtual_field_names_by_role': {
            role: {
                key: int(value)
                for key, value in sorted(names.items(), key=lambda item: (-item[1], item[0]))
            }
            for role, names in sorted(unresolved_virtual_field_names_by_role.items())
        },
        'top_synthetic_scratch_prefixes': top_scratch_prefixes,
        'sample_missing_liveness': sample_missing_liveness,
        'sample_lookup_virtual': sample_lookup_virtual,
        'sample_unresolved_virtual_field': sample_unresolved_virtual_field,
        'sample_synthetic_scratch': sample_synthetic_scratch,
        'sample_unclassified': sample_unclassified,
        'checks': checks,
        'pass': all(checks.values()),
        'completion_blockers': [
            {
                'name': 'field_operand_liveness_binding',
                'active': unresolved_virtual_field_observation_count > 0,
                'required_to_close': 'Bind every non-lookup field:* operand used by the modular primitive iterator to the scheduled trace liveness map, or replace virtual internal-product field operands with a wire-level streaming circuit whose wires have counted owners.',
            },
            {
                'name': 'lookup_virtual_field_stream_binding',
                'active': False,
                'required_to_close': 'Lookup virtual operands are classified separately from unresolved field slots and are backed by the public QROAM stream plan; the remaining task is to preserve that binding through the final modular physical stream.',
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
