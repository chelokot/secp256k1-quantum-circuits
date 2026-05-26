#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
README_PATH = PROJECT_ROOT / 'README.md'
ARTIFACT_PATH = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts' / 'primary_strict_result.json'
BASELINE_STATUS_PATH = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts' / 'current_baseline_status.json'
BEGIN = '<!-- BEGIN GENERATED: strict-replayed-tail-headline -->'
END = '<!-- END GENERATED: strict-replayed-tail-headline -->'


def _format_int(value: int) -> str:
    return f'{value:,}'


def render_headline_block(payload: dict) -> str:
    selected = payload['selected_result']
    baseline_status = json.loads(BASELINE_STATUS_PATH.read_text())
    accepted = baseline_status['accepted_physical_baseline']
    guard_corrected = baseline_status['guard_corrected_no_alias_candidate']
    hardening_target = baseline_status['conservative_hardening_target']
    source = json.loads((PROJECT_ROOT / payload['source_artifact']).read_text())
    formula = source['logical_qubit_formula']
    comparison = source['comparison_against_public_google_baseline']
    low_qubit = comparison['low_qubit']
    low_gate = comparison['low_gate']
    hardening_low_qubit_delta = hardening_target['logical_qubits'] - low_qubit['baseline_logical_qubits']
    hardening_low_gate_delta = hardening_target['logical_qubits'] - low_gate['baseline_logical_qubits']
    accepted_label = (
        'none yet'
        if accepted is None
        else f'{_format_int(accepted["non_clifford"])} non-Clifford, {_format_int(accepted["logical_qubits"])} logical qubits'
    )
    return '\n'.join([
        BEGIN,
        f'- **accepted Clifford-complete physical baseline:** `{accepted_label}`',
        f'- **conservative hardening target:** `{_format_int(hardening_target["non_clifford"])} non-Clifford`, `{_format_int(hardening_target["logical_qubits"])} logical qubits` (`not accepted; gate blocked`)',
        f'- **strict replayed-tail engine candidate:** `{_format_int(selected["non_clifford"])} non-Clifford`, `{_format_int(selected["logical_qubits"])} logical qubits` (`guard capacity not promoted`)',
        f'- **strict-candidate formula:** `{formula["tail_field_slots"]} * {formula["field_bits"]} + {formula["lookup_workspace_qubits"]} + {formula["control_qubits"]} + {formula["phase_qubits"]} = {_format_int(formula["reconstructed_total"])}`',
        f'- **hardening-target formula:** `{_format_int(guard_corrected["derivation"]["strict_candidate_logical_qubits"])} + {_format_int(guard_corrected["derivation"]["additional_logical_qubits_if_no_aliasing_proof"])} = {_format_int(guard_corrected["logical_qubits"])}`',
        f'- **hardening target vs Google low-qubit line:** `{low_qubit["non_clifford_improvement_ratio"]:.4f}x` lower non-Clifford, `{hardening_low_qubit_delta:+,}` logical qubits',
        f'- **hardening target vs Google low-gate line:** `{low_gate["non_clifford_improvement_ratio"]:.4f}x` lower non-Clifford, `{hardening_low_gate_delta:+,}` logical qubits',
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
