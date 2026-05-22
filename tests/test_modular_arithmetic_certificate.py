#!/usr/bin/env python3

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT_SRC = REPO_ROOT / 'src'
COMPILER_SRC = REPO_ROOT / 'compiler_verification_project' / 'src'
if str(ROOT_SRC) not in sys.path:
    sys.path.insert(0, str(ROOT_SRC))
if str(COMPILER_SRC) not in sys.path:
    sys.path.insert(0, str(COMPILER_SRC))

from integrity import build_modular_arithmetic_certificate_checks  # noqa: E402
from modular_arithmetic_certificate import build_executable_modular_circuit_ir, build_modular_arithmetic_certificate, pseudo_mersenne_reduce  # noqa: E402
from project import FIELD_BITS, FOLDED_MAG_DOMAIN, arithmetic_lowering_library, leaf_opcode_histogram  # noqa: E402


def _arithmetic_lowerings() -> dict:
    return arithmetic_lowering_library(
        field_bits=FIELD_BITS,
        leaf_opcode_histogram=leaf_opcode_histogram(),
        qroam_domain_size=FOLDED_MAG_DOMAIN,
    )


def _artifacts(certificate: dict, arithmetic_lowerings: dict) -> dict:
    return {
        'modular_arithmetic_certificate': certificate,
        'arithmetic_lowerings': arithmetic_lowerings,
    }


def test_modular_arithmetic_certificate_matches_checked_artifact() -> None:
    checked = json.loads(
        (REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'modular_arithmetic_certificate.json').read_text()
    )
    expected = build_modular_arithmetic_certificate(
        arithmetic_lowerings=_arithmetic_lowerings(),
        field_bits=FIELD_BITS,
    )
    assert checked == expected
    assert checked['pass'] is True


def test_reduced_width_pseudo_mersenne_reduce_matches_modular_product() -> None:
    field_bits = 6
    shift = 3
    low_term = 3
    modulus = (1 << field_bits) - (1 << shift) - low_term
    for left in range(modulus):
        for right in range(modulus):
            trace = pseudo_mersenne_reduce(
                left * right,
                field_bits=field_bits,
                shift=shift,
                low_term=low_term,
                subtract_passes=2,
            )
            assert trace['canonical'] == (left * right) % modulus


def test_executable_modular_circuit_ir_derives_256_bit_opcode_counts() -> None:
    arithmetic_lowerings = _arithmetic_lowerings()
    certificate = build_modular_arithmetic_certificate(
        arithmetic_lowerings=arithmetic_lowerings,
        field_bits=FIELD_BITS,
    )
    ir = certificate['executable_modular_circuit_ir']
    assert ir == build_executable_modular_circuit_ir(
        field_bits=FIELD_BITS,
        shift=certificate['secp256k1_parameters']['shift'],
        low_term=certificate['secp256k1_parameters']['low_term'],
        subtract_passes=certificate['secp256k1_parameters']['canonical_subtract_passes'],
    )
    assert certificate['executable_circuit_ir_count_certificate']['counts_match_arithmetic_lowerings'] is True
    assert ir['non_clifford_by_opcode']['field_add'] == 2 * (FIELD_BITS - 1)
    assert ir['non_clifford_by_opcode']['mul_const'] == 6 * ir['non_clifford_by_opcode']['field_add']
    assert ir['non_clifford_by_opcode']['field_mul'] == certificate['field_mul_stage_count_certificate']['observed_total_ccx']


def test_modular_arithmetic_certificate_detects_forged_stage_count() -> None:
    arithmetic_lowerings = _arithmetic_lowerings()
    certificate = build_modular_arithmetic_certificate(
        arithmetic_lowerings=arithmetic_lowerings,
        field_bits=FIELD_BITS,
    )
    forged = deepcopy(certificate)
    forged['field_mul_stage_count_certificate']['observed_stage_ccx']['pseudo_mersenne_first_fold'] -= 1
    checks = build_modular_arithmetic_certificate_checks(_artifacts(forged, arithmetic_lowerings))
    assert checks['pass'] < checks['total']


def test_modular_arithmetic_certificate_detects_forged_opcode_count() -> None:
    arithmetic_lowerings = _arithmetic_lowerings()
    certificate = build_modular_arithmetic_certificate(
        arithmetic_lowerings=arithmetic_lowerings,
        field_bits=FIELD_BITS,
    )
    forged = deepcopy(certificate)
    forged['opcode_count_certificate']['observed_non_clifford_per_opcode']['field_add'] = FIELD_BITS - 1
    checks = build_modular_arithmetic_certificate_checks(_artifacts(forged, arithmetic_lowerings))
    assert checks['pass'] < checks['total']


def test_modular_arithmetic_certificate_detects_forged_reduced_width_result() -> None:
    arithmetic_lowerings = _arithmetic_lowerings()
    certificate = build_modular_arithmetic_certificate(
        arithmetic_lowerings=arithmetic_lowerings,
        field_bits=FIELD_BITS,
    )
    forged = deepcopy(certificate)
    forged['reduced_width_exhaustive_cases'][0]['pass'] = False
    checks = build_modular_arithmetic_certificate_checks(_artifacts(forged, arithmetic_lowerings))
    assert checks['pass'] < checks['total']


def test_modular_arithmetic_certificate_detects_forged_executable_ir_count() -> None:
    arithmetic_lowerings = _arithmetic_lowerings()
    certificate = build_modular_arithmetic_certificate(
        arithmetic_lowerings=arithmetic_lowerings,
        field_bits=FIELD_BITS,
    )
    forged = deepcopy(certificate)
    forged['executable_circuit_ir_count_certificate']['observed_non_clifford_per_opcode']['field_mul'] -= 1
    checks = build_modular_arithmetic_certificate_checks(_artifacts(forged, arithmetic_lowerings))
    assert checks['pass'] < checks['total']


def test_verify_groups_runs_modular_certificate_without_semantic_replay() -> None:
    result = subprocess.run(
        [
            sys.executable,
            'compiler_verification_project/scripts/verify.py',
            '--groups',
            'modular_arithmetic_certificate_checks',
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert set(payload) == {'modular_arithmetic_certificate_checks'}
    group = payload['modular_arithmetic_certificate_checks']
    assert group['pass'] == group['total']
