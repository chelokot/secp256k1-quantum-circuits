#!/usr/bin/env python3

from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any, Dict, Mapping

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_ROOT = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
CANDIDATE_ROOT = ARTIFACT_ROOT / 'zkp_attestation_reusable_chunk_candidate'


def _load(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text())


def _sha256_path(path: Path) -> str:
    from common import sha256_path

    return sha256_path(path)


def _sha256_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')
    return hashlib.sha256(encoded).hexdigest()


def _file_record(relative_path: str) -> Dict[str, Any]:
    path = PROJECT_ROOT / relative_path
    return {
        'path': relative_path,
        'sha256': _sha256_path(path),
        'bytes': path.stat().st_size,
    }


def _fixture_record(fixture_name: str) -> Dict[str, Any]:
    relative_path = f'compiler_verification_project/artifacts/zkp_attestation_reusable_chunk_candidate/{fixture_name}'
    fixture = _load(PROJECT_ROOT / relative_path)
    record = _file_record(relative_path)
    record['proof_system'] = fixture['proof_system']
    record['verification_key'] = fixture['verification_key']
    record['input_path'] = fixture.get('input_path')
    record['input_sha256'] = fixture.get('input_sha256')
    record['input_size_bytes'] = fixture.get('input_size_bytes')
    record['proof_path'] = fixture['proof_path']
    record['proof_sha256'] = fixture['proof_sha256']
    record['proof_size_bytes'] = fixture['proof_size_bytes']
    record['verifier_key_path'] = fixture['verifier_key_path']
    record['verifier_key_sha256'] = fixture['verifier_key_sha256']
    record['verifier_key_size_bytes'] = fixture['verifier_key_size_bytes']
    return record


def _comparison_rows(public_values: Mapping[str, Any], baseline: Mapping[str, Any]) -> Dict[str, Any]:
    non_clifford = int(public_values['expected_full_oracle_non_clifford'])
    qubits = int(public_values['expected_total_logical_qubits'])
    return {
        name: {
            'baseline_non_clifford': int(row['non_clifford']),
            'baseline_logical_qubits': int(row['logical_qubits']),
            'non_clifford_improvement_ratio': int(row['non_clifford']) / non_clifford,
            'qubit_delta_vs_baseline': int(row['logical_qubits']) - qubits,
            'beats_non_clifford': non_clifford < int(row['non_clifford']),
            'beats_logical_qubits': qubits < int(row['logical_qubits']),
        }
        for name, row in baseline.items()
    }


def build_public_headline_result(*, baseline: Mapping[str, Any]) -> Dict[str, Any]:
    input_payload = _load(CANDIDATE_ROOT / 'zkp_attestation_input.json')
    public_values = _load(CANDIDATE_ROOT / 'zkp_attestation_public_values.json')
    core_fixture = _load(CANDIDATE_ROOT / 'zkp_attestation_fixture_core.json')
    compressed_fixture = _load(CANDIDATE_ROOT / 'zkp_attestation_fixture_compressed.json')
    groth16_fixture = _load(CANDIDATE_ROOT / 'zkp_attestation_fixture_groth16.json')
    lowering = _load(ARTIFACT_ROOT / 'reusable_chunk_lowering.json')
    qroam_primitive = _load(ARTIFACT_ROOT / 'qroam_primitive_certificate.json')
    qroam_reference = _load(ARTIFACT_ROOT / 'qroam_reference_crosscheck.json')
    modular_arithmetic = _load(ARTIFACT_ROOT / 'modular_arithmetic_certificate.json')
    headline_resource_manifest = _load(ARTIFACT_ROOT / 'headline_resource_manifest.json')
    public_candidate_materialized_manifest = _load(ARTIFACT_ROOT / 'public_candidate_materialized_circuit_manifest.json')
    public_engine_manifest = _load(ARTIFACT_ROOT / 'public_engine_manifest.json')
    compiler_parameters = _load(ARTIFACT_ROOT / 'compiler_parameters.json')
    family_frontier = _load(ARTIFACT_ROOT / 'family_frontier.json')
    public_policy = compiler_parameters['public_headline_policy']
    non_clifford_limit = int(public_policy['non_clifford_limit_exclusive'])
    qubit_limit = int(public_policy['logical_qubit_limit_exclusive'])
    proof_corpus_profiles = _load(ARTIFACT_ROOT / 'proof_corpus_profiles.json')
    tail_candidate = _load(ARTIFACT_ROOT / 'reusable_chunk_tail_candidate.json')
    executable_liveness = lowering['executable_liveness']
    counted_resource_ir = lowering['counted_resource_ir']
    resource_contract_engine = lowering['resource_contract_engine']
    superseded_reference = family_frontier['best_qubit_family']
    engine_public_totals = public_engine_manifest['public_totals']
    materialized_public_totals = public_candidate_materialized_manifest['public_totals']
    current_values = {
        'schema': public_values['schema'],
        'selected_family_name': input_payload['selected_family_name'],
        'document_digest_scheme': input_payload['document_digest_scheme'],
        'claim_sha256': input_payload['claim_sha256'],
        'leaf_sha256': input_payload['leaf_sha256'],
        'family_sha256': input_payload['family_sha256'],
        'case_corpus_sha256': input_payload['case_corpus_sha256'],
        'resource_certificate_sha256': input_payload['resource_certificate_sha256'],
        'public_engine_manifest_sha256': input_payload['public_engine_manifest_sha256'],
        'expected_full_oracle_non_clifford': int(engine_public_totals['non_clifford']),
        'expected_total_logical_qubits': int(engine_public_totals['logical_qubits']),
        'case_count': int(input_payload['prepared_case_corpus']['case_count']),
        'passed_case_count': int(input_payload['prepared_case_corpus']['case_count']),
    }
    non_clifford = int(current_values['expected_full_oracle_non_clifford'])
    qubits = int(current_values['expected_total_logical_qubits'])
    checks = {
        'public_values_match_input_claim': (
            public_values['claim_sha256'] == input_payload['claim_sha256']
            and public_values['leaf_sha256'] == input_payload['leaf_sha256']
            and public_values['family_sha256'] == input_payload['family_sha256']
            and public_values['case_corpus_sha256'] == input_payload['case_corpus_sha256']
            and public_values['resource_certificate_sha256'] == input_payload['resource_certificate_sha256']
            and non_clifford == int(input_payload['claim_summary']['expected_full_oracle_non_clifford'])
            and qubits == int(input_payload['claim_summary']['expected_total_logical_qubits'])
        ),
        'public_headline_totals_come_from_engine_output': (
            public_engine_manifest['pass'] is True
            and public_candidate_materialized_manifest['pass'] is True
            and non_clifford == int(engine_public_totals['non_clifford'])
            and qubits == int(engine_public_totals['logical_qubits'])
            and non_clifford == int(materialized_public_totals['non_clifford'])
            and qubits == int(materialized_public_totals['logical_qubits'])
        ),
        'input_claim_summary_is_engine_snapshot_not_primary_formula': (
            input_payload['claim_summary']['resource_engine_summary']['non_clifford'] == non_clifford
            and input_payload['claim_summary']['resource_engine_summary']['logical_qubits'] == qubits
            and input_payload['claim_summary']['resource_engine_summary']['source'] == 'public_engine_manifest.public_totals'
            and input_payload['claim_summary']['resource_engine_summary']['source_document_type'] == 'public_engine_manifest'
            and input_payload['claim_summary']['resource_engine_summary']['source_sha256'] == input_payload['public_engine_manifest_sha256']
            and input_payload['claim_summary']['resource_engine_summary']['matches_family_snapshot'] is True
            and input_payload['claim_summary']['resource_engine_summary']['matches_resource_certificate_snapshot'] is True
            and int(input_payload['claim_summary']['non_clifford_formula']['reconstructed_total']) == non_clifford
            and int(input_payload['claim_summary']['logical_qubit_formula']['reconstructed_total']) == qubits
        ),
        'all_fixtures_bind_same_public_values': (
            core_fixture['public_values'] == public_values
            and compressed_fixture['public_values'] == public_values
            and groth16_fixture['public_values'] == public_values
        ),
        'fixtures_bind_checked_input_digest': (
            all(
                fixture.get('input_sha256') == _sha256_path(CANDIDATE_ROOT / 'zkp_attestation_input.json')
                and fixture.get('input_size_bytes') == (CANDIDATE_ROOT / 'zkp_attestation_input.json').stat().st_size
                for fixture in (core_fixture, compressed_fixture, groth16_fixture)
            )
        ),
        'compressed_fixture_binds_checked_proof_binary': (
            compressed_fixture['proof_path'] == 'compiler_verification_project/artifacts/zkp_attestation_reusable_chunk_candidate/zkp_attestation_proof_compressed.bin'
            and compressed_fixture['proof_sha256'] == _sha256_path(PROJECT_ROOT / compressed_fixture['proof_path'])
            and compressed_fixture['proof_size_bytes'] == (PROJECT_ROOT / compressed_fixture['proof_path']).stat().st_size
        ),
        'groth16_fixture_binds_checked_proof_and_verifier_key': (
            groth16_fixture['proof_path'] == 'compiler_verification_project/artifacts/zkp_attestation_reusable_chunk_candidate/zkp_attestation_proof_groth16.bin'
            and groth16_fixture['proof_sha256'] == _sha256_path(PROJECT_ROOT / groth16_fixture['proof_path'])
            and groth16_fixture['proof_size_bytes'] == (PROJECT_ROOT / groth16_fixture['proof_path']).stat().st_size
            and groth16_fixture['verifier_key_path'] == 'compiler_verification_project/artifacts/zkp_attestation_reusable_chunk_candidate/zkp_attestation_groth16_verifier/groth16_vk.bin'
            and groth16_fixture['verifier_key_sha256'] == _sha256_path(PROJECT_ROOT / groth16_fixture['verifier_key_path'])
            and groth16_fixture['verifier_key_size_bytes'] == (PROJECT_ROOT / groth16_fixture['verifier_key_path']).stat().st_size
        ),
        'reusable_chunk_lowering_is_proven_for_public_headline': (
            lowering['status'] == 'proven_public_headline'
            and lowering['pass'] is True
            and lowering['non_clifford_derivation']['candidate_total_non_clifford'] == non_clifford
            and lowering['qubit_derivation']['candidate_total_logical_qubits'] == qubits
        ),
        'reusable_chunk_executable_liveness_binds_public_qubits': (
            executable_liveness['pass'] is True
            and executable_liveness['global_peak_live_qubits'] == qubits
            and executable_liveness['owner_peak_live_qubits'] == executable_liveness['owner_capacity_qubits']
            and executable_liveness['checks']['qroam_target_and_qchunk_are_concurrently_live'] is True
            and executable_liveness['checks']['no_full_coordinate_lane_wire_is_live'] is True
        ),
        'reusable_chunk_counted_resource_ir_binds_public_totals': (
            counted_resource_ir['pass'] is True
            and counted_resource_ir['recomputed_total_non_clifford'] == non_clifford
            and counted_resource_ir['recomputed_peak_live_qubits'] == qubits
            and sum(term['total_non_clifford'] for term in counted_resource_ir['non_clifford_terms']) == non_clifford
            and max(interval['total_live_qubits'] for interval in counted_resource_ir['liveness_intervals']) == qubits
        ),
        'reusable_chunk_resource_contract_engine_unifies_liveness_and_capacity': (
            resource_contract_engine['pass'] is True
            and resource_contract_engine['peak_live_qubits'] == qubits
            and resource_contract_engine['owner_peak_live_qubits'] == resource_contract_engine['owner_capacity_qubits']
            and resource_contract_engine['checks']['counted_wire_catalog_matches_executable_liveness'] is True
            and resource_contract_engine['checks']['counted_intervals_match_executable_liveness'] is True
        ),
        'headline_resource_manifest_binds_current_public_result': (
            headline_resource_manifest['pass'] is True
            and headline_resource_manifest['selected_family_name'] == current_values['selected_family_name']
            and headline_resource_manifest['source_counted_resource_ir_sha256'] == resource_contract_engine['counted_resource_ir_sha256']
            and headline_resource_manifest['public_totals']['non_clifford'] == non_clifford
            and headline_resource_manifest['public_totals']['logical_qubits'] == qubits
            and headline_resource_manifest['checks']['term_rows_sum_to_public_total'] is True
            and headline_resource_manifest['checks']['liveness_rows_peak_to_public_qubits'] is True
        ),
        'public_engine_manifest_binds_current_public_result': (
            public_engine_manifest['pass'] is True
            and public_engine_manifest['selected_family_name'] == current_values['selected_family_name']
            and input_payload['public_engine_manifest_document']['payload'] == public_engine_manifest
            and input_payload['public_engine_manifest_document']['sha256'] == current_values['public_engine_manifest_sha256']
            and input_payload['public_engine_manifest_document']['document_type'] == 'public_engine_manifest'
            and public_engine_manifest['public_totals']['non_clifford'] == non_clifford
            and public_engine_manifest['public_totals']['logical_qubits'] == qubits
            and public_engine_manifest['source_digests']['counted_resource_ir_sha256'] == resource_contract_engine['counted_resource_ir_sha256']
            and public_engine_manifest['source_digests']['public_candidate_materialized_circuit_manifest_sha256'] == _sha256_payload(public_candidate_materialized_manifest)
            and public_engine_manifest['source_digests']['executable_liveness_sha256'] == resource_contract_engine['executable_liveness_sha256']
            and public_engine_manifest['source_digests']['owner_capacity_sha256'] == resource_contract_engine['owner_capacity_sha256']
            and public_engine_manifest['fast_no_zkp_contract']['prover_required'] is False
        ),
        'public_candidate_materialized_manifest_binds_current_public_result': (
            public_candidate_materialized_manifest['pass'] is True
            and public_candidate_materialized_manifest['selected_family_name'] == current_values['selected_family_name']
            and public_candidate_materialized_manifest['public_totals']['non_clifford'] == non_clifford
            and public_candidate_materialized_manifest['public_totals']['logical_qubits'] == qubits
            and public_candidate_materialized_manifest['source_digests']['counted_resource_ir_sha256'] == resource_contract_engine['counted_resource_ir_sha256']
            and public_candidate_materialized_manifest['qroam_expansion']['non_clifford'] == lowering['non_clifford_derivation']['qroam_chunk_non_clifford']
        ),
        'proof_register_contract_binds_prepared_leaf_to_resource_owners': (
            input_payload['proof_register_contract']['pass'] is True
            and len(input_payload['proof_register_contract']['register_rows']) == input_payload['prepared_leaf']['register_count']
            and input_payload['proof_register_contract']['checks']['every_register_has_declared_contract_class'] is True
            and input_payload['proof_register_contract']['checks']['every_unclassified_written_register_is_rejected'] is True
            and input_payload['proof_register_contract']['checks']['semantic_lookup_constants_are_not_materialized_full_coordinate_lanes'] is True
        ),
        'compiler_parameters_document_binds_parameter_source': (
            input_payload['compiler_parameters_document']['payload'] == compiler_parameters
            and input_payload['compiler_parameters_document']['sha256'] == input_payload['compiler_parameters_sha256']
            and compiler_parameters['pass'] is True
            and isinstance(compiler_parameters['parameter_digest_sha256'], str)
            and len(compiler_parameters['parameter_digest_sha256']) == 64
        ),
        'reusable_chunk_binds_generated_qroam_primitive_certificate': (
            qroam_primitive['pass'] is True
            and lowering['qroam_primitive_certificate'] == qroam_primitive
            and lowering['checks']['per_stream_cost_matches_generated_qroam_primitive'] is True
            and qroam_primitive['traversed_counts']['per_stream_non_clifford'] == lowering['standard_qroamclean_k1_model']['per_stream_non_clifford']
            and qroam_primitive['traversed_counts']['target_plus_junk_qubits'] == lowering['standard_qroamclean_k1_model']['target_plus_junk_qubits']
        ),
        'reusable_chunk_binds_independent_qroam_reference_crosscheck': (
            qroam_reference['pass'] is True
            and lowering['qroam_reference_crosscheck'] == qroam_reference
            and lowering['checks']['per_stream_cost_matches_independent_qroam_reference_crosscheck'] is True
            and qroam_reference['selected_reference']['per_stream_non_clifford'] == lowering['standard_qroamclean_k1_model']['per_stream_non_clifford']
            and qroam_reference['selected_reference']['target_plus_junk_qubits'] == lowering['standard_qroamclean_k1_model']['target_plus_junk_qubits']
        ),
        'reusable_chunk_binds_modular_arithmetic_certificate': (
            modular_arithmetic['pass'] is True
            and lowering['modular_arithmetic_certificate'] == modular_arithmetic
            and lowering['checks']['modular_arithmetic_certificate_binds_counted_field_mul'] is True
            and modular_arithmetic['field_mul_stage_count_certificate']['stage_counts_match'] is True
            and modular_arithmetic['field_mul_stage_count_certificate']['observed_total_ccx'] == modular_arithmetic['field_mul_stage_count_certificate']['expected_total_ccx']
            and modular_arithmetic['executable_circuit_ir_count_certificate']['counts_match_arithmetic_lowerings'] is True
            and modular_arithmetic['executable_circuit_ir_count_certificate']['observed_non_clifford_per_opcode'] == modular_arithmetic['executable_circuit_ir_count_certificate']['expected_non_clifford_per_opcode']
            and modular_arithmetic['opcode_count_certificate']['opcode_counts_match'] is True
            and modular_arithmetic['opcode_count_certificate']['observed_non_clifford_per_opcode'] == modular_arithmetic['opcode_count_certificate']['expected_non_clifford_per_opcode']
            and modular_arithmetic['executable_modular_circuit_ir']['schema'] == 'compiler-project-executable-modular-circuit-ir-v1'
            and modular_arithmetic['executable_circuit_ir_count_certificate']['counts_match_arithmetic_lowerings'] is True
            and modular_arithmetic['executable_circuit_ir_count_certificate']['observed_non_clifford_per_opcode'] == modular_arithmetic['executable_circuit_ir_count_certificate']['expected_non_clifford_per_opcode']
        ),
        'reusable_chunk_tail_contract_is_proven_for_public_headline': (
            tail_candidate['status'] == 'proven_public_headline'
            and tail_candidate['toy_semantic_equivalence']['all_rows_semantic'] is True
            and tail_candidate['toy_semantic_equivalence']['all_rows_executable'] is True
        ),
        'fits_strict_public_goal': non_clifford < non_clifford_limit and qubits < qubit_limit,
        'public_case_count_matches_selected_proof_profile': (
            int(current_values['case_count'])
            == int(current_values['passed_case_count'])
            == int(proof_corpus_profiles['profiles'][proof_corpus_profiles['selected_public_profile']]['case_count'])
        ),
    }
    return {
        'schema': 'compiler-project-public-headline-result-v1',
        'selected_result': {
            'name': current_values['selected_family_name'],
            'non_clifford': non_clifford,
            'logical_qubits': qubits,
            'case_count': current_values['case_count'],
            'passed_case_count': current_values['passed_case_count'],
            'document_digest_scheme': current_values['document_digest_scheme'],
        },
        'selection_policy': {
            'role': 'single public repository headline',
            'reason': 'Verified reusable-chunk four-slot contract is the strongest checked result that keeps non-Clifford below the compiler-parameter headline limit and logical qubits strictly below the compiler-parameter headline limit under the strict standard-QROAM model.',
            'limits': dict(public_policy),
            'supersedes_for_public_headline': [
                'folded_standard_qroam_streamed_coordinate_v1__streamed_lookup_tail_leaf_v1__semiclassical_qft_v1',
            ],
            'superseded_result_kept_as_reference': {
                'name': superseded_reference['name'],
                'non_clifford': int(superseded_reference['full_oracle_non_clifford']),
                'logical_qubits': int(superseded_reference['total_logical_qubits']),
                'reason': 'Lower qubit count at the earlier three-slot compiler-family boundary, but not the selected stricter four-slot reusable-chunk public headline.',
            },
        },
        'comparison_to_public_google_baseline': _comparison_rows(current_values, baseline),
        'bound_documents': {
            'claim_sha256': current_values['claim_sha256'],
            'leaf_sha256': current_values['leaf_sha256'],
            'family_sha256': current_values['family_sha256'],
            'case_corpus_sha256': current_values['case_corpus_sha256'],
            'resource_certificate_sha256': current_values['resource_certificate_sha256'],
            'public_engine_manifest_sha256': current_values['public_engine_manifest_sha256'],
        },
        'checked_artifacts': {
            'input': _file_record('compiler_verification_project/artifacts/zkp_attestation_reusable_chunk_candidate/zkp_attestation_input.json'),
            'claim': _file_record('compiler_verification_project/artifacts/zkp_attestation_reusable_chunk_candidate/zkp_attestation_claim.json'),
            'family': _file_record('compiler_verification_project/artifacts/zkp_attestation_reusable_chunk_candidate/zkp_attestation_family.json'),
            'case_corpus': _file_record('compiler_verification_project/artifacts/zkp_attestation_reusable_chunk_candidate/zkp_attestation_cases.json'),
            'proof_corpus_profiles': _file_record('compiler_verification_project/artifacts/proof_corpus_profiles.json'),
            'compiler_parameters': _file_record('compiler_verification_project/artifacts/compiler_parameters.json'),
            'public_values': _file_record('compiler_verification_project/artifacts/zkp_attestation_reusable_chunk_candidate/zkp_attestation_public_values.json'),
            'core_fixture': _fixture_record('zkp_attestation_fixture_core.json'),
            'compressed_fixture': _fixture_record('zkp_attestation_fixture_compressed.json'),
            'groth16_fixture': _fixture_record('zkp_attestation_fixture_groth16.json'),
            'compressed_proof': _file_record('compiler_verification_project/artifacts/zkp_attestation_reusable_chunk_candidate/zkp_attestation_proof_compressed.bin'),
            'groth16_proof': _file_record('compiler_verification_project/artifacts/zkp_attestation_reusable_chunk_candidate/zkp_attestation_proof_groth16.bin'),
            'wrap_proof': _file_record('compiler_verification_project/artifacts/zkp_attestation_reusable_chunk_candidate/zkp_attestation_wrap_proof.bin'),
            'groth16_verifier_key': _file_record('compiler_verification_project/artifacts/zkp_attestation_reusable_chunk_candidate/zkp_attestation_groth16_verifier/groth16_vk.bin'),
            'qroam_primitive_certificate': _file_record('compiler_verification_project/artifacts/qroam_primitive_certificate.json'),
            'qroam_reference_crosscheck': _file_record('compiler_verification_project/artifacts/qroam_reference_crosscheck.json'),
            'modular_arithmetic_certificate': _file_record('compiler_verification_project/artifacts/modular_arithmetic_certificate.json'),
            'reusable_chunk_lowering': _file_record('compiler_verification_project/artifacts/reusable_chunk_lowering.json'),
            'reusable_chunk_tail_candidate': _file_record('compiler_verification_project/artifacts/reusable_chunk_tail_candidate.json'),
            'headline_resource_manifest': _file_record('compiler_verification_project/artifacts/headline_resource_manifest.json'),
            'public_candidate_materialized_circuit_manifest': _file_record('compiler_verification_project/artifacts/public_candidate_materialized_circuit_manifest.json'),
            'public_engine_manifest': _file_record('compiler_verification_project/artifacts/public_engine_manifest.json'),
        },
        'verification_commands': {
            'metadata': 'python compiler_verification_project/scripts/verify_public_headline.py',
            'metadata_and_compressed': 'python compiler_verification_project/scripts/verify_public_headline.py --verify-compressed',
            'metadata_and_groth16': 'python compiler_verification_project/scripts/verify_public_headline.py --verify-groth16',
            'compressed': 'SP1_CIRCUIT_MODE=dev python compiler_verification_project/scripts/run_zkp_attestation_guarded.py --verify-proof-input compiler_verification_project/artifacts/zkp_attestation_reusable_chunk_candidate/zkp_attestation_proof_compressed.bin --system compressed --resource-profile safe --systemd-property TasksMax=128 --skip-build --input compiler_verification_project/artifacts/zkp_attestation_reusable_chunk_candidate/zkp_attestation_input.json --output-dir compiler_verification_project/artifacts/zkp_attestation_reusable_chunk_candidate',
            'groth16': 'SP1_CIRCUIT_MODE=dev python compiler_verification_project/scripts/run_zkp_attestation_guarded.py --verify-proof-input compiler_verification_project/artifacts/zkp_attestation_reusable_chunk_candidate/zkp_attestation_proof_groth16.bin --system groth16 --resource-profile safe --systemd-property TasksMax=128 --skip-build --groth16-verify-dir compiler_verification_project/artifacts/zkp_attestation_reusable_chunk_candidate/zkp_attestation_groth16_verifier --input compiler_verification_project/artifacts/zkp_attestation_reusable_chunk_candidate/zkp_attestation_input.json --output-dir compiler_verification_project/artifacts/zkp_attestation_reusable_chunk_candidate',
        },
        'reviewer_verification': {
            'fast_metadata_command': 'python compiler_verification_project/scripts/verify_public_headline.py',
            'compressed_verification_command': 'python compiler_verification_project/scripts/verify_public_headline.py --verify-compressed',
            'groth16_verification_command': 'python compiler_verification_project/scripts/verify_public_headline.py --verify-groth16',
            'metadata_scope': [
                'public headline result status and strict <40M / <1200 bounds',
                'checked input, public values, sidecar documents, fixtures, proof binaries, wrap proof, and Groth16 verifier-key digests',
                'semantic hashes for committed claim, leaf, family, case corpus, and resource-certificate documents',
                'generated QROAM K=1 primitive-count certificate bound into the reusable-chunk resource document',
                'executable liveness peak, qchunk/QROAM-target concurrency, and owner-capacity checks',
                'current-headline counted-resource stream manifest derived from reusable_chunk_lowering counted_resource_ir',
                'public engine manifest binding instruction, wire, schedule, owner, and resource-term streams without invoking a prover',
                'fixture-to-proof and fixture-to-verifier-key binding',
            ],
        },
        'checks': checks,
        'pass': all(checks.values()),
        'boundary': [
            'This is a checked standard-QROAM compiler-family boundary, not a Clifford-complete flattened full-Shor netlist.',
            'The checked proof uses the selected public proof-corpus profile, currently an explicit 8-case smoke profile rather than Google\'s hidden-circuit 9024-case disclosure boundary.',
            'The proof binds and executes the reusable-chunk contract and resource certificate; it does not by itself prove an external physical runtime.',
        ],
    }


def write_public_headline_result(*, baseline: Mapping[str, Any]) -> Dict[str, Any]:
    from common import dump_json

    payload = build_public_headline_result(baseline=baseline)
    dump_json(ARTIFACT_ROOT / 'public_headline_result.json', payload)
    return payload


__all__ = ['build_public_headline_result', 'write_public_headline_result']
