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
    'available_family_names',
    'build_materialized_family_manifest',
    'iter_family_operation_stream',
    'resolve_selected_family_names',
    'write_materialized_family_circuit',
]
