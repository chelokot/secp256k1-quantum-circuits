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

from modular_accumulator_full_adder_stream import FULL_ADDER_STREAM_UNPROMOTED_STATUS, MODULAR_ACCUMULATOR_FULL_ADDER_STREAM_SCHEMA, build_modular_accumulator_full_adder_stream  # noqa: E402


ARTIFACT_DIR = REPO_ROOT / 'compiler_verification_project' / 'artifacts'


def _load(name: str) -> dict:
    return json.loads((ARTIFACT_DIR / name).read_text())


def _build() -> dict:
    return build_modular_accumulator_full_adder_stream(
        modular_accumulator_carry_save_candidate=_load('modular_accumulator_carry_save_candidate.json'),
        modular_accumulator_full_adder_contract=_load('modular_accumulator_full_adder_contract.json'),
    )


def test_modular_accumulator_full_adder_stream_reconstructs_checked_artifact() -> None:
    assert _load('modular_accumulator_full_adder_stream.json') == _build()


def test_modular_accumulator_full_adder_stream_binds_exact_primitive_rows() -> None:
    stream = _load('modular_accumulator_full_adder_stream.json')
    contract = _load('modular_accumulator_full_adder_contract.json')
    candidate = _load('modular_accumulator_carry_save_candidate.json')

    assert stream['schema'] == MODULAR_ACCUMULATOR_FULL_ADDER_STREAM_SCHEMA
    assert stream['pass'] is True
    assert stream['full_adder_cell_count'] == contract['candidate_totals']['full_adder_cell_count']
    assert stream['primitive_counts_total'] == contract['candidate_totals']['embedded_full_adder_primitive_counts']
    assert stream['operation_count'] == stream['primitive_counts_total']['ccx'] + stream['primitive_counts_total']['cx']
    assert stream['non_clifford_count'] == stream['primitive_counts_total']['ccx']
    assert stream['retained_input_obligation_bits'] == contract['candidate_totals']['retained_input_obligation_bits']
    assert stream['output_obligation_bits'] == contract['candidate_totals']['output_obligation_bits']
    assert stream['single_grid']['layers'] == candidate['single_grid']['layers']
    assert stream['schoolbook_grid_count'] == candidate['schoolbook_grid_count']
    assert len(stream['operation_stream_sha256']) == 64
    assert stream['segment_count'] == len(stream['segments'])
    assert stream['promotion_status']['status'] == FULL_ADDER_STREAM_UNPROMOTED_STATUS
