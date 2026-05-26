#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
COMPILER_SRC = REPO_ROOT / 'compiler_verification_project' / 'src'
ROOT_SRC = REPO_ROOT / 'src'
if str(ROOT_SRC) not in sys.path:
    sys.path.insert(0, str(ROOT_SRC))
if str(COMPILER_SRC) not in sys.path:
    sys.path.insert(0, str(COMPILER_SRC))

from qroam_table_cnot_materialization import build_qroam_table_cnot_materialization  # noqa: E402


def _table_manifests() -> dict:
    return json.loads((REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'table_manifests.json').read_text())


def test_qroam_table_cnot_materialization_classifies_toy_domain_sites() -> None:
    domain_size = 8
    target_bits = 155
    payload = build_qroam_table_cnot_materialization(
        table_manifests=_table_manifests(),
        raw32_schedule={
            'leaf_calls': [
                {
                    'call_index': 0,
                    'phase_register': 'phase_a',
                    'window_index_within_register': 1,
                },
            ],
        },
        reusable_chunk_lowering={
            'stream_plan': {
                'chunk_bits': target_bits,
                'chunk_count': 2,
                'leaf_call_count_total': 1,
                'whole_oracle_chunk_streams': 6,
            },
        },
        qroam_primitive_certificate={
            'parameters': {
                'domain_size': domain_size,
                'segment_size': 4,
            },
            'operation_stream': {
                'segment_count': 4,
            },
            'target_bit_load_site_stream': {
                'potential_cnot_site_count': domain_size * target_bits * 2,
            },
        },
        field_bits=256,
    )
    assert payload['pass'] is True
    assert payload['totals']['chunk_stream_count'] == 6
    assert payload['totals']['segment_count'] == 24
    assert payload['totals']['full_oracle_potential_target_bit_sites'] == 6 * domain_size * target_bits * 2
    assert payload['totals']['full_oracle_effective_target_bit_sites'] == 3 * domain_size * (155 + 101) * 2
    assert payload['totals']['full_oracle_zero_padded_target_bit_sites'] == 3 * domain_size * (155 - 101) * 2
    assert 0 < payload['totals']['full_oracle_emitted_clifford_cx'] < payload['totals']['full_oracle_effective_target_bit_sites']
    assert len(payload['segment_merkle_root_sha256']) == 64
