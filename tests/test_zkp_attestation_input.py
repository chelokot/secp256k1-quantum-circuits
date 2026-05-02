from __future__ import annotations

import json
import sys
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
from zkp_attestation import DIGEST_SCHEME, build_zkp_attestation_input, write_zkp_attestation_inputs  # noqa: E402


def test_zkp_attestation_input_reconstructs_public_claim() -> None:
    payload = build_zkp_attestation_input()
    claim = payload['claim_summary']
    family = payload['family_summary']
    non_clifford = claim['non_clifford_formula']
    qubits = claim['logical_qubit_formula']
    assert non_clifford['reconstructed_total'] == family['full_oracle_non_clifford']
    assert claim['expected_full_oracle_non_clifford'] == family['full_oracle_non_clifford']
    assert qubits['reconstructed_total'] == family['total_logical_qubits']
    assert claim['expected_total_logical_qubits'] == family['total_logical_qubits']
    assert family['name'].endswith('__streamed_lookup_tail_leaf_v1__semiclassical_qft_v1')
    assert family['full_oracle_non_clifford'] == 23_953_656
    assert family['total_logical_qubits'] == 5_652


def test_zkp_attestation_cases_match_leaf_and_group_law() -> None:
    payload = build_zkp_attestation_input(case_count=8)
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
    payload = build_zkp_attestation_input()
    artifact_dir = REPO_ROOT / 'compiler_verification_project' / 'artifacts'
    public_values = json.loads((artifact_dir / 'zkp_attestation_public_values.json').read_text())
    fixture = json.loads((artifact_dir / 'zkp_attestation_fixture_core.json').read_text())
    assert public_values['schema'] == 'compiler-project-zkp-attestation-public-v2'
    assert public_values['document_digest_scheme'] == DIGEST_SCHEME
    assert public_values['selected_family_name'] == payload['selected_family_name']
    assert public_values['claim_sha256'] == payload['claim_sha256']
    assert public_values['leaf_sha256'] == payload['leaf_sha256']
    assert public_values['family_sha256'] == payload['family_sha256']
    assert public_values['case_corpus_sha256'] == payload['case_corpus_sha256']
    assert public_values['case_count'] == payload['prepared_case_corpus']['case_count']
    assert public_values['passed_case_count'] == public_values['case_count']
    assert fixture['proof_system'] == 'core'
    assert fixture['proof'] is None
    assert fixture['public_values'] == public_values


def test_checked_in_all_fixtures_match_public_values() -> None:
    artifact_dir = REPO_ROOT / 'compiler_verification_project' / 'artifacts'
    public_values = json.loads((artifact_dir / 'zkp_attestation_public_values.json').read_text())
    expected = {
        'zkp_attestation_fixture_core.json': ('core', None),
        'zkp_attestation_fixture_compressed.json': ('compressed', None),
        'zkp_attestation_fixture_groth16.json': ('groth16', '0x'),
    }
    verification_key = None
    for fixture_name, (proof_system, proof_prefix) in expected.items():
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


def test_zkp_attestation_bundle_supports_alternate_output_dir(tmp_path: Path) -> None:
    payload = write_zkp_attestation_inputs(case_count=1, output_dir=tmp_path)
    assert json.loads((tmp_path / 'zkp_attestation_input.json').read_text()) == payload
    assert json.loads((tmp_path / 'zkp_attestation_claim.json').read_text())['schema'] == 'compiler-project-zkp-attestation-claim-v1'
    assert json.loads((tmp_path / 'zkp_attestation_family.json').read_text())['name'] == payload['selected_family_name']
    assert json.loads((tmp_path / 'zkp_attestation_cases.json').read_text())['case_count'] == payload['prepared_case_corpus']['case_count']


def test_zkp_attestation_case_start_selects_late_case_ids() -> None:
    payload = build_zkp_attestation_input(case_count=1, case_start=7)
    case_corpus = payload['prepared_case_corpus']
    assert case_corpus['case_start_index'] == 7
    assert case_corpus['case_count'] == 1
    assert [case['case_id'] for case in case_corpus['cases']] == ['random_0007']
