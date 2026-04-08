#!/usr/bin/env python3

from __future__ import annotations

from typing import Any, Dict, List, Mapping


def _recount_family_row(ft_ir_family: Mapping[str, Any], public_google_baseline: Mapping[str, Any]) -> Dict[str, Any]:
    primitive_totals = {'ccx': 0, 'cx': 0, 'x': 0, 'measurement': 0}
    total_logical_qubits = 0
    phase_shell_measurements = 0
    phase_shell_rotations = 0
    for entry in ft_ir_family['leaf_sigma']:
        semantics = entry['resource_profile']['resource_semantics']
        if semantics == 'additive_primitive':
            for key in primitive_totals:
                primitive_totals[key] += int(entry['primitive_counts_total'][key])
        elif semantics == 'peak_live_qubits':
            total_logical_qubits += int(entry['logical_qubits_total'])
        elif semantics == 'additive_phase_measurements':
            phase_shell_measurements += int(entry['count_total'])
        elif semantics == 'additive_phase_rotations':
            phase_shell_rotations += int(entry['count_total'])
    low_qubit = public_google_baseline['low_qubit']
    low_gate = public_google_baseline['low_gate']
    full_oracle_non_clifford = int(primitive_totals['ccx'])
    return {
        'name': ft_ir_family['name'],
        'lookup_family': ft_ir_family['lookup_family'],
        'phase_shell': ft_ir_family['phase_shell'],
        'arithmetic_kernel_family': ft_ir_family['arithmetic_kernel_family'],
        'full_oracle_non_clifford': full_oracle_non_clifford,
        'primitive_totals': primitive_totals,
        'total_logical_qubits': int(total_logical_qubits),
        'phase_shell_measurements': int(phase_shell_measurements),
        'phase_shell_rotations': int(phase_shell_rotations),
        'graph_summary': dict(ft_ir_family['graph']['summary']),
        'improvement_vs_google_low_qubit': low_qubit['non_clifford'] / full_oracle_non_clifford,
        'improvement_vs_google_low_gate': low_gate['non_clifford'] / full_oracle_non_clifford,
        'qubit_ratio_vs_google_low_qubit': low_qubit['logical_qubits'] / int(total_logical_qubits),
        'qubit_ratio_vs_google_low_gate': low_gate['logical_qubits'] / int(total_logical_qubits),
    }


def build_whole_oracle_recount(
    ft_ir_compositions: Mapping[str, Any],
    public_google_baseline: Mapping[str, Any],
) -> Dict[str, Any]:
    families = [
        _recount_family_row(family, public_google_baseline)
        for family in ft_ir_compositions['families']
    ]
    best_gate_family = min(
        families,
        key=lambda row: (int(row['full_oracle_non_clifford']), int(row['total_logical_qubits'])),
    )
    best_qubit_family = min(
        families,
        key=lambda row: (int(row['total_logical_qubits']), int(row['full_oracle_non_clifford'])),
    )
    return {
        'schema': 'compiler-project-whole-oracle-recount-v1',
        'source_artifacts': {
            'ft_ir_compositions': 'compiler_verification_project/artifacts/ft_ir_compositions.json',
            'family_frontier': 'compiler_verification_project/artifacts/family_frontier.json',
        },
        'source_references': [
            {
                'title': 'Qualtran call graph protocol',
                'url': 'https://qualtran.readthedocs.io/en/latest/resource_counting/call_graph.html',
                'reason': 'Reference design for recounting leaf-resource sigma from a hierarchical call graph.',
            },
            {
                'title': 'Qualtran testing for equivalent bloq counts',
                'url': 'https://qualtran.readthedocs.io/en/latest/resource_counting/call_graph.html#testing',
                'reason': 'Reference for comparing manually annotated counts against decomposition-derived counts.',
            },
        ],
        'public_google_baseline': dict(public_google_baseline),
        'families': families,
        'best_gate_family': best_gate_family,
        'best_qubit_family': best_qubit_family,
        'notes': [
            'This artifact performs a full exact whole-oracle recount by aggregating the FT IR leaf sigma for each named compiler family.',
            'The recount is independent of the flattened generated block inventory totals and serves as the primary exact total source for the compiler frontier.',
        ],
    }


__all__ = ['build_whole_oracle_recount']
