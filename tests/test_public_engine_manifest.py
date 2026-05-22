from __future__ import annotations

import json
import sys
from pathlib import Path

from support import ensure_compiler_project_build_summary


REPO_ROOT = Path(__file__).resolve().parents[1]
COMPILER_SRC = REPO_ROOT / 'compiler_verification_project' / 'src'
if str(COMPILER_SRC) not in sys.path:
    sys.path.insert(0, str(COMPILER_SRC))

from public_engine_manifest import PUBLIC_ENGINE_MANIFEST_SCHEMA, build_public_engine_manifest  # noqa: E402


def _load(name: str) -> dict:
    ensure_compiler_project_build_summary()
    return json.loads((REPO_ROOT / 'compiler_verification_project' / 'artifacts' / name).read_text())


def test_public_engine_manifest_reconstructs_checked_artifact() -> None:
    reusable = _load('reusable_chunk_lowering.json')
    tail_candidate = _load('reusable_chunk_tail_candidate.json')
    streamed_equivalence = _load('streamed_lookup_tail_leaf_equivalence.json')
    release_preflight = _load('release_corpus_preflight.json')
    candidate_input = json.loads(
        (
            REPO_ROOT
            / 'compiler_verification_project'
            / 'artifacts'
            / 'zkp_attestation_reusable_chunk_candidate'
            / 'zkp_attestation_input.json'
        ).read_text()
    )
    expected = _load('public_engine_manifest.json')
    observed = build_public_engine_manifest(
        reusable_chunk_lowering=reusable,
        reusable_chunk_tail_candidate=tail_candidate,
        streamed_lookup_tail_leaf_equivalence=streamed_equivalence,
        release_corpus_preflight=release_preflight,
        zkp_attestation_input=candidate_input,
        selected_family_name=candidate_input['selected_family_name'],
    )
    assert observed == expected
    assert expected['schema'] == PUBLIC_ENGINE_MANIFEST_SCHEMA
    assert expected['pass'] is True
    assert expected['public_totals'] == reusable['executable_resource_engine']['public_totals']
    assert expected['fast_no_zkp_contract']['prover_required'] is False
    assert expected['semantic_boundary_evidence']['release_corpus_preflight']['case_count'] == 9024
    assert set(expected['semantic_boundary_evidence']['required_categories']).issubset(
        expected['semantic_boundary_evidence']['smoke_case_corpus']['category_counts']
    )


def test_public_engine_manifest_rejects_engine_total_drift() -> None:
    reusable = _load('reusable_chunk_lowering.json')
    tail_candidate = _load('reusable_chunk_tail_candidate.json')
    streamed_equivalence = _load('streamed_lookup_tail_leaf_equivalence.json')
    release_preflight = _load('release_corpus_preflight.json')
    candidate_input = json.loads(
        (
            REPO_ROOT
            / 'compiler_verification_project'
            / 'artifacts'
            / 'zkp_attestation_reusable_chunk_candidate'
            / 'zkp_attestation_input.json'
        ).read_text()
    )
    reusable['executable_resource_engine']['public_totals']['logical_qubits'] += 1
    observed = build_public_engine_manifest(
        reusable_chunk_lowering=reusable,
        reusable_chunk_tail_candidate=tail_candidate,
        streamed_lookup_tail_leaf_equivalence=streamed_equivalence,
        release_corpus_preflight=release_preflight,
        zkp_attestation_input=candidate_input,
        selected_family_name=candidate_input['selected_family_name'],
    )
    assert observed['checks']['public_totals_match_counted_resource_engine'] is False
    assert observed['checks']['public_totals_match_resource_contract_engine'] is False
    assert observed['pass'] is False


def test_public_engine_manifest_rejects_semantic_boundary_drift() -> None:
    reusable = _load('reusable_chunk_lowering.json')
    tail_candidate = _load('reusable_chunk_tail_candidate.json')
    streamed_equivalence = _load('streamed_lookup_tail_leaf_equivalence.json')
    release_preflight = _load('release_corpus_preflight.json')
    candidate_input = json.loads(
        (
            REPO_ROOT
            / 'compiler_verification_project'
            / 'artifacts'
            / 'zkp_attestation_reusable_chunk_candidate'
            / 'zkp_attestation_input.json'
        ).read_text()
    )
    release_preflight['category_counts']['lookup_infinity'] = 0
    observed = build_public_engine_manifest(
        reusable_chunk_lowering=reusable,
        reusable_chunk_tail_candidate=tail_candidate,
        streamed_lookup_tail_leaf_equivalence=streamed_equivalence,
        release_corpus_preflight=release_preflight,
        zkp_attestation_input=candidate_input,
        selected_family_name=candidate_input['selected_family_name'],
    )
    assert observed['checks']['release_corpus_preflight_covers_required_categories'] is False
    assert observed['pass'] is False
