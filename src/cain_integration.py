#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from common import artifact_projection_path, dump_json, load_json


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


def _iter_projection_cases(projection: Dict[str, Any]) -> List[Dict[str, Any]]:
    cases = [
        {
            'model_name': projection['model_name'],
            'model_status': 'default',
            'ecdlp': projection['optimized_ecdlp_projection'],
        }
    ]
    for alternative in projection.get('alternative_backend_scenarios', []):
        cases.append({
            'model_name': alternative['model_name'],
            'model_status': alternative['status'],
            'ecdlp': alternative['ecdlp'],
        })
    return cases


def build_cain_integration_summary(repo_root: Path) -> Dict[str, Any]:
    projection = load_json(artifact_projection_path(repo_root / 'artifacts', 'resource_projection.json'))
    google_baseline = projection['public_google_baseline']

    cases: List[Dict[str, Any]] = []
    headline_times: List[float] = []
    headline_balanced: List[float] = []
    time_efficient_spaces: List[float] = []
    min_spaces: List[float] = []

    for model_case in _iter_projection_cases(projection):
        optimized = model_case['ecdlp']
        for baseline_key in ('low_qubit', 'low_gate'):
            baseline = google_baseline[baseline_key]
            logical_ratio = optimized['logical_qubits_total'] / baseline['logical_qubits']
            for lookup_label, lookup_key in (
                ('2lookup', 'lookup_model_2channel'),
                ('3lookup', 'lookup_model_3channel'),
            ):
                optimized_non_clifford = optimized[lookup_key]['total_non_clifford']
                non_clifford_ratio = optimized_non_clifford / baseline['non_clifford']
                projected_time_efficient = CAIN_2026['time_efficient_runtime_days'] * non_clifford_ratio
                projected_balanced = CAIN_2026['balanced_runtime_days'] * non_clifford_ratio
                same_density_time_efficient_space = CAIN_2026['time_efficient_physical_qubits'] * logical_ratio
                same_density_min_space = CAIN_2026['headline_min_physical_qubits'] * logical_ratio

                headline_times.append(projected_time_efficient)
                headline_balanced.append(projected_balanced)
                time_efficient_spaces.append(same_density_time_efficient_space)
                min_spaces.append(same_density_min_space)

                cases.append({
                    'source_model': model_case['model_name'],
                    'source_model_status': model_case['model_status'],
                    'google_baseline_line': baseline_key,
                    'optimized_lookup_model': lookup_label,
                    'google_logical_qubits': baseline['logical_qubits'],
                    'google_non_clifford': baseline['non_clifford'],
                    'optimized_logical_qubits': optimized['logical_qubits_total'],
                    'optimized_non_clifford': optimized_non_clifford,
                    'ratios': {
                        'logical_qubit_ratio': logical_ratio,
                        'non_clifford_ratio': non_clifford_ratio,
                        'logical_qubit_gain': baseline['logical_qubits'] / optimized['logical_qubits_total'],
                        'non_clifford_gain': baseline['non_clifford'] / optimized_non_clifford,
                    },
                    'runtime_transfer': {
                        'assumption': 'Fixed physical architecture, cycle time, and parallelization regime; runtime scales with non-Clifford ratio.',
                        'projected_time_efficient_days': projected_time_efficient,
                        'projected_balanced_days': projected_balanced,
                    },
                    'space_transfer': {
                        'assumption': 'Logical-to-physical density is inherited from the cited Cain reference line.',
                        'same_density_time_efficient_physical_qubits': same_density_time_efficient_space,
                        'same_density_min_space_physical_qubits': same_density_min_space,
                    },
                })

    return {
        'integration_name': 'cain_2026_neutral_atom_transfer_v2',
        'warning': 'This file combines a secp256k1-specialized logical projection with a P-256 physical architecture paper. Runtime and space are transferred separately and remain approximate.',
        'source_papers': {
            'our_repository_baseline': {
                'path': 'artifacts/projections/resource_projection.json',
            },
            'cain_2026': CAIN_2026,
        },
        'headline_ranges': {
            'projected_time_efficient_days_min': min(headline_times),
            'projected_time_efficient_days_max': max(headline_times),
            'projected_balanced_days_min': min(headline_balanced),
            'projected_balanced_days_max': max(headline_balanced),
            'same_density_time_efficient_physical_qubits_min': min(time_efficient_spaces),
            'same_density_time_efficient_physical_qubits_max': max(time_efficient_spaces),
            'same_density_min_space_physical_qubits_min': min(min_spaces),
            'same_density_min_space_physical_qubits_max': max(min_spaces),
        },
        'cases': cases,
        'publication_safe_summary': {
            'single_sentence': "If the repository's optimized logical secp256k1 projection is transferred into the neutral-atom architecture of Cain et al. under fixed cycle-time and parallelism assumptions, the current supported backend family maps to roughly 2.5-3.3 days on the time-efficient line and about 6.1k-19.1k physical qubits under same-density scaling, depending on which public baseline line and backend scenario are used.",
            'do_not_say': [
                'Do not say the paper is beaten on its own P-256 target without recompiling for P-256.',
                'Do not say any single runtime or physical-qubit number is exact; the file intentionally reports a scenario range.',
                'Do not say the transfer is theorem-proved end-to-end.',
            ],
        },
    }


def write_cain_integration_summary(repo_root: Path) -> Dict[str, Any]:
    summary = build_cain_integration_summary(repo_root)
    dump_json(repo_root / 'results' / 'cain_2026_integration_summary.json', summary)
    return summary
