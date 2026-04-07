from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def ensure_repo_verification_summary() -> Path:
    summary_path = REPO_ROOT / 'results' / 'repo_verification_summary.json'
    if not summary_path.exists():
        subprocess.run([sys.executable, 'scripts/verify_all.py'], cwd=REPO_ROOT, check=True)
    return summary_path
