#!/usr/bin/env python3
"""Print a concise literature-and-frontier summary from repository JSON artifacts."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    dominant = json.loads((REPO_ROOT / 'artifacts' / 'out' / 'dominant_cost_breakdown.json').read_text())
    lit = json.loads((REPO_ROOT / 'results' / 'literature_matrix.json').read_text())
    scenarios = json.loads((REPO_ROOT / 'artifacts' / 'out' / 'literature_projection_scenarios.json').read_text())
    ladder = json.loads((REPO_ROOT / 'benchmarks' / 'challenge_ladder' / 'challenge_ladder_summary.json').read_text())

    print('Research and literature summary')
    print('===============================')
    print(f"lookup share (2-lookup): {100.0 * dominant['breakdown']['lookup_share_fraction_2lookup']:.2f}%")
    print(f"lookup share (3-lookup): {100.0 * dominant['breakdown']['lookup_share_fraction_3lookup']:.2f}%")
    print(f"max arithmetic-only gain (2-lookup): {100.0 * dominant['ceilings']['max_total_reduction_fraction_from_arithmetic_only_2lookup']:.2f}%")
    print(f"max arithmetic-only gain (3-lookup): {100.0 * dominant['ceilings']['max_total_reduction_fraction_from_arithmetic_only_3lookup']:.2f}%")
    print()
    print('Challenge ladder')
    print('---------------')
    print(f"curves: {ladder['summary']['curve_count']}  audited cases: {ladder['summary']['total']}  all-pass: {ladder['summary']['pass'] == ladder['summary']['total']}")
    print()
    print('Selected literature entries')
    print('---------------------------')
    for entry in lit['entries']:
        print(f"[{entry['year']}] {entry['id']:22s}  {entry['layer']:34s}  {entry['direct_mergeability']}")
    print()
    print('Scenario families')
    print('-----------------')
    for scenario in scenarios['scenarios']:
        print(f"{scenario['name']:40s}  {scenario['status']}")


if __name__ == '__main__':
    main()
