from __future__ import annotations

import copy
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
COMPILER_SRC = REPO_ROOT / 'compiler_verification_project' / 'src'
if str(COMPILER_SRC) not in sys.path:
    sys.path.insert(0, str(COMPILER_SRC))

from headline_resource_manifest import HEADLINE_RESOURCE_MANIFEST_SCHEMA, build_headline_resource_manifest  # noqa: E402


def _lowering() -> dict:
    return json.loads((REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'reusable_chunk_lowering.json').read_text())


def _selected_family_name() -> str:
    payload = json.loads(
        (
            REPO_ROOT
            / 'compiler_verification_project'
            / 'artifacts'
            / 'zkp_attestation_reusable_chunk_candidate'
            / 'zkp_attestation_input.json'
        ).read_text()
    )
    return payload['selected_family_name']


def test_headline_resource_manifest_reconstructs_checked_artifact() -> None:
    expected = json.loads((REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'headline_resource_manifest.json').read_text())
    observed = build_headline_resource_manifest(
        reusable_chunk_lowering=_lowering(),
        selected_family_name=_selected_family_name(),
    )
    assert observed == expected
    assert observed['schema'] == HEADLINE_RESOURCE_MANIFEST_SCHEMA
    assert observed['pass'] is True
    assert observed['public_totals'] == {
        'non_clifford': _lowering()['non_clifford_derivation']['candidate_total_non_clifford'],
        'logical_qubits': _lowering()['qubit_derivation']['candidate_total_logical_qubits'],
    }


def test_headline_resource_manifest_rejects_term_total_drift() -> None:
    lowering = copy.deepcopy(_lowering())
    lowering['counted_resource_ir']['non_clifford_terms'][1]['per_instance_non_clifford'] -= 1
    manifest = build_headline_resource_manifest(
        reusable_chunk_lowering=lowering,
        selected_family_name=_selected_family_name(),
    )
    assert manifest['pass'] is False
    assert manifest['checks']['term_rows_sum_to_public_total'] is False
