#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC = PROJECT_ROOT / 'compiler_verification_project' / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from materialized_circuit import available_family_names, resolve_selected_family_names, write_materialized_family_circuit  # noqa: E402
from project import compiler_family_frontier  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Materialize exact generated whole-oracle operation streams for named compiler families.')
    parser.add_argument('--family', action='append', default=[], help='Family name to materialize. Supports best-gate and best-qubit aliases.')
    parser.add_argument('--all-families', action='store_true', help='Materialize all exact compiler families.')
    parser.add_argument('--output-dir', default='compiler_verification_project/generated_circuits', help='Ignored output directory for generated circuit dumps.')
    parser.add_argument('--no-gzip', action='store_true', help='Write plain TSV instead of operations.tsv.gz.')
    parser.add_argument('--list-families', action='store_true', help='Print the available family names and exit.')
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    frontier = compiler_family_frontier()
    if args.list_families:
        print(json.dumps({
            'available_families': available_family_names(frontier),
            'best_gate_family': frontier['best_gate_family']['name'],
            'best_qubit_family': frontier['best_qubit_family']['name'],
        }, indent=2))
        return
    output_root = PROJECT_ROOT / args.output_dir
    family_names = resolve_selected_family_names(args.family, include_all=args.all_families, frontier=frontier)
    manifests = [
        write_materialized_family_circuit(
            family_name=family_name,
            output_root=output_root,
            frontier=frontier,
            gzip_output=not args.no_gzip,
        )
        for family_name in family_names
    ]
    print(json.dumps({
        'output_dir': str(output_root.relative_to(PROJECT_ROOT)),
        'families': manifests,
    }, indent=2))


if __name__ == '__main__':
    main()
