#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TEST_WEIGHTS = {
    'tests/test_compiler_verification_project.py': 12,
    'tests/test_verification_pipeline.py': 8,
    'tests/test_extended_artifacts.py': 6,
    'tests/test_release_inventory.py': 5,
    'tests/test_whole_oracle_recount.py': 4,
    'tests/test_subcircuit_equivalence.py': 4,
    'tests/test_ft_ir.py': 4,
    'tests/test_generated_block_inventory.py': 4,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run repository tests with optional multicore parallelism.')
    parser.add_argument('--jobs', default='auto', help='Parallel worker count. Use auto, 1, or a positive integer.')
    parser.add_argument('tests', nargs='*', help='Optional test files or pytest selectors.')
    return parser.parse_args()


def _resolve_jobs(value: str, test_count: int) -> int:
    if value == 'auto':
        cpu_count = os.cpu_count() or 1
        return max(1, min(4, cpu_count, test_count))
    return max(1, int(value))


def _collect_test_files(selected: list[str]) -> list[str]:
    if selected:
        return selected
    return sorted(str(path.relative_to(REPO_ROOT)) for path in (REPO_ROOT / 'tests').glob('test_*.py'))


def _weight(test_path: str) -> int:
    return TEST_WEIGHTS.get(test_path, 2)


def _partition(test_files: list[str], jobs: int) -> list[list[str]]:
    groups: list[list[str]] = [[] for _ in range(jobs)]
    loads = [0 for _ in range(jobs)]
    for test_path in sorted(test_files, key=_weight, reverse=True):
        index = min(range(jobs), key=lambda item: loads[item])
        groups[index].append(test_path)
        loads[index] += _weight(test_path)
    return [group for group in groups if group]


def _run(command: list[str], env: dict[str, str] | None = None) -> None:
    subprocess.run(command, cwd=REPO_ROOT, check=True, env=env)


def _prewarm_artifacts() -> None:
    _run([sys.executable, 'scripts/refresh_repo.py'])
    _run([sys.executable, 'scripts/compare_cain_2026.py'])


def main() -> None:
    args = parse_args()
    test_files = _collect_test_files(args.tests)
    jobs = _resolve_jobs(args.jobs, len(test_files))
    if jobs == 1:
        _run([sys.executable, '-m', 'pytest', '-q', *test_files])
        return

    _prewarm_artifacts()
    env = dict(os.environ)
    env['SECP256K1_OPEN_AUDIT_REUSE_ARTIFACTS'] = '1'
    groups = _partition(test_files, jobs)
    processes: list[tuple[list[str], subprocess.Popen[str]]] = []
    for group in groups:
        process = subprocess.Popen(
            [sys.executable, '-m', 'pytest', '-q', *group],
            cwd=REPO_ROOT,
            env=env,
            text=True,
        )
        processes.append((group, process))

    failed = False
    for group, process in processes:
        return_code = process.wait()
        if return_code != 0:
            failed = True
            print(f'parallel pytest group failed: {group}', file=sys.stderr)
    if failed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
