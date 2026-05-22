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
    current = public_values_match_current and resource_digest_matches_input and proof_current and key_current
    return {
        'system': system,
        'current': current,
        'verification_key': fixture['verification_key'],
        'resource_certificate_sha256': fixture_public_values['resource_certificate_sha256'],
        'public_values_match_current': public_values_match_current,
        'resource_digest_matches_input': resource_digest_matches_input,
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
