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


def _load(name: str) -> dict:
    return json.loads((REPO_ROOT / 'compiler_verification_project' / 'artifacts' / name).read_text())


def test_primary_strict_result_matches_generator_and_demotes_legacy_wrapper() -> None:
    observed = _load('primary_strict_result.json')
    expected = build_primary_strict_result(
        strict_replayed_tail_headline=_load('strict_replayed_tail_headline.json'),
        public_headline_result=_load('public_headline_result.json'),
        engine_completion_audit=_load('engine_completion_audit.json'),
        hybrid_bridge_search=_load('hybrid_bridge_search.json'),
    )

    assert observed == expected
    assert observed['pass'] is True
    assert observed['role'] == 'single current public resource headline'
    assert observed['selected_result']['logical_qubits'] == 1968
    assert observed['selected_result']['non_clifford'] == 36973222
    assert observed['legacy_wrapper_reference']['status'] == 'legacy_macro_zkp_wrapper_not_primary_resource_headline'
    assert observed['resource_claim_level']['clifford_complete_flat_netlist'] == 'not_yet_achieved'
    assert observed['resource_claim_level']['zkp_binds_this_strict_result'] == 'not_yet_achieved'


def test_primary_strict_result_does_not_confuse_legacy_flat_netlist_with_strict_headline() -> None:
    observed = _load('primary_strict_result.json')
    flat_status = observed['flat_netlist_status']

    assert flat_status['current_materialized_flat_netlist_binds_selected_strict_result'] is False
    assert flat_status['current_materialized_flat_netlist_binds_legacy_wrapper'] is True
    assert flat_status['peak_live_qubits'] == observed['legacy_wrapper_reference']['selected_result']['logical_qubits']
    assert flat_status['peak_live_qubits'] != observed['selected_result']['logical_qubits']
