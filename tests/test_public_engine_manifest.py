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
        selected_family_name=candidate_input['selected_family_name'],
    )
    assert observed == expected
    assert expected['schema'] == PUBLIC_ENGINE_MANIFEST_SCHEMA
    assert expected['pass'] is True
    assert expected['public_totals'] == reusable['executable_resource_engine']['public_totals']
    assert expected['fast_no_zkp_contract']['prover_required'] is False


def test_public_engine_manifest_rejects_engine_total_drift() -> None:
    reusable = _load('reusable_chunk_lowering.json')
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
        selected_family_name=candidate_input['selected_family_name'],
    )
    assert observed['checks']['public_totals_match_counted_resource_engine'] is False
    assert observed['checks']['public_totals_match_resource_contract_engine'] is False
    assert observed['pass'] is False
