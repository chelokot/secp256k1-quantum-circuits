#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
COMPILER_SRC = REPO_ROOT / 'compiler_verification_project' / 'src'
ROOT_SRC = REPO_ROOT / 'src'
for path in (COMPILER_SRC, ROOT_SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scheduled_modular_primitive_netlist import SCHEDULED_MODULAR_PRIMITIVE_NETLIST_SCHEMA, build_scheduled_modular_primitive_netlist  # noqa: E402


def _artifact(name: str) -> dict:
    return json.loads((REPO_ROOT / 'compiler_verification_project' / 'artifacts' / name).read_text())


def _build(
    *,
    modular_execution_trace: dict | None = None,
    modular_arithmetic_certificate: dict | None = None,
    arithmetic_lowerings: dict | None = None,
) -> dict:
    return build_scheduled_modular_primitive_netlist(
        modular_execution_trace=modular_execution_trace or _artifact('modular_execution_trace.json'),
        modular_arithmetic_certificate=modular_arithmetic_certificate or _artifact('modular_arithmetic_certificate.json'),
        arithmetic_lowerings=arithmetic_lowerings or _artifact('arithmetic_lowerings.json'),
    )


def test_scheduled_modular_primitive_netlist_reconstructs_checked_artifact() -> None:
    expected = _artifact('scheduled_modular_primitive_netlist.json')
    observed = _build()
    assert observed == expected
    assert expected['schema'] == SCHEDULED_MODULAR_PRIMITIVE_NETLIST_SCHEMA
    assert expected['pass'] is True
    assert expected['operation_count'] == 1204598
    assert expected['non_clifford_count'] == 1126842
    assert expected['primitive_counts_total'] == {'ccx': 1126842, 'cx': 0, 'x': 0, 'measurement': 77756}
    assert expected['segment_count'] == 74
    assert len(expected['operation_stream_sha256']) == 64


def test_scheduled_modular_primitive_netlist_rejects_forged_trace_count() -> None:
    trace = deepcopy(_artifact('modular_execution_trace.json'))
    trace['trace_rows'][0]['suboperations'][0]['primitive_counts_total']['ccx'] += 1
    observed = _build(modular_execution_trace=trace)
    assert observed['pass'] is False
    assert observed['checks']['all_suboperation_counts_match_trace'] is False
    assert observed['checks']['total_counts_match_trace_suboperations'] is False


def test_scheduled_modular_primitive_netlist_rejects_stale_certificate() -> None:
    certificate = deepcopy(_artifact('modular_arithmetic_certificate.json'))
    certificate['pass'] = False
    observed = _build(modular_arithmetic_certificate=certificate)
    assert observed['pass'] is False
    assert observed['checks']['modular_arithmetic_certificate_passes'] is False
