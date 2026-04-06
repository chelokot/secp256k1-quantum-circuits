#!/usr/bin/env python3
"""Print the repository's approximate transfer into Cain et al. 2026.

This script intentionally keeps the model simple and explicit.  It does not
pretend to prove a new physical architecture result.  Instead it combines:
1. the repository's optimized logical non-Clifford budgets, and
2. the neutral-atom headline runtimes from Cain et al. 2026.

The main transfer rule is linear in the dominant non-Clifford budget.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SUMMARY_PATH = REPO_ROOT / 'results' / 'cain_2026_integration_summary.json'


def main() -> None:
    summary = json.loads(SUMMARY_PATH.read_text())
    head = summary['headline_ranges']
    print('Cain et al. 2026 integration')
    print('=============================')
    print(summary['warning'])
    print()
    print('Headline ranges')
    print('---------------')
    print(f"time-efficient runtime : {head['projected_time_efficient_days_min']:.2f} to {head['projected_time_efficient_days_max']:.2f} days")
    print(f"balanced runtime       : {head['projected_balanced_days_min']:.1f} to {head['projected_balanced_days_max']:.1f} days")
    print(f"naive linear space     : {head['naive_linear_space_physical_qubits_min']:.0f} to {head['naive_linear_space_physical_qubits_max']:.0f} physical qubits")
    print(f"half-fixed space       : {head['half_fixed_overhead_space_physical_qubits_min']:.0f} to {head['half_fixed_overhead_space_physical_qubits_max']:.0f} physical qubits")
    print()
    print('Case table')
    print('----------')
    for case in summary['cases']:
        print(
            f"{case['google_baseline_line']:10s} {case['optimized_lookup_model']:7s}  "
            f"speedup x{case['runtime_speedup_factor']:.4f}  "
            f"time-efficient={case['projected_time_efficient_days']:.2f}d  "
            f"balanced={case['projected_balanced_days']:.1f}d"
        )


if __name__ == '__main__':
    main()
