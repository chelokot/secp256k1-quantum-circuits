#!/usr/bin/env python3
"""Generate publication figures from repository JSON artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = REPO_ROOT / 'artifacts' / 'figures'
OUT_DIR = REPO_ROOT / 'artifacts' / 'out'
BENCH_DIR = REPO_ROOT / 'benchmarks' / 'challenge_ladder'
RESULTS_DIR = REPO_ROOT / 'results'


def load(name: str):
    return json.loads((OUT_DIR / name).read_text())


def fig_progression(meta, projection):
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
    for i, v in enumerate(values):
        ax.text(i, v + max(values) * 0.03, f'{v:.2f}', ha='center')
    fig.tight_layout()
    fig.savefig(FIG_DIR / 'progression_instruction_count.png', dpi=180)
    plt.close(fig)

    values = [
        low_qubit['logical_qubits'],
        low_gate['logical_qubits'],
        optimized_projection['logical_qubits_total'],
        optimized_projection['logical_qubits_total'],
    ]
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.bar(labels, values)
    ax.set_ylabel('logical qubits')
    ax.set_title('Logical-qubit comparison')
    for i, v in enumerate(values):
        ax.text(i, v + max(values) * 0.03, str(v), ha='center')
    fig.tight_layout()
    fig.savefig(FIG_DIR / 'progression_register_count.png', dpi=180)
    plt.close(fig)


def fig_headroom(sensitivity):
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
    fig.savefig(FIG_DIR / 'projection_headroom.png', dpi=180)
    plt.close(fig)


def fig_verification_coverage(strict_summary, ladder_summary):
    entries = [
        ('quick secp audit', 16384),
        ('quick toy family', 19850),
        ('lookup contract', strict_summary['lookup_contract']['summary']['signed_i16']['total'] + strict_summary['lookup_contract']['summary']['unsigned_u16']['total']),
        ('scaffold replay', strict_summary['scaffold_schedule']['summary']['total']),
        ('extended toy family', strict_summary['toy_extended']['summary']['total']),
        ('challenge ladder', ladder_summary['summary']['total']),
    ]
    labels = [k for k, _ in entries]
    values = [v for _, v in entries]
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    ax.bar(labels, values)
    ax.set_ylabel('checked cases')
    ax.set_title('Verification coverage')
    ax.tick_params(axis='x', rotation=18)
    for i, v in enumerate(values):
        ax.text(i, v + max(values) * 0.02, f'{v:,}', ha='center', fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG_DIR / 'verification_coverage_extended.png', dpi=180)
    plt.close(fig)


def fig_frontier_ranges(frontier):
    items = frontier['frontiers']
    names = [item['name'].replace('_', ' ') for item in items]
    lows = [item['estimated_total_non_clifford_multiplier_range'][0] for item in items]
    highs = [item['estimated_total_non_clifford_multiplier_range'][1] for item in items]
    mids = [(a + b) / 2 for a, b in zip(lows, highs)]
    fig, ax = plt.subplots(figsize=(8.5, 5.0))
    y = list(range(len(items)))
    ax.hlines(y, lows, highs, linewidth=2)
    ax.plot(mids, y, 'o')
    ax.set_yticks(y)
    ax.set_yticklabels(names)
    ax.set_xlabel('estimated total non-Clifford multiplier')
    ax.set_title('Possible future optimization ranges (heuristic)')
    ax.axvline(1.0, linestyle='--')
    fig.tight_layout()
    fig.savefig(FIG_DIR / 'optimization_frontier_ranges.png', dpi=180)
    plt.close(fig)


def fig_dominant_cost_breakdown(dominant):
    lookup2 = dominant['breakdown']['lookup_non_clifford_2lookup'] / 1_000_000
    lookup3 = dominant['breakdown']['lookup_non_clifford_3lookup'] / 1_000_000
    arith = dominant['baseline']['modeled_non_clifford_total_arithmetic_only'] / 1_000_000
    fig, ax = plt.subplots(figsize=(7.6, 4.8))
    xs = [0, 1]
    ax.bar(xs, [arith, arith], label='Arithmetic-only')
    ax.bar(xs, [lookup2, lookup3], bottom=[arith, arith], label='Lookup-only')
    ax.set_xticks(xs)
    ax.set_xticklabels(['2-lookup', '3-lookup'])
    ax.set_ylabel('non-Clifford (millions)')
    ax.set_title('Modeled cost breakdown: arithmetic vs lookup')
    ax.legend()
    ax.text(0, arith + lookup2 + 0.25, f"{100.0 * dominant['breakdown']['lookup_share_fraction_2lookup']:.2f}% lookup", ha='center', fontsize=9)
    ax.text(1, arith + lookup3 + 0.25, f"{100.0 * dominant['breakdown']['lookup_share_fraction_3lookup']:.2f}% lookup", ha='center', fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG_DIR / 'dominant_cost_breakdown.png', dpi=180)
    plt.close(fig)


def fig_lookup_reduction_targets(dominant):
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
    fig.savefig(FIG_DIR / 'lookup_reduction_targets.png', dpi=180)
    plt.close(fig)


def fig_challenge_ladder(ladder):
    curves = ladder['curves']
    labels = [str(curve['field_bits']) for curve in curves]
    subgroup_bits = [curve['subgroup_bits'] for curve in curves]
    subgroup_orders = [curve['subgroup_order'] for curve in curves]
    fig, ax1 = plt.subplots(figsize=(7.8, 4.8))
    ax1.bar(labels, subgroup_orders)
    ax1.set_xlabel('field size (bits)')
    ax1.set_ylabel('subgroup order')
    ax1.set_title('Deterministic secp-family challenge ladder')
    for i, (q, qb) in enumerate(zip(subgroup_orders, subgroup_bits)):
        ax1.text(i, q + max(subgroup_orders) * 0.015, f'q≈2^{qb}', ha='center', fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG_DIR / 'challenge_ladder_orders.png', dpi=180)
    plt.close(fig)


def fig_literature_layers(matrix):
    counts = {}
    for entry in matrix['entries']:
        counts[entry['layer']] = counts.get(entry['layer'], 0) + 1
    labels = list(counts.keys())
    values = [counts[k] for k in labels]
    fig, ax = plt.subplots(figsize=(9.4, 5.2))
    ax.bar(labels, values)
    ax.set_ylabel('selected works')
    ax.set_title('Where the current literature pressure actually sits')
    ax.tick_params(axis='x', rotation=28)
    for i, v in enumerate(values):
        ax.text(i, v + 0.05, str(v), ha='center', fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG_DIR / 'literature_layer_map.png', dpi=180)
    plt.close(fig)


def fig_lookup_fold_pad_sweep(folded):
    rows = folded['pad_sweep']
    pads = [row['per_window_small_overhead_pad'] for row in rows]
    total2 = [row['total_non_clifford_2channel_folded'] / 1_000_000 for row in rows]
    total3 = [row['total_non_clifford_3channel_folded_conservative'] / 1_000_000 for row in rows]
    total3m = [row['total_non_clifford_3channel_folded_meta_elided'] / 1_000_000 for row in rows]
    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    ax.plot(pads, total2, marker='o', label='2-channel folded')
    ax.plot(pads, total3, marker='o', label='3-channel folded (conservative)')
    ax.plot(pads, total3m, marker='o', label='3-channel folded (meta elided)')
    ax.axhline(30.998464, linestyle='--', label='Current 2-channel')
    ax.axhline(32.833472, linestyle=':', label='Current 3-channel')
    ax.set_xlabel('per-window small overhead pad')
    ax.set_ylabel('projected non-Clifford (millions)')
    ax.set_title('Signed lookup folding: pad sweep projection')
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_DIR / 'lookup_fold_pad_sweep.png', dpi=180)
    plt.close(fig)

def main():
    meta = load('meta_analysis.json')
    projection = load('resource_projection.json')
    sens = load('projection_sensitivity.json')
    verification = json.loads((RESULTS_DIR / 'repo_verification_summary.json').read_text())
    frontier = load('optimization_frontier_estimates.json')
    dominant = load('dominant_cost_breakdown.json')
    ladder = json.loads((BENCH_DIR / 'challenge_ladder.json').read_text())
    ladder_summary = json.loads((BENCH_DIR / 'challenge_ladder_summary.json').read_text())
    matrix = json.loads((RESULTS_DIR / 'literature_matrix.json').read_text())
    folded = load('lookup_folded_projection.json')

    fig_progression(meta, projection)
    fig_headroom(sens)
    fig_verification_coverage(verification['extended'], ladder_summary)
    fig_frontier_ranges(frontier)
    fig_dominant_cost_breakdown(dominant)
    fig_lookup_reduction_targets(dominant)
    fig_challenge_ladder(ladder)
    fig_literature_layers(matrix)
    fig_lookup_fold_pad_sweep(folded)
    print('wrote figures to', FIG_DIR)


if __name__ == '__main__':
    main()
