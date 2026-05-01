#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from common import dump_json, load_json


CAIN_2026 = {
    'paper_id': 'arXiv:2603.28627',
    'title': "Shor's algorithm is possible with as few as 10,000 reconfigurable atomic qubits",
    'target_curve_in_paper': 'P-256',
    'time_efficient_runtime_days': 10.0,
    'balanced_runtime_days': 264.0,
    'time_efficient_physical_qubits': 26_000,
    'headline_min_physical_qubits': 10_000,
    'cycle_time_ms': 1.0,
}

def build_cain_integration_summary(repo_root: Path) -> Dict[str, Any]:
    frontier_path = repo_root / 'compiler_verification_project' / 'artifacts' / 'family_frontier.json'
    exact_transfer_path = repo_root / 'compiler_verification_project' / 'artifacts' / 'cain_exact_transfer.json'
    frontier = load_json(frontier_path)
    exact_transfer = load_json(exact_transfer_path)
    google_baseline = frontier['public_google_baseline']
    family_rows = {entry['name']: entry for entry in frontier['families']}

    cases: List[Dict[str, Any]] = []
    runtime_90m_values: List[float] = []
    runtime_70m_values: List[float] = []
    time_efficient_space_values: List[float] = []
    low_gate_space_values: List[float] = []

    for transfer_row in exact_transfer['families']:
        family = family_rows[transfer_row['family']]
        runtime_90m_values.append(transfer_row['heuristic_time_efficient_days_if_90M_maps_to_10d'])
        runtime_70m_values.append(transfer_row['heuristic_time_efficient_days_if_70M_maps_to_10d'])
        time_efficient_space_values.append(transfer_row['same_density_physical_qubits_if_1200_maps_to_26k'])
        low_gate_space_values.append(transfer_row['same_density_physical_qubits_if_1450_maps_to_26k'])
        cases.append({
            'family': transfer_row['family'],
            'exact_non_clifford': family['full_oracle_non_clifford'],
            'exact_logical_qubits': family['total_logical_qubits'],
            'runtime_transfer': {
                'assumption': 'Fixed physical architecture, cycle time, and parallelization regime; runtime scales with exact-family non-Clifford ratio.',
                'time_efficient_days_if_90M_maps_to_10d': transfer_row['heuristic_time_efficient_days_if_90M_maps_to_10d'],
                'time_efficient_days_if_70M_maps_to_10d': transfer_row['heuristic_time_efficient_days_if_70M_maps_to_10d'],
            },
            'space_transfer': {
                'assumption': 'Logical-to-physical density is inherited from the cited Cain reference line.',
                'same_density_physical_qubits_if_1200_maps_to_26k': transfer_row['same_density_physical_qubits_if_1200_maps_to_26k'],
                'same_density_physical_qubits_if_1450_maps_to_26k': transfer_row['same_density_physical_qubits_if_1450_maps_to_26k'],
            },
        })

    runtime_values = runtime_90m_values + runtime_70m_values
    space_values = time_efficient_space_values + low_gate_space_values
    publication_runtime_range = f'{min(runtime_values):.1f}-{max(runtime_values):.1f} days'
    publication_space_range = f'{min(space_values) / 1000:.1f}k-{max(space_values) / 1000:.1f}k physical qubits'

    return {
        'integration_name': 'cain_2026_neutral_atom_transfer_exact_family_v2',
        'warning': 'This file combines a secp256k1 exact compiler-family frontier with a P-256 physical architecture paper. Runtime and space remain approximate transfer studies.',
        'source_artifacts': {
            'exact_frontier': {'path': 'compiler_verification_project/artifacts/family_frontier.json'},
            'exact_estimator_results': {'path': 'compiler_verification_project/artifacts/azure_resource_estimator_results.json'},
            'exact_transfer_table': {'path': 'compiler_verification_project/artifacts/cain_exact_transfer.json'},
        },
        'source_papers': {
            'cain_2026': CAIN_2026,
        },
        'public_google_baseline': google_baseline,
        'headline_ranges': {
            'time_efficient_days_if_90M_min': min(runtime_90m_values),
            'time_efficient_days_if_90M_max': max(runtime_90m_values),
            'time_efficient_days_if_70M_min': min(runtime_70m_values),
            'time_efficient_days_if_70M_max': max(runtime_70m_values),
            'same_density_physical_qubits_if_1200_min': min(time_efficient_space_values),
            'same_density_physical_qubits_if_1200_max': max(time_efficient_space_values),
            'same_density_physical_qubits_if_1450_min': min(low_gate_space_values),
            'same_density_physical_qubits_if_1450_max': max(low_gate_space_values),
        },
        'cases': cases,
        'publication_safe_summary': {
            'single_sentence': f"If the repository's central named-boundary compiler family is transferred into the neutral-atom architecture of Cain et al. under fixed cycle-time and parallelism assumptions, the checked result maps to roughly {publication_runtime_range} and about {publication_space_range} under the stored reference-line transfers.",
            'do_not_say': [
                'Do not say the paper is beaten on its own P-256 target without recompiling for P-256.',
                'Do not say the transferred runtime or physical-qubit range is exact; it is still a cross-paper architecture transfer.',
                'Do not say the transfer is theorem-proved end-to-end.',
            ],
        },
    }


def write_cain_integration_summary(repo_root: Path) -> Dict[str, Any]:
    summary = build_cain_integration_summary(repo_root)
    dump_json(repo_root / 'results' / 'cain_2026_integration_summary.json', summary)
    return summary
