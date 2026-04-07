#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from common import artifact_core_verification_path, dump_json, relative_file_manifest, sha256_path
from verifier import run_audit, run_toy


PROOF_MANIFEST_PATHS = [
    'artifacts/README.md',
    'artifacts/circuits/optimized_pointadd_secp256k1.json',
    'artifacts/circuits/optimized_pointadd_family.json',
    'artifacts/circuits/ecdlp_scaffold_optimized.json',
    'artifacts/circuits/ecdlp_expanded_isa_optimized.json',
    'artifacts/verification/core/optimized_pointadd_audit_16384.csv',
    'artifacts/verification/core/toy_curve_exhaustive_19850.csv',
    'artifacts/verification/extended/scaffold_schedule_audit_256.csv',
    'artifacts/verification/extended/toy_curve_family_extended_110692.csv',
    'artifacts/projections/resource_projection.json',
    'artifacts/projections/structural_accounting.json',
    'artifacts/projections/backend_model_bundle.json',
    'artifacts/projections/projection_sensitivity.json',
    'artifacts/projections/meta_analysis.json',
    'artifacts/projections/claim_boundary_matrix.json',
    'artifacts/projections/optimization_frontier_estimates.json',
    'artifacts/verification/core/verification_summary.json',
    'artifacts/verification/core/verifier_rebuild_summary.json',
    'artifacts/verification/extended/lookup_contract_summary.json',
    'artifacts/verification/extended/scaffold_schedule_summary.json',
    'artifacts/verification/extended/toy_curve_family_extended_summary.json',
    'figures/core/instruction_mix.png',
    'figures/core/qubit_comparison.png',
    'figures/core/toffoli_comparison.png',
    'figures/core/verification_stack.png',
    'figures/core/window_schedule.png',
    'figures/core/progression_instruction_count.png',
    'figures/core/progression_register_count.png',
    'figures/core/projection_headroom.png',
    'figures/research/verification_coverage_extended.png',
    'figures/research/optimization_frontier_ranges.png',
    'src/verifier.py',
    'src/extended_verifier.py',
    'src/figure_generation.py',
    'src/resource_projection.py',
    'src/derived_resources.py',
    'compiler_verification_project/README.md',
    'compiler_verification_project/src/project.py',
    'compiler_verification_project/scripts/build.py',
    'compiler_verification_project/scripts/verify.py',
    'compiler_verification_project/artifacts/build_summary.json',
    'compiler_verification_project/artifacts/family_frontier.json',
    'compiler_verification_project/artifacts/full_raw32_oracle.json',
    'compiler_verification_project/artifacts/exact_leaf_slot_allocation.json',
    'compiler_verification_project/artifacts/primitive_multiplier_library.json',
    'compiler_verification_project/artifacts/phase_shell_families.json',
    'compiler_verification_project/artifacts/verification_summary.json',
    'compiler_verification_project/artifacts/cain_exact_transfer.json',
    'compiler_verification_project/artifacts/azure_resource_estimator_logical_counts.json',
]


def write_verifier_rebuild_summary(repo_root: Path) -> Dict[str, Any]:
    package_dir = repo_root / 'artifacts'
    summary = {
        'audit': run_audit(package_dir),
        'toy': run_toy(package_dir),
    }
    dump_json(artifact_core_verification_path(package_dir, 'verifier_rebuild_summary.json'), summary)
    return summary


def write_proof_manifest(repo_root: Path) -> Dict[str, Any]:
    files = {}
    for relative_path in PROOF_MANIFEST_PATHS:
        path = repo_root / relative_path
        files[relative_path] = {
            'sha256': sha256_path(path),
            'bytes': path.stat().st_size,
        }

    proof_manifest = {
        'artifact_family': 'secp256k1_mainline_plus_exact_compiler_v1',
        'base_dir': 'repository_root',
        'notes': [
            'This manifest records the main optimized artifact files plus the exact compiler-family subproject artifacts.',
            'Paths are repository-relative.',
        ],
        'files': files,
    }
    dump_json(repo_root / 'artifacts' / 'package' / 'proof_manifest.json', proof_manifest)
    return proof_manifest


def write_repository_manifest(repo_root: Path) -> None:
    manifest = relative_file_manifest(repo_root)
    lines = [f"{record['sha256']}  {relative_path}" for relative_path, record in manifest.items()]
    (repo_root / 'MANIFEST.sha256').write_text('\n'.join(lines) + '\n')
