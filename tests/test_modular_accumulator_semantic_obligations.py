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

from modular_accumulator_semantic_obligations import MODULAR_ACCUMULATOR_SEMANTIC_OBLIGATIONS_SCHEMA, build_modular_accumulator_semantic_obligations  # noqa: E402


ARTIFACT_DIR = REPO_ROOT / 'compiler_verification_project' / 'artifacts'


def _load(name: str) -> dict:
    return json.loads((ARTIFACT_DIR / name).read_text())


def _build() -> dict:
    return build_modular_accumulator_semantic_obligations(
        modular_accumulator_row_stream=_load('modular_accumulator_row_stream.json'),
        modular_accumulator_capacity_certificate=_load('modular_accumulator_capacity_certificate.json'),
        modular_accumulator_scratch_schedule=_load('modular_accumulator_scratch_schedule.json'),
        field_bits=256,
    )


def test_modular_accumulator_semantic_obligations_reconstructs_checked_artifact() -> None:
    assert _load('modular_accumulator_semantic_obligations.json') == _build()


def test_modular_accumulator_semantic_obligations_cover_schedule_without_promotion() -> None:
    obligations = _load('modular_accumulator_semantic_obligations.json')
    row_stream = _load('modular_accumulator_row_stream.json')
    scratch_schedule = _load('modular_accumulator_scratch_schedule.json')
    classes = {row['name']: row for row in obligations['obligation_classes']}
    summary = obligations['obligation_summary']
    field_bits = obligations['field_bits']

    assert obligations['schema'] == MODULAR_ACCUMULATOR_SEMANTIC_OBLIGATIONS_SCHEMA
    assert obligations['pass'] is True
    assert summary['row_stream_row_count'] == row_stream['row_stream']['row_count']
    assert summary['consume_event_count'] == scratch_schedule['schedule_stream']['phase_counts']['consume_into_counted_owner']
    assert summary['cleanup_event_count'] == scratch_schedule['schedule_stream']['phase_counts']['cleanup_or_measure_uncompute']
    assert summary['partial_product_consume_rows'] == 11 * field_bits * field_bits
    assert summary['zero_lift_guard_consume_rows'] == 2 * (field_bits - 1)
    assert summary['pseudo_mersenne_fold_rows'] == row_stream['expanded_counts']['pseudo_mersenne_fold_rows']
    assert summary['temporary_cleanup_rows'] == row_stream['expanded_counts']['temporary_cleanup_rows']
    assert classes['partial_product_column_consume']['required_logical_qubit_capacity'] == 2 * field_bits - 1
    assert classes['partial_product_column_consume']['single_field_slot_shortcut_allowed'] is False
    assert classes['pseudo_mersenne_high_column_fold']['overflowing_shift_column_count'] == 31
    assert classes['temporary_cleanup_uncompute']['serialized_candidate_peak_logical_qubits'] == 1
    assert summary['semantic_gate_lowering_proven'] is False
    assert all(row['semantic_gate_lowering_proven'] is False for row in obligations['obligation_classes'])
    assert obligations['promotion_status']['status'] == 'semantic_obligations_not_promoted_to_public_resource_contract'
