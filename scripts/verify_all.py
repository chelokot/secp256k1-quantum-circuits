#!/usr/bin/env python3
"""Run the full repository verification pipeline."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from common import artifact_core_verification_path, dump_json, load_json, sha256_path  # noqa: E402
from extended_verifier import (  # noqa: E402
    run_claim_boundary_matrix,
    run_coherent_cleanup,
    run_extended_toy_family,
    run_lookup_contract,
    run_scaffold_schedule,
)
from research_extensions import build_challenge_ladder, run_challenge_ladder_audit  # noqa: E402
from resource_projection import write_resource_projection  # noqa: E402
from verifier import run_audit, run_toy  # noqa: E402


AUDIT_CATEGORY_DESCRIPTIONS = {
    'random': 'random accumulator / lookup pairs',
    'doubling': 'same-point addition cases',
    'inverse': 'point-plus-inverse to infinity',
    'accumulator_infinity': 'accumulator starts at infinity',
    'lookup_infinity': 'lookup point is infinity',
}


class Console:
    def __init__(self, color: bool):
        self.color = color

    def style(self, text: str, code: str) -> str:
        if not self.color:
            return text
        return f'\033[{code}m{text}\033[0m'

    def heading(self, text: str) -> str:
        return self.style(text, '1;36')

    def ok(self, text: str) -> str:
        return self.style(text, '1;32')

    def fail(self, text: str) -> str:
        return self.style(text, '1;31')

    def dim(self, text: str) -> str:
        return self.style(text, '2')

    def detail(self, text: str) -> str:
        return self.style(text, '37')


class ProgressReporter:
    def __init__(self, console: Console, enabled: bool):
        self.console = console
        self.enabled = enabled
        self.interactive = enabled and sys.stdout.isatty() and console.color

    def start(self, step: int, total_steps: int, title: str) -> None:
        return

    def advance(self, step: int, total_steps: int, title: str, completed: int, total: int, passed: int) -> None:
        if not self.enabled:
            return
        width = 24
        filled = 0 if total == 0 else int(width * completed / total)
        bar = '#' * filled + '-' * (width - filled)
        line = f'[{step}/{total_steps}] {title} [{bar}] {completed:,}/{total:,}'
        if self.interactive:
            print(f'\r{line}', end='', flush=True)
            if completed == total:
                print()
        else:
            if completed == 0 or completed == total or completed % 2048 == 0:
                print(line, flush=True)

    def done(self, step: int, total_steps: int, title: str, status: str) -> None:
        return


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run the repository verification path.')
    parser.add_argument('--json', action='store_true', help='Print the raw JSON summary instead of the human-readable view.')
    parser.add_argument('--no-color', action='store_true', help='Disable ANSI colors in the human-readable output.')
    parser.add_argument('--quick', action='store_true', help='Run only the core secp256k1 and toy-curve checks.')
    return parser.parse_args()


def build_extended_summary(repo_root: Path, progress: ProgressReporter, step: int, total_steps: int) -> Dict[str, Any]:
    return {
        'lookup_contract': run_lookup_contract(
            repo_root,
            progress=lambda completed, total: progress.advance(step, total_steps, 'Running lookup-contract audit', completed, total, completed),
        ),
        'coherent_cleanup': run_coherent_cleanup(
            repo_root,
            progress=lambda completed, total: progress.advance(step + 1, total_steps, 'Running coherent cleanup audit', completed, total, completed),
        ),
        'scaffold_schedule': run_scaffold_schedule(
            repo_root,
            progress=lambda completed, total: progress.advance(step + 2, total_steps, 'Running scaffold replay audit', completed, total, completed),
        ),
        'toy_extended': run_extended_toy_family(
            repo_root,
            progress=lambda completed, total: progress.advance(step + 3, total_steps, 'Running extended toy-family check', completed, total, completed),
        ),
        'claim_boundaries': run_claim_boundary_matrix(repo_root),
        'challenge_ladder': run_challenge_ladder_audit(
            repo_root,
            build_challenge_ladder(),
            progress=lambda completed, total: progress.advance(step + 4, total_steps, 'Running challenge-ladder replay', completed, total, completed),
        ),
    }


def build_compiler_project_summary(repo_root: Path) -> Dict[str, Any]:
    subprocess.run([sys.executable, 'compiler_verification_project/scripts/build.py'], cwd=repo_root, check=True, stdout=subprocess.DEVNULL)
    subprocess.run([sys.executable, 'compiler_verification_project/scripts/verify.py', '--cases', '16'], cwd=repo_root, check=True, stdout=subprocess.DEVNULL)
    build_path = repo_root / 'compiler_verification_project' / 'artifacts' / 'build_summary.json'
    verify_path = repo_root / 'compiler_verification_project' / 'artifacts' / 'verification_summary.json'
    frontier_path = repo_root / 'compiler_verification_project' / 'artifacts' / 'family_frontier.json'
    cain_path = repo_root / 'compiler_verification_project' / 'artifacts' / 'cain_exact_transfer.json'
    physical_targets_path = repo_root / 'compiler_verification_project' / 'artifacts' / 'azure_resource_estimator_targets.json'
    physical_results_path = repo_root / 'compiler_verification_project' / 'artifacts' / 'azure_resource_estimator_results.json'
    return {
        'build_summary': load_json(build_path),
        'verification_summary': load_json(verify_path),
        'frontier': load_json(frontier_path),
        'cain_transfer': load_json(cain_path),
        'physical_estimator_targets': load_json(physical_targets_path),
        'physical_estimator_results': load_json(physical_results_path),
        'build_summary_sha256': sha256_path(build_path),
        'verification_summary_sha256': sha256_path(verify_path),
        'frontier_sha256': sha256_path(frontier_path),
        'cain_transfer_sha256': sha256_path(cain_path),
        'physical_estimator_targets_sha256': sha256_path(physical_targets_path),
        'physical_estimator_results_sha256': sha256_path(physical_results_path),
    }


def build_summary(console: Console, show_progress: bool, quick: bool) -> Dict[str, Any]:
    optimized_root = REPO_ROOT / 'artifacts'
    step_count = 2 if quick else 9
    progress = ProgressReporter(console, enabled=show_progress)
    write_resource_projection(REPO_ROOT)

    audit_title = 'Running deterministic secp256k1 audit'
    progress.start(1, step_count, audit_title)
    audit = run_audit(
        optimized_root,
        progress=lambda completed, total, passed: progress.advance(1, step_count, audit_title, completed, total, passed),
    )
    progress.done(1, step_count, audit_title, 'done')

    toy_title = 'Running toy-curve finite-model check'
    progress.start(2, step_count, toy_title)
    toy = run_toy(
        optimized_root,
        progress=lambda completed, total, passed: progress.advance(2, step_count, toy_title, completed, total, passed),
    )
    progress.done(2, step_count, toy_title, 'done')

    optimized = {
        'audit': audit,
        'toy': toy,
    }
    optimized['verification_summary_sha256'] = sha256_path(artifact_core_verification_path(optimized_root, 'verification_summary.json'))
    extended = None
    compiler_project = None
    if not quick:
        extended = build_extended_summary(REPO_ROOT, progress, 3, step_count)
        compiler_project = build_compiler_project_summary(REPO_ROOT)
    google_baseline = (
        compiler_project['frontier']['public_google_baseline']
        if compiler_project is not None
        else {
            'low_qubit': {'logical_qubits': 1200, 'non_clifford': 90_000_000},
            'low_gate': {'logical_qubits': 1450, 'non_clifford': 70_000_000},
        }
    )

    summary = {
        'optimized': optimized,
        'google_baseline': google_baseline,
        'headline_checks': {
            'optimized_audit_pass': optimized['audit']['summary']['pass'] == optimized['audit']['summary']['total'] == 16384,
            'optimized_toy_pass': optimized['toy']['summary']['pass'] == optimized['toy']['summary']['total'] == 19850,
            'google_baseline_present': (
                google_baseline['low_qubit']['logical_qubits'] == 1200
                and google_baseline['low_qubit']['non_clifford'] == 90_000_000
                and google_baseline['low_gate']['logical_qubits'] == 1450
                and google_baseline['low_gate']['non_clifford'] == 70_000_000
            ),
        },
    }
    if extended is not None:
        summary['extended'] = extended
        lookup = extended['lookup_contract']['summary']
        cleanup = extended['coherent_cleanup']['summary']
        summary['headline_checks']['extended_checks_pass'] = (
            lookup['parameter_checks']['pass'] == lookup['parameter_checks']['total']
            and lookup['canonical_full_exhaustive']['pass'] == lookup['canonical_full_exhaustive']['total']
            and lookup['multibase_direct_samples']['pass'] == lookup['multibase_direct_samples']['total']
            and cleanup['pass'] == cleanup['total']
            and extended['scaffold_schedule']['summary']['pass'] == extended['scaffold_schedule']['summary']['total']
            and extended['toy_extended']['summary']['pass'] == extended['toy_extended']['summary']['total']
            and extended['challenge_ladder']['summary']['pass'] == extended['challenge_ladder']['summary']['total']
        )
    if compiler_project is not None:
        summary['compiler_project'] = compiler_project
        compiler_verify = compiler_project['verification_summary']
        compiler_build = compiler_project['build_summary']
        compiler_frontier = compiler_project['frontier']
        summary['headline_checks']['compiler_exact_checks_pass'] = (
            compiler_verify['summary']['semantic_cases']['pass'] == compiler_verify['summary']['semantic_cases']['total']
            and compiler_verify['summary']['invariant_checks']['pass'] == compiler_verify['summary']['invariant_checks']['total']
            and compiler_build['headline']['best_gate_family'] == compiler_frontier['best_gate_family']
            and compiler_build['headline']['best_qubit_family'] == compiler_frontier['best_qubit_family']
        )
    return summary


def print_human_summary(summary: Dict[str, Any], console: Console, quick: bool) -> None:
    optimized = summary['optimized']
    extended = summary.get('extended')
    compiler_project = summary.get('compiler_project')
    total_sections = 2 + (5 if extended is not None else 0) + (2 if compiler_project is not None else 0)
    audit = optimized['audit']['summary']
    toy = optimized['toy']['summary']
    baseline = summary['google_baseline']
    checks = summary['headline_checks']

    print(console.heading('Repository verification'))
    if quick:
        print(console.dim('quick mode: results/repo_verification_summary.json was left unchanged'))
    else:
        print(console.dim('results/repo_verification_summary.json was rebuilt'))
    print()

    section = 1
    print(f"[{section}/{total_sections}] Deterministic secp256k1 audit  {console.ok('PASS') if checks['optimized_audit_pass'] else console.fail('FAIL')}")
    print(console.detail(f"      {audit['pass']:,} / {audit['total']:,} cases passed"))
    print(console.detail("      checks the exact point-add leaf on secp256k1 with Q <- Q + L against independent reference paths"))
    for category in ('random', 'doubling', 'inverse', 'accumulator_infinity', 'lookup_infinity'):
        category_summary = audit['categories'][category]
        description = AUDIT_CATEGORY_DESCRIPTIONS[category]
        print(console.detail(f"      - {category}: {category_summary['pass']:,} / {category_summary['total']:,}  {description}"))
    print(console.detail(f"      audit sha256: {optimized['audit']['sha256']}"))
    print(console.detail(f"      netlist sha256: {optimized['audit']['netlist_sha256']}"))
    print()

    section += 1
    toy_pass = toy['pass'] == toy['total']
    print(f"[{section}/{total_sections}] Toy-curve finite-model check   {console.ok('PASS') if toy_pass else console.fail('FAIL')}")
    print(console.detail(f"      {toy['pass']:,} / {toy['total']:,} cases passed"))
    print(console.detail("      exhaustively checks the same point-add leaf semantics over two small prime-order j=0 toy curves"))
    for curve_name, curve_summary in toy['curves'].items():
        print(console.detail(
            f"      - {curve_name}: {curve_summary['pass']:,} / {curve_summary['total']:,}  "
            f"order={curve_summary['order']}, p={curve_summary['p']}, b={curve_summary['b']}"
        ))
    print(console.detail(f"      toy sha256: {optimized['toy']['sha256']}"))
    print()

    if extended is not None:
        lookup = extended['lookup_contract']['summary']
        cleanup = extended['coherent_cleanup']['summary']
        scaffold = extended['scaffold_schedule']['summary']
        toy_extended = extended['toy_extended']['summary']
        lookup_pass = (
            lookup['parameter_checks']['pass'] == lookup['parameter_checks']['total']
            and lookup['canonical_full_exhaustive']['pass'] == lookup['canonical_full_exhaustive']['total']
            and lookup['multibase_direct_samples']['pass'] == lookup['multibase_direct_samples']['total']
        )
        section += 1
        print(f"[{section}/{total_sections}] Lookup-contract audit       {console.ok('PASS') if lookup_pass else console.fail('FAIL')}")
        print(console.detail(
            f"      contract checks: {lookup['parameter_checks']['pass']:,} / {lookup['parameter_checks']['total']:,} machine-readable parameter checks"
        ))
        print(console.detail(
            f"      canonical exhaustive: {lookup['canonical_full_exhaustive']['pass']:,} / {lookup['canonical_full_exhaustive']['total']:,} cases on {lookup['canonical_full_exhaustive']['base_id']}"
        ))
        print(console.detail(
            f"      multibase samples: {lookup['multibase_direct_samples']['pass']:,} / {lookup['multibase_direct_samples']['total']:,} across {lookup['multibase_direct_samples']['base_count']} bases"
        ))
        print(console.detail(f"      lookup summary sha256: {extended['lookup_contract']['sha256']}"))
        print()

        section += 1
        print(f"[{section}/{total_sections}] Coherent cleanup audit     {console.ok('PASS') if cleanup['pass'] == cleanup['total'] else console.fail('FAIL')}")
        print(console.detail(f"      cleanup replay: {cleanup['pass']:,} / {cleanup['total']:,} cases cleared the flag and preserved the selected projective state"))
        for category in ('random', 'doubling', 'inverse', 'accumulator_infinity', 'lookup_infinity'):
            category_summary = cleanup['categories'][category]
            description = AUDIT_CATEGORY_DESCRIPTIONS[category]
            print(console.detail(f"      - {category}: {category_summary['pass']:,} / {category_summary['total']:,}  {description}"))
        print(console.detail(f"      cleanup summary sha256: {extended['coherent_cleanup']['sha256']}"))
        print()

        section += 1
        print(f"[{section}/{total_sections}] Scaffold replay audit       {console.ok('PASS') if scaffold['pass'] == scaffold['total'] else console.fail('FAIL')}")
        print(console.detail(f"      scaffold replay: {scaffold['pass']:,} / {scaffold['total']:,} retained-window replay cases"))
        print(console.detail(f"      scaffold sha256: {extended['scaffold_schedule']['sha256']}"))
        print()

        section += 1
        print(f"[{section}/{total_sections}] Extended toy-family check   {console.ok('PASS') if toy_extended['pass'] == toy_extended['total'] else console.fail('FAIL')}")
        print(console.detail(f"      extended toy family: {toy_extended['pass']:,} / {toy_extended['total']:,} exhaustive cases across four toy curves"))
        print(console.detail(f"      extended toy sha256: {extended['toy_extended']['sha256']}"))
        print()

        challenge_ladder = extended['challenge_ladder']['summary']
        section += 1
        print(f"[{section}/{total_sections}] Challenge-ladder replay     {console.ok('PASS') if challenge_ladder['pass'] == challenge_ladder['total'] else console.fail('FAIL')}")
        print(console.detail(
            f"      challenge ladder: {challenge_ladder['pass']:,} / {challenge_ladder['total']:,} replay cases across {challenge_ladder['curve_count']} deterministic benchmark curves"
        ))
        print()

    if compiler_project is not None:
        compiler_verify = compiler_project['verification_summary']
        frontier = compiler_project['frontier']
        section += 1
        print(f"[{section}/{total_sections}] Exact compiler build        {console.ok('PASS')}")
        print(console.detail(f"      best exact gate family: {frontier['best_gate_family']['full_oracle_non_clifford']:,} non-Clifford"))
        print(console.detail(f"      best exact qubit family: {frontier['best_qubit_family']['total_logical_qubits']:,} logical qubits"))
        print(console.detail(f"      best exact qubit family name: {frontier['best_qubit_family']['name']}"))
        print(console.detail(f"      frontier sha256: {compiler_project['frontier_sha256']}"))
        print()

        section += 1
        exact_pass = (
            compiler_verify['summary']['semantic_cases']['pass'] == compiler_verify['summary']['semantic_cases']['total']
            and compiler_verify['summary']['invariant_checks']['pass'] == compiler_verify['summary']['invariant_checks']['total']
        )
        print(f"[{section}/{total_sections}] Exact compiler verification {console.ok('PASS') if exact_pass else console.fail('FAIL')}")
        print(console.detail(
            f"      semantic replay: {compiler_verify['summary']['semantic_cases']['pass']:,} / {compiler_verify['summary']['semantic_cases']['total']:,} cases"
        ))
        print(console.detail(
            f"      integrity checks: {compiler_verify['summary']['invariant_checks']['pass']:,} / {compiler_verify['summary']['invariant_checks']['total']:,} (canonical point + schedule + slot allocation + lowered arithmetic/lookup/phase shell + generated inventories + FT IR + whole-oracle recount + subcircuit equivalence + frontier + physical-estimator handoffs + transfer handoffs)"
        ))
        print(console.detail(f"      verification sha256: {compiler_project['verification_summary_sha256']}"))
        print(console.detail(
            f"      physical estimator targets/results sha256: {compiler_project['physical_estimator_targets_sha256']} / {compiler_project['physical_estimator_results_sha256']}"
        ))
        print()

    if compiler_project is not None:
        best_exact_gate = compiler_project['frontier']['best_gate_family']
        best_exact_qubit = compiler_project['frontier']['best_qubit_family']
        print(console.heading('Exact compiler-project frontier'))
        print(f"  best exact gate family: {best_exact_gate['full_oracle_non_clifford']:,} non-Clifford / {best_exact_gate['total_logical_qubits']:,} q")
        print(f"  best exact qubit family: {best_exact_qubit['total_logical_qubits']:,} q / {best_exact_qubit['full_oracle_non_clifford']:,} non-Clifford")
        print(f"  public baseline: {baseline['low_qubit']['logical_qubits']:,} q / {baseline['low_qubit']['non_clifford']:,} and {baseline['low_gate']['logical_qubits']:,} q / {baseline['low_gate']['non_clifford']:,}")
        print()
        print(console.heading('Exact comparison to Google 2026 baseline'))
        print(f"  best exact gate family vs low-qubit line: {best_exact_gate['improvement_vs_google_low_qubit']:.4f}x lower non-Clifford")
        print(f"  best exact gate family vs low-gate line:  {best_exact_gate['improvement_vs_google_low_gate']:.4f}x lower non-Clifford")
        print(f"  best exact qubit family vs low-qubit line: {baseline['low_qubit']['logical_qubits'] - best_exact_qubit['total_logical_qubits']:+,} q margin")
        print(f"  best exact qubit family vs low-gate line:  {baseline['low_gate']['logical_qubits'] - best_exact_qubit['total_logical_qubits']:+,} q margin")


def main() -> None:
    args = parse_args()
    console = Console(color=not args.no_color and sys.stdout.isatty())
    summary = build_summary(console, show_progress=not args.json, quick=args.quick)
    if not args.quick:
        dump_json(REPO_ROOT / 'results' / 'repo_verification_summary.json', summary)
    if args.json:
        print(json.dumps(summary, indent=2))
        return

    print_human_summary(summary, console, args.quick)


if __name__ == '__main__':
    main()
