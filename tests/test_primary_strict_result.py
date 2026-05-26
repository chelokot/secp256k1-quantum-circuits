#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / 'compiler_verification_project' / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from primary_strict_result import build_primary_strict_result  # noqa: E402
from public_engine_contract import STRICT_RESOURCE_CLAIM_NOT_YET_ACHIEVED  # noqa: E402


def _load(name: str) -> dict:
    return json.loads((REPO_ROOT / 'compiler_verification_project' / 'artifacts' / name).read_text())


def test_primary_strict_result_matches_generator_and_demotes_legacy_wrapper() -> None:
    observed = _load('primary_strict_result.json')
    strict_headline = _load('strict_replayed_tail_headline.json')
    public_engine = _load('public_engine_manifest.json')
    expected = build_primary_strict_result(
        strict_replayed_tail_headline=strict_headline,
        public_headline_result=_load('public_headline_result.json'),
        engine_completion_audit=_load('engine_completion_audit.json'),
        public_candidate_materialized_circuit_manifest=_load('public_candidate_materialized_circuit_manifest.json'),
        hybrid_bridge_search=_load('hybrid_bridge_search.json'),
    )

    assert observed == expected
    assert observed['pass'] is True
    assert observed['role'] == 'strict replayed-tail engine candidate, not repo physical baseline'
    assert observed['selected_result'] == strict_headline['selected_result']
    assert observed['selected_result']['logical_qubits'] == public_engine['public_totals']['logical_qubits']
    assert observed['selected_result']['non_clifford'] == public_engine['public_totals']['non_clifford']
    assert observed['selected_result']['logical_qubits'] != public_engine['legacy_wrapper_totals']['logical_qubits']
    assert observed['legacy_wrapper_reference']['status'] == 'legacy_macro_zkp_wrapper_not_primary_resource_headline'
    assert observed['resource_claim_level']['clifford_complete_flat_netlist'] == STRICT_RESOURCE_CLAIM_NOT_YET_ACHIEVED
    assert observed['resource_claim_level']['zkp_binds_this_strict_result'] == STRICT_RESOURCE_CLAIM_NOT_YET_ACHIEVED


def test_primary_strict_result_does_not_confuse_legacy_flat_netlist_with_strict_headline() -> None:
    observed = _load('primary_strict_result.json')
    flat_status = observed['flat_netlist_status']

    assert flat_status['current_materialized_flat_netlist_binds_selected_strict_result'] is True
    assert flat_status['current_materialized_flat_netlist_binds_legacy_wrapper'] is False
    assert flat_status['strict_capacity_overlay_binds_selected_result'] is True
    assert flat_status['strict_capacity_overlay_is_full_liveness_rewrite'] is False
    assert flat_status['strict_capacity_peak_qubits'] == observed['selected_result']['logical_qubits']
    assert flat_status['strict_liveness_projection_binds_selected_result'] is True
    assert flat_status['strict_liveness_projection_is_segment_hashed_flat_netlist'] is True
    assert flat_status['strict_materialized_flat_netlist_binds_selected_strict_result'] is True
    assert flat_status['strict_liveness_projection_peak_qubits'] == observed['selected_result']['logical_qubits']
    assert flat_status['strict_materialized_flat_netlist_peak_live_qubits'] == observed['selected_result']['logical_qubits']
    assert len(flat_status['strict_materialized_flat_netlist_operation_stream_sha256']) == 64
    assert len(flat_status['strict_materialized_flat_netlist_segment_merkle_root_sha256']) == 64
    assert flat_status['peak_live_qubits'] == observed['selected_result']['logical_qubits']
    assert flat_status['legacy_materialized_flat_netlist_peak_live_qubits'] == observed['legacy_wrapper_reference']['selected_result']['logical_qubits']
    assert flat_status['legacy_materialized_flat_netlist_peak_live_qubits'] != observed['selected_result']['logical_qubits']
