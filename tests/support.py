from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
_prepared_targets: set[Path] = set()


def ensure_repo_verification_summary() -> Path:
    summary_path = REPO_ROOT / 'results' / 'repo_verification_summary.json'
    if summary_path not in _prepared_targets:
        if not summary_path.exists():
            subprocess.run([sys.executable, 'scripts/verify_all.py'], cwd=REPO_ROOT, check=True)
        _prepared_targets.add(summary_path)
    return summary_path


def ensure_cain_summary() -> Path:
    summary_path = REPO_ROOT / 'results' / 'cain_2026_integration_summary.json'
    if summary_path not in _prepared_targets:
        if not summary_path.exists():
            subprocess.run([sys.executable, 'scripts/compare_cain_2026.py'], cwd=REPO_ROOT, check=True)
        _prepared_targets.add(summary_path)
    return summary_path


def ensure_compiler_project_build_summary() -> Path:
    summary_path = REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'build_summary.json'
    if summary_path not in _prepared_targets:
        if not summary_path.exists():
            subprocess.run([sys.executable, 'compiler_verification_project/scripts/build.py'], cwd=REPO_ROOT, check=True)
        _prepared_targets.add(summary_path)
    return summary_path


def ensure_compiler_project_verification_summary() -> Path:
    summary_path = REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'verification_summary.json'
    if summary_path not in _prepared_targets:
        if not summary_path.exists():
            subprocess.run([sys.executable, 'compiler_verification_project/scripts/verify.py', '--cases', '16'], cwd=REPO_ROOT, check=True)
        _prepared_targets.add(summary_path)
    return summary_path
