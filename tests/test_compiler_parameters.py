#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
COMPILER_SRC = REPO_ROOT / 'compiler_verification_project' / 'src'
if str(COMPILER_SRC) not in sys.path:
    sys.path.insert(0, str(COMPILER_SRC))

from compiler_parameters import build_compiler_parameters  # noqa: E402
from integrity import build_compiler_parameter_checks  # noqa: E402


def _artifacts(parameters: dict) -> dict:
    artifact_root = REPO_ROOT / 'compiler_verification_project' / 'artifacts'
    return {
        'compiler_parameters': parameters,
        'build_summary': json.loads((artifact_root / 'build_summary.json').read_text()),
        'full_raw32_oracle': json.loads((artifact_root / 'full_raw32_oracle.json').read_text()),
        'logical_resource_ledger': json.loads((artifact_root / 'logical_resource_ledger.json').read_text()),
        'reusable_chunk_lowering': json.loads((artifact_root / 'reusable_chunk_lowering.json').read_text()),
        'public_headline_result': json.loads((artifact_root / 'public_headline_result.json').read_text()),
    }


def test_compiler_parameters_match_checked_artifact() -> None:
    artifact = json.loads(
        (REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'compiler_parameters.json').read_text()
    )
    assert artifact == build_compiler_parameters()
    checks = build_compiler_parameter_checks(_artifacts(artifact))
    assert checks['pass'] == checks['total']


def test_compiler_parameters_reject_forged_reusable_chunk_policy() -> None:
    forged = deepcopy(build_compiler_parameters())
    forged['reusable_chunk_policy']['chunk_bits'] -= 1
    checks = build_compiler_parameter_checks(_artifacts(forged))
    assert checks['pass'] < checks['total']


def test_compiler_parameters_reject_forged_lookup_policy() -> None:
    forged = deepcopy(build_compiler_parameters())
    forged['lookup_policy']['standard_qroamclean_block_size'] += 1
    checks = build_compiler_parameter_checks(_artifacts(forged))
    assert checks['pass'] < checks['total']


def test_compiler_parameters_reject_forged_public_headline_policy() -> None:
    forged = deepcopy(build_compiler_parameters())
    forged['public_headline_policy']['logical_qubit_limit_exclusive'] = 1199
    checks = build_compiler_parameter_checks(_artifacts(forged))
    assert checks['pass'] < checks['total']
