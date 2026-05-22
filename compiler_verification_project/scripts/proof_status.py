#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CANDIDATE_ROOT = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts' / 'zkp_attestation_reusable_chunk_candidate'


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Fast checked-artifact freshness report for reusable-chunk ZKP proofs.',
    )
    parser.add_argument(
        '--require-all-current',
        action='store_true',
        help='Exit nonzero if any checked proof fixture is stale against the current input/public values.',
    )
    return parser.parse_args()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def proof_file_status(fixture: dict[str, Any]) -> dict[str, Any]:
    proof_path = fixture['proof_path']
    if proof_path is None:
        return {
            'proof_path': None,
            'proof_file_exists': None,
            'proof_sha256_matches_fixture': None,
        }
    path = PROJECT_ROOT / proof_path
    exists = path.exists()
    observed_sha256 = sha256_path(path) if exists else None
    observed_size = path.stat().st_size if exists else None
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
    }


def verifier_key_status(fixture: dict[str, Any]) -> dict[str, Any]:
    verifier_key_path = fixture['verifier_key_path']
    if verifier_key_path is None:
        return {
            'verifier_key_path': None,
            'verifier_key_file_exists': None,
            'verifier_key_sha256_matches_fixture': None,
        }
    path = PROJECT_ROOT / verifier_key_path
    exists = path.exists()
    observed_sha256 = sha256_path(path) if exists else None
    observed_size = path.stat().st_size if exists else None
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
    }


def fixture_status(system: str, input_payload: dict[str, Any], public_values: dict[str, Any]) -> dict[str, Any]:
    fixture = load_json(CANDIDATE_ROOT / f'zkp_attestation_fixture_{system}.json')
    proof_status = proof_file_status(fixture)
    key_status = verifier_key_status(fixture)
    fixture_public_values = fixture['public_values']
    input_path = CANDIDATE_ROOT / 'zkp_attestation_input.json'
    input_sha256 = sha256_path(input_path)
    input_size = input_path.stat().st_size
    fixture_input_path = fixture.get('input_path')
    fixture_input_file_exists = None
    fixture_input_observed_sha256 = None
    fixture_input_observed_size = None
    if fixture_input_path is None:
        input_binding_status = 'missing_fixture_input_metadata'
    else:
        fixture_input_file = PROJECT_ROOT / fixture_input_path
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
    current = (
        input_digest_matches_fixture
        and public_values_match_current
        and resource_digest_matches_input
        and proof_current
        and key_current
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
    return {
        'system': system,
        'current': current,
        'verification_key': fixture['verification_key'],
        'input_path': fixture_input_path,
        'input_file_exists': fixture_input_file_exists,
        'input_sha256': fixture.get('input_sha256'),
        'input_size_bytes': fixture.get('input_size_bytes'),
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


def build_report() -> dict[str, Any]:
    input_payload = load_json(CANDIDATE_ROOT / 'zkp_attestation_input.json')
    public_values = load_json(CANDIDATE_ROOT / 'zkp_attestation_public_values.json')
    systems = {
        system: fixture_status(system, input_payload, public_values)
        for system in ('core', 'compressed', 'groth16')
    }
    stale_systems = [system for system, status in systems.items() if not status['current']]
    return {
        'schema': 'compiler-project-proof-status-v1',
        'candidate_input': 'compiler_verification_project/artifacts/zkp_attestation_reusable_chunk_candidate/zkp_attestation_input.json',
        'candidate_input_sha256': sha256_path(CANDIDATE_ROOT / 'zkp_attestation_input.json'),
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


def main() -> None:
    args = parse_args()
    report = build_report()
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.require_all_current and not report['all_current']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
