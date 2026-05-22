#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from common import load_json, sha256_path
from proof_status_report import PROOF_STATUS_SCHEMA, build_proof_status_report


PROOF_PUBLICATION_STATUS_SCHEMA = 'compiler-project-proof-publication-status-v1'


def _canonical_sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')
    return hashlib.sha256(encoded).hexdigest()


def build_proof_publication_status(*, repo_root: Path) -> dict[str, Any]:
    artifact_root = repo_root / 'compiler_verification_project' / 'artifacts'
    public_result = load_json(artifact_root / 'public_headline_result.json')
    environment_contract = load_json(artifact_root / 'proof_environment_contract.json')
    proof_status = build_proof_status_report(repo_root)
    systems = proof_status['systems']
    stale_systems = list(proof_status['stale_systems'])
    blocker_rows = [
        {
            'system': system,
            'fixture_path': systems[system]['fixture_path'],
            'stale_reasons': list(systems[system]['stale_reasons']),
            'input_binding_status': systems[system]['input_binding_status'],
            'resource_certificate_sha256': systems[system]['resource_certificate_sha256'],
        }
        for system in stale_systems
    ]
    publication_commands = [
        command
        for command in environment_contract['command_contracts']
        if command['publication_gate'] is True
    ]
    checks = {
        'proof_status_schema_is_current': proof_status['schema'] == PROOF_STATUS_SCHEMA,
        'proof_status_all_current_matches_stale_systems': proof_status['all_current'] == (stale_systems == []),
        'proof_status_heavy_rebuild_steps_are_stale_proof_systems': proof_status['heavy_rebuild_steps_remaining'] == [
            system for system in ('compressed', 'groth16') if system in stale_systems
        ],
        'public_headline_pass_matches_proof_status': public_result['pass'] == proof_status['all_current'],
        'public_headline_checked_input_digest_matches_proof_status': (
            public_result['checked_artifacts']['input']['sha256'] == proof_status['candidate_input_sha256']
        ),
        'public_headline_resource_digest_matches_proof_status_input': (
            public_result['bound_documents']['resource_certificate_sha256'] == proof_status['resource_certificate_sha256']
        ),
        'proof_manifest_digest_matches_environment_contract': (
            environment_contract['proof_manifest']['sha256'] == proof_status['proof_manifest_sha256']
        ),
        'environment_contract_has_current_publication_gates': (
            environment_contract['pass'] is True
            and any(command['name'] == 'proof_status_publication_gate' for command in publication_commands)
            and any(command['name'] == 'public_headline_compressed_verify' for command in publication_commands)
            and any(command['name'] == 'public_headline_groth16_verify' for command in publication_commands)
        ),
        'stale_publication_has_explicit_blockers': proof_status['all_current'] or bool(blocker_rows),
        'publication_ready_requires_compressed_and_groth16_verification': (
            not proof_status['all_current']
            or (
                systems['compressed']['current'] is True
                and systems['groth16']['current'] is True
                and public_result['pass'] is True
            )
        ),
    }
    return {
        'schema': PROOF_PUBLICATION_STATUS_SCHEMA,
        'scope': 'checked publication freshness status for the public reusable-chunk proof bundle',
        'publication_ready': proof_status['all_current'],
        'selected_result': public_result['selected_result'],
        'proof_status_sha256': _canonical_sha256(proof_status),
        'proof_status': proof_status,
        'publication_blockers': blocker_rows,
        'publication_gate_commands': publication_commands,
        'source_artifacts': {
            'public_headline_result': {
                'path': 'compiler_verification_project/artifacts/public_headline_result.json',
                'sha256': sha256_path(artifact_root / 'public_headline_result.json'),
            },
            'proof_environment_contract': {
                'path': 'compiler_verification_project/artifacts/proof_environment_contract.json',
                'sha256': sha256_path(artifact_root / 'proof_environment_contract.json'),
            },
            'proof_manifest': {
                'path': proof_status['proof_manifest'],
                'sha256': proof_status['proof_manifest_sha256'],
            },
        },
        'checks': checks,
        'pass': all(checks.values()),
        'notes': [
            'pass means the publication status was derived consistently; publication_ready is the separate freshness verdict.',
            'When publication_ready is false, the public result remains a checked resource candidate but not a current compressed/Groth16 proof claim.',
        ],
    }


__all__ = ['PROOF_PUBLICATION_STATUS_SCHEMA', 'build_proof_publication_status']
