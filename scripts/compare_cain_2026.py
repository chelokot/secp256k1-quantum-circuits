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
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cain_integration import write_cain_integration_summary  # noqa: E402

SUMMARY_PATH = REPO_ROOT / 'results' / 'cain_2026_integration_summary.json'


class Console:
    def __init__(self) -> None:
        self.color = sys.stdout.isatty()

    def style(self, text: str, code: str) -> str:
        if not self.color:
            return text
        return f'\033[{code}m{text}\033[0m'

    def heading(self, text: str) -> str:
        return self.style(text, '1;36')

    def accent(self, text: str) -> str:
        return self.style(text, '1;33')

    def good(self, text: str) -> str:
        return self.style(text, '1;32')

    def detail(self, text: str) -> str:
        return self.style(text, '37')


def main() -> None:
    if not SUMMARY_PATH.exists():
        write_cain_integration_summary(REPO_ROOT)
    console = Console()
    summary = json.loads(SUMMARY_PATH.read_text())
    head = summary['headline_ranges']
    cain = summary['source_papers']['cain_2026']
    time_efficient_range = console.good(
        f"{head['projected_time_efficient_days_min']:.2f} to {head['projected_time_efficient_days_max']:.2f} days"
    )
    balanced_range = console.good(
        f"{head['projected_balanced_days_min']:.1f} to {head['projected_balanced_days_max']:.1f} days"
    )
    print(console.heading('Cain et al. 2026 integration'))
    print(console.heading('============================='))
    print(console.detail(summary['warning']))
    print()
    print(console.accent('Cain 2026 reference point'))
    print(console.accent('-------------------------'))
    print(console.detail(f"paper target            : ECC-256 / {cain['target_curve_in_paper']}"))
    print(console.detail(f"time-efficient runtime  : {cain['time_efficient_runtime_days']:.1f} days"))
    print(console.detail(f"balanced runtime        : {cain['balanced_runtime_days']:.1f} days"))
    print(console.detail(f"time-efficient hardware : {cain['time_efficient_physical_qubits']:,} physical qubits"))
    print(console.detail(f"headline minimum space  : {cain['headline_min_physical_qubits']:,} physical qubits"))
    print(console.detail(f"architecture cycle time : {cain['cycle_time_ms']:.1f} ms"))
    print()
    print(console.heading('Headline ranges'))
    print(console.heading('---------------'))
    print(f"time-efficient runtime : {time_efficient_range}")
    print(f"balanced runtime       : {balanced_range}")
    print(f"naive linear space     : {head['naive_linear_space_physical_qubits_min']:.0f} to {head['naive_linear_space_physical_qubits_max']:.0f} physical qubits")
    print(f"half-fixed space       : {head['half_fixed_overhead_space_physical_qubits_min']:.0f} to {head['half_fixed_overhead_space_physical_qubits_max']:.0f} physical qubits")
    print()
    print(console.heading('Case table'))
    print(console.heading('----------'))
    for case in summary['cases']:
        speedup = console.good(f"x{case['runtime_speedup_factor']:.4f}")
        time_efficient = console.good(f"{case['projected_time_efficient_days']:.2f}d")
        balanced = console.good(f"{case['projected_balanced_days']:.1f}d")
        print(
            f"{case['google_baseline_line']:10s} {case['optimized_lookup_model']:7s}  "
            f"speedup {speedup}  "
            f"time-efficient={time_efficient} "
            f"(vs Cain {cain['time_efficient_runtime_days']:.1f}d, -{cain['time_efficient_runtime_days'] - case['projected_time_efficient_days']:.2f}d)  "
            f"balanced={balanced} "
            f"(vs Cain {cain['balanced_runtime_days']:.1f}d, -{cain['balanced_runtime_days'] - case['projected_balanced_days']:.1f}d)"
        )


if __name__ == '__main__':
    main()
