#!/usr/bin/env python3

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
COMPILER_SRC = REPO_ROOT / 'compiler_verification_project' / 'src'
ROOT_SRC = REPO_ROOT / 'src'
if str(ROOT_SRC) not in sys.path:
    sys.path.insert(0, str(ROOT_SRC))
if str(COMPILER_SRC) not in sys.path:
    sys.path.insert(0, str(COMPILER_SRC))

from integrity import build_qroam_reference_crosscheck_checks  # noqa: E402
from qroam_reference_crosscheck import build_qroam_reference_crosscheck, reference_qroamclean_cost  # noqa: E402


ARTIFACTS = REPO_ROOT / 'compiler_verification_project' / 'artifacts'


def _load_artifact(name: str) -> dict:
    return json.loads((ARTIFACTS / name).read_text())


def _compiler_parameters() -> dict:
    return _load_artifact('compiler_parameters.json')


def _qroam_primitive_parameters() -> dict:
    return _load_artifact('qroam_primitive_certificate.json')['parameters']


def _ledger_selected_reference() -> dict:
    return _load_artifact('logical_resource_ledger.json')['qroam_clean_tradeoff_sweep']['selected_row']


def _minimal_artifacts(crosscheck: dict) -> dict:
    return {
        'qroam_reference_crosscheck': crosscheck,
        'qroam_primitive_certificate': _load_artifact('qroam_primitive_certificate.json'),
        'logical_resource_ledger': _load_artifact('logical_resource_ledger.json'),
    }


def test_reference_cost_exposes_qroamclean_gate_and_workspace_tradeoff() -> None:
    parameters = _compiler_parameters()
    domain_size = parameters['windowing']['folded_magnitude_domain']
    field_bits = parameters['field']['field_bits']
    comparison_block_size = parameters['lookup_policy']['standard_qroamclean_block_size'] * 16
    k16 = reference_qroamclean_cost(
        domain_size=domain_size,
        target_bits=field_bits,
        block_size=comparison_block_size,
    )
    address_blocks = (domain_size + comparison_block_size - 1) // comparison_block_size
    assert k16['lookup_compute_non_clifford'] == address_blocks + (comparison_block_size - 1) * field_bits
    assert k16['measured_uncompute_non_clifford'] == address_blocks + comparison_block_size - 1
    assert k16['per_stream_non_clifford'] == k16['lookup_compute_non_clifford'] + k16['measured_uncompute_non_clifford']
    assert k16['junk_register_qubits'] == (comparison_block_size - 1) * field_bits
    assert k16['target_plus_junk_qubits'] == comparison_block_size * field_bits

    primitive_parameters = _qroam_primitive_parameters()
    k1_chunk = reference_qroamclean_cost(
        domain_size=primitive_parameters['domain_size'],
        target_bits=primitive_parameters['target_bits'],
        block_size=primitive_parameters['block_size'],
    )
    assert k1_chunk['per_stream_non_clifford'] == 2 * primitive_parameters['domain_size']
    assert k1_chunk['junk_register_qubits'] == 0
    assert k1_chunk['target_plus_junk_qubits'] == primitive_parameters['target_bits']


def test_qroam_reference_crosscheck_artifact_matches_generator() -> None:
    artifact = _load_artifact('qroam_reference_crosscheck.json')
    expected = build_qroam_reference_crosscheck(
        qroam_primitive_certificate=_load_artifact('qroam_primitive_certificate.json'),
        logical_resource_ledger=_load_artifact('logical_resource_ledger.json'),
    )
    checks = build_qroam_reference_crosscheck_checks(_minimal_artifacts(artifact))
    assert artifact == expected
    assert artifact['pass'] is True
    assert checks['pass'] == checks['total']


def test_qroam_reference_crosscheck_keeps_chunk_and_full_field_widths_separate() -> None:
    artifact = _load_artifact('qroam_reference_crosscheck.json')
    parameters = _compiler_parameters()
    primitive_parameters = _qroam_primitive_parameters()
    ledger_row = _ledger_selected_reference()
    selected = artifact['selected_reference']
    ledger_selected = artifact['ledger_selected_reference']
    assert selected['domain_size'] == ledger_selected['domain_size'] == parameters['windowing']['folded_magnitude_domain']
    assert selected['block_size'] == ledger_selected['block_size'] == parameters['lookup_policy']['standard_qroamclean_block_size']
    assert selected['target_bits'] == primitive_parameters['target_bits']
    assert ledger_selected['target_bits'] == parameters['field']['field_bits'] == ledger_row['target_register_qubits']
    assert selected['target_plus_junk_qubits'] == primitive_parameters['target_bits']
    assert ledger_selected['target_plus_junk_qubits'] == ledger_row['target_plus_junk_qubits']
    assert selected['per_stream_non_clifford'] == ledger_selected['per_stream_non_clifford']


def test_qroam_reference_crosscheck_toy_semantics_trace_unary_iteration() -> None:
    artifact = _load_artifact('qroam_reference_crosscheck.json')
    toy_case = artifact['toy_semantics'][0]
    row = toy_case['rows'][2]
    assert row['compute_operation_count'] == toy_case['domain_size']
    assert row['measured_uncompute_operation_count'] == toy_case['domain_size']
    assert len(row['compute_trace']) == toy_case['domain_size']
    assert [step['match_control'] for step in row['compute_trace']].count(True) == 1
    assert row['compute_trace'][2]['match_control'] is True
    assert row['compute_trace'][-1]['target_after_step'] == row['expected_table_value']
    assert row['target_after_measured_uncompute'] == 0


def test_qroam_reference_crosscheck_checks_reject_forged_chunk_workspace() -> None:
    forged = deepcopy(_load_artifact('qroam_reference_crosscheck.json'))
    forged['selected_reference']['target_plus_junk_qubits'] -= 1
    checks = build_qroam_reference_crosscheck_checks(_minimal_artifacts(forged))
    assert checks['pass'] < checks['total']


def test_qroam_reference_crosscheck_checks_reject_forged_toy_semantics() -> None:
    forged = deepcopy(_load_artifact('qroam_reference_crosscheck.json'))
    forged['toy_semantics'][0]['rows'][0]['target_after_compute'] += 1
    forged['toy_semantics'][0]['rows'][0]['pass'] = False
    forged['toy_semantics'][0]['pass'] = False
    forged['checks']['toy_qroam_semantics_select_and_uncompute'] = False
    forged['pass'] = False
    checks = build_qroam_reference_crosscheck_checks(_minimal_artifacts(forged))
    assert checks['pass'] < checks['total']
