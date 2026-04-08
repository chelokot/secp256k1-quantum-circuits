from __future__ import annotations

import json
import sys
from pathlib import Path

from support import ensure_compiler_project_build_summary, ensure_compiler_project_verification_summary

REPO_ROOT = Path(__file__).resolve().parents[1]
COMPILER_SRC = REPO_ROOT / 'compiler_verification_project' / 'src'
if str(COMPILER_SRC) not in sys.path:
    sys.path.insert(0, str(COMPILER_SRC))

from lookup_lowering import lowered_lookup_semantic_summary  # noqa: E402


def _load_lookup_lowerings() -> dict:
    ensure_compiler_project_build_summary()
    ensure_compiler_project_verification_summary()
    path = REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'lookup_lowerings.json'
    return json.loads(path.read_text())


def test_lookup_lowering_stage_inventory_reconstructs_family_totals() -> None:
    lookup_lowerings = _load_lookup_lowerings()
    for family in lookup_lowerings['families']:
        assert family['direct_lookup_non_clifford'] == sum(stage['non_clifford_total'] for stage in family['stages'])
        assert family['per_leaf_lookup_non_clifford'] == family['direct_lookup_non_clifford']
        assert family['extra_lookup_workspace_qubits'] == max(stage['total_workspace_qubits'] for stage in family['stages'])


def test_lookup_lowering_semantics_match_contract() -> None:
    summary = lowered_lookup_semantic_summary()
    for family in summary['families']:
        assert family['canonical_full_exhaustive_pass'] == family['canonical_full_exhaustive_total']
        assert family['multibase_edge_pass'] == family['multibase_edge_total']
