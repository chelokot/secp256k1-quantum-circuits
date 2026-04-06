#!/usr/bin/env python3
"""Run the full repository verification pipeline.

This is the simplest end-user entrypoint.  It rebuilds the optimized package,
replays the archived exact package, checks expected headline hashes, and writes a
combined summary to `results/repo_verification_summary.json`.
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
from verify_exact_archive import replay_exact_audit, verify_manifest, verify_scaffold, verify_toy_summary  # noqa: E402


def main() -> None:
    optimized_root = REPO_ROOT / 'artifacts' / 'optimized'
    exact_root = REPO_ROOT / 'artifacts' / 'exact_kickmix'

    optimized = {
        'audit': run_audit(optimized_root),
        'toy': run_toy(optimized_root),
    }
    optimized['verification_summary_sha256'] = sha256_path(optimized_root / 'out' / 'verification_summary.json')
    optimized['resource_projection'] = load_json(optimized_root / 'out' / 'resource_projection.json')

    archived_exact = {
        'manifest': verify_manifest(REPO_ROOT),
        'scaffold': verify_scaffold(REPO_ROOT),
        'audit_replay': replay_exact_audit(REPO_ROOT),
        'toy_summary': verify_toy_summary(REPO_ROOT),
        'proof_manifest_sha256': sha256_path(exact_root / 'out' / 'proof_manifest.json'),
    }

    summary = {
        'optimized': optimized,
        'archived_exact': archived_exact,
        'headline_checks': {
            'optimized_audit_pass': optimized['audit']['summary']['pass'] == optimized['audit']['summary']['total'] == 16384,
            'optimized_toy_pass': optimized['toy']['summary']['pass'] == optimized['toy']['summary']['total'] == 19850,
            'exact_archive_pass': archived_exact['audit_replay']['failed_rows'] == 0,
            'exact_scaffold_hash_link_pass': archived_exact['scaffold']['oracle_hash_matches_netlist'],
        },
    }
    out_path = REPO_ROOT / 'results' / 'repo_verification_summary.json'
    dump_json(out_path, summary)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
