from __future__ import annotations

import copy
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
COMPILER_SRC = REPO_ROOT / 'compiler_verification_project' / 'src'
if str(COMPILER_SRC) not in sys.path:
    sys.path.insert(0, str(COMPILER_SRC))

from resource_ir_engine import (  # noqa: E402
    RESOURCE_CONTRACT_ENGINE_SCHEMA,
    RESOURCE_IR_ENGINE_SCHEMA,
    evaluate_counted_resource_ir,
    evaluate_resource_contract,
)


def _lowering() -> dict:
    return json.loads((REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'reusable_chunk_lowering.json').read_text())


def _counted_resource_ir() -> dict:
    return _lowering()['counted_resource_ir']


def test_resource_ir_engine_recomputes_checked_reusable_chunk_ir() -> None:
    counted_ir = _counted_resource_ir()
    report = evaluate_counted_resource_ir(counted_ir)
    assert report['schema'] == RESOURCE_IR_ENGINE_SCHEMA
    assert report['pass'] is True
    assert report['non_clifford_total_from_terms'] == counted_ir['recomputed_total_non_clifford']
    assert report['peak_live_qubits_from_intervals'] == counted_ir['recomputed_peak_live_qubits']


def test_resource_contract_engine_unifies_counted_and_executable_liveness() -> None:
    lowering = _lowering()
    report = evaluate_resource_contract(
        counted_resource_ir=lowering['counted_resource_ir'],
        counted_resource_engine=lowering['counted_resource_engine'],
        executable_liveness=lowering['executable_liveness'],
        owner_capacity=lowering['owner_capacity'],
    )
    assert report == lowering['resource_contract_engine']
    assert report['schema'] == RESOURCE_CONTRACT_ENGINE_SCHEMA
    assert report['pass'] is True
    assert report['owner_peak_live_qubits'] == report['owner_capacity_qubits']


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


def test_resource_contract_engine_rejects_counted_executable_liveness_drift() -> None:
    lowering = copy.deepcopy(_lowering())
    lowering['counted_resource_ir']['liveness_intervals'][0]['live_wire_ids'].append('folded_lookup_control_workspace')
    lowering['counted_resource_ir']['liveness_intervals'][0]['owner_live_qubits']['lookup_workspace'] = 18
    lowering['counted_resource_ir']['liveness_intervals'][0]['total_live_qubits'] += 18
    lowering['counted_resource_engine'] = evaluate_counted_resource_ir(lowering['counted_resource_ir'])
    report = evaluate_resource_contract(
        counted_resource_ir=lowering['counted_resource_ir'],
        counted_resource_engine=lowering['counted_resource_engine'],
        executable_liveness=lowering['executable_liveness'],
        owner_capacity=lowering['owner_capacity'],
    )
    assert report['pass'] is False
    assert report['checks']['counted_intervals_match_executable_liveness'] is False
