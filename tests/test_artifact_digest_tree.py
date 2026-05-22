#!/usr/bin/env python3

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
COMPILER_SRC = REPO_ROOT / 'compiler_verification_project' / 'src'
ROOT_SRC = REPO_ROOT / 'src'
if str(ROOT_SRC) not in sys.path:
    sys.path.insert(0, str(ROOT_SRC))
if str(COMPILER_SRC) not in sys.path:
    sys.path.insert(0, str(COMPILER_SRC))

from artifact_digest_tree import build_artifact_digest_tree  # noqa: E402
from integrity import build_artifact_digest_tree_checks  # noqa: E402


ARTIFACT_PATH = REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'artifact_digest_tree.json'


def _artifact() -> dict:
    return json.loads(ARTIFACT_PATH.read_text())


def _large_tracked_paths(threshold: int) -> set[str]:
    result = subprocess.run(
        ['git', 'ls-files'],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    return {
        relative_path
        for relative_path in result.stdout.splitlines()
        if (REPO_ROOT / relative_path).is_file()
        and (REPO_ROOT / relative_path).stat().st_size >= threshold
    }


def test_artifact_digest_tree_matches_generator_and_covers_large_tracked_files() -> None:
    artifact = _artifact()
    expected = build_artifact_digest_tree(
        repo_root=REPO_ROOT,
        size_threshold_bytes=artifact['size_threshold_bytes'],
        chunk_size_bytes=artifact['chunk_size_bytes'],
    )
    checks = build_artifact_digest_tree_checks({'artifact_digest_tree': artifact}, REPO_ROOT)
    assert artifact == expected
    assert checks['pass'] == checks['total']
    assert {row['path'] for row in artifact['files']} == _large_tracked_paths(artifact['size_threshold_bytes'])


def test_artifact_digest_tree_checks_reject_forged_chunk_hash() -> None:
    forged = deepcopy(_artifact())
    forged['files'][0]['chunks'][0]['sha256'] = '0' * 64
    checks = build_artifact_digest_tree_checks({'artifact_digest_tree': forged}, REPO_ROOT)
    assert checks['pass'] < checks['total']
