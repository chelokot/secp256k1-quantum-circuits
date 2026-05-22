#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from common import load_json, sha256_path
from proof_environment import tool_contracts


PROOF_ENVIRONMENT_CONTRACT_SCHEMA = 'compiler-project-proof-environment-contract-v1'


def _file_record(repo_root: Path, relative_path: str) -> dict[str, Any]:
    path = repo_root / relative_path
    return {
        'path': relative_path,
        'sha256': sha256_path(path),
        'bytes': path.stat().st_size,
    }


def _command_text(command: Mapping[str, Any]) -> str:
    if 'shell_command' in command:
        return str(command['shell_command'])
    return ' '.join(str(part) for part in command['argv'])


def _invokes_prover(command: Mapping[str, Any]) -> bool:
    text = _command_text(command)
    argv = command.get('argv', [])
    return '--prove' in argv or ' --prove' in text or text.strip().startswith('--prove')


def _command_contracts(public_result: Mapping[str, Any]) -> list[dict[str, Any]]:
    verification = public_result['verification_commands']
    return [
        {
            'name': 'environment_readiness_report',
            'phase': 'environment',
            'argv': ['python', 'compiler_verification_project/scripts/proof_environment_report.py', '--require-ready'],
            'cwd': '.',
            'invokes_prover': False,
            'publication_gate': False,
        },
        {
            'name': 'proof_environment_contract_refresh',
            'phase': 'environment',
            'argv': ['python', 'compiler_verification_project/scripts/build.py', '--target', 'proof-environment-contract'],
            'cwd': '.',
            'invokes_prover': False,
            'publication_gate': False,
        },
        {
            'name': 'proof_status_edit_loop',
            'phase': 'freshness',
            'argv': ['python', 'compiler_verification_project/scripts/proof_status.py'],
            'cwd': '.',
            'invokes_prover': False,
            'publication_gate': False,
        },
        {
            'name': 'proof_status_publication_gate',
            'phase': 'freshness',
            'argv': ['python', 'compiler_verification_project/scripts/proof_status.py', '--require-all-current'],
            'cwd': '.',
            'invokes_prover': False,
            'publication_gate': True,
        },
        {
            'name': 'fast_zkp_preflight_edit_loop',
            'phase': 'fast_no_prover_preflight',
            'argv': ['python', 'compiler_verification_project/scripts/fast_zkp_preflight.py'],
            'cwd': '.',
            'invokes_prover': False,
            'publication_gate': False,
        },
        {
            'name': 'fast_zkp_preflight_publication_gate',
            'phase': 'fast_no_prover_preflight',
            'argv': ['python', 'compiler_verification_project/scripts/fast_zkp_preflight.py', '--require-current-proofs'],
            'cwd': '.',
            'invokes_prover': False,
            'publication_gate': True,
        },
        {
            'name': 'release_candidate_input_refresh',
            'phase': 'input_generation',
            'argv': ['python', 'compiler_verification_project/scripts/build.py', '--target', 'release-candidate-zkp'],
            'cwd': '.',
            'invokes_prover': False,
            'publication_gate': False,
        },
        {
            'name': 'public_headline_metadata_verify',
            'phase': 'metadata_verification',
            'argv': verification['metadata'].split(' '),
            'cwd': '.',
            'invokes_prover': False,
            'publication_gate': False,
        },
        {
            'name': 'public_headline_compressed_verify',
            'phase': 'proof_verification',
            'argv': verification['metadata_and_compressed'].split(' '),
            'cwd': '.',
            'invokes_prover': False,
            'publication_gate': True,
        },
        {
            'name': 'public_headline_groth16_verify',
            'phase': 'proof_verification',
            'argv': verification['metadata_and_groth16'].split(' '),
            'cwd': '.',
            'invokes_prover': False,
            'publication_gate': True,
        },
        {
            'name': 'direct_compressed_verify',
            'phase': 'proof_verification',
            'shell_command': verification['compressed'],
            'cwd': '.',
            'invokes_prover': False,
            'publication_gate': True,
        },
        {
            'name': 'direct_groth16_verify',
            'phase': 'proof_verification',
            'shell_command': verification['groth16'],
            'cwd': '.',
            'invokes_prover': False,
            'publication_gate': True,
        },
    ]


def build_proof_environment_contract(*, repo_root: Path) -> dict[str, Any]:
    artifact_root = repo_root / 'compiler_verification_project' / 'artifacts'
    public_result = load_json(artifact_root / 'public_headline_result.json')
    proof_manifest_path = repo_root / 'artifacts' / 'package' / 'proof_manifest.json'
    proof_manifest = load_json(proof_manifest_path)
    commands = _command_contracts(public_result)
    checked_artifacts = public_result['checked_artifacts']
    manifest_files = proof_manifest['files']
    checked_records = {
        name: {
            **record,
            'manifest_record': manifest_files.get(record['path']),
            'manifest_record_present': record['path'] in manifest_files,
            'manifest_sha256_matches_checked_record': (
                record['path'] in manifest_files
                and manifest_files[record['path']]['sha256'] == record['sha256']
                and manifest_files[record['path']]['bytes'] == record['bytes']
            ),
        }
        for name, record in checked_artifacts.items()
    }
    compressed_verify = next(command for command in commands if command['name'] == 'direct_compressed_verify')
    groth16_verify = next(command for command in commands if command['name'] == 'direct_groth16_verify')
    compressed_text = _command_text(compressed_verify)
    groth16_text = _command_text(groth16_verify)
    input_path = checked_artifacts['input']['path']
    compressed_proof_path = checked_artifacts['compressed_proof']['path']
    groth16_proof_path = checked_artifacts['groth16_proof']['path']
    groth16_vk_path = checked_artifacts['groth16_verifier_key']['path']
    groth16_vk_dir = str(Path(groth16_vk_path).parent)
    freshness_check_names = {
        'public_values_match_input_claim',
        'all_fixtures_bind_same_public_values',
        'fixtures_bind_checked_input_digest',
    }
    non_freshness_checks = {
        name: passed
        for name, passed in public_result['checks'].items()
        if name not in freshness_check_names
    }
    checks = {
        'public_headline_result_metadata_is_self_consistent': all(non_freshness_checks.values()),
        'public_headline_result_keeps_proof_freshness_separate': all(
            name in public_result['checks']
            for name in freshness_check_names
        ),
        'all_checked_artifacts_exist_and_match_digest': all(
            (repo_root / record['path']).exists()
            and sha256_path(repo_root / record['path']) == record['sha256']
            and (repo_root / record['path']).stat().st_size == record['bytes']
            for record in checked_artifacts.values()
        ),
        'proof_manifest_records_public_headline_checked_artifacts': all(
            record['manifest_record_present'] for record in checked_records.values()
        ),
        'proof_manifest_records_match_public_headline_checked_artifacts': all(
            record['manifest_sha256_matches_checked_record'] for record in checked_records.values()
        ),
        'publication_freshness_gate_requires_all_current_proofs': any(
            command['name'] == 'proof_status_publication_gate'
            and command['publication_gate'] is True
            and '--require-all-current' in command['argv']
            for command in commands
        ),
        'fast_publication_gate_uses_current_proof_requirement': any(
            command['name'] == 'fast_zkp_preflight_publication_gate'
            and command['publication_gate'] is True
            and '--require-current-proofs' in command['argv']
            for command in commands
        ),
        'no_fast_or_metadata_command_invokes_prover': all(
            not _invokes_prover(command)
            for command in commands
            if command['phase'] != 'proof_rebuild'
        ),
        'declared_invokes_prover_flags_match_commands': all(
            bool(command['invokes_prover']) == _invokes_prover(command)
            for command in commands
        ),
        'direct_verify_commands_bind_checked_input_and_proofs': (
            input_path in compressed_text
            and compressed_proof_path in compressed_text
            and input_path in groth16_text
            and groth16_proof_path in groth16_text
            and groth16_vk_dir in groth16_text
        ),
        'tool_contract_lists_required_sp1_stack': set(tool_contracts()['required_tool_names']) == {
            'python',
            'cargo',
            'rustc',
            'protoc',
            'clang',
            'go',
        },
    }
    return {
        'schema': PROOF_ENVIRONMENT_CONTRACT_SCHEMA,
        'scope': 'checked reproducible proof-environment contract for public headline verification and rebuild gates',
        'tool_contract': tool_contracts(),
        'command_contracts': commands,
        'checked_artifacts': checked_records,
        'proof_manifest': {
            **_file_record(repo_root, 'artifacts/package/proof_manifest.json'),
            'schema': proof_manifest.get('schema'),
            'file_count': len(proof_manifest['files']),
        },
        'public_headline_result': _file_record(repo_root, 'compiler_verification_project/artifacts/public_headline_result.json'),
        'notes': [
            'This artifact is deterministic and repository-bound; it is not a pinned container or Nix lock.',
            'Publication still requires proof_status.py --require-all-current plus compressed and Groth16 verification against checked artifacts.',
            'No command in this contract invokes --prove; proof rebuilds remain an explicit separate operation.',
        ],
        'checks': checks,
        'pass': all(checks.values()),
    }


__all__ = ['PROOF_ENVIRONMENT_CONTRACT_SCHEMA', 'build_proof_environment_contract']
