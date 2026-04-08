from __future__ import annotations

import itertools
import json
import subprocess
import sys
from pathlib import Path

from support import ensure_compiler_project_build_summary


REPO_ROOT = Path(__file__).resolve().parents[1]
COMPILER_SRC = REPO_ROOT / 'compiler_verification_project' / 'src'
if str(COMPILER_SRC) not in sys.path:
    sys.path.insert(0, str(COMPILER_SRC))

from materialized_circuit import iter_family_operation_stream, resolve_selected_family_names  # noqa: E402


def _frontier() -> dict:
    ensure_compiler_project_build_summary()
    return json.loads((REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'family_frontier.json').read_text())


def test_materialized_family_aliases_resolve_to_frontier_rows() -> None:
    frontier = _frontier()
    resolved = resolve_selected_family_names(['best-gate', 'best-qubit'], frontier=frontier)
    assert resolved[0] == frontier['best_gate_family']['name']
    assert resolved[1] == frontier['best_qubit_family']['name']


def test_materialized_operation_stream_emits_seed_lookup_rows() -> None:
    frontier = _frontier()
    family_name = frontier['best_gate_family']['name']
    preview = list(itertools.islice(iter_family_operation_stream(family_name, frontier=frontier), 16))
    assert preview
    assert all(row['family'] == family_name for row in preview)
    assert all(row['scope'] == 'direct_seed' for row in preview[:8])
    assert all(row['gate'] in {'ccx', 'measurement'} for row in preview)


def test_materialized_circuit_script_lists_available_families() -> None:
    output = subprocess.check_output(
        [sys.executable, 'compiler_verification_project/scripts/materialize_exact_circuits.py', '--list-families'],
        cwd=REPO_ROOT,
        text=True,
    )
    payload = json.loads(output)
    assert payload['best_gate_family']
    assert payload['best_qubit_family']
    assert len(payload['available_families']) == 6
