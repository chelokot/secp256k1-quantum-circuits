#!/usr/bin/env python3
"""Run the full repository verification pipeline.

This is the simplest end-user entrypoint. It rebuilds the optimized package,
checks the cited rounded Google baseline stored in the projection file, and
writes a combined summary to `results/repo_verification_summary.json`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from common import dump_json, load_json, sha256_path  # noqa: E402
from verifier import run_audit, run_toy  # noqa: E402


def main() -> None:
    optimized_root = REPO_ROOT / 'artifacts'

    optimized = {
        'audit': run_audit(optimized_root),
        'toy': run_toy(optimized_root),
    }
    optimized['verification_summary_sha256'] = sha256_path(optimized_root / 'out' / 'verification_summary.json')
    optimized['resource_projection'] = load_json(optimized_root / 'out' / 'resource_projection.json')
    optimized['resource_projection_sha256'] = sha256_path(optimized_root / 'out' / 'resource_projection.json')
    google_baseline = optimized['resource_projection']['public_google_baseline']

    summary = {
        'optimized': optimized,
        'google_baseline': google_baseline,
        'headline_checks': {
            'optimized_audit_pass': optimized['audit']['summary']['pass'] == optimized['audit']['summary']['total'] == 16384,
            'optimized_toy_pass': optimized['toy']['summary']['pass'] == optimized['toy']['summary']['total'] == 19850,
            'google_baseline_present': bool(google_baseline['source']) and google_baseline['window_size'] == 16 and google_baseline['retained_window_additions'] == 28,
        },
    }
    out_path = REPO_ROOT / 'results' / 'repo_verification_summary.json'
    dump_json(out_path, summary)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
