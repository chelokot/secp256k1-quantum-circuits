from __future__ import annotations

import importlib.util
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
UPDATE_SCRIPT = REPO_ROOT / 'compiler_verification_project' / 'scripts' / 'update_readme_headline.py'
SPEC = importlib.util.spec_from_file_location('update_readme_headline', UPDATE_SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text()


def _artifact(name: str) -> dict:
    return json.loads((REPO_ROOT / 'compiler_verification_project' / 'artifacts' / name).read_text())


def test_readme_headline_block_is_generated_from_baseline_status() -> None:
    readme = _read('README.md')
    primary = _artifact('primary_strict_result.json')
    baseline = _artifact('current_baseline_status.json')
    rendered = MODULE.render_headline_block(primary)

    assert MODULE.replace_block(readme, rendered) == readme
    assert baseline['accepted_physical_baseline'] is None
    assert baseline['conservative_hardening_target']['logical_qubits'] == 2222
    assert '**accepted Clifford-complete physical baseline:** `none yet`' in readme
    assert '**conservative hardening target:** `36,973,222 non-Clifford`, `2,222 logical qubits`' in readme
    assert '**strict replayed-tail engine candidate:** `36,973,222 non-Clifford`, `1,968 logical qubits`' in readme


def test_public_docs_do_not_promote_candidate_numbers_as_accepted_baseline() -> None:
    paths = [
        'README.md',
        'compiler_verification_project/README.md',
        'docs/core/CLAIMS_AND_BOUNDARIES.md',
        'docs/core/RED_TEAM_REVIEW.md',
        'docs/references/GOOGLE_BASELINE_COMPARISON.md',
        'docs/references/IBM_QUANTUM_ROADMAP_CONTEXT.md',
        'docs/research/OPTIMIZATION_FRONTIERS.md',
        'docs/research/RED_TEAM_REVIEW_1044Q_STANDARD_QROM.md',
    ]
    forbidden_fragments = [
        'single current public resource headline',
        'primary strict resource headline',
        'accepted physical baseline: `36,973,222 / 1,968`',
        'accepted physical baseline: `36,973,222 / 2,222`',
        'accepted Clifford-complete physical baseline:** `36,973,222',
    ]

    for path in paths:
        text = _read(path)
        for fragment in forbidden_fragments:
            assert fragment not in text, f'{path} still contains stale baseline wording: {fragment}'


def test_historical_red_team_report_is_visibly_quarantined() -> None:
    report = _read('docs/research/RED_TEAM_REVIEW_1044Q_STANDARD_QROM.md')

    assert 'This is a historical adversarial report, not the current release authority.' in report
    assert 'current_baseline_status.json' in report
    assert 'records no accepted Clifford-complete physical baseline yet' in report
    assert '36,973,222 / 2,222' in report
