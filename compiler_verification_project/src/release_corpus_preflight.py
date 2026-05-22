#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ROOT_SRC = PROJECT_ROOT / 'src'
if str(ROOT_SRC) not in sys.path:
    sys.path.insert(0, str(ROOT_SRC))

from common import (  # noqa: E402
    SECP_B,
    SECP_G,
    SECP_N,
    SECP_P,
    affine_to_proj,
    deterministic_scalars,
    mul_fixed_window,
    precompute_window_tables,
    proj_to_affine,
    sha256_bytes,
)
from lookup_fed_leaf import execute_leaf_contract  # noqa: E402
from proof_corpus_profiles import GOOGLE_COMPARABLE_CASE_COUNT, GOOGLE_COMPARABLE_PROFILE  # noqa: E402


PointAffine = Optional[Tuple[int, int]]


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def _point_payload(point: PointAffine) -> Dict[str, Any]:
    if point is None:
        return {'infinity': True, 'x': None, 'y': None}
    return {'infinity': False, 'x': format(point[0], '064x'), 'y': format(point[1], '064x')}


def _case_category(case_index: int) -> str:
    if case_index % 16 == 0:
        return 'zero_zero'
    if case_index % 16 == 1:
        return 'accumulator_infinity'
    if case_index % 16 == 2:
        return 'lookup_infinity'
    if case_index % 16 == 3:
        return 'doubling'
    if case_index % 16 == 4:
        return 'inverse'
    return 'random'


def _case_scalars(case_index: int, accumulator_scalar: int, lookup_scalar: int) -> tuple[int, int]:
    category = _case_category(case_index)
    if category == 'zero_zero':
        return 0, 0
    if category == 'accumulator_infinity':
        return 0, lookup_scalar
    if category == 'lookup_infinity':
        return accumulator_scalar, 0
    if category == 'doubling':
        return accumulator_scalar, accumulator_scalar
    if category == 'inverse':
        return accumulator_scalar, (-accumulator_scalar) % SECP_N
    return accumulator_scalar, lookup_scalar


def _digest_case(hasher: 'hashlib._Hash', case_payload: Mapping[str, Any]) -> None:
    encoded = _canonical_json(case_payload).encode('ascii')
    hasher.update(len(encoded).to_bytes(8, 'big'))
    hasher.update(encoded)


def build_release_corpus_preflight(
    *,
    leaf: Mapping[str, Any],
    proof_corpus_profiles: Mapping[str, Any],
) -> Dict[str, Any]:
    release_profile = proof_corpus_profiles['profiles'][proof_corpus_profiles['release_profile']]
    case_count = int(release_profile['case_count'])
    case_start = int(release_profile['case_start'])
    leaf_case_seed_sha256 = sha256_bytes(_canonical_json(leaf).encode('ascii'))
    tables = precompute_window_tables(SECP_G, SECP_P, SECP_B, width=8, bits=256)
    seed = bytes.fromhex(leaf_case_seed_sha256)
    scalars = deterministic_scalars(seed + b'compiler-project-zkp-attestation', (case_start + case_count) * 2, SECP_N)
    category_counts: Dict[str, int] = {}
    digest = hashlib.sha256()
    digest.update(b'compiler-project-release-corpus-preflight-v1\n')
    digest.update(leaf_case_seed_sha256.encode('ascii'))
    preview_cases: List[Dict[str, Any]] = []
    tail_cases: List[Dict[str, Any]] = []
    for offset in range(case_count):
        case_index = case_start + offset
        accumulator_scalar, lookup_scalar = _case_scalars(
            case_index,
            scalars[2 * case_index],
            scalars[2 * case_index + 1],
        )
        category = _case_category(case_index)
        accumulator = mul_fixed_window(accumulator_scalar, tables, SECP_P, SECP_B, width=8, order=SECP_N)
        lookup = mul_fixed_window(lookup_scalar, tables, SECP_P, SECP_B, width=8, order=SECP_N)
        expected = proj_to_affine(
            execute_leaf_contract(
                leaf,
                SECP_P,
                affine_to_proj(accumulator, SECP_P),
                lookup,
                0 if lookup is None else 1,
            ),
            SECP_P,
        )
        category_counts[category] = category_counts.get(category, 0) + 1
        case_payload = {
            'case_id': f'{category}_{case_index:04d}',
            'category': category,
            'accumulator': _point_payload(accumulator),
            'lookup': _point_payload(lookup),
            'expected': _point_payload(expected),
        }
        _digest_case(digest, case_payload)
        if len(preview_cases) < 4:
            preview_cases.append(case_payload)
        tail_cases.append(case_payload)
        if len(tail_cases) > 4:
            tail_cases.pop(0)
    expected_categories = {
        'zero_zero',
        'accumulator_infinity',
        'lookup_infinity',
        'doubling',
        'inverse',
        'random',
    }
    checks = {
        'release_profile_is_google_comparable_9024': (
            proof_corpus_profiles['release_profile'] == GOOGLE_COMPARABLE_PROFILE
            and case_count == GOOGLE_COMPARABLE_CASE_COUNT
            and release_profile['release_grade'] is True
        ),
        'all_edge_categories_present': expected_categories.issubset(category_counts),
        'case_count_matches_profile': sum(category_counts.values()) == case_count,
        'leaf_seed_is_canonical_sha256': len(leaf_case_seed_sha256) == 64,
    }
    return {
        'schema': 'compiler-project-release-corpus-preflight-v1',
        'profile': proof_corpus_profiles['release_profile'],
        'profile_role': release_profile['role'],
        'release_grade': bool(release_profile['release_grade']),
        'case_count': case_count,
        'case_start': case_start,
        'leaf_case_seed_sha256': leaf_case_seed_sha256,
        'case_digest_scheme': 'length-prefixed canonical-json rolling sha256 over every release preflight case',
        'case_stream_sha256': digest.hexdigest(),
        'category_counts': dict(sorted(category_counts.items())),
        'preview_head': preview_cases,
        'preview_tail': tail_cases,
        'checks': checks,
        'pass': all(checks.values()),
        'boundary': [
            'This is a fast release-size semantic preflight over the same executable point-add leaf contract; it is not a compressed or Groth16 proof.',
            'The release proof remains stale/missing until proof_status.py reports the compressed and Groth16 layers current for this input.',
        ],
    }


__all__ = ['build_release_corpus_preflight']
