from __future__ import annotations

import copy
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
COMPILER_SRC = REPO_ROOT / 'compiler_verification_project' / 'src'
if str(COMPILER_SRC) not in sys.path:
    sys.path.insert(0, str(COMPILER_SRC))

from resource_ir_engine import RESOURCE_IR_ENGINE_SCHEMA, evaluate_counted_resource_ir  # noqa: E402


def _counted_resource_ir() -> dict:
    lowering = json.loads(
        (REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'reusable_chunk_lowering.json').read_text()
    )
    return lowering['counted_resource_ir']


def test_resource_ir_engine_recomputes_checked_reusable_chunk_ir() -> None:
    counted_ir = _counted_resource_ir()
    report = evaluate_counted_resource_ir(counted_ir)
    assert report['schema'] == RESOURCE_IR_ENGINE_SCHEMA
    assert report['pass'] is True
    assert report['non_clifford_total_from_terms'] == counted_ir['recomputed_total_non_clifford']
    assert report['peak_live_qubits_from_intervals'] == counted_ir['recomputed_peak_live_qubits']


def test_resource_ir_engine_rejects_interval_wire_double_count() -> None:
    counted_ir = copy.deepcopy(_counted_resource_ir())
    first_wire = counted_ir['liveness_intervals'][0]['live_wire_ids'][0]
    counted_ir['liveness_intervals'][0]['live_wire_ids'].append(first_wire)
    report = evaluate_counted_resource_ir(counted_ir)
    assert report['pass'] is False
    assert report['checks']['intervals_do_not_double_count_wires'] is False


def test_resource_ir_engine_rejects_malformed_term_total() -> None:
    counted_ir = copy.deepcopy(_counted_resource_ir())
    counted_ir['non_clifford_terms'][0]['total_non_clifford'] += 1
    report = evaluate_counted_resource_ir(counted_ir)
    assert report['pass'] is False
    assert report['checks']['term_products_match_totals'] is False
