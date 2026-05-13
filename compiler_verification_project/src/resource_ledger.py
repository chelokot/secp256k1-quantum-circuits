#!/usr/bin/env python3

from __future__ import annotations

from typing import Any, Dict, List, Mapping


def qroam_clean_stream_cost(domain_size: int, field_bits: int, block_size: int) -> Dict[str, int]:
    compute = (int(domain_size) + int(block_size) - 1) // int(block_size) + (int(block_size) - 1) * int(field_bits)
    measured_uncompute = (int(domain_size) + int(block_size) - 1) // int(block_size) + (int(block_size) - 1)
    return {
        'domain_size': int(domain_size),
        'field_bits': int(field_bits),
        'block_size': int(block_size),
        'target_register_qubits': int(field_bits),
        'junk_register_count': int(block_size) - 1,
        'junk_register_qubits': (int(block_size) - 1) * int(field_bits),
        'target_plus_junk_qubits': int(block_size) * int(field_bits),
        'lookup_compute_non_clifford': compute,
        'measured_uncompute_non_clifford': measured_uncompute,
        'per_stream_non_clifford': compute + measured_uncompute,
    }


def _owner(owner_id: str, logical_qubits: int, source_artifact: str, decomposition: Mapping[str, int]) -> Dict[str, Any]:
    return {
        'owner_id': owner_id,
        'logical_qubits': int(logical_qubits),
        'source_artifact': source_artifact,
        'decomposition': {key: int(value) for key, value in decomposition.items()},
        'decomposition_total': sum(int(value) for value in decomposition.values()),
    }


def _pareto_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in rows:
        dominated = any(
            int(other['full_oracle_non_clifford']) <= int(row['full_oracle_non_clifford'])
            and int(other['total_logical_qubits']) <= int(row['total_logical_qubits'])
            and (
                int(other['full_oracle_non_clifford']) < int(row['full_oracle_non_clifford'])
                or int(other['total_logical_qubits']) < int(row['total_logical_qubits'])
            )
            for other in rows
        )
        if not dominated:
            out.append(row)
    return out


def build_logical_resource_ledger(
    frontier: Mapping[str, Any],
    generated_block_inventories: Mapping[str, Any],
    streamed_lookup_resource: Mapping[str, Any],
    field_bits: int,
    public_google_baseline: Mapping[str, Any],
) -> Dict[str, Any]:
    selected = frontier['best_qubit_family']
    generated_lookup = {row['name']: row for row in generated_block_inventories['families']}
    generated = generated_lookup[selected['name']]
    reconstruction = generated['reconstruction']
    slot_family = next(row for row in frontier['slot_allocation_families'] if row['name'] == selected['slot_allocation_family'])
    slot_source_artifact = str(slot_family['source_artifact'])
    workspace = streamed_lookup_resource['workspace_contract']
    model = streamed_lookup_resource['streamed_data_selection_model']
    folded_workspace = int(workspace['folded_control_workspace_qubits'])
    qroam_block_size = int(model['qroam_block_size'])
    coordinate_bits = int(model['qroam_target_bitsize'])
    domain_size = int(model['folded_coordinate_domain_size'])
    stream_count = int(streamed_lookup_resource['capacity_check']['whole_oracle_stream_count'])
    selected_cost = qroam_clean_stream_cost(domain_size, coordinate_bits, qroam_block_size)
    base_without_streamed_qroam = (
        int(selected['full_oracle_non_clifford'])
        - int(model['whole_oracle_data_select_non_clifford'])
    )
    owners = [
        _owner(
            'arithmetic_slot_register_file',
            int(selected['arithmetic_slot_count']) * int(field_bits),
            slot_source_artifact,
            {'field_slots': int(selected['arithmetic_slot_count']) * int(field_bits)},
        ),
        _owner(
            'control_slot_register_file',
            int(selected['control_slot_count']),
            slot_source_artifact,
            {'control_bits': int(selected['control_slot_count'])},
        ),
        _owner(
            'lookup_workspace',
            int(selected['lookup_workspace_qubits']),
            'compiler_verification_project/artifacts/streamed_lookup_table_multiplier_resource.json',
            {
                'folded_control_workspace_qubits': folded_workspace,
                'qroam_clean_target_register_qubits': int(workspace['qroam_clean_target_register_qubits']),
                'qroam_clean_junk_register_qubits': int(workspace['qroam_clean_junk_register_qubits']),
            },
        ),
        _owner(
            'phase_shell_live_register',
            int(selected['live_phase_bits']),
            'compiler_verification_project/artifacts/phase_shell_lowerings.json',
            {'phase_bits': int(selected['live_phase_bits'])},
        ),
    ]
    tradeoff_rows: List[Dict[str, Any]] = []
    for candidate_block_size in range(1, 65):
        cost = qroam_clean_stream_cost(domain_size, coordinate_bits, candidate_block_size)
        full_oracle_non_clifford = base_without_streamed_qroam + stream_count * int(cost['per_stream_non_clifford'])
        total_logical_qubits = (
            int(selected['arithmetic_slot_count']) * int(field_bits)
            + int(selected['control_slot_count'])
            + folded_workspace
            + int(cost['target_plus_junk_qubits'])
            + int(selected['live_phase_bits'])
        )
        tradeoff_rows.append({
            **cost,
            'whole_oracle_stream_count': stream_count,
            'full_oracle_non_clifford': full_oracle_non_clifford,
            'total_logical_qubits': total_logical_qubits,
            'qubit_delta_vs_google_low_gate': total_logical_qubits - int(public_google_baseline['low_gate']['logical_qubits']),
            'qubit_delta_vs_google_low_qubit': total_logical_qubits - int(public_google_baseline['low_qubit']['logical_qubits']),
            'non_clifford_delta_vs_google_low_gate': full_oracle_non_clifford - int(public_google_baseline['low_gate']['non_clifford']),
            'non_clifford_delta_vs_google_low_qubit': full_oracle_non_clifford - int(public_google_baseline['low_qubit']['non_clifford']),
            'under_google_low_gate_non_clifford': full_oracle_non_clifford < int(public_google_baseline['low_gate']['non_clifford']),
            'under_google_low_qubit_non_clifford': full_oracle_non_clifford < int(public_google_baseline['low_qubit']['non_clifford']),
            'under_google_low_gate_qubits': total_logical_qubits < int(public_google_baseline['low_gate']['logical_qubits']),
            'under_google_low_qubit_qubits': total_logical_qubits < int(public_google_baseline['low_qubit']['logical_qubits']),
            'under_24m_non_clifford': full_oracle_non_clifford < 24_000_000,
            'under_1700_logical_qubits': total_logical_qubits < 1700,
        })
    selected_tradeoff = next(row for row in tradeoff_rows if int(row['block_size']) == qroam_block_size)
    best_qubit_under_google_low_gate = min(
        (row for row in tradeoff_rows if row['under_google_low_gate_non_clifford']),
        key=lambda row: (int(row['total_logical_qubits']), int(row['full_oracle_non_clifford'])),
    )
    sub24m_rows = [row for row in tradeoff_rows if row['under_24m_non_clifford']]
    best_qubit_under_24m = None if not sub24m_rows else min(
        sub24m_rows,
        key=lambda row: (int(row['total_logical_qubits']), int(row['full_oracle_non_clifford'])),
    )
    rows_under_24m_and_1700 = [
        row for row in tradeoff_rows
        if bool(row['under_24m_non_clifford']) and bool(row['under_1700_logical_qubits'])
    ]
    peak_total = sum(int(owner['logical_qubits']) for owner in owners)
    owner_failures = [
        owner for owner in owners
        if int(owner['logical_qubits']) != int(owner['decomposition_total'])
    ]
    checks = {
        'owner_decompositions_match': not owner_failures,
        'selected_tradeoff_matches_frontier_non_clifford': int(selected_tradeoff['full_oracle_non_clifford']) == int(selected['full_oracle_non_clifford']),
        'selected_tradeoff_matches_frontier_qubits': int(selected_tradeoff['total_logical_qubits']) == int(selected['total_logical_qubits']),
        'peak_total_matches_frontier': peak_total == int(selected['total_logical_qubits']),
        'qroam_gate_workspace_same_block_size': int(selected_cost['block_size']) == qroam_block_size,
        'qroam_workspace_matches_cost_model': int(workspace['qroam_clean_target_plus_junk_qubits']) == int(selected_cost['target_plus_junk_qubits']),
        'selected_row_is_lowest_qubit_standard_qroam_under_google_gate_count': int(selected_tradeoff['block_size']) == int(best_qubit_under_google_low_gate['block_size']),
        'no_standard_qroamclean_tradeoff_row_hits_24m_and_1700': not rows_under_24m_and_1700,
    }
    return {
        'schema': 'compiler-project-logical-resource-ledger-v1',
        'selected_family': selected['name'],
        'selected_family_summary': {
            'full_oracle_non_clifford': int(selected['full_oracle_non_clifford']),
            'total_logical_qubits': int(selected['total_logical_qubits']),
            'qroam_clean_block_size': qroam_block_size,
        },
        'source_artifacts': {
            'family_frontier': 'compiler_verification_project/artifacts/family_frontier.json',
            'generated_block_inventories': 'compiler_verification_project/artifacts/generated_block_inventories.json',
            'streamed_lookup_table_multiplier_resource': 'compiler_verification_project/artifacts/streamed_lookup_table_multiplier_resource.json',
        },
        'peak_live_qubit_owners': owners,
        'peak_live_qubit_total_from_owners': peak_total,
        'qroam_clean_tradeoff_sweep': {
            'base_non_clifford_without_streamed_qroam': base_without_streamed_qroam,
            'rows': tradeoff_rows,
            'selected_row': selected_tradeoff,
            'pareto_rows': _pareto_rows(tradeoff_rows),
            'best_qubit_under_google_low_gate_non_clifford': best_qubit_under_google_low_gate,
            'best_qubit_under_24m_non_clifford': best_qubit_under_24m,
            'rows_under_24m_and_1700': rows_under_24m_and_1700,
        },
        'checks': checks,
        'pass': all(checks.values()),
        'notes': [
            'This ledger is the repo-level guard against mixing QROAMClean gate and workspace models: the block size drives both non-Clifford cost and live target-plus-junk qubits.',
            'The peak live-qubit total is derived by summing named owners with numeric decomposition, not by a free-form prose claim.',
        ],
    }


__all__ = ['build_logical_resource_ledger', 'qroam_clean_stream_cost']
