from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
COMPILER_SRC = REPO_ROOT / 'compiler_verification_project' / 'src'
ROOT_SRC = REPO_ROOT / 'src'
if str(COMPILER_SRC) not in sys.path:
    sys.path.insert(0, str(COMPILER_SRC))
if str(ROOT_SRC) not in sys.path:
    sys.path.insert(0, str(ROOT_SRC))

from modular_accumulator_promotion_options import (  # noqa: E402
    MODULAR_ACCUMULATOR_PROMOTION_OPTIONS_SCHEMA,
    OPTION_CURRENT_SYNTHETIC_SCRATCH,
    OPTION_FORWARD_ONLY_CARRY_SAVE,
    OPTION_LOCAL_ONE_BIT_WITNESS,
    OPTION_LOCAL_TWO_BIT_WITNESS,
    OPTION_SOURCE_UNCOMPUTE,
    PROMOTION_OPTIONS_UNPROMOTED_STATUS,
    STATUS_INVALID_RESOURCE_CONTRACT,
    STATUS_ONLY_REMAINING_UNPROVEN,
    STATUS_REJECTED_HEADLINE_QUBITS,
    STATUS_REJECTED_NON_INJECTIVE,
    build_modular_accumulator_promotion_options,
)


ARTIFACT_DIR = REPO_ROOT / 'compiler_verification_project' / 'artifacts'


def _load(name: str) -> dict:
    return json.loads((ARTIFACT_DIR / name).read_text())


def _build() -> dict:
    return build_modular_accumulator_promotion_options(
        primary_strict_result=_load('primary_strict_result.json'),
        modular_primitive_wire_audit=_load('modular_primitive_wire_audit.json'),
        modular_accumulator_full_adder_liveness=_load('modular_accumulator_full_adder_liveness.json'),
        modular_accumulator_full_adder_reversibility=_load('modular_accumulator_full_adder_reversibility.json'),
    )


def test_modular_accumulator_promotion_options_reconstructs_checked_artifact() -> None:
    assert _load('modular_accumulator_promotion_options.json') == _build()


def test_modular_accumulator_promotion_options_rejects_local_carry_save_paths() -> None:
    options = _load('modular_accumulator_promotion_options.json')
    statuses = {row['name']: row['status'] for row in options['options']}

    assert options['schema'] == MODULAR_ACCUMULATOR_PROMOTION_OPTIONS_SCHEMA
    assert options['pass'] is True
    assert options['scratch_placeholder']['abandoned_scratch_wire_observations'] == options['scratch_placeholder']['synthetic_scratch_wire_observations']
    assert statuses[OPTION_CURRENT_SYNTHETIC_SCRATCH] == STATUS_INVALID_RESOURCE_CONTRACT
    assert statuses[OPTION_FORWARD_ONLY_CARRY_SAVE] == STATUS_REJECTED_HEADLINE_QUBITS
    assert statuses[OPTION_LOCAL_TWO_BIT_WITNESS] == STATUS_REJECTED_HEADLINE_QUBITS
    assert statuses[OPTION_LOCAL_ONE_BIT_WITNESS] == STATUS_REJECTED_NON_INJECTIVE
    assert statuses[OPTION_SOURCE_UNCOMPUTE] == STATUS_ONLY_REMAINING_UNPROVEN
    assert options['carry_save_local_bounds']['local_witness_sequential_peak_lower_bound'] > options['current_public_headline']['logical_qubits']
    assert options['promotion_status']['status'] == PROMOTION_OPTIONS_UNPROMOTED_STATUS
