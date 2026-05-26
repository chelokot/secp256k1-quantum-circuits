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

from modular_accumulator_capacity_certificate import MODULAR_ACCUMULATOR_CAPACITY_CERTIFICATE_SCHEMA, build_modular_accumulator_capacity_certificate  # noqa: E402


ARTIFACT_DIR = REPO_ROOT / 'compiler_verification_project' / 'artifacts'


def _load(name: str) -> dict:
    return json.loads((ARTIFACT_DIR / name).read_text())


def _build() -> dict:
    return build_modular_accumulator_capacity_certificate(
        modular_accumulator_row_stream=_load('modular_accumulator_row_stream.json'),
        field_bits=256,
    )


def test_modular_accumulator_capacity_certificate_reconstructs_checked_artifact() -> None:
    assert _load('modular_accumulator_capacity_certificate.json') == _build()


def test_modular_accumulator_capacity_certificate_blocks_free_scratch_and_product_columns() -> None:
    certificate = _load('modular_accumulator_capacity_certificate.json')
    row_stream = _load('modular_accumulator_row_stream.json')
    field_bits = certificate['field_bits']
    obligations = {
        row['owner_id']: row
        for row in certificate['owner_capacity_obligations']
    }
    assert certificate['schema'] == MODULAR_ACCUMULATOR_CAPACITY_CERTIFICATE_SCHEMA
    assert certificate['pass'] is True
    product = obligations['streamed_product_accumulator_column_space']
    fold = obligations['streamed_modular_accumulator_field_lane']
    temporary = obligations['temporary_and_target_wire']
    guard = obligations['guard_ladder_predicate_workspace']
    assert product['partial_product_column_count'] == 2 * field_bits - 1
    assert product['logical_qubit_budget_required_by_materialized_columns'] == 2 * field_bits
    assert product['field_slot_capacity_bits'] == field_bits
    assert product['fits_single_field_slot'] is False
    assert fold['logical_qubit_budget_required_by_direct_shifted_columns'] == field_bits + 31
    assert fold['overflowing_shift_column_count'] == 31
    assert fold['fits_single_field_slot_without_second_fold'] is False
    assert temporary['obligation_order_peak_logical_qubits'] == row_stream['expanded_counts']['temporary_cleanup_rows']
    assert temporary['serialized_candidate_peak_logical_qubits'] == 1
    assert guard['obligation_order_peak_logical_qubits'] == row_stream['expanded_counts']['zero_lift_guard_rows']
    assert guard['serialized_candidate_peak_logical_qubits'] == 1
    assert certificate['promotion_status']['status'] == 'capacity_certificate_not_promoted_to_public_resource_contract'
