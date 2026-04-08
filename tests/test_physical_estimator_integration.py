from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from support import ensure_compiler_project_build_summary

REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT_SRC = REPO_ROOT / 'src'
COMPILER_SRC = REPO_ROOT / 'compiler_verification_project' / 'src'
if str(ROOT_SRC) not in sys.path:
    sys.path.insert(0, str(ROOT_SRC))
if str(COMPILER_SRC) not in sys.path:
    sys.path.insert(0, str(COMPILER_SRC))

from physical_estimator import build_azure_estimator_results_payload  # noqa: E402


def _load_targets_and_results() -> tuple[dict, dict, dict]:
    ensure_compiler_project_build_summary()
    logical_counts = json.loads(
        (REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'azure_resource_estimator_logical_counts.json').read_text()
    )
    targets = json.loads(
        (REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'azure_resource_estimator_targets.json').read_text()
    )
    results = json.loads(
        (REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'azure_resource_estimator_results.json').read_text()
    )
    return logical_counts, targets, results


def test_physical_estimator_target_profiles_are_complete() -> None:
    logical_counts, targets, results = _load_targets_and_results()
    assert len(targets['targets']) == 6
    assert len(results['families']) == len(logical_counts['families'])
    for family in results['families']:
        assert len(family['estimates']) == len(targets['targets'])


def test_physical_estimator_target_summaries_match_estimates() -> None:
    _, targets, results = _load_targets_and_results()
    for target in targets['targets']:
        name = target['name']
        summary = next(row for row in results['target_summaries'] if row['target'] == name)
        target_estimates = [next(estimate for estimate in family['estimates'] if estimate['target'] == name) for family in results['families']]
        best_space = min(
            target_estimates,
            key=lambda row: (
                row['physical_counts']['physicalQubits'],
                row['physical_counts']['runtime'],
                row['physical_counts']['rqops'],
            ),
        )
        best_runtime = min(
            target_estimates,
            key=lambda row: (
                row['physical_counts']['runtime'],
                row['physical_counts']['physicalQubits'],
                -row['physical_counts']['rqops'],
            ),
        )
        assert summary['lowest_physical_qubits_family']['family'] == best_space['family']
        assert summary['fastest_runtime_family']['family'] == best_runtime['family']


def test_physical_estimator_runtime_replay_matches_recorded_results_when_qsharp_is_available() -> None:
    if importlib.util.find_spec('qsharp') is None:
        return
    logical_counts, targets, results = _load_targets_and_results()
    recomputed = build_azure_estimator_results_payload(logical_counts, targets)
    assert recomputed == results
