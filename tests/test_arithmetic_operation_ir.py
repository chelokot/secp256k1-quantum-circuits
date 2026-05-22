from __future__ import annotations

import copy
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

from arithmetic_operation_ir import ARITHMETIC_OPERATION_IR_SCHEMA, build_arithmetic_operation_ir  # noqa: E402
from project import leaf_opcode_histogram  # noqa: E402


def _arithmetic_lowerings() -> dict:
    return json.loads(
        (REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'arithmetic_lowerings.json').read_text()
    )


def test_arithmetic_operation_ir_reconstructs_checked_artifact() -> None:
    lowerings = _arithmetic_lowerings()
    expected = json.loads(
        (REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'arithmetic_operation_ir.json').read_text()
    )
    observed = build_arithmetic_operation_ir(
        arithmetic_lowerings=lowerings,
        leaf_opcode_histogram=leaf_opcode_histogram(),
    )
    assert observed == expected
    assert observed['schema'] == ARITHMETIC_OPERATION_IR_SCHEMA
    assert observed['pass'] is True
    assert all(observed['checks'].values())


def test_arithmetic_operation_ir_rejects_forged_block_total() -> None:
    lowerings = copy.deepcopy(_arithmetic_lowerings())
    lowerings['kernels'][0]['stages'][0]['blocks'][0]['primitive_counts_total']['ccx'] += 1
    observed = build_arithmetic_operation_ir(
        arithmetic_lowerings=lowerings,
        leaf_opcode_histogram=leaf_opcode_histogram(),
    )
    assert observed['pass'] is False
    assert observed['checks']['block_totals_match_materialized_operations'] is False
