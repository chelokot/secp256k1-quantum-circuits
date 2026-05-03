#!/usr/bin/env python3

from __future__ import annotations

import gzip
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
from project import FIELD_BITS, FULL_PHASE_REGISTER_BITS as PROJECT_PHASE_BITS, compiler_family_frontier, leaf_opcode_histogram, raw32_schedule


def _family_lookup(frontier: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {row['name']: row for row in frontier['families']}


def available_family_names(frontier: Optional[Mapping[str, Any]] = None) -> List[str]:
    resolved_frontier = frontier if frontier is not None else compiler_family_frontier()
    return [row['name'] for row in resolved_frontier['families']]


def resolve_selected_family_names(
    selected: Optional[Iterable[str]] = None,
    include_all: bool = False,
    frontier: Optional[Mapping[str, Any]] = None,
) -> List[str]:
    resolved_frontier = frontier if frontier is not None else compiler_family_frontier()
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
) -> Iterator[Dict[str, Any]]:
    leaf = json.loads((Path(__file__).resolve().parents[2] / 'artifacts' / 'circuits' / 'optimized_pointadd_secp256k1.json').read_text())
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
) -> Iterator[Dict[str, Any]]:
    resolved_frontier = frontier if frontier is not None else compiler_family_frontier()
    family = _family_lookup(resolved_frontier)[family_name]
    schedule = raw32_schedule()
    arithmetic_lowerings = arithmetic_lowering_library(field_bits=FIELD_BITS, leaf_opcode_histogram=leaf_opcode_histogram())
    kernel_lookup = {row['opcode']: row for row in arithmetic_lowerings['kernels']}
    lookup_family = next(row for row in lookup_lowering_library()['families'] if row['name'] == family['lookup_family'])
    phase_shell = next(row for row in phase_shell_lowering_library(PROJECT_PHASE_BITS)['families'] if row['name'] == family['phase_shell'])

    global_index = 0
    for stream in (
        _iter_lookup_operations(family_name, lookup_family, schedule),
        _iter_arithmetic_operations(family_name, kernel_lookup, schedule),
        _iter_phase_shell_operations(family_name, phase_shell),
    ):
        for row in stream:
            row['stream_index'] = global_index
            yield row
            global_index += 1


def build_materialized_family_manifest(
    family_name: str,
    frontier: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    resolved_frontier = frontier if frontier is not None else compiler_family_frontier()
    family = _family_lookup(resolved_frontier)[family_name]
    gate_totals = {
        'ccx': 0,
        'cx': 0,
        'x': 0,
        'measurement': 0,
        'hadamard': 0,
        'single_qubit_rotation': 0,
        'controlled_rotation': 0,
    }
    operation_count = 0
    preview_head: List[Dict[str, Any]] = []
    preview_tail: List[Dict[str, Any]] = []
    for row in iter_family_operation_stream(family_name, frontier=resolved_frontier):
        gate = str(row['gate'])
        gate_totals[gate] += 1
        operation_count += 1
        if len(preview_head) < 8:
            preview_head.append(dict(row))
        preview_tail.append(dict(row))
        if len(preview_tail) > 8:
            preview_tail.pop(0)
    return {
        'family': family_name,
        'summary': family['summary'],
        'lookup_family': family['lookup_family'],
        'phase_shell': family['phase_shell'],
        'arithmetic_kernel_family': family['arithmetic_kernel_family'],
        'stream_encoding': ['stream_index', 'family', 'scope', 'invocation', 'source', 'gate', 'operand_0', 'operand_1', 'operand_2'],
        'operation_count': operation_count,
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
    resolved_frontier = frontier if frontier is not None else compiler_family_frontier()
    family_dir = output_root / family_name
    family_dir.mkdir(parents=True, exist_ok=True)
    operations_name = 'operations.tsv.gz' if gzip_output else 'operations.tsv'
    operations_path = family_dir / operations_name
    columns = ['stream_index', 'family', 'scope', 'invocation', 'source', 'gate', 'operand_0', 'operand_1', 'operand_2']
    opener = gzip.open if gzip_output else open
    with opener(operations_path, 'wt', encoding='utf-8') as handle:
        handle.write('\t'.join(columns) + '\n')
        for row in iter_family_operation_stream(family_name, frontier=resolved_frontier):
            handle.write('\t'.join(str(row[column]) for column in columns) + '\n')
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
