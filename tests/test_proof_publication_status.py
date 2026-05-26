#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
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
from proof_publication_status import PROOF_PUBLICATION_STATUS_SCHEMA, build_proof_publication_status  # noqa: E402
from proof_status_report import build_proof_status_report  # noqa: E402


def _artifact() -> dict:
    return json.loads((REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'proof_publication_status.json').read_text())


def test_proof_status_script_matches_library_report() -> None:
    result = subprocess.run(
        [sys.executable, 'compiler_verification_project/scripts/proof_status.py'],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout) == build_proof_status_report(REPO_ROOT)


def test_proof_publication_status_matches_generator_and_keeps_ready_separate() -> None:
    observed = _artifact()
    expected = build_proof_publication_status(repo_root=REPO_ROOT)
    assert observed == expected
    assert observed['schema'] == PROOF_PUBLICATION_STATUS_SCHEMA
    assert observed['pass'] is True
    assert all(observed['checks'].values())
    public_result = json.loads(
        (REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'public_headline_result.json').read_text()
    )
    assert observed['publication_ready'] is (observed['proof_status']['all_current'] and public_result['pass'])
    if not observed['publication_ready']:
        assert observed['publication_blockers']


def test_proof_publication_status_integrity_rejects_forged_ready_flag() -> None:
    artifacts = load_compiler_artifacts(REPO_ROOT)
    mutated = dict(artifacts)
    mutated['proof_publication_status'] = deepcopy(artifacts['proof_publication_status'])
    mutated['proof_publication_status']['publication_ready'] = not mutated['proof_publication_status']['publication_ready']
    report = evaluate_mutated_verification_groups(mutated, REPO_ROOT, group_names=['proof_publication_status_checks'])
    group = report['proof_publication_status_checks']
    assert group['pass'] < group['total']


def test_proof_publication_status_integrity_rejects_removed_groth16_gate() -> None:
    artifacts = load_compiler_artifacts(REPO_ROOT)
    mutated = dict(artifacts)
    mutated['proof_publication_status'] = deepcopy(artifacts['proof_publication_status'])
    mutated['proof_publication_status']['publication_gate_commands'] = [
        command
        for command in mutated['proof_publication_status']['publication_gate_commands']
        if command['name'] != 'public_headline_groth16_verify'
    ]
    report = evaluate_mutated_verification_groups(mutated, REPO_ROOT, group_names=['proof_publication_status_checks'])
    group = report['proof_publication_status_checks']
    assert group['pass'] < group['total']
