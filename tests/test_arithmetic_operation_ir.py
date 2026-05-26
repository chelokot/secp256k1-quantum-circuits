from __future__ import annotations

import copy
import gzip
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT_SRC = REPO_ROOT / 'src'
COMPILER_SRC = REPO_ROOT / 'compiler_verification_project' / 'src'
if str(ROOT_SRC) not in sys.path:
    sys.path.insert(0, str(ROOT_SRC))
if str(COMPILER_SRC) not in sys.path:
    sys.path.insert(0, str(COMPILER_SRC))

from arithmetic_operation_ir import (  # noqa: E402
    ARITHMETIC_OPERATION_IR_SCHEMA,
    SELECTED_LEAF_EXACT_OPERATION_COLUMNS,
    build_arithmetic_operation_ir,
    iter_selected_leaf_exact_arithmetic_operations,
)
from project import leaf_opcode_histogram  # noqa: E402


def _arithmetic_lowerings() -> dict:
    return json.loads(
        (REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'arithmetic_lowerings.json').read_text()
    )


def _checked_arithmetic_operation_ir() -> dict:
    return json.loads(
        (REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'arithmetic_operation_ir.json').read_text()
    )


def _preview_row(row: dict) -> dict:
    return {
        'operation_index': int(row['operation_index']),
        'leaf_instance_index': int(row['leaf_instance_index']),
        'kernel': str(row['kernel']),
        'stage': str(row['stage']),
        'block': str(row['block']),
        'block_operation_index': int(row['block_operation_index']),
        'gate': str(row['gate']),
        'operands': list(row['operands']),
    }


def test_arithmetic_operation_ir_reconstructs_checked_artifact() -> None:
    lowerings = _arithmetic_lowerings()
    expected = _checked_arithmetic_operation_ir()
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
    assert observed['tail_macro_engine']['fallback_schedule_peak_field_slots'] == 9
    assert observed['tail_macro_engine']['fallback_schedule_additional_logical_qubits'] == 1536
    assert observed['tail_macro_engine']['destructive_candidate_peak_field_slots'] == 8
    assert observed['tail_macro_engine']['destructive_candidate_status'] == 'optimizer_candidate_not_a_reversible_proof'
    assert observed['tail_macro_engine']['non_clifford_total'] == 1126842


def test_arithmetic_operation_ir_ladder_generators_use_bit_indices() -> None:
    observed = _checked_arithmetic_operation_ir()
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


def test_selected_leaf_exact_arithmetic_iterator_matches_checked_preview() -> None:
    expected_stream = _checked_arithmetic_operation_ir()['selected_leaf_exact_operation_stream']
    rows = list(iter_selected_leaf_exact_arithmetic_operations(
        arithmetic_lowerings=_arithmetic_lowerings(),
        leaf_opcode_histogram=leaf_opcode_histogram(),
        start=0,
        stop=6,
    ))
    assert [_preview_row(row) for row in rows] == expected_stream['preview_head']

    tail_start = int(expected_stream['operation_count']) - 6
    tail_rows = list(iter_selected_leaf_exact_arithmetic_operations(
        arithmetic_lowerings=_arithmetic_lowerings(),
        leaf_opcode_histogram=leaf_opcode_histogram(),
        start=tail_start,
        stop=tail_start + 6,
    ))
    assert [_preview_row(row) for row in tail_rows] == expected_stream['preview_tail']


def test_selected_leaf_exact_arithmetic_export_cli_writes_slice(tmp_path: Path) -> None:
    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / 'compiler_verification_project' / 'scripts' / 'materialize_exact_circuits.py'),
            '--selected-leaf-exact-arithmetic',
            '--slice-start',
            '0',
            '--slice-count',
            '6',
            '--output-dir',
            str(tmp_path),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    output_path = tmp_path / 'selected_leaf_exact_arithmetic' / 'operations.tsv.gz'
    with gzip.open(output_path, 'rt', encoding='utf-8') as handle:
        rows = [line.rstrip('\n').split('\t') for line in handle]
    assert rows[0] == SELECTED_LEAF_EXACT_OPERATION_COLUMNS
    assert len(rows) == 7
    expected_head = _checked_arithmetic_operation_ir()['selected_leaf_exact_operation_stream']['preview_head']
    assert [int(row[0]) for row in rows[1:]] == [int(row['operation_index']) for row in expected_head]
    assert [row[6] for row in rows[1:]] == [row['gate'] for row in expected_head]


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
