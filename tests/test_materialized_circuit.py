from __future__ import annotations

import itertools
import json
import subprocess
import sys
from pathlib import Path

from support import ensure_compiler_project_build_summary


REPO_ROOT = Path(__file__).resolve().parents[1]
COMPILER_SRC = REPO_ROOT / 'compiler_verification_project' / 'src'
if str(COMPILER_SRC) not in sys.path:
    sys.path.insert(0, str(COMPILER_SRC))

from materialized_circuit import MATERIALIZED_CIRCUIT_MANIFEST_SCHEMA, PUBLIC_CANDIDATE_MATERIALIZED_CIRCUIT_MANIFEST_SCHEMA, build_public_candidate_materialized_circuit_manifest, iter_family_operation_stream, resolve_selected_family_names  # noqa: E402


def _frontier() -> dict:
    ensure_compiler_project_build_summary()
    return json.loads((REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'family_frontier.json').read_text())


def _artifact(name: str) -> dict:
    ensure_compiler_project_build_summary()
    return json.loads((REPO_ROOT / 'compiler_verification_project' / 'artifacts' / name).read_text())


def _candidate_input() -> dict:
    ensure_compiler_project_build_summary()
    return json.loads((
        REPO_ROOT
        / 'compiler_verification_project'
        / 'artifacts'
        / 'zkp_attestation_reusable_chunk_candidate'
        / 'zkp_attestation_input.json'
    ).read_text())


def test_materialized_family_aliases_resolve_to_frontier_rows() -> None:
    frontier = _frontier()
    resolved = resolve_selected_family_names(['best-gate', 'best-qubit'], frontier=frontier)
    expected = []
    for family in (frontier['best_gate_family']['name'], frontier['best_qubit_family']['name']):
        if family not in expected:
            expected.append(family)
    assert resolved == expected


def test_materialized_operation_stream_emits_seed_lookup_rows() -> None:
    frontier = _frontier()
    family_name = frontier['best_gate_family']['name']
    preview = list(itertools.islice(iter_family_operation_stream(family_name, frontier=frontier), 16))
    assert preview
    assert all(row['family'] == family_name for row in preview)
    assert all(row['scope'] == 'direct_seed' for row in preview[:8])
    assert all(row['gate'] in {'ccx', 'measurement'} for row in preview)


def test_checked_materialized_manifest_reconstructs_best_qubit_headline() -> None:
    frontier = _frontier()
    family = frontier['best_qubit_family']
    manifest = json.loads(
        (
            REPO_ROOT
            / 'compiler_verification_project'
            / 'artifacts'
            / 'materialized_circuit_manifest.json'
        ).read_text()
    )
    assert manifest['schema'] == MATERIALIZED_CIRCUIT_MANIFEST_SCHEMA
    assert manifest['family'] == family['name']
    assert manifest['gate_totals']['ccx'] == family['full_oracle_non_clifford']
    assert manifest['gate_totals']['measurement'] == family['total_measurements']
    assert all(manifest['reconstruction_checks'].values())
    assert len(manifest['operation_stream_sha256']) == 64
    assert manifest['segment_count'] == len(manifest['segments'])
    assert sum(segment['operation_count'] for segment in manifest['segments']) == manifest['operation_count']
    assert len(manifest['segment_merkle_root_sha256']) == 64


def test_public_candidate_materialized_manifest_reconstructs_current_headline() -> None:
    manifest = _artifact('public_candidate_materialized_circuit_manifest.json')
    reusable = _artifact('reusable_chunk_lowering.json')
    assert manifest['schema'] == PUBLIC_CANDIDATE_MATERIALIZED_CIRCUIT_MANIFEST_SCHEMA
    assert manifest['selected_family_name'] == _candidate_input()['selected_family_name']
    assert manifest['pass'] is True
    assert manifest['public_totals']['non_clifford'] == reusable['non_clifford_derivation']['candidate_total_non_clifford']
    assert manifest['public_totals']['logical_qubits'] == reusable['qubit_derivation']['candidate_total_logical_qubits']
    assert manifest['liveness_binding_row_count'] == manifest['run_length_row_count']
    assert manifest['materialized_liveness']['peak_live_qubits'] == reusable['qubit_derivation']['candidate_total_logical_qubits']
    assert manifest['base_row_count'] == reusable['stream_plan']['leaf_call_count_total'] + 1
    assert manifest['qroam_expansion']['stream_instances'] == reusable['stream_plan']['whole_oracle_chunk_streams']
    assert manifest['qroam_expansion']['non_clifford'] == reusable['non_clifford_derivation']['qroam_chunk_non_clifford']
    assert manifest['qroam_segment_row_count'] == manifest['qroam_expansion']['stream_instances'] * manifest['qroam_expansion']['segments_per_stream']
    assert manifest['checks']['qroam_liveness_bindings_use_matching_chunk_target'] is True


def test_public_candidate_materialized_manifest_rejects_qroam_segment_drift() -> None:
    qroam = _artifact('qroam_primitive_certificate.json')
    qroam['operation_stream']['segments'][0]['ccx'] -= 1
    candidate_input = _candidate_input()
    observed = build_public_candidate_materialized_circuit_manifest(
        reusable_chunk_lowering=_artifact('reusable_chunk_lowering.json'),
        arithmetic_operation_ir=_artifact('arithmetic_operation_ir.json'),
        qroam_primitive_certificate=qroam,
        phase_shell_lowerings=_artifact('phase_shell_lowerings.json'),
        zkp_attestation_input=candidate_input,
        selected_family_name=candidate_input['selected_family_name'],
    )
    assert observed['checks']['non_clifford_total_matches_public_candidate'] is False
    assert observed['checks']['qroam_rows_sum_to_public_qroam_derivation'] is False
    assert observed['pass'] is False


def test_materialized_circuit_script_lists_available_families() -> None:
    output = subprocess.check_output(
        [sys.executable, 'compiler_verification_project/scripts/materialize_exact_circuits.py', '--list-families'],
        cwd=REPO_ROOT,
        text=True,
    )
    payload = json.loads(output)
    assert payload['best_gate_family']
    assert payload['best_qubit_family']
    frontier = _frontier()
    expected_family_count = (
        len(frontier['lookup_families'])
        * len(frontier['phase_shell_families'])
        * len(frontier['slot_allocation_families'])
    )
    assert len(payload['available_families']) == expected_family_count
