#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cain_integration import write_cain_integration_summary  # noqa: E402
from figure_generation import write_figures  # noqa: E402
from maintenance import write_proof_manifest, write_repository_manifest, write_verifier_rebuild_summary  # noqa: E402
from research_extensions import run_research_pass  # noqa: E402
from resource_projection import write_resource_projection  # noqa: E402


def main() -> None:
    write_resource_projection(REPO_ROOT)
    write_verifier_rebuild_summary(REPO_ROOT)
    run_research_pass(REPO_ROOT)
    subprocess.run([sys.executable, 'compiler_verification_project/scripts/build.py'], cwd=REPO_ROOT, check=True)
    subprocess.run([sys.executable, 'compiler_verification_project/scripts/verify.py', '--cases', '16'], cwd=REPO_ROOT, check=True)
    subprocess.run([sys.executable, 'scripts/verify_all.py'], cwd=REPO_ROOT, check=True)
    write_cain_integration_summary(REPO_ROOT)
    write_figures(REPO_ROOT)
    write_proof_manifest(REPO_ROOT)
    write_repository_manifest(REPO_ROOT)
    print('Refreshed repository artifacts.')


if __name__ == '__main__':
    main()
