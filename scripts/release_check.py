#!/usr/bin/env python3
"""One-shot publication readiness check."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

COMMANDS = [
    [sys.executable, 'scripts/rebuild_resource_projection.py'],
    [sys.executable, 'src/verifier.py', '--package-dir', 'artifacts', '--mode', 'all'],
    [sys.executable, 'scripts/verify_all.py'],
    [sys.executable, 'scripts/run_research_pass.py'],
    [sys.executable, 'scripts/generate_figures.py'],
    [sys.executable, 'scripts/rebuild_proof_manifest.py'],
    [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
    [sys.executable, 'scripts/compare_google_baseline.py'],
    [sys.executable, 'scripts/compare_cain_2026.py'],
    [sys.executable, 'scripts/compare_literature.py'],
    [sys.executable, 'scripts/compare_lookup_research.py'],
    [sys.executable, 'scripts/hash_repo.py'],
]

def main() -> None:
    for cmd in COMMANDS:
        print('$', ' '.join(cmd))
        subprocess.run(cmd, cwd=REPO_ROOT, check=True)
    print('Publication readiness check complete.')

if __name__ == '__main__':
    main()
