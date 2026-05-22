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
PUBLIC_CANDIDATE_FLAT_NETLIST_COLUMNS = [
    'operation_index',
    'run_length_row_index',
    'row_instance_ordinal',
    'scope',
    'source',
    'gate',
    'operand_wires',
    'liveness_interval_id',
    'total_live_qubits',
    'primitive_operand_contract_sha256',
    'liveness_binding_sha256',
]
PUBLIC_CANDIDATE_STREAM_COLUMNS = [
    'row_index',
    'scope',
    'source',
    'gate',
    'instance_count',
    'total_count',
    'non_clifford_count',
    'provenance_sha256',
    'primitive_operand_contract_sha256',
]
PUBLIC_CANDIDATE_LIVENESS_COLUMNS = [
    'row_index',
    'scope',
    'interval_id',
    'live_wire_ids',
    'owner_live_qubits',
    'derived_owner_live_qubits',
    'total_live_qubits',
    'owner_capacity_pass',
]
PUBLIC_CANDIDATE_FLAT_SEGMENT_SIZE = 1_000_000
PUBLIC_CANDIDATE_FLAT_PROBE_WIDTH = 4
PRIMITIVE_GATE_ARITY = {
    'ccx': 3,
    'cx': 2,
    'x': 1,
    'measurement': 1,
    'hadamard': 1,
    'single_qubit_rotation': 1,
    'controlled_rotation': 2,
}


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


def _primitive_operand_contract(
    *,
    scope: str,
    gate: str,
    source_kind: str,
    operand_domains: List[Mapping[str, Any]],
    source_digest: str,
) -> Dict[str, Any]:
    owner_ids = sorted({str(domain['owner_id']) for domain in operand_domains})
    return {
        'schema': 'compiler-project-primitive-operand-contract-v1',
        'scope': scope,
        'gate': gate,
        'source_kind': source_kind,
        'source_digest_sha256': source_digest,
        'owner_ids': owner_ids,
        'operand_domains': [dict(domain) for domain in operand_domains],
    }


def _parent_wire_domain(
    *,
    parent_wire_ids: List[str],
    parent_bit_width: int,
    parent_selection_rule: str,
) -> Dict[str, Any]:
    return {
        'parent_wire_ids': list(parent_wire_ids),
        'parent_bit_width': int(parent_bit_width),
        'parent_selection_rule': parent_selection_rule,
    }


def _arithmetic_parent_domain(parent_wire_ids: List[str]) -> Dict[str, Any]:
    return _parent_wire_domain(
        parent_wire_ids=parent_wire_ids,
        parent_bit_width=256,
        parent_selection_rule='parent_wire_index = operand_index // parent_bit_width; parent_bit_index = operand_index % parent_bit_width',
    )


def _arithmetic_block_operand_domains(stage: Mapping[str, Any], block: Mapping[str, Any], gate: str) -> List[Dict[str, Any]]:
    operand_slots = int(block['operand_profile']['operand_slots_required'])
    gate_arities = block['operand_profile']['gate_arities']
    if gate == 'measurement':
        return [
            {
                'domain_id': f"{stage['stage']}:{block['block']}:measured_arithmetic_bit",
                'owner_id': 'arithmetic_slot_register_file',
                'wire_template': 'arithmetic_slot_register_file.measurement.bit[{operand_index}]',
                'operand_index_min': 0,
                'operand_index_max_exclusive': operand_slots,
                'row_instance_to_operand_index': 'operand_index = row_instance_ordinal % operand_domain_width',
                'role': str(stage['category']),
                **_arithmetic_parent_domain(['qz']),
            }
        ]
    if gate == 'ccx' and gate_arities.get('ccx') == [2]:
        return [
            {
                'domain_id': f"{stage['stage']}:{block['block']}:left_field_bits",
                'owner_id': 'arithmetic_slot_register_file',
                'wire_template': 'arithmetic_slot_register_file.left_input.bit[{left_bit}]',
                'operand_index_min': 0,
                'operand_index_max_exclusive': operand_slots,
                'row_instance_to_operand_index': 'left_bit = row_instance_ordinal // operand_slots_required',
                'role': str(stage['category']),
                **_arithmetic_parent_domain(['qx']),
            },
            {
                'domain_id': f"{stage['stage']}:{block['block']}:right_field_bits",
                'owner_id': 'arithmetic_slot_register_file',
                'wire_template': 'arithmetic_slot_register_file.right_input.bit[{right_bit}]',
                'operand_index_min': 0,
                'operand_index_max_exclusive': operand_slots,
                'row_instance_to_operand_index': 'right_bit = row_instance_ordinal % operand_slots_required',
                'role': str(stage['category']),
                **_arithmetic_parent_domain(['qy']),
            },
            {
                'domain_id': f"{stage['stage']}:{block['block']}:partial_product_target",
                'owner_id': 'arithmetic_slot_register_file',
                'wire_template': 'arithmetic_slot_register_file.partial_product_target.bit[{row_instance_ordinal}]',
                'operand_index_min': 0,
                'operand_index_max_exclusive': int(block['primitive_counts_total'][gate]),
                'row_instance_to_operand_index': 'operand_index = row_instance_ordinal % operand_domain_width',
                'role': str(stage['category']),
                **_arithmetic_parent_domain(['qchunk']),
            },
        ]
    if gate == 'ccx':
        return [
            {
                'domain_id': f"{stage['stage']}:{block['block']}:control_a",
                'owner_id': 'arithmetic_slot_register_file',
                'wire_template': 'arithmetic_slot_register_file.control_a.bit[{operand_index}]',
                'operand_index_min': 0,
                'operand_index_max_exclusive': operand_slots,
                'row_instance_to_operand_index': 'operand_index = row_instance_ordinal % operand_domain_width',
                'role': str(stage['category']),
                **_arithmetic_parent_domain(['qx']),
            },
            {
                'domain_id': f"{stage['stage']}:{block['block']}:control_b",
                'owner_id': 'arithmetic_slot_register_file',
                'wire_template': 'arithmetic_slot_register_file.control_b.bit[{operand_index}]',
                'operand_index_min': 0,
                'operand_index_max_exclusive': operand_slots,
                'row_instance_to_operand_index': 'operand_index = row_instance_ordinal % operand_domain_width',
                'role': str(stage['category']),
                **_arithmetic_parent_domain(['qy']),
            },
            {
                'domain_id': f"{stage['stage']}:{block['block']}:target",
                'owner_id': 'arithmetic_slot_register_file',
                'wire_template': 'arithmetic_slot_register_file.target.bit[{operand_index}]',
                'operand_index_min': 0,
                'operand_index_max_exclusive': operand_slots,
                'row_instance_to_operand_index': 'operand_index = row_instance_ordinal % operand_domain_width',
                'role': str(stage['category']),
                **_arithmetic_parent_domain(['qz']),
            },
        ]
    return [
        {
            'domain_id': f"{stage['stage']}:{block['block']}:arithmetic_field_bits",
            'owner_id': 'arithmetic_slot_register_file',
            'wire_template': 'arithmetic_slot_register_file.bit[{operand_index}]',
            'operand_index_min': 0,
            'operand_index_max_exclusive': operand_slots,
            'row_instance_to_operand_index': 'operand_index = row_instance_ordinal % operand_slots_required',
            'role': str(stage['category']),
            **_arithmetic_parent_domain(['qx']),
        }
    ]


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


def _flat_segment_hash(contributions: List[Mapping[str, Any]]) -> str:
    digest = hashlib.sha256()
    digest.update(b'compiler-project-public-candidate-flat-segment-v1\n')
    for contribution in contributions:
        digest.update((_canonical_json(contribution) + '\n').encode('ascii'))
    return digest.hexdigest()


def _flat_netlist_commitment(
    *,
    operation_rows: List[Mapping[str, Any]],
    liveness_rows: List[Mapping[str, Any]],
    segment_size: int = PUBLIC_CANDIDATE_FLAT_SEGMENT_SIZE,
) -> Dict[str, Any]:
    if segment_size <= 0:
        raise ValueError('segment_size must be positive')
    liveness_hash_by_row = {
        int(row['row_index']): _sha256_payload(row)
        for row in liveness_rows
    }
    operation_count = sum(int(row['total_count']) for row in operation_rows)
    flat_gate_totals = _empty_gate_totals()
    flat_non_clifford = 0
    segments: List[Dict[str, Any]] = []
    row_index = 0
    row_offset = 0
    operation_cursor = 0
    while operation_cursor < operation_count:
        segment_start = operation_cursor
        segment_end = min(segment_start + segment_size, operation_count)
        segment_gate_totals = _empty_gate_totals()
        segment_non_clifford = 0
        contributions: List[Dict[str, Any]] = []
        while operation_cursor < segment_end:
            row = operation_rows[row_index]
            row_total = int(row['total_count'])
            take = min(row_total - row_offset, segment_end - operation_cursor)
            gate = str(row['gate'])
            contribution = {
                'run_length_row_index': int(row['row_index']),
                'operation_start': operation_cursor,
                'operation_end_exclusive': operation_cursor + take,
                'row_instance_start': row_offset,
                'row_instance_end_exclusive': row_offset + take,
                'scope': str(row['scope']),
                'gate': gate,
                'source': str(row['source']),
                'liveness_binding_sha256': liveness_hash_by_row[int(row['row_index'])],
                'primitive_operand_contract_sha256': str(row['primitive_operand_contract_sha256']),
                'primitive_operand_owner_ids': list(row['primitive_operand_contract']['owner_ids']),
            }
            contributions.append(contribution)
            segment_gate_totals[gate] += take
            flat_gate_totals[gate] += take
            if gate == 'ccx':
                segment_non_clifford += take
                flat_non_clifford += take
            operation_cursor += take
            row_offset += take
            if row_offset == row_total:
                row_index += 1
                row_offset = 0
        segments.append({
            'segment_index': len(segments),
            'operation_start': segment_start,
            'operation_end_exclusive': segment_end,
            'operation_count': segment_end - segment_start,
            'contribution_count': len(contributions),
            'gate_totals': segment_gate_totals,
            'non_clifford_count': segment_non_clifford,
            'sha256': _flat_segment_hash(contributions),
            'contributions': contributions,
        })
    return {
        'schema': 'compiler-project-public-candidate-flat-index-netlist-v1',
        'operation_schema': [
            'operation_index',
            'run_length_row_index',
            'row_instance_ordinal',
            'gate',
            'scope',
            'source',
            'live_wire_ids',
            'derived_owner_live_qubits',
        ],
        'expansion_rule': 'Each segment contribution expands to one primitive instruction for every operation_index in [operation_start, operation_end_exclusive); row_instance_ordinal is the corresponding offset inside the contributing run-length row.',
        'segment_size': segment_size,
        'operation_count': operation_count,
        'segment_count': len(segments),
        'segment_merkle_root_sha256': _merkle_root([segment['sha256'] for segment in segments]),
        'gate_totals': flat_gate_totals,
        'non_clifford_count': flat_non_clifford,
        'segments': segments,
    }


def _wire_from_domain(domain: Mapping[str, Any], operand_index: int, row_instance_ordinal: int) -> Dict[str, Any]:
    parent_wire_ids = [str(wire_id) for wire_id in domain.get('parent_wire_ids', [])]
    parent_bit_width = int(domain.get('parent_bit_width', 0))
    if parent_wire_ids and parent_bit_width > 0:
        parent_offset = max(0, int(operand_index) - int(domain['operand_index_min']))
        parent_wire_id = parent_wire_ids[(parent_offset // parent_bit_width) % len(parent_wire_ids)]
        parent_bit_index = parent_offset % parent_bit_width
    else:
        parent_wire_id = ''
        parent_bit_index = int(operand_index)
    template = str(domain['wire_template'])
    wire_id = template.format(
        operand_index=int(operand_index),
        left_bit=int(operand_index),
        right_bit=int(operand_index),
        row_instance_ordinal=int(row_instance_ordinal),
    )
    if parent_wire_id:
        wire_id = f'{parent_wire_id}.bit[{parent_bit_index}]'
    return {
        'domain_id': str(domain['domain_id']),
        'owner_id': str(domain['owner_id']),
        'role': str(domain['role']),
        'operand_index': int(operand_index),
        'parent_wire_id': parent_wire_id,
        'parent_bit_index': parent_bit_index,
        'wire_id': wire_id,
    }


def _operation_domain_wires(row: Mapping[str, Any], row_instance_ordinal: int) -> List[Dict[str, Any]]:
    domains = row['primitive_operand_contract']['operand_domains']
    wires: List[Dict[str, Any]] = []
    for domain in domains:
        domain_min = int(domain['operand_index_min'])
        domain_max = int(domain['operand_index_max_exclusive'])
        domain_width = domain_max - domain_min
        rule = str(domain.get('row_instance_to_operand_index', 'operand_index = row_instance_ordinal % operand_domain_width'))
        if domain_width <= 0:
            operand_index = domain_min
        elif 'left_bit = row_instance_ordinal // operand_slots_required' in rule:
            operand_index = domain_min + (int(row_instance_ordinal) // domain_width)
        elif 'right_bit = row_instance_ordinal % operand_slots_required' in rule:
            operand_index = domain_min + (int(row_instance_ordinal) % domain_width)
        else:
            operand_index = domain_min + (int(row_instance_ordinal) % domain_width)
        wires.append(_wire_from_domain(domain, operand_index, int(row_instance_ordinal)))
    return wires


def iter_public_candidate_flat_netlist(
    operation_rows: List[Mapping[str, Any]],
    liveness_rows: List[Mapping[str, Any]],
    *,
    start: int = 0,
    stop: Optional[int] = None,
) -> Iterator[Dict[str, Any]]:
    if start < 0:
        raise ValueError('start must be non-negative')
    row_by_index = {int(row['row_index']): row for row in liveness_rows}
    operation_index = 0
    for row in operation_rows:
        row_total = int(row['total_count'])
        row_start = operation_index
        row_end = row_start + row_total
        requested_stop = row_end if stop is None else min(int(stop), row_end)
        if requested_stop > start and row_total > 0:
            local_start = max(int(start), row_start) - row_start
            local_stop = requested_stop - row_start
            liveness = row_by_index[int(row['row_index'])]
            for row_instance_ordinal in range(local_start, local_stop):
                yield {
                    'operation_index': row_start + row_instance_ordinal,
                    'run_length_row_index': int(row['row_index']),
                    'row_instance_ordinal': row_instance_ordinal,
                    'scope': str(row['scope']),
                    'source': str(row['source']),
                    'gate': str(row['gate']),
                    'operand_wires': _operation_domain_wires(row, row_instance_ordinal),
                    'liveness': {
                        'interval_id': str(liveness['interval_id']),
                        'live_wire_ids': list(liveness['live_wire_ids']),
                        'derived_owner_live_qubits': dict(liveness['derived_owner_live_qubits']),
                        'total_live_qubits': int(liveness['total_live_qubits']),
                    },
                    'primitive_operand_contract_sha256': str(row['primitive_operand_contract_sha256']),
                    'liveness_binding_sha256': _sha256_payload(liveness),
                }
        operation_index = row_end
        if stop is not None and operation_index >= int(stop):
            break


def _encoded_public_candidate_flat_operation(row: Mapping[str, Any]) -> str:
    encoded = [
        int(row['operation_index']),
        int(row['run_length_row_index']),
        int(row['row_instance_ordinal']),
        str(row['scope']),
        str(row['source']),
        str(row['gate']),
        _canonical_json(row['operand_wires']),
        str(row['liveness']['interval_id']),
        int(row['liveness']['total_live_qubits']),
        str(row['primitive_operand_contract_sha256']),
        str(row['liveness_binding_sha256']),
    ]
    return '\t'.join(str(value) for value in encoded) + '\n'


def write_public_candidate_flat_netlist(
    manifest: Mapping[str, Any],
    output_path: Path,
    *,
    gzip_output: bool = True,
    start: int = 0,
    stop: Optional[int] = None,
) -> Dict[str, Any]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    opener = gzip.open if gzip_output else open
    row_count = 0
    stream_hash = hashlib.sha256()
    header = '\t'.join(PUBLIC_CANDIDATE_FLAT_NETLIST_COLUMNS) + '\n'
    stream_hash.update(header.encode('ascii'))
    with opener(output_path, 'wt', encoding='utf-8') as handle:
        handle.write(header)
        for row in iter_public_candidate_flat_netlist(
            list(manifest['run_length_rows']),
            list(manifest['materialized_liveness']['rows']),
            start=start,
            stop=stop,
        ):
            encoded_row = _encoded_public_candidate_flat_operation(row)
            handle.write(encoded_row)
            stream_hash.update(encoded_row.encode('utf-8'))
            row_count += 1
    return {
        'schema': 'compiler-project-public-candidate-flat-netlist-export-v1',
        'source_manifest_schema': manifest['schema'],
        'source_manifest_sha256': _sha256_payload(manifest),
        'columns': PUBLIC_CANDIDATE_FLAT_NETLIST_COLUMNS,
        'path': str(output_path),
        'gzip': bool(gzip_output),
        'start': int(start),
        'stop': None if stop is None else int(stop),
        'row_count': row_count,
        'sha256': stream_hash.hexdigest(),
    }


def _segment_contribution_for_operation(flat_netlist: Mapping[str, Any], operation_index: int) -> Mapping[str, Any]:
    for segment in flat_netlist['segments']:
        if int(segment['operation_start']) <= int(operation_index) < int(segment['operation_end_exclusive']):
            for contribution in segment['contributions']:
                if int(contribution['operation_start']) <= int(operation_index) < int(contribution['operation_end_exclusive']):
                    return contribution
    raise KeyError(f'operation index is not covered by flat netlist segments: {operation_index}')


def _probe_ordinals(total_count: int) -> List[int]:
    if total_count <= 0:
        return []
    return sorted({0, int(total_count) // 2, int(total_count) - 1})


def _probe_rows(rows: List[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
    selected: List[Mapping[str, Any]] = []

    def add(row: Mapping[str, Any]) -> None:
        if int(row['row_index']) not in {int(existing['row_index']) for existing in selected}:
            selected.append(row)

    for scope in ('direct_seed_base', 'lookup_leaf_base', 'arithmetic_leaf_block', 'qroam_chunk_stream', 'phase_shell'):
        add(next(row for row in rows if row['scope'] == scope))
    schoolbook_arithmetic = next(
        (
            row
            for row in rows
            if row['scope'] == 'arithmetic_leaf_block'
            and any(str(domain['domain_id']).endswith(':left_field_bits') for domain in row['primitive_operand_contract']['operand_domains'])
            and any(str(domain['domain_id']).endswith(':right_field_bits') for domain in row['primitive_operand_contract']['operand_domains'])
        ),
        None,
    )
    if schoolbook_arithmetic is not None:
        add(schoolbook_arithmetic)
    return selected


def _row_operation_starts(rows: List[Mapping[str, Any]]) -> Dict[int, int]:
    starts: Dict[int, int] = {}
    cursor = 0
    for row in rows:
        starts[int(row['row_index'])] = cursor
        cursor += int(row['total_count'])
    return starts


def _reduced_arithmetic_probe(row: Mapping[str, Any], probe_width: int) -> Dict[str, Any]:
    domains = row['primitive_operand_contract']['operand_domains']
    left_domain = next((domain for domain in domains if str(domain['domain_id']).endswith(':left_field_bits')), None)
    right_domain = next((domain for domain in domains if str(domain['domain_id']).endswith(':right_field_bits')), None)
    if row['scope'] != 'arithmetic_leaf_block' or left_domain is None or right_domain is None:
        return {
            'applies': False,
            'pass': True,
        }
    width = min(
        int(probe_width),
        int(left_domain['operand_index_max_exclusive']) - int(left_domain['operand_index_min']),
        int(right_domain['operand_index_max_exclusive']) - int(right_domain['operand_index_min']),
    )
    full_right_width = int(right_domain['operand_index_max_exclusive']) - int(right_domain['operand_index_min'])
    ordinals = [
        left * full_right_width + right
        for left in range(width)
        for right in range(width)
    ]
    observed_pairs = [
        tuple(
            wire['operand_index']
            for wire in _operation_domain_wires(row, ordinal)
            if wire['domain_id'] in {left_domain['domain_id'], right_domain['domain_id']}
        )
        for ordinal in ordinals
    ]
    expected_pairs = [
        (left, right)
        for left in range(width)
        for right in range(width)
    ]
    return {
        'applies': True,
        'probe_width': width,
        'observed_pairs': observed_pairs,
        'expected_pairs': expected_pairs,
        'pass': observed_pairs == expected_pairs,
    }


def _flat_execution_probe(
    *,
    rows: List[Mapping[str, Any]],
    liveness_rows: List[Mapping[str, Any]],
    flat_netlist: Mapping[str, Any],
    owner_capacity_by_id: Mapping[str, int],
    wire_catalog: Mapping[str, Any],
) -> Dict[str, Any]:
    row_starts = _row_operation_starts(rows)
    liveness_by_row = {int(row['row_index']): row for row in liveness_rows}
    probes: List[Dict[str, Any]] = []
    reduced_checks = []
    for row in _probe_rows(rows):
        reduced_checks.append(_reduced_arithmetic_probe(row, PUBLIC_CANDIDATE_FLAT_PROBE_WIDTH))
        for row_instance_ordinal in _probe_ordinals(int(row['total_count'])):
            operation_index = row_starts[int(row['row_index'])] + row_instance_ordinal
            operation = next(iter_public_candidate_flat_netlist(
                rows,
                liveness_rows,
                start=operation_index,
                stop=operation_index + 1,
            ))
            contribution = _segment_contribution_for_operation(flat_netlist, operation_index)
            operand_wires = operation['operand_wires']
            derived_owner_live_qubits = operation['liveness']['derived_owner_live_qubits']
            live_wire_ids = set(str(wire_id) for wire_id in operation['liveness']['live_wire_ids'])
            parent_bit_refs = [
                (str(wire['parent_wire_id']), int(wire['parent_bit_index']))
                for wire in operand_wires
            ]
            probes.append({
                'operation_index': operation_index,
                'run_length_row_index': int(row['row_index']),
                'row_instance_ordinal': row_instance_ordinal,
                'scope': operation['scope'],
                'gate': operation['gate'],
                'operand_wires': operand_wires,
                'segment_contribution': {
                    'operation_start': int(contribution['operation_start']),
                    'operation_end_exclusive': int(contribution['operation_end_exclusive']),
                    'primitive_operand_contract_sha256': str(contribution['primitive_operand_contract_sha256']),
                    'liveness_binding_sha256': str(contribution['liveness_binding_sha256']),
                },
                'checks': {
                    'operation_matches_requested_index': int(operation['operation_index']) == operation_index,
                    'segment_contribution_covers_operation': (
                        int(contribution['run_length_row_index']) == int(row['row_index'])
                        and int(contribution['row_instance_start']) <= row_instance_ordinal < int(contribution['row_instance_end_exclusive'])
                    ),
                    'segment_binds_operand_contract': str(contribution['primitive_operand_contract_sha256']) == str(row['primitive_operand_contract_sha256']),
                    'segment_binds_liveness': str(contribution['liveness_binding_sha256']) == _sha256_payload(liveness_by_row[int(row['row_index'])]),
                    'operand_indices_within_domains': all(
                        int(domain['operand_index_min']) <= int(wire['operand_index']) < int(domain['operand_index_max_exclusive'])
                        for domain, wire in zip(row['primitive_operand_contract']['operand_domains'], operand_wires)
                    ),
                    'operand_owners_are_live': all(
                        str(wire['owner_id']) in derived_owner_live_qubits
                        for wire in operand_wires
                    ),
                    'operand_parent_wires_are_live': all(
                        str(wire['parent_wire_id']) in live_wire_ids
                        for wire in operand_wires
                    ),
                    'operand_parent_bits_are_within_capacity': all(
                        str(wire['parent_wire_id']) in wire_catalog
                        and int(wire['parent_bit_index']) < int(wire_catalog[str(wire['parent_wire_id'])]['qubits'])
                        for wire in operand_wires
                    ),
                    'ccx_operands_use_distinct_parent_bits': (
                        operation['gate'] != 'ccx'
                        or len(parent_bit_refs) == len(set(parent_bit_refs))
                    ),
                    'live_owner_capacity_covers_operands': all(
                        str(wire['owner_id']) in derived_owner_live_qubits
                        and str(wire['owner_id']) in owner_capacity_by_id
                        and int(derived_owner_live_qubits[str(wire['owner_id'])]) <= int(owner_capacity_by_id[str(wire['owner_id'])])
                        for wire in operand_wires
                    ),
                },
            })
    probe_digest = hashlib.sha256()
    for probe in probes:
        probe_digest.update((_canonical_json({
            'operation_index': probe['operation_index'],
            'run_length_row_index': probe['run_length_row_index'],
            'row_instance_ordinal': probe['row_instance_ordinal'],
            'scope': probe['scope'],
            'gate': probe['gate'],
            'operand_wires': probe['operand_wires'],
            'checks': probe['checks'],
        }) + '\n').encode('ascii'))
    qroam_domain_capacity_checks = []
    arithmetic_domain_capacity_checks = []
    for row in rows:
        domains = row['primitive_operand_contract']['operand_domains']
        if row['scope'] == 'qroam_chunk_stream':
            target_domain = next(domain for domain in domains if domain['role'] == 'qroam_target_or_unary_step')
            qroam_domain_capacity_checks.append({
                'row_index': int(row['row_index']),
                'total_count': int(row['total_count']),
                'target_domain_width': int(target_domain['operand_index_max_exclusive']) - int(target_domain['operand_index_min']),
                'pass': int(row['total_count']) == int(target_domain['operand_index_max_exclusive']) - int(target_domain['operand_index_min']),
            })
        left_domain = next((domain for domain in domains if str(domain['domain_id']).endswith(':left_field_bits')), None)
        right_domain = next((domain for domain in domains if str(domain['domain_id']).endswith(':right_field_bits')), None)
        if row['scope'] == 'arithmetic_leaf_block' and left_domain is not None and right_domain is not None:
            domain_product = 1
            for domain in (left_domain, right_domain):
                domain_product *= int(domain['operand_index_max_exclusive']) - int(domain['operand_index_min'])
            arithmetic_domain_capacity_checks.append({
                'row_index': int(row['row_index']),
                'total_count': int(row['total_count']),
                'domain_product': domain_product,
                'repeat_count': int(row['total_count']) // domain_product if domain_product else 0,
                'pass': domain_product > 0 and int(row['total_count']) % domain_product == 0,
            })
    return {
        'schema': 'compiler-project-flat-netlist-execution-probe-v1',
        'source_flat_netlist_schema': flat_netlist['schema'],
        'probe_width': PUBLIC_CANDIDATE_FLAT_PROBE_WIDTH,
        'probe_count': len(probes),
        'probe_stream_sha256': probe_digest.hexdigest(),
        'probes': probes,
        'reduced_arithmetic_probes': reduced_checks,
        'qroam_domain_capacity_checks': qroam_domain_capacity_checks,
        'arithmetic_domain_capacity_checks': arithmetic_domain_capacity_checks,
        'checks': {
            'probe_operations_bind_segment_contributions': all(
                probe['checks']['operation_matches_requested_index']
                and probe['checks']['segment_contribution_covers_operation']
                and probe['checks']['segment_binds_operand_contract']
                and probe['checks']['segment_binds_liveness']
                for probe in probes
            ),
            'probe_operand_indices_within_domains': all(
                probe['checks']['operand_indices_within_domains']
                for probe in probes
            ),
            'probe_operand_owners_are_live_and_within_capacity': all(
                probe['checks']['operand_owners_are_live']
                and probe['checks']['operand_parent_wires_are_live']
                and probe['checks']['operand_parent_bits_are_within_capacity']
                and probe['checks']['ccx_operands_use_distinct_parent_bits']
                and probe['checks']['live_owner_capacity_covers_operands']
                for probe in probes
            ),
            'reduced_schoolbook_operand_grid_executes_cartesian_prefix': all(
                check['pass'] is True
                for check in reduced_checks
            ),
            'qroam_target_domain_width_matches_each_stream_segment': all(
                check['pass'] is True
                for check in qroam_domain_capacity_checks
            ),
            'arithmetic_two_operand_domain_product_matches_row_total': all(
                check['pass'] is True
                for check in arithmetic_domain_capacity_checks
            ),
        },
    }


def _strict_primitive_completeness_report(rows: List[Mapping[str, Any]]) -> Dict[str, Any]:
    incomplete_rows: List[Dict[str, Any]] = []
    rows_by_gate: Dict[str, int] = {}
    incomplete_by_scope_gate: Dict[str, int] = {}
    for row in rows:
        gate = str(row['gate'])
        rows_by_gate[gate] = rows_by_gate.get(gate, 0) + 1
        expected_arity = PRIMITIVE_GATE_ARITY[gate]
        observed_arity = len(row['primitive_operand_contract']['operand_domains'])
        if observed_arity == expected_arity:
            continue
        key = f"{row['scope']}:{gate}"
        incomplete_by_scope_gate[key] = incomplete_by_scope_gate.get(key, 0) + 1
        if len(incomplete_rows) < 16:
            incomplete_rows.append({
                'row_index': int(row['row_index']),
                'scope': str(row['scope']),
                'source': str(row['source']),
                'gate': gate,
                'total_count': int(row['total_count']),
                'expected_operand_arity': expected_arity,
                'observed_operand_domain_count': observed_arity,
                'operand_domain_ids': [
                    str(domain['domain_id'])
                    for domain in row['primitive_operand_contract']['operand_domains']
                ],
            })
    incomplete_row_count = sum(incomplete_by_scope_gate.values())
    return {
        'schema': 'compiler-project-strict-primitive-completeness-report-v1',
        'definition': 'A Clifford-complete primitive netlist row must give the exact concrete wire operands required by the gate arity, not only owner/domain templates.',
        'required_gate_arity': dict(PRIMITIVE_GATE_ARITY),
        'rows_checked': len(rows),
        'rows_by_gate': {
            key: int(value)
            for key, value in sorted(rows_by_gate.items())
        },
        'incomplete_row_count': incomplete_row_count,
        'incomplete_by_scope_gate': {
            key: int(value)
            for key, value in sorted(incomplete_by_scope_gate.items())
        },
        'sample_incomplete_rows': incomplete_rows,
        'clifford_complete': incomplete_row_count == 0,
        'next_required_lowering': [
            'Replace arithmetic operand-domain templates with exact control/target wires for every generated field-arithmetic primitive.',
            'Replace lookup and QROAM operand-domain templates with exact address/control/target wires for every primitive gate.',
            'Make this report a passing public-engine invariant before calling the result a Clifford-complete full netlist.',
        ],
    }


def _operand_parent_binding_report(
    *,
    rows: List[Mapping[str, Any]],
    liveness_rows: List[Mapping[str, Any]],
    wire_catalog: Mapping[str, Any],
) -> Dict[str, Any]:
    failures: List[Dict[str, Any]] = []
    liveness_by_row = {int(row['row_index']): row for row in liveness_rows}
    domains_checked = 0
    for row in rows:
        liveness = liveness_by_row[int(row['row_index'])]
        live_wire_ids = {str(wire_id) for wire_id in liveness['live_wire_ids']}
        for domain in row['primitive_operand_contract']['operand_domains']:
            domains_checked += 1
            parent_wire_ids = [str(wire_id) for wire_id in domain.get('parent_wire_ids', [])]
            parent_bit_width = int(domain.get('parent_bit_width', 0))
            domain_failures: List[str] = []
            if not parent_wire_ids:
                domain_failures.append('missing_parent_wire_ids')
            if parent_bit_width <= 0:
                domain_failures.append('missing_parent_bit_width')
            for parent_wire_id in parent_wire_ids:
                if parent_wire_id not in wire_catalog:
                    domain_failures.append(f'unknown_parent_wire:{parent_wire_id}')
                    continue
                wire = wire_catalog[parent_wire_id]
                if str(wire['owner_id']) != str(domain['owner_id']):
                    domain_failures.append(f'parent_owner_mismatch:{parent_wire_id}')
                if parent_wire_id not in live_wire_ids:
                    domain_failures.append(f'parent_not_live:{parent_wire_id}')
                if parent_bit_width > int(wire['qubits']):
                    domain_failures.append(f'parent_bit_width_exceeds_wire:{parent_wire_id}')
            if domain_failures and len(failures) < 32:
                failures.append({
                    'row_index': int(row['row_index']),
                    'scope': str(row['scope']),
                    'gate': str(row['gate']),
                    'domain_id': str(domain['domain_id']),
                    'owner_id': str(domain['owner_id']),
                    'parent_wire_ids': parent_wire_ids,
                    'parent_bit_width': parent_bit_width,
                    'failures': domain_failures,
                })
            elif domain_failures:
                failures.append({'failures': domain_failures})
    return {
        'schema': 'compiler-project-operand-parent-binding-report-v1',
        'definition': 'Every primitive operand domain must map to counted parent wires that are present in the executable wire catalog, owned by the same counted owner, live for the row liveness interval, and wide enough for the domain bit mapping.',
        'rows_checked': len(rows),
        'domains_checked': domains_checked,
        'failure_count': len(failures),
        'sample_failures': failures[:32],
        'pass': len(failures) == 0,
    }


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
                if gate == 'controlled_rotation':
                    operand_domains = [
                        {
                            'domain_id': 'semiclassical_qft_control_phase_bit',
                            'owner_id': 'phase_shell_live_register',
                            'wire_template': 'semiclassical_qft_live_phase_bit',
                            'operand_index_min': 0,
                            'operand_index_max_exclusive': 1,
                            'role': 'phase_shell_control_qubit',
                            **_parent_wire_domain(
                                parent_wire_ids=['semiclassical_qft_live_phase_bit'],
                                parent_bit_width=1,
                                parent_selection_rule='single live semiclassical phase bit',
                            ),
                        },
                        {
                            'domain_id': 'semiclassical_qft_target_phase_bit',
                            'owner_id': 'phase_shell_live_register',
                            'wire_template': 'semiclassical_qft_live_phase_bit',
                            'operand_index_min': 0,
                            'operand_index_max_exclusive': 1,
                            'role': 'phase_shell_target_qubit',
                            **_parent_wire_domain(
                                parent_wire_ids=['semiclassical_qft_live_phase_bit'],
                                parent_bit_width=1,
                                parent_selection_rule='single live semiclassical phase bit',
                            ),
                        },
                    ]
                else:
                    operand_domains = [
                        {
                            'domain_id': 'semiclassical_qft_live_phase_bit',
                            'owner_id': 'phase_shell_live_register',
                            'wire_template': 'semiclassical_qft_live_phase_bit',
                            'operand_index_min': 0,
                            'operand_index_max_exclusive': 1,
                            'role': 'phase_shell_live_qubit',
                            **_parent_wire_domain(
                                parent_wire_ids=['semiclassical_qft_live_phase_bit'],
                                parent_bit_width=1,
                                parent_selection_rule='single live semiclassical phase bit',
                            ),
                        }
                    ]
                provenance = {
                    'phase_shell': phase_shell['name'],
                    'stage': stage['name'],
                    'block': block['name'],
                    'gate': gate,
                    'count': int(count),
                }
                contract = _primitive_operand_contract(
                    scope='phase_shell',
                    gate=gate,
                    source_kind='phase_shell_lowering',
                    source_digest=_sha256_payload(provenance),
                    operand_domains=operand_domains,
                )
                rows.append({
                    'row_index': row_index + len(rows),
                    'scope': 'phase_shell',
                    'source': f"{phase_shell['name']}:{stage['name']}:{block['name']}",
                    'gate': gate,
                    'instance_count': int(count),
                    'total_count': int(count),
                    'non_clifford_count': 0,
                    'provenance_sha256': _sha256_payload(provenance),
                    'primitive_operand_contract': contract,
                    'primitive_operand_contract_sha256': _sha256_payload(contract),
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
                provenance = {
                    'term_id': term['term_id'],
                    'term_instance_index': instance_index,
                    'segment': segment,
                }
                contract = _primitive_operand_contract(
                    scope='qroam_chunk_stream',
                    gate='ccx',
                    source_kind='qroam_primitive_certificate',
                    source_digest=str(segment['sha256']),
                    operand_domains=[
                        {
                            'domain_id': f"{term['table']}:chunk_{term['chunk_index']}:qroam_selection_control",
                            'owner_id': 'lookup_workspace',
                            'wire_template': f"qroam_selection_control__{term['table']}__chunk_{term['chunk_index']}.bit[{{operand_index}}]",
                            'operand_index_min': int(segment['start_address']),
                            'operand_index_max_exclusive': int(segment['end_address_exclusive']),
                            'role': 'qroam_selection_control',
                            **_parent_wire_domain(
                                parent_wire_ids=['folded_lookup_control_workspace'],
                                parent_bit_width=18,
                                parent_selection_rule='folded QROAM selection controls reuse counted folded lookup-control workspace bits',
                            ),
                        },
                        {
                            'domain_id': f"{term['table']}:chunk_{term['chunk_index']}:qroam_target",
                            'owner_id': 'lookup_workspace',
                            'wire_template': f"qroam_chunk_target__{term['table']}__chunk_{term['chunk_index']}.bit[{{operand_index}}]",
                            'operand_index_min': int(segment['start_address']),
                            'operand_index_max_exclusive': int(segment['end_address_exclusive']),
                            'role': 'qroam_target_or_unary_step',
                            **_parent_wire_domain(
                                parent_wire_ids=[f"qroam_chunk_target__{term['table']}__chunk_{term['chunk_index']}"],
                                parent_bit_width=int(qroam_primitive_certificate['parameters']['target_bits']),
                                parent_selection_rule='selected QROAM target bit = operand offset modulo target_bits',
                            ),
                        },
                        {
                            'domain_id': 'qchunk',
                            'owner_id': 'arithmetic_slot_register_file',
                            'wire_template': 'qchunk.bit[{operand_index}]',
                            'operand_index_min': 0,
                            'operand_index_max_exclusive': int(reusable_chunk_lowering['stream_plan']['chunk_bits']),
                            'role': 'qroam_chunk_consumer_register',
                            **_parent_wire_domain(
                                parent_wire_ids=['qchunk'],
                                parent_bit_width=int(reusable_chunk_lowering['stream_plan']['chunk_bits']),
                                parent_selection_rule='qchunk consumer bit = operand offset modulo chunk_bits',
                            ),
                        },
                    ],
                )
                rows.append({
                    'row_index': row_index + len(rows),
                    'scope': 'qroam_chunk_stream',
                    'source': f"{term['term_id']}:{instance_index}:{segment['phase']}:{segment['start_address']}-{segment['end_address_exclusive']}",
                    'gate': 'ccx',
                    'instance_count': int(segment['operation_count']),
                    'total_count': int(segment['operation_count']),
                    'non_clifford_count': int(segment['ccx']),
                    'provenance_sha256': _sha256_payload(provenance),
                    'primitive_operand_contract': contract,
                    'primitive_operand_contract_sha256': _sha256_payload(contract),
                    'term_id': str(term['term_id']),
                    'term_instance_index': instance_index,
                    'table': str(term['table']),
                    'chunk_index': int(term['chunk_index']),
                    'qroam_phase': str(segment['phase']),
                    'qroam_segment_sha256': str(segment['sha256']),
                })
    return rows


def _count_rows_from_primitive_counts(
    *,
    row_index: int,
    scope: str,
    source: str,
    primitive_counts: Mapping[str, Any],
    provenance_payload: Mapping[str, Any],
    operand_domains: List[Mapping[str, Any]] | Mapping[str, List[Mapping[str, Any]]],
    source_kind: str,
    extra: Optional[Mapping[str, Any]] = None,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for gate, count in sorted(primitive_counts.items()):
        gate_count = int(count)
        if gate_count == 0:
            continue
        provenance = {
            **provenance_payload,
            'gate': gate,
            'count': gate_count,
        }
        provenance_sha256 = _sha256_payload(provenance)
        contract = _primitive_operand_contract(
            scope=scope,
            gate=str(gate),
            source_kind=source_kind,
            source_digest=provenance_sha256,
            operand_domains=operand_domains[str(gate)] if isinstance(operand_domains, dict) else operand_domains,
        )
        rows.append({
            'row_index': row_index + len(rows),
            'scope': scope,
            'source': source,
            'gate': str(gate),
            'instance_count': gate_count,
            'total_count': gate_count,
            'non_clifford_count': gate_count if gate == 'ccx' else 0,
            'provenance_sha256': provenance_sha256,
            'primitive_operand_contract': contract,
            'primitive_operand_contract_sha256': _sha256_payload(contract),
            **dict(extra or {}),
        })
    return rows


def _selected_lookup_family(lookup_lowerings: Mapping[str, Any], selected_name: str) -> Mapping[str, Any]:
    return next(row for row in lookup_lowerings['families'] if row['name'] == selected_name)


def _selected_arithmetic_kernel(arithmetic_operation_ir: Mapping[str, Any]) -> Mapping[str, Any]:
    leaf_rows = arithmetic_operation_ir['leaf_arithmetic_summary']['rows']
    if len(leaf_rows) != 1:
        raise ValueError('public materialized candidate expects one arithmetic leaf kernel')
    opcode = str(leaf_rows[0]['opcode'])
    return next(row for row in arithmetic_operation_ir['kernels'] if row['opcode'] == opcode)


def _public_base_run_length_rows(
    *,
    reusable_chunk_lowering: Mapping[str, Any],
    arithmetic_operation_ir: Mapping[str, Any],
    lookup_lowerings: Mapping[str, Any],
    compiler_parameters: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    lookup_family = _selected_lookup_family(
        lookup_lowerings,
        str(compiler_parameters['lookup_policy']['selected_public_lookup_family']),
    )
    arithmetic_kernel = _selected_arithmetic_kernel(arithmetic_operation_ir)
    leaf_call_count = int(reusable_chunk_lowering['stream_plan']['leaf_call_count_total'])
    lookup_operand_domains = [
        {
            'domain_id': 'folded_lookup_control_workspace',
            'owner_id': 'lookup_workspace',
            'wire_template': 'folded_lookup_control_workspace.bit[{operand_index}]',
            'operand_index_min': 0,
            'operand_index_max_exclusive': 18,
            'role': 'folded_lookup_decode_control',
            **_parent_wire_domain(
                parent_wire_ids=['folded_lookup_control_workspace'],
                parent_bit_width=18,
                parent_selection_rule='folded lookup-control bit = operand offset modulo 18',
            ),
        },
        {
            'domain_id': 'lookup_conditioned_arithmetic_slots',
            'owner_id': 'arithmetic_slot_register_file',
            'wire_template': 'qx_qy_qz.bit[{operand_index}]',
            'operand_index_min': 0,
            'operand_index_max_exclusive': 768,
            'role': 'lookup_infinity_and_conditional_y_negation_target',
            **_parent_wire_domain(
                parent_wire_ids=['qx', 'qy', 'qz'],
                parent_bit_width=256,
                parent_selection_rule='parent_wire_index = operand_index // field_bits; parent_bit_index = operand_index % field_bits',
            ),
        },
        {
            'domain_id': 'lookup_infinity_flag',
            'owner_id': 'control_slot_register_file',
            'wire_template': 'f_lookup_inf',
            'operand_index_min': 0,
            'operand_index_max_exclusive': 1,
            'role': 'lookup_boundary_control_flag',
            **_parent_wire_domain(
                parent_wire_ids=['f_lookup_inf'],
                parent_bit_width=1,
                parent_selection_rule='single lookup infinity flag bit',
            ),
        },
    ]
    lookup_operand_domains_by_gate = {
        'ccx': lookup_operand_domains,
        'measurement': [
            {
                'domain_id': 'lookup_measurement_workspace_bits',
                'owner_id': 'lookup_workspace',
                'wire_template': 'folded_lookup_control_workspace.measurement.bit[{operand_index}]',
                'operand_index_min': 0,
                'operand_index_max_exclusive': int(lookup_family['primitive_counts_total']['measurement']),
                'role': 'lookup_measurement_bit',
                **_parent_wire_domain(
                    parent_wire_ids=['folded_lookup_control_workspace'],
                    parent_bit_width=18,
                    parent_selection_rule='lookup measurement bits reuse counted folded lookup-control workspace bits',
                ),
            }
        ],
    }
    rows: List[Dict[str, Any]] = []
    rows.extend(_count_rows_from_primitive_counts(
        row_index=len(rows),
        scope='direct_seed_base',
        source=f"lookup_lowerings:{lookup_family['name']}:direct_seed",
        primitive_counts=lookup_family['primitive_counts_total'],
        provenance_payload={
            'lookup_family': lookup_family['name'],
            'usage': 'direct_seed',
            'primitive_counts_total': lookup_family['primitive_counts_total'],
        },
        operand_domains=lookup_operand_domains_by_gate,
        source_kind='lookup_lowering',
    ))
    for leaf_call_index in range(leaf_call_count):
        rows.extend(_count_rows_from_primitive_counts(
            row_index=len(rows),
            scope='lookup_leaf_base',
            source=f"lookup_lowerings:{lookup_family['name']}:leaf_call_{leaf_call_index}",
            primitive_counts=lookup_family['primitive_counts_total'],
            provenance_payload={
                'lookup_family': lookup_family['name'],
                'usage': 'leaf_lookup_base',
                'leaf_call_index': leaf_call_index,
                'primitive_counts_total': lookup_family['primitive_counts_total'],
            },
            operand_domains=lookup_operand_domains_by_gate,
            source_kind='lookup_lowering',
            extra={'leaf_call_index': leaf_call_index},
        ))
        for stage in arithmetic_kernel['stages']:
            if stage['category'] == 'streamed_lookup_data_select':
                continue
            for block in stage['blocks']:
                rows.extend(_count_rows_from_primitive_counts(
                    row_index=len(rows),
                    scope='arithmetic_leaf_block',
                    source=f"arithmetic_operation_ir:{arithmetic_kernel['opcode']}:{stage['stage']}:{block['block']}:leaf_call_{leaf_call_index}",
                    primitive_counts=block['primitive_counts_total'],
                    provenance_payload={
                        'arithmetic_kernel': arithmetic_kernel['opcode'],
                        'leaf_call_index': leaf_call_index,
                        'stage': stage['stage'],
                        'stage_category': stage['category'],
                        'block': block['block'],
                        'operation_start': int(block['operation_start']),
                        'operation_end_exclusive': int(block['operation_end_exclusive']),
                        'operation_stream_sha256': block['operation_stream_sha256'],
                        'primitive_counts_total': block['primitive_counts_total'],
                        'operand_profile': block['operand_profile'],
                    },
                    operand_domains={
                        gate: _arithmetic_block_operand_domains(stage, block, gate)
                        for gate, count in block['primitive_counts_total'].items()
                        if int(count) > 0
                    },
                    source_kind='arithmetic_operation_ir',
                    extra={
                        'leaf_call_index': leaf_call_index,
                        'arithmetic_stage': str(stage['stage']),
                        'arithmetic_block': str(block['block']),
                        'arithmetic_category': str(stage['category']),
                    },
                ))
    for row_index, row in enumerate(rows):
        row['row_index'] = row_index
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
    direct_seed_interval_id = 'pc4_lookup_infinity_flag'
    phase_interval_id = 'pc0_2_load_carried_inputs'
    wire_catalog = reusable_chunk_lowering['executable_liveness']['wire_catalog']
    owner_capacity_by_id = {
        str(row['owner_id']): int(row['logical_qubits'])
        for row in reusable_chunk_lowering['owner_capacity']['rows']
    }
    rows: List[Dict[str, Any]] = []
    for operation in operation_rows:
        if operation['scope'] == 'qroam_chunk_stream':
            interval_id = qroam_interval_by_chunk[(str(operation['table']), int(operation['chunk_index']))]
        elif operation['scope'] in ('direct_seed_base', 'lookup_leaf_base'):
            interval_id = direct_seed_interval_id
        elif operation['scope'] == 'phase_shell':
            interval_id = phase_interval_id
        else:
            interval_id = peak_interval_id
        interval = intervals[interval_id]
        live_wire_ids = [str(wire_id) for wire_id in interval['live_wire_ids']]
        derived_owner_live_qubits: Dict[str, int] = {}
        for wire_id in live_wire_ids:
            wire = wire_catalog[wire_id]
            owner_id = str(wire['owner_id'])
            derived_owner_live_qubits[owner_id] = derived_owner_live_qubits.get(owner_id, 0) + int(wire['qubits'])
        rows.append({
            'row_index': int(operation['row_index']),
            'scope': str(operation['scope']),
            'interval_id': interval_id,
            'live_wire_ids': live_wire_ids,
            'owner_live_qubits': {
                owner_id: int(qubits)
                for owner_id, qubits in sorted(interval['owner_live_qubits'].items())
            },
            'derived_owner_live_qubits': {
                owner_id: int(qubits)
                for owner_id, qubits in sorted(derived_owner_live_qubits.items())
            },
            'total_live_qubits': int(interval['total_live_qubits']),
            'owner_capacity_pass': all(
                int(qubits) <= owner_capacity_by_id[owner_id]
                for owner_id, qubits in derived_owner_live_qubits.items()
            ),
        })
    return rows


def build_public_candidate_materialized_circuit_manifest(
    *,
    reusable_chunk_lowering: Mapping[str, Any],
    arithmetic_operation_ir: Mapping[str, Any],
    lookup_lowerings: Mapping[str, Any],
    qroam_primitive_certificate: Mapping[str, Any],
    phase_shell_lowerings: Mapping[str, Any],
    compiler_parameters: Mapping[str, Any],
    selected_family_name: str,
) -> Dict[str, Any]:
    counted_resource_ir = reusable_chunk_lowering['counted_resource_ir']
    public_totals = reusable_chunk_lowering['executable_resource_engine']['public_totals']
    selected_phase_shell_name = str(compiler_parameters['phase_shell']['selected_public_shell'])
    selected_phase_shell = _selected_phase_shell(phase_shell_lowerings, selected_phase_shell_name)
    base_non_clifford = int(reusable_chunk_lowering['non_clifford_derivation']['base_non_clifford_without_streamed_qroam'])
    rows = _public_base_run_length_rows(
        reusable_chunk_lowering=reusable_chunk_lowering,
        arithmetic_operation_ir=arithmetic_operation_ir,
        lookup_lowerings=lookup_lowerings,
        compiler_parameters=compiler_parameters,
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
    flat_netlist = _flat_netlist_commitment(
        operation_rows=rows,
        liveness_rows=liveness_rows,
    )
    materialized_public_totals = {
        'non_clifford': int(flat_netlist['non_clifford_count']),
        'logical_qubits': max(int(row['total_live_qubits']) for row in liveness_rows),
    }
    base_rows = [row for row in rows if row['scope'] in ('direct_seed_base', 'lookup_leaf_base', 'arithmetic_leaf_block')]
    direct_seed_rows = [row for row in rows if row['scope'] == 'direct_seed_base']
    lookup_leaf_rows = [row for row in rows if row['scope'] == 'lookup_leaf_base']
    arithmetic_leaf_rows = [row for row in rows if row['scope'] == 'arithmetic_leaf_block']
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
    selected_lookup_family = _selected_lookup_family(
        lookup_lowerings,
        str(compiler_parameters['lookup_policy']['selected_public_lookup_family']),
    )
    selected_arithmetic_kernel = _selected_arithmetic_kernel(arithmetic_operation_ir)
    leaf_call_count = int(reusable_chunk_lowering['stream_plan']['leaf_call_count_total'])
    arithmetic_generated_non_qroam_per_leaf = sum(
        int(stage['primitive_counts_total']['ccx'])
        for stage in selected_arithmetic_kernel['stages']
        if stage['category'] != 'streamed_lookup_data_select'
    )
    arithmetic_generated_streamed_qroam_per_leaf = sum(
        int(stage['primitive_counts_total']['ccx'])
        for stage in selected_arithmetic_kernel['stages']
        if stage['category'] == 'streamed_lookup_data_select'
    )
    lookup_base_non_clifford_per_leaf = int(selected_lookup_family['primitive_counts_total']['ccx'])
    owner_capacity_by_id = {
        str(row['owner_id']): int(row['logical_qubits'])
        for row in reusable_chunk_lowering['owner_capacity']['rows']
    }
    wire_catalog = reusable_chunk_lowering['executable_liveness']['wire_catalog']
    flat_execution_probe = _flat_execution_probe(
        rows=rows,
        liveness_rows=liveness_rows,
        flat_netlist=flat_netlist,
        owner_capacity_by_id=owner_capacity_by_id,
        wire_catalog=wire_catalog,
    )
    strict_primitive_completeness = _strict_primitive_completeness_report(rows)
    operand_parent_binding = _operand_parent_binding_report(
        rows=rows,
        liveness_rows=liveness_rows,
        wire_catalog=wire_catalog,
    )
    checks = {
        'selected_family_matches_compiler_parameters': selected_family_name == compiler_parameters['public_headline_policy']['selected_public_family_name'],
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
        'generated_base_rows_match_public_non_qroam_derivation': (
            sum(int(row['non_clifford_count']) for row in direct_seed_rows) == lookup_base_non_clifford_per_leaf
            and sum(int(row['non_clifford_count']) for row in lookup_leaf_rows) == lookup_base_non_clifford_per_leaf * leaf_call_count
            and sum(int(row['non_clifford_count']) for row in arithmetic_leaf_rows) == arithmetic_generated_non_qroam_per_leaf * leaf_call_count
            and sum(int(row['non_clifford_count']) for row in base_rows) == base_non_clifford
        ),
        'arithmetic_rows_exclude_replaced_streamed_qroam_stages': (
            arithmetic_generated_streamed_qroam_per_leaf > 0
            and not any(row.get('arithmetic_category') == 'streamed_lookup_data_select' for row in arithmetic_leaf_rows)
        ),
        'generated_base_rows_bind_compiler_parameters': (
            'reusable_chunk_tail_leaf_v1' in selected_family_name
            and sum(int(row['non_clifford_count']) for row in direct_seed_rows) == lookup_base_non_clifford_per_leaf
            and lookup_base_non_clifford_per_leaf > 0
            and arithmetic_generated_non_qroam_per_leaf > 0
        ),
        'phase_rows_bind_selected_phase_shell': (
            selected_phase_shell['name'] in selected_family_name
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
        'liveness_bindings_have_unique_live_wires': all(
            len(liveness['live_wire_ids']) == len(set(liveness['live_wire_ids']))
            for liveness in liveness_rows
        ),
        'liveness_bindings_recompute_owner_sums_from_wire_catalog': all(
            liveness['derived_owner_live_qubits'] == liveness['owner_live_qubits']
            and sum(int(qubits) for qubits in liveness['derived_owner_live_qubits'].values()) == int(liveness['total_live_qubits'])
            for liveness in liveness_rows
        ),
        'liveness_bindings_recompute_owner_capacity_from_wire_catalog': all(
            liveness['owner_capacity_pass'] is True
            and all(int(qubits) <= owner_capacity_by_id[owner_id] for owner_id, qubits in liveness['derived_owner_live_qubits'].items())
            for liveness in liveness_rows
        ),
        'liveness_bindings_reconstruct_public_peak': materialized_public_totals['logical_qubits'] == int(public_totals['logical_qubits']),
        'flat_netlist_expands_all_run_length_rows': (
            flat_netlist['operation_count'] == sum(int(row['total_count']) for row in rows)
            and sum(int(segment['operation_count']) for segment in flat_netlist['segments']) == flat_netlist['operation_count']
            and flat_netlist['segments'][0]['operation_start'] == 0
            and flat_netlist['segments'][-1]['operation_end_exclusive'] == flat_netlist['operation_count']
        ),
        'flat_netlist_gate_totals_match_run_length_rows': flat_netlist['gate_totals'] == gate_totals,
        'flat_netlist_non_clifford_matches_public_candidate': materialized_public_totals['non_clifford'] == int(public_totals['non_clifford']),
        'primitive_operand_contracts_cover_all_run_length_rows': all(
            row['primitive_operand_contract']['schema'] == 'compiler-project-primitive-operand-contract-v1'
            and row['primitive_operand_contract']['gate'] == row['gate']
            and row['primitive_operand_contract_sha256'] == _sha256_payload(row['primitive_operand_contract'])
            for row in rows
        ),
        'primitive_operand_contract_owners_are_known_and_live': all(
            all(owner_id in owner_capacity_by_id for owner_id in row['primitive_operand_contract']['owner_ids'])
            and set(row['primitive_operand_contract']['owner_ids']).issubset(set(liveness_rows[int(row['row_index'])]['derived_owner_live_qubits']))
            for row in rows
        ),
        'primitive_operand_domains_bind_counted_live_parent_wires': operand_parent_binding['pass'] is True,
        'flat_netlist_binds_operand_contract_hashes': all(
            contribution['primitive_operand_contract_sha256'] == rows[int(contribution['run_length_row_index'])]['primitive_operand_contract_sha256']
            and contribution['primitive_operand_owner_ids'] == rows[int(contribution['run_length_row_index'])]['primitive_operand_contract']['owner_ids']
            for segment in flat_netlist['segments']
            for contribution in segment['contributions']
        ),
        'flat_execution_probe_operations_bind_segment_contributions': flat_execution_probe['checks']['probe_operations_bind_segment_contributions'] is True,
        'flat_execution_probe_operand_indices_within_domains': flat_execution_probe['checks']['probe_operand_indices_within_domains'] is True,
        'flat_execution_probe_operand_owners_are_live_and_within_capacity': flat_execution_probe['checks']['probe_operand_owners_are_live_and_within_capacity'] is True,
        'flat_execution_probe_reduced_schoolbook_grid_executes': flat_execution_probe['checks']['reduced_schoolbook_operand_grid_executes_cartesian_prefix'] is True,
        'flat_execution_probe_qroam_target_width_matches_segments': flat_execution_probe['checks']['qroam_target_domain_width_matches_each_stream_segment'] is True,
        'flat_execution_probe_arithmetic_two_operand_domains_match_rows': flat_execution_probe['checks']['arithmetic_two_operand_domain_product_matches_row_total'] is True,
        'strict_primitive_completeness_report_is_current': (
            strict_primitive_completeness['rows_checked'] == len(rows)
            and sum(strict_primitive_completeness['rows_by_gate'].values()) == len(rows)
            and strict_primitive_completeness['clifford_complete'] is True
        ),
        'operand_parent_binding_report_is_current': (
            operand_parent_binding['rows_checked'] == len(rows)
            and operand_parent_binding['domains_checked'] == sum(len(row['primitive_operand_contract']['operand_domains']) for row in rows)
            and operand_parent_binding['pass'] is True
        ),
        'qroam_liveness_bindings_use_matching_chunk_target': all(
            f"qroam_chunk_target__{row['table']}__chunk_{row['chunk_index']}" in liveness_rows[int(row['row_index'])]['live_wire_ids']
            for row in qroam_rows
        ),
        'direct_seed_liveness_excludes_qroam_target_and_chunk': all(
            not any(str(wire_id).startswith('qroam_chunk_target__') or wire_id == 'qchunk' for wire_id in liveness_rows[int(row['row_index'])]['live_wire_ids'])
            for row in rows
            if row['scope'] == 'direct_seed_base'
        ),
        'lookup_leaf_liveness_excludes_qroam_target_and_chunk': all(
            not any(str(wire_id).startswith('qroam_chunk_target__') or wire_id == 'qchunk' for wire_id in liveness_rows[int(row['row_index'])]['live_wire_ids'])
            for row in lookup_leaf_rows
        ),
        'phase_liveness_uses_phase_load_interval_without_lookup_target': all(
            'semiclassical_qft_live_phase_bit' in liveness_rows[int(row['row_index'])]['live_wire_ids']
            and not any(str(wire_id).startswith('qroam_chunk_target__') for wire_id in liveness_rows[int(row['row_index'])]['live_wire_ids'])
            for row in phase_rows
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
            'lookup_lowerings_sha256': _sha256_payload(lookup_lowerings),
            'qroam_primitive_certificate_sha256': _sha256_payload(qroam_primitive_certificate),
            'phase_shell_lowerings_sha256': _sha256_payload(phase_shell_lowerings),
            'compiler_parameters_sha256': _sha256_payload(compiler_parameters),
        },
        'operation_stream_sha256': _public_candidate_stream_hash(rows),
        'liveness_binding_stream_sha256': _public_candidate_liveness_hash(liveness_rows),
        'run_length_row_count': len(rows),
        'liveness_binding_row_count': len(liveness_rows),
        'base_row_count': len(base_rows),
        'direct_seed_row_count': len(direct_seed_rows),
        'lookup_leaf_base_row_count': len(lookup_leaf_rows),
        'arithmetic_leaf_block_row_count': len(arithmetic_leaf_rows),
        'qroam_segment_row_count': len(qroam_rows),
        'phase_row_count': len(phase_rows),
        'gate_totals': gate_totals,
        'run_length_rows': rows,
        'public_totals': {
            **materialized_public_totals,
            'source': 'public_candidate_materialized.flat_netlist.non_clifford_count + materialized_liveness.peak_live_qubits',
        },
        'materialized_liveness': {
            'peak_live_qubits': materialized_public_totals['logical_qubits'],
            'peak_interval_ids': sorted({
                str(row['interval_id'])
                for row in liveness_rows
                if int(row['total_live_qubits']) == materialized_public_totals['logical_qubits']
            }),
            'owner_capacity_qubits': owner_capacity_by_id,
            'rows': liveness_rows,
            'preview_head': liveness_rows[:8],
            'preview_tail': liveness_rows[-8:],
        },
        'flat_netlist': flat_netlist,
        'flat_execution_probe': flat_execution_probe,
        'strict_primitive_completeness': strict_primitive_completeness,
        'operand_parent_binding': operand_parent_binding,
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
            'selected_kernel': selected_arithmetic_kernel['opcode'],
            'selected_kernel_stage_digest_sha256': selected_arithmetic_kernel['stage_digest_sha256'],
            'generated_non_qroam_non_clifford_per_leaf': arithmetic_generated_non_qroam_per_leaf,
            'replaced_streamed_qroam_non_clifford_per_leaf': arithmetic_generated_streamed_qroam_per_leaf,
            'expanded_block_rows': len(arithmetic_leaf_rows),
        },
        'lookup_base_evidence': {
            'name': selected_lookup_family['name'],
            'primitive_counts_total': {
                key: int(value)
                for key, value in sorted(selected_lookup_family['primitive_counts_total'].items())
            },
            'direct_seed_non_clifford': sum(int(row['non_clifford_count']) for row in direct_seed_rows),
            'per_leaf_base_non_clifford': lookup_base_non_clifford_per_leaf,
            'expanded_leaf_rows': len(lookup_leaf_rows),
        },
        'preview_head': rows[:8],
        'preview_tail': rows[-8:],
        'checks': checks,
        'pass': all(checks.values()),
        'boundary': [
            'This artifact defines the canonical flat operation-index netlist for the current public candidate with run-length contributions, liveness, and owner bindings.',
            'The flat_execution_probe section is generated by executing representative operation indices through the same expandable flat-netlist API used for the full stream.',
            'strict_primitive_completeness requires every row to expose arity-correct primitive operand domains so the flat-netlist iterator emits exact operand references for each primitive operation.',
            'It is intentionally stored as an expandable segmented commitment rather than a checked-in multi-gigabyte TSV with one physical line per primitive instruction.',
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
    'PRIMITIVE_GATE_ARITY',
    'PUBLIC_CANDIDATE_MATERIALIZED_CIRCUIT_MANIFEST_SCHEMA',
    'available_family_names',
    'build_materialized_family_manifest',
    'build_public_candidate_materialized_circuit_manifest',
    'iter_public_candidate_flat_netlist',
    'iter_family_operation_stream',
    'resolve_selected_family_names',
    'write_public_candidate_flat_netlist',
    'write_materialized_family_circuit',
]
