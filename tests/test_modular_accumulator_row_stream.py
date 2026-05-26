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

from modular_accumulator_row_stream import MODULAR_ACCUMULATOR_ROW_STREAM_SCHEMA, build_modular_accumulator_row_stream  # noqa: E402


ARTIFACT_DIR = REPO_ROOT / 'compiler_verification_project' / 'artifacts'


def _load(name: str) -> dict:
    return json.loads((ARTIFACT_DIR / name).read_text())


def _build() -> dict:
    return build_modular_accumulator_row_stream(
        modular_multiplier_lifecycle=_load('modular_multiplier_lifecycle.json'),
        modular_accumulator_lowering=_load('modular_accumulator_lowering.json'),
        field_bits=256,
    )


def test_modular_accumulator_row_stream_reconstructs_checked_artifact() -> None:
    assert _load('modular_accumulator_row_stream.json') == _build()


def test_modular_accumulator_row_stream_expands_route_obligations_without_promoting_cost() -> None:
    row_stream = _load('modular_accumulator_row_stream.json')
    counts = row_stream['expanded_counts']
    stream = row_stream['row_stream']
    role_counts = stream['role_counts']
    assert row_stream['schema'] == MODULAR_ACCUMULATOR_ROW_STREAM_SCHEMA
    assert row_stream['pass'] is True
    assert counts['schoolbook_grid_count'] == 11
    assert counts['partial_product_consume_rows'] == 11 * 256 * 256
    assert counts['pseudo_mersenne_fold_rows'] == 11 * (2 * 256 - 1)
    assert counts['temporary_cleanup_rows'] == counts['partial_product_consume_rows'] + counts['zero_lift_guard_rows']
    assert counts['total_rows'] == stream['row_count']
    assert role_counts['partial_product_accumulator_consume'] == counts['partial_product_consume_rows']
    assert role_counts['temporary_and_cleanup'] == counts['temporary_cleanup_rows']
    assert stream['max_source_column'] == 510
    assert stream['max_destination_column'] == 510
    assert row_stream['known_cost_status']['promoted_to_public_resource_contract'] is False
    assert row_stream['known_cost_status']['exact_non_clifford_delta'] is None
    assert row_stream['promotion_status']['status'] == 'row_stream_obligations_not_promoted_to_scheduled_primitive_netlist'
