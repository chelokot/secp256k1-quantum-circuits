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

from modular_accumulator_lowering import MODULAR_ACCUMULATOR_LOWERING_SCHEMA, build_modular_accumulator_lowering  # noqa: E402


ARTIFACT_DIR = REPO_ROOT / 'compiler_verification_project' / 'artifacts'


def _load(name: str) -> dict:
    return json.loads((ARTIFACT_DIR / name).read_text())


def _build() -> dict:
    return build_modular_accumulator_lowering(
        modular_multiplier_lifecycle=_load('modular_multiplier_lifecycle.json'),
        field_bits=256,
    )


def test_modular_accumulator_lowering_reconstructs_checked_artifact() -> None:
    assert _load('modular_accumulator_lowering.json') == _build()


def test_modular_accumulator_lowering_binds_schoolbook_and_fold_shape() -> None:
    lowering = _load('modular_accumulator_lowering.json')
    field_bits = lowering['field_bits']
    grid = lowering['single_schoolbook_grid']
    routes = lowering['pseudo_mersenne_fold_routes']
    public_routes = lowering['public_tail_route_count']
    assert lowering['schema'] == MODULAR_ACCUMULATOR_LOWERING_SCHEMA
    assert lowering['pass'] is True
    assert grid['partial_product_count'] == field_bits * field_bits
    assert grid['column_count'] == 2 * field_bits - 1
    assert grid['preview_head'][0] == {'column': 0, 'partial_products': 1}
    assert grid['preview_tail'][-1] == {'column': 2 * field_bits - 2, 'partial_products': 1}
    assert public_routes['schoolbook_grid_count'] == 11
    assert public_routes['partial_product_routes'] == public_routes['expected_partial_product_routes']
    assert public_routes['partial_product_routes'] == 11 * field_bits * field_bits
    assert routes['route_count'] == 2 * field_bits - 1
    assert routes['low_product_column_count'] == field_bits
    assert routes['high_product_column_count'] == field_bits - 1
    assert routes['overflowing_shift_column_count'] == 31
    assert lowering['pseudo_mersenne']['shift'] == 32
    assert lowering['pseudo_mersenne']['low_term'] == 977
    assert lowering['checks']['materialized_product_accumulator_shortcut_is_rejected'] is True
    assert lowering['promotion_status']['status'] == 'lowering_plan_not_promoted_to_scheduled_primitive_netlist'
