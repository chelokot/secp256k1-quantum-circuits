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

from current_baseline_status import (  # noqa: E402
    CURRENT_BASELINE_STATUS_SCHEMA,
    STATUS_GUARD_CORRECTED_NOT_PROMOTED,
    STATUS_NO_ACCEPTED_PHYSICAL_BASELINE,
    build_current_baseline_status,
)


ARTIFACT_DIR = REPO_ROOT / 'compiler_verification_project' / 'artifacts'


def _load(name: str) -> dict:
    return json.loads((ARTIFACT_DIR / name).read_text())


def _build() -> dict:
    return build_current_baseline_status(
        strict_replayed_tail_headline=_load('strict_replayed_tail_headline.json'),
        public_headline_result=_load('public_headline_result.json'),
        primary_strict_result=_load('primary_strict_result.json'),
        engine_completion_audit=_load('engine_completion_audit.json'),
        zero_lift_guard_resource_audit=_load('zero_lift_guard_resource_audit.json'),
        modular_accumulator_source_uncompute=_load('modular_accumulator_source_uncompute.json'),
    )


def test_current_baseline_status_reconstructs_checked_artifact() -> None:
    assert _load('current_baseline_status.json') == _build()


def test_current_baseline_status_blocks_unpromoted_resource_numbers() -> None:
    status = _load('current_baseline_status.json')

    assert status['schema'] == CURRENT_BASELINE_STATUS_SCHEMA
    assert status['pass'] is True
    assert status['status'] == STATUS_NO_ACCEPTED_PHYSICAL_BASELINE
    assert status['accepted_physical_baseline'] is None
    assert status['current_strict_candidate']['logical_qubits'] == 1968
    assert status['current_strict_candidate']['status'] == 'not_accepted_as_physical_baseline'
    assert status['guard_corrected_no_alias_candidate']['status'] == STATUS_GUARD_CORRECTED_NOT_PROMOTED
    assert status['guard_corrected_no_alias_candidate']['derivation']['strict_candidate_logical_qubits'] == 1968
    assert status['guard_corrected_no_alias_candidate']['derivation']['additional_logical_qubits_if_no_aliasing_proof'] == 254
    assert status['guard_corrected_no_alias_candidate']['logical_qubits'] == 2222
    assert status['publication_policy']['may_publish_resource_headline_as_physical_baseline'] is False
    assert status['conservative_hardening_target']['status'] == 'repo_presentation_target_not_accepted_physical_baseline'
    assert status['conservative_hardening_target']['source'] == 'guard_corrected_no_alias_candidate'
    assert status['conservative_hardening_target']['logical_qubits'] == 2222
    assert status['conservative_hardening_target']['non_clifford'] == status['guard_corrected_no_alias_candidate']['non_clifford']
    assert status['publication_policy']['default_docs_resource_target_before_acceptance'] == 'conservative_hardening_target'
    assert status['publication_policy']['default_docs_logical_qubits_before_acceptance'] == 2222


def test_current_baseline_status_names_the_remaining_physical_blockers() -> None:
    status = _load('current_baseline_status.json')
    blockers = {row['name']: row for row in status['remaining_physical_baseline_blockers']}

    assert set(blockers) == {
        'zero_lift_guard_capacity_not_promoted',
        'modular_accumulator_source_uncompute_not_promoted',
        'modular_arithmetic_clifford_expansion_not_flattened',
    }
    assert blockers['zero_lift_guard_capacity_not_promoted']['missing_logical_qubits_under_clean_ladder'] == 254
    assert blockers['modular_accumulator_source_uncompute_not_promoted']['partial_product_cleanup_ccx_proven'] == 720896
    assert blockers['modular_accumulator_source_uncompute_not_promoted']['guard_cleanup_ccx_missing_source_controls'] == 510
    assert blockers['modular_arithmetic_clifford_expansion_not_flattened']['engine_clifford_complete_goal_achieved'] is False


def test_current_baseline_status_has_an_explicit_baseline_acceptance_gate() -> None:
    status = _load('current_baseline_status.json')
    gate = status['accepted_baseline_gate']
    rows = {row['name']: row for row in gate['rows']}

    assert gate['status'] == 'blocked'
    assert gate['decision'] == 'do_not_promote_any_resource_number_to_accepted_physical_baseline'
    assert gate['candidate_under_review'] == 'guard_corrected_no_alias_candidate'
    assert gate['candidate_under_review_logical_qubits'] == 2222
    assert gate['policy'].startswith('accepted_physical_baseline may be populated only when every gate row passes')
    assert set(rows) == {
        'single_authoritative_primitive_stream',
        'guard_corrected_no_alias_capacity_promoted_into_liveness',
        'modular_accumulator_source_uncompute_promoted',
        'no_abandoned_synthetic_arithmetic_scratch',
        'publication_gate_allows_resource_headline',
    }
    assert all(row['pass'] is False for row in rows.values())
    assert rows['no_abandoned_synthetic_arithmetic_scratch']['evidence'].endswith('synthetic_arithmetic_scratch_abandoned_garbage')
    assert status['checks']['acceptance_gate_blocks_guard_corrected_total_until_every_required_gate_passes'] is True
    assert status['checks']['hardening_target_uses_guard_corrected_total_not_lower_strict_candidate'] is True
    assert status['checks']['presentation_policy_uses_hardening_target_without_accepting_it'] is True
