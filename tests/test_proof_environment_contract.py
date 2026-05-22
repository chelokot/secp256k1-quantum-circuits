#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT_SRC = REPO_ROOT / 'src'
COMPILER_SRC = REPO_ROOT / 'compiler_verification_project' / 'src'
if str(ROOT_SRC) not in sys.path:
    sys.path.insert(0, str(ROOT_SRC))
if str(COMPILER_SRC) not in sys.path:
    sys.path.insert(0, str(COMPILER_SRC))

from integrity import evaluate_mutated_verification_groups, load_compiler_artifacts  # noqa: E402
from proof_environment_contract import PROOF_ENVIRONMENT_CONTRACT_SCHEMA, build_proof_environment_contract  # noqa: E402


def _artifact() -> dict:
    return json.loads((REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'proof_environment_contract.json').read_text())


def test_proof_environment_contract_matches_generator() -> None:
    observed = _artifact()
    expected = build_proof_environment_contract(repo_root=REPO_ROOT)
    assert observed == expected
    assert observed['schema'] == PROOF_ENVIRONMENT_CONTRACT_SCHEMA
    assert observed['pass'] is True
    assert all(observed['checks'].values())


def test_proof_environment_contract_has_no_implicit_prover_commands() -> None:
    contract = _artifact()
    command_texts = [
        command['shell_command'] if 'shell_command' in command else ' '.join(command['argv'])
        for command in contract['command_contracts']
    ]
    assert not any(' --prove' in text or text.endswith(' --prove') for text in command_texts)
    assert contract['checks']['direct_verify_commands_bind_checked_input_and_proofs'] is True
    assert contract['checks']['publication_freshness_gate_requires_all_current_proofs'] is True
    assert contract['checks']['fast_publication_gate_uses_current_proof_requirement'] is True
    assert any('release_candidate_preproof.py' in text and '--execute' in text for text in command_texts)


def test_proof_environment_contract_integrity_rejects_manifest_drift() -> None:
    artifacts = load_compiler_artifacts(REPO_ROOT)
    mutated = dict(artifacts)
    mutated['proof_environment_contract'] = deepcopy(artifacts['proof_environment_contract'])
    mutated['proof_environment_contract']['checked_artifacts']['compressed_proof']['manifest_sha256_matches_checked_record'] = False
    report = evaluate_mutated_verification_groups(mutated, REPO_ROOT, group_names=['proof_environment_contract_checks'])
    group = report['proof_environment_contract_checks']
    assert group['pass'] < group['total']


def test_proof_environment_contract_integrity_rejects_publication_gate_drift() -> None:
    artifacts = load_compiler_artifacts(REPO_ROOT)
    mutated = dict(artifacts)
    mutated['proof_environment_contract'] = deepcopy(artifacts['proof_environment_contract'])
    gate = next(
        command
        for command in mutated['proof_environment_contract']['command_contracts']
        if command['name'] == 'proof_status_publication_gate'
    )
    gate['argv'].remove('--require-all-current')
    report = evaluate_mutated_verification_groups(mutated, REPO_ROOT, group_names=['proof_environment_contract_checks'])
    group = report['proof_environment_contract_checks']
    assert group['pass'] < group['total']
