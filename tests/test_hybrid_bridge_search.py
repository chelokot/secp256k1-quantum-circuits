from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT_SRC = REPO_ROOT / 'src'
COMPILER_SRC = REPO_ROOT / 'compiler_verification_project' / 'src'
if str(ROOT_SRC) not in sys.path:
    sys.path.insert(0, str(ROOT_SRC))
if str(COMPILER_SRC) not in sys.path:
    sys.path.insert(0, str(COMPILER_SRC))

from hybrid_bridge_search import build_hybrid_bridge_search  # noqa: E402


def _load(name: str) -> dict:
    return json.loads((REPO_ROOT / 'compiler_verification_project' / 'artifacts' / name).read_text())


def test_hybrid_bridge_search_reconstructs_checked_artifact() -> None:
    checked = _load('hybrid_bridge_search.json')
    observed = build_hybrid_bridge_search(
        strict_replayed_tail_headline=_load('strict_replayed_tail_headline.json'),
        reusable_chunk_lowering=_load('reusable_chunk_lowering.json'),
    )

    assert observed == checked
    assert checked['pass'] is True
    assert checked['status'] == 'blocked_no_promotable_hybrid_found'


def test_hybrid_bridge_search_identifies_exact_remaining_breakthrough() -> None:
    checked = _load('hybrid_bridge_search.json')
    corrected = checked['corrected_public_envelope']
    strict_budget = checked['strict_qubit_budget_analysis']
    lookup_tradeoff = checked['strict_lookup_chunk_tradeoff_for_six_slots']
    five_slot = next(row for row in checked['candidate_rows'] if row['name'] == 'projective_five_slot_no_inverse_core')

    assert corrected['listed_register_qubits'] == 1431
    assert corrected['missing_field_lane_qubits'] == 256
    assert corrected['corrected_ecdlp_logical_qubits_with_window_key'] == 1447
    assert corrected['fits_logical_qubit_limit'] is True
    assert corrected['fits_non_clifford_limit'] is False
    assert strict_budget['max_field_slots_with_current_lookup_workspace'] == 5
    assert lookup_tradeoff['total_non_clifford_lower_bound'] >= checked['target']['non_clifford_exclusive']
    assert checked['checks']['periodic_normalization_has_no_target_fitting_row'] is True
    assert five_slot['fits_logical_qubit_limit'] is True
    assert five_slot['fits_non_clifford_limit'] is True
    assert five_slot['status'] == 'only_numeric_target_that_would_fit_current_lookup_and_gate_budget'
