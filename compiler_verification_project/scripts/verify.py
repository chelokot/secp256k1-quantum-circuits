#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC = PROJECT_ROOT / 'compiler_verification_project' / 'src'
ROOT_SRC = PROJECT_ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT_SRC) not in sys.path:
    sys.path.insert(0, str(ROOT_SRC))

from integrity import (  # noqa: E402
    build_integrity_report,
    load_compiler_artifacts,
    refresh_verification_summary_groups,
    refresh_verification_summary_integrity,
    write_verification_summary,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run compiler-project semantic verification.')
    parser.add_argument('--cases', type=int, default=32, help='Deterministic case count for the raw-32 semantic replay.')
    parser.add_argument(
        '--groups',
        nargs='+',
        help='Run only named integrity groups without semantic replay or rewriting verification_summary.json.',
    )
    parser.add_argument(
        '--summary',
        action='store_true',
        help='With --groups, print only group pass/total counts instead of full check payloads.',
    )
    parser.add_argument(
        '--refresh-integrity',
        action='store_true',
        help='Rewrite verification_summary.json by reusing and rechecking the checked semantic replay artifact.',
    )
    parser.add_argument(
        '--refresh-groups',
        nargs='+',
        help='Rewrite verification_summary.json by refreshing only named groups plus semantic replay artifact checks.',
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.refresh_groups:
        payload = refresh_verification_summary_groups(args.refresh_groups, repo_root=PROJECT_ROOT)
        print(json.dumps({
            'summary': payload['summary'],
            'semantic_replay': payload['semantic_replay']['summary'],
            'refreshed_groups': args.refresh_groups,
            'artifact': 'compiler_verification_project/artifacts/verification_summary.json',
            'semantic_replay_mode': 'checked-artifact-reused',
        }, indent=2))
        return
    if args.refresh_integrity:
        payload = refresh_verification_summary_integrity(repo_root=PROJECT_ROOT)
        print(json.dumps({
            'summary': payload['summary'],
            'semantic_replay': payload['semantic_replay']['summary'],
            'artifact': 'compiler_verification_project/artifacts/verification_summary.json',
            'semantic_replay_mode': 'checked-artifact-reused',
        }, indent=2))
        return
    if args.groups:
        artifacts = load_compiler_artifacts(PROJECT_ROOT)
        payload = build_integrity_report(PROJECT_ROOT, artifacts, group_names=args.groups)
        if args.summary:
            output = {
                name: {
                    'pass': group['pass'],
                    'total': group['total'],
                }
                for name, group in payload.items()
            }
        else:
            output = payload
        print(json.dumps(output, indent=2, sort_keys=True))
        failed_groups = [
            name
            for name, group in payload.items()
            if isinstance(group, dict) and group.get('pass') != group.get('total')
        ]
        if failed_groups:
            raise SystemExit(1)
        return
    payload = write_verification_summary(case_count=args.cases)
    print(json.dumps({
        'summary': payload['summary'],
        'semantic_replay': payload['semantic_replay']['summary'],
        'artifact': 'compiler_verification_project/artifacts/verification_summary.json',
    }, indent=2))


if __name__ == '__main__':
    main()
