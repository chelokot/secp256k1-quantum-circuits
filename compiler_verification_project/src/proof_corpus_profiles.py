#!/usr/bin/env python3

from __future__ import annotations

from typing import Any, Dict

PROOF_CORPUS_PROFILE_SCHEMA = 'compiler-project-proof-corpus-profiles-v1'
SMOKE_PUBLIC_PROFILE = 'smoke_public_8'
GOOGLE_COMPARABLE_PROFILE = 'google_comparable_9024'


def build_proof_corpus_profiles() -> Dict[str, Any]:
    profiles = {
        SMOKE_PUBLIC_PROFILE: {
            'case_count': 8,
            'case_start': 0,
            'role': 'current public smoke attestation',
            'release_grade': False,
        },
        GOOGLE_COMPARABLE_PROFILE: {
            'case_count': 9024,
            'case_start': 0,
            'role': 'Google-disclosure-size public corpus target',
            'release_grade': True,
        },
    }
    selected = profiles[SMOKE_PUBLIC_PROFILE]
    checks = {
        'selected_public_profile_exists': SMOKE_PUBLIC_PROFILE in profiles,
        'google_comparable_profile_exists': GOOGLE_COMPARABLE_PROFILE in profiles,
        'selected_public_profile_is_explicit_smoke': selected['case_count'] == 8 and selected['release_grade'] is False,
        'google_comparable_profile_is_release_grade': profiles[GOOGLE_COMPARABLE_PROFILE]['case_count'] == 9024 and profiles[GOOGLE_COMPARABLE_PROFILE]['release_grade'] is True,
    }
    return {
        'schema': PROOF_CORPUS_PROFILE_SCHEMA,
        'selected_public_profile': SMOKE_PUBLIC_PROFILE,
        'release_profile': GOOGLE_COMPARABLE_PROFILE,
        'profiles': profiles,
        'checks': checks,
        'pass': all(checks.values()),
        'boundary': [
            'The current checked public proof profile is an explicit 8-case smoke attestation.',
            'The Google-comparable release target is tracked as a separate 9024-case profile and must be rebuilt before claiming Google-equivalent proof confidence.',
        ],
    }


def selected_public_case_count() -> int:
    profiles = build_proof_corpus_profiles()
    return int(profiles['profiles'][profiles['selected_public_profile']]['case_count'])


__all__ = [
    'GOOGLE_COMPARABLE_PROFILE',
    'PROOF_CORPUS_PROFILE_SCHEMA',
    'SMOKE_PUBLIC_PROFILE',
    'build_proof_corpus_profiles',
    'selected_public_case_count',
]
