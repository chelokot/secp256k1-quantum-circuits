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


def _minimal_artifacts(crosscheck: dict) -> dict:
    return {
        'qroam_reference_crosscheck': crosscheck,
        'qroam_primitive_certificate': _load_artifact('qroam_primitive_certificate.json'),
        'logical_resource_ledger': _load_artifact('logical_resource_ledger.json'),
    }


def test_reference_cost_exposes_qroamclean_gate_and_workspace_tradeoff() -> None:
    k16 = reference_qroamclean_cost(domain_size=32768, target_bits=256, block_size=16)
    assert k16['lookup_compute_non_clifford'] == 5888
    assert k16['measured_uncompute_non_clifford'] == 2063
    assert k16['per_stream_non_clifford'] == 7951
    assert k16['junk_register_qubits'] == 3840
    assert k16['target_plus_junk_qubits'] == 4096

    k1_chunk = reference_qroamclean_cost(domain_size=32768, target_bits=155, block_size=1)
    assert k1_chunk['per_stream_non_clifford'] == 65536
    assert k1_chunk['junk_register_qubits'] == 0
    assert k1_chunk['target_plus_junk_qubits'] == 155


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
    selected = artifact['selected_reference']
    ledger_selected = artifact['ledger_selected_reference']
    assert selected['domain_size'] == ledger_selected['domain_size'] == 32768
    assert selected['block_size'] == ledger_selected['block_size'] == 1
    assert selected['target_bits'] == 155
    assert ledger_selected['target_bits'] == 256
    assert selected['target_plus_junk_qubits'] == 155
    assert ledger_selected['target_plus_junk_qubits'] == 256
    assert selected['per_stream_non_clifford'] == ledger_selected['per_stream_non_clifford']


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
