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


def _public_headline() -> dict:
    return json.loads(
        (REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'public_headline_result.json').read_text()
    )['selected_result']


def _release_profile() -> dict:
    return MODULE.resolve_proof_corpus_profile('release')


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


def test_release_candidate_build_uses_profiled_builder(monkeypatch: Any, tmp_path: Path) -> None:
    calls: list[list[str]] = []
    release_profile = _release_profile()
    payload = {
        'selected_family_name': 'reusable-family',
        'claim_sha256': '00' * 32,
        'leaf_sha256': '11' * 32,
        'family_sha256': '22' * 32,
        'case_corpus_sha256': '33' * 32,
        'resource_certificate_sha256': '44' * 32,
    }

    def fake_run(command: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        (tmp_path / 'zkp_attestation_input.json').write_text(json.dumps(payload))
        stdout = '\n'.join((
            '[build-zkp-attestation-input] wrote release bundle',
            json.dumps({'case_count': release_profile['case_count']}),
        ))
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr='')

    monkeypatch.setattr(MODULE.subprocess, 'run', fake_run)
    report = MODULE.build_release_input(tmp_path)
    command = calls[0]
    assert 'build_zkp_attestation_input.py' in ' '.join(command)
    assert '--profile' in command
    assert command[command.index('--profile') + 1] == 'release'
    assert '--cases' not in command
    assert report['case_count'] == release_profile['case_count']
    assert report['builder_command'] == command
    assert report['input_sha256']
    assert report['selected_family_name'] == payload['selected_family_name']


def test_release_candidate_execute_command_has_no_prover(monkeypatch: Any, tmp_path: Path) -> None:
    calls: list[list[str]] = []
    release_profile = _release_profile()
    selected = _public_headline()

    def fake_run(command: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        stdout = '\n'.join((
            '[zkp-attestation] starting execute',
            json.dumps({
                'public_values': {
                    'case_count': release_profile['case_count'],
                    'passed_case_count': release_profile['case_count'],
                    'expected_full_oracle_non_clifford': selected['non_clifford'],
                    'expected_total_logical_qubits': selected['logical_qubits'],
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
    assert report['case_count'] == release_profile['case_count']
    assert report['passed_case_count'] == release_profile['case_count']
    assert report['expected_full_oracle_non_clifford'] == selected['non_clifford']
    assert report['expected_total_logical_qubits'] == selected['logical_qubits']
