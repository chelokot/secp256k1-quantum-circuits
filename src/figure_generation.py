#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from common import artifact_core_figure_path, artifact_projection_path, artifact_research_figure_path
from research_extensions import build_challenge_ladder


def load_projection(package_dir: Path, name: str) -> Any:
    return json.loads(artifact_projection_path(package_dir, name).read_text())


def fig_progression(package_dir: Path, meta: Any, projection: Any) -> None:
    low_qubit = meta['google_baseline_estimates']['low_qubit']
    low_gate = meta['google_baseline_estimates']['low_gate']
    optimized_projection = projection['optimized_ecdlp_projection']
    labels = ['Google low-qubit', 'Google low-gate', 'Optimized 2-lookup', 'Optimized 3-lookup']
    values = [
        low_qubit['non_clifford'] / 1_000_000,
        low_gate['non_clifford'] / 1_000_000,
        optimized_projection['lookup_model_2channel']['total_non_clifford'] / 1_000_000,
        optimized_projection['lookup_model_3channel']['total_non_clifford'] / 1_000_000,
    ]
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.bar(labels, values)
    ax.set_ylabel('non-Clifford (millions)')
    ax.set_title('Modeled non-Clifford comparison')
    for index, value in enumerate(values):
        ax.text(index, value + max(values) * 0.03, f'{value:.2f}', ha='center')
    fig.tight_layout()
    fig.savefig(artifact_core_figure_path(package_dir, 'progression_instruction_count.png'), dpi=180)
    plt.close(fig)

    qubit_values = [
        low_qubit['logical_qubits'],
        low_gate['logical_qubits'],
        optimized_projection['logical_qubits_total'],
        optimized_projection['logical_qubits_total'],
    ]
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.bar(labels, qubit_values)
    ax.set_ylabel('logical qubits')
    ax.set_title('Logical-qubit comparison')
    for index, value in enumerate(qubit_values):
        ax.text(index, value + max(qubit_values) * 0.03, str(value), ha='center')
    fig.tight_layout()
    fig.savefig(artifact_core_figure_path(package_dir, 'progression_register_count.png'), dpi=180)
    plt.close(fig)


def fig_headroom(package_dir: Path, sensitivity: Any) -> None:
    base = sensitivity['base']
    xs = [1.0, 1.1, 1.25, 1.5, 1.75, 2.0]
    ys2 = [base['optimized_nc_2lookup'] * x / 1_000_000 for x in xs]
    ys3 = [base['optimized_nc_3lookup'] * x / 1_000_000 for x in xs]
    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    ax.plot(xs, ys2, marker='o', label='Optimized 2-lookup')
    ax.plot(xs, ys3, marker='o', label='Optimized 3-lookup')
    ax.axhline(base['google_low_gate']['non_clifford'] / 1_000_000, linestyle='--', label='Google low-gate')
    ax.axhline(base['google_low_qubit']['non_clifford'] / 1_000_000, linestyle=':', label='Google low-qubit')
    ax.set_xlabel('multiplicative backend overhead')
    ax.set_ylabel('non-Clifford (millions)')
    ax.set_title('Projection headroom under multiplicative overhead')
    ax.legend()
    fig.tight_layout()
    fig.savefig(artifact_core_figure_path(package_dir, 'projection_headroom.png'), dpi=180)
    plt.close(fig)


def fig_verification_coverage(package_dir: Path, verification: Any) -> None:
    extended = verification['extended']
    lookup = extended['lookup_contract']['summary']
    entries = [
        ('quick secp audit', 16384),
        ('quick toy family', 19850),
        ('lookup contract', lookup['canonical_full_exhaustive']['total'] + lookup['multibase_direct_samples']['total']),
        ('scaffold replay', extended['scaffold_schedule']['summary']['total']),
        ('extended toy family', extended['toy_extended']['summary']['total']),
        ('challenge ladder', extended['challenge_ladder']['summary']['total']),
    ]
    labels = [label for label, _ in entries]
    values = [value for _, value in entries]
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    ax.bar(labels, values)
    ax.set_ylabel('checked cases')
    ax.set_title('Verification coverage')
    ax.tick_params(axis='x', rotation=18)
    for index, value in enumerate(values):
        ax.text(index, value + max(values) * 0.02, f'{value:,}', ha='center', fontsize=8)
    fig.tight_layout()
    fig.savefig(artifact_research_figure_path(package_dir, 'verification_coverage_extended.png'), dpi=180)
    plt.close(fig)


def fig_frontier_ranges(package_dir: Path, frontier: Any) -> None:
    items = frontier['frontiers']
    names = [item['name'].replace('_', ' ') for item in items]
    lows = [item['estimated_total_non_clifford_multiplier_range'][0] for item in items]
    highs = [item['estimated_total_non_clifford_multiplier_range'][1] for item in items]
    mids = [(low + high) / 2 for low, high in zip(lows, highs)]
    fig, ax = plt.subplots(figsize=(8.5, 5.0))
    rows = list(range(len(items)))
    ax.hlines(rows, lows, highs, linewidth=2)
    ax.plot(mids, rows, 'o')
    ax.set_yticks(rows)
    ax.set_yticklabels(names)
    ax.set_xlabel('estimated total non-Clifford multiplier')
    ax.set_title('Possible future optimization ranges (heuristic)')
    ax.axvline(1.0, linestyle='--')
    fig.tight_layout()
    fig.savefig(artifact_research_figure_path(package_dir, 'optimization_frontier_ranges.png'), dpi=180)
    plt.close(fig)


def fig_dominant_cost_breakdown(package_dir: Path, dominant: Any) -> None:
    lookup2 = dominant['breakdown']['lookup_non_clifford_2lookup'] / 1_000_000
    lookup3 = dominant['breakdown']['lookup_non_clifford_3lookup'] / 1_000_000
    arithmetic = dominant['baseline']['modeled_non_clifford_total_arithmetic_only'] / 1_000_000
    fig, ax = plt.subplots(figsize=(7.6, 4.8))
    xs = [0, 1]
    ax.bar(xs, [arithmetic, arithmetic], label='Arithmetic-only')
    ax.bar(xs, [lookup2, lookup3], bottom=[arithmetic, arithmetic], label='Lookup-only')
    ax.set_xticks(xs)
    ax.set_xticklabels(['2-lookup', '3-lookup'])
    ax.set_ylabel('non-Clifford (millions)')
    ax.set_title('Modeled cost breakdown: arithmetic vs lookup')
    ax.legend()
    ax.text(0, arithmetic + lookup2 + 0.25, f"{100.0 * dominant['breakdown']['lookup_share_fraction_2lookup']:.2f}% lookup", ha='center', fontsize=9)
    ax.text(1, arithmetic + lookup3 + 0.25, f"{100.0 * dominant['breakdown']['lookup_share_fraction_3lookup']:.2f}% lookup", ha='center', fontsize=9)
    fig.tight_layout()
    fig.savefig(artifact_research_figure_path(package_dir, 'dominant_cost_breakdown.png'), dpi=180)
    plt.close(fig)


def fig_lookup_reduction_targets(package_dir: Path, dominant: Any) -> None:
    total2 = dominant['baseline']['total_non_clifford_2lookup'] / 1_000_000
    total3 = dominant['baseline']['total_non_clifford_3lookup'] / 1_000_000
    lookup2 = dominant['breakdown']['lookup_non_clifford_2lookup'] / 1_000_000
    lookup3 = dominant['breakdown']['lookup_non_clifford_3lookup'] / 1_000_000
    xs = [i / 100.0 for i in range(0, 36, 2)]
    ys2 = [total2 - lookup2 * x for x in xs]
    ys3 = [total3 - lookup3 * x for x in xs]
    fig, ax = plt.subplots(figsize=(7.8, 4.8))
    ax.plot([100 * x for x in xs], ys2, marker='o', label='2-lookup total')
    ax.plot([100 * x for x in xs], ys3, marker='o', label='3-lookup total')
    for target in (30, 29, 25, 20):
        ax.axhline(target, linestyle='--')
        ax.text(36.2, target, f'{target}M', va='center', fontsize=8)
    ax.set_xlabel('lookup reduction applied to lookup share (%)')
    ax.set_ylabel('projected non-Clifford (millions)')
    ax.set_title('Lookup-only reductions are bounded under the corrected model')
    ax.legend()
    fig.tight_layout()
    fig.savefig(artifact_research_figure_path(package_dir, 'lookup_reduction_targets.png'), dpi=180)
    plt.close(fig)


def fig_challenge_ladder(package_dir: Path, ladder: Any) -> None:
    curves = ladder['curves']
    labels = [str(curve['field_bits']) for curve in curves]
    subgroup_bits = [curve['subgroup_bits'] for curve in curves]
    subgroup_orders = [curve['subgroup_order'] for curve in curves]
    fig, ax = plt.subplots(figsize=(7.8, 4.8))
    ax.bar(labels, subgroup_orders)
    ax.set_xlabel('field size (bits)')
    ax.set_ylabel('subgroup order')
    ax.set_title('Deterministic secp-family challenge ladder')
    for index, (order, subgroup_bits_value) in enumerate(zip(subgroup_orders, subgroup_bits)):
        ax.text(index, order + max(subgroup_orders) * 0.015, f'q≈2^{subgroup_bits_value}', ha='center', fontsize=8)
    fig.tight_layout()
    fig.savefig(artifact_research_figure_path(package_dir, 'challenge_ladder_orders.png'), dpi=180)
    plt.close(fig)


def fig_literature_layers(package_dir: Path, matrix: Any) -> None:
    counts = {}
    for entry in matrix['entries']:
        counts[entry['layer']] = counts.get(entry['layer'], 0) + 1
    labels = list(counts.keys())
    values = [counts[label] for label in labels]
    fig, ax = plt.subplots(figsize=(9.4, 5.2))
    ax.bar(labels, values)
    ax.set_ylabel('selected works')
    ax.set_title('Where the current literature pressure actually sits')
    ax.tick_params(axis='x', rotation=28)
    for index, value in enumerate(values):
        ax.text(index, value + 0.05, str(value), ha='center', fontsize=8)
    fig.tight_layout()
    fig.savefig(artifact_research_figure_path(package_dir, 'literature_layer_map.png'), dpi=180)
    plt.close(fig)


def fig_lookup_fold_pad_sweep(package_dir: Path, folded: Any, projection: Any) -> None:
    rows = folded['pad_sweep']
    pads = [row['per_window_small_overhead_pad'] for row in rows]
    total2 = [row['total_non_clifford_2channel_folded'] / 1_000_000 for row in rows]
    total3 = [row['total_non_clifford_3channel_folded_conservative'] / 1_000_000 for row in rows]
    total3_meta = [row['total_non_clifford_3channel_folded_meta_elided'] / 1_000_000 for row in rows]
    current2 = projection['optimized_ecdlp_projection']['lookup_model_2channel']['total_non_clifford'] / 1_000_000
    current3 = projection['optimized_ecdlp_projection']['lookup_model_3channel']['total_non_clifford'] / 1_000_000
    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    ax.plot(pads, total2, marker='o', label='2-channel folded')
    ax.plot(pads, total3, marker='o', label='3-channel folded (conservative)')
    ax.plot(pads, total3_meta, marker='o', label='3-channel folded (meta elided)')
    ax.axhline(current2, linestyle='--', label='Current 2-channel')
    ax.axhline(current3, linestyle=':', label='Current 3-channel')
    ax.set_xlabel('per-window small overhead pad')
    ax.set_ylabel('projected non-Clifford (millions)')
    ax.set_title('Signed lookup folding: pad sweep projection')
    ax.legend()
    fig.tight_layout()
    fig.savefig(artifact_research_figure_path(package_dir, 'lookup_fold_pad_sweep.png'), dpi=180)
    plt.close(fig)


def write_figures(repo_root: Path) -> None:
    package_dir = repo_root / 'artifacts'
    results_dir = repo_root / 'results'
    meta = load_projection(package_dir, 'meta_analysis.json')
    projection = load_projection(package_dir, 'resource_projection.json')
    sensitivity = load_projection(package_dir, 'projection_sensitivity.json')
    verification = json.loads((results_dir / 'repo_verification_summary.json').read_text())
    frontier = load_projection(package_dir, 'optimization_frontier_estimates.json')
    dominant = load_projection(package_dir, 'dominant_cost_breakdown.json')
    ladder = build_challenge_ladder()
    matrix = json.loads((results_dir / 'literature_matrix.json').read_text())
    folded = load_projection(package_dir, 'lookup_folded_projection.json')

    fig_progression(package_dir, meta, projection)
    fig_headroom(package_dir, sensitivity)
    fig_verification_coverage(package_dir, verification)
    fig_frontier_ranges(package_dir, frontier)
    fig_dominant_cost_breakdown(package_dir, dominant)
    fig_lookup_reduction_targets(package_dir, dominant)
    fig_challenge_ladder(package_dir, ladder)
    fig_literature_layers(package_dir, matrix)
    fig_lookup_fold_pad_sweep(package_dir, folded, projection)
