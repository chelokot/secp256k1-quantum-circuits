from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
_prepared_targets: set[Path] = set()


def _ensure_target(summary_path: Path, command: list[str]) -> Path:
    if summary_path in _prepared_targets:
        return summary_path
    if os.environ.get('SECP256K1_OPEN_AUDIT_REUSE_ARTIFACTS') == '1' and summary_path.exists():
        _prepared_targets.add(summary_path)
        return summary_path
    subprocess.run(command, cwd=REPO_ROOT, check=True, stdout=subprocess.DEVNULL)
    _prepared_targets.add(summary_path)
    return summary_path


def ensure_repo_verification_summary() -> Path:
    summary_path = REPO_ROOT / 'results' / 'repo_verification_summary.json'
    return _ensure_target(summary_path, [sys.executable, 'scripts/verify_all.py'])


def ensure_cain_summary() -> Path:
    summary_path = REPO_ROOT / 'results' / 'cain_2026_integration_summary.json'
    return _ensure_target(summary_path, [sys.executable, 'scripts/compare_cain_2026.py'])


def ensure_compiler_project_build_summary() -> Path:
    summary_path = REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'build_summary.json'
    return _ensure_target(summary_path, [sys.executable, 'compiler_verification_project/scripts/build.py'])


def ensure_compiler_project_verification_summary() -> Path:
    summary_path = REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'verification_summary.json'
    return _ensure_target(summary_path, [sys.executable, 'compiler_verification_project/scripts/verify.py', '--cases', '16'])
