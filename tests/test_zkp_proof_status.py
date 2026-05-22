#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT_SRC = REPO_ROOT / 'src'
COMPILER_SRC = REPO_ROOT / 'compiler_verification_project' / 'src'
if str(ROOT_SRC) not in sys.path:
    sys.path.insert(0, str(ROOT_SRC))
if str(COMPILER_SRC) not in sys.path:
    sys.path.insert(0, str(COMPILER_SRC))

from proof_status_report import build_proof_status_report  # noqa: E402


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
    assert report['proof_manifest'] == 'artifacts/package/proof_manifest.json'
    assert isinstance(report['proof_manifest_sha256'], str)
    assert isinstance(report['input_and_public_values_match'], bool)
    assert isinstance(report['candidate_input_sha256'], str)
    assert report['compiler_parameters_sha256'] == report['compiler_parameters_document_sha256']
    assert set(report['systems']) == {'core', 'compressed', 'groth16'}
    assert set(report['stale_systems']).issubset({'core', 'compressed', 'groth16'})
    assert set(report['heavy_rebuild_steps_remaining']).issubset({'compressed', 'groth16'})
    for status in report['systems'].values():
        assert status['system'] in {'core', 'compressed', 'groth16'}
        assert isinstance(status['current'], bool)
        assert status['fixture_path'].endswith(f"zkp_attestation_fixture_{status['system']}.json")
        assert status['fixture_manifest_record_exists'] is True
        assert status['fixture_manifest_sha256_matches_file'] is True
        assert isinstance(status['input_digest_matches_fixture'], bool)
        assert status['observed_input_sha256'] == report['candidate_input_sha256']
        assert status['input_binding_status'] in {
            'matches_current_input',
            'fixture_declares_no_input_metadata',
            'fixture_input_metadata_fields_missing',
            'fixture_input_file_missing',
            'fixture_input_file_digest_mismatch',
            'fixture_input_metadata_incomplete',
            'points_to_stale_input_artifact',
        }
        assert isinstance(status['stale_reasons'], list)
        assert isinstance(status['missing_input_metadata_keys'], list)
        if status['input_binding_status'] == 'fixture_declares_no_input_metadata':
            assert status['missing_input_metadata_keys'] == []
            assert status['input_path'] is None
            assert status['input_file_exists'] is None
            assert status['fixture_input_observed_sha256'] is None
        if status['input_binding_status'] == 'fixture_input_metadata_fields_missing':
            assert status['missing_input_metadata_keys']
        if status['input_binding_status'] != 'matches_current_input':
            assert status['input_binding_status'] in status['stale_reasons']
        assert isinstance(status['public_values_match_current'], bool)
        assert isinstance(status['resource_digest_matches_input'], bool)
        proof_current = status['proof_sha256_matches_fixture']
        if proof_current is None:
            proof_current = True
        key_current = status['verifier_key_sha256_matches_fixture']
        if key_current is None:
            key_current = True
        proof_manifest_current = status['proof_manifest_sha256_matches_file']
        if proof_manifest_current is None:
            proof_manifest_current = True
        key_manifest_current = status['verifier_key_manifest_sha256_matches_file']
        if key_manifest_current is None:
            key_manifest_current = True
        if status['proof_path'] is not None:
            assert status['proof_manifest_record_exists'] is True
            assert status['proof_manifest_sha256_matches_file'] is True
        if status['verifier_key_path'] is not None:
            assert status['verifier_key_manifest_record_exists'] is True
            assert status['verifier_key_manifest_sha256_matches_file'] is True
        assert status['current'] == (
            status['input_digest_matches_fixture']
            and status['public_values_match_current']
            and status['resource_digest_matches_input']
            and proof_current
            and key_current
            and proof_manifest_current
            and key_manifest_current
            and status['fixture_manifest_sha256_matches_file']
        )
        assert status['current'] == (status['stale_reasons'] == [])
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


def test_proof_status_cli_is_thin_wrapper_around_shared_report_engine() -> None:
    result = subprocess.run(
        [sys.executable, 'compiler_verification_project/scripts/proof_status.py'],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout) == build_proof_status_report(REPO_ROOT)
