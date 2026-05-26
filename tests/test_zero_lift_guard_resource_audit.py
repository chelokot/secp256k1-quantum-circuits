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

from zero_lift_guard_resource_audit import (  # noqa: E402
    ZERO_LIFT_GUARD_RESOURCE_AUDIT_SCHEMA,
    ZERO_LIFT_GUARD_RESOURCE_GAP_STATUS,
    build_zero_lift_guard_resource_audit,
)


ARTIFACT_DIR = REPO_ROOT / 'compiler_verification_project' / 'artifacts'


def _load(name: str) -> dict:
    return json.loads((ARTIFACT_DIR / name).read_text())


def test_zero_lift_guard_resource_audit_reconstructs_checked_artifact() -> None:
    assert _load('zero_lift_guard_resource_audit.json') == build_zero_lift_guard_resource_audit(
        tail_macro_engine=_load('tail_macro_engine.json'),
    )


def test_zero_lift_guard_resource_audit_rejects_one_qubit_clean_ladder_capacity() -> None:
    audit = _load('zero_lift_guard_resource_audit.json')

    assert audit['schema'] == ZERO_LIFT_GUARD_RESOURCE_AUDIT_SCHEMA
    assert audit['pass'] is True
    assert audit['current_guard_owner_capacity']['logical_qubits'] == 1
    assert audit['current_guard_owner_capacity']['non_clifford'] == 510
    assert audit['standard_clean_ladder_requirement']['total_ccx'] == 510
    assert audit['standard_clean_ladder_requirement']['prefix_ancilla_bits'] == 254
    assert audit['standard_clean_ladder_requirement']['peak_predicate_workspace_bits'] == 255
    assert audit['capacity_gap']['missing_logical_qubits_under_clean_ladder'] == 254
    assert audit['promotion_status']['status'] == ZERO_LIFT_GUARD_RESOURCE_GAP_STATUS
