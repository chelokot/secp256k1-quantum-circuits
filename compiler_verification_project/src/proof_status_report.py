#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
from typing import Any

from common import load_json, sha256_path


PROOF_STATUS_SCHEMA = 'compiler-project-proof-status-v1'
CANDIDATE_ROOT_RELATIVE = 'compiler_verification_project/artifacts/zkp_attestation_reusable_chunk_candidate'
PROOF_MANIFEST_RELATIVE = 'artifacts/package/proof_manifest.json'


def proof_manifest_files(repo_root: Path) -> dict[str, Any]:
    manifest = load_json(repo_root / PROOF_MANIFEST_RELATIVE)
    return manifest['files']


def manifest_file_status(repo_root: Path, relative_path: str | None, manifest_files: dict[str, Any]) -> dict[str, Any]:
    if relative_path is None:
        return {
            'manifest_path': None,
            'manifest_record_exists': None,
            'manifest_sha256_matches_file': None,
        }
    path = repo_root / relative_path
    record = manifest_files.get(relative_path)
    exists = path.exists()
    observed_sha256 = sha256_path(path) if exists else None
    observed_size = path.stat().st_size if exists else None
    return {
        'manifest_path': relative_path,
        'manifest_record_exists': record is not None,
        'manifest_sha256_matches_file': (
            record is not None
            and exists
            and record['sha256'] == observed_sha256
            and record['bytes'] == observed_size
        ),
        'manifest_sha256': None if record is None else record['sha256'],
        'manifest_size_bytes': None if record is None else record['bytes'],
    }


def proof_file_status(repo_root: Path, fixture: dict[str, Any], manifest_files: dict[str, Any]) -> dict[str, Any]:
    proof_path = fixture['proof_path']
    if proof_path is None:
        return {
            'proof_path': None,
            'proof_file_exists': None,
            'proof_sha256_matches_fixture': None,
            'proof_manifest_record_exists': None,
            'proof_manifest_sha256_matches_file': None,
        }
    path = repo_root / proof_path
    exists = path.exists()
    observed_sha256 = sha256_path(path) if exists else None
    observed_size = path.stat().st_size if exists else None
    manifest_status = manifest_file_status(repo_root, proof_path, manifest_files)
    return {
        'proof_path': proof_path,
        'proof_file_exists': exists,
        'proof_sha256_matches_fixture': (
            exists
            and observed_sha256 == fixture['proof_sha256']
            and observed_size == fixture['proof_size_bytes']
        ),
        'observed_proof_sha256': observed_sha256,
        'fixture_proof_sha256': fixture['proof_sha256'],
        'proof_manifest_record_exists': manifest_status['manifest_record_exists'],
        'proof_manifest_sha256_matches_file': manifest_status['manifest_sha256_matches_file'],
        'proof_manifest_sha256': manifest_status.get('manifest_sha256'),
    }


def verifier_key_status(repo_root: Path, fixture: dict[str, Any], manifest_files: dict[str, Any]) -> dict[str, Any]:
    verifier_key_path = fixture['verifier_key_path']
    if verifier_key_path is None:
        return {
            'verifier_key_path': None,
            'verifier_key_file_exists': None,
            'verifier_key_sha256_matches_fixture': None,
            'verifier_key_manifest_record_exists': None,
            'verifier_key_manifest_sha256_matches_file': None,
        }
    path = repo_root / verifier_key_path
    exists = path.exists()
    observed_sha256 = sha256_path(path) if exists else None
    observed_size = path.stat().st_size if exists else None
    manifest_status = manifest_file_status(repo_root, verifier_key_path, manifest_files)
    return {
        'verifier_key_path': verifier_key_path,
        'verifier_key_file_exists': exists,
        'verifier_key_sha256_matches_fixture': (
            exists
            and observed_sha256 == fixture['verifier_key_sha256']
            and observed_size == fixture['verifier_key_size_bytes']
        ),
        'observed_verifier_key_sha256': observed_sha256,
        'fixture_verifier_key_sha256': fixture['verifier_key_sha256'],
        'verifier_key_manifest_record_exists': manifest_status['manifest_record_exists'],
        'verifier_key_manifest_sha256_matches_file': manifest_status['manifest_sha256_matches_file'],
        'verifier_key_manifest_sha256': manifest_status.get('manifest_sha256'),
    }


def fixture_status(
    repo_root: Path,
    system: str,
    input_payload: dict[str, Any],
    public_values: dict[str, Any],
    manifest_files: dict[str, Any],
) -> dict[str, Any]:
    candidate_root = repo_root / CANDIDATE_ROOT_RELATIVE
    fixture_relative_path = f'{CANDIDATE_ROOT_RELATIVE}/zkp_attestation_fixture_{system}.json'
    fixture = load_json(repo_root / fixture_relative_path)
    proof_status = proof_file_status(repo_root, fixture, manifest_files)
    key_status = verifier_key_status(repo_root, fixture, manifest_files)
    fixture_manifest_status = manifest_file_status(repo_root, fixture_relative_path, manifest_files)
    fixture_public_values = fixture['public_values']
    input_path = candidate_root / 'zkp_attestation_input.json'
    input_sha256 = sha256_path(input_path)
    input_size = input_path.stat().st_size
    input_metadata_keys = ('input_path', 'input_sha256', 'input_size_bytes')
    missing_input_metadata_keys = [key for key in input_metadata_keys if key not in fixture]
    fixture_input_path = fixture.get('input_path')
    fixture_input_file_exists = None
    fixture_input_observed_sha256 = None
    fixture_input_observed_size = None
    if missing_input_metadata_keys:
        input_binding_status = 'fixture_input_metadata_fields_missing'
    elif (
        fixture_input_path is None
        and fixture.get('input_sha256') is None
        and fixture.get('input_size_bytes') is None
    ):
        input_binding_status = 'fixture_declares_no_input_metadata'
    elif (
        fixture_input_path is None
        or fixture.get('input_sha256') is None
        or fixture.get('input_size_bytes') is None
    ):
        input_binding_status = 'fixture_input_metadata_incomplete'
    else:
        fixture_input_file = repo_root / fixture_input_path
        fixture_input_file_exists = fixture_input_file.exists()
        if fixture_input_file_exists:
            fixture_input_observed_sha256 = sha256_path(fixture_input_file)
            fixture_input_observed_size = fixture_input_file.stat().st_size
        if not fixture_input_file_exists:
            input_binding_status = 'fixture_input_file_missing'
        elif (
            fixture_input_observed_sha256 != fixture.get('input_sha256')
            or fixture_input_observed_size != fixture.get('input_size_bytes')
        ):
            input_binding_status = 'fixture_input_file_digest_mismatch'
        elif (
            fixture.get('input_sha256') == input_sha256
            and fixture.get('input_size_bytes') == input_size
        ):
            input_binding_status = 'matches_current_input'
        else:
            input_binding_status = 'points_to_stale_input_artifact'
    input_digest_matches_fixture = (
        fixture.get('input_sha256') == input_sha256
        and fixture.get('input_size_bytes') == input_size
    )
    public_values_match_current = fixture_public_values == public_values
    resource_digest_matches_input = (
        fixture_public_values['resource_certificate_sha256']
        == input_payload['resource_certificate_sha256']
    )
    proof_current = proof_status['proof_sha256_matches_fixture']
    if proof_current is None:
        proof_current = True
    key_current = key_status['verifier_key_sha256_matches_fixture']
    if key_current is None:
        key_current = True
    proof_manifest_current = proof_status['proof_manifest_sha256_matches_file']
    if proof_manifest_current is None:
        proof_manifest_current = True
    key_manifest_current = key_status['verifier_key_manifest_sha256_matches_file']
    if key_manifest_current is None:
        key_manifest_current = True
    fixture_manifest_current = fixture_manifest_status['manifest_sha256_matches_file']
    current = (
        input_digest_matches_fixture
        and public_values_match_current
        and resource_digest_matches_input
        and proof_current
        and key_current
        and proof_manifest_current
        and key_manifest_current
        and fixture_manifest_current
    )
    stale_reasons = []
    if input_binding_status != 'matches_current_input':
        stale_reasons.append(input_binding_status)
    if not public_values_match_current:
        stale_reasons.append('fixture_public_values_do_not_match_checked_public_values')
    if not resource_digest_matches_input:
        stale_reasons.append('fixture_resource_digest_does_not_match_current_input')
    if not proof_current:
        stale_reasons.append('proof_binary_does_not_match_fixture')
    if not key_current:
        stale_reasons.append('verifier_key_does_not_match_fixture')
    if not fixture_manifest_current:
        stale_reasons.append('fixture_json_does_not_match_proof_manifest')
    if not proof_manifest_current:
        stale_reasons.append('proof_binary_does_not_match_proof_manifest')
    if not key_manifest_current:
        stale_reasons.append('verifier_key_does_not_match_proof_manifest')
    return {
        'system': system,
        'current': current,
        'fixture_path': fixture_relative_path,
        'fixture_manifest_record_exists': fixture_manifest_status['manifest_record_exists'],
        'fixture_manifest_sha256_matches_file': fixture_manifest_status['manifest_sha256_matches_file'],
        'fixture_manifest_sha256': fixture_manifest_status.get('manifest_sha256'),
        'verification_key': fixture['verification_key'],
        'input_path': fixture_input_path,
        'input_file_exists': fixture_input_file_exists,
        'input_sha256': fixture.get('input_sha256'),
        'input_size_bytes': fixture.get('input_size_bytes'),
        'missing_input_metadata_keys': missing_input_metadata_keys,
        'observed_input_sha256': input_sha256,
        'fixture_input_observed_sha256': fixture_input_observed_sha256,
        'fixture_input_observed_size_bytes': fixture_input_observed_size,
        'input_binding_status': input_binding_status,
        'input_digest_matches_fixture': input_digest_matches_fixture,
        'resource_certificate_sha256': fixture_public_values['resource_certificate_sha256'],
        'public_values_match_current': public_values_match_current,
        'resource_digest_matches_input': resource_digest_matches_input,
        'stale_reasons': stale_reasons,
        **proof_status,
        **key_status,
    }


def build_proof_status_report(repo_root: Path) -> dict[str, Any]:
    candidate_root = repo_root / CANDIDATE_ROOT_RELATIVE
    input_payload = load_json(candidate_root / 'zkp_attestation_input.json')
    public_values = load_json(candidate_root / 'zkp_attestation_public_values.json')
    manifest_files = proof_manifest_files(repo_root)
    systems = {
        system: fixture_status(repo_root, system, input_payload, public_values, manifest_files)
        for system in ('core', 'compressed', 'groth16')
    }
    stale_systems = [system for system, status in systems.items() if not status['current']]
    return {
        'schema': PROOF_STATUS_SCHEMA,
        'proof_manifest': PROOF_MANIFEST_RELATIVE,
        'proof_manifest_sha256': sha256_path(repo_root / PROOF_MANIFEST_RELATIVE),
        'candidate_input': f'{CANDIDATE_ROOT_RELATIVE}/zkp_attestation_input.json',
        'candidate_input_sha256': sha256_path(candidate_root / 'zkp_attestation_input.json'),
        'compiler_parameters_sha256': input_payload['compiler_parameters_sha256'],
        'compiler_parameters_document_sha256': input_payload['compiler_parameters_document']['sha256'],
        'resource_certificate_sha256': input_payload['resource_certificate_sha256'],
        'public_values_resource_certificate_sha256': public_values['resource_certificate_sha256'],
        'input_and_public_values_match': input_payload['resource_certificate_sha256'] == public_values['resource_certificate_sha256'],
        'systems': systems,
        'stale_systems': stale_systems,
        'all_current': not stale_systems,
        'heavy_rebuild_steps_remaining': [
            system for system in ('compressed', 'groth16') if system in stale_systems
        ],
    }


__all__ = [
    'PROOF_STATUS_SCHEMA',
    'build_proof_status_report',
    'fixture_status',
    'manifest_file_status',
    'proof_file_status',
    'proof_manifest_files',
    'verifier_key_status',
]
