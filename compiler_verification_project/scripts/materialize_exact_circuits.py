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

from materialized_circuit import available_family_names, resolve_selected_family_names, write_materialized_family_circuit, write_public_candidate_flat_netlist  # noqa: E402
from project import compiler_family_frontier  # noqa: E402


def checked_frontier_artifact() -> dict | None:
    path = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts' / 'family_frontier.json'
    if not path.exists():
        return None
    return json.loads(path.read_text())


def checked_public_candidate_materialized_artifact() -> dict:
    path = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts' / 'public_candidate_materialized_circuit_manifest.json'
    return json.loads(path.read_text())


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Materialize exact generated whole-oracle operation streams for named compiler families.')
    parser.add_argument('--family', action='append', default=[], help='Family name to materialize. Supports best-gate and best-qubit aliases.')
    parser.add_argument('--all-families', action='store_true', help='Materialize all exact compiler families.')
    parser.add_argument('--output-dir', default='compiler_verification_project/generated_circuits', help='Ignored output directory for generated circuit dumps.')
    parser.add_argument('--no-gzip', action='store_true', help='Write plain TSV instead of operations.tsv.gz.')
    parser.add_argument('--list-families', action='store_true', help='Print the available family names and exit.')
    parser.add_argument('--public-candidate-flat-netlist', action='store_true', help='Stream the current public-candidate flat primitive netlist from the checked materialized manifest.')
    parser.add_argument('--slice-start', type=int, default=0, help='First operation index to export for --public-candidate-flat-netlist.')
    parser.add_argument('--slice-count', type=int, default=None, help='Optional operation count to export for --public-candidate-flat-netlist.')
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    frontier = checked_frontier_artifact() if args.list_families else None
    if frontier is None:
        frontier = compiler_family_frontier()
    if args.list_families:
        print(json.dumps({
            'available_families': available_family_names(frontier),
            'best_gate_family': frontier['best_gate_family']['name'],
            'best_qubit_family': frontier['best_qubit_family']['name'],
        }, indent=2))
        return
    output_root = PROJECT_ROOT / args.output_dir
    if args.public_candidate_flat_netlist:
        manifest = checked_public_candidate_materialized_artifact()
        stop = None if args.slice_count is None else int(args.slice_start) + int(args.slice_count)
        suffix = 'tsv.gz' if not args.no_gzip else 'tsv'
        output_path = output_root / 'public_candidate_flat_netlist' / f'operations.{suffix}'
        export_manifest = write_public_candidate_flat_netlist(
            manifest,
            output_path,
            gzip_output=not args.no_gzip,
            start=int(args.slice_start),
            stop=stop,
        )
        print(json.dumps({
            'output_dir': display_path(output_root),
            'public_candidate_flat_netlist': {
                **export_manifest,
                'path': display_path(output_path),
            },
        }, indent=2))
        return
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
        'output_dir': display_path(output_root),
        'families': manifests,
    }, indent=2))


if __name__ == '__main__':
    main()
