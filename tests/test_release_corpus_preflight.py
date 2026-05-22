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

from integrity import build_release_corpus_preflight_checks  # noqa: E402
from release_corpus_preflight import build_release_corpus_preflight  # noqa: E402


ARTIFACTS = REPO_ROOT / 'compiler_verification_project' / 'artifacts'


def _load_artifact(name: str) -> dict:
    return json.loads((ARTIFACTS / name).read_text())


def _minimal_artifacts(preflight: dict) -> dict:
    return {
        'release_corpus_preflight': preflight,
        'streamed_lookup_tail_leaf': _load_artifact('streamed_lookup_tail_leaf.json'),
        'proof_corpus_profiles': _load_artifact('proof_corpus_profiles.json'),
    }


def test_release_corpus_preflight_matches_generator_and_covers_9024_cases() -> None:
    artifact = _load_artifact('release_corpus_preflight.json')
    expected = build_release_corpus_preflight(
        leaf=_load_artifact('streamed_lookup_tail_leaf.json'),
        proof_corpus_profiles=_load_artifact('proof_corpus_profiles.json'),
    )
    checks = build_release_corpus_preflight_checks(_minimal_artifacts(artifact))
    assert artifact == expected
    assert artifact['pass'] is True
    assert artifact['case_count'] == 9024
    assert checks['pass'] == checks['total']
    assert set(artifact['category_counts']) == {
        'accumulator_infinity',
        'doubling',
        'inverse',
        'lookup_infinity',
        'random',
        'zero_zero',
    }


def test_release_corpus_preflight_checks_reject_forged_digest() -> None:
    forged = deepcopy(_load_artifact('release_corpus_preflight.json'))
    forged['case_stream_sha256'] = '0' * 64
    checks = build_release_corpus_preflight_checks(_minimal_artifacts(forged))
    assert checks['pass'] < checks['total']
