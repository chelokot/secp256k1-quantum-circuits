#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ROOT_SRC = PROJECT_ROOT / 'src'
if str(ROOT_SRC) not in sys.path:
    sys.path.insert(0, str(ROOT_SRC))

from arithmetic_lowering import DEFAULT_QROAM_CLEAN_BLOCK_SIZE
from common import SECP_B, SECP_G, SECP_N, SECP_P, sha256_bytes
from reusable_chunk_tail_candidate import PRODUCTION_CHUNK_BITS, PRODUCTION_CHUNK_COUNT

COMPILER_PARAMETERS_SCHEMA = 'compiler-project-parameters-v1'
PUBLIC_HEADLINE_NON_CLIFFORD_LIMIT_EXCLUSIVE = 40_000_000
PUBLIC_HEADLINE_LOGICAL_QUBIT_LIMIT_EXCLUSIVE = 1200


def _digest_payload(payload: Dict[str, Any]) -> str:
    return sha256_bytes(json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode())


def build_compiler_parameters() -> Dict[str, Any]:
    payload = {
        'schema': COMPILER_PARAMETERS_SCHEMA,
        'curve': {
            'name': 'secp256k1',
            'field_modulus_hex': format(SECP_P, '064x'),
            'scalar_order_hex': format(SECP_N, '064x'),
            'curve_b': SECP_B,
            'generator_x_hex': format(SECP_G[0], '064x'),
            'generator_y_hex': format(SECP_G[1], '064x'),
        },
        'field': {
            'field_bits': SECP_P.bit_length(),
            'pseudo_mersenne_shift': 32,
            'pseudo_mersenne_low_term': 977,
            'canonical_subtract_passes': 2,
        },
        'windowing': {
            'raw_window_bits': 16,
            'full_raw_windows': 32,
            'folded_magnitude_bits': 15,
            'folded_magnitude_domain': 1 << 15,
            'fixed_window_width': 8,
        },
        'phase_shell': {
            'full_phase_register_bits': 512,
            'selected_public_shell': 'semiclassical_qft_v1',
        },
        'lookup_policy': {
            'selected_public_lookup_family': 'folded_standard_qroam_streamed_coordinate_v1',
            'standard_qroamclean_block_size': DEFAULT_QROAM_CLEAN_BLOCK_SIZE,
        },
        'reusable_chunk_policy': {
            'chunk_bits': PRODUCTION_CHUNK_BITS,
            'chunk_count': PRODUCTION_CHUNK_COUNT,
            'scratch_slot': 'qchunk',
        },
        'public_headline_policy': {
            'selected_public_family_name': 'folded_standard_qroam_reusable_chunked_coordinate_v1__reusable_chunk_tail_leaf_v1__semiclassical_qft_v1',
            'non_clifford_limit_exclusive': PUBLIC_HEADLINE_NON_CLIFFORD_LIMIT_EXCLUSIVE,
            'logical_qubit_limit_exclusive': PUBLIC_HEADLINE_LOGICAL_QUBIT_LIMIT_EXCLUSIVE,
            'proof_freshness_required_for_public_pass': True,
        },
    }
    checks = {
        'field_modulus_has_declared_bit_width': int(payload['field']['field_bits']) == 256,
        'pseudo_mersenne_identity_matches_modulus': SECP_P == (1 << 256) - (1 << 32) - 977,
        'folded_domain_matches_magnitude_bits': payload['windowing']['folded_magnitude_domain'] == (1 << payload['windowing']['folded_magnitude_bits']),
        'raw_window_span_matches_scalar_width': payload['windowing']['raw_window_bits'] * payload['windowing']['full_raw_windows'] == 512,
        'qroamclean_selected_block_size_is_k1': payload['lookup_policy']['standard_qroamclean_block_size'] == 1,
        'reusable_chunk_policy_covers_field_width': payload['reusable_chunk_policy']['chunk_bits'] * payload['reusable_chunk_policy']['chunk_count'] >= payload['field']['field_bits'],
        'selected_public_family_matches_reusable_chunk_policy': 'reusable_chunk_tail_leaf_v1' in payload['public_headline_policy']['selected_public_family_name'],
        'public_headline_limits_are_strict': payload['public_headline_policy']['non_clifford_limit_exclusive'] == 40_000_000 and payload['public_headline_policy']['logical_qubit_limit_exclusive'] == 1200,
    }
    payload['checks'] = checks
    payload['pass'] = all(checks.values())
    payload['parameter_digest_sha256'] = _digest_payload({
        key: payload[key]
        for key in ('schema', 'curve', 'field', 'windowing', 'phase_shell', 'lookup_policy', 'reusable_chunk_policy', 'public_headline_policy')
    })
    return payload


__all__ = [
    'COMPILER_PARAMETERS_SCHEMA',
    'PUBLIC_HEADLINE_LOGICAL_QUBIT_LIMIT_EXCLUSIVE',
    'PUBLIC_HEADLINE_NON_CLIFFORD_LIMIT_EXCLUSIVE',
    'build_compiler_parameters',
]
