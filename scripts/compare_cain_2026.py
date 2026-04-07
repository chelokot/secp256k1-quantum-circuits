#!/usr/bin/env python3
"""Print the repository's approximate exact-family transfer into Cain et al. 2026.

This script intentionally keeps the model simple and explicit.  It does not
pretend to prove a new physical architecture result.  Instead it combines:
1. the repository's exact compiler-family logical budgets, and
2. the neutral-atom headline runtimes from Cain et al. 2026.
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
    runtime_90m_range = console.good(
        f"{head['time_efficient_days_if_90M_min']:.2f} to {head['time_efficient_days_if_90M_max']:.2f} days"
    )
    runtime_70m_range = console.good(
        f"{head['time_efficient_days_if_70M_min']:.2f} to {head['time_efficient_days_if_70M_max']:.2f} days"
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
    print(f"time-efficient runtime if 90M->10d : {runtime_90m_range}")
    print(f"time-efficient runtime if 70M->10d : {runtime_70m_range}")
    print(f"same-density space if 1200->26k    : {head['same_density_physical_qubits_if_1200_min']:.0f} to {head['same_density_physical_qubits_if_1200_max']:.0f} physical qubits")
    print(f"same-density space if 1450->26k    : {head['same_density_physical_qubits_if_1450_min']:.0f} to {head['same_density_physical_qubits_if_1450_max']:.0f} physical qubits")
    print()
    print(console.heading('Case table'))
    print(console.heading('----------'))
    for case in summary['cases']:
        gain_90m = console.good(f"x{summary['public_google_baseline']['low_qubit']['non_clifford'] / case['exact_non_clifford']:.4f}")
        gain_70m = console.good(f"x{summary['public_google_baseline']['low_gate']['non_clifford'] / case['exact_non_clifford']:.4f}")
        print(
            f"{case['family']:54s} "
            f"gain90={gain_90m} "
            f"gain70={gain_70m} "
            f"time90={case['runtime_transfer']['time_efficient_days_if_90M_maps_to_10d']:.2f}d "
            f"time70={case['runtime_transfer']['time_efficient_days_if_70M_maps_to_10d']:.2f}d "
            f"space1200={case['space_transfer']['same_density_physical_qubits_if_1200_maps_to_26k']:.0f} "
            f"space1450={case['space_transfer']['same_density_physical_qubits_if_1450_maps_to_26k']:.0f}"
        )


if __name__ == '__main__':
    main()
