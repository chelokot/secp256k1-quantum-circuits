from __future__ import annotations

import json
import sys
from pathlib import Path

from support import ensure_compiler_project_build_summary


REPO_ROOT = Path(__file__).resolve().parents[1]
COMPILER_SRC = REPO_ROOT / 'compiler_verification_project' / 'src'
if str(COMPILER_SRC) not in sys.path:
    sys.path.insert(0, str(COMPILER_SRC))

from engine_completion_audit import ENGINE_COMPLETION_AUDIT_SCHEMA, build_engine_completion_audit  # noqa: E402
from public_engine_contract import CANONICAL_MATERIALIZED_FLAT_NETLIST, PUBLIC_ENGINE_CANONICAL_TOTALS_SOURCE, PUBLIC_TOTALS_DERIVE_FROM_CANONICAL_CHECK  # noqa: E402


def _load(name: str) -> dict:
    ensure_compiler_project_build_summary()
    return json.loads((REPO_ROOT / 'compiler_verification_project' / 'artifacts' / name).read_text())


def _build_audit(
    *,
    public_engine: dict | None = None,
    public_candidate: dict | None = None,
    arithmetic_ir: dict | None = None,
    qroam_primitive: dict | None = None,
    lookup_lowerings: dict | None = None,
) -> dict:
    return build_engine_completion_audit(
        public_engine_manifest=public_engine or _load('public_engine_manifest.json'),
        public_candidate_materialized_circuit_manifest=public_candidate or _load('public_candidate_materialized_circuit_manifest.json'),
        reusable_chunk_lowering=_load('reusable_chunk_lowering.json'),
        arithmetic_operation_ir=arithmetic_ir or _load('arithmetic_operation_ir.json'),
        lookup_lowerings=lookup_lowerings or _load('lookup_lowerings.json'),
        qroam_primitive_certificate=qroam_primitive or _load('qroam_primitive_certificate.json'),
        phase_shell_lowerings=_load('phase_shell_lowerings.json'),
        release_corpus_preflight=_load('release_corpus_preflight.json'),
        streamed_lookup_tail_leaf_equivalence=_load('streamed_lookup_tail_leaf_equivalence.json'),
        modular_arithmetic_certificate=_load('modular_arithmetic_certificate.json'),
        tail_macro_engine=_load('tail_macro_engine.json'),
        tail_macro_liveness=_load('tail_macro_liveness.json'),
        tail_macro_reversibility=_load('tail_macro_reversibility.json'),
        tail_macro_schedule_search=_load('tail_macro_schedule_search.json'),
        compiler_parameters=_load('compiler_parameters.json'),
    )


def test_engine_completion_audit_reconstructs_checked_artifact() -> None:
    expected = _load('engine_completion_audit.json')
    observed = _build_audit()
    materialized = _load('public_candidate_materialized_circuit_manifest.json')[CANONICAL_MATERIALIZED_FLAT_NETLIST]
    assert observed == expected
    assert expected['schema'] == ENGINE_COMPLETION_AUDIT_SCHEMA
    assert expected['pass'] is True
    assert expected['clifford_complete_goal_achieved'] is False
    assert expected['public_totals']['source'] == PUBLIC_ENGINE_CANONICAL_TOTALS_SOURCE
    assert expected['public_totals']['non_clifford'] == materialized['non_clifford_count']
    assert expected['public_totals']['logical_qubits'] == materialized['peak_live_qubits']
    assert expected['public_totals']['operation_count'] == materialized['operation_count']
    assert len(expected['remaining_macro_boundaries']) > 0
    assert all(expected['checks'].values())


def test_engine_completion_audit_rejects_public_total_drift() -> None:
    public_engine = _load('public_engine_manifest.json')
    public_engine['public_totals']['non_clifford'] -= 1
    observed = _build_audit(public_engine=public_engine)
    assert observed['checks'][PUBLIC_TOTALS_DERIVE_FROM_CANONICAL_CHECK] is False
    assert observed['pass'] is False


def test_engine_completion_audit_rejects_forged_source_binding() -> None:
    public_candidate = _load('public_candidate_materialized_circuit_manifest.json')
    public_candidate['operand_source_binding']['rows_by_source_kind']['lookup_lowering_block'] = 0
    observed = _build_audit(public_candidate=public_candidate)
    assert observed['checks']['source_binding_covers_every_run_length_row'] is False
    assert observed['pass'] is False


def test_engine_completion_audit_rejects_forged_qroam_cost() -> None:
    qroam_primitive = _load('qroam_primitive_certificate.json')
    qroam_primitive['qroamclean_cost_model']['per_stream_non_clifford'] -= 1
    observed = _build_audit(qroam_primitive=qroam_primitive)
    assert observed['checks']['qroam_rows_bind_standard_qroam_primitive_costs'] is False
    assert observed['pass'] is False


def test_engine_completion_audit_rejects_lookup_block_stream_drift() -> None:
    lookup_lowerings = _load('lookup_lowerings.json')
    block = lookup_lowerings['families'][0]['stages'][0]['blocks'][0]
    block['primitive_operation_stream']['operation_count'] += 1
    observed = _build_audit(lookup_lowerings=lookup_lowerings)
    assert observed['checks']['lookup_rows_are_per_block_source_bound'] is False
    assert observed['pass'] is False


def test_engine_completion_audit_rejects_false_completion_claim() -> None:
    audit = _load('engine_completion_audit.json')
    assert audit['clifford_complete_goal_achieved'] is False
    assert audit['checks']['public_claim_not_marked_full_clifford_complete_until_macro_boundaries_flattened'] is True
