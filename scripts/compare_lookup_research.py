#!/usr/bin/env python3
"""Print a concise summary of the lookup-focused research pass."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    summary = json.loads((REPO_ROOT / 'results' / 'research_pass_summary.json').read_text())
    dominant = json.loads((REPO_ROOT / 'artifacts' / 'out' / 'dominant_cost_breakdown.json').read_text())
    folded = json.loads((REPO_ROOT / 'artifacts' / 'out' / 'lookup_folded_projection.json').read_text())
    audit = json.loads((REPO_ROOT / 'artifacts' / 'out' / 'lookup_signed_fold_summary.json').read_text())

    base = folded['base_case_pad0']
    print('Lookup research summary')
    print('=======================')
    print(f"lookup share (2-channel): {100.0 * dominant['breakdown']['lookup_share_fraction_2lookup']:.2f}%")
    print(f"lookup share (3-channel): {100.0 * dominant['breakdown']['lookup_share_fraction_3lookup']:.2f}%")
    print(f"arithmetic share (2-channel): {100.0 * dominant['breakdown']['arithmetic_share_fraction_2lookup']:.2f}%")
    print(f"arithmetic share (3-channel): {100.0 * dominant['breakdown']['arithmetic_share_fraction_3lookup']:.2f}%")
    print()
    print('Signed lookup folding audit')
    print('---------------------------')
    print(f"full exhaustive cases: {audit['summary']['full_exhaustive_cases']}  pass: {audit['summary']['full_exhaustive_pass']}")
    print(f"multibase samples: {audit['summary']['direct_semantic_samples']}  pass: {audit['summary']['direct_semantic_pass']}")
    print()
    print('Merged lookup-folded mainline (pad = 0)')
    print('---------------------------------------')
    print(f"2-channel folded total: {base['total_non_clifford_2channel_folded']:,}  gain vs Google low-qubit line: {base['gain_vs_google_low_qubit_2channel']:.4f}x")
    print(f"3-channel conservative folded total: {base['total_non_clifford_3channel_folded_conservative']:,}")
    print()
    print('Research pass summary')
    print('---------------------')
    for key, value in summary['lookup_folding'].items():
        if key.endswith('sha256'):
            continue
        print(f'{key}: {value}')


if __name__ == '__main__':
    main()
