#!/usr/bin/env python3
"""Rebuild the curated proof manifest for the primary artifact package."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from common import dump_json, sha256_path  # noqa: E402


PROOF_MANIFEST_PATHS = [
    'artifacts/README.md',
    'artifacts/out/circuits/optimized_pointadd_secp256k1.json',
    'artifacts/out/circuits/optimized_pointadd_family.json',
    'artifacts/out/circuits/ecdlp_scaffold_optimized.json',
    'artifacts/out/verification/core/optimized_pointadd_audit_16384.csv',
    'artifacts/out/verification/core/toy_curve_exhaustive_19850.csv',
    'artifacts/out/verification/extended/lookup_contract_audit_8192.csv',
    'artifacts/out/verification/extended/scaffold_schedule_audit_256.csv',
    'artifacts/out/verification/extended/toy_curve_family_extended_110692.csv',
    'artifacts/out/projections/resource_projection.json',
    'artifacts/out/projections/projection_sensitivity.json',
    'artifacts/out/projections/meta_analysis.json',
    'artifacts/out/projections/claim_boundary_matrix.json',
    'artifacts/out/projections/optimization_frontier_estimates.json',
    'artifacts/out/verification/core/verification_summary.json',
    'artifacts/out/verification/core/verifier_rebuild_summary.json',
    'artifacts/out/verification/extended/lookup_contract_summary.json',
    'artifacts/out/verification/extended/scaffold_schedule_summary.json',
    'artifacts/out/verification/extended/toy_curve_family_extended_summary.json',
    'artifacts/figures/core/instruction_mix.png',
    'artifacts/figures/core/qubit_comparison.png',
    'artifacts/figures/core/toffoli_comparison.png',
    'artifacts/figures/core/verification_stack.png',
    'artifacts/figures/core/window_schedule.png',
    'artifacts/figures/core/progression_instruction_count.png',
    'artifacts/figures/core/progression_register_count.png',
    'artifacts/figures/core/projection_headroom.png',
    'artifacts/figures/research/verification_coverage_extended.png',
    'artifacts/figures/research/optimization_frontier_ranges.png',
    'reports/secp256k1_optimized_report.pdf',
    'src/verifier.py',
    'src/extended_verifier.py',
    'scripts/generate_figures.py',
]


def main() -> None:
    files = {}
    for rel in PROOF_MANIFEST_PATHS:
        path = REPO_ROOT / rel
        files[rel] = {
            'sha256': sha256_path(path),
            'bytes': path.stat().st_size,
        }

    proof_manifest = {
        'artifact_family': 'secp256k1_optimized_kickmix_v2',
        'base_dir': 'repository_root',
        'notes': [
            'This manifest records the main optimized artifact files after the publication-hardening pass.',
            'Paths are repository-relative.',
        ],
        'files': files,
    }
    out_path = REPO_ROOT / 'artifacts' / 'out' / 'package' / 'proof_manifest.json'
    dump_json(out_path, proof_manifest)
    print(f'Wrote {out_path}')


if __name__ == '__main__':
    main()
