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
from proof_corpus_profiles import GOOGLE_COMPARABLE_CASE_COUNT  # noqa: E402


def _load(name: str) -> dict:
    ensure_compiler_project_build_summary()
    return json.loads((REPO_ROOT / 'compiler_verification_project' / 'artifacts' / name).read_text())


def _candidate_input() -> dict:
    return json.loads(
        (
            REPO_ROOT
            / 'compiler_verification_project'
            / 'artifacts'
            / 'zkp_attestation_reusable_chunk_candidate'
            / 'zkp_attestation_input.json'
        ).read_text()
    )


def _build_manifest(
    *,
    reusable: dict | None = None,
    tail_candidate: dict | None = None,
    streamed_equivalence: dict | None = None,
    release_preflight: dict | None = None,
    candidate_input: dict | None = None,
    arithmetic_operation_ir: dict | None = None,
    qroam_primitive: dict | None = None,
    phase_shell: dict | None = None,
    public_candidate_materialized: dict | None = None,
) -> dict:
    resolved_candidate_input = candidate_input or _candidate_input()
    return build_public_engine_manifest(
        reusable_chunk_lowering=reusable or _load('reusable_chunk_lowering.json'),
        reusable_chunk_tail_candidate=tail_candidate or _load('reusable_chunk_tail_candidate.json'),
        streamed_lookup_tail_leaf_equivalence=streamed_equivalence or _load('streamed_lookup_tail_leaf_equivalence.json'),
        release_corpus_preflight=release_preflight or _load('release_corpus_preflight.json'),
        zkp_attestation_input=resolved_candidate_input,
        arithmetic_operation_ir=arithmetic_operation_ir or _load('arithmetic_operation_ir.json'),
        qroam_primitive_certificate=qroam_primitive or _load('qroam_primitive_certificate.json'),
        phase_shell_lowerings=phase_shell or _load('phase_shell_lowerings.json'),
        public_candidate_materialized_circuit_manifest=public_candidate_materialized or _load('public_candidate_materialized_circuit_manifest.json'),
        selected_family_name=resolved_candidate_input['selected_family_name'],
    )


def test_public_engine_manifest_reconstructs_checked_artifact() -> None:
    reusable = _load('reusable_chunk_lowering.json')
    expected = _load('public_engine_manifest.json')
    observed = _build_manifest(reusable=reusable)
    assert observed == expected
    assert expected['schema'] == PUBLIC_ENGINE_MANIFEST_SCHEMA
    assert expected['pass'] is True
    assert expected['public_totals'] == reusable['executable_resource_engine']['public_totals']
    assert expected['fast_no_zkp_contract']['prover_required'] is False
    assert expected['semantic_boundary_evidence']['release_corpus_preflight']['case_count'] == GOOGLE_COMPARABLE_CASE_COUNT
    assert set(expected['semantic_boundary_evidence']['required_categories']).issubset(
        expected['semantic_boundary_evidence']['smoke_case_corpus']['category_counts']
    )
    assert expected['primitive_operation_evidence']['qroam_primitive_certificate']['whole_oracle_non_clifford'] == reusable['non_clifford_derivation']['qroam_chunk_non_clifford']
    assert expected['primitive_operation_evidence']['phase_shell']['phase_register_bits'] == expected['primitive_operation_evidence']['phase_shell']['hadamard_count']
    assert expected['primitive_operation_evidence']['public_candidate_materialized_circuit_manifest']['non_clifford'] == reusable['non_clifford_derivation']['candidate_total_non_clifford']


def test_public_engine_manifest_rejects_engine_total_drift() -> None:
    reusable = _load('reusable_chunk_lowering.json')
    reusable['executable_resource_engine']['public_totals']['logical_qubits'] += 1
    observed = _build_manifest(reusable=reusable)
    assert observed['checks']['public_totals_match_counted_resource_engine'] is False
    assert observed['checks']['public_totals_match_resource_contract_engine'] is False
    assert observed['pass'] is False


def test_public_engine_manifest_rejects_semantic_boundary_drift() -> None:
    release_preflight = _load('release_corpus_preflight.json')
    release_preflight['category_counts']['lookup_infinity'] = 0
    observed = _build_manifest(release_preflight=release_preflight)
    assert observed['checks']['release_corpus_preflight_covers_required_categories'] is False
    assert observed['pass'] is False


def test_public_engine_manifest_rejects_qroam_primitive_drift() -> None:
    qroam_primitive = _load('qroam_primitive_certificate.json')
    qroam_primitive['traversed_counts']['per_stream_non_clifford'] += 1
    observed = _build_manifest(qroam_primitive=qroam_primitive)
    assert observed['checks']['qroam_primitive_stream_binds_stream_terms'] is False
    assert observed['pass'] is False


def test_public_engine_manifest_rejects_arithmetic_operation_drift() -> None:
    arithmetic_operation_ir = _load('arithmetic_operation_ir.json')
    arithmetic_operation_ir['leaf_arithmetic_summary']['rows'][0]['primitive_counts_total']['ccx'] += 1
    observed = _build_manifest(arithmetic_operation_ir=arithmetic_operation_ir)
    assert observed['checks']['arithmetic_operation_ir_binds_tail_opcode'] is False
    assert observed['pass'] is False


def test_public_engine_manifest_rejects_phase_shell_drift() -> None:
    phase_shell = _load('phase_shell_lowerings.json')
    for row in phase_shell['families']:
        if row['name'] == 'semiclassical_qft_v1':
            row['hadamard_count'] -= 1
    observed = _build_manifest(phase_shell=phase_shell)
    assert observed['checks']['phase_shell_primitive_counts_bind_public_family'] is False
    assert observed['pass'] is False


def test_public_engine_manifest_rejects_public_candidate_materialized_drift() -> None:
    public_candidate_materialized = _load('public_candidate_materialized_circuit_manifest.json')
    public_candidate_materialized['public_totals']['non_clifford'] -= 1
    observed = _build_manifest(public_candidate_materialized=public_candidate_materialized)
    assert observed['checks']['public_candidate_materialized_stream_binds_engine_totals'] is False
    assert observed['pass'] is False
