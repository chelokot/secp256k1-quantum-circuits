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

from modular_accumulator_carry_save_candidate import MODULAR_ACCUMULATOR_CARRY_SAVE_CANDIDATE_SCHEMA, build_modular_accumulator_carry_save_candidate  # noqa: E402


ARTIFACT_DIR = REPO_ROOT / 'compiler_verification_project' / 'artifacts'


def _load(name: str) -> dict:
    return json.loads((ARTIFACT_DIR / name).read_text())


def _build() -> dict:
    return build_modular_accumulator_carry_save_candidate(
        modular_accumulator_row_stream=_load('modular_accumulator_row_stream.json'),
        modular_accumulator_carry_obligations=_load('modular_accumulator_carry_obligations.json'),
        field_bits=256,
    )


def test_modular_accumulator_carry_save_candidate_reconstructs_checked_artifact() -> None:
    assert _load('modular_accumulator_carry_save_candidate.json') == _build()


def test_modular_accumulator_carry_save_candidate_replays_reduced_width_products() -> None:
    candidate = _load('modular_accumulator_carry_save_candidate.json')
    field_bits = candidate['field_bits']
    single_grid = candidate['single_grid']
    all_grids = candidate['all_grids']

    assert candidate['schema'] == MODULAR_ACCUMULATOR_CARRY_SAVE_CANDIDATE_SCHEMA
    assert candidate['pass'] is True
    assert single_grid['input_column_count'] == 2 * field_bits - 1
    assert single_grid['initial_partial_product_bits'] == field_bits * field_bits
    assert single_grid['final_max_column_height'] <= 2
    assert single_grid['final_carry_propagate_bits'] == 2 * field_bits
    assert all_grids['carry_save_full_adder_count'] == candidate['schoolbook_grid_count'] * single_grid['full_adder_count']
    assert all_grids['final_carry_propagate_bits'] == candidate['schoolbook_grid_count'] * 2 * field_bits
    assert all_grids['candidate_touch_count'] < all_grids['naive_carry_obligation_rows']
    assert all(row['pass'] is True for row in candidate['reduced_width_exhaustive_checks'])
    assert candidate['promotion_status']['status'] == 'carry_save_candidate_not_promoted_to_public_resource_contract'
