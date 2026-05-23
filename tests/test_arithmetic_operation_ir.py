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
    assert observed['summary']['generated_ladder_max_operand_slots_required'] == 287
    assert observed['checks']['modular_kernels_derive_from_executable_modular_circuit_ir'] is True
    assert observed['checks']['tail_macro_kernel_derives_from_tail_macro_engine'] is True
    assert observed['executable_modular_circuit_ir']['non_clifford_by_opcode']['field_mul'] == 71492
    assert observed['tail_macro_engine']['expanded_field_operation_count'] == 23
    assert observed['tail_macro_engine']['non_clifford_total'] == 1126332


def test_arithmetic_operation_ir_ladder_generators_use_bit_indices() -> None:
    observed = json.loads(
        (REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'arithmetic_operation_ir.json').read_text()
    )
    ladder_contracts = [
        block['source_contract']['generator_operand_contract']
        for kernel in observed['kernels']
        for stage in kernel['stages']
        for block in stage['blocks']
        if (
            block['source_contract']['generator_operand_contract'] is not None
            and block['source_contract']['generator_operand_contract']['kind'] == 'repeated_ladder_with_measurement'
        )
    ]
    assert ladder_contracts
    assert all(contract['pass'] is True for contract in ladder_contracts)
    assert all(contract['operand_domain'] == 'ladder_bit_index' for contract in ladder_contracts)
    assert max(contract['observed_operand_slots_required'] for contract in ladder_contracts) == 287
    assert any(contract['repeat_count'] > 1 for contract in ladder_contracts)


def test_arithmetic_operation_ir_rejects_forged_block_total() -> None:
    lowerings = copy.deepcopy(_arithmetic_lowerings())
    lowerings['kernels'][0]['stages'][0]['blocks'][0]['primitive_counts_total']['ccx'] += 1
    observed = build_arithmetic_operation_ir(
        arithmetic_lowerings=lowerings,
        leaf_opcode_histogram=leaf_opcode_histogram(),
    )
    assert observed['pass'] is False
    assert observed['checks']['block_totals_match_materialized_operations'] is False


def test_arithmetic_operation_ir_rejects_ladder_generator_shape_forgery() -> None:
    lowerings = copy.deepcopy(_arithmetic_lowerings())
    generator = lowerings['kernels'][0]['stages'][3]['blocks'][0]['primitive_operation_generator']
    assert generator['kind'] == 'repeated_ladder_with_measurement'
    generator['kind'] = 'repeated_gate_with_measurement'
    generator['count'] = generator['bit_count'] * generator['repeat_count']
    observed = build_arithmetic_operation_ir(
        arithmetic_lowerings=lowerings,
        leaf_opcode_histogram=leaf_opcode_histogram(),
    )
    assert observed['pass'] is False
    assert observed['checks']['non_qroam_generated_ladders_use_typed_ladder_generator'] is False


def test_arithmetic_operation_ir_rejects_executable_modular_ir_drift() -> None:
    lowerings = copy.deepcopy(_arithmetic_lowerings())
    lowerings['executable_modular_circuit_ir']['non_clifford_by_opcode']['field_mul'] -= 1
    observed = build_arithmetic_operation_ir(
        arithmetic_lowerings=lowerings,
        leaf_opcode_histogram=leaf_opcode_histogram(),
    )
    assert observed['pass'] is False
    assert observed['checks']['modular_kernels_derive_from_executable_modular_circuit_ir'] is False


def test_arithmetic_operation_ir_rejects_tail_macro_engine_drift() -> None:
    lowerings = copy.deepcopy(_arithmetic_lowerings())
    lowerings['tail_macro_engine']['non_clifford_total'] -= 1
    observed = build_arithmetic_operation_ir(
        arithmetic_lowerings=lowerings,
        leaf_opcode_histogram=leaf_opcode_histogram(),
    )
    assert observed['pass'] is False
    assert observed['checks']['tail_macro_kernel_derives_from_tail_macro_engine'] is False
