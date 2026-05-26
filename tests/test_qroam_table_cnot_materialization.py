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

from qroam_table_cnot_materialization import build_qroam_table_cnot_materialization, decode_segment_emitted_cx  # noqa: E402


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
    assert len(payload['row_index_contract_merkle_root_sha256']) == 64
    assert len(payload['row_decoder_sample_merkle_root_sha256']) == 64
    assert payload['checks']['emitted_cx_operation_ranges_cover_total'] is True
    assert payload['checks']['emitted_cx_probes_are_within_effective_target_bits'] is True
    assert payload['checks']['rank_checkpoints_cover_every_segment'] is True
    assert payload['checks']['row_index_contract_domains_match_ranges'] is True
    assert payload['checks']['row_decoder_samples_are_exact_table_cnot_rows'] is True
    assert payload['totals']['rank_checkpoint_count'] > payload['totals']['segment_count']
    assert payload['totals']['row_decoder_sample_count'] > 0
    emitted_segments = [segment for segment in payload['segments'] if segment['emitted_cx_count'] > 0]
    assert emitted_segments
    first_sample = emitted_segments[0]['first_emitted_cx']
    last_sample = emitted_segments[-1]['last_emitted_cx']
    assert first_sample['global_emitted_cx_index'] == emitted_segments[0]['emitted_cx_operation_start']
    assert last_sample['global_emitted_cx_index'] == emitted_segments[-1]['emitted_cx_operation_end_exclusive'] - 1
    assert first_sample['control_wire'] == f"qroam_unary_match_control[{first_sample['address']}]"
    assert first_sample['target_wire'] == f"qroam_target.bit[{first_sample['target_bit_index']}]"
    segment = next(candidate for candidate in emitted_segments if candidate['emitted_cx_count'] >= 3)
    decoded = decode_segment_emitted_cx(
        segment=segment,
        base=(int(_table_manifests()['phase_a_bases'][1]['base_x_hex'], 16), int(_table_manifests()['phase_a_bases'][1]['base_y_hex'], 16)),
        local_emitted_cx_index=segment['emitted_cx_count'] // 2,
        field_bits=256,
        chunk_bits=target_bits,
    )
    assert decoded['operation'] == 'cx'
    assert decoded['global_emitted_cx_index'] == segment['emitted_cx_operation_start'] + segment['emitted_cx_count'] // 2
    assert segment['start_address'] <= decoded['address'] < segment['end_address_exclusive']
    assert ((decoded['chunk_value'] >> decoded['target_bit_index']) & 1) == 1
    assert decoded['control_wire'] == f"qroam_unary_match_control[{decoded['address']}]"
    assert decoded['target_wire'] == f"qroam_target.bit[{decoded['target_bit_index']}]"
