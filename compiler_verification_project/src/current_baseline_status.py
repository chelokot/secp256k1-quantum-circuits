#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Mapping


CURRENT_BASELINE_STATUS_SCHEMA = 'compiler-project-current-baseline-status-v1'
STATUS_NO_ACCEPTED_PHYSICAL_BASELINE = 'no_accepted_clifford_complete_physical_baseline'
STATUS_GUARD_CORRECTED_NOT_PROMOTED = 'guard_corrected_no_alias_total_not_promoted'


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def _sha256_payload(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode('ascii')).hexdigest()


def _active_blocker_names(public_headline_result: Mapping[str, Any]) -> set[str]:
    return {
        str(blocker['name'])
        for blocker in public_headline_result.get('publication_blockers', [])
        if blocker.get('active') is True
    }


def _gate(name: str, status: str, passed: bool, evidence: str, required_to_close: str) -> Dict[str, Any]:
    return {
        'name': name,
        'status': status,
        'pass': passed,
        'evidence': evidence,
        'required_to_close': required_to_close,
    }


def build_current_baseline_status(
    *,
    strict_replayed_tail_headline: Mapping[str, Any],
    public_headline_result: Mapping[str, Any],
    primary_strict_result: Mapping[str, Any],
    engine_completion_audit: Mapping[str, Any],
    zero_lift_guard_resource_audit: Mapping[str, Any],
    modular_accumulator_source_uncompute: Mapping[str, Any],
) -> Dict[str, Any]:
    selected = strict_replayed_tail_headline['selected_result']
    selected_non_clifford = int(selected['non_clifford'])
    selected_logical_qubits = int(selected['logical_qubits'])
    guard_gap = zero_lift_guard_resource_audit['capacity_gap']
    guard_delta = int(guard_gap['corrected_public_qubit_delta_if_no_aliasing_proof'])
    guard_corrected_logical_qubits = selected_logical_qubits + guard_delta
    source_uncompute_status = modular_accumulator_source_uncompute['promotion_status']['status']
    source_cleanup_counts = modular_accumulator_source_uncompute['source_uncompute_stream']['cleanup_status_counts']
    public_blockers = _active_blocker_names(public_headline_result)
    remaining_boundaries = [str(row['name']) for row in engine_completion_audit['remaining_macro_boundaries']]
    remaining_metrics = engine_completion_audit['remaining_macro_boundaries'][0]['evidence_metrics'] if engine_completion_audit['remaining_macro_boundaries'] else {}
    clifford_complete = engine_completion_audit['clifford_complete_goal_achieved'] is True
    guard_promoted = zero_lift_guard_resource_audit['promotion_status']['status'] != 'zero_lift_guard_capacity_gap_not_promoted_to_public_contract'
    source_uncompute_promoted = source_uncompute_status != 'source_uncompute_contract_not_promoted_to_scheduled_primitive_netlist'
    synthetic_scratch_clean = int(remaining_metrics.get('synthetic_arithmetic_scratch_abandoned_garbage', 0)) == 0
    accepted_gate_rows = [
        _gate(
            'single_authoritative_primitive_stream',
            'blocked',
            clifford_complete,
            'engine_completion_audit.clifford_complete_goal_achieved',
            'Make the global flat primitive stream the only source for execution, liveness, owner capacity, and resource totals.',
        ),
        _gate(
            'guard_corrected_no_alias_capacity_promoted_into_liveness',
            'blocked',
            guard_promoted,
            'zero_lift_guard_resource_audit.promotion_status',
            'Promote the zero-lift guard capacity into the scheduled primitive liveness owner model or prove a concrete alias/no-ancilla predicate construction.',
        ),
        _gate(
            'modular_accumulator_source_uncompute_promoted',
            'blocked',
            source_uncompute_promoted,
            'modular_accumulator_source_uncompute.promotion_status',
            'Promote consume/fold/source-uncompute rows into the same scheduled primitive netlist used for the public peak calculation.',
        ),
        _gate(
            'no_abandoned_synthetic_arithmetic_scratch',
            'blocked',
            synthetic_scratch_clean,
            'engine_completion_audit.remaining_macro_boundaries[0].evidence_metrics.synthetic_arithmetic_scratch_abandoned_garbage',
            'Replace synthetic modular-arithmetic scratch observations with concrete primitive wires, owners, liveness, and cleanup.',
        ),
        _gate(
            'publication_gate_allows_resource_headline',
            'blocked',
            public_headline_result['pass'] is True and len(public_blockers) == 0,
            'public_headline_result.pass + publication_blockers',
            'Clear public-headline publication blockers before any accepted baseline is advertised outside the candidate layer.',
        ),
    ]
    checks = {
        'strict_replayed_tail_artifact_passes': strict_replayed_tail_headline['pass'] is True,
        'primary_strict_result_binds_strict_replayed_tail': primary_strict_result['selected_result'] == selected,
        'public_headline_result_blocks_publication': public_headline_result['pass'] is False and 'remaining_macro_boundaries_not_flattened' in public_blockers,
        'engine_completion_blocks_clifford_complete_claim': clifford_complete is False and len(remaining_boundaries) > 0,
        'zero_lift_guard_audit_passes': zero_lift_guard_resource_audit['pass'] is True,
        'guard_corrected_total_is_derived_not_literal': guard_corrected_logical_qubits == selected_logical_qubits + int(guard_gap['missing_logical_qubits_under_clean_ladder']),
        'guard_corrected_total_is_not_promoted': zero_lift_guard_resource_audit['promotion_status']['status'] == 'zero_lift_guard_capacity_gap_not_promoted_to_public_contract',
        'modular_accumulator_source_uncompute_not_promoted': source_uncompute_status == 'source_uncompute_contract_not_promoted_to_scheduled_primitive_netlist',
        'partial_product_cleanup_proven_but_guard_cleanup_unproven': (
            int(source_cleanup_counts['source_uncompute_cleanup_ccx_proven']) > 0
            and int(source_cleanup_counts['missing_source_controls_for_cleanup']) > 0
        ),
        'acceptance_gate_blocks_guard_corrected_total_until_every_required_gate_passes': not all(row['pass'] for row in accepted_gate_rows),
        'no_accepted_physical_baseline_until_all_blockers_close': clifford_complete is False,
        'hardening_target_uses_guard_corrected_total_not_lower_strict_candidate': guard_corrected_logical_qubits == selected_logical_qubits + guard_delta and guard_corrected_logical_qubits > selected_logical_qubits,
        'presentation_policy_uses_hardening_target_without_accepting_it': guard_corrected_logical_qubits > selected_logical_qubits and clifford_complete is False,
    }
    return {
        'schema': CURRENT_BASELINE_STATUS_SCHEMA,
        'status': STATUS_NO_ACCEPTED_PHYSICAL_BASELINE,
        'scope': 'single repo authority for whether any checked resource number is accepted as the Clifford-complete physical baseline',
        'source_digests': {
            'strict_replayed_tail_headline_sha256': _sha256_payload(strict_replayed_tail_headline),
            'public_headline_result_sha256': _sha256_payload(public_headline_result),
            'primary_strict_result_sha256': _sha256_payload(primary_strict_result),
            'engine_completion_audit_sha256': _sha256_payload(engine_completion_audit),
            'zero_lift_guard_resource_audit_sha256': _sha256_payload(zero_lift_guard_resource_audit),
            'modular_accumulator_source_uncompute_sha256': _sha256_payload(modular_accumulator_source_uncompute),
        },
        'accepted_physical_baseline': None,
        'current_strict_candidate': {
            'status': 'not_accepted_as_physical_baseline',
            'reason': 'strict replayed-tail count still depends on unpromoted modular arithmetic and guard-capacity boundaries',
            'non_clifford': selected_non_clifford,
            'logical_qubits': selected_logical_qubits,
            'source_artifact': 'compiler_verification_project/artifacts/strict_replayed_tail_headline.json',
        },
        'guard_corrected_no_alias_candidate': {
            'status': STATUS_GUARD_CORRECTED_NOT_PROMOTED,
            'reason': 'counts the clean-ladder zero-lift guard workspace if no aliasing/no-ancilla proof exists, but the corrected owner model is not yet promoted into the global primitive stream',
            'non_clifford': selected_non_clifford,
            'logical_qubits': guard_corrected_logical_qubits,
            'derivation': {
                'strict_candidate_logical_qubits': selected_logical_qubits,
                'zero_lift_guard_current_logical_qubits': int(guard_gap['current_logical_qubits']),
                'zero_lift_guard_clean_ladder_logical_qubits': int(guard_gap['minimum_clean_ladder_logical_qubits']),
                'additional_logical_qubits_if_no_aliasing_proof': guard_delta,
                'reconstructed_logical_qubits': guard_corrected_logical_qubits,
            },
        },
        'conservative_hardening_target': {
            'status': 'repo_presentation_target_not_accepted_physical_baseline',
            'source': 'guard_corrected_no_alias_candidate',
            'reason': 'use the guard-corrected no-alias total as the conservative repo-wide hardening target while the accepted physical baseline gate is closed',
            'non_clifford': selected_non_clifford,
            'logical_qubits': guard_corrected_logical_qubits,
            'derivation': {
                'strict_replayed_tail_candidate_logical_qubits': selected_logical_qubits,
                'additional_clean_ladder_guard_qubits': guard_delta,
                'reconstructed_logical_qubits': guard_corrected_logical_qubits,
            },
            'not_claimed': [
                'not an accepted Clifford-complete physical baseline',
                'not a fresh compressed/Groth16 proof claim',
                'not a sub-1600 optimization result',
            ],
        },
        'accepted_baseline_gate': {
            'status': 'blocked',
            'decision': 'do_not_promote_any_resource_number_to_accepted_physical_baseline',
            'candidate_under_review': 'guard_corrected_no_alias_candidate',
            'candidate_under_review_logical_qubits': guard_corrected_logical_qubits,
            'candidate_under_review_non_clifford': selected_non_clifford,
            'policy': 'accepted_physical_baseline may be populated only when every gate row passes and the accepted totals are recomputed from that same primitive stream',
            'rows': accepted_gate_rows,
        },
        'remaining_physical_baseline_blockers': [
            {
                'name': 'zero_lift_guard_capacity_not_promoted',
                'status': zero_lift_guard_resource_audit['promotion_status']['status'],
                'minimum_clean_ladder_logical_qubits': int(guard_gap['minimum_clean_ladder_logical_qubits']),
                'missing_logical_qubits_under_clean_ladder': guard_delta,
            },
            {
                'name': 'modular_accumulator_source_uncompute_not_promoted',
                'status': source_uncompute_status,
                'partial_product_cleanup_ccx_proven': int(source_cleanup_counts['source_uncompute_cleanup_ccx_proven']),
                'guard_cleanup_ccx_missing_source_controls': int(source_cleanup_counts['missing_source_controls_for_cleanup']),
            },
            {
                'name': 'modular_arithmetic_clifford_expansion_not_flattened',
                'status': remaining_boundaries[0] if remaining_boundaries else 'closed',
                'engine_clifford_complete_goal_achieved': clifford_complete,
            },
        ],
        'publication_policy': {
            'may_publish_resource_headline_as_physical_baseline': False,
            'default_docs_resource_target_before_acceptance': 'conservative_hardening_target',
            'default_docs_logical_qubits_before_acceptance': guard_corrected_logical_qubits,
            'default_docs_non_clifford_before_acceptance': selected_non_clifford,
            'forbidden_presentations_until_gate_closes': [
                'do not present 1199, 1044, or 1968 logical qubits as the accepted physical baseline',
                'do not present 2222 logical qubits as accepted; present it only as the conservative hardening target under review',
                'do not run or advertise proof freshness until the cheap artifact gates and proof_status gates pass',
            ],
            'required_to_publish': [
                'Promote zero-lift guard capacity into the scheduled primitive liveness owner model or prove an executable alias/no-ancilla construction.',
                'Promote modular accumulator consume/fold/source-uncompute rows into the global scheduled primitive netlist.',
                'Recompute public totals from the same primitive stream used by tests and ZKP input.',
                'Only then rebuild proof inputs and proof bundles if a ZKP-backed release claim is desired.',
            ],
        },
        'checks': checks,
        'pass': all(checks.values()),
    }


__all__ = [
    'CURRENT_BASELINE_STATUS_SCHEMA',
    'STATUS_GUARD_CORRECTED_NOT_PROMOTED',
    'STATUS_NO_ACCEPTED_PHYSICAL_BASELINE',
    'build_current_baseline_status',
]
