#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_proof_status_reports_fixture_freshness_without_running_provers() -> None:
    result = subprocess.run(
        [sys.executable, 'compiler_verification_project/scripts/proof_status.py'],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(result.stdout)
    assert report['schema'] == 'compiler-project-proof-status-v1'
    assert isinstance(report['input_and_public_values_match'], bool)
    assert set(report['systems']) == {'core', 'compressed', 'groth16'}
    assert set(report['stale_systems']).issubset({'core', 'compressed', 'groth16'})
    assert set(report['heavy_rebuild_steps_remaining']).issubset({'compressed', 'groth16'})
    for status in report['systems'].values():
        assert status['system'] in {'core', 'compressed', 'groth16'}
        assert isinstance(status['current'], bool)
        assert isinstance(status['public_values_match_current'], bool)
        assert isinstance(status['resource_digest_matches_input'], bool)
        proof_current = status['proof_sha256_matches_fixture']
        if proof_current is None:
            proof_current = True
        key_current = status['verifier_key_sha256_matches_fixture']
        if key_current is None:
            key_current = True
        assert status['current'] == (
            status['public_values_match_current'] and status['resource_digest_matches_input']
            and proof_current and key_current
        )
    assert report['all_current'] == (report['stale_systems'] == [])
    assert report['all_current'] == all(status['current'] for status in report['systems'].values())


def test_proof_status_require_all_current_exit_code_matches_report() -> None:
    result = subprocess.run(
        [
            sys.executable,
            'compiler_verification_project/scripts/proof_status.py',
            '--require-all-current',
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    report = json.loads(result.stdout)
    assert result.returncode == (0 if report['all_current'] else 1)
