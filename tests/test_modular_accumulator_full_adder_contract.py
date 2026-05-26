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

from modular_accumulator_full_adder_contract import FULL_ADDER_CONTRACT_UNPROMOTED_STATUS, FULL_ADDER_PRIMITIVE_COUNTS_PER_CELL, MODULAR_ACCUMULATOR_FULL_ADDER_CONTRACT_SCHEMA, build_modular_accumulator_full_adder_contract  # noqa: E402


ARTIFACT_DIR = REPO_ROOT / 'compiler_verification_project' / 'artifacts'


def _load(name: str) -> dict:
    return json.loads((ARTIFACT_DIR / name).read_text())


def _build() -> dict:
    return build_modular_accumulator_full_adder_contract(
        modular_accumulator_carry_save_candidate=_load('modular_accumulator_carry_save_candidate.json'),
    )


def test_modular_accumulator_full_adder_contract_reconstructs_checked_artifact() -> None:
    assert _load('modular_accumulator_full_adder_contract.json') == _build()


def test_modular_accumulator_full_adder_contract_keeps_reversibility_obligations_explicit() -> None:
    contract = _load('modular_accumulator_full_adder_contract.json')
    candidate = _load('modular_accumulator_carry_save_candidate.json')
    cell = contract['cell_contract']
    totals = contract['candidate_totals']

    assert contract['schema'] == MODULAR_ACCUMULATOR_FULL_ADDER_CONTRACT_SCHEMA
    assert contract['pass'] is True
    assert len(cell['truth_table']) == 8
    assert all(row['passes'] is True for row in cell['truth_table'])
    assert all(row['inputs_retained'] is True for row in cell['truth_table'])
    assert cell['primitive_counts_per_cell'] == FULL_ADDER_PRIMITIVE_COUNTS_PER_CELL
    assert cell['irreversible_three_to_two_collision_count'] > 0
    assert totals['full_adder_cell_count'] == candidate['all_grids']['carry_save_full_adder_count']
    assert totals['embedded_full_adder_primitive_counts']['ccx'] == 3 * totals['full_adder_cell_count']
    assert totals['embedded_full_adder_primitive_counts']['cx'] == 3 * totals['full_adder_cell_count']
    assert totals['retained_input_obligation_bits'] == 3 * totals['full_adder_cell_count']
    assert totals['output_obligation_bits'] == 2 * totals['full_adder_cell_count']
    assert contract['promotion_status']['status'] == FULL_ADDER_CONTRACT_UNPROMOTED_STATUS
