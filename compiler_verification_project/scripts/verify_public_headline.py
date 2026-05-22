#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_ROOT = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
CANDIDATE_ROOT = ARTIFACT_ROOT / 'zkp_attestation_reusable_chunk_candidate'
DIGEST_SCHEME = 'compiler-project-semantic-json-sha256-v1'


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Verify the checked public headline bundle without rebuilding proofs by default.',
    )
    parser.add_argument('--verify-compressed', action='store_true')
    parser.add_argument('--verify-groth16', action='store_true')
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--resource-profile', choices=('safe', 'balanced', 'throughput', 'full'), default='safe')
    parser.add_argument('--systemd-property', action='append', default=['TasksMax=128'])
    return parser.parse_args()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def semantic_hash_feed(hasher: 'hashlib._Hash', value: Any) -> None:
    if value is None:
        hasher.update(b'n')
        return
    if isinstance(value, bool):
        hasher.update(b't' if value else b'f')
        return
    if isinstance(value, int):
        encoded = str(value).encode('ascii')
        hasher.update(b'i')
        hasher.update(len(encoded).to_bytes(8, 'big'))
        hasher.update(encoded)
        return
    if isinstance(value, float):
        encoded = json.dumps(value, allow_nan=False, ensure_ascii=True, separators=(',', ':')).encode('ascii')
        hasher.update(b'i')
        hasher.update(len(encoded).to_bytes(8, 'big'))
        hasher.update(encoded)
        return
    if isinstance(value, str):
        encoded = value.encode('utf-8')
        hasher.update(b's')
        hasher.update(len(encoded).to_bytes(8, 'big'))
        hasher.update(encoded)
        return
    if isinstance(value, list):
        hasher.update(b'l')
        hasher.update(len(value).to_bytes(8, 'big'))
        for item in value:
            semantic_hash_feed(hasher, item)
        return
    if isinstance(value, dict):
        hasher.update(b'o')
        keys = sorted(value)
        hasher.update(len(keys).to_bytes(8, 'big'))
        for key in keys:
            semantic_hash_feed(hasher, str(key))
            semantic_hash_feed(hasher, value[key])
        return
    raise TypeError(f'unsupported semantic hash value: {type(value)!r}')


def semantic_payload_sha256(document_type: str, payload: Any) -> str:
    hasher = hashlib.sha256()
    hasher.update(DIGEST_SCHEME.encode('ascii'))
    hasher.update(b'\0')
    hasher.update(document_type.encode('utf-8'))
    hasher.update(b'\0')
    semantic_hash_feed(hasher, payload)
    return hasher.hexdigest()


def check(checks: list[dict[str, Any]], name: str, passed: bool, expected: Any, observed: Any) -> None:
    checks.append(
        {
            'name': name,
            'pass': bool(passed),
            'expected': expected,
            'observed': observed,
        }
    )


def checked_path(relative_path: str) -> Path:
    path = PROJECT_ROOT / relative_path
    if not path.exists():
        raise FileNotFoundError(relative_path)
    return path


def verify_file_record(checks: list[dict[str, Any]], label: str, record: dict[str, Any]) -> None:
    path = checked_path(record['path'])
    observed = {
        'sha256': sha256_path(path),
        'bytes': path.stat().st_size,
    }
    expected = {
        'sha256': record['sha256'],
        'bytes': record['bytes'],
    }
    check(checks, f'{label}_file_record_matches_checked_file', observed == expected, expected, observed)


def verify_fixture_record(
    checks: list[dict[str, Any]],
    label: str,
    fixture: dict[str, Any],
    record: dict[str, Any],
    public_values: dict[str, Any],
) -> None:
    check(checks, f'{label}_fixture_public_values_match', fixture['public_values'] == public_values, public_values, fixture['public_values'])
    for key in (
        'proof_system',
        'verification_key',
        'proof_path',
        'proof_sha256',
        'proof_size_bytes',
        'verifier_key_path',
        'verifier_key_sha256',
        'verifier_key_size_bytes',
    ):
        check(checks, f'{label}_record_{key}_matches_fixture', record[key] == fixture[key], fixture[key], record[key])
    if fixture['proof_path'] is not None:
        proof_path = checked_path(fixture['proof_path'])
        proof_observed = {
            'sha256': sha256_path(proof_path),
            'bytes': proof_path.stat().st_size,
        }
        proof_expected = {
            'sha256': fixture['proof_sha256'],
            'bytes': fixture['proof_size_bytes'],
        }
        check(checks, f'{label}_fixture_binds_proof_binary', proof_observed == proof_expected, proof_expected, proof_observed)
    if fixture['verifier_key_path'] is not None:
        verifier_key_path = checked_path(fixture['verifier_key_path'])
        key_observed = {
            'sha256': sha256_path(verifier_key_path),
            'bytes': verifier_key_path.stat().st_size,
        }
        key_expected = {
            'sha256': fixture['verifier_key_sha256'],
            'bytes': fixture['verifier_key_size_bytes'],
        }
        check(checks, f'{label}_fixture_binds_verifier_key', key_observed == key_expected, key_expected, key_observed)


def verify_committed_document(
    checks: list[dict[str, Any]],
    label: str,
    document: dict[str, Any],
    expected_digest: str,
    sidecar_payload: Any | None,
) -> None:
    observed_digest = semantic_payload_sha256(document['document_type'], document['payload'])
    check(checks, f'{label}_document_declared_digest_matches_header', document['sha256'] == expected_digest, expected_digest, document['sha256'])
    check(checks, f'{label}_document_semantic_digest_recomputes', observed_digest == document['sha256'], document['sha256'], observed_digest)
    if sidecar_payload is not None:
        check(checks, f'{label}_document_payload_matches_checked_sidecar', sidecar_payload == document['payload'], document['payload'], sidecar_payload)


def build_metadata_report() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    public_result = load_json(ARTIFACT_ROOT / 'public_headline_result.json')
    input_payload = load_json(CANDIDATE_ROOT / 'zkp_attestation_input.json')
    public_values = load_json(CANDIDATE_ROOT / 'zkp_attestation_public_values.json')
    core_fixture = load_json(CANDIDATE_ROOT / 'zkp_attestation_fixture_core.json')
    compressed_fixture = load_json(CANDIDATE_ROOT / 'zkp_attestation_fixture_compressed.json')
    groth16_fixture = load_json(CANDIDATE_ROOT / 'zkp_attestation_fixture_groth16.json')
    lowering = load_json(ARTIFACT_ROOT / 'reusable_chunk_lowering.json')
    tail_candidate = load_json(ARTIFACT_ROOT / 'reusable_chunk_tail_candidate.json')

    selected = public_result['selected_result']
    checked_artifacts = public_result['checked_artifacts']
    bound_documents = public_result['bound_documents']

    check(checks, 'public_headline_schema_is_current', public_result['schema'] == 'compiler-project-public-headline-result-v1', 'compiler-project-public-headline-result-v1', public_result['schema'])
    check(checks, 'public_headline_passes_internal_checks', public_result['pass'] is True and all(public_result['checks'].values()), True, public_result['checks'])
    check(checks, 'public_headline_stays_under_strict_goal', selected['non_clifford'] < 40_000_000 and selected['logical_qubits'] < 1200, '<40M non-Clifford and <1200 logical qubits', selected)
    check(checks, 'public_headline_matches_public_values', selected['name'] == public_values['selected_family_name'] and selected['non_clifford'] == public_values['expected_full_oracle_non_clifford'] and selected['logical_qubits'] == public_values['expected_total_logical_qubits'], public_values, selected)
    check(checks, 'public_values_match_input_digest_headers', all(public_values[key] == input_payload[key] == bound_documents[key] for key in bound_documents), bound_documents, {key: {'public_values': public_values[key], 'input': input_payload[key]} for key in bound_documents})
    check(checks, 'case_counts_match_and_pass', selected['case_count'] == selected['passed_case_count'] == public_values['case_count'] == public_values['passed_case_count'] == 8, 8, {'selected': selected, 'public_values': public_values})

    for label, record in checked_artifacts.items():
        verify_file_record(checks, label, record)

    verify_fixture_record(checks, 'core_fixture', core_fixture, checked_artifacts['core_fixture'], public_values)
    verify_fixture_record(checks, 'compressed_fixture', compressed_fixture, checked_artifacts['compressed_fixture'], public_values)
    verify_fixture_record(checks, 'groth16_fixture', groth16_fixture, checked_artifacts['groth16_fixture'], public_values)

    sidecars = {
        'claim': load_json(CANDIDATE_ROOT / 'zkp_attestation_claim.json'),
        'leaf': None,
        'family': load_json(CANDIDATE_ROOT / 'zkp_attestation_family.json'),
        'case_corpus': load_json(CANDIDATE_ROOT / 'zkp_attestation_cases.json'),
        'resource_certificate': lowering,
    }
    documents = {
        'claim': input_payload['claim_document'],
        'leaf': input_payload['leaf_document'],
        'family': input_payload['family_document'],
        'case_corpus': input_payload['case_corpus_document'],
        'resource_certificate': input_payload['resource_certificate_document'],
    }
    digest_keys = {
        'claim': 'claim_sha256',
        'leaf': 'leaf_sha256',
        'family': 'family_sha256',
        'case_corpus': 'case_corpus_sha256',
        'resource_certificate': 'resource_certificate_sha256',
    }
    for label, document in documents.items():
        verify_committed_document(checks, label, document, bound_documents[digest_keys[label]], sidecars[label])

    leaf_payload = documents['leaf']['payload']
    executable_leaf = tail_candidate['executable_leaf_contract']
    check(checks, 'leaf_document_instructions_match_checked_tail_contract', leaf_payload['instructions'] == executable_leaf['instructions'], executable_leaf['instructions'], leaf_payload['instructions'])
    check(checks, 'leaf_document_arithmetic_slots_match_checked_tail_contract', leaf_payload['arithmetic_slots'] == executable_leaf['arithmetic_slots'], executable_leaf['arithmetic_slots'], leaf_payload['arithmetic_slots'])
    check(checks, 'leaf_document_lookup_slots_match_checked_tail_contract', leaf_payload['lookup_interface_slots'] == executable_leaf['lookup_interface_slots'], executable_leaf['lookup_interface_slots'], leaf_payload['lookup_interface_slots'])
    check(checks, 'leaf_document_chunk_shape_matches_checked_tail_contract', leaf_payload['instructions'][-1]['chunk_bits'] == executable_leaf['chunk_contract']['chunk_bits'] and leaf_payload['instructions'][-1]['chunk_count'] == executable_leaf['chunk_contract']['chunk_count'], executable_leaf['chunk_contract'], leaf_payload['instructions'][-1])

    check(checks, 'reusable_chunk_lowering_status_is_public_headline', lowering['status'] == 'proven_public_headline' and lowering['pass'] is True, 'proven_public_headline pass=true', {'status': lowering['status'], 'pass': lowering['pass']})
    executable_liveness = lowering['executable_liveness']
    check(checks, 'reusable_chunk_executable_liveness_recomputes_public_peak', executable_liveness['pass'] is True and executable_liveness['global_peak_live_qubits'] == public_values['expected_total_logical_qubits'], public_values['expected_total_logical_qubits'], executable_liveness)
    check(checks, 'reusable_chunk_executable_liveness_counts_qchunk_and_qroam_target_concurrently', executable_liveness['checks']['qroam_target_and_qchunk_are_concurrently_live'] is True and executable_liveness['checks']['no_full_coordinate_lane_wire_is_live'] is True, {'qchunk_and_qroam_target_concurrent': True, 'full_coordinate_lane_live': False}, executable_liveness['checks'])
    check(checks, 'reusable_chunk_tail_status_is_public_headline', tail_candidate['status'] == 'proven_public_headline', 'proven_public_headline', tail_candidate['status'])
    check(checks, 'compressed_fixture_keeps_large_proof_out_of_line_but_bound', compressed_fixture['proof'] is None and compressed_fixture['proof_path'] is not None and compressed_fixture['proof_sha256'] is not None, 'out-of-line proof with digest', {'proof': compressed_fixture['proof'], 'proof_path': compressed_fixture['proof_path'], 'proof_sha256': compressed_fixture['proof_sha256']})
    check(checks, 'groth16_fixture_has_embedded_short_proof_and_bundle_digest', isinstance(groth16_fixture['proof'], str) and groth16_fixture['proof'].startswith('0x') and groth16_fixture['proof_sha256'] is not None, 'embedded Groth16 proof plus checked bundle digest', {'proof_prefix': str(groth16_fixture['proof'])[:10], 'proof_sha256': groth16_fixture['proof_sha256']})

    failed = [item for item in checks if not item['pass']]
    return {
        'schema': 'compiler-project-public-headline-verification-v1',
        'metadata_pass': not failed,
        'failed_checks': failed,
        'check_count': len(checks),
        'selected_result': selected,
        'bound_documents': bound_documents,
        'checked_proofs': {
            'compressed_proof_sha256': checked_artifacts['compressed_proof']['sha256'],
            'groth16_proof_sha256': checked_artifacts['groth16_proof']['sha256'],
            'groth16_verifier_key_sha256': checked_artifacts['groth16_verifier_key']['sha256'],
        },
        'checks': checks,
    }


def verification_command(system: str, resource_profile: str, systemd_properties: list[str]) -> list[str]:
    script = 'compiler_verification_project/scripts/run_zkp_attestation_guarded.py'
    input_path = 'compiler_verification_project/artifacts/zkp_attestation_reusable_chunk_candidate/zkp_attestation_input.json'
    output_dir = 'compiler_verification_project/artifacts/zkp_attestation_reusable_chunk_candidate'
    if system == 'compressed':
        command = [
            sys.executable,
            script,
            '--verify-proof-input',
            f'{output_dir}/zkp_attestation_proof_compressed.bin',
            '--system',
            'compressed',
            '--resource-profile',
            resource_profile,
            '--skip-build',
            '--input',
            input_path,
            '--output-dir',
            output_dir,
        ]
    elif system == 'groth16':
        command = [
            sys.executable,
            script,
            '--verify-proof-input',
            f'{output_dir}/zkp_attestation_proof_groth16.bin',
            '--system',
            'groth16',
            '--resource-profile',
            resource_profile,
            '--skip-build',
            '--groth16-verify-dir',
            f'{output_dir}/zkp_attestation_groth16_verifier',
            '--input',
            input_path,
            '--output-dir',
            output_dir,
        ]
    else:
        raise ValueError(system)
    for property_value in systemd_properties:
        command.extend(['--systemd-property', property_value])
    return command


def run_external_verification(system: str, resource_profile: str, systemd_properties: list[str]) -> dict[str, Any]:
    env = os.environ.copy()
    env['SP1_CIRCUIT_MODE'] = 'dev'
    command = verification_command(system, resource_profile, systemd_properties)
    result = subprocess.run(command, cwd=PROJECT_ROOT, env=env, check=False)
    return {
        'system': system,
        'pass': result.returncode == 0,
        'returncode': result.returncode,
        'command': 'SP1_CIRCUIT_MODE=dev ' + ' '.join(command),
    }


def main() -> int:
    args = parse_args()
    report = build_metadata_report()
    proof_verifications = []
    if report['metadata_pass'] and args.verify_compressed:
        proof_verifications.append(run_external_verification('compressed', args.resource_profile, args.systemd_property))
    if report['metadata_pass'] and args.verify_groth16:
        proof_verifications.append(run_external_verification('groth16', args.resource_profile, args.systemd_property))
    report['proof_verifications'] = proof_verifications
    report['pass'] = report['metadata_pass'] and all(item['pass'] for item in proof_verifications)
    if report['pass'] and not args.verbose:
        report.pop('checks')
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report['pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
