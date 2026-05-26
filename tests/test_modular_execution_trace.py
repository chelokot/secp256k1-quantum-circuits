#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
COMPILER_SRC = REPO_ROOT / 'compiler_verification_project' / 'src'
if str(COMPILER_SRC) not in sys.path:
    sys.path.insert(0, str(COMPILER_SRC))

from modular_execution_trace import MODULAR_EXECUTION_TRACE_SCHEMA, build_modular_execution_trace  # noqa: E402


def _artifact(name: str) -> dict:
    return json.loads((REPO_ROOT / 'compiler_verification_project' / 'artifacts' / name).read_text())


def _build(
    *,
    tail_macro_engine: dict | None = None,
    modular_arithmetic_certificate: dict | None = None,
    public_candidate_materialized_circuit_manifest: dict | None = None,
) -> dict:
    return build_modular_execution_trace(
        tail_macro_engine=tail_macro_engine or _artifact('tail_macro_engine.json'),
        modular_arithmetic_certificate=modular_arithmetic_certificate or _artifact('modular_arithmetic_certificate.json'),
        public_candidate_materialized_circuit_manifest=public_candidate_materialized_circuit_manifest or _artifact('public_candidate_materialized_circuit_manifest.json'),
    )


def test_modular_execution_trace_reconstructs_checked_artifact() -> None:
    expected = _artifact('modular_execution_trace.json')
    observed = _build()
    assert observed == expected
    assert expected['schema'] == MODULAR_EXECUTION_TRACE_SCHEMA
    assert expected['pass'] is True
    assert expected['tail_schedule_row_count'] == 17
    assert expected['reconstructed_non_clifford'] == expected['selected_tail_kernel_non_clifford'] == 1126842
    assert expected['modular_opcode_histogram'] == {
        'field_add': 6,
        'field_mul': 11,
        'field_sub': 2,
        'field_sub_sum': 1,
        'field_triple': 1,
        'mul_const': 2,
    }
    assert expected['checks']['zero_lift_guard_is_explicit_and_counted'] is True
    assert len(expected['trace_stream_sha256']) == 64


def test_modular_execution_trace_rejects_forged_tail_cost() -> None:
    tail_macro_engine = _artifact('tail_macro_engine.json')
    tail_macro_engine['fused_output_field_operation_stream'][0]['non_clifford'] += 1
    observed = _build(tail_macro_engine=tail_macro_engine)
    assert observed['pass'] is False
    assert observed['checks']['every_tail_row_reconstructs_non_clifford'] is False
    assert observed['checks']['scheduled_tail_rows_sum_selected_tail_non_clifford'] is False


def test_modular_execution_trace_rejects_forged_public_engine_bridge() -> None:
    public_candidate = deepcopy(_artifact('public_candidate_materialized_circuit_manifest.json'))
    public_candidate['modular_arithmetic_engine_integration']['pass'] = False
    observed = _build(public_candidate_materialized_circuit_manifest=public_candidate)
    assert observed['pass'] is False
    assert observed['checks']['public_engine_modular_integration_passes'] is False
