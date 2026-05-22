from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SUMMARY_PATH = REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'verification_summary.json'


def test_refresh_integrity_reuses_checked_semantic_replay() -> None:
    before = json.loads(SUMMARY_PATH.read_text())
    result = subprocess.run(
        [
            sys.executable,
            'compiler_verification_project/scripts/verify.py',
            '--refresh-groups',
            'headline_resource_manifest_checks',
            'proof_publication_status_checks',
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    output = json.loads(result.stdout)
    after = json.loads(SUMMARY_PATH.read_text())
    assert output['semantic_replay_mode'] == 'checked-artifact-reused'
    assert output['refreshed_groups'] == [
        'headline_resource_manifest_checks',
        'proof_publication_status_checks',
    ]
    assert after['semantic_replay'] == before['semantic_replay']
    assert after['semantic_replay_checks']['pass'] == after['semantic_replay_checks']['total']
    assert after['headline_resource_manifest_checks']['pass'] == after['headline_resource_manifest_checks']['total']
    assert after['proof_publication_status_checks']['pass'] == after['proof_publication_status_checks']['total']
