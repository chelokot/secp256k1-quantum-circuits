from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / 'compiler_verification_project' / 'scripts' / 'release_candidate_preproof.py'
SPEC = importlib.util.spec_from_file_location('release_candidate_preproof', SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_release_candidate_preproof_dry_run_never_proves() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), '--dry-run-json', '--execute', '--skip-build'],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    plan = json.loads(result.stdout)
    assert plan['schema'] == 'compiler-project-release-candidate-preproof-plan-v1'
    assert plan['build_release_input']['profile'] == 'release'
    assert plan['build_release_input']['family'] == 'reusable-chunk'
    assert plan['execute'] is True
    assert plan['proof_invoked'] is False


def test_release_candidate_execute_command_has_no_prover(monkeypatch: Any, tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        stdout = '\n'.join((
            '[zkp-attestation] starting execute',
            json.dumps({
                'public_values': {
                    'case_count': 9024,
                    'passed_case_count': 9024,
                    'expected_full_oracle_non_clifford': 36_957_412,
                    'expected_total_logical_qubits': 1199,
                },
                'stage_seconds': {'execute': 1.0},
                'total_instruction_count': 123,
            }),
        ))
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=stdout,
            stderr='',
        )

    monkeypatch.setattr(MODULE.subprocess, 'run', fake_run)
    report = MODULE.execute_release_input(
        input_path=tmp_path / 'zkp_attestation_input.json',
        output_dir=tmp_path,
        resource_profile='safe',
        skip_build=True,
    )
    rendered = ' '.join(calls[0])
    assert '--execute' in calls[0]
    assert '--prove' not in calls[0]
    assert '--verify-proof-input' not in calls[0]
    assert '--skip-build' in calls[0]
    assert 'run_zkp_attestation_guarded.py' in rendered
    assert report['case_count'] == 9024
    assert report['passed_case_count'] == 9024
    assert report['expected_total_logical_qubits'] == 1199
