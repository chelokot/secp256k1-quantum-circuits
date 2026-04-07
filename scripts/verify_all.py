#!/usr/bin/env python3
"""Run the full repository verification pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from common import artifact_core_verification_path, artifact_projection_path, dump_json, load_json, sha256_path  # noqa: E402
from extended_verifier import (  # noqa: E402
    run_claim_boundary_matrix,
    run_extended_toy_family,
    run_lookup_contract,
    run_meta_analysis,
    run_projection_sensitivity,
    run_scaffold_schedule,
)
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
    title = 'Running extended supporting checks'
    total = 6
    completed = 0

    def mark_done() -> None:
        nonlocal completed
        completed += 1
        progress.advance(step, total_steps, title, completed, total, completed)

    progress.advance(step, total_steps, title, 0, total, 0)
    lookup_contract = run_lookup_contract(repo_root)
    mark_done()
    scaffold_schedule = run_scaffold_schedule(repo_root)
    mark_done()
    toy_extended = run_extended_toy_family(repo_root)
    mark_done()
    projection_sensitivity = run_projection_sensitivity(repo_root)
    mark_done()
    meta_analysis = run_meta_analysis(repo_root)
    mark_done()
    claim_boundaries = run_claim_boundary_matrix(repo_root)
    mark_done()

    return {
        'lookup_contract': lookup_contract,
        'scaffold_schedule': scaffold_schedule,
        'toy_extended': toy_extended,
        'projection_sensitivity': projection_sensitivity,
        'meta_analysis': meta_analysis,
        'claim_boundaries': claim_boundaries,
    }


def build_summary(console: Console, show_progress: bool, quick: bool) -> Dict[str, Any]:
    optimized_root = REPO_ROOT / 'artifacts'
    step_count = 2 if quick else 3
    progress = ProgressReporter(console, enabled=show_progress)

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
    optimized['resource_projection'] = load_json(artifact_projection_path(optimized_root, 'resource_projection.json'))
    optimized['resource_projection_sha256'] = sha256_path(artifact_projection_path(optimized_root, 'resource_projection.json'))
    google_baseline = optimized['resource_projection']['public_google_baseline']
    extended = None
    if not quick:
        extended = build_extended_summary(REPO_ROOT, progress, 3, step_count)

    summary = {
        'optimized': optimized,
        'google_baseline': google_baseline,
        'headline_checks': {
            'optimized_audit_pass': optimized['audit']['summary']['pass'] == optimized['audit']['summary']['total'] == 16384,
            'optimized_toy_pass': optimized['toy']['summary']['pass'] == optimized['toy']['summary']['total'] == 19850,
            'google_baseline_present': bool(google_baseline['source']) and google_baseline['window_size'] == 16 and google_baseline['retained_window_additions'] == 28,
        },
    }
    if extended is not None:
        summary['extended'] = extended
        summary['headline_checks']['extended_checks_pass'] = (
            extended['lookup_contract']['summary']['signed_i16']['pass'] == extended['lookup_contract']['summary']['signed_i16']['total']
            and extended['lookup_contract']['summary']['unsigned_u16']['pass'] == extended['lookup_contract']['summary']['unsigned_u16']['total']
            and extended['scaffold_schedule']['summary']['pass'] == extended['scaffold_schedule']['summary']['total']
            and extended['toy_extended']['summary']['pass'] == extended['toy_extended']['summary']['total']
        )
    return summary


def print_human_summary(summary: Dict[str, Any], console: Console, quick: bool) -> None:
    optimized = summary['optimized']
    extended = summary.get('extended')
    total_sections = 3 if extended is not None else 2
    audit = optimized['audit']['summary']
    toy = optimized['toy']['summary']
    projection = optimized['resource_projection']
    baseline = summary['google_baseline']
    checks = summary['headline_checks']

    print(console.heading('Repository verification'))
    if quick:
        print(console.dim('quick mode: results/repo_verification_summary.json was left unchanged'))
    else:
        print(console.dim('results/repo_verification_summary.json was rebuilt'))
    print()

    print(f"[1/{total_sections}] Deterministic secp256k1 audit  {console.ok('PASS') if checks['optimized_audit_pass'] else console.fail('FAIL')}")
    print(console.detail(f"      {audit['pass']:,} / {audit['total']:,} cases passed"))
    print(console.detail("      checks the exact point-add leaf on secp256k1 with Q <- Q + L against independent reference paths"))
    for category in ('random', 'doubling', 'inverse', 'accumulator_infinity', 'lookup_infinity'):
        category_summary = audit['categories'][category]
        description = AUDIT_CATEGORY_DESCRIPTIONS[category]
        print(console.detail(f"      - {category}: {category_summary['pass']:,} / {category_summary['total']:,}  {description}"))
    print(console.detail(f"      audit sha256: {optimized['audit']['sha256']}"))
    print(console.detail(f"      netlist sha256: {optimized['audit']['netlist_sha256']}"))
    print()

    toy_pass = toy['pass'] == toy['total']
    print(f"[2/{total_sections}] Toy-curve finite-model check   {console.ok('PASS') if toy_pass else console.fail('FAIL')}")
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
        scaffold = extended['scaffold_schedule']['summary']
        toy_extended = extended['toy_extended']['summary']
        extended_pass = summary['headline_checks']['extended_checks_pass']
        print(f"[3/{total_sections}] Extended supporting checks  {console.ok('PASS') if extended_pass else console.fail('FAIL')}")
        print(console.detail(
            f"      lookup contract: {lookup['signed_i16']['pass'] + lookup['unsigned_u16']['pass']:,} / "
            f"{lookup['signed_i16']['total'] + lookup['unsigned_u16']['total']:,} deterministic signed/unsigned cases"
        ))
        print(console.detail(
            f"      scaffold replay: {scaffold['pass']:,} / {scaffold['total']:,} retained-window replay cases"
        ))
        print(console.detail(
            f"      extended toy family: {toy_extended['pass']:,} / {toy_extended['total']:,} exhaustive cases across four toy curves"
        ))
        print(console.detail(f"      lookup sha256: {extended['lookup_contract']['sha256']}"))
        print(console.detail(f"      scaffold sha256: {extended['scaffold_schedule']['sha256']}"))
        print(console.detail(f"      extended toy sha256: {extended['toy_extended']['sha256']}"))
        print()

    print(console.heading('Primary modeled projection'))
    print(f"  logical qubits: {projection['optimized_ecdlp_projection']['logical_qubits_total']:,}")
    print(f"  2-channel total: {projection['optimized_ecdlp_projection']['lookup_model_2channel']['total_non_clifford']:,} non-Clifford")
    print(f"  3-channel total: {projection['optimized_ecdlp_projection']['lookup_model_3channel']['total_non_clifford']:,} non-Clifford")
    print(f"  public baseline: {baseline['low_qubit']['logical_qubits']:,} q / {baseline['low_qubit']['non_clifford']:,} and {baseline['low_gate']['logical_qubits']:,} q / {baseline['low_gate']['non_clifford']:,}")
    print()

    print(console.heading('Advantage vs Google 2026 secp256k1 estimates'))
    low_qubit_2channel = console.ok(f"{projection['improvement_vs_google']['versus_low_qubit']['toffoli_gain_2lookup']:.4f}x")
    low_qubit_3channel = console.ok(f"{projection['improvement_vs_google']['versus_low_qubit']['toffoli_gain_3lookup']:.4f}x")
    low_gate_2channel = console.ok(f"{projection['improvement_vs_google']['versus_low_gate']['toffoli_gain_2lookup']:.4f}x")
    low_gate_3channel = console.ok(f"{projection['improvement_vs_google']['versus_low_gate']['toffoli_gain_3lookup']:.4f}x")
    print(f"  lower modeled non-Clifford cost vs Google low-qubit line: {low_qubit_2channel} (2-channel), {low_qubit_3channel} (3-channel)")
    print(f"  lower modeled non-Clifford cost vs Google low-gate line:  {low_gate_2channel} (2-channel), {low_gate_3channel} (3-channel)")


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
