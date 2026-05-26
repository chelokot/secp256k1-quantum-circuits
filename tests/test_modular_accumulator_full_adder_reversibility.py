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

from modular_accumulator_full_adder_reversibility import FULL_ADDER_REVERSIBILITY_UNPROMOTED_STATUS, MODULAR_ACCUMULATOR_FULL_ADDER_REVERSIBILITY_SCHEMA, build_modular_accumulator_full_adder_reversibility  # noqa: E402


ARTIFACT_DIR = REPO_ROOT / 'compiler_verification_project' / 'artifacts'


def _load(name: str) -> dict:
    return json.loads((ARTIFACT_DIR / name).read_text())


def _build() -> dict:
    return build_modular_accumulator_full_adder_reversibility(
        modular_accumulator_full_adder_liveness=_load('modular_accumulator_full_adder_liveness.json'),
    )


def test_modular_accumulator_full_adder_reversibility_reconstructs_checked_artifact() -> None:
    assert _load('modular_accumulator_full_adder_reversibility.json') == _build()


def test_modular_accumulator_full_adder_reversibility_rejects_one_bit_witness() -> None:
    reversibility = _load('modular_accumulator_full_adder_reversibility.json')
    liveness = _load('modular_accumulator_full_adder_liveness.json')

    assert reversibility['schema'] == MODULAR_ACCUMULATOR_FULL_ADDER_REVERSIBILITY_SCHEMA
    assert reversibility['pass'] is True
    assert reversibility['max_preimage_size'] == 3
    assert reversibility['minimum_witness_bits_per_cell'] == 2
    assert reversibility['minimum_witness_bits_total'] == 2 * liveness['full_adder_cell_count']
    assert reversibility['one_bit_witness_exhaustive_search']['candidate_function_count'] == 256
    assert reversibility['one_bit_witness_exhaustive_search']['collision_free_function_count'] == 0
    assert all(len(set(tags)) == len(reversibility['output_classes'][key]) for key, tags in reversibility['two_bit_witness_assignment'].items())
    assert reversibility['promotion_status']['status'] == FULL_ADDER_REVERSIBILITY_UNPROMOTED_STATUS
