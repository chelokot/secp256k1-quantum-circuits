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
    baseline_runtime_values: Dict[str, List[float]] = {name: [] for name in google_baseline}
    baseline_space_values: Dict[str, List[float]] = {name: [] for name in google_baseline}

    for transfer_row in exact_transfer['families']:
        family = family_rows[transfer_row['family']]
        baseline_transfers = transfer_row['baseline_transfers']
        for baseline_name, baseline_transfer in baseline_transfers.items():
            baseline_runtime_values[baseline_name].append(baseline_transfer['heuristic_time_efficient_days_if_baseline_maps_to_10d'])
            baseline_space_values[baseline_name].append(baseline_transfer['same_density_physical_qubits_if_baseline_maps_to_26k'])
        cases.append({
            'family': transfer_row['family'],
            'exact_non_clifford': family['full_oracle_non_clifford'],
            'exact_logical_qubits': family['total_logical_qubits'],
            'baseline_transfers': baseline_transfers,
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

    runtime_values = [
        value
        for values in baseline_runtime_values.values()
        for value in values
    ]
    space_values = [
        value
        for values in baseline_space_values.values()
        for value in values
    ]
    publication_runtime_range = f'{min(runtime_values):.1f}-{max(runtime_values):.1f} days'
    publication_space_range = f'{min(space_values) / 1000:.1f}k-{max(space_values) / 1000:.1f}k physical qubits'
    baseline_ranges = {
        baseline_name: {
            'runtime_days_if_baseline_maps_to_10d_min': min(baseline_runtime_values[baseline_name]),
            'runtime_days_if_baseline_maps_to_10d_max': max(baseline_runtime_values[baseline_name]),
            'same_density_physical_qubits_if_baseline_maps_to_26k_min': min(baseline_space_values[baseline_name]),
            'same_density_physical_qubits_if_baseline_maps_to_26k_max': max(baseline_space_values[baseline_name]),
        }
        for baseline_name in google_baseline
    }

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
        'baseline_transfer_ranges': baseline_ranges,
        'headline_ranges': {
            'time_efficient_days_if_90M_min': baseline_ranges['low_qubit']['runtime_days_if_baseline_maps_to_10d_min'],
            'time_efficient_days_if_90M_max': baseline_ranges['low_qubit']['runtime_days_if_baseline_maps_to_10d_max'],
            'time_efficient_days_if_70M_min': baseline_ranges['low_gate']['runtime_days_if_baseline_maps_to_10d_min'],
            'time_efficient_days_if_70M_max': baseline_ranges['low_gate']['runtime_days_if_baseline_maps_to_10d_max'],
            'same_density_physical_qubits_if_1200_min': baseline_ranges['low_qubit']['same_density_physical_qubits_if_baseline_maps_to_26k_min'],
            'same_density_physical_qubits_if_1200_max': baseline_ranges['low_qubit']['same_density_physical_qubits_if_baseline_maps_to_26k_max'],
            'same_density_physical_qubits_if_1450_min': baseline_ranges['low_gate']['same_density_physical_qubits_if_baseline_maps_to_26k_min'],
            'same_density_physical_qubits_if_1450_max': baseline_ranges['low_gate']['same_density_physical_qubits_if_baseline_maps_to_26k_max'],
        },
        'cases': cases,
        'publication_safe_summary': {
            'single_sentence': f"If the repository's central standard-QROM compiler family is transferred into the neutral-atom architecture of Cain et al. under fixed cycle-time and parallelism assumptions, the checked result maps to roughly {publication_runtime_range} and about {publication_space_range} under the stored reference-line transfers.",
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
