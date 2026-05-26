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

from modular_accumulator_source_uncompute import (  # noqa: E402
    MODULAR_ACCUMULATOR_SOURCE_UNCOMPUTE_SCHEMA,
    ROUTE_PARTIAL_PRODUCT,
    ROUTE_ZERO_LIFT_GUARD,
    SOURCE_UNCOMPUTE_UNPROMOTED_STATUS,
    STATUS_MISSING_SOURCE_CONTROLS,
    STATUS_SOURCE_UNCOMPUTE_PROVEN,
    build_modular_accumulator_source_uncompute,
)


ARTIFACT_DIR = REPO_ROOT / 'compiler_verification_project' / 'artifacts'


def _load(name: str) -> dict:
    return json.loads((ARTIFACT_DIR / name).read_text())


def _build() -> dict:
    return build_modular_accumulator_source_uncompute(
        modular_execution_trace=_load('modular_execution_trace.json'),
        modular_arithmetic_certificate=_load('modular_arithmetic_certificate.json'),
        arithmetic_lowerings=_load('arithmetic_lowerings.json'),
        reusable_chunk_lowering=_load('reusable_chunk_lowering.json'),
        scheduled_modular_primitive_netlist=_load('scheduled_modular_primitive_netlist.json'),
        modular_multiplier_lifecycle=_load('modular_multiplier_lifecycle.json'),
        field_bits=256,
    )


def test_modular_accumulator_source_uncompute_reconstructs_checked_artifact() -> None:
    assert _load('modular_accumulator_source_uncompute.json') == _build()


def test_modular_accumulator_source_uncompute_splits_proven_cleanup_from_guard_gap() -> None:
    source_uncompute = _load('modular_accumulator_source_uncompute.json')
    lifecycle = _load('modular_multiplier_lifecycle.json')['current_stream']
    route_counts = source_uncompute['source_uncompute_stream']['route_kind_counts']
    cleanup_counts = source_uncompute['source_uncompute_stream']['cleanup_status_counts']

    assert source_uncompute['schema'] == MODULAR_ACCUMULATOR_SOURCE_UNCOMPUTE_SCHEMA
    assert source_uncompute['pass'] is True
    assert source_uncompute['promotion_status']['status'] == SOURCE_UNCOMPUTE_UNPROMOTED_STATUS
    assert route_counts[ROUTE_PARTIAL_PRODUCT] == lifecycle['partial_product_scratch_observation_count']
    assert cleanup_counts[STATUS_SOURCE_UNCOMPUTE_PROVEN] == lifecycle['partial_product_scratch_observation_count']
    assert source_uncompute['cleanup_cost_bounds']['partial_product_cleanup_ccx_delta_exact'] == lifecycle['partial_product_scratch_observation_count']
    assert source_uncompute['cleanup_cost_bounds']['additional_witness_bits_for_partial_product_cleanup'] == 0
    assert route_counts[ROUTE_ZERO_LIFT_GUARD] == lifecycle['non_partial_product_scratch_observation_count']
    assert cleanup_counts[STATUS_MISSING_SOURCE_CONTROLS] == lifecycle['non_partial_product_scratch_observation_count']
    assert source_uncompute['truth_table']['pass'] is True
