#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
README_PATH = PROJECT_ROOT / 'README.md'
ARTIFACT_PATH = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts' / 'primary_strict_result.json'
BEGIN = '<!-- BEGIN GENERATED: strict-replayed-tail-headline -->'
END = '<!-- END GENERATED: strict-replayed-tail-headline -->'


def _format_int(value: int) -> str:
    return f'{value:,}'


def render_headline_block(payload: dict) -> str:
    selected = payload['selected_result']
    source = json.loads((PROJECT_ROOT / payload['source_artifact']).read_text())
    formula = source['logical_qubit_formula']
    comparison = source['comparison_against_public_google_baseline']
    low_qubit = comparison['low_qubit']
    low_gate = comparison['low_gate']
    return '\n'.join([
        BEGIN,
        f'- **primary strict replayed-tail headline:** `{_format_int(selected["non_clifford"])} non-Clifford`, `{_format_int(selected["logical_qubits"])} logical qubits`',
        f'- **logical-qubit formula:** `{formula["tail_field_slots"]} * {formula["field_bits"]} + {formula["lookup_workspace_qubits"]} + {formula["control_qubits"]} + {formula["phase_qubits"]} = {_format_int(formula["reconstructed_total"])}`',
        f'- **vs Google low-qubit line:** `{low_qubit["non_clifford_improvement_ratio"]:.4f}x` lower non-Clifford, `{low_qubit["logical_qubit_delta_vs_baseline"]:+,}` logical qubits',
        f'- **vs Google low-gate line:** `{low_gate["non_clifford_improvement_ratio"]:.4f}x` lower non-Clifford, `{low_gate["logical_qubit_delta_vs_baseline"]:+,}` logical qubits',
        END,
    ])


def replace_block(readme: str, rendered: str) -> str:
    before, marker, tail = readme.partition(BEGIN)
    if not marker:
        raise SystemExit(f'missing generated block marker: {BEGIN}')
    current, marker, after = tail.partition(END)
    if not marker:
        raise SystemExit(f'missing generated block marker: {END}')
    return before + rendered + after


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    payload = json.loads(ARTIFACT_PATH.read_text())
    rendered = render_headline_block(payload)
    readme = README_PATH.read_text()
    updated = replace_block(readme, rendered)
    if args.check:
        if updated != readme:
            raise SystemExit('README generated strict-headline block is stale')
        return
    README_PATH.write_text(updated)


if __name__ == '__main__':
    main()
