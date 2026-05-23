#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load(relative_path: str) -> dict:
    return json.loads((REPO_ROOT / relative_path).read_text())


def test_strict_replayed_tail_headline_is_derived_from_replay_artifacts() -> None:
    headline = _load('compiler_verification_project/artifacts/strict_replayed_tail_headline.json')
    tail_engine = _load('compiler_verification_project/artifacts/tail_macro_engine.json')
    lowering = _load('compiler_verification_project/artifacts/reusable_chunk_lowering.json')
    selected = headline['selected_result']
    formula = headline['logical_qubit_formula']
    replay = tail_engine['fused_output_replay_certificate']

    assert headline['pass'] is True
    assert selected['tail_field_slots'] == tail_engine['fused_output_slot_assignment']['peak_field_slots'] == 7
    assert replay['pass'] is True
    assert replay['owner_capacity_pass'] is True
    assert replay['checked_non_infinity_pairs'] == headline['semantic_replay_evidence']['checked_non_infinity_pairs']
    assert replay['checked_lookup_infinity_pairs'] == headline['semantic_replay_evidence']['checked_lookup_infinity_pairs']
    assert formula['reconstructed_total'] == (
        formula['tail_field_slots'] * formula['field_bits']
        + formula['lookup_workspace_qubits']
        + formula['control_qubits']
        + formula['phase_qubits']
    )
    assert selected['logical_qubits'] == formula['reconstructed_total']
    assert selected['non_clifford'] == lowering['non_clifford_derivation']['candidate_total_non_clifford']


def test_readme_strict_headline_block_is_generated_from_artifact() -> None:
    subprocess.run(
        [sys.executable, 'compiler_verification_project/scripts/update_readme_headline.py', '--check'],
        cwd=REPO_ROOT,
        check=True,
    )
