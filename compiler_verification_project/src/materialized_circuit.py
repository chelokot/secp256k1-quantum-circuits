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
from qroam_table_cnot_materialization import decode_segment_emitted_cx
from public_engine_contract import (
    CANONICAL_FLAT_NETLIST_IS_STRICT_REPLAY_CHECK,
    CANONICAL_MATERIALIZED_FLAT_NETLIST,
    LEGACY_WRAPPER_MATERIALIZED_FLAT_NETLIST,
    PUBLIC_CANDIDATE_CANONICAL_TOTALS_SOURCE,
    PUBLIC_TOTALS_DERIVE_FROM_CANONICAL_CHECK,
    STRICT_REPLAYED_TAIL_MATERIALIZED_FLAT_NETLIST,
)


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
CANONICAL_PHYSICAL_FLAT_NETLIST_COLUMNS = [
    'operation_index',
    'contribution_kind',
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
PUBLIC_CANDIDATE_MATERIALIZED_FLAT_NETLIST_COLUMNS = [
    'operation_index',
    'run_length_row_index',
    'row_instance_ordinal',
    'scope',
    'source',
    'gate',
    'operand_0_wire',
    'operand_0_owner',
    'operand_0_role',
    'operand_0_parent_wire',
    'operand_0_parent_bit',
    'operand_1_wire',
    'operand_1_owner',
    'operand_1_role',
    'operand_1_parent_wire',
    'operand_1_parent_bit',
    'operand_2_wire',
    'operand_2_owner',
    'operand_2_role',
    'operand_2_parent_wire',
    'operand_2_parent_bit',
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


def _arithmetic_parent_domain(parent_wire_ids: List[str], parent_bit_offsets: Optional[Mapping[str, int]] = None) -> Dict[str, Any]:
    return _parent_wire_domain(
        parent_wire_ids=parent_wire_ids,
        parent_bit_width=256,
        parent_selection_rule='parent_wire_index = operand_index // parent_bit_width; parent_bit_index = operand_index % parent_bit_width',
    ) | {
        'parent_bit_offsets': {
            str(wire_id): int(offset)
            for wire_id, offset in dict(parent_bit_offsets or {}).items()
        },
    }


def _arithmetic_spill_parent_domain(primary_wire_id: str, qchunk_bit_offset: int) -> Dict[str, Any]:
    return _arithmetic_parent_domain(
        [primary_wire_id, 'qchunk'],
        parent_bit_offsets={'qchunk': int(qchunk_bit_offset)},
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
                **_arithmetic_spill_parent_domain('qz', 128),
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
                **_arithmetic_spill_parent_domain('qx', 0),
            },
            {
                'domain_id': f"{stage['stage']}:{block['block']}:control_b",
                'owner_id': 'arithmetic_slot_register_file',
                'wire_template': 'arithmetic_slot_register_file.control_b.bit[{operand_index}]',
                'operand_index_min': 0,
                'operand_index_max_exclusive': operand_slots,
                'row_instance_to_operand_index': 'operand_index = row_instance_ordinal % operand_domain_width',
                'role': str(stage['category']),
                **_arithmetic_spill_parent_domain('qy', 64),
            },
            {
                'domain_id': f"{stage['stage']}:{block['block']}:target",
                'owner_id': 'arithmetic_slot_register_file',
                'wire_template': 'arithmetic_slot_register_file.target.bit[{operand_index}]',
                'operand_index_min': 0,
                'operand_index_max_exclusive': operand_slots,
                'row_instance_to_operand_index': 'operand_index = row_instance_ordinal % operand_domain_width',
                'role': str(stage['category']),
                **_arithmetic_spill_parent_domain('qz', 128),
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


def _materialized_operand_columns(operand_wires: List[Mapping[str, Any]], operand_index: int) -> List[str]:
    if operand_index >= len(operand_wires):
        return ['', '', '', '', '']
    wire = operand_wires[operand_index]
    return [
        str(wire['wire_id']),
        str(wire['owner_id']),
        str(wire['role']),
        str(wire['parent_wire_id']),
        str(wire['parent_bit_index']),
    ]


def _compact_materialized_flat_operation(row: Mapping[str, Any]) -> Dict[str, Any]:
    operand_wires = list(row['operand_wires'])
    return {
        'operation_index': int(row['operation_index']),
        'run_length_row_index': int(row['run_length_row_index']),
        'row_instance_ordinal': int(row['row_instance_ordinal']),
        'scope': str(row['scope']),
        'source': str(row['source']),
        'gate': str(row['gate']),
        'operand_wires': [
            {
                'wire_id': str(wire['wire_id']),
                'owner_id': str(wire['owner_id']),
                'role': str(wire['role']),
                'parent_wire_id': str(wire['parent_wire_id']),
                'parent_bit_index': int(wire['parent_bit_index']),
            }
            for wire in operand_wires
        ],
        'liveness_interval_id': str(row['liveness']['interval_id']),
        'total_live_qubits': int(row['liveness']['total_live_qubits']),
        'primitive_operand_contract_sha256': str(row['primitive_operand_contract_sha256']),
        'liveness_binding_sha256': str(row['liveness_binding_sha256']),
    }


def _encoded_materialized_flat_operation(row: Mapping[str, Any]) -> str:
    operand_wires = list(row['operand_wires'])
    fields: List[str] = [
        str(int(row['operation_index'])),
        str(int(row['run_length_row_index'])),
        str(int(row['row_instance_ordinal'])),
        str(row['scope']),
        str(row['source']),
        str(row['gate']),
    ]
    fields.extend(_materialized_operand_columns(operand_wires, 0))
    fields.extend(_materialized_operand_columns(operand_wires, 1))
    fields.extend(_materialized_operand_columns(operand_wires, 2))
    fields.extend([
        str(row['liveness']['interval_id']),
        str(int(row['liveness']['total_live_qubits'])),
        str(row['primitive_operand_contract_sha256']),
        str(row['liveness_binding_sha256']),
    ])
    return '\t'.join(fields) + '\n'


def _new_materialized_flat_segment_digest() -> Any:
    digest = hashlib.sha256()
    digest.update(b'compiler-project-public-candidate-materialized-flat-segment-v1\n')
    return digest


def _materialized_flat_netlist_commitment(
    *,
    operation_rows: List[Mapping[str, Any]],
    liveness_rows: List[Mapping[str, Any]],
    segment_size: int = PUBLIC_CANDIDATE_FLAT_SEGMENT_SIZE,
) -> Dict[str, Any]:
    if segment_size <= 0:
        raise ValueError('segment_size must be positive')
    stream_digest = hashlib.sha256()
    header = '\t'.join(PUBLIC_CANDIDATE_MATERIALIZED_FLAT_NETLIST_COLUMNS) + '\n'
    stream_digest.update(header.encode('ascii'))
    operation_count = 0
    non_clifford_count = 0
    peak_live_qubits = 0
    gate_totals = _empty_gate_totals()
    segment_digest = _new_materialized_flat_segment_digest()
    segment_count = 0
    segment_gate_totals = _empty_gate_totals()
    segment_non_clifford = 0
    segment_start = 0
    segments: List[Dict[str, Any]] = []
    preview_head: List[Dict[str, Any]] = []
    preview_tail_operations: List[Dict[str, Any]] = []

    for operation in iter_public_candidate_flat_netlist(operation_rows, liveness_rows):
        encoded_row = _encoded_materialized_flat_operation(operation)
        encoded_bytes = encoded_row.encode('utf-8')
        stream_digest.update(encoded_bytes)
        segment_digest.update(encoded_bytes)
        segment_count += 1
        operation_count += 1
        gate = str(operation['gate'])
        gate_totals[gate] += 1
        segment_gate_totals[gate] += 1
        if gate == 'ccx':
            non_clifford_count += 1
            segment_non_clifford += 1
        peak_live_qubits = max(peak_live_qubits, int(operation['liveness']['total_live_qubits']))
        if len(preview_head) < 4:
            preview_head.append(_compact_materialized_flat_operation(operation))
        preview_tail_operations.append(operation)
        if len(preview_tail_operations) > 4:
            preview_tail_operations.pop(0)
        if segment_count == segment_size:
            segments.append({
                'segment_index': len(segments),
                'operation_start': segment_start,
                'operation_end_exclusive': operation_count,
                'operation_count': segment_count,
                'gate_totals': segment_gate_totals,
                'non_clifford_count': segment_non_clifford,
                'sha256': segment_digest.hexdigest(),
            })
            segment_digest = _new_materialized_flat_segment_digest()
            segment_count = 0
            segment_gate_totals = _empty_gate_totals()
            segment_non_clifford = 0
            segment_start = operation_count
    if segment_count:
        segments.append({
            'segment_index': len(segments),
            'operation_start': segment_start,
            'operation_end_exclusive': operation_count,
            'operation_count': segment_count,
            'gate_totals': segment_gate_totals,
            'non_clifford_count': segment_non_clifford,
            'sha256': segment_digest.hexdigest(),
        })
    return {
        'schema': 'compiler-project-public-candidate-materialized-flat-netlist-v1',
        'definition': 'Fully materialized primitive operation stream: every primitive gate is emitted with concrete operand wires and row liveness, and totals are derived by scanning this stream.',
        'columns': PUBLIC_CANDIDATE_MATERIALIZED_FLAT_NETLIST_COLUMNS,
        'exact_operation_stream_materialized': True,
        'segment_size': segment_size,
        'operation_count': operation_count,
        'segment_count': len(segments),
        'operation_stream_sha256': stream_digest.hexdigest(),
        'segment_merkle_root_sha256': _merkle_root([segment['sha256'] for segment in segments]),
        'gate_totals': gate_totals,
        'non_clifford_count': non_clifford_count,
        'peak_live_qubits': peak_live_qubits,
        'segments': segments,
        'preview_head': preview_head,
        'preview_tail': [
            _compact_materialized_flat_operation(operation)
            for operation in preview_tail_operations
        ],
    }


def _omitted_materialized_flat_netlist_summary(
    *,
    flat_netlist: Mapping[str, Any],
    liveness_rows: List[Mapping[str, Any]],
) -> Dict[str, Any]:
    return {
        'schema': 'compiler-project-public-candidate-materialized-flat-netlist-v1',
        'definition': 'Full primitive operation stream materialization was intentionally skipped for a lightweight mutation/unit build.',
        'columns': PUBLIC_CANDIDATE_MATERIALIZED_FLAT_NETLIST_COLUMNS,
        'exact_operation_stream_materialized': False,
        'operation_count': int(flat_netlist['operation_count']),
        'segment_count': int(flat_netlist['segment_count']),
        'operation_stream_sha256': '',
        'segment_merkle_root_sha256': '',
        'gate_totals': dict(flat_netlist['gate_totals']),
        'non_clifford_count': int(flat_netlist['non_clifford_count']),
        'peak_live_qubits': max(int(row['total_live_qubits']) for row in liveness_rows),
        'segments': [],
        'preview_head': [],
        'preview_tail': [],
    }


def _wire_from_domain(domain: Mapping[str, Any], operand_index: int, row_instance_ordinal: int) -> Dict[str, Any]:
    parent_wire_ids = [str(wire_id) for wire_id in domain.get('parent_wire_ids', [])]
    parent_bit_width = int(domain.get('parent_bit_width', 0))
    parent_bit_offsets = {
        str(wire_id): int(offset)
        for wire_id, offset in dict(domain.get('parent_bit_offsets', {})).items()
    }
    if parent_wire_ids and parent_bit_width > 0:
        parent_offset = max(0, int(operand_index) - int(domain['operand_index_min']))
        parent_wire_id = parent_wire_ids[(parent_offset // parent_bit_width) % len(parent_wire_ids)]
        parent_bit_index = (parent_offset % parent_bit_width) + parent_bit_offsets.get(parent_wire_id, 0)
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
        'logical_operand_index': int(operand_index),
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
            operand_index = domain_min + ((int(row_instance_ordinal) % (domain_width * domain_width)) // domain_width)
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


def _base_point_from_table_manifests(raw32_call: Mapping[str, Any], table_manifests: Mapping[str, Any]) -> tuple[int, int]:
    phase_register = str(raw32_call['phase_register'])
    window_index = int(raw32_call['window_index_within_register'])
    if phase_register == 'phase_a':
        row = table_manifests['phase_a_bases'][window_index]
    elif phase_register == 'phase_b':
        row = table_manifests['phase_b_bases'][window_index]
    else:
        raise KeyError(f'unknown phase register: {phase_register}')
    return int(str(row['base_x_hex']), 16), int(str(row['base_y_hex']), 16)


def _qroam_table_cnot_operand_wires(
    *,
    extension: Mapping[str, Any],
    decoded: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    table = str(extension['table'])
    chunk_index = int(extension['chunk_index'])
    address = int(decoded['address'])
    target_bit_index = int(decoded['target_bit_index'])
    target_parent = f'qroam_chunk_target__{table}__chunk_{chunk_index}'
    return [
        {
            'domain_id': f'{table}:chunk_{chunk_index}:qroam_table_cnot_control',
            'owner_id': 'lookup_workspace',
            'role': 'qroam_table_cnot_control',
            'operand_index': address,
            'parent_wire_id': 'folded_lookup_control_workspace',
            'parent_bit_index': address % 18,
            'wire_id': str(decoded['control_wire']),
        },
        {
            'domain_id': f'{table}:chunk_{chunk_index}:qroam_table_cnot_target',
            'owner_id': 'lookup_workspace',
            'role': 'qroam_table_cnot_target',
            'operand_index': target_bit_index,
            'parent_wire_id': target_parent,
            'parent_bit_index': target_bit_index,
            'wire_id': f'{target_parent}.bit[{target_bit_index}]',
        },
    ]


def _qroam_segment_by_extension_key(qroam_table_cnot_materialization: Mapping[str, Any]) -> Dict[tuple[Any, ...], Mapping[str, Any]]:
    return {
        (
            int(segment['call_index']),
            str(segment['table']),
            int(segment['chunk_index']),
            str(segment['phase']),
            int(segment['start_address']),
            int(segment['end_address_exclusive']),
        ): segment
        for segment in qroam_table_cnot_materialization['segments']
    }


def iter_canonical_physical_flat_netlist(
    manifest: Mapping[str, Any],
    *,
    table_manifests: Mapping[str, Any],
    raw32_schedule: Mapping[str, Any],
    qroam_table_cnot_materialization: Mapping[str, Any],
    start: int = 0,
    stop: Optional[int] = None,
) -> Iterator[Dict[str, Any]]:
    if start < 0:
        raise ValueError('start must be non-negative')
    stop_index = None if stop is None else int(stop)
    raw32_call_by_index = {
        int(call['call_index']): call
        for call in raw32_schedule['leaf_calls']
    }
    qroam_segment_by_key = _qroam_segment_by_extension_key(qroam_table_cnot_materialization)
    qroam_extension_by_row_index = {
        int(row['run_length_row_index']): row
        for row in manifest['qroam_table_cnot_flat_extension']['rows']
    }
    liveness_by_row_index = {
        int(row['row_index']): row
        for row in manifest['strict_replayed_tail_liveness_projection']['rows']
    }
    operation_index = 0
    for row in manifest['run_length_rows']:
        row_index = int(row['row_index'])
        row_total = int(row['total_count'])
        row_start = operation_index
        row_end = row_start + row_total
        requested_stop = row_end if stop_index is None else min(stop_index, row_end)
        if requested_stop > start and row_total > 0:
            local_start = max(int(start), row_start) - row_start
            local_stop = requested_stop - row_start
            liveness = liveness_by_row_index[row_index]
            for row_instance_ordinal in range(local_start, local_stop):
                yield {
                    'operation_index': row_start + row_instance_ordinal,
                    'contribution_kind': 'run_length_primitive_row',
                    'run_length_row_index': row_index,
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
        extension = qroam_extension_by_row_index.get(row_index)
        if extension is not None:
            emitted_cx_count = int(extension['emitted_cx_count'])
            extension_start = operation_index
            extension_end = extension_start + emitted_cx_count
            requested_extension_stop = extension_end if stop_index is None else min(stop_index, extension_end)
            if requested_extension_stop > start and emitted_cx_count > 0:
                local_start = max(int(start), extension_start) - extension_start
                local_stop = requested_extension_stop - extension_start
                segment_key = (
                    int(extension['call_index']),
                    str(extension['table']),
                    int(extension['chunk_index']),
                    str(extension['phase']),
                    int(extension['start_address']),
                    int(extension['end_address_exclusive']),
                )
                segment = qroam_segment_by_key[segment_key]
                base = _base_point_from_table_manifests(raw32_call_by_index[int(extension['call_index'])], table_manifests)
                row_liveness = liveness_by_row_index[row_index]
                liveness = {
                    'interval_id': str(row_liveness['interval_id']),
                    'live_wire_ids': list(row_liveness['live_wire_ids']),
                    'derived_owner_live_qubits': dict(row_liveness['derived_owner_live_qubits']),
                    'total_live_qubits': int(row_liveness['total_live_qubits']),
                }
                for local_index in range(local_start, local_stop):
                    decoded = decode_segment_emitted_cx(
                        segment=segment,
                        base=base,
                        local_emitted_cx_index=local_index,
                        field_bits=int(qroam_table_cnot_materialization['parameters']['field_bits']),
                        chunk_bits=int(qroam_table_cnot_materialization['parameters']['chunk_bits']),
                    )
                    yield {
                        'operation_index': extension_start + local_index,
                        'contribution_kind': 'qroam_table_cnot_indexed_row',
                        'run_length_row_index': row_index,
                        'row_instance_ordinal': local_index,
                        'scope': 'qroam_table_cnot_indexed_stream',
                        'source': 'qroam_table_cnot_materialization.row_index_contract',
                        'gate': 'cx',
                        'operand_wires': _qroam_table_cnot_operand_wires(extension=extension, decoded=decoded),
                        'liveness': liveness,
                        'primitive_operand_contract_sha256': str(extension['primitive_operand_contract_sha256']),
                        'liveness_binding_sha256': str(extension['liveness_binding_sha256']),
                        'qroam_table_cnot': decoded,
                    }
            operation_index = extension_end
        if stop_index is not None and operation_index >= stop_index:
            break


def _encoded_canonical_physical_flat_operation(row: Mapping[str, Any]) -> str:
    encoded = [
        int(row['operation_index']),
        str(row['contribution_kind']),
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


def write_canonical_physical_flat_netlist(
    manifest: Mapping[str, Any],
    output_path: Path,
    *,
    table_manifests: Mapping[str, Any],
    raw32_schedule: Mapping[str, Any],
    qroam_table_cnot_materialization: Mapping[str, Any],
    gzip_output: bool = True,
    start: int = 0,
    stop: Optional[int] = None,
) -> Dict[str, Any]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    opener = gzip.open if gzip_output else open
    row_count = 0
    stream_hash = hashlib.sha256()
    header = '\t'.join(CANONICAL_PHYSICAL_FLAT_NETLIST_COLUMNS) + '\n'
    stream_hash.update(header.encode('ascii'))
    with opener(output_path, 'wt', encoding='utf-8') as handle:
        handle.write(header)
        for row in iter_canonical_physical_flat_netlist(
            manifest,
            table_manifests=table_manifests,
            raw32_schedule=raw32_schedule,
            qroam_table_cnot_materialization=qroam_table_cnot_materialization,
            start=start,
            stop=stop,
        ):
            encoded_row = _encoded_canonical_physical_flat_operation(row)
            handle.write(encoded_row)
            stream_hash.update(encoded_row.encode('utf-8'))
            row_count += 1
    return {
        'schema': 'compiler-project-canonical-physical-flat-netlist-export-v1',
        'source_manifest_schema': manifest['schema'],
        'source_manifest_sha256': _sha256_payload(manifest),
        'columns': CANONICAL_PHYSICAL_FLAT_NETLIST_COLUMNS,
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


def _operand_source_binding_report(
    *,
    rows: List[Mapping[str, Any]],
    selected_lookup_family: Mapping[str, Any],
    selected_arithmetic_kernel: Mapping[str, Any],
    qroam_primitive_certificate: Mapping[str, Any],
    selected_phase_shell: Mapping[str, Any],
) -> Dict[str, Any]:
    lookup_blocks = {
        (str(stage['name']), str(block['name'])): (stage, block)
        for stage in selected_lookup_family['stages']
        for block in stage.get('blocks', [])
    }
    arithmetic_blocks = {
        (str(stage['stage']), str(block['block'])): (stage, block)
        for stage in selected_arithmetic_kernel['stages']
        for block in stage['blocks']
    }
    qroam_segments = {
        str(segment['sha256']): segment
        for segment in qroam_primitive_certificate['operation_stream']['segments']
    }
    phase_blocks = {
        (str(stage['name']), str(block['name'])): (stage, block)
        for stage in selected_phase_shell['stages']
        for block in stage['blocks']
    }
    rows_by_source_kind: Dict[str, int] = {}
    failures: List[Dict[str, Any]] = []

    def record_global_failure(source_kind: str, reasons: List[str]) -> None:
        if not reasons:
            return
        failures.append({
            'row_index': -1,
            'scope': 'source_artifact',
            'source': source_kind,
            'gate': '',
            'source_kind': source_kind,
            'reasons': reasons,
        })

    def record_failure(row: Mapping[str, Any], reasons: List[str]) -> None:
        if not reasons:
            return
        failures.append({
            'row_index': int(row['row_index']),
            'scope': str(row['scope']),
            'source': str(row['source']),
            'gate': str(row['gate']),
            'source_kind': str(row['primitive_operand_contract']['source_kind']),
            'reasons': reasons,
        })

    lookup_block_totals = _empty_gate_totals()
    for _, block in lookup_blocks.values():
        for gate, count in block['primitive_counts_total'].items():
            lookup_block_totals[gate] += int(count)
    record_global_failure(
        'lookup_lowering_block',
        [
            'lookup_family_primitive_counts_do_not_match_block_sum'
        ] if any(
            int(selected_lookup_family['primitive_counts_total'].get(gate, 0)) != lookup_block_totals.get(gate, 0)
            for gate in selected_lookup_family['primitive_counts_total']
        ) else [],
    )

    arithmetic_block_totals = _empty_gate_totals()
    for _, block in arithmetic_blocks.values():
        for gate, count in block['primitive_counts_total'].items():
            arithmetic_block_totals[gate] += int(count)
    record_global_failure(
        'arithmetic_operation_ir',
        [
            'arithmetic_kernel_primitive_counts_do_not_match_block_sum'
        ] if any(
            int(selected_arithmetic_kernel['primitive_counts_total'].get(gate, 0)) != arithmetic_block_totals.get(gate, 0)
            for gate in selected_arithmetic_kernel['primitive_counts_total']
        ) else [],
    )

    for row in rows:
        gate = str(row['gate'])
        source_kind = str(row['primitive_operand_contract']['source_kind'])
        rows_by_source_kind[source_kind] = rows_by_source_kind.get(source_kind, 0) + 1
        reasons: List[str] = []
        if row['scope'] in ('direct_seed_base', 'lookup_leaf_base'):
            stage_name = str(row.get('lookup_stage', ''))
            block_name = str(row.get('lookup_block', ''))
            block_entry = lookup_blocks.get((stage_name, block_name))
            if source_kind != 'lookup_lowering_block':
                reasons.append('wrong_lookup_source_kind')
            if block_entry is None:
                reasons.append('missing_lookup_block')
            else:
                _, block = block_entry
                expected_count = int(block['primitive_counts_total'].get(gate, 0))
                if int(row['total_count']) != expected_count:
                    reasons.append('lookup_block_gate_count_mismatch')
                if str(row.get('lookup_block_operation_stream_sha256')) != str(block['primitive_operation_stream']['sha256']):
                    reasons.append('lookup_block_stream_digest_mismatch')
                if int(block['primitive_operation_stream']['operation_count']) != sum(int(value) for value in block['primitive_counts_total'].values()):
                    reasons.append('lookup_block_operation_count_mismatch')
        elif row['scope'] == 'arithmetic_leaf_block':
            stage_name = str(row.get('arithmetic_stage', ''))
            block_name = str(row.get('arithmetic_block', ''))
            block_entry = arithmetic_blocks.get((stage_name, block_name))
            if source_kind != 'arithmetic_operation_ir':
                reasons.append('wrong_arithmetic_source_kind')
            if block_entry is None:
                reasons.append('missing_arithmetic_block')
            else:
                _, block = block_entry
                expected_count = int(block['primitive_counts_total'].get(gate, 0))
                if int(row['total_count']) != expected_count:
                    reasons.append('arithmetic_block_gate_count_mismatch')
                if int(block['operation_count']) != int(block['operation_end_exclusive']) - int(block['operation_start']):
                    reasons.append('arithmetic_block_operation_span_mismatch')
                if int(block['operation_count']) != sum(int(value) for value in block['primitive_counts_total'].values()):
                    reasons.append('arithmetic_block_operation_count_mismatch')
                if len(str(block['operation_stream_sha256'])) != 64:
                    reasons.append('arithmetic_block_stream_digest_missing')
        elif row['scope'] == 'qroam_chunk_stream':
            segment = qroam_segments.get(str(row.get('qroam_segment_sha256', '')))
            if source_kind != 'qroam_primitive_certificate':
                reasons.append('wrong_qroam_source_kind')
            if segment is None:
                reasons.append('missing_qroam_segment')
            else:
                if int(row['total_count']) != int(segment['operation_count']):
                    reasons.append('qroam_segment_operation_count_mismatch')
                if int(row['non_clifford_count']) != int(segment['ccx']):
                    reasons.append('qroam_segment_ccx_mismatch')
                if str(row.get('qroam_phase')) != str(segment['phase']):
                    reasons.append('qroam_segment_phase_mismatch')
                if str(row['primitive_operand_contract']['source_digest_sha256']) != str(segment['sha256']):
                    reasons.append('qroam_operand_contract_digest_mismatch')
        elif row['scope'] == 'phase_shell':
            source_parts = str(row['source']).split(':')
            block_entry = None
            if len(source_parts) == 3:
                block_entry = phase_blocks.get((source_parts[1], source_parts[2]))
            if source_kind != 'phase_shell_lowering':
                reasons.append('wrong_phase_source_kind')
            if block_entry is None:
                reasons.append('missing_phase_block')
            else:
                _, block = block_entry
                expected_count = int(block['count_profile_total'].get(gate, 0))
                if int(row['total_count']) != expected_count:
                    reasons.append('phase_block_gate_count_mismatch')
                if int(block['phase_operation_stream']['operation_count']) != sum(
                    int(value)
                    for key, value in block['count_profile_total'].items()
                    if key != 'rotation_depth'
                ):
                    reasons.append('phase_block_operation_count_mismatch')
        else:
            reasons.append('unknown_scope')
        record_failure(row, reasons)
    return {
        'schema': 'compiler-project-operand-source-binding-report-v1',
        'definition': 'Every public-candidate run-length row must bind to a concrete source operation block or QROAM segment, not only to an aggregate family/resource formula.',
        'rows_checked': len(rows),
        'rows_by_source_kind': {
            key: int(value)
            for key, value in sorted(rows_by_source_kind.items())
        },
        'failure_count': len(failures),
        'sample_failures': failures[:32],
        'pass': len(failures) == 0,
    }


def _arithmetic_source_blocks(
    *,
    arithmetic_lowerings: Mapping[str, Any],
    arithmetic_operation_ir: Mapping[str, Any],
) -> Dict[tuple[str, str], Mapping[str, Any]]:
    selected_kernel = _selected_arithmetic_kernel(arithmetic_operation_ir)
    lowering_kernel = next(
        kernel
        for kernel in arithmetic_lowerings['kernels']
        if str(kernel['opcode']) == str(selected_kernel['opcode'])
    )
    return {
        (str(stage['name']), str(block['name'])): block
        for stage in lowering_kernel['stages']
        for block in stage['blocks']
    }


def build_arithmetic_operand_replay_audit(
    *,
    public_candidate_materialized_circuit_manifest: Mapping[str, Any],
    arithmetic_lowerings: Mapping[str, Any],
    arithmetic_operation_ir: Mapping[str, Any],
    max_failures: int = 32,
) -> Dict[str, Any]:
    source_blocks = _arithmetic_source_blocks(
        arithmetic_lowerings=arithmetic_lowerings,
        arithmetic_operation_ir=arithmetic_operation_ir,
    )
    arithmetic_rows = [
        row
        for row in public_candidate_materialized_circuit_manifest['run_length_rows']
        if row['scope'] == 'arithmetic_leaf_block'
    ]
    cache: Dict[tuple[str, str, str], Dict[str, Any]] = {}
    failures: List[Dict[str, Any]] = []
    rows_with_failures = 0
    source_operations_checked = 0

    def replay_block_gate(row: Mapping[str, Any]) -> Dict[str, Any]:
        key = (str(row['arithmetic_stage']), str(row['arithmetic_block']), str(row['gate']))
        if key in cache:
            return cache[key]
        block = source_blocks.get((key[0], key[1]))
        if block is None:
            result = {
                'source_operation_count': 0,
                'operations_checked': 0,
                'failure_count': 1,
                'first_failure': {
                    'reason': 'missing_arithmetic_source_block',
                    'arithmetic_stage': key[0],
                    'arithmetic_block': key[1],
                    'gate': key[2],
                },
            }
            cache[key] = result
            return result
        source_operations = [
            operation
            for operation in materialize_arithmetic_primitive_operations(block)
            if str(operation[0]) == key[2]
        ]
        first_failure = None
        failure_count = 0
        for occurrence_index, operation in enumerate(source_operations):
            source_operands = [int(value) for value in operation[1:]]
            materialized_wires = _operation_domain_wires(row, occurrence_index)
            materialized_logical_operands = [
                int(wire['logical_operand_index'])
                for wire in materialized_wires[:len(source_operands)]
            ]
            materialized_physical_wires = [
                (str(wire['parent_wire_id']), int(wire['parent_bit_index']))
                for wire in materialized_wires
            ]
            duplicate_physical_wire = len(materialized_physical_wires) != len(set(materialized_physical_wires))
            spilled_source_operands = [
                value
                for value in source_operands
                if value >= 256
            ]
            spilled_operands_not_on_qchunk = any(
                int(wire['logical_operand_index']) >= 256
                and str(wire['parent_wire_id']) != 'qchunk'
                for wire in materialized_wires[:len(source_operands)]
            )
            if source_operands != materialized_logical_operands or duplicate_physical_wire or spilled_operands_not_on_qchunk:
                failure_count += 1
                if first_failure is None:
                    first_failure = {
                        'reason': 'source_operand_tuple_not_replayed_by_materialized_domain',
                        'arithmetic_stage': key[0],
                        'arithmetic_block': key[1],
                        'gate': key[2],
                        'occurrence_index': occurrence_index,
                        'source_operands': source_operands,
                        'materialized_logical_operands': materialized_logical_operands,
                        'duplicate_physical_wire': duplicate_physical_wire,
                        'spilled_source_operands': spilled_source_operands,
                        'spilled_operands_not_on_qchunk': spilled_operands_not_on_qchunk,
                        'materialized_wires': materialized_wires,
                    }
        result = {
            'source_operation_count': len(source_operations),
            'operations_checked': len(source_operations),
            'failure_count': failure_count,
            'first_failure': first_failure,
        }
        cache[key] = result
        return result

    for row in arithmetic_rows:
        result = replay_block_gate(row)
        source_operations_checked += int(result['operations_checked'])
        count_matches = int(result['source_operation_count']) == int(row['total_count'])
        row_failure_count = int(result['failure_count'])
        if not count_matches:
            row_failure_count += 1
        if row_failure_count:
            rows_with_failures += 1
            if len(failures) < max_failures:
                failures.append({
                    'row_index': int(row['row_index']),
                    'source': str(row['source']),
                    'arithmetic_stage': str(row['arithmetic_stage']),
                    'arithmetic_block': str(row['arithmetic_block']),
                    'gate': str(row['gate']),
                    'row_total_count': int(row['total_count']),
                    'source_operation_count': int(result['source_operation_count']),
                    'count_matches': count_matches,
                    'failure_count': row_failure_count,
                    'first_failure': result['first_failure'],
                })
    unique_failures = [
        {
            'arithmetic_stage': stage,
            'arithmetic_block': block,
            'gate': gate,
            'source_operation_count': int(result['source_operation_count']),
            'failure_count': int(result['failure_count']),
            'first_failure': result['first_failure'],
        }
        for (stage, block, gate), result in sorted(cache.items())
        if int(result['failure_count']) > 0
    ]
    return {
        'schema': 'compiler-project-arithmetic-operand-replay-audit-v1',
        'definition': 'Compares generated arithmetic primitive operands with the concrete parent-bit operands emitted by the public flat-netlist operand-domain replay.',
        'arithmetic_run_length_rows_checked': len(arithmetic_rows),
        'unique_block_gate_pairs_checked': len(cache),
        'source_operations_checked': source_operations_checked,
        'rows_with_failures': rows_with_failures,
        'unique_block_gate_failures': len(unique_failures),
        'sample_failures': failures,
        'unique_failures': unique_failures[:max_failures],
        'pass': rows_with_failures == 0 and len(unique_failures) == 0,
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
                    'qroam_start_address': int(segment['start_address']),
                    'qroam_end_address_exclusive': int(segment['end_address_exclusive']),
                    'qroam_segment_sha256': str(segment['sha256']),
                })
    return rows


def _qroam_table_cnot_flat_extension(
    *,
    qroam_rows: List[Mapping[str, Any]],
    liveness_rows: List[Mapping[str, Any]],
    qroam_table_cnot_materialization: Mapping[str, Any],
) -> Dict[str, Any]:
    liveness_by_row = {int(row['row_index']): row for row in liveness_rows}
    qroam_row_by_key = {
        (
            int(row['term_instance_index']),
            str(row['table']),
            int(row['chunk_index']),
            str(row['qroam_phase']),
            int(row['qroam_start_address']),
            int(row['qroam_end_address_exclusive']),
        ): row
        for row in qroam_rows
    }
    extension_rows: List[Dict[str, Any]] = []
    missing_keys: List[Dict[str, Any]] = []
    duplicate_keys = len(qroam_row_by_key) != len(qroam_rows)
    for segment_index, segment in enumerate(qroam_table_cnot_materialization['segments']):
        key = (
            int(segment['call_index']),
            str(segment['table']),
            int(segment['chunk_index']),
            str(segment['phase']),
            int(segment['start_address']),
            int(segment['end_address_exclusive']),
        )
        row = qroam_row_by_key.get(key)
        if row is None:
            missing_keys.append({
                'segment_index': segment_index,
                'key': list(key),
            })
            continue
        liveness = liveness_by_row[int(row['row_index'])]
        qroam_target_wire = f"qroam_chunk_target__{segment['table']}__chunk_{segment['chunk_index']}"
        extension_rows.append({
            'extension_segment_index': segment_index,
            'run_length_row_index': int(row['row_index']),
            'call_index': int(segment['call_index']),
            'table': str(segment['table']),
            'chunk_index': int(segment['chunk_index']),
            'phase': str(segment['phase']),
            'start_address': int(segment['start_address']),
            'end_address_exclusive': int(segment['end_address_exclusive']),
            'emitted_cx_count': int(segment['emitted_cx_count']),
            'emitted_cx_operation_start': int(segment['emitted_cx_operation_start']),
            'emitted_cx_operation_end_exclusive': int(segment['emitted_cx_operation_end_exclusive']),
            'effective_target_bit_sites': int(segment['effective_target_bit_sites']),
            'zero_padded_target_bit_sites': int(segment['zero_padded_target_bit_sites']),
            'first_emitted_cx': segment.get('first_emitted_cx'),
            'last_emitted_cx': segment.get('last_emitted_cx'),
            'row_index_contract': {
                'global_index_domain_start': int(segment['row_index_contract']['global_index_domain_start']),
                'global_index_domain_end_exclusive': int(segment['row_index_contract']['global_index_domain_end_exclusive']),
                'rank_checkpoint_count': int(segment['row_index_contract']['rank_checkpoint_count']),
                'rank_checkpoint_sha256': str(segment['row_index_contract']['rank_checkpoint_sha256']),
                'sample_count': int(segment['row_index_contract']['sample_count']),
                'sample_sha256': str(segment['row_index_contract']['sample_sha256']),
            },
            'source_segment_sha256': str(segment['sha256']),
            'qroam_run_length_segment_sha256': str(row['qroam_segment_sha256']),
            'primitive_operand_contract_sha256': str(row['primitive_operand_contract_sha256']),
            'liveness_binding_sha256': _sha256_payload(liveness),
            'liveness_interval_id': str(liveness['interval_id']),
            'total_live_qubits': int(liveness['total_live_qubits']),
            'qroam_target_wire': qroam_target_wire,
            'qroam_target_wire_live': qroam_target_wire in set(str(wire_id) for wire_id in liveness['live_wire_ids']),
            'qchunk_wire_live': 'qchunk' in set(str(wire_id) for wire_id in liveness['live_wire_ids']),
        })
    stream_digest = hashlib.sha256()
    columns = [
        'extension_segment_index',
        'run_length_row_index',
        'call_index',
        'table',
        'chunk_index',
        'phase',
        'start_address',
        'end_address_exclusive',
        'emitted_cx_count',
        'emitted_cx_operation_start',
        'emitted_cx_operation_end_exclusive',
        'effective_target_bit_sites',
        'zero_padded_target_bit_sites',
        'first_emitted_cx',
        'last_emitted_cx',
        'row_index_contract',
        'source_segment_sha256',
        'qroam_run_length_segment_sha256',
        'primitive_operand_contract_sha256',
        'liveness_binding_sha256',
        'liveness_interval_id',
        'total_live_qubits',
        'qroam_target_wire',
        'qroam_target_wire_live',
        'qchunk_wire_live',
    ]
    stream_digest.update(('\t'.join(columns) + '\n').encode('ascii'))
    segment_hashes: List[str] = []
    for row in extension_rows:
        encoded = '\t'.join(_canonical_json(row[column]) for column in columns) + '\n'
        row_hash = hashlib.sha256(encoded.encode('ascii')).hexdigest()
        segment_hashes.append(row_hash)
        stream_digest.update(encoded.encode('ascii'))
    emitted_cx_count = sum(int(row['emitted_cx_count']) for row in extension_rows)
    peak_live_qubits = max((int(row['total_live_qubits']) for row in extension_rows), default=0)
    checks = {
        'table_cnot_segments_match_qroam_run_length_rows': (
            not duplicate_keys
            and not missing_keys
            and len(extension_rows) == len(qroam_rows) == int(qroam_table_cnot_materialization['totals']['segment_count'])
        ),
        'table_cnot_operation_count_matches_artifact': emitted_cx_count == int(qroam_table_cnot_materialization['totals']['full_oracle_emitted_clifford_cx']),
        'table_cnot_operation_ranges_match_artifact': all(
            int(row['emitted_cx_operation_end_exclusive']) - int(row['emitted_cx_operation_start']) == int(row['emitted_cx_count'])
            and int(row['emitted_cx_operation_start']) <= int(row['emitted_cx_operation_end_exclusive'])
            and (
                row['first_emitted_cx'] is None
                or int(row['first_emitted_cx']['global_emitted_cx_index']) == int(row['emitted_cx_operation_start'])
            )
            and (
                row['last_emitted_cx'] is None
                or int(row['last_emitted_cx']['global_emitted_cx_index']) == int(row['emitted_cx_operation_end_exclusive']) - 1
            )
            for row in extension_rows
        ),
        'table_cnot_row_index_contract_matches_artifact': all(
            int(row['row_index_contract']['global_index_domain_start']) == int(row['emitted_cx_operation_start'])
            and int(row['row_index_contract']['global_index_domain_end_exclusive']) == int(row['emitted_cx_operation_end_exclusive'])
            and int(row['row_index_contract']['rank_checkpoint_count']) > 0
            and len(row['row_index_contract']['rank_checkpoint_sha256']) == 64
            and int(row['row_index_contract']['sample_count']) in (0, 2)
            and len(row['row_index_contract']['sample_sha256']) == 64
            for row in extension_rows
        ),
        'table_cnot_extension_adds_only_clifford_cx': True,
        'table_cnot_liveness_reuses_counted_qroam_rows': all(
            bool(row['qroam_target_wire_live'])
            and bool(row['qchunk_wire_live'])
            and int(row['total_live_qubits']) > 0
            for row in extension_rows
        ),
        'table_cnot_segments_have_merkle_root': len(qroam_table_cnot_materialization['segment_merkle_root_sha256']) == 64,
    }
    return {
        'schema': 'compiler-project-qroam-table-cnot-flat-extension-v1',
        'definition': 'Concrete Clifford CNOT extension for QROAM table-bit loads, bound to the public candidate run-length QROAM rows and their counted liveness intervals.',
        'source': 'qroam_table_cnot_materialization',
        'source_sha256': _sha256_payload(qroam_table_cnot_materialization),
        'columns': columns,
        'segment_count': len(extension_rows),
        'operation_count': emitted_cx_count,
        'gate_totals': {
            **_empty_gate_totals(),
            'cx': emitted_cx_count,
        },
        'non_clifford_count': 0,
        'peak_live_qubits': peak_live_qubits,
        'operation_stream_sha256': stream_digest.hexdigest(),
        'segment_merkle_root_sha256': _merkle_root(segment_hashes),
        'source_segment_merkle_root_sha256': qroam_table_cnot_materialization['segment_merkle_root_sha256'],
        'missing_segment_keys': missing_keys[:32],
        'duplicate_qroam_row_keys': duplicate_keys,
        'rows': extension_rows,
        'preview_head': extension_rows[:4],
        'preview_tail': extension_rows[-4:],
        'checks': checks,
        'pass': all(checks.values()),
    }


def _spliced_physical_segment_hash(contributions: List[Mapping[str, Any]]) -> str:
    digest = hashlib.sha256()
    digest.update(b'compiler-project-canonical-physical-flat-segment-v1\n')
    for contribution in contributions:
        digest.update((_canonical_json(contribution) + '\n').encode('ascii'))
    return digest.hexdigest()


def _spliced_physical_flat_netlist(
    *,
    operation_rows: List[Mapping[str, Any]],
    liveness_rows: List[Mapping[str, Any]],
    canonical_materialized_flat_netlist: Mapping[str, Any],
    qroam_table_cnot_flat_extension: Mapping[str, Any],
    segment_size: int = PUBLIC_CANDIDATE_FLAT_SEGMENT_SIZE,
) -> Dict[str, Any]:
    extension_by_row_index = {
        int(row['run_length_row_index']): row
        for row in qroam_table_cnot_flat_extension['rows']
    }
    liveness_by_row_index = {
        int(row['row_index']): row
        for row in liveness_rows
    }
    liveness_hash_by_row_index = {
        int(row['row_index']): _sha256_payload(row)
        for row in liveness_rows
    }
    operation_cursor = 0
    gate_totals = _empty_gate_totals()
    non_clifford_count = 0
    peak_live_qubits = int(canonical_materialized_flat_netlist['peak_live_qubits'])
    qroam_table_cnot_splice_count = 0
    qroam_table_cnot_operation_count = 0
    segment_start = 0
    segment_count = 0
    segment_gate_totals = _empty_gate_totals()
    segment_non_clifford = 0
    segment_digest_contributions: List[Dict[str, Any]] = []
    segments: List[Dict[str, Any]] = []
    qroam_table_cnot_splices: List[Dict[str, Any]] = []
    preview_head: List[Dict[str, Any]] = []
    preview_tail: List[Dict[str, Any]] = []

    def append_contribution(contribution: Mapping[str, Any]) -> None:
        nonlocal operation_cursor, segment_start, segment_count, segment_gate_totals
        nonlocal segment_non_clifford, segment_digest_contributions, non_clifford_count
        contribution_start = int(contribution['operation_start'])
        contribution_end = int(contribution['operation_end_exclusive'])
        if contribution_start != operation_cursor:
            raise AssertionError('spliced physical stream contribution order drifted')
        gate = str(contribution['gate'])
        remaining = contribution_end - contribution_start
        offset = 0
        compact = {
            key: contribution[key]
            for key in (
                'contribution_kind',
                'operation_start',
                'operation_end_exclusive',
                'gate',
                'scope',
                'source',
                'run_length_row_index',
            )
        }
        if len(preview_head) < 6:
            preview_head.append(dict(compact))
        preview_tail.append(dict(compact))
        if len(preview_tail) > 6:
            preview_tail.pop(0)
        while remaining:
            take = min(remaining, segment_size - segment_count)
            chunk = {
                **dict(contribution),
                'operation_start': operation_cursor,
                'operation_end_exclusive': operation_cursor + take,
                'contribution_instance_start': offset,
                'contribution_instance_end_exclusive': offset + take,
            }
            segment_digest_contributions.append(chunk)
            segment_gate_totals[gate] += take
            gate_totals[gate] += take
            if gate == 'ccx':
                segment_non_clifford += take
                non_clifford_count += take
            operation_cursor += take
            offset += take
            remaining -= take
            segment_count += take
            if segment_count == segment_size:
                segments.append({
                    'segment_index': len(segments),
                    'operation_start': segment_start,
                    'operation_end_exclusive': operation_cursor,
                    'operation_count': segment_count,
                    'gate_totals': segment_gate_totals,
                    'non_clifford_count': segment_non_clifford,
                    'sha256': _spliced_physical_segment_hash(segment_digest_contributions),
                })
                segment_start = operation_cursor
                segment_count = 0
                segment_gate_totals = _empty_gate_totals()
                segment_non_clifford = 0
                segment_digest_contributions = []

    for row in operation_rows:
        row_index = int(row['row_index'])
        row_total = int(row['total_count'])
        liveness = liveness_by_row_index[row_index]
        append_contribution({
            'contribution_kind': 'run_length_primitive_row',
            'operation_start': operation_cursor,
            'operation_end_exclusive': operation_cursor + row_total,
            'run_length_row_index': row_index,
            'scope': str(row['scope']),
            'source': str(row['source']),
            'gate': str(row['gate']),
            'primitive_operand_contract_sha256': str(row['primitive_operand_contract_sha256']),
            'liveness_binding_sha256': liveness_hash_by_row_index[row_index],
            'total_live_qubits': int(liveness['total_live_qubits']),
        })
        peak_live_qubits = max(peak_live_qubits, int(liveness['total_live_qubits']))
        extension = extension_by_row_index.get(row_index)
        if extension is not None:
            emitted_cx_count = int(extension['emitted_cx_count'])
            qroam_table_cnot_splices.append({
                'extension_segment_index': int(extension['extension_segment_index']),
                'run_length_row_index': row_index,
                'operation_start': operation_cursor,
                'operation_end_exclusive': operation_cursor + emitted_cx_count,
                'operation_count': emitted_cx_count,
                'emitted_cx_operation_start': int(extension['emitted_cx_operation_start']),
                'emitted_cx_operation_end_exclusive': int(extension['emitted_cx_operation_end_exclusive']),
                'source_segment_sha256': str(extension['source_segment_sha256']),
                'liveness_binding_sha256': str(extension['liveness_binding_sha256']),
                'qroam_target_wire': str(extension['qroam_target_wire']),
            })
            append_contribution({
                'contribution_kind': 'qroam_table_cnot_indexed_rows',
                'operation_start': operation_cursor,
                'operation_end_exclusive': operation_cursor + emitted_cx_count,
                'run_length_row_index': row_index,
                'extension_segment_index': int(extension['extension_segment_index']),
                'scope': 'qroam_table_cnot_indexed_stream',
                'source': 'qroam_table_cnot_materialization.row_index_contract',
                'gate': 'cx',
                'source_segment_sha256': str(extension['source_segment_sha256']),
                'qroam_run_length_segment_sha256': str(extension['qroam_run_length_segment_sha256']),
                'row_index_contract': extension['row_index_contract'],
                'liveness_binding_sha256': str(extension['liveness_binding_sha256']),
                'total_live_qubits': int(extension['total_live_qubits']),
                'qroam_target_wire': str(extension['qroam_target_wire']),
            })
            qroam_table_cnot_splice_count += 1
            qroam_table_cnot_operation_count += emitted_cx_count
            peak_live_qubits = max(peak_live_qubits, int(extension['total_live_qubits']))
    if segment_count:
        segments.append({
            'segment_index': len(segments),
            'operation_start': segment_start,
            'operation_end_exclusive': operation_cursor,
            'operation_count': segment_count,
            'gate_totals': segment_gate_totals,
            'non_clifford_count': segment_non_clifford,
            'sha256': _spliced_physical_segment_hash(segment_digest_contributions),
        })
    checks = {
        'canonical_rows_are_prefix_contributions': sum(
            int(row['total_count'])
            for row in operation_rows
        ) == int(canonical_materialized_flat_netlist['operation_count']),
        'qroam_table_cnot_rows_are_spliced': (
            qroam_table_cnot_splice_count == int(qroam_table_cnot_flat_extension['segment_count'])
            and qroam_table_cnot_operation_count == int(qroam_table_cnot_flat_extension['operation_count'])
        ),
        'gate_totals_include_indexed_qroam_table_cx': (
            gate_totals['cx'] == int(qroam_table_cnot_flat_extension['operation_count'])
            and gate_totals['ccx'] == int(canonical_materialized_flat_netlist['gate_totals']['ccx'])
        ),
        'non_clifford_count_is_unchanged_by_clifford_splice': non_clifford_count == int(canonical_materialized_flat_netlist['non_clifford_count']),
        'peak_live_qubits_covers_canonical_and_table_cnot_liveness': (
            peak_live_qubits >= int(canonical_materialized_flat_netlist['peak_live_qubits'])
            and peak_live_qubits >= int(qroam_table_cnot_flat_extension['peak_live_qubits'])
        ),
        'qroam_table_cnot_splice_ranges_cover_cx_total': (
            len(qroam_table_cnot_splices) == qroam_table_cnot_splice_count
            and sum(int(row['operation_count']) for row in qroam_table_cnot_splices) == qroam_table_cnot_operation_count
            and all(
                int(row['operation_end_exclusive']) - int(row['operation_start']) == int(row['operation_count'])
                for row in qroam_table_cnot_splices
            )
        ),
    }
    return {
        'schema': 'compiler-project-canonical-physical-flat-netlist-v1',
        'definition': 'Canonical physical flat stream summary that splices indexed QROAM table-CNOT rows into the canonical materialized primitive stream without expanding every Clifford CNOT row into JSON.',
        'operation_schema': [
            'operation_index',
            'contribution_kind',
            'run_length_row_index',
            'gate',
            'scope',
            'source',
            'liveness_binding_sha256',
            'row_index_contract_for_qroam_table_cnot',
        ],
        'exact_virtual_operation_stream_materialized': True,
        'per_operation_rows_materialized_in_json': False,
        'segment_size': segment_size,
        'operation_count': operation_cursor,
        'segment_count': len(segments),
        'operation_stream_sha256': _sha256_payload({
            'canonical_operation_stream_sha256': canonical_materialized_flat_netlist['operation_stream_sha256'],
            'qroam_table_cnot_operation_stream_sha256': qroam_table_cnot_flat_extension['operation_stream_sha256'],
            'segment_merkle_root_sha256': _merkle_root([segment['sha256'] for segment in segments]),
        }),
        'segment_merkle_root_sha256': _merkle_root([segment['sha256'] for segment in segments]),
        'gate_totals': gate_totals,
        'non_clifford_count': non_clifford_count,
        'peak_live_qubits': peak_live_qubits,
        'qroam_table_cnot_splice_count': qroam_table_cnot_splice_count,
        'qroam_table_cnot_operation_count': qroam_table_cnot_operation_count,
        'qroam_table_cnot_splices': qroam_table_cnot_splices,
        'segments': segments,
        'preview_head': preview_head,
        'preview_tail': preview_tail,
        'checks': checks,
        'pass': all(checks.values()),
    }


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


def _lookup_operand_domains_by_gate(lookup_family: Mapping[str, Any]) -> Dict[str, List[Mapping[str, Any]]]:
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
    return {
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


def _lookup_base_run_length_rows(
    *,
    row_index: int,
    lookup_family: Mapping[str, Any],
    usage: str,
    leaf_call_index: Optional[int] = None,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    operand_domains_by_gate = _lookup_operand_domains_by_gate(lookup_family)
    for stage in lookup_family['stages']:
        for block in stage.get('blocks', []):
            primitive_counts = block['primitive_counts_total']
            if not any(int(count) > 0 for count in primitive_counts.values()):
                continue
            extra = {
                'lookup_family': str(lookup_family['name']),
                'lookup_stage': str(stage['name']),
                'lookup_block': str(block['name']),
                'lookup_block_operation_stream_sha256': str(block['primitive_operation_stream']['sha256']),
            }
            if leaf_call_index is not None:
                extra['leaf_call_index'] = int(leaf_call_index)
            rows.extend(_count_rows_from_primitive_counts(
                row_index=row_index + len(rows),
                scope='direct_seed_base' if usage == 'direct_seed' else 'lookup_leaf_base',
                source=f"lookup_lowerings:{lookup_family['name']}:{stage['name']}:{block['name']}:{usage}",
                primitive_counts=primitive_counts,
                provenance_payload={
                    'lookup_family': lookup_family['name'],
                    'usage': usage,
                    'leaf_call_index': leaf_call_index,
                    'stage': stage['name'],
                    'stage_category': stage['category'],
                    'block': block['name'],
                    'operation_stream_sha256': block['primitive_operation_stream']['sha256'],
                    'primitive_operation_encoding': block['primitive_operation_encoding'],
                    'primitive_counts_total': primitive_counts,
                },
                operand_domains={
                    gate: operand_domains_by_gate[gate]
                    for gate, count in primitive_counts.items()
                    if int(count) > 0
                },
                source_kind='lookup_lowering_block',
                extra=extra,
            ))
    return rows


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
    rows: List[Dict[str, Any]] = []
    rows.extend(_lookup_base_run_length_rows(
        row_index=len(rows),
        lookup_family=lookup_family,
        usage='direct_seed',
    ))
    for leaf_call_index in range(leaf_call_count):
        rows.extend(_lookup_base_run_length_rows(
            row_index=len(rows),
            lookup_family=lookup_family,
            usage='leaf_lookup_base',
            leaf_call_index=leaf_call_index,
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


def _strict_replayed_tail_capacity_overlay(
    *,
    strict_replayed_tail_headline: Mapping[str, Any],
    tail_macro_engine: Mapping[str, Any],
    reusable_chunk_lowering: Mapping[str, Any],
    materialized_flat_netlist: Mapping[str, Any],
) -> Dict[str, Any]:
    selected = strict_replayed_tail_headline['selected_result']
    formula = strict_replayed_tail_headline['logical_qubit_formula']
    non_clifford_formula = strict_replayed_tail_headline['non_clifford_formula']
    tail_rows = [
        {
            'owner_id': str(row['owner_id']),
            'logical_qubits': int(row['logical_qubits']),
            'required_peak_qubits': int(row.get('required_peak_qubits', row['logical_qubits'])),
            'capacity_field_values': int(row.get('capacity_field_values', 1)),
            'counted_in_legacy_leaf_budget': bool(row.get('counted_in_current_leaf_budget', True)),
            'capacity_pass': int(row['logical_qubits']) >= int(row.get('required_peak_qubits', row['logical_qubits'])) and int(row.get('capacity_field_values', 1)) >= 1,
        }
        for row in tail_macro_engine['fused_output_slot_assignment']['owner_capacity_rows']
    ]
    tail_capacity_qubits = sum(int(row['logical_qubits']) for row in tail_rows)
    lookup_workspace_qubits = int(reusable_chunk_lowering['qubit_derivation']['lookup_workspace_qubits'])
    control_qubits = int(reusable_chunk_lowering['qubit_derivation']['control_qubits']) + int(selected['fused_output_guard_qubits'])
    phase_qubits = int(reusable_chunk_lowering['qubit_derivation']['phase_qubits'])
    reconstructed_logical_qubits = tail_capacity_qubits + lookup_workspace_qubits + control_qubits + phase_qubits
    checks = {
        'strict_headline_passes': strict_replayed_tail_headline['pass'] is True,
        'materialized_stream_non_clifford_matches_strict_headline': int(materialized_flat_netlist['non_clifford_count']) == int(selected['non_clifford']),
        'strict_non_clifford_formula_matches_materialized_stream': int(non_clifford_formula['reconstructed_total']) == int(materialized_flat_netlist['non_clifford_count']),
        'tail_capacity_rows_match_replayed_seven_slot_assignment': len(tail_rows) == int(selected['tail_field_slots']) == int(formula['tail_field_slots']),
        'tail_capacity_rows_are_field_sized_and_pass': all(int(row['logical_qubits']) == int(selected['field_bits']) and row['capacity_pass'] is True for row in tail_rows),
        'strict_logical_qubits_reconstruct_from_capacity_terms': reconstructed_logical_qubits == int(selected['logical_qubits']) == int(formula['reconstructed_total']),
        'strict_capacity_peak_exceeds_legacy_materialized_liveness_peak': int(selected['logical_qubits']) > int(materialized_flat_netlist['peak_live_qubits']),
    }
    return {
        'schema': 'compiler-project-strict-replayed-tail-capacity-overlay-v1',
        'status': 'strict_capacity_overlay_bound_to_flat_operation_stream_not_full_liveness_rewrite',
        'selected_result_name': str(selected['name']),
        'source_artifact': 'compiler_verification_project/artifacts/strict_replayed_tail_headline.json',
        'flat_operation_stream': {
            'operation_count': int(materialized_flat_netlist['operation_count']),
            'non_clifford_count': int(materialized_flat_netlist['non_clifford_count']),
            'operation_stream_sha256': str(materialized_flat_netlist['operation_stream_sha256']),
            'segment_merkle_root_sha256': str(materialized_flat_netlist['segment_merkle_root_sha256']),
        },
        'strict_capacity_terms': {
            'tail_field_slot_count': int(selected['tail_field_slots']),
            'field_bits': int(selected['field_bits']),
            'tail_field_qubits': tail_capacity_qubits,
            'lookup_workspace_qubits': lookup_workspace_qubits,
            'control_qubits': control_qubits,
            'fused_output_guard_qubits': int(selected['fused_output_guard_qubits']),
            'phase_qubits': phase_qubits,
            'reconstructed_logical_qubits': reconstructed_logical_qubits,
        },
        'tail_owner_capacity_rows': tail_rows,
        'comparison_to_materialized_liveness': {
            'materialized_flat_liveness_peak_qubits': int(materialized_flat_netlist['peak_live_qubits']),
            'strict_capacity_peak_qubits': int(selected['logical_qubits']),
            'delta_qubits': int(selected['logical_qubits']) - int(materialized_flat_netlist['peak_live_qubits']),
        },
        'claim_boundary': {
            'flat_operation_stream_binds_non_clifford': True,
            'strict_replayed_tail_capacity_binds_logical_qubits': True,
            'full_operation_index_liveness_rewrite_binds_strict_qubits': False,
        },
        'checks': checks,
        'pass': all(checks.values()),
    }


def _strict_replayed_tail_liveness_projection(
    *,
    liveness_rows: List[Mapping[str, Any]],
    strict_capacity_overlay: Mapping[str, Any],
) -> Dict[str, Any]:
    strict_terms = strict_capacity_overlay['strict_capacity_terms']
    strict_tail_owner_qubits = {
        str(row['owner_id']): int(row['logical_qubits'])
        for row in strict_capacity_overlay['tail_owner_capacity_rows']
    }
    strict_tail_owner_qubits['lookup_workspace'] = int(strict_terms['lookup_workspace_qubits'])
    strict_tail_owner_qubits['control_slot_register_file'] = int(strict_terms['control_qubits'])
    strict_tail_owner_qubits['phase_shell_live_register'] = int(strict_terms['phase_qubits'])
    strict_tail_wire_ids = [f"{owner_id}.strict_live" for owner_id in strict_tail_owner_qubits]
    projected_rows: List[Dict[str, Any]] = []
    for row in liveness_rows:
        if row['scope'] == 'arithmetic_leaf_block':
            projected_rows.append({
                'row_index': int(row['row_index']),
                'scope': str(row['scope']),
                'interval_id': 'strict_replayed_tail_capacity',
                'live_wire_ids': strict_tail_wire_ids,
                'owner_live_qubits': dict(strict_tail_owner_qubits),
                'derived_owner_live_qubits': dict(strict_tail_owner_qubits),
                'total_live_qubits': int(strict_terms['reconstructed_logical_qubits']),
                'owner_capacity_pass': True,
                'source_liveness_interval_id': str(row['interval_id']),
                'projection_reason': 'arithmetic tail row uses the replayed seven-slot capacity contract',
            })
        else:
            projected_rows.append({
                **row,
                'source_liveness_interval_id': str(row['interval_id']),
                'projection_reason': 'non-tail row keeps materialized engine liveness',
            })
    peak_live_qubits = max(int(row['total_live_qubits']) for row in projected_rows)
    peak_interval_ids = sorted({
        str(row['interval_id'])
        for row in projected_rows
        if int(row['total_live_qubits']) == peak_live_qubits
    })
    checks = {
        'projection_covers_all_liveness_rows': len(projected_rows) == len(liveness_rows),
        'strict_tail_rows_get_strict_capacity_peak': all(
            int(row['total_live_qubits']) == int(strict_terms['reconstructed_logical_qubits'])
            for row in projected_rows
            if row['scope'] == 'arithmetic_leaf_block'
        ),
        'non_tail_rows_keep_materialized_liveness': all(
            int(row['total_live_qubits']) == int(liveness_rows[int(row['row_index'])]['total_live_qubits'])
            and row['live_wire_ids'] == liveness_rows[int(row['row_index'])]['live_wire_ids']
            for row in projected_rows
            if row['scope'] != 'arithmetic_leaf_block'
        ),
        'projection_peak_matches_strict_capacity': peak_live_qubits == int(strict_terms['reconstructed_logical_qubits']),
        'projected_owner_sums_reconstruct_totals': all(
            sum(int(qubits) for qubits in row['derived_owner_live_qubits'].values()) == int(row['total_live_qubits'])
            for row in projected_rows
        ),
    }
    return {
        'schema': 'compiler-project-strict-replayed-tail-liveness-projection-v1',
        'status': 'run_length_liveness_projection_bound_to_strict_replayed_tail_capacity',
        'row_count': len(projected_rows),
        'peak_live_qubits': peak_live_qubits,
        'peak_interval_ids': peak_interval_ids,
        'strict_tail_owner_capacity_qubits': strict_tail_owner_qubits,
        'liveness_binding_stream_sha256': _public_candidate_liveness_hash(projected_rows),
        'rows': projected_rows,
        'preview_head': projected_rows[:8],
        'preview_tail': projected_rows[-8:],
        'claim_boundary': {
            'run_length_rows_bind_strict_tail_liveness': True,
            'operation_index_rows_can_inherit_projected_liveness': True,
            'materialized_flat_netlist_segment_hashes_include_projected_liveness': False,
        },
        'checks': checks,
        'pass': all(checks.values()),
    }


def build_public_candidate_materialized_circuit_manifest(
    *,
    reusable_chunk_lowering: Mapping[str, Any],
    arithmetic_operation_ir: Mapping[str, Any],
    lookup_lowerings: Mapping[str, Any],
    qroam_primitive_certificate: Mapping[str, Any],
    qroam_table_cnot_materialization: Mapping[str, Any],
    phase_shell_lowerings: Mapping[str, Any],
    compiler_parameters: Mapping[str, Any],
    selected_family_name: str,
    include_materialized_flat_netlist: bool = True,
    materialized_flat_netlist_override: Optional[Mapping[str, Any]] = None,
    strict_materialized_flat_netlist_override: Optional[Mapping[str, Any]] = None,
    strict_replayed_tail_headline: Optional[Mapping[str, Any]] = None,
    tail_macro_engine: Optional[Mapping[str, Any]] = None,
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
    if materialized_flat_netlist_override is not None:
        materialized_flat_netlist = dict(materialized_flat_netlist_override)
    elif include_materialized_flat_netlist:
        materialized_flat_netlist = _materialized_flat_netlist_commitment(
            operation_rows=rows,
            liveness_rows=liveness_rows,
        )
    else:
        materialized_flat_netlist = _omitted_materialized_flat_netlist_summary(
            flat_netlist=flat_netlist,
            liveness_rows=liveness_rows,
        )
    materialized_public_totals = {
        'non_clifford': int(materialized_flat_netlist['non_clifford_count']),
        'logical_qubits': int(materialized_flat_netlist['peak_live_qubits']),
    }
    strict_capacity_overlay = None
    if strict_replayed_tail_headline is not None and tail_macro_engine is not None:
        strict_capacity_overlay = _strict_replayed_tail_capacity_overlay(
            strict_replayed_tail_headline=strict_replayed_tail_headline,
            tail_macro_engine=tail_macro_engine,
            reusable_chunk_lowering=reusable_chunk_lowering,
            materialized_flat_netlist=materialized_flat_netlist,
        )
    strict_liveness_projection = None
    if strict_capacity_overlay is not None:
        strict_liveness_projection = _strict_replayed_tail_liveness_projection(
            liveness_rows=liveness_rows,
            strict_capacity_overlay=strict_capacity_overlay,
        )
    strict_materialized_flat_netlist = None
    if strict_liveness_projection is not None:
        if strict_materialized_flat_netlist_override is not None:
            strict_materialized_flat_netlist = dict(strict_materialized_flat_netlist_override)
        elif include_materialized_flat_netlist:
            strict_materialized_flat_netlist = _materialized_flat_netlist_commitment(
                operation_rows=rows,
                liveness_rows=list(strict_liveness_projection['rows']),
            )
        else:
            strict_materialized_flat_netlist = _omitted_materialized_flat_netlist_summary(
                flat_netlist=flat_netlist,
                liveness_rows=list(strict_liveness_projection['rows']),
            )
        strict_liveness_projection['claim_boundary']['materialized_flat_netlist_segment_hashes_include_projected_liveness'] = (
            strict_materialized_flat_netlist['exact_operation_stream_materialized'] is True
        )
        strict_liveness_projection['pass'] = all(strict_liveness_projection['checks'].values())
    if strict_materialized_flat_netlist is not None and strict_materialized_flat_netlist['exact_operation_stream_materialized'] is True:
        canonical_materialized_flat_netlist = strict_materialized_flat_netlist
        public_totals = {
            'non_clifford': int(canonical_materialized_flat_netlist['non_clifford_count']),
            'logical_qubits': int(canonical_materialized_flat_netlist['peak_live_qubits']),
            'source': PUBLIC_CANDIDATE_CANONICAL_TOTALS_SOURCE,
        }
    else:
        canonical_materialized_flat_netlist = materialized_flat_netlist
        public_totals = {
            **materialized_public_totals,
            'source': PUBLIC_CANDIDATE_CANONICAL_TOTALS_SOURCE,
        }
    base_rows = [row for row in rows if row['scope'] in ('direct_seed_base', 'lookup_leaf_base', 'arithmetic_leaf_block')]
    direct_seed_rows = [row for row in rows if row['scope'] == 'direct_seed_base']
    lookup_leaf_rows = [row for row in rows if row['scope'] == 'lookup_leaf_base']
    arithmetic_leaf_rows = [row for row in rows if row['scope'] == 'arithmetic_leaf_block']
    qroam_rows = [row for row in rows if row['scope'] == 'qroam_chunk_stream']
    phase_rows = [row for row in rows if row['scope'] == 'phase_shell']
    qroam_table_cnot_flat_extension = _qroam_table_cnot_flat_extension(
        qroam_rows=qroam_rows,
        liveness_rows=liveness_rows,
        qroam_table_cnot_materialization=qroam_table_cnot_materialization,
    )
    canonical_physical_flat_netlist = _spliced_physical_flat_netlist(
        operation_rows=rows,
        liveness_rows=list(strict_liveness_projection['rows']) if strict_liveness_projection is not None else liveness_rows,
        canonical_materialized_flat_netlist=canonical_materialized_flat_netlist,
        qroam_table_cnot_flat_extension=qroam_table_cnot_flat_extension,
    )
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
    operand_source_binding = _operand_source_binding_report(
        rows=rows,
        selected_lookup_family=selected_lookup_family,
        selected_arithmetic_kernel=selected_arithmetic_kernel,
        qroam_primitive_certificate=qroam_primitive_certificate,
        selected_phase_shell=selected_phase_shell,
    )
    checks = {
        'selected_family_matches_compiler_parameters': selected_family_name == compiler_parameters['public_headline_policy']['selected_public_family_name'],
        'source_engines_pass': (
            reusable_chunk_lowering['executable_resource_engine']['pass'] is True
            and reusable_chunk_lowering['counted_resource_engine']['pass'] is True
            and arithmetic_operation_ir['pass'] is True
            and qroam_primitive_certificate['pass'] is True
            and qroam_table_cnot_materialization['pass'] is True
        ),
        'non_clifford_total_matches_public_candidate': non_clifford_total == int(public_totals['non_clifford']),
        'qroam_rows_expand_every_public_stream_segment': len(qroam_rows) == qroam_stream_term_instances * qroam_segment_count,
        'qroam_rows_sum_to_public_qroam_derivation': qroam_non_clifford_total == int(reusable_chunk_lowering['non_clifford_derivation']['qroam_chunk_non_clifford']),
        'qroam_table_cnot_flat_extension_is_bound': (
            qroam_table_cnot_flat_extension['pass'] is True
            and int(qroam_table_cnot_flat_extension['segment_count']) == len(qroam_rows)
            and int(qroam_table_cnot_flat_extension['operation_count']) == int(qroam_table_cnot_materialization['totals']['full_oracle_emitted_clifford_cx'])
            and int(qroam_table_cnot_flat_extension['non_clifford_count']) == 0
            and int(qroam_table_cnot_flat_extension['peak_live_qubits']) <= int(materialized_public_totals['logical_qubits'])
        ),
        'canonical_physical_flat_netlist_splices_qroam_table_cnot_rows': (
            canonical_physical_flat_netlist['pass'] is True
            and int(canonical_physical_flat_netlist['operation_count']) == int(canonical_materialized_flat_netlist['operation_count']) + int(qroam_table_cnot_flat_extension['operation_count'])
            and int(canonical_physical_flat_netlist['gate_totals']['cx']) == int(qroam_table_cnot_flat_extension['operation_count'])
            and int(canonical_physical_flat_netlist['gate_totals']['ccx']) == int(canonical_materialized_flat_netlist['gate_totals']['ccx'])
            and int(canonical_physical_flat_netlist['non_clifford_count']) == int(canonical_materialized_flat_netlist['non_clifford_count'])
            and int(canonical_physical_flat_netlist['peak_live_qubits']) == int(public_totals['logical_qubits'])
        ),
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
        'legacy_liveness_bindings_reconstruct_legacy_materialized_peak': materialized_public_totals['logical_qubits'] == int(reusable_chunk_lowering['qubit_derivation']['candidate_total_logical_qubits']),
        'flat_netlist_expands_all_run_length_rows': (
            flat_netlist['operation_count'] == sum(int(row['total_count']) for row in rows)
            and sum(int(segment['operation_count']) for segment in flat_netlist['segments']) == flat_netlist['operation_count']
            and flat_netlist['segments'][0]['operation_start'] == 0
            and flat_netlist['segments'][-1]['operation_end_exclusive'] == flat_netlist['operation_count']
        ),
        'flat_netlist_gate_totals_match_run_length_rows': flat_netlist['gate_totals'] == gate_totals,
        'flat_netlist_non_clifford_matches_public_candidate': materialized_public_totals['non_clifford'] == int(public_totals['non_clifford']),
        PUBLIC_TOTALS_DERIVE_FROM_CANONICAL_CHECK: (
            canonical_materialized_flat_netlist['exact_operation_stream_materialized'] is True
            and public_totals['source'] == PUBLIC_CANDIDATE_CANONICAL_TOTALS_SOURCE
            and int(public_totals['non_clifford']) == int(canonical_materialized_flat_netlist['non_clifford_count'])
            and int(public_totals['logical_qubits']) == int(canonical_materialized_flat_netlist['peak_live_qubits'])
        ),
        CANONICAL_FLAT_NETLIST_IS_STRICT_REPLAY_CHECK: (
            strict_materialized_flat_netlist is not None
            and canonical_materialized_flat_netlist['operation_stream_sha256'] == strict_materialized_flat_netlist['operation_stream_sha256']
            and int(canonical_materialized_flat_netlist['peak_live_qubits']) == int(public_totals['logical_qubits'])
        ),
        'materialized_flat_netlist_stream_is_exact': (
            materialized_flat_netlist['exact_operation_stream_materialized'] is True
            and materialized_flat_netlist['operation_count'] == flat_netlist['operation_count']
            and materialized_flat_netlist['gate_totals'] == gate_totals
            and materialized_flat_netlist['non_clifford_count'] == non_clifford_total
            and materialized_flat_netlist['peak_live_qubits'] == materialized_public_totals['logical_qubits']
            and materialized_flat_netlist['segment_count'] == len(materialized_flat_netlist['segments'])
            and len(materialized_flat_netlist['operation_stream_sha256']) == 64
            and len(materialized_flat_netlist['segment_merkle_root_sha256']) == 64
        ),
        'materialized_flat_netlist_counts_match_index_netlist': (
            materialized_flat_netlist['operation_count'] == flat_netlist['operation_count']
            and materialized_flat_netlist['gate_totals'] == flat_netlist['gate_totals']
            and materialized_flat_netlist['non_clifford_count'] == flat_netlist['non_clifford_count']
        ),
        'materialized_flat_netlist_segments_cover_stream': (
            materialized_flat_netlist['segment_count'] == len(materialized_flat_netlist['segments'])
            and (
                materialized_flat_netlist['operation_count'] == 0
                or (
                    materialized_flat_netlist['segments'][0]['operation_start'] == 0
                    and materialized_flat_netlist['segments'][-1]['operation_end_exclusive'] == materialized_flat_netlist['operation_count']
                    and sum(int(segment['operation_count']) for segment in materialized_flat_netlist['segments']) == materialized_flat_netlist['operation_count']
                )
            )
        ),
        'materialized_flat_netlist_preview_rows_are_concrete': (
            materialized_flat_netlist['exact_operation_stream_materialized'] is True
            and all(
                len(operation['operand_wires']) == PRIMITIVE_GATE_ARITY[operation['gate']]
                and all(str(wire['wire_id']) and str(wire['parent_wire_id']) for wire in operation['operand_wires'])
                for operation in materialized_flat_netlist['preview_head'] + materialized_flat_netlist['preview_tail']
            )
        ),
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
        'primitive_operand_rows_bind_source_operation_blocks': operand_source_binding['pass'] is True,
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
        'operand_source_binding_report_is_current': (
            operand_source_binding['rows_checked'] == len(rows)
            and operand_source_binding['pass'] is True
            and set(operand_source_binding['rows_by_source_kind']) == {
                'arithmetic_operation_ir',
                'lookup_lowering_block',
                'phase_shell_lowering',
                'qroam_primitive_certificate',
            }
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
        'strict_replayed_tail_capacity_overlay_is_bound': (
            strict_capacity_overlay is not None
            and strict_capacity_overlay['pass'] is True
            and strict_capacity_overlay['claim_boundary']['full_operation_index_liveness_rewrite_binds_strict_qubits'] is False
        ),
        'strict_replayed_tail_liveness_projection_is_bound': (
            strict_liveness_projection is not None
            and strict_liveness_projection['pass'] is True
            and strict_liveness_projection['peak_live_qubits'] == strict_capacity_overlay['strict_capacity_terms']['reconstructed_logical_qubits']
            and strict_liveness_projection['claim_boundary']['materialized_flat_netlist_segment_hashes_include_projected_liveness'] is True
        ),
        'strict_replayed_tail_materialized_flat_netlist_is_bound': (
            strict_materialized_flat_netlist is not None
            and strict_materialized_flat_netlist['exact_operation_stream_materialized'] is True
            and strict_materialized_flat_netlist['operation_count'] == flat_netlist['operation_count']
            and strict_materialized_flat_netlist['gate_totals'] == gate_totals
            and strict_materialized_flat_netlist['non_clifford_count'] == non_clifford_total
            and strict_materialized_flat_netlist['peak_live_qubits'] == strict_capacity_overlay['strict_capacity_terms']['reconstructed_logical_qubits']
            and strict_materialized_flat_netlist['segment_count'] == len(strict_materialized_flat_netlist['segments'])
            and len(strict_materialized_flat_netlist['operation_stream_sha256']) == 64
            and len(strict_materialized_flat_netlist['segment_merkle_root_sha256']) == 64
        ),
        'strict_replayed_tail_materialized_flat_netlist_segments_cover_stream': (
            strict_materialized_flat_netlist is not None
            and strict_materialized_flat_netlist['segment_count'] == len(strict_materialized_flat_netlist['segments'])
            and (
                strict_materialized_flat_netlist['operation_count'] == 0
                or (
                    strict_materialized_flat_netlist['segments'][0]['operation_start'] == 0
                    and strict_materialized_flat_netlist['segments'][-1]['operation_end_exclusive'] == strict_materialized_flat_netlist['operation_count']
                    and sum(int(segment['operation_count']) for segment in strict_materialized_flat_netlist['segments']) == strict_materialized_flat_netlist['operation_count']
                )
            )
        ),
        'strict_replayed_tail_materialized_flat_netlist_preview_rows_are_concrete': (
            strict_materialized_flat_netlist is not None
            and strict_materialized_flat_netlist['exact_operation_stream_materialized'] is True
            and all(
                len(operation['operand_wires']) == PRIMITIVE_GATE_ARITY[operation['gate']]
                and all(str(wire['wire_id']) and str(wire['parent_wire_id']) for wire in operation['operand_wires'])
                for operation in strict_materialized_flat_netlist['preview_head'] + strict_materialized_flat_netlist['preview_tail']
            )
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
            'qroam_table_cnot_materialization_sha256': _sha256_payload(qroam_table_cnot_materialization),
            'phase_shell_lowerings_sha256': _sha256_payload(phase_shell_lowerings),
            'compiler_parameters_sha256': _sha256_payload(compiler_parameters),
            'strict_replayed_tail_headline_sha256': _sha256_payload(strict_replayed_tail_headline) if strict_replayed_tail_headline is not None else None,
            'tail_macro_engine_sha256': _sha256_payload(tail_macro_engine) if tail_macro_engine is not None else None,
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
        'public_totals': public_totals,
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
        'strict_replayed_tail_capacity_overlay': strict_capacity_overlay,
        'strict_replayed_tail_liveness_projection': strict_liveness_projection,
        STRICT_REPLAYED_TAIL_MATERIALIZED_FLAT_NETLIST: strict_materialized_flat_netlist,
        CANONICAL_MATERIALIZED_FLAT_NETLIST: canonical_materialized_flat_netlist,
        'canonical_physical_flat_netlist': canonical_physical_flat_netlist,
        LEGACY_WRAPPER_MATERIALIZED_FLAT_NETLIST: materialized_flat_netlist,
        'flat_netlist': flat_netlist,
        'materialized_flat_netlist': materialized_flat_netlist,
        'flat_execution_probe': flat_execution_probe,
        'strict_primitive_completeness': strict_primitive_completeness,
        'operand_parent_binding': operand_parent_binding,
        'operand_source_binding': operand_source_binding,
        'qroam_table_cnot_flat_extension': qroam_table_cnot_flat_extension,
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
            'materialized_flat_netlist is the checked full primitive stream: the build scans every emitted primitive operation with concrete operand wires and derives the public non-Clifford and peak-live-qubit totals from that stream.',
            'operand_source_binding requires every run-length row to bind to a source arithmetic block, lookup block, QROAM segment, or phase-shell block rather than only to an aggregate family count.',
            'The flat_execution_probe section is generated by executing representative operation indices through the same expandable flat-netlist API used for the full stream.',
            'strict_primitive_completeness requires every row to expose arity-correct primitive operand domains so the flat-netlist iterator emits exact operand references for each primitive operation.',
            'The full stream is stored as exact segment hashes and previews in JSON; materialize_exact_circuits.py can export physical TSV slices or the entire stream when an audit wants lines on disk.',
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
    'build_arithmetic_operand_replay_audit',
    'build_materialized_family_manifest',
    'build_public_candidate_materialized_circuit_manifest',
    'iter_canonical_physical_flat_netlist',
    'iter_public_candidate_flat_netlist',
    'iter_family_operation_stream',
    'resolve_selected_family_names',
    'write_canonical_physical_flat_netlist',
    'write_public_candidate_flat_netlist',
    'write_materialized_family_circuit',
]
