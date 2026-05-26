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

from modular_accumulator_carry_obligations import MODULAR_ACCUMULATOR_CARRY_OBLIGATIONS_SCHEMA, build_modular_accumulator_carry_obligations  # noqa: E402


ARTIFACT_DIR = REPO_ROOT / 'compiler_verification_project' / 'artifacts'


def _load(name: str) -> dict:
    return json.loads((ARTIFACT_DIR / name).read_text())


def _build() -> dict:
    return build_modular_accumulator_carry_obligations(
        modular_accumulator_row_stream=_load('modular_accumulator_row_stream.json'),
        modular_accumulator_capacity_certificate=_load('modular_accumulator_capacity_certificate.json'),
        modular_accumulator_semantic_obligations=_load('modular_accumulator_semantic_obligations.json'),
        field_bits=256,
    )


def test_modular_accumulator_carry_obligations_reconstructs_checked_artifact() -> None:
    assert _load('modular_accumulator_carry_obligations.json') == _build()


def test_modular_accumulator_carry_obligations_reject_parity_consume() -> None:
    obligations = _load('modular_accumulator_carry_obligations.json')
    row_stream = _load('modular_accumulator_row_stream.json')
    stream = obligations['column_carry_obligation_stream']
    field_bits = obligations['field_bits']

    assert obligations['schema'] == MODULAR_ACCUMULATOR_CARRY_OBLIGATIONS_SCHEMA
    assert obligations['pass'] is True
    assert obligations['product_owner']['partial_product_column_count'] == 2 * field_bits - 1
    assert obligations['product_owner']['carry_complete_capacity_bits'] == 2 * field_bits
    assert obligations['product_owner']['fits_single_field_slot'] is False
    assert stream['column_count'] == 2 * field_bits - 1
    assert stream['total_partial_product_rows'] == row_stream['expanded_counts']['partial_product_consume_rows']
    assert stream['total_carry_obligation_rows'] > stream['total_partial_product_rows']
    assert stream['max_single_increment_carry_span_bits'] == 2 * field_bits
    assert all(row['carry_reference_passes'] is True for row in obligations['reduced_width_exhaustive_checks'])
    assert all(row['parity_only_rejected'] is True for row in obligations['reduced_width_exhaustive_checks'])
    assert sum(row['parity_only_mismatch_count'] for row in obligations['reduced_width_exhaustive_checks']) > 0
    assert obligations['promotion_status']['status'] == 'carry_obligations_not_promoted_to_public_resource_contract'
