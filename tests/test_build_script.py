from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / 'compiler_verification_project' / 'scripts' / 'build.py'
SPEC = importlib.util.spec_from_file_location('compiler_project_build', SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_build_targets_include_no_prover_release_candidate() -> None:
    assert 'release-candidate-zkp' in MODULE.BUILD_TARGETS
    assert 'materialized-circuit-manifest' in MODULE.BUILD_TARGETS


def test_release_candidate_zkp_uses_release_profile(monkeypatch: Any) -> None:
    calls: list[dict[str, Any]] = []
    profile = MODULE.resolve_proof_corpus_profile('release')

    def fake_write_zkp_attestation_inputs(**kwargs: Any) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(MODULE, 'write_zkp_attestation_inputs', fake_write_zkp_attestation_inputs)
    MODULE.build_release_candidate_zkp()

    assert calls == [
        {
            'family_name': 'reusable-chunk',
            'case_count': profile['case_count'],
            'case_start': profile['case_start'],
            'output_dir': REPO_ROOT
            / 'compiler_verification_project'
            / 'artifacts'
            / 'zkp_attestation_release_candidate',
        },
    ]
