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

from integrity import build_qroam_primitive_certificate_checks  # noqa: E402
from qroam_primitive import build_qroam_k1_primitive_certificate  # noqa: E402


def _selected_parameters() -> dict:
    artifacts = REPO_ROOT / 'compiler_verification_project' / 'artifacts'
    ledger = json.loads((artifacts / 'logical_resource_ledger.json').read_text())
    stress = json.loads((artifacts / 'fallback_frontier_stress.json').read_text())
    return {
        'domain_size': ledger['qroam_clean_tradeoff_sweep']['selected_row']['domain_size'],
        'target_bits': stress['chunked_coordinate_qroam_counterfactual']['max_qroam_target_bits_per_live_chunk'],
        'block_size': 1,
    }


def _minimal_artifacts(certificate: dict) -> dict:
    parameters = _selected_parameters()
    return {
        'qroam_primitive_certificate': certificate,
        'logical_resource_ledger': {
            'qroam_clean_tradeoff_sweep': {
                'selected_row': {
                    'domain_size': parameters['domain_size'],
                },
            },
        },
        'fallback_frontier_stress': {
            'chunked_coordinate_qroam_counterfactual': {
                'max_qroam_target_bits_per_live_chunk': parameters['target_bits'],
            },
        },
    }


def test_qroam_k1_certificate_reconstructs_selected_stream_counts() -> None:
    parameters = _selected_parameters()
    certificate = build_qroam_k1_primitive_certificate(**parameters)
    checks = build_qroam_primitive_certificate_checks(_minimal_artifacts(certificate))
    assert certificate['pass'] is True
    assert certificate['traversed_counts']['lookup_compute_non_clifford'] == parameters['domain_size']
    assert certificate['traversed_counts']['measured_uncompute_non_clifford'] == parameters['domain_size']
    assert certificate['traversed_counts']['per_stream_non_clifford'] == parameters['domain_size'] * 2
    assert certificate['traversed_counts']['target_plus_junk_qubits'] == parameters['target_bits']
    assert checks['pass'] == checks['total']


def test_qroam_k1_certificate_checks_reject_forged_count() -> None:
    certificate = build_qroam_k1_primitive_certificate(**_selected_parameters())
    forged = deepcopy(certificate)
    forged['traversed_counts']['per_stream_non_clifford'] -= 1
    checks = build_qroam_primitive_certificate_checks(_minimal_artifacts(forged))
    assert checks['pass'] < checks['total']


def test_qroam_k1_certificate_checks_reject_forged_workspace() -> None:
    certificate = build_qroam_k1_primitive_certificate(**_selected_parameters())
    forged = deepcopy(certificate)
    forged['wire_catalog']['target_register']['qubits'] -= 1
    checks = build_qroam_primitive_certificate_checks(_minimal_artifacts(forged))
    assert checks['pass'] < checks['total']
