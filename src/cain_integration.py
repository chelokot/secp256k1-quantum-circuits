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


def build_cain_integration_summary(repo_root: Path) -> Dict[str, Any]:
    projection = load_json(artifact_projection_path(repo_root / 'artifacts', 'resource_projection.json'))
    google_baseline = projection['public_google_baseline']
    optimized = projection['optimized_ecdlp_projection']
    gains = projection['improvement_vs_google']

    cases: List[Dict[str, Any]] = []
    headline_times: List[float] = []
    headline_balanced: List[float] = []
    naive_spaces: List[float] = []
    half_fixed_spaces: List[float] = []

    for baseline_key, gain_key in (('low_qubit', 'versus_low_qubit'), ('low_gate', 'versus_low_gate')):
        baseline = google_baseline[baseline_key]
        for lookup_label, lookup_key, gain_field in (
            ('2lookup', 'lookup_model_2channel', 'toffoli_gain_2lookup'),
            ('3lookup', 'lookup_model_3channel', 'toffoli_gain_3lookup'),
        ):
            optimized_non_clifford = optimized[lookup_key]['total_non_clifford']
            runtime_speedup = gains[gain_key][gain_field]
            projected_time_efficient = CAIN_2026['time_efficient_runtime_days'] / runtime_speedup
            projected_balanced = CAIN_2026['balanced_runtime_days'] / runtime_speedup
            naive_linear_space = CAIN_2026['time_efficient_physical_qubits'] * (
                optimized['logical_qubits_total'] / baseline['logical_qubits']
            )
            half_fixed_space = (CAIN_2026['time_efficient_physical_qubits'] * 0.5) + (naive_linear_space * 0.5)

            headline_times.append(projected_time_efficient)
            headline_balanced.append(projected_balanced)
            naive_spaces.append(naive_linear_space)
            half_fixed_spaces.append(half_fixed_space)

            cases.append({
                'google_baseline_line': baseline_key,
                'optimized_lookup_model': lookup_label,
                'google_logical_qubits': baseline['logical_qubits'],
                'google_non_clifford': baseline['non_clifford'],
                'optimized_logical_qubits': optimized['logical_qubits_total'],
                'optimized_non_clifford': optimized_non_clifford,
                'runtime_speedup_factor': runtime_speedup,
                'projected_time_efficient_days': projected_time_efficient,
                'projected_balanced_days': projected_balanced,
                'space_transfer': {
                    'same_hardware_regime_physical_qubits': CAIN_2026['time_efficient_physical_qubits'],
                    'naive_linear_logical_scaling_physical_qubits': naive_linear_space,
                    'half_fixed_overhead_scaling_physical_qubits': half_fixed_space,
                },
                'assumptions': [
                    'Runtime is transferred linearly with the dominant non-Clifford/Toffoli budget.',
                    'The physical architecture, cycle time, and parallelization regime are held fixed.',
                    'Space scaling is heuristic only; time transfer is the main supported comparison.',
                ],
            })

    return {
        'integration_name': 'cain_2026_neutral_atom_transfer_v1',
        'warning': 'This file combines a secp256k1-specialized logical projection with a P-256 physical architecture paper. The time transfer is approximate; the space transfer is only heuristic.',
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
            'naive_linear_space_physical_qubits_min': min(naive_spaces),
            'naive_linear_space_physical_qubits_max': max(naive_spaces),
            'half_fixed_overhead_space_physical_qubits_min': min(half_fixed_spaces),
            'half_fixed_overhead_space_physical_qubits_max': max(half_fixed_spaces),
        },
        'cases': cases,
        'publication_safe_summary': {
            'single_sentence': "If the optimized secp256k1 logical layer is transferred into the neutral-atom architecture of Cain et al. under constant cycle-time and parallelism assumptions, the headline ECC runtime moves from about 10 days to roughly 3-4 days, while physical-qubit savings are likely more modest and much more model-sensitive.",
            'do_not_say': [
                'Do not say the paper is beaten on its own P-256 target without recompiling for P-256.',
                'Do not say the physical qubit count is exactly 20k or exactly 26k for our circuit.',
                'Do not say the transfer is theorem-proved end-to-end.',
            ],
        },
    }


def write_cain_integration_summary(repo_root: Path) -> Dict[str, Any]:
    summary = build_cain_integration_summary(repo_root)
    dump_json(repo_root / 'results' / 'cain_2026_integration_summary.json', summary)
    return summary
