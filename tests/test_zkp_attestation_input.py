from __future__ import annotations

import json
import hashlib
import subprocess
import sys
from functools import lru_cache
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
COMPILER_SRC = REPO_ROOT / 'compiler_verification_project' / 'src'
ROOT_SRC = REPO_ROOT / 'src'
if str(COMPILER_SRC) not in sys.path:
    sys.path.insert(0, str(COMPILER_SRC))
if str(ROOT_SRC) not in sys.path:
    sys.path.insert(0, str(ROOT_SRC))

from common import SECP_P, add_affine, affine_to_proj, proj_to_affine  # noqa: E402
from lookup_fed_leaf import build_streamed_lookup_tail_leaf, execute_leaf_contract  # noqa: E402
from proof_corpus_profiles import GOOGLE_COMPARABLE_CASE_COUNT, GOOGLE_COMPARABLE_PROFILE, resolve_proof_corpus_profile, selected_public_case_count  # noqa: E402
from zkp_attestation import DIGEST_SCHEME, build_zkp_attestation_input, write_zkp_attestation_inputs  # noqa: E402


@lru_cache(maxsize=None)
def _proof_status_report() -> dict:
    result = subprocess.run(
        [sys.executable, 'compiler_verification_project/scripts/proof_status.py'],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


@lru_cache(maxsize=None)
def _default_payload() -> dict:
    return build_zkp_attestation_input()


@lru_cache(maxsize=None)
def _reusable_chunk_payload(case_count: int | None = None) -> dict:
    if case_count is None:
        case_count = selected_public_case_count()
    return build_zkp_attestation_input(family_name='reusable-chunk', case_count=case_count)


def test_zkp_attestation_input_reconstructs_public_claim() -> None:
    payload = _default_payload()
    claim = payload['claim_summary']
    family = payload['family_summary']
    resource_document = payload['resource_certificate_document']
    arithmetic_operation_ir = resource_document['payload']['arithmetic_operation_ir']
    non_clifford = claim['non_clifford_formula']
    qubits = claim['logical_qubit_formula']
    assert non_clifford['reconstructed_total'] == family['full_oracle_non_clifford']
    assert claim['expected_full_oracle_non_clifford'] == family['full_oracle_non_clifford']
    assert qubits['reconstructed_total'] == family['total_logical_qubits']
    assert claim['expected_total_logical_qubits'] == family['total_logical_qubits']
    assert family['name'].endswith('__streamed_lookup_tail_leaf_v1__semiclassical_qft_v1')
    assert resource_document['document_type'] == 'resource_liveness_certificate'
    assert arithmetic_operation_ir['schema'] == 'compiler-project-arithmetic-operation-ir-v1'
    assert arithmetic_operation_ir['pass'] is True
    assert arithmetic_operation_ir['summary']['kernel_count'] == len(arithmetic_operation_ir['kernels'])
    assert arithmetic_operation_ir['leaf_arithmetic_summary']['non_clifford_total'] == family['arithmetic_leaf_non_clifford']
    assert arithmetic_operation_ir['leaf_arithmetic_summary']['operation_stream_sha256']
    frontier = json.loads((REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'family_frontier.json').read_text())
    assert family['full_oracle_non_clifford'] == frontier['best_gate_family']['full_oracle_non_clifford']
    assert family['total_logical_qubits'] == frontier['best_gate_family']['total_logical_qubits']


def test_reusable_chunk_zkp_attestation_input_binds_candidate_contract() -> None:
    payload = _reusable_chunk_payload()
    claim = payload['claim_summary']
    family = payload['family_summary']
    family_document = payload['family_document']['payload']
    leaf_document = payload['leaf_document']
    resource_document = payload['resource_certificate_document']
    compiler_parameters_document = payload['compiler_parameters_document']
    liveness = resource_document['payload']['executable_liveness']
    primitive_contract = resource_document['payload']['chunked_multiplier_primitive_contract']
    qroam_primitive = resource_document['payload']['qroam_primitive_certificate']
    qroam_reference = resource_document['payload']['qroam_reference_crosscheck']
    modular_certificate = resource_document['payload']['modular_arithmetic_certificate']
    stream_plan = resource_document['payload']['stream_plan']
    scratch_execution_contract = resource_document['payload']['executable_contract']['scratch_execution_contract']
    qroam_model = resource_document['payload']['standard_qroamclean_k1_model']
    qubit_derivation = resource_document['payload']['qubit_derivation']
    non_clifford_derivation = resource_document['payload']['non_clifford_derivation']
    counted_resource_ir = resource_document['payload']['counted_resource_ir']
    proof_register_contract = payload['proof_register_contract']
    phase_shells = json.loads((REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'phase_shell_lowerings.json').read_text())
    phase_shell = next(row for row in phase_shells['families'] if row['name'] == family_document['phase_shell'])
    generated_inventories = json.loads((REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'generated_block_inventories.json').read_text())
    direct_seed_values = {
        int(row['reconstruction']['direct_seed_non_clifford'])
        for row in generated_inventories['families']
        if 'direct_seed_non_clifford' in row.get('reconstruction', {})
    }
    for selected_key in ('best_gate_family', 'best_qubit_family'):
        selected = generated_inventories[selected_key]
        if 'direct_seed_non_clifford' in selected.get('reconstruction', {}):
            direct_seed_values.add(int(selected['reconstruction']['direct_seed_non_clifford']))
    assert payload['selected_family_name'].endswith('__reusable_chunk_tail_leaf_v1__semiclassical_qft_v1')
    assert claim['expected_full_oracle_non_clifford'] == non_clifford_derivation['candidate_total_non_clifford']
    assert claim['expected_total_logical_qubits'] == qubit_derivation['candidate_total_logical_qubits']
    assert len(direct_seed_values) == 1
    assert family['direct_seed_non_clifford'] == next(iter(direct_seed_values))
    assert family['arithmetic_slot_count'] == qubit_derivation['arithmetic_slot_count']
    assert family['lookup_workspace_qubits'] == qubit_derivation['lookup_workspace_qubits']
    assert family_document['phase_shell_hadamards'] == phase_shell['hadamard_count']
    assert family_document['phase_shell_measurements'] == phase_shell['measurement_count']
    assert family_document['phase_shell_rotations'] == phase_shell['rotation_count']
    assert family_document['phase_shell_rotation_depth'] == phase_shell['rotation_depth']
    assert family_document['total_measurements'] == phase_shell['total_measurements']
    assert leaf_document['document_type'] == 'reusable_chunk_tail_leaf'
    assert resource_document['document_type'] == 'reusable_chunk_lowering'
    assert compiler_parameters_document['document_type'] == 'compiler_parameters'
    assert payload['compiler_parameters_sha256'] == compiler_parameters_document['sha256']
    assert compiler_parameters_document['payload']['pass'] is True
    assert compiler_parameters_document['payload']['parameter_digest_sha256']
    assert resource_document['payload']['status'] == 'proven_public_headline'
    assert payload['prepared_leaf']['instructions'][-1]['kind'] == 'complete_a0_reusable_chunk_tail'
    assert payload['prepared_leaf']['instructions'][-1]['chunk_bits'] == stream_plan['chunk_bits']
    assert payload['prepared_leaf']['instructions'][-1]['chunk_count'] == stream_plan['chunk_count']
    assert primitive_contract['chunk_effective_bits'] == [
        max(0, min(stream_plan['chunk_bits'], qubit_derivation['field_bits'] - stream_plan['chunk_bits'] * index))
        for index in range(stream_plan['chunk_count'])
    ]
    assert primitive_contract['table_multiplier_partial_products_per_leaf'] == primitive_contract['inherited_table_multiplier_partial_products_per_leaf']
    assert qroam_primitive['pass'] is True
    assert qroam_primitive['parameters']['domain_size'] == qroam_model['domain_size']
    assert qroam_primitive['parameters']['target_bits'] == qroam_model['target_register_qubits']
    assert qroam_primitive['parameters']['block_size'] == qroam_model['block_size']
    assert qroam_primitive['traversed_counts']['per_stream_non_clifford'] == qroam_model['per_stream_non_clifford']
    assert qroam_primitive['traversed_counts']['target_plus_junk_qubits'] == qroam_model['target_plus_junk_qubits']
    assert qroam_reference['pass'] is True
    assert qroam_reference['selected_reference']['per_stream_non_clifford'] == qroam_model['per_stream_non_clifford']
    assert qroam_reference['selected_reference']['target_plus_junk_qubits'] == qroam_model['target_plus_junk_qubits']
    assert modular_certificate['pass'] is True
    assert modular_certificate['secp256k1_parameters']['field_bits'] == qubit_derivation['field_bits']
    assert modular_certificate['opcode_count_certificate']['opcode_counts_match'] is True
    assert modular_certificate['opcode_count_certificate']['observed_non_clifford_per_opcode']['field_add'] == 2 * (qubit_derivation['field_bits'] - 1)
    assert modular_certificate['opcode_count_certificate']['observed_non_clifford_per_opcode']['mul_const'] == 6 * 2 * (qubit_derivation['field_bits'] - 1)
    assert modular_certificate['field_mul_stage_count_certificate']['observed_total_ccx'] == modular_certificate['field_mul_stage_count_certificate']['expected_total_ccx']
    assert modular_certificate['field_mul_stage_count_certificate']['stage_counts_match'] is True
    assert all(row['rows_checked'] == row['modulus'] * row['modulus'] for row in modular_certificate['reduced_width_exhaustive_cases'])
    assert resource_document['payload']['owner_capacity']['capacity_global_peak_qubits'] == qubit_derivation['candidate_total_logical_qubits']
    assert liveness['pass'] is True
    assert liveness['global_peak_live_qubits'] == qubit_derivation['candidate_total_logical_qubits']
    assert liveness['owner_peak_live_qubits'] == liveness['owner_capacity_qubits']
    assert liveness['checks']['qroam_target_and_qchunk_are_concurrently_live'] is True
    assert liveness['checks']['no_full_coordinate_lane_wire_is_live'] is True
    assert scratch_execution_contract['scratch_register'] == 'qchunk'
    assert scratch_execution_contract['chunk_load_events_per_leaf'] == 5 * stream_plan['chunk_count']
    assert scratch_execution_contract['final_scratch_value'] == 0
    assert resource_document['payload']['checks']['executable_leaf_executes_reusable_chunk_scratch_contract'] is True
    assert counted_resource_ir['pass'] is True
    assert counted_resource_ir['recomputed_total_non_clifford'] == non_clifford_derivation['candidate_total_non_clifford']
    assert counted_resource_ir['recomputed_peak_live_qubits'] == qubit_derivation['candidate_total_logical_qubits']
    assert sum(row['total_non_clifford'] for row in counted_resource_ir['non_clifford_terms']) == claim['expected_full_oracle_non_clifford']
    assert max(row['total_live_qubits'] for row in counted_resource_ir['liveness_intervals']) == claim['expected_total_logical_qubits']
    assert proof_register_contract['pass'] is True
    assert proof_register_contract['checks']['every_register_has_declared_contract_class'] is True
    assert proof_register_contract['checks']['every_unclassified_written_register_is_rejected'] is True
    assert proof_register_contract['checks']['semantic_lookup_constants_are_not_materialized_full_coordinate_lanes'] is True
    assert len(proof_register_contract['register_rows']) == payload['prepared_leaf']['register_count']
    counted_registers = {
        row['register']
        for row in proof_register_contract['register_rows']
        if row['resource_class'] == 'counted_quantum_wire'
    }
    assert {'qx', 'qy', 'qz', 'qchunk', 'f_lookup_inf'}.issubset(counted_registers)
    written_registers = {
        row['register']
        for row in proof_register_contract['register_rows']
        if row['is_written_by_instruction']
    }
    assert {'qx', 'qy', 'qz', 'qchunk', 'f_lookup_inf'}.issubset(written_registers)
    semantic_lookup_registers = {
        row['register']
        for row in proof_register_contract['register_rows']
        if row['resource_class'] == 'semantic_lookup_constant'
    }
    assert semantic_lookup_registers == {'lookup_x', 'lookup_y'}
    assert resource_document['payload']['pass'] is True


def test_checked_reusable_chunk_candidate_core_fixture_matches_bundle() -> None:
    payload = _reusable_chunk_payload()
    artifact_dir = REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'zkp_attestation_reusable_chunk_candidate'
    public_values = json.loads((artifact_dir / 'zkp_attestation_public_values.json').read_text())
    fixture = json.loads((artifact_dir / 'zkp_attestation_fixture_core.json').read_text())
    assert public_values['selected_family_name'] == payload['selected_family_name']
    assert public_values['passed_case_count'] == public_values['case_count'] == selected_public_case_count()
    assert fixture['proof_system'] == 'core'
    assert fixture['public_values'] == public_values
    status = _proof_status_report()
    if status['all_current']:
        assert public_values['claim_sha256'] == payload['claim_sha256']
        assert public_values['expected_full_oracle_non_clifford'] == payload['claim_summary']['expected_full_oracle_non_clifford']
        assert public_values['expected_total_logical_qubits'] == payload['claim_summary']['expected_total_logical_qubits']
        assert public_values['resource_certificate_sha256'] == payload['resource_certificate_sha256']
    else:
        assert 'core' in status['stale_systems']
        assert status['resource_certificate_sha256'] == payload['resource_certificate_sha256']
        assert public_values['claim_sha256'] != payload['claim_sha256']
        assert public_values['resource_certificate_sha256'] == status['public_values_resource_certificate_sha256']


def _assert_attestation_fixtures_match_public_values(
    artifact_dir: Path,
    expected: dict[str, tuple[str, str | None, str | None, str | None]],
) -> None:
    public_values = json.loads((artifact_dir / 'zkp_attestation_public_values.json').read_text())
    verification_key = None
    for fixture_name, (proof_system, proof_prefix, proof_path, verifier_key_path) in expected.items():
        fixture = json.loads((artifact_dir / fixture_name).read_text())
        assert fixture['schema'] == 'compiler-project-zkp-attestation-fixture-v1'
        assert fixture['proof_system'] == proof_system
        assert fixture['public_values'] == public_values
        if proof_prefix is None:
            assert fixture['proof'] is None
        else:
            assert isinstance(fixture['proof'], str)
            assert fixture['proof'].startswith(proof_prefix)
        if verification_key is None:
            verification_key = fixture['verification_key']
        assert fixture['verification_key'] == verification_key
        if proof_path is None:
            assert fixture['proof_path'] is None
            assert fixture['proof_sha256'] is None
            assert fixture['proof_size_bytes'] is None
        else:
            proof_file = REPO_ROOT / proof_path
            proof_bytes = proof_file.read_bytes()
            assert fixture['proof_path'] == proof_path
            assert fixture['proof_sha256'] == hashlib.sha256(proof_bytes).hexdigest()
            assert fixture['proof_size_bytes'] == len(proof_bytes)
        assert {'input_path', 'input_sha256', 'input_size_bytes'}.issubset(fixture)
        if fixture['input_path'] is None:
            assert fixture['input_sha256'] is None
            assert fixture['input_size_bytes'] is None
        else:
            input_file = REPO_ROOT / fixture['input_path']
            input_bytes = input_file.read_bytes()
            assert fixture['input_sha256'] == hashlib.sha256(input_bytes).hexdigest()
            assert fixture['input_size_bytes'] == len(input_bytes)
        if verifier_key_path is None:
            assert fixture['verifier_key_path'] is None
            assert fixture['verifier_key_sha256'] is None
            assert fixture['verifier_key_size_bytes'] is None
        else:
            verifier_key_file = REPO_ROOT / verifier_key_path
            verifier_key_bytes = verifier_key_file.read_bytes()
            assert fixture['verifier_key_path'] == verifier_key_path
            assert fixture['verifier_key_sha256'] == hashlib.sha256(verifier_key_bytes).hexdigest()
            assert fixture['verifier_key_size_bytes'] == len(verifier_key_bytes)


def test_checked_reusable_chunk_candidate_fixtures_match_public_values() -> None:
    artifact_dir = REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'zkp_attestation_reusable_chunk_candidate'
    expected_by_system = {
        'zkp_attestation_fixture_core.json': ('core', None, None, None),
        'zkp_attestation_fixture_compressed.json': (
            'compressed',
            None,
            'compiler_verification_project/artifacts/zkp_attestation_reusable_chunk_candidate/zkp_attestation_proof_compressed.bin',
            None,
        ),
        'zkp_attestation_fixture_groth16.json': (
            'groth16',
            '0x',
            'compiler_verification_project/artifacts/zkp_attestation_reusable_chunk_candidate/zkp_attestation_proof_groth16.bin',
            'compiler_verification_project/artifacts/zkp_attestation_reusable_chunk_candidate/zkp_attestation_groth16_verifier/groth16_vk.bin',
        ),
    }
    status = _proof_status_report()
    if status['all_current']:
        expected = expected_by_system
    else:
        expected = {
            fixture_name: expected_row
            for fixture_name, expected_row in expected_by_system.items()
            if status['systems'][expected_row[0]]['public_values_match_current']
        }
        assert set(expected) != set(expected_by_system)
    _assert_attestation_fixtures_match_public_values(artifact_dir, expected)


def test_public_headline_result_binds_reusable_chunk_candidate_artifacts() -> None:
    artifact_dir = REPO_ROOT / 'compiler_verification_project' / 'artifacts'
    public_result = json.loads((artifact_dir / 'public_headline_result.json').read_text())
    selected = public_result['selected_result']
    input_payload = json.loads((artifact_dir / 'zkp_attestation_reusable_chunk_candidate' / 'zkp_attestation_input.json').read_text())
    public_values = json.loads((artifact_dir / 'zkp_attestation_reusable_chunk_candidate' / 'zkp_attestation_public_values.json').read_text())
    status = _proof_status_report()
    assert public_result['pass'] is status['all_current']
    if status['all_current']:
        assert all(public_result['checks'].values())
    else:
        assert public_result['checks']['fits_strict_public_goal'] is True
        assert public_result['checks']['public_values_match_input_claim'] is False
        assert public_result['checks']['all_fixtures_bind_same_public_values'] is False
    assert public_result['checks']['reusable_chunk_lowering_is_proven_for_public_headline'] is True
    assert public_result['checks']['reusable_chunk_executable_liveness_binds_public_qubits'] is True
    assert public_result['checks']['reusable_chunk_binds_generated_qroam_primitive_certificate'] is True
    assert public_result['checks']['reusable_chunk_binds_modular_arithmetic_certificate'] is True
    assert public_result['checks']['reusable_chunk_tail_contract_is_proven_for_public_headline'] is True
    assert selected['non_clifford'] == input_payload['claim_summary']['expected_full_oracle_non_clifford']
    assert selected['logical_qubits'] == input_payload['claim_summary']['expected_total_logical_qubits']
    public_policy = public_result['selection_policy']['limits']
    assert selected['non_clifford'] < public_policy['non_clifford_limit_exclusive']
    assert selected['logical_qubits'] < public_policy['logical_qubit_limit_exclusive']
    assert selected['name'] == input_payload['selected_family_name']
    assert public_values['expected_full_oracle_non_clifford'] != selected['non_clifford'] or status['all_current']
    checked = public_result['checked_artifacts']
    for key in ('compressed_proof', 'groth16_proof', 'wrap_proof', 'groth16_verifier_key'):
        record = checked[key]
        path = REPO_ROOT / record['path']
        data = path.read_bytes()
        assert record['sha256'] == hashlib.sha256(data).hexdigest()
        assert record['bytes'] == len(data)


def test_zkp_attestation_cases_match_leaf_and_group_law() -> None:
    payload = _default_payload()
    leaf = build_streamed_lookup_tail_leaf()
    case_corpus = payload['prepared_case_corpus']
    for case in case_corpus['cases']:
        accumulator = None if case['accumulator'] is None else (
            int(case['accumulator']['x_hex'], 16),
            int(case['accumulator']['y_hex'], 16),
        )
        lookup = None if case['lookup'] is None else (
            int(case['lookup']['x_hex'], 16),
            int(case['lookup']['y_hex'], 16),
        )
        expected = None if case['expected'] is None else (
            int(case['expected']['x_hex'], 16),
            int(case['expected']['y_hex'], 16),
        )
        observed = proj_to_affine(
            execute_leaf_contract(
                leaf,
                SECP_P,
                affine_to_proj(accumulator, SECP_P),
                lookup,
                0 if lookup is None else 1,
            ),
            SECP_P,
        )
        assert observed == expected
        assert add_affine(accumulator, lookup, SECP_P, 7) == expected


def test_checked_in_zkp_attestation_bundle_matches_default_build(tmp_path: Path) -> None:
    payload = write_zkp_attestation_inputs(output_dir=tmp_path)
    artifact_dir = REPO_ROOT / 'compiler_verification_project' / 'artifacts'
    assert json.loads((artifact_dir / 'zkp_attestation_input.json').read_text()) == payload
    assert json.loads((artifact_dir / 'zkp_attestation_claim.json').read_text()) == json.loads((tmp_path / 'zkp_attestation_claim.json').read_text())
    assert json.loads((artifact_dir / 'zkp_attestation_family.json').read_text()) == json.loads((tmp_path / 'zkp_attestation_family.json').read_text())
    assert json.loads((artifact_dir / 'zkp_attestation_cases.json').read_text()) == json.loads((tmp_path / 'zkp_attestation_cases.json').read_text())


def test_checked_in_public_values_and_core_fixture_match_bundle() -> None:
    payload = _default_payload()
    artifact_dir = REPO_ROOT / 'compiler_verification_project' / 'artifacts'
    public_values = json.loads((artifact_dir / 'zkp_attestation_public_values.json').read_text())
    fixture = json.loads((artifact_dir / 'zkp_attestation_fixture_core.json').read_text())
    assert public_values['schema'] == 'compiler-project-zkp-attestation-public-v2'
    assert public_values['document_digest_scheme'] == DIGEST_SCHEME
    assert public_values['selected_family_name'] == payload['selected_family_name']
    assert public_values['leaf_sha256'] == payload['leaf_sha256']
    assert public_values['case_corpus_sha256'] == payload['case_corpus_sha256']
    status = _proof_status_report()
    if public_values['claim_sha256'] == payload['claim_sha256'] and public_values['resource_certificate_sha256'] == payload['resource_certificate_sha256']:
        assert public_values['family_sha256'] == payload['family_sha256']
        assert status['systems']['core']['resource_digest_matches_input'] is True
    else:
        assert 'core' in status['stale_systems']
        assert status['systems']['core']['resource_digest_matches_input'] is False
        assert public_values['claim_sha256'] != payload['claim_sha256']
        assert status['resource_certificate_sha256'] != public_values['resource_certificate_sha256']
    assert public_values['case_count'] == payload['prepared_case_corpus']['case_count']
    assert public_values['passed_case_count'] == public_values['case_count']
    assert fixture['proof_system'] == 'core'
    assert fixture['proof'] is None
    assert fixture['public_values'] == public_values


def test_checked_in_all_fixtures_match_public_values() -> None:
    artifact_dir = REPO_ROOT / 'compiler_verification_project' / 'artifacts'
    expected = {
        'zkp_attestation_fixture_core.json': ('core', None, None, None),
        'zkp_attestation_fixture_compressed.json': (
            'compressed',
            None,
            'compiler_verification_project/artifacts/zkp_attestation_proof_compressed.bin',
            None,
        ),
        'zkp_attestation_fixture_groth16.json': (
            'groth16',
            '0x',
            'compiler_verification_project/artifacts/zkp_attestation_proof_groth16.bin',
            'compiler_verification_project/artifacts/zkp_attestation_groth16_verifier/groth16_vk.bin',
        ),
    }
    _assert_attestation_fixtures_match_public_values(artifact_dir, expected)


def test_zkp_attestation_bundle_supports_alternate_output_dir(tmp_path: Path) -> None:
    payload = write_zkp_attestation_inputs(case_count=1, output_dir=tmp_path)
    assert json.loads((tmp_path / 'zkp_attestation_input.json').read_text()) == payload
    assert json.loads((tmp_path / 'zkp_attestation_claim.json').read_text())['schema'] == 'compiler-project-zkp-attestation-claim-v1'
    assert json.loads((tmp_path / 'zkp_attestation_family.json').read_text())['name'] == payload['selected_family_name']
    assert json.loads((tmp_path / 'zkp_attestation_cases.json').read_text())['case_count'] == payload['prepared_case_corpus']['case_count']
    assert payload['resource_certificate_document']['payload']['pass'] is True


def test_release_profile_selector_resolves_google_comparable_corpus() -> None:
    profile = resolve_proof_corpus_profile('release')
    assert profile['name'] == GOOGLE_COMPARABLE_PROFILE
    assert profile['case_count'] == GOOGLE_COMPARABLE_CASE_COUNT
    assert profile['case_start'] == 0
    assert profile['release_grade'] is True


def test_zkp_attestation_input_cli_profile_overrides_cases(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            'compiler_verification_project/scripts/build_zkp_attestation_input.py',
            '--profile',
            'release',
            '--cases',
            '2',
            '--output-dir',
            str(tmp_path),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    summary = json.loads(result.stdout)
    assert summary['profile'] == GOOGLE_COMPARABLE_PROFILE
    assert summary['profile_release_grade'] is True
    assert summary['case_count'] == 2
    assert json.loads((tmp_path / 'zkp_attestation_cases.json').read_text())['case_count'] == 2


def test_zkp_attestation_case_start_selects_late_case_ids() -> None:
    payload = build_zkp_attestation_input(case_count=1, case_start=7)
    case_corpus = payload['prepared_case_corpus']
    assert case_corpus['case_start_index'] == 7
    assert case_corpus['case_count'] == 1
    assert [case['case_id'] for case in case_corpus['cases']] == ['random_0007']
