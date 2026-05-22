#!/usr/bin/env python3

from __future__ import annotations

import gzip
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ROOT_SRC = PROJECT_ROOT / 'src'
if str(ROOT_SRC) not in sys.path:
    sys.path.insert(0, str(ROOT_SRC))

from arithmetic_lowering import arithmetic_lowering_library, materialize_arithmetic_primitive_operations
from lookup_lowering import lookup_lowering_library, materialize_lookup_primitive_operations
from phase_shell_lowering import materialize_phase_operations, phase_shell_lowering_library


STREAM_COLUMNS = ['stream_index', 'family', 'scope', 'invocation', 'source', 'gate', 'operand_0', 'operand_1', 'operand_2']
DEFAULT_SEGMENT_SIZE = 1_000_000
MATERIALIZED_CIRCUIT_MANIFEST_SCHEMA = 'compiler-project-materialized-circuit-manifest-v1'
PUBLIC_CANDIDATE_MATERIALIZED_CIRCUIT_MANIFEST_SCHEMA = 'compiler-project-public-candidate-materialized-circuit-manifest-v1'
PUBLIC_CANDIDATE_STREAM_COLUMNS = [
    'row_index',
    'scope',
    'source',
    'gate',
    'instance_count',
    'total_count',
    'non_clifford_count',
]
PUBLIC_CANDIDATE_LIVENESS_COLUMNS = [
    'row_index',
    'scope',
    'interval_id',
    'live_wire_ids',
    'owner_live_qubits',
    'total_live_qubits',
]


def _empty_gate_totals() -> Dict[str, int]:
    return {
        'ccx': 0,
        'cx': 0,
        'x': 0,
        'measurement': 0,
        'hadamard': 0,
        'single_qubit_rotation': 0,
        'controlled_rotation': 0,
    }


def _merkle_parent(left_hex: str, right_hex: str) -> str:
    digest = hashlib.sha256()
    digest.update(bytes.fromhex(left_hex))
    digest.update(bytes.fromhex(right_hex))
    return digest.hexdigest()


def _merkle_root(leaf_hashes: List[str]) -> str:
    if not leaf_hashes:
        return hashlib.sha256(b'').hexdigest()
    level = list(leaf_hashes)
    while len(level) > 1:
        next_level: List[str] = []
        for index in range(0, len(level), 2):
            left = level[index]
            right = level[index + 1] if index + 1 < len(level) else left
            next_level.append(_merkle_parent(left, right))
        level = next_level
    return level[0]


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def _sha256_payload(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode('ascii')).hexdigest()


def _public_candidate_stream_hash(rows: List[Mapping[str, Any]]) -> str:
    digest = hashlib.sha256()
    digest.update(('\t'.join(PUBLIC_CANDIDATE_STREAM_COLUMNS) + '\n').encode('ascii'))
    for row in rows:
        digest.update(('\t'.join(_canonical_json(row[column]) for column in PUBLIC_CANDIDATE_STREAM_COLUMNS) + '\n').encode('ascii'))
    return digest.hexdigest()


def _public_candidate_liveness_hash(rows: List[Mapping[str, Any]]) -> str:
    digest = hashlib.sha256()
    digest.update(('\t'.join(PUBLIC_CANDIDATE_LIVENESS_COLUMNS) + '\n').encode('ascii'))
    for row in rows:
        digest.update(('\t'.join(_canonical_json(row[column]) for column in PUBLIC_CANDIDATE_LIVENESS_COLUMNS) + '\n').encode('ascii'))
    return digest.hexdigest()


def _project_defaults() -> Dict[str, Any]:
    from project import FIELD_BITS, FOLDED_MAG_DOMAIN, FULL_PHASE_REGISTER_BITS, central_executable_leaf, compiler_family_frontier, leaf_opcode_histogram, raw32_schedule

    return {
        'field_bits': FIELD_BITS,
        'qroam_domain_size': FOLDED_MAG_DOMAIN,
        'phase_bits': FULL_PHASE_REGISTER_BITS,
        'frontier': compiler_family_frontier(),
        'leaf': central_executable_leaf(),
        'schedule': raw32_schedule(),
        'leaf_opcode_histogram': leaf_opcode_histogram(),
    }


def _family_lookup(frontier: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {row['name']: row for row in frontier['families']}


def available_family_names(frontier: Optional[Mapping[str, Any]] = None) -> List[str]:
    resolved_frontier = frontier if frontier is not None else _project_defaults()['frontier']
    return [row['name'] for row in resolved_frontier['families']]


def resolve_selected_family_names(
    selected: Optional[Iterable[str]] = None,
    include_all: bool = False,
    frontier: Optional[Mapping[str, Any]] = None,
) -> List[str]:
    resolved_frontier = frontier if frontier is not None else _project_defaults()['frontier']
    family_lookup = _family_lookup(resolved_frontier)
    if include_all:
        return list(family_lookup)
    requested = list(selected or [])
    if not requested:
        requested = ['best-gate', 'best-qubit']
    resolved: List[str] = []
    for item in requested:
        if item == 'best-gate':
            family_name = str(resolved_frontier['best_gate_family']['name'])
        elif item == 'best-qubit':
            family_name = str(resolved_frontier['best_qubit_family']['name'])
        else:
            family_name = item
        if family_name not in family_lookup:
            raise KeyError(f'unknown family name: {item}')
        if family_name not in resolved:
            resolved.append(family_name)
    return resolved


def _iter_arithmetic_operations(
    family_name: str,
    kernel_lookup: Mapping[str, Dict[str, Any]],
    schedule: Mapping[str, Any],
    leaf: Mapping[str, Any],
) -> Iterator[Dict[str, Any]]:
    stream_index = 0
    for call in schedule['leaf_calls']:
        call_label = f"{call['phase_register']}:{call['window_index_within_register']}"
        for instruction in leaf['instructions']:
            opcode = str(instruction['op'])
            if opcode not in kernel_lookup:
                continue
            kernel = kernel_lookup[opcode]
            for stage in kernel['stages']:
                for block in stage['blocks']:
                    for operation in materialize_arithmetic_primitive_operations(block):
                        operands = [int(value) for value in operation[1:]]
                        yield {
                            'stream_index': stream_index,
                            'family': family_name,
                            'scope': 'leaf_arithmetic',
                            'invocation': call_label,
                            'source': f"pc:{instruction['pc']}:{opcode}:{stage['name']}:{block['name']}",
                            'gate': str(operation[0]),
                            'operand_0': operands[0] if len(operands) > 0 else '',
                            'operand_1': operands[1] if len(operands) > 1 else '',
                            'operand_2': operands[2] if len(operands) > 2 else '',
                        }
                        stream_index += 1


def _encoded_stream_row(row: Mapping[str, Any]) -> str:
    return '\t'.join(str(row[column]) for column in STREAM_COLUMNS) + '\n'


def _iter_lookup_operations(
    family_name: str,
    lookup_family: Mapping[str, Any],
    schedule: Mapping[str, Any],
) -> Iterator[Dict[str, Any]]:
    stream_index = 0
    for invocation, call_label in [('direct_seed', 'seed'), *[('leaf_lookup', f"{call['phase_register']}:{call['window_index_within_register']}") for call in schedule['leaf_calls']]]:
        for stage in lookup_family['stages']:
            for block in stage['blocks']:
                for operation in materialize_lookup_primitive_operations(block['primitive_operation_generator']):
                    operands = [int(value) for value in operation[1:]]
                    yield {
                        'stream_index': stream_index,
                        'family': family_name,
                        'scope': invocation,
                        'invocation': call_label,
                        'source': f"{stage['name']}:{block['name']}",
                        'gate': str(operation[0]),
                        'operand_0': operands[0] if len(operands) > 0 else '',
                        'operand_1': operands[1] if len(operands) > 1 else '',
                        'operand_2': operands[2] if len(operands) > 2 else '',
                    }
                    stream_index += 1


def _iter_phase_shell_operations(family_name: str, phase_shell: Mapping[str, Any]) -> Iterator[Dict[str, Any]]:
    stream_index = 0
    for stage in phase_shell['stages']:
        for block in stage['blocks']:
            for operation in materialize_phase_operations(block['phase_operation_generator']):
                operands = [int(value) for value in operation[1:]]
                yield {
                    'stream_index': stream_index,
                    'family': family_name,
                    'scope': 'phase_shell',
                    'invocation': phase_shell['name'],
                    'source': f"{stage['name']}:{block['name']}",
                    'gate': str(operation[0]),
                    'operand_0': operands[0] if len(operands) > 0 else '',
                    'operand_1': operands[1] if len(operands) > 1 else '',
                    'operand_2': operands[2] if len(operands) > 2 else '',
                }
                stream_index += 1


def iter_family_operation_stream(
    family_name: str,
    frontier: Optional[Mapping[str, Any]] = None,
    schedule: Optional[Mapping[str, Any]] = None,
    leaf: Optional[Mapping[str, Any]] = None,
    arithmetic_lowerings: Optional[Mapping[str, Any]] = None,
    lookup_lowerings: Optional[Mapping[str, Any]] = None,
    phase_shell_lowerings: Optional[Mapping[str, Any]] = None,
    field_bits: Optional[int] = None,
    qroam_domain_size: Optional[int] = None,
    phase_bits: Optional[int] = None,
    leaf_histogram: Optional[Mapping[str, int]] = None,
) -> Iterator[Dict[str, Any]]:
    defaults: Optional[Dict[str, Any]] = None
    if (
        frontier is None
        or schedule is None
        or leaf is None
        or arithmetic_lowerings is None
        or lookup_lowerings is None
        or phase_shell_lowerings is None
        or field_bits is None
        or qroam_domain_size is None
        or phase_bits is None
        or leaf_histogram is None
    ):
        defaults = _project_defaults()
    resolved_frontier = frontier if frontier is not None else defaults['frontier']
    family = _family_lookup(resolved_frontier)[family_name]
    resolved_schedule = schedule if schedule is not None else defaults['schedule']
    resolved_leaf = leaf if leaf is not None else defaults['leaf']
    resolved_field_bits = int(field_bits if field_bits is not None else defaults['field_bits'])
    resolved_qroam_domain_size = int(qroam_domain_size if qroam_domain_size is not None else defaults['qroam_domain_size'])
    resolved_phase_bits = int(phase_bits if phase_bits is not None else defaults['phase_bits'])
    resolved_leaf_histogram = leaf_histogram if leaf_histogram is not None else defaults['leaf_opcode_histogram']
    resolved_arithmetic_lowerings = (
        arithmetic_lowerings
        if arithmetic_lowerings is not None
        else arithmetic_lowering_library(
            field_bits=resolved_field_bits,
            leaf_opcode_histogram=resolved_leaf_histogram,
            qroam_domain_size=resolved_qroam_domain_size,
        )
    )
    resolved_lookup_lowerings = lookup_lowerings if lookup_lowerings is not None else lookup_lowering_library()
    resolved_phase_shell_lowerings = (
        phase_shell_lowerings
        if phase_shell_lowerings is not None
        else phase_shell_lowering_library(resolved_phase_bits)
    )
    kernel_lookup = {row['opcode']: row for row in resolved_arithmetic_lowerings['kernels']}
    lookup_family = next(row for row in resolved_lookup_lowerings['families'] if row['name'] == family['lookup_family'])
    phase_shell = next(row for row in resolved_phase_shell_lowerings['families'] if row['name'] == family['phase_shell'])

    global_index = 0
    for stream in (
        _iter_lookup_operations(family_name, lookup_family, resolved_schedule),
        _iter_arithmetic_operations(family_name, kernel_lookup, resolved_schedule, resolved_leaf),
        _iter_phase_shell_operations(family_name, phase_shell),
    ):
        for row in stream:
            row['stream_index'] = global_index
            yield row
            global_index += 1


def build_materialized_family_manifest(
    family_name: str,
    frontier: Optional[Mapping[str, Any]] = None,
    schedule: Optional[Mapping[str, Any]] = None,
    leaf: Optional[Mapping[str, Any]] = None,
    arithmetic_lowerings: Optional[Mapping[str, Any]] = None,
    lookup_lowerings: Optional[Mapping[str, Any]] = None,
    phase_shell_lowerings: Optional[Mapping[str, Any]] = None,
    field_bits: Optional[int] = None,
    phase_bits: Optional[int] = None,
    leaf_histogram: Optional[Mapping[str, int]] = None,
    segment_size: int = DEFAULT_SEGMENT_SIZE,
) -> Dict[str, Any]:
    defaults: Optional[Dict[str, Any]] = None
    if frontier is None:
        defaults = _project_defaults()
    resolved_frontier = frontier if frontier is not None else defaults['frontier']
    family = _family_lookup(resolved_frontier)[family_name]
    gate_totals = _empty_gate_totals()
    operation_count = 0
    operation_stream_hash = hashlib.sha256()
    operation_stream_hash.update(('\t'.join(STREAM_COLUMNS) + '\n').encode('utf-8'))
    segment_hash = hashlib.sha256()
    segment_count = 0
    segment_start = 0
    segment_gate_totals = _empty_gate_totals()
    segments: List[Dict[str, Any]] = []
    preview_head: List[Dict[str, Any]] = []
    preview_tail: List[Dict[str, Any]] = []
    if segment_size <= 0:
        raise ValueError('segment_size must be positive')
    for row in iter_family_operation_stream(
        family_name,
        frontier=resolved_frontier,
        schedule=schedule,
        leaf=leaf,
        arithmetic_lowerings=arithmetic_lowerings,
        lookup_lowerings=lookup_lowerings,
        phase_shell_lowerings=phase_shell_lowerings,
        field_bits=field_bits,
        phase_bits=phase_bits,
        leaf_histogram=leaf_histogram,
    ):
        gate = str(row['gate'])
        gate_totals[gate] += 1
        operation_count += 1
        encoded_row = _encoded_stream_row(row).encode('utf-8')
        operation_stream_hash.update(encoded_row)
        segment_hash.update(encoded_row)
        segment_count += 1
        segment_gate_totals[gate] += 1
        if len(preview_head) < 8:
            preview_head.append(dict(row))
        preview_tail.append(dict(row))
        if len(preview_tail) > 8:
            preview_tail.pop(0)
        if segment_count == segment_size:
            segments.append({
                'segment_index': len(segments),
                'operation_start': segment_start,
                'operation_end_exclusive': operation_count,
                'operation_count': segment_count,
                'sha256': segment_hash.hexdigest(),
                'gate_totals': segment_gate_totals,
            })
            segment_hash = hashlib.sha256()
            segment_count = 0
            segment_start = operation_count
            segment_gate_totals = _empty_gate_totals()
    if segment_count:
        segments.append({
            'segment_index': len(segments),
            'operation_start': segment_start,
            'operation_end_exclusive': operation_count,
            'operation_count': segment_count,
            'sha256': segment_hash.hexdigest(),
            'gate_totals': segment_gate_totals,
        })
    segment_hashes = [segment['sha256'] for segment in segments]
    return {
        'schema': MATERIALIZED_CIRCUIT_MANIFEST_SCHEMA,
        'family': family_name,
        'summary': family['summary'],
        'lookup_family': family['lookup_family'],
        'phase_shell': family['phase_shell'],
        'arithmetic_kernel_family': family['arithmetic_kernel_family'],
        'stream_encoding': STREAM_COLUMNS,
        'operation_stream_sha256': operation_stream_hash.hexdigest(),
        'operation_count': operation_count,
        'segment_size': segment_size,
        'segment_count': len(segments),
        'segment_merkle_root_sha256': _merkle_root(segment_hashes),
        'segments': segments,
        'gate_totals': gate_totals,
        'expected_totals': {
            'full_oracle_non_clifford': int(family['full_oracle_non_clifford']),
            'phase_shell_hadamards': int(family['phase_shell_hadamards']),
            'phase_shell_rotations': int(family['phase_shell_rotations']),
            'phase_shell_measurements': int(family['phase_shell_measurements']),
            'total_measurements': int(family['total_measurements']),
        },
        'reconstruction_checks': {
            'non_clifford_matches_frontier': gate_totals['ccx'] == int(family['full_oracle_non_clifford']),
            'phase_hadamards_match_frontier': gate_totals['hadamard'] == int(family['phase_shell_hadamards']),
            'phase_rotations_match_frontier': gate_totals['single_qubit_rotation'] + gate_totals['controlled_rotation'] == int(family['phase_shell_rotations']),
            'measurements_match_frontier': gate_totals['measurement'] == int(family['total_measurements']),
        },
        'preview_head': preview_head,
        'preview_tail': preview_tail,
    }


def _selected_phase_shell(phase_shell_lowerings: Mapping[str, Any], selected_name: str) -> Mapping[str, Any]:
    return next(row for row in phase_shell_lowerings['families'] if row['name'] == selected_name)


def _phase_run_length_rows(phase_shell: Mapping[str, Any], row_index: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for stage in phase_shell['stages']:
        for block in stage['blocks']:
            for gate, count in sorted(block['count_profile_total'].items()):
                if gate == 'rotation_depth' or int(count) == 0:
                    continue
                rows.append({
                    'row_index': row_index + len(rows),
                    'scope': 'phase_shell',
                    'source': f"{phase_shell['name']}:{stage['name']}:{block['name']}",
                    'gate': gate,
                    'instance_count': int(count),
                    'total_count': int(count),
                    'non_clifford_count': 0,
                })
    return rows


def _qroam_run_length_rows(
    *,
    reusable_chunk_lowering: Mapping[str, Any],
    qroam_primitive_certificate: Mapping[str, Any],
    row_index: int,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    qroam_terms = [
        term
        for term in reusable_chunk_lowering['counted_resource_ir']['non_clifford_terms']
        if term['category'] == 'qroam_chunk_stream'
    ]
    for term in qroam_terms:
        for instance_index in range(int(term['instances'])):
            for segment in qroam_primitive_certificate['operation_stream']['segments']:
                rows.append({
                    'row_index': row_index + len(rows),
                    'scope': 'qroam_chunk_stream',
                    'source': f"{term['term_id']}:{instance_index}:{segment['phase']}:{segment['start_address']}-{segment['end_address_exclusive']}",
                    'gate': 'ccx',
                    'instance_count': int(segment['operation_count']),
                    'total_count': int(segment['operation_count']),
                    'non_clifford_count': int(segment['ccx']),
                    'term_id': str(term['term_id']),
                    'term_instance_index': instance_index,
                    'table': str(term['table']),
                    'chunk_index': int(term['chunk_index']),
                    'qroam_phase': str(segment['phase']),
                    'qroam_segment_sha256': str(segment['sha256']),
                })
    return rows


def _public_base_run_length_rows(
    *,
    reusable_chunk_lowering: Mapping[str, Any],
    zkp_attestation_input: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    family_payload = zkp_attestation_input['family_document']['payload']
    direct_seed_non_clifford = int(family_payload['direct_seed_non_clifford'])
    arithmetic_leaf_non_clifford = int(family_payload['arithmetic_leaf_non_clifford'])
    leaf_call_count = int(reusable_chunk_lowering['stream_plan']['leaf_call_count_total'])
    rows = [
        {
            'row_index': 0,
            'scope': 'direct_seed_base',
            'source': 'zkp_family_document.direct_seed_non_clifford',
            'gate': 'ccx',
            'instance_count': direct_seed_non_clifford,
            'total_count': direct_seed_non_clifford,
            'non_clifford_count': direct_seed_non_clifford,
        }
    ]
    for leaf_call_index in range(leaf_call_count):
        rows.append({
            'row_index': len(rows),
            'scope': 'arithmetic_leaf_base',
            'source': f"zkp_family_document.arithmetic_leaf_non_clifford:leaf_call_{leaf_call_index}",
            'gate': 'ccx',
            'instance_count': arithmetic_leaf_non_clifford,
            'total_count': arithmetic_leaf_non_clifford,
            'non_clifford_count': arithmetic_leaf_non_clifford,
            'leaf_call_index': leaf_call_index,
        })
    return rows


def _liveness_binding_rows(
    *,
    operation_rows: List[Mapping[str, Any]],
    reusable_chunk_lowering: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    intervals = {
        str(interval['interval_id']): interval
        for interval in reusable_chunk_lowering['executable_liveness']['intervals']
    }
    qroam_interval_by_chunk = {
        (
            str(event['stream_table']),
            int(event['stream_chunk_index']),
        ): str(event['event_id'])
        for event in reusable_chunk_lowering['executable_liveness']['executable_schedule_ir']['events']
        if event['event_type'] == 'qroam_chunk_load_consume_uncompute'
    }
    peak_interval_id = str(reusable_chunk_lowering['executable_liveness']['global_peak_interval_id'])
    rows: List[Dict[str, Any]] = []
    for operation in operation_rows:
        if operation['scope'] == 'qroam_chunk_stream':
            interval_id = qroam_interval_by_chunk[(str(operation['table']), int(operation['chunk_index']))]
        else:
            interval_id = peak_interval_id
        interval = intervals[interval_id]
        rows.append({
            'row_index': int(operation['row_index']),
            'scope': str(operation['scope']),
            'interval_id': interval_id,
            'live_wire_ids': [str(wire_id) for wire_id in interval['live_wire_ids']],
            'owner_live_qubits': {
                owner_id: int(qubits)
                for owner_id, qubits in sorted(interval['owner_live_qubits'].items())
            },
            'total_live_qubits': int(interval['total_live_qubits']),
        })
    return rows


def build_public_candidate_materialized_circuit_manifest(
    *,
    reusable_chunk_lowering: Mapping[str, Any],
    arithmetic_operation_ir: Mapping[str, Any],
    qroam_primitive_certificate: Mapping[str, Any],
    phase_shell_lowerings: Mapping[str, Any],
    zkp_attestation_input: Mapping[str, Any],
    selected_family_name: str,
) -> Dict[str, Any]:
    counted_resource_ir = reusable_chunk_lowering['counted_resource_ir']
    public_totals = reusable_chunk_lowering['executable_resource_engine']['public_totals']
    compiler_parameters = zkp_attestation_input['compiler_parameters_document']['payload']
    selected_phase_shell_name = str(compiler_parameters['phase_shell']['selected_public_shell'])
    selected_phase_shell = _selected_phase_shell(phase_shell_lowerings, selected_phase_shell_name)
    base_non_clifford = int(reusable_chunk_lowering['non_clifford_derivation']['base_non_clifford_without_streamed_qroam'])
    rows = _public_base_run_length_rows(
        reusable_chunk_lowering=reusable_chunk_lowering,
        zkp_attestation_input=zkp_attestation_input,
    )
    rows.extend(_qroam_run_length_rows(
        reusable_chunk_lowering=reusable_chunk_lowering,
        qroam_primitive_certificate=qroam_primitive_certificate,
        row_index=len(rows),
    ))
    rows.extend(_phase_run_length_rows(selected_phase_shell, len(rows)))
    liveness_rows = _liveness_binding_rows(
        operation_rows=rows,
        reusable_chunk_lowering=reusable_chunk_lowering,
    )
    base_rows = [row for row in rows if row['scope'] in ('direct_seed_base', 'arithmetic_leaf_base')]
    qroam_rows = [row for row in rows if row['scope'] == 'qroam_chunk_stream']
    phase_rows = [row for row in rows if row['scope'] == 'phase_shell']
    non_clifford_total = sum(int(row['non_clifford_count']) for row in rows)
    gate_totals = _empty_gate_totals()
    for row in rows:
        gate = str(row['gate'])
        gate_totals[gate] += int(row['total_count'])
    qroam_stream_term_instances = sum(
        int(term['instances'])
        for term in counted_resource_ir['non_clifford_terms']
        if term['category'] == 'qroam_chunk_stream'
    )
    qroam_segment_count = int(qroam_primitive_certificate['operation_stream']['segment_count'])
    qroam_non_clifford_total = sum(int(row['non_clifford_count']) for row in qroam_rows)
    phase_total_measurements = sum(int(row['total_count']) for row in phase_rows if row['gate'] == 'measurement')
    phase_total_hadamards = sum(int(row['total_count']) for row in phase_rows if row['gate'] == 'hadamard')
    phase_total_rotations = sum(
        int(row['total_count'])
        for row in phase_rows
        if row['gate'] in ('single_qubit_rotation', 'controlled_rotation')
    )
    owner_capacity_by_id = {
        str(row['owner_id']): int(row['logical_qubits'])
        for row in reusable_chunk_lowering['owner_capacity']['rows']
    }
    wire_catalog = reusable_chunk_lowering['executable_liveness']['wire_catalog']
    checks = {
        'selected_family_matches_public_input': selected_family_name == zkp_attestation_input['selected_family_name'],
        'source_engines_pass': (
            reusable_chunk_lowering['executable_resource_engine']['pass'] is True
            and reusable_chunk_lowering['counted_resource_engine']['pass'] is True
            and arithmetic_operation_ir['pass'] is True
            and qroam_primitive_certificate['pass'] is True
        ),
        'non_clifford_total_matches_public_candidate': non_clifford_total == int(public_totals['non_clifford']),
        'qroam_rows_expand_every_public_stream_segment': len(qroam_rows) == qroam_stream_term_instances * qroam_segment_count,
        'qroam_rows_sum_to_public_qroam_derivation': qroam_non_clifford_total == int(reusable_chunk_lowering['non_clifford_derivation']['qroam_chunk_non_clifford']),
        'base_rows_match_public_non_qroam_derivation': sum(int(row['non_clifford_count']) for row in base_rows) == base_non_clifford == int(public_totals['non_clifford']) - qroam_non_clifford_total,
        'phase_rows_bind_selected_phase_shell': (
            selected_phase_shell['name'] == zkp_attestation_input['family_document']['payload']['phase_shell']
            and phase_total_hadamards == int(selected_phase_shell['hadamard_count'])
            and phase_total_measurements == int(selected_phase_shell['total_measurements'])
            and phase_total_rotations == int(selected_phase_shell['total_rotations'])
        ),
        'liveness_bindings_cover_all_materialized_rows': (
            len(liveness_rows) == len(rows)
            and [int(row['row_index']) for row in liveness_rows] == list(range(len(rows)))
        ),
        'liveness_bindings_use_known_wires_and_capacity': all(
            all(wire_id in wire_catalog for wire_id in liveness['live_wire_ids'])
            and all(int(qubits) <= owner_capacity_by_id[owner_id] for owner_id, qubits in liveness['owner_live_qubits'].items())
            for liveness in liveness_rows
        ),
        'liveness_bindings_reconstruct_public_peak': max(int(row['total_live_qubits']) for row in liveness_rows) == int(public_totals['logical_qubits']),
        'qroam_liveness_bindings_use_matching_chunk_target': all(
            f"qroam_chunk_target__{row['table']}__chunk_{row['chunk_index']}" in liveness_rows[int(row['row_index'])]['live_wire_ids']
            for row in qroam_rows
        ),
    }
    return {
        'schema': PUBLIC_CANDIDATE_MATERIALIZED_CIRCUIT_MANIFEST_SCHEMA,
        'scope': 'current public reusable-chunk candidate run-length primitive stream manifest',
        'selected_family_name': selected_family_name,
        'stream_encoding': PUBLIC_CANDIDATE_STREAM_COLUMNS,
        'liveness_binding_encoding': PUBLIC_CANDIDATE_LIVENESS_COLUMNS,
        'source_digests': {
            'reusable_chunk_lowering_sha256': _sha256_payload(reusable_chunk_lowering),
            'counted_resource_ir_sha256': reusable_chunk_lowering['executable_resource_engine']['counted_resource_ir_sha256'],
            'arithmetic_operation_ir_sha256': _sha256_payload(arithmetic_operation_ir),
            'qroam_primitive_certificate_sha256': _sha256_payload(qroam_primitive_certificate),
            'phase_shell_lowerings_sha256': _sha256_payload(phase_shell_lowerings),
            'zkp_attestation_input_sha256': _sha256_payload(zkp_attestation_input),
        },
        'operation_stream_sha256': _public_candidate_stream_hash(rows),
        'liveness_binding_stream_sha256': _public_candidate_liveness_hash(liveness_rows),
        'run_length_row_count': len(rows),
        'liveness_binding_row_count': len(liveness_rows),
        'base_row_count': len(base_rows),
        'qroam_segment_row_count': len(qroam_rows),
        'phase_row_count': len(phase_rows),
        'gate_totals': gate_totals,
        'public_totals': {
            'non_clifford': non_clifford_total,
            'logical_qubits': int(public_totals['logical_qubits']),
        },
        'materialized_liveness': {
            'peak_live_qubits': max(int(row['total_live_qubits']) for row in liveness_rows),
            'peak_interval_ids': sorted({
                str(row['interval_id'])
                for row in liveness_rows
                if int(row['total_live_qubits']) == int(public_totals['logical_qubits'])
            }),
            'owner_capacity_qubits': owner_capacity_by_id,
            'preview_head': liveness_rows[:8],
            'preview_tail': liveness_rows[-8:],
        },
        'qroam_expansion': {
            'stream_instances': qroam_stream_term_instances,
            'segments_per_stream': qroam_segment_count,
            'expanded_segment_rows': len(qroam_rows),
            'non_clifford': qroam_non_clifford_total,
            'segment_merkle_root_sha256': qroam_primitive_certificate['operation_stream']['segment_merkle_root_sha256'],
        },
        'phase_shell_expansion': {
            'name': selected_phase_shell['name'],
            'hadamards': phase_total_hadamards,
            'measurements': phase_total_measurements,
            'rotations': phase_total_rotations,
        },
        'arithmetic_evidence': {
            'schema': arithmetic_operation_ir['schema'],
            'operation_stream_sha256': arithmetic_operation_ir['leaf_arithmetic_summary']['operation_stream_sha256'],
            'non_clifford_total': int(arithmetic_operation_ir['leaf_arithmetic_summary']['non_clifford_total']),
            'note': 'Arithmetic primitive rows are still represented by the public non-QROAM base run until the full reusable-tail macro is flattened.',
        },
        'preview_head': rows[:8],
        'preview_tail': rows[-8:],
        'checks': checks,
        'pass': all(checks.values()),
        'boundary': [
            'This is a deterministic run-length primitive stream for the current public candidate, not yet a Clifford-complete flat netlist.',
            'It prevents the public candidate from relying on the superseded materialized frontier manifest while the full flat engine is developed.',
        ],
    }


def write_materialized_family_circuit(
    family_name: str,
    output_root: Path,
    frontier: Optional[Mapping[str, Any]] = None,
    gzip_output: bool = True,
) -> Dict[str, Any]:
    resolved_frontier = frontier if frontier is not None else _project_defaults()['frontier']
    family_dir = output_root / family_name
    family_dir.mkdir(parents=True, exist_ok=True)
    operations_name = 'operations.tsv.gz' if gzip_output else 'operations.tsv'
    operations_path = family_dir / operations_name
    opener = gzip.open if gzip_output else open
    with opener(operations_path, 'wt', encoding='utf-8') as handle:
        handle.write('\t'.join(STREAM_COLUMNS) + '\n')
        for row in iter_family_operation_stream(family_name, frontier=resolved_frontier):
            handle.write(_encoded_stream_row(row))
    manifest = build_materialized_family_manifest(family_name, frontier=resolved_frontier)
    manifest['operations_path'] = str(operations_path.relative_to(PROJECT_ROOT))
    (family_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


__all__ = [
    'MATERIALIZED_CIRCUIT_MANIFEST_SCHEMA',
    'PUBLIC_CANDIDATE_MATERIALIZED_CIRCUIT_MANIFEST_SCHEMA',
    'available_family_names',
    'build_materialized_family_manifest',
    'build_public_candidate_materialized_circuit_manifest',
    'iter_family_operation_stream',
    'resolve_selected_family_names',
    'write_materialized_family_circuit',
]
