from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / 'compiler_verification_project' / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from constant_provenance import CONSTANT_PROVENANCE_SCHEMA, build_constant_provenance  # noqa: E402


ARTIFACTS = REPO_ROOT / 'compiler_verification_project' / 'artifacts'


def _load(relative: str) -> dict:
    return json.loads((ARTIFACTS / relative).read_text())


def test_constant_provenance_matches_generator_and_passes() -> None:
    actual = _load('constant_provenance.json')
    expected = build_constant_provenance(
        repo_root=REPO_ROOT,
        compiler_parameters=_load('compiler_parameters.json'),
        phase_shell_lowerings=_load('phase_shell_lowerings.json'),
        reusable_chunk_lowering=_load('reusable_chunk_lowering.json'),
        zkp_attestation_input=_load('zkp_attestation_reusable_chunk_candidate/zkp_attestation_input.json'),
        public_headline_result=_load('public_headline_result.json'),
        headline_resource_manifest=_load('headline_resource_manifest.json'),
    )
    assert actual == expected
    assert actual['schema'] == CONSTANT_PROVENANCE_SCHEMA
    assert actual['pass'] is True


def test_constant_provenance_binds_phase_shell_counts_to_zkp_family() -> None:
    provenance = _load('constant_provenance.json')
    row_by_name = {row['name']: row for row in provenance['source_rows']}
    for name in (
        'semiclassical_phase_shell_hadamards',
        'semiclassical_phase_shell_measurements',
        'semiclassical_phase_shell_rotations',
        'semiclassical_phase_shell_rotation_depth',
        'semiclassical_total_measurements',
    ):
        row = row_by_name[name]
        assert row['source_artifact'] == 'compiler_verification_project/artifacts/phase_shell_lowerings.json'
        assert row['pass'] is True
        assert row['consumers'][0]['artifact'] == 'compiler_verification_project/artifacts/zkp_attestation_reusable_chunk_candidate/zkp_attestation_input.json'
        assert row['consumers'][0]['observed'] == row['value']


def test_constant_provenance_rejects_historic_hardcoded_zkp_literals() -> None:
    provenance = _load('constant_provenance.json')
    assert provenance['checks']['forbidden_historic_literals_absent'] is True
    assert provenance['checks']['tracked_zkp_family_resource_fields_are_not_integer_literals'] is True
    assert all(row['match_count'] == 0 for row in provenance['forbidden_literal_scan'])
    assert all(not row['integer_literals'] for row in provenance['ast_literal_audits'])
