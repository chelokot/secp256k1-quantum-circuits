#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_ROOT = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
REPORT_PATH = PROJECT_ROOT / 'docs' / 'core' / 'BASELINE_HARDENING.md'


def _load_artifact(name: str) -> dict[str, Any]:
    return json.loads((ARTIFACT_ROOT / name).read_text())


def _format_int(value: int) -> str:
    return f'{value:,}'


def _status_label(passed: bool) -> str:
    return 'pass' if passed else 'blocked'


def _render_gate_table(rows: list[Mapping[str, Any]]) -> list[str]:
    table = [
        '| Gate | Status | Evidence | Required closeout |',
        '|---|---:|---|---|',
    ]
    for row in rows:
        table.append(
            f'| `{row["name"]}` | {_status_label(bool(row["pass"]))} | '
            f'`{row["evidence"]}` | {row["required_to_close"]} |'
        )
    return table


def render_report() -> str:
    baseline = _load_artifact('current_baseline_status.json')
    strict = baseline['current_strict_candidate']
    hardening = baseline['conservative_hardening_target']
    gate = baseline['accepted_baseline_gate']
    blockers = baseline['remaining_physical_baseline_blockers']
    forbidden = baseline['publication_policy']['forbidden_presentations_until_gate_closes']
    required = baseline['publication_policy']['required_to_publish']

    hardening_non_clifford = _format_int(int(hardening['non_clifford']))
    hardening_qubits = _format_int(int(hardening['logical_qubits']))
    strict_non_clifford = _format_int(int(strict['non_clifford']))
    strict_qubits = _format_int(int(strict['logical_qubits']))
    guard_derivation = hardening['derivation']

    lines = [
        '# Baseline hardening track',
        '',
        'This report is generated from `compiler_verification_project/artifacts/current_baseline_status.json`.',
        'It is the human-readable checklist for turning the current conservative',
        'resource target into an accepted Clifford-complete physical baseline.',
        '',
        '## Current verdict',
        '',
        f'- Accepted Clifford-complete physical baseline: **none yet**.',
        f'- Conservative hardening target under review: **{hardening_non_clifford} non-Clifford / {hardening_qubits} logical qubits**.',
        f'- Lower strict replayed-tail candidate: **{strict_non_clifford} non-Clifford / {strict_qubits} logical qubits**, not accepted.',
        f'- Acceptance gate: **{gate["status"]}**; decision is `{gate["decision"]}`.',
        '',
        'The repository should present the conservative hardening target when it',
        'needs a single current number, because it includes the zero-lift guard',
        'clean-ladder capacity consequence that the lower strict candidate does not',
        'promote. It must not be described as accepted until the gate below closes.',
        '',
        '## Hardening-target derivation',
        '',
        '| Term | Logical qubits |',
        '|---|---:|',
        f'| strict replayed-tail candidate | {_format_int(int(guard_derivation["strict_replayed_tail_candidate_logical_qubits"]))} |',
        f'| additional clean-ladder guard qubits | {_format_int(int(guard_derivation["additional_clean_ladder_guard_qubits"]))} |',
        f'| reconstructed hardening target | {_format_int(int(guard_derivation["reconstructed_logical_qubits"]))} |',
        '',
        'The non-Clifford count is unchanged in this conservative correction because',
        'the guard audit is a capacity correction, not a new gate-count reduction.',
        '',
        '## Acceptance gate',
        '',
        *_render_gate_table(gate['rows']),
        '',
        '## Active physical-baseline blockers',
        '',
    ]
    for blocker in blockers:
        lines.append(f'- `{blocker["name"]}`: `{blocker["status"]}`')
        if 'missing_logical_qubits_under_clean_ladder' in blocker:
            lines.append(
                f'  Missing clean-ladder guard capacity: '
                f'{_format_int(int(blocker["missing_logical_qubits_under_clean_ladder"]))} logical qubits.'
            )
        if 'partial_product_cleanup_ccx_proven' in blocker:
            lines.append(
                f'  Proven partial-product cleanup: '
                f'{_format_int(int(blocker["partial_product_cleanup_ccx_proven"]))} CCX rows.'
            )
            lines.append(
                f'  Guard cleanup rows still missing source controls: '
                f'{_format_int(int(blocker["guard_cleanup_ccx_missing_source_controls"]))}.'
            )
        if 'engine_clifford_complete_goal_achieved' in blocker:
            lines.append(
                f'  Clifford-complete engine achieved: '
                f'{str(blocker["engine_clifford_complete_goal_achieved"]).lower()}.'
            )
    lines.extend([
        '',
        '## Forbidden wording before acceptance',
        '',
        *[f'- {item}' for item in forbidden],
        '',
        '## Required closeout',
        '',
        *[f'- {item}' for item in required],
        '',
        '## Practical policy',
        '',
        'Use `36,973,222 / 2,222` as the central hardening track and cleanup',
        'target. Use `36,973,222 / 1,968`, `1,199`, `1,044`, and sub-1600 rows',
        'only as candidates, references, or quarantined hypotheses unless a future',
        'artifact closes the acceptance gate and recomputes the accepted totals from',
        'the same executable primitive stream.',
        '',
    ])
    return '\n'.join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    rendered = render_report()
    if args.check:
        if REPORT_PATH.read_text() != rendered:
            raise SystemExit('baseline hardening report is stale')
        return
    REPORT_PATH.write_text(rendered)


if __name__ == '__main__':
    main()
