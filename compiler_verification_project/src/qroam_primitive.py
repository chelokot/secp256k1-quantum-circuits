#!/usr/bin/env python3

from __future__ import annotations

import json
from typing import Any, Dict, List

from common import sha256_bytes
from resource_ledger import qroam_clean_stream_cost


def _digest_row(row: Dict[str, Any]) -> str:
    return sha256_bytes(json.dumps(row, sort_keys=True, separators=(',', ':')).encode())


def _merkle_root(hashes: List[str]) -> str:
    if not hashes:
        return sha256_bytes(b'')
    level = list(hashes)
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [
            sha256_bytes((level[index] + level[index + 1]).encode())
            for index in range(0, len(level), 2)
        ]
    return level[0]


def _selection_bit_count(domain_size: int) -> int:
    return (int(domain_size) - 1).bit_length()


def _operation_row(*, phase: str, address: int, domain_size: int, target_bits: int) -> Dict[str, Any]:
    selection_bit_count = _selection_bit_count(domain_size)
    return {
        'phase': phase,
        'address': int(address),
        'primitive': 'qroamclean_k1_unary_iteration_word_step',
        'ccx': 1,
        'selection_bit_count': selection_bit_count,
        'selection_control_wires': [
            f'selection.bit[{bit_index}]'
            for bit_index in range(selection_bit_count)
        ],
        'selection_control_pattern_lsb_first': [
            (int(address) >> bit_index) & 1
            for bit_index in range(selection_bit_count)
        ],
        'target_register': {
            'wire_template': 'qroam_target.bit[{bit_index}]',
            'bit_count': int(target_bits),
        },
        'loaded_word_source': {
            'table_address': int(address),
            'bit_range': [0, int(target_bits)],
        },
    }


def _segment_digest(*, phase: str, start_index: int, end_index: int, domain_size: int, target_bits: int) -> str:
    digest = sha256_bytes(b'')
    for address in range(start_index, end_index):
        row = _operation_row(
            phase=phase,
            address=address,
            domain_size=domain_size,
            target_bits=target_bits,
        )
        digest = sha256_bytes((digest + _digest_row(row)).encode())
    return digest


def _segments(*, phase: str, domain_size: int, target_bits: int, segment_size: int) -> List[Dict[str, Any]]:
    rows = []
    for start in range(0, domain_size, segment_size):
        end = min(start + segment_size, domain_size)
        rows.append({
            'phase': phase,
            'start_address': start,
            'end_address_exclusive': end,
            'operation_count': end - start,
            'ccx': end - start,
            'selection_bit_count': _selection_bit_count(domain_size),
            'target_register_qubits': int(target_bits),
            'sha256': _segment_digest(
                phase=phase,
                start_index=start,
                end_index=end,
                domain_size=domain_size,
                target_bits=target_bits,
            ),
        })
    return rows


def _preview_rows(*, phase: str, domain_size: int, target_bits: int) -> List[Dict[str, Any]]:
    addresses = [0, 1, max(0, int(domain_size) - 2), int(domain_size) - 1]
    return [
        _operation_row(
            phase=phase,
            address=address,
            domain_size=domain_size,
            target_bits=target_bits,
        )
        for address in dict.fromkeys(addresses)
    ]


def build_qroam_k1_primitive_certificate(
    *,
    domain_size: int,
    target_bits: int,
    block_size: int = 1,
    segment_size: int = 4096,
) -> Dict[str, Any]:
    cost = qroam_clean_stream_cost(domain_size, target_bits, block_size)
    compute_segments = _segments(
        phase='compute',
        domain_size=int(domain_size),
        target_bits=int(target_bits),
        segment_size=int(segment_size),
    )
    cleanup_segments = _segments(
        phase='measured_uncompute',
        domain_size=int(domain_size),
        target_bits=int(target_bits),
        segment_size=int(segment_size),
    )
    all_segments = compute_segments + cleanup_segments
    compute_ccx = sum(row['ccx'] for row in compute_segments)
    cleanup_ccx = sum(row['ccx'] for row in cleanup_segments)
    wire_catalog = {
        'selection_register': {
            'role': 'folded table address',
            'qubits': (int(domain_size) - 1).bit_length(),
            'logical_owner': 'caller_control_registers',
        },
        'target_register': {
            'role': 'QROAM target chunk',
            'qubits': int(target_bits),
            'logical_owner': 'lookup_workspace',
        },
        'junk_registers': {
            'role': 'QROAMClean junk registers',
            'register_count': int(block_size) - 1,
            'qubits': int(cost['junk_register_qubits']),
            'logical_owner': 'lookup_workspace',
        },
    }
    checks = {
        'block_size_is_k1': int(block_size) == 1,
        'segment_rows_cover_compute_domain': compute_ccx == int(domain_size),
        'segment_rows_cover_cleanup_domain': cleanup_ccx == int(domain_size),
        'segment_rows_bind_selection_and_target_widths': all(
            int(row['selection_bit_count']) == int(wire_catalog['selection_register']['qubits'])
            and int(row['target_register_qubits']) == int(target_bits)
            for row in all_segments
        ),
        'traversed_counts_match_qroamclean_cost': (
            compute_ccx == int(cost['lookup_compute_non_clifford'])
            and cleanup_ccx == int(cost['measured_uncompute_non_clifford'])
            and compute_ccx + cleanup_ccx == int(cost['per_stream_non_clifford'])
        ),
        'workspace_matches_cost_model': (
            int(wire_catalog['target_register']['qubits'])
            + int(wire_catalog['junk_registers']['qubits'])
            == int(cost['target_plus_junk_qubits'])
        ),
        'no_junk_registers_for_k1': int(wire_catalog['junk_registers']['qubits']) == 0,
    }
    return {
        'schema': 'compiler-project-qroam-k1-primitive-certificate-v1',
        'construction': 'standard QROAMClean K=1 unary-iteration primitive over the full folded lookup domain',
        'parameters': {
            'domain_size': int(domain_size),
            'target_bits': int(target_bits),
            'block_size': int(block_size),
            'segment_size': int(segment_size),
        },
        'wire_catalog': wire_catalog,
        'operation_stream': {
            'operation_schema': 'qroamclean-k1-unary-iteration-word-step-v1',
            'operation_level': 'word_level_unary_iteration_rows',
            'selection_bit_count': int(wire_catalog['selection_register']['qubits']),
            'target_register_qubits': int(target_bits),
            'segments': all_segments,
            'segment_count': len(all_segments),
            'segment_merkle_root_sha256': _merkle_root([row['sha256'] for row in all_segments]),
            'preview_head': _preview_rows(
                phase='compute',
                domain_size=int(domain_size),
                target_bits=int(target_bits),
            ),
            'preview_tail': _preview_rows(
                phase='measured_uncompute',
                domain_size=int(domain_size),
                target_bits=int(target_bits),
            ),
        },
        'traversed_counts': {
            'lookup_compute_non_clifford': compute_ccx,
            'measured_uncompute_non_clifford': cleanup_ccx,
            'per_stream_non_clifford': compute_ccx + cleanup_ccx,
            'target_register_qubits': int(target_bits),
            'junk_register_qubits': int(cost['junk_register_qubits']),
            'target_plus_junk_qubits': int(cost['target_plus_junk_qubits']),
        },
        'qroamclean_cost_model': cost,
        'checks': checks,
        'pass': all(checks.values()),
        'notes': [
            'This is a deterministic word-level unary-iteration stream certificate with concrete selection-control and target-register contracts; it is still not a Clifford-complete routed bit-level QROAM netlist.',
            'Counts are obtained by traversing generated compute and measured-uncompute unary-iteration word segments, then checked against the QROAMClean K=1 resource rule.',
        ],
    }


__all__ = ['build_qroam_k1_primitive_certificate']
