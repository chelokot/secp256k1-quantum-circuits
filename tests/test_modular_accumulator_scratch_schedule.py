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

from modular_accumulator_scratch_schedule import MODULAR_ACCUMULATOR_SCRATCH_SCHEDULE_SCHEMA, build_modular_accumulator_scratch_schedule  # noqa: E402


ARTIFACT_DIR = REPO_ROOT / 'compiler_verification_project' / 'artifacts'


def _load(name: str) -> dict:
    return json.loads((ARTIFACT_DIR / name).read_text())


def _build() -> dict:
    return build_modular_accumulator_scratch_schedule(
        modular_multiplier_lifecycle=_load('modular_multiplier_lifecycle.json'),
        modular_accumulator_capacity_certificate=_load('modular_accumulator_capacity_certificate.json'),
        field_bits=256,
    )


def test_modular_accumulator_scratch_schedule_reconstructs_checked_artifact() -> None:
    assert _load('modular_accumulator_scratch_schedule.json') == _build()


def test_modular_accumulator_scratch_schedule_proves_adjacent_triplet_liveness_only() -> None:
    schedule = _load('modular_accumulator_scratch_schedule.json')
    stream = schedule['schedule_stream']
    lifecycle = _load('modular_multiplier_lifecycle.json')
    triplets = lifecycle['candidate_lifecycle_stream']['temporary_and_compute_events']
    assert schedule['schema'] == MODULAR_ACCUMULATOR_SCRATCH_SCHEDULE_SCHEMA
    assert schedule['pass'] is True
    assert schedule['triplet_count'] == triplets
    assert stream['event_count'] == 3 * triplets
    assert stream['phase_counts'] == {
        'cleanup_or_measure_uncompute': triplets,
        'consume_into_counted_owner': triplets,
        'temporary_and_compute': triplets,
    }
    assert stream['peak_temporary_live_qubits'] == 1
    assert schedule['liveness_certificate']['obligation_order_temporary_peak_qubits'] == triplets
    assert schedule['liveness_certificate']['serialized_schedule_temporary_peak_qubits'] == 1
    assert schedule['liveness_certificate']['semantic_gate_lowering_proven'] is False
    assert schedule['promotion_status']['status'] == 'scratch_schedule_not_promoted_to_public_resource_contract'
