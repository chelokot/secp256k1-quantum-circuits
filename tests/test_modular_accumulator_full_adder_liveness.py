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

from modular_accumulator_full_adder_liveness import FULL_ADDER_LIVENESS_UNPROMOTED_STATUS, MODULAR_ACCUMULATOR_FULL_ADDER_LIVENESS_SCHEMA, build_modular_accumulator_full_adder_liveness  # noqa: E402


ARTIFACT_DIR = REPO_ROOT / 'compiler_verification_project' / 'artifacts'


def _load(name: str) -> dict:
    return json.loads((ARTIFACT_DIR / name).read_text())


def _build() -> dict:
    return build_modular_accumulator_full_adder_liveness(
        modular_accumulator_carry_save_candidate=_load('modular_accumulator_carry_save_candidate.json'),
        modular_accumulator_full_adder_stream=_load('modular_accumulator_full_adder_stream.json'),
    )


def test_modular_accumulator_full_adder_liveness_reconstructs_checked_artifact() -> None:
    assert _load('modular_accumulator_full_adder_liveness.json') == _build()


def test_modular_accumulator_full_adder_liveness_counts_retained_wires() -> None:
    liveness = _load('modular_accumulator_full_adder_liveness.json')
    stream = _load('modular_accumulator_full_adder_stream.json')
    candidate = _load('modular_accumulator_carry_save_candidate.json')

    assert liveness['schema'] == MODULAR_ACCUMULATOR_FULL_ADDER_LIVENESS_SCHEMA
    assert liveness['pass'] is True
    assert liveness['operation_count'] == stream['operation_count']
    assert liveness['primitive_counts_total'] == stream['primitive_counts_total']
    assert liveness['full_adder_cell_count'] == stream['full_adder_cell_count']
    assert liveness['retained_input_observation_count'] == stream['retained_input_obligation_bits']
    assert liveness['sum_carry_output_wire_count'] == stream['output_obligation_bits']
    assert len(liveness['per_grid']) == stream['schoolbook_grid_count']
    assert liveness['forward_only']['sequential_grid_peak_live_wires'] > liveness['optimistic_consumed_lower_bound']['sequential_grid_peak_live_wires']
    assert liveness['forward_only']['all_grids_peak_live_wires'] == sum(row['forward_only_final_live_wires'] for row in liveness['per_grid'])
    assert liveness['optimistic_consumed_lower_bound']['all_grids_final_live_wires'] == candidate['schoolbook_grid_count'] * candidate['single_grid']['final_live_column_bits']
    assert liveness['promotion_status']['status'] == FULL_ADDER_LIVENESS_UNPROMOTED_STATUS
