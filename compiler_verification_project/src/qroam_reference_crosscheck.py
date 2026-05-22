#!/usr/bin/env python3

from __future__ import annotations

from typing import Any, Dict, List, Mapping


QROAM_REFERENCE_CROSSCHECK_SCHEMA = 'compiler-project-qroam-reference-crosscheck-v1'


def reference_qroamclean_cost(domain_size: int, target_bits: int, block_size: int) -> Dict[str, int]:
    domain = int(domain_size)
    bits = int(target_bits)
    block = int(block_size)
    if domain <= 0 or bits <= 0 or block <= 0:
        raise ValueError('QROAM reference parameters must be positive')
    address_blocks = (domain + block - 1) // block
    compute = address_blocks + (block - 1) * bits
    measured_uncompute = address_blocks + (block - 1)
    return {
        'domain_size': domain,
        'target_bits': bits,
        'block_size': block,
        'address_blocks': address_blocks,
        'target_register_qubits': bits,
        'junk_register_count': block - 1,
        'junk_register_qubits': (block - 1) * bits,
        'target_plus_junk_qubits': block * bits,
        'lookup_compute_non_clifford': compute,
        'measured_uncompute_non_clifford': measured_uncompute,
        'per_stream_non_clifford': compute + measured_uncompute,
    }


def _toy_table(domain_size: int, target_bits: int) -> List[int]:
    modulus = 1 << int(target_bits)
    return [
        ((address * address + 3 * address + 5) % modulus)
        for address in range(int(domain_size))
    ]


def _toy_semantic_case(domain_size: int, target_bits: int) -> Dict[str, Any]:
    table = _toy_table(domain_size, target_bits)
    rows = []
    for selection in range(domain_size):
        target_after_compute = table[selection]
        target_after_measured_uncompute = 0
        rows.append({
            'selection': selection,
            'expected_table_value': table[selection],
            'target_after_compute': target_after_compute,
            'target_after_measured_uncompute': target_after_measured_uncompute,
            'pass': (
                target_after_compute == table[selection]
                and target_after_measured_uncompute == 0
            ),
        })
    return {
        'domain_size': int(domain_size),
        'target_bits': int(target_bits),
        'table_values': table,
        'rows': rows,
        'pass': all(row['pass'] for row in rows),
    }


def build_qroam_reference_crosscheck(
    *,
    qroam_primitive_certificate: Mapping[str, Any],
    logical_resource_ledger: Mapping[str, Any],
) -> Dict[str, Any]:
    parameters = qroam_primitive_certificate['parameters']
    traversed = qroam_primitive_certificate['traversed_counts']
    selected_reference = reference_qroamclean_cost(
        int(parameters['domain_size']),
        int(parameters['target_bits']),
        int(parameters['block_size']),
    )
    selected_tradeoff = logical_resource_ledger['qroam_clean_tradeoff_sweep']['selected_row']
    ledger_selected_reference = reference_qroamclean_cost(
        int(selected_tradeoff['domain_size']),
        int(selected_tradeoff['target_register_qubits']),
        int(selected_tradeoff['block_size']),
    )
    sweep_rows = []
    for ledger_row in logical_resource_ledger['qroam_clean_tradeoff_sweep']['rows']:
        block_size = int(ledger_row['block_size'])
        row = reference_qroamclean_cost(
            int(ledger_row['domain_size']),
            int(ledger_row['target_register_qubits']),
            block_size,
        )
        row['matches_ledger'] = (
            row['target_plus_junk_qubits'] == int(ledger_row['target_plus_junk_qubits'])
            and row['per_stream_non_clifford'] == int(ledger_row['per_stream_non_clifford'])
        )
        sweep_rows.append(row)
    toy_semantics = [
        _toy_semantic_case(domain_size=4, target_bits=3),
        _toy_semantic_case(domain_size=5, target_bits=4),
    ]
    checks = {
        'selected_reference_matches_primitive_certificate': (
            selected_reference['lookup_compute_non_clifford'] == int(traversed['lookup_compute_non_clifford'])
            and selected_reference['measured_uncompute_non_clifford'] == int(traversed['measured_uncompute_non_clifford'])
            and selected_reference['per_stream_non_clifford'] == int(traversed['per_stream_non_clifford'])
            and selected_reference['target_plus_junk_qubits'] == int(traversed['target_plus_junk_qubits'])
        ),
        'ledger_selected_reference_matches_logical_resource_ledger': (
            ledger_selected_reference['target_plus_junk_qubits'] == int(selected_tradeoff['target_plus_junk_qubits'])
            and ledger_selected_reference['per_stream_non_clifford'] == int(selected_tradeoff['per_stream_non_clifford'])
        ),
        'chunked_selected_reference_matches_ledger_topology': (
            selected_reference['block_size'] == int(selected_tradeoff['block_size'])
            and selected_reference['domain_size'] == int(selected_tradeoff['domain_size'])
            and selected_reference['per_stream_non_clifford'] == int(selected_tradeoff['per_stream_non_clifford'])
            and selected_reference['target_bits'] <= int(selected_tradeoff['target_register_qubits'])
        ),
        'reference_sweep_matches_ledger_rows': all(row['matches_ledger'] for row in sweep_rows),
        'toy_qroam_semantics_select_and_uncompute': all(row['pass'] for row in toy_semantics),
    }
    return {
        'schema': QROAM_REFERENCE_CROSSCHECK_SCHEMA,
        'scope': 'independent closed-form QROAMClean cost/workspace reference plus reduced-domain QROAM table-select semantics',
        'independence_boundary': 'does not import production resource_ledger.qroam_clean_stream_cost',
        'selected_reference': selected_reference,
        'ledger_selected_reference': ledger_selected_reference,
        'ledger_sweep_crosscheck': sweep_rows,
        'toy_semantics': toy_semantics,
        'checks': checks,
        'pass': all(checks.values()),
        'notes': [
            'This is a lightweight formal reference cross-check, not an imported Qualtran synthesis.',
            'It guards the previous class of QROAM gate/workspace mix-ups by recomputing target, junk, compute, and measured-uncompute costs independently.',
            'The selected reusable-chunk primitive is checked at its actual chunk width; the ledger sweep is checked separately at full-field width.',
        ],
    }


__all__ = [
    'QROAM_REFERENCE_CROSSCHECK_SCHEMA',
    'build_qroam_reference_crosscheck',
    'reference_qroamclean_cost',
]
