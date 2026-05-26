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

from modular_multiplier_lifecycle import MODULAR_MULTIPLIER_LIFECYCLE_SCHEMA, build_modular_multiplier_lifecycle  # noqa: E402


ARTIFACT_DIR = REPO_ROOT / 'compiler_verification_project' / 'artifacts'


def _load(name: str) -> dict:
    return json.loads((ARTIFACT_DIR / name).read_text())


def _build() -> dict:
    return build_modular_multiplier_lifecycle(
        scheduled_modular_primitive_netlist=_load('scheduled_modular_primitive_netlist.json'),
        modular_primitive_wire_audit=_load('modular_primitive_wire_audit.json'),
        field_bits=256,
    )


def test_modular_multiplier_lifecycle_reconstructs_checked_artifact() -> None:
    assert _load('modular_multiplier_lifecycle.json') == _build()


def test_modular_multiplier_lifecycle_keeps_candidate_unpromoted() -> None:
    lifecycle = _load('modular_multiplier_lifecycle.json')
    current = lifecycle['current_stream']
    candidate = lifecycle['streamed_lifecycle_candidate']
    assert lifecycle['schema'] == MODULAR_MULTIPLIER_LIFECYCLE_SCHEMA
    assert lifecycle['pass'] is True
    assert current['physical_lifecycle_status'] == 'invalid_abandoned_temporary_and_targets'
    assert current['scratch_abandoned_garbage_count'] == current['scratch_observation_count']
    assert candidate['status'] == 'candidate_not_promoted_to_public_resource_contract'
    assert candidate['temporary_and_compute_events'] == current['scratch_observation_count']
    assert candidate['required_consume_events'] == current['scratch_observation_count']
    assert candidate['required_cleanup_events'] == current['scratch_observation_count']
    assert candidate['peak_temporary_and_wires_if_serialized'] == 1
    assert candidate['non_clifford_delta_unproven_until_consume_cleanup_lowering_exists'] is None
