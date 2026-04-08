#!/usr/bin/env python3

from __future__ import annotations

import csv
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Mapping, Tuple

from common import (
    SECP_B,
    SECP_G,
    SECP_N,
    SECP_P,
    deterministic_scalars,
    dump_json,
    load_json,
    mul_fixed_window,
    precompute_window_tables,
    sha256_bytes,
    sha256_path,
)
from lookup_lowering import lookup_lowering_library, lowered_lookup_semantic_summary
from project import (
    FIELD_BITS,
    FOLDED_MAG_BITS,
    FOLDED_MAG_DOMAIN,
    FULL_PHASE_REGISTER_BITS,
    PROJECT_ROOT,
    PUBLIC_GOOGLE_BASELINE,
    RAW_WINDOW_BITS,
    _leaf,
    _register_map,
    build_azure_logical_counts_payload,
    build_cain_transfer_payload,
    exact_leaf_slot_allocation,
    full_attack_inventory,
    leaf_opcode_histogram,
    phase_shell_families,
    primitive_multiplier_library,
    raw32_schedule,
    run_full_raw32_semantic_check,
    arithmetic_kernel_library,
    lookup_families,
    structured_raw32_cases,
    table_manifests,
)


def _check(name: str, passed: bool, expected: Any, observed: Any) -> Dict[str, Any]:
    return {
        'name': name,
        'pass': int(passed),
        'expected': expected,
        'observed': observed,
    }


def _summarize_checks(checks: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        'pass': sum(check['pass'] for check in checks),
        'total': len(checks),
        'checks': checks,
    }


def _load_artifact(path: Path) -> Dict[str, Any]:
    return load_json(path)


def load_compiler_artifacts(repo_root: Path) -> Dict[str, Any]:
    artifact_root = repo_root / 'compiler_verification_project' / 'artifacts'
    required = {
        'canonical_public_point': artifact_root / 'canonical_public_point.json',
        'full_raw32_oracle': artifact_root / 'full_raw32_oracle.json',
        'exact_leaf_slot_allocation': artifact_root / 'exact_leaf_slot_allocation.json',
        'module_library': artifact_root / 'module_library.json',
        'primitive_multiplier_library': artifact_root / 'primitive_multiplier_library.json',
        'phase_shell_families': artifact_root / 'phase_shell_families.json',
        'table_manifests': artifact_root / 'table_manifests.json',
        'lookup_lowerings': artifact_root / 'lookup_lowerings.json',
        'family_frontier': artifact_root / 'family_frontier.json',
        'full_attack_inventory': artifact_root / 'full_attack_inventory.json',
        'build_summary': artifact_root / 'build_summary.json',
        'cain_exact_transfer': artifact_root / 'cain_exact_transfer.json',
        'azure_resource_estimator_logical_counts': artifact_root / 'azure_resource_estimator_logical_counts.json',
    }
    if not all(path.exists() for path in required.values()):
        from project import build_all_artifacts, write_cain_transfer

        build_all_artifacts()
        write_cain_transfer()
    return {name: _load_artifact(path) for name, path in required.items()}


def _recomputed_canonical_public_point() -> Dict[str, Any]:
    leaf_path = PROJECT_ROOT / 'artifacts' / 'circuits' / 'optimized_pointadd_secp256k1.json'
    scaffold_path = PROJECT_ROOT / 'artifacts' / 'circuits' / 'ecdlp_scaffold_optimized.json'
    leaf_sha = sha256_path(leaf_path)
    scaffold_sha = sha256_path(scaffold_path)
    seed = bytes.fromhex(sha256_bytes(bytes.fromhex(leaf_sha) + bytes.fromhex(scaffold_sha)))
    h_scalar = deterministic_scalars(seed + b'compiler-project-public-point', 1, SECP_N)[0]
    tables = precompute_window_tables(SECP_G, SECP_P, SECP_B, width=8, bits=256)
    point = mul_fixed_window(h_scalar, tables, SECP_P, SECP_B, width=8, order=SECP_N)
    assert point is not None
    return {
        'derivation': 'first deterministic public-point base from the checked-in leaf/scaffold hash stream',
        'leaf_sha256': leaf_sha,
        'scaffold_sha256': scaffold_sha,
        'h_scalar_hex': format(h_scalar, '064x'),
        'point': {
            'x_hex': format(point[0], '064x'),
            'y_hex': format(point[1], '064x'),
        },
    }


def build_canonical_public_point_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    expected = _recomputed_canonical_public_point()
    checks = [
        _check('canonical_public_point_matches_hash_derivation', artifacts['canonical_public_point'] == expected, expected, artifacts['canonical_public_point']),
        _check(
            'table_manifests_share_canonical_public_point',
            artifacts['table_manifests']['canonical_public_point'] == artifacts['canonical_public_point'],
            artifacts['canonical_public_point'],
            artifacts['table_manifests']['canonical_public_point'],
        ),
    ]
    return _summarize_checks(checks)


def build_schedule_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    schedule = artifacts['full_raw32_oracle']
    calls = schedule['leaf_calls']
    phase_a_windows = [schedule['direct_seed']['window_index_within_register']] + [row['window_index_within_register'] for row in calls if row['phase_register'] == 'phase_a']
    phase_b_windows = [row['window_index_within_register'] for row in calls if row['phase_register'] == 'phase_b']
    checks = [
        _check('schedule_matches_generator', schedule == raw32_schedule(), raw32_schedule(), schedule),
        _check('raw_window_count_matches_completed_schedule', schedule['raw_window_count'] == 1 + len(calls), 1 + len(calls), schedule['raw_window_count']),
        _check('phase_a_windows_cover_0_through_15_once', sorted(phase_a_windows) == list(range(16)), list(range(16)), sorted(phase_a_windows)),
        _check('phase_b_windows_cover_0_through_15_once', sorted(phase_b_windows) == list(range(16)), list(range(16)), sorted(phase_b_windows)),
        _check(
            'leaf_call_indexes_are_consecutive',
            [row['call_index'] for row in calls] == list(range(len(calls))),
            list(range(len(calls))),
            [row['call_index'] for row in calls],
        ),
        _check(
            'bit_starts_match_window_indexes',
            all(row['bit_start'] == RAW_WINDOW_BITS * row['window_index_within_register'] and row['bit_width'] == RAW_WINDOW_BITS for row in calls),
            'bit_start == 16 * window_index and bit_width == 16 for every leaf call',
            [{'call_index': row['call_index'], 'bit_start': row['bit_start'], 'window_index_within_register': row['window_index_within_register'], 'bit_width': row['bit_width']} for row in calls],
        ),
        _check(
            'summary_lookup_invocations_match_schedule',
            schedule['summary']['lookup_invocations_total'] == 1 + len(calls),
            1 + len(calls),
            schedule['summary']['lookup_invocations_total'],
        ),
        _check(
            'phase_register_bits_match_two_raw_registers',
            schedule['phase_register_bits_total'] == 2 * FIELD_BITS,
            2 * FIELD_BITS,
            schedule['phase_register_bits_total'],
        ),
        _check(
            'full_phase_register_constant_matches_schedule',
            schedule['phase_register_bits_total'] == FULL_PHASE_REGISTER_BITS,
            FULL_PHASE_REGISTER_BITS,
            schedule['phase_register_bits_total'],
        ),
    ]
    return _summarize_checks(checks)


def build_table_manifest_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    manifests = artifacts['table_manifests']
    checks = [
        _check('table_manifests_match_generator', manifests == table_manifests(), table_manifests(), manifests),
        _check('phase_a_table_count_is_16', len(manifests['phase_a_bases']) == 16, 16, len(manifests['phase_a_bases'])),
        _check('phase_b_table_count_is_16', len(manifests['phase_b_bases']) == 16, 16, len(manifests['phase_b_bases'])),
        _check(
            'folded_contract_matches_compiler_constants',
            manifests['folded_contract'] == {
                'word_bits': RAW_WINDOW_BITS,
                'magnitude_bits': FOLDED_MAG_BITS,
                'positive_domain_size': FOLDED_MAG_DOMAIN,
                'coordinate_bits_per_record': 2 * FIELD_BITS,
            },
            {
                'word_bits': RAW_WINDOW_BITS,
                'magnitude_bits': FOLDED_MAG_BITS,
                'positive_domain_size': FOLDED_MAG_DOMAIN,
                'coordinate_bits_per_record': 2 * FIELD_BITS,
            },
            manifests['folded_contract'],
        ),
    ]
    return _summarize_checks(checks)


def build_arithmetic_kernel_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    kernel = artifacts['module_library']
    hist = leaf_opcode_histogram()
    add_cost = FIELD_BITS - 1
    mul_cost = (FIELD_BITS * FIELD_BITS) + (2 * FIELD_BITS) - 1
    mul_const_cost = (len(kernel['addition_chain_21']) - 1) * add_cost
    expected_leaf_non_clifford = (
        hist.get('field_mul', 0) * mul_cost
        + hist.get('field_add', 0) * add_cost
        + hist.get('field_sub', 0) * add_cost
        + hist.get('mul_const', 0) * mul_const_cost
        + hist.get('select_field_if_flag', 0) * add_cost
    )
    checks = [
        _check('module_library_matches_generator', kernel == arithmetic_kernel_library(), arithmetic_kernel_library(), kernel),
        _check('leaf_opcode_histogram_matches_leaf', kernel['leaf_opcode_histogram'] == hist, hist, kernel['leaf_opcode_histogram']),
        _check('field_add_cost_matches_n_minus_1', kernel['field_add_non_clifford'] == add_cost, add_cost, kernel['field_add_non_clifford']),
        _check('field_mul_cost_matches_family_formula', kernel['field_mul_non_clifford'] == mul_cost, mul_cost, kernel['field_mul_non_clifford']),
        _check('mul_const_cost_matches_addition_chain', kernel['mul_const_non_clifford'] == mul_const_cost, mul_const_cost, kernel['mul_const_non_clifford']),
        _check(
            'arithmetic_leaf_non_clifford_matches_weighted_histogram',
            kernel['arithmetic_leaf_non_clifford'] == expected_leaf_non_clifford,
            expected_leaf_non_clifford,
            kernel['arithmetic_leaf_non_clifford'],
        ),
    ]
    return _summarize_checks(checks)


def build_lookup_lowering_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    lowering = artifacts['lookup_lowerings']
    expected = lookup_lowering_library()
    semantic = lowered_lookup_semantic_summary()
    contract_summary = lowering['lookup_contract_summary']
    families = lowering['families']
    family_lookup = {family['name']: family for family in families}
    reconstructed_family_totals = []
    reconstructed_family_workspace = []
    semantic_pairs = []
    for family in families:
        stages = family['stages']
        persistent_total = sum(int(entry['qubits']) for entry in family['persistent_workspace'])
        reconstructed_non_clifford = sum(int(stage['non_clifford_total']) for stage in stages)
        reconstructed_workspace = max(int(stage['total_workspace_qubits']) for stage in stages)
        reconstructed_family_totals.append({
            'name': family['name'],
            'direct_lookup_non_clifford': reconstructed_non_clifford,
            'per_leaf_lookup_non_clifford': reconstructed_non_clifford,
        })
        reconstructed_family_workspace.append({
            'name': family['name'],
            'persistent_workspace_qubits': persistent_total,
            'peak_total_workspace_qubits': reconstructed_workspace,
        })
        semantic_row = next(row for row in semantic['families'] if row['name'] == family['name'])
        semantic_pairs.append({
            'name': family['name'],
            'canonical_full_exhaustive_pass': semantic_row['canonical_full_exhaustive_pass'],
            'canonical_full_exhaustive_total': semantic_row['canonical_full_exhaustive_total'],
            'multibase_edge_pass': semantic_row['multibase_edge_pass'],
            'multibase_edge_total': semantic_row['multibase_edge_total'],
        })
    checks = [
        _check('lookup_lowering_library_matches_generator', lowering == expected, expected, lowering),
        _check(
            'lookup_lowering_contract_summary_matches_constants',
            contract_summary == {
                'word_bits': RAW_WINDOW_BITS,
                'magnitude_bits': FOLDED_MAG_BITS,
                'positive_domain_size': FOLDED_MAG_DOMAIN,
                'coordinate_bits': FIELD_BITS,
            },
            {
                'word_bits': RAW_WINDOW_BITS,
                'magnitude_bits': FOLDED_MAG_BITS,
                'positive_domain_size': FOLDED_MAG_DOMAIN,
                'coordinate_bits': FIELD_BITS,
            },
            contract_summary,
        ),
        _check(
            'lookup_lowering_contract_hash_matches_main_lookup_contract',
            lowering['lookup_contract_sha256'] == sha256_path(PROJECT_ROOT / 'artifacts' / 'lookup' / 'lookup_signed_fold_contract.json'),
            sha256_path(PROJECT_ROOT / 'artifacts' / 'lookup' / 'lookup_signed_fold_contract.json'),
            lowering['lookup_contract_sha256'],
        ),
        _check(
            'lookup_lowering_totals_reconstruct_from_stage_inventory',
            all(
                family_lookup[row['name']]['direct_lookup_non_clifford'] == row['direct_lookup_non_clifford']
                and family_lookup[row['name']]['per_leaf_lookup_non_clifford'] == row['per_leaf_lookup_non_clifford']
                for row in reconstructed_family_totals
            ),
            reconstructed_family_totals,
            [
                {
                    'name': family['name'],
                    'direct_lookup_non_clifford': family['direct_lookup_non_clifford'],
                    'per_leaf_lookup_non_clifford': family['per_leaf_lookup_non_clifford'],
                }
                for family in families
            ],
        ),
        _check(
            'lookup_lowering_workspace_reconstructs_from_persistent_plus_peak_stage',
            all(
                family_lookup[row['name']]['workspace_reconstruction']['persistent_workspace_qubits'] == row['persistent_workspace_qubits']
                and family_lookup[row['name']]['workspace_reconstruction']['peak_total_workspace_qubits'] == row['peak_total_workspace_qubits']
                and family_lookup[row['name']]['extra_lookup_workspace_qubits'] == row['peak_total_workspace_qubits']
                for row in reconstructed_family_workspace
            ),
            reconstructed_family_workspace,
            [
                {
                    'name': family['name'],
                    'persistent_workspace_qubits': family['workspace_reconstruction']['persistent_workspace_qubits'],
                    'peak_total_workspace_qubits': family['workspace_reconstruction']['peak_total_workspace_qubits'],
                }
                for family in families
            ],
        ),
        _check(
            'lookup_lowering_semantics_match_contract',
            all(
                row['canonical_full_exhaustive_pass'] == row['canonical_full_exhaustive_total']
                and row['multibase_edge_pass'] == row['multibase_edge_total']
                for row in semantic_pairs
            ),
            [
                {
                    'name': row['name'],
                    'canonical_full_exhaustive': row['canonical_full_exhaustive_total'],
                    'multibase_edge': row['multibase_edge_total'],
                }
                for row in semantic_pairs
            ],
            semantic_pairs,
        ),
    ]
    return _summarize_checks(checks)


def _versions_during_write(slot_alloc: Mapping[str, Any], pc: int) -> Tuple[set[Tuple[str, int]], set[Tuple[str, int]]]:
    before = set()
    during = set()
    for entry in slot_alloc['versions']:
        slot = (entry['reg_type'], entry['assigned_slot'])
        if entry['def_pc'] < pc <= entry['last_use_pc'] or (entry['def_pc'] < pc and entry['last_use_pc'] == pc):
            before.add(slot)
        if entry['def_pc'] < pc <= entry['last_use_pc'] or entry['def_pc'] == pc:
            during.add(slot)
    return before, during


def build_slot_allocation_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    slot_alloc = artifacts['exact_leaf_slot_allocation']
    leaf = _leaf()
    register_map = _register_map()
    arithmetic_registers = sorted(register_map['arithmetic_slots'])
    control_registers = sorted(register_map['auxiliary_control_slots'])
    overlap_violations: List[Dict[str, Any]] = []
    slot_buckets: Dict[Tuple[str, int], List[Dict[str, Any]]] = defaultdict(list)
    for entry in slot_alloc['versions']:
        slot_buckets[(entry['reg_type'], entry['assigned_slot'])].append(entry)
    for (reg_type, assigned_slot), entries in slot_buckets.items():
        ordered = sorted(entries, key=lambda row: (row['def_pc'], row['last_use_pc'], row['version_id']))
        for left, right in zip(ordered, ordered[1:]):
            if right['def_pc'] < left['last_use_pc']:
                overlap_violations.append({
                    'reg_type': reg_type,
                    'assigned_slot': assigned_slot,
                    'left_version_id': left['version_id'],
                    'right_version_id': right['version_id'],
                    'left_interval': [left['def_pc'], left['last_use_pc']],
                    'right_interval': [right['def_pc'], right['last_use_pc']],
                })
    reconstructed = []
    for row in slot_alloc['per_pc']:
        before, during = _versions_during_write(slot_alloc, row['pc'])
        reconstructed.append({
            'pc': row['pc'],
            'opcode': row['opcode'],
            'arithmetic_slots_live_before_write': sum(1 for reg_type, _ in before if reg_type == 'arithmetic'),
            'control_slots_live_before_write': sum(1 for reg_type, _ in before if reg_type == 'control'),
            'arithmetic_slots_needed_during_write': sum(1 for reg_type, _ in during if reg_type == 'arithmetic'),
            'control_slots_needed_during_write': sum(1 for reg_type, _ in during if reg_type == 'control'),
            'dst': row['dst'],
            'reuses_existing_slot': row['reuses_existing_slot'],
        })
    reconstructed_peak_arithmetic = max(entry['arithmetic_slots_needed_during_write'] for entry in reconstructed)
    reconstructed_peak_control = max(entry['control_slots_needed_during_write'] for entry in reconstructed)
    reconstructed_peak_total = max(entry['arithmetic_slots_needed_during_write'] + entry['control_slots_needed_during_write'] for entry in reconstructed)
    checks = [
        _check('slot_allocation_matches_generator', slot_alloc == exact_leaf_slot_allocation(), exact_leaf_slot_allocation(), slot_alloc),
        _check('tracked_arithmetic_registers_match_register_map', slot_alloc['tracked_arithmetic_registers'] == arithmetic_registers, arithmetic_registers, slot_alloc['tracked_arithmetic_registers']),
        _check('tracked_control_registers_match_register_map', slot_alloc['tracked_control_registers'] == control_registers, control_registers, slot_alloc['tracked_control_registers']),
        _check('version_intervals_do_not_overlap_on_same_slot', len(overlap_violations) == 0, [], overlap_violations),
        _check(
            'per_pc_live_counts_match_assigned_intervals',
            slot_alloc['per_pc'] == reconstructed,
            reconstructed,
            slot_alloc['per_pc'],
        ),
        _check(
            'allocator_summary_arithmetic_peak_matches_reconstructed_live_set',
            slot_alloc['allocator_summary']['exact_arithmetic_slot_count'] == reconstructed_peak_arithmetic,
            reconstructed_peak_arithmetic,
            slot_alloc['allocator_summary']['exact_arithmetic_slot_count'],
        ),
        _check(
            'allocator_summary_control_peak_matches_reconstructed_live_set',
            slot_alloc['allocator_summary']['exact_control_slot_count'] == reconstructed_peak_control,
            reconstructed_peak_control,
            slot_alloc['allocator_summary']['exact_control_slot_count'],
        ),
        _check(
            'peak_total_matches_reconstructed_live_set',
            slot_alloc['peak_total_slots']['count'] == reconstructed_peak_total,
            reconstructed_peak_total,
            slot_alloc['peak_total_slots']['count'],
        ),
        _check(
            'per_pc_rows_cover_leaf_instruction_count',
            len(slot_alloc['per_pc']) == len(leaf['instructions']),
            len(leaf['instructions']),
            len(slot_alloc['per_pc']),
        ),
    ]
    return _summarize_checks(checks)


def build_full_attack_inventory_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    inventory = artifacts['full_attack_inventory']
    schedule = artifacts['full_raw32_oracle']
    hist = artifacts['module_library']['leaf_opcode_histogram']
    leaf_calls = schedule['summary']['leaf_call_count_total']
    expected_inventory = {
        'direct_seed_count': 1,
        'phase_a_leaf_calls': schedule['summary']['phase_a_leaf_calls'],
        'phase_b_leaf_calls': schedule['summary']['phase_b_leaf_calls'],
        'total_leaf_calls': leaf_calls,
        'classical_tail_elisions_removed': schedule['summary']['classical_tail_elisions_removed'],
        'whole_oracle_field_mul_count': leaf_calls * hist.get('field_mul', 0),
        'whole_oracle_field_add_count': leaf_calls * hist.get('field_add', 0),
        'whole_oracle_field_sub_count': leaf_calls * hist.get('field_sub', 0),
        'whole_oracle_mul_const_count': leaf_calls * hist.get('mul_const', 0),
        'whole_oracle_select_count': leaf_calls * hist.get('select_field_if_flag', 0),
        'whole_oracle_lookup_count': schedule['summary']['lookup_invocations_total'],
    }
    checks = [
        _check('full_attack_inventory_matches_generator', inventory == full_attack_inventory(), full_attack_inventory(), inventory),
        _check('inventory_counts_match_schedule_and_histogram', inventory['inventory'] == expected_inventory, expected_inventory, inventory['inventory']),
        _check('inventory_best_gate_family_matches_frontier', inventory['best_gate_family'] == artifacts['family_frontier']['best_gate_family'], artifacts['family_frontier']['best_gate_family'], inventory['best_gate_family']),
        _check('inventory_best_qubit_family_matches_frontier', inventory['best_qubit_family'] == artifacts['family_frontier']['best_qubit_family'], artifacts['family_frontier']['best_qubit_family'], inventory['best_qubit_family']),
    ]
    return _summarize_checks(checks)


def build_primitive_multiplier_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    primitive = artifacts['primitive_multiplier_library']
    schedule = artifacts['full_raw32_oracle']
    kernel = artifacts['module_library']
    field_mul_pcs = [instruction['pc'] for instruction in _leaf()['instructions'] if instruction['op'] == 'field_mul']
    expected_per_leaf = [
        {
            'leaf_multiplier_index': ordinal,
            'leaf_pc': pc,
            'family': kernel['name'],
            'field_bits': FIELD_BITS,
            'exact_non_clifford': kernel['field_mul_non_clifford'],
            'gate_set': kernel['gate_set'],
        }
        for ordinal, pc in enumerate(field_mul_pcs)
    ]
    expected_examples = []
    for call in schedule['leaf_calls']:
        for entry in expected_per_leaf:
            expected_examples.append({
                'call_index': call['call_index'],
                'phase_register': call['phase_register'],
                'window_index_within_register': call['window_index_within_register'],
                **entry,
            })
    checks = [
        _check('primitive_multiplier_library_matches_generator', primitive == primitive_multiplier_library(), primitive_multiplier_library(), primitive),
        _check('per_leaf_multiplier_instances_match_leaf_field_mul_pcs', primitive['per_leaf_multiplier_instances'] == expected_per_leaf, expected_per_leaf, primitive['per_leaf_multiplier_instances']),
        _check(
            'whole_oracle_multiplier_instance_count_matches_schedule_times_leaf_multipliers',
            primitive['whole_oracle_multiplier_instance_count'] == schedule['summary']['leaf_call_count_total'] * len(expected_per_leaf),
            schedule['summary']['leaf_call_count_total'] * len(expected_per_leaf),
            primitive['whole_oracle_multiplier_instance_count'],
        ),
        _check(
            'whole_oracle_multiplier_total_matches_instance_count',
            primitive['whole_oracle_multiplier_non_clifford_total'] == primitive['whole_oracle_multiplier_instance_count'] * kernel['field_mul_non_clifford'],
            primitive['whole_oracle_multiplier_instance_count'] * kernel['field_mul_non_clifford'],
            primitive['whole_oracle_multiplier_non_clifford_total'],
        ),
        _check('example_instances_match_cross_product_prefix', primitive['example_instances'] == expected_examples[:8], expected_examples[:8], primitive['example_instances']),
    ]
    return _summarize_checks(checks)


def build_frontier_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    frontier = artifacts['family_frontier']
    schedule = artifacts['full_raw32_oracle']
    slot_alloc = artifacts['exact_leaf_slot_allocation']
    kernel = artifacts['module_library']
    expected_lookup_families = [row.__dict__ for row in lookup_families()]
    expected_phase_shells = [row.__dict__ for row in phase_shell_families()]
    families = frontier['families']
    expected_families = []
    low_qubit = PUBLIC_GOOGLE_BASELINE['low_qubit']
    low_gate = PUBLIC_GOOGLE_BASELINE['low_gate']
    for lookup in frontier['lookup_families']:
        for phase_shell in frontier['phase_shell_families']:
            total_nc = lookup['direct_lookup_non_clifford'] + schedule['summary']['leaf_call_count_total'] * (kernel['arithmetic_leaf_non_clifford'] + lookup['per_leaf_lookup_non_clifford'])
            total_qubits = (
                slot_alloc['allocator_summary']['exact_arithmetic_slot_count'] * FIELD_BITS
                + slot_alloc['allocator_summary']['exact_control_slot_count']
                + lookup['extra_lookup_workspace_qubits']
                + phase_shell['live_quantum_bits']
            )
            expected_families.append({
                'name': f"{lookup['name']}__{phase_shell['name']}",
                'summary': f"{lookup['summary']} / {phase_shell['summary']}",
                'gate_set': f"{lookup['gate_set']}; phase shell: {phase_shell['name']}",
                'phase_shell': phase_shell['name'],
                'arithmetic_kernel_family': kernel['name'],
                'lookup_family': lookup['name'],
                'arithmetic_leaf_non_clifford': kernel['arithmetic_leaf_non_clifford'],
                'direct_seed_non_clifford': lookup['direct_lookup_non_clifford'],
                'per_leaf_lookup_non_clifford': lookup['per_leaf_lookup_non_clifford'],
                'full_oracle_non_clifford': total_nc,
                'arithmetic_slot_count': slot_alloc['allocator_summary']['exact_arithmetic_slot_count'],
                'control_slot_count': slot_alloc['allocator_summary']['exact_control_slot_count'],
                'lookup_workspace_qubits': lookup['extra_lookup_workspace_qubits'],
                'live_phase_bits': phase_shell['live_quantum_bits'],
                'total_logical_qubits': total_qubits,
                'improvement_vs_google_low_qubit': low_qubit['non_clifford'] / total_nc,
                'improvement_vs_google_low_gate': low_gate['non_clifford'] / total_nc,
                'qubit_ratio_vs_google_low_qubit': low_qubit['logical_qubits'] / total_qubits,
                'qubit_ratio_vs_google_low_gate': low_gate['logical_qubits'] / total_qubits,
                'notes': [*lookup['notes'], *phase_shell['notes']],
            })
    expected_best_gate = min(expected_families, key=lambda row: (row['full_oracle_non_clifford'], row['total_logical_qubits']))
    expected_best_qubit = min(expected_families, key=lambda row: (row['total_logical_qubits'], row['full_oracle_non_clifford']))
    checks = [
        _check('public_google_baseline_matches_constant', frontier['public_google_baseline'] == PUBLIC_GOOGLE_BASELINE, PUBLIC_GOOGLE_BASELINE, frontier['public_google_baseline']),
        _check('frontier_schedule_matches_standalone_schedule', frontier['schedule'] == schedule, schedule, frontier['schedule']),
        _check('frontier_slot_allocation_matches_standalone_slot_allocation', frontier['slot_allocation'] == slot_alloc, slot_alloc, frontier['slot_allocation']),
        _check('frontier_arithmetic_kernel_matches_module_library', frontier['arithmetic_kernel_family'] == kernel, kernel, frontier['arithmetic_kernel_family']),
        _check('frontier_lookup_lowering_matches_lookup_lowering_artifact', frontier['lookup_lowerings'] == artifacts['lookup_lowerings'], artifacts['lookup_lowerings'], frontier['lookup_lowerings']),
        _check('lookup_family_library_matches_named_lookup_families', frontier['lookup_families'] == expected_lookup_families, expected_lookup_families, frontier['lookup_families']),
        _check('phase_shell_library_matches_named_phase_shells', frontier['phase_shell_families'] == expected_phase_shells, expected_phase_shells, frontier['phase_shell_families']),
        _check('frontier_family_rows_reconstruct_from_components', families == expected_families, expected_families, families),
        _check('best_gate_family_is_minimum_over_family_rows', frontier['best_gate_family'] == expected_best_gate, expected_best_gate, frontier['best_gate_family']),
        _check('best_qubit_family_is_minimum_over_family_rows', frontier['best_qubit_family'] == expected_best_qubit, expected_best_qubit, frontier['best_qubit_family']),
    ]
    return _summarize_checks(checks)


def build_build_summary_checks(artifacts: Mapping[str, Any], repo_root: Path) -> Dict[str, Any]:
    build_summary = artifacts['build_summary']
    expected_paths = {
        'canonical_public_point': 'compiler_verification_project/artifacts/canonical_public_point.json',
        'full_raw32_oracle': 'compiler_verification_project/artifacts/full_raw32_oracle.json',
        'exact_leaf_slot_allocation': 'compiler_verification_project/artifacts/exact_leaf_slot_allocation.json',
        'module_library': 'compiler_verification_project/artifacts/module_library.json',
        'primitive_multiplier_library': 'compiler_verification_project/artifacts/primitive_multiplier_library.json',
        'phase_shell_families': 'compiler_verification_project/artifacts/phase_shell_families.json',
        'table_manifests': 'compiler_verification_project/artifacts/table_manifests.json',
        'lookup_lowerings': 'compiler_verification_project/artifacts/lookup_lowerings.json',
        'family_frontier': 'compiler_verification_project/artifacts/family_frontier.json',
        'full_attack_inventory': 'compiler_verification_project/artifacts/full_attack_inventory.json',
        'azure_resource_estimator_logical_counts': 'compiler_verification_project/artifacts/azure_resource_estimator_logical_counts.json',
    }
    checks = [
        _check('build_summary_schema_matches_current_version', build_summary['schema'] == 'compiler-project-build-summary-v4', 'compiler-project-build-summary-v4', build_summary['schema']),
        _check('build_summary_artifact_paths_match_expected_set', build_summary['artifacts'] == expected_paths, expected_paths, build_summary['artifacts']),
        _check(
            'build_summary_paths_exist_on_disk',
            all((repo_root / path).exists() for path in build_summary['artifacts'].values()),
            sorted(build_summary['artifacts'].values()),
            sorted(path for path in build_summary['artifacts'].values() if (repo_root / path).exists()),
        ),
        _check('build_summary_best_gate_matches_frontier', build_summary['headline']['best_gate_family'] == artifacts['family_frontier']['best_gate_family'], artifacts['family_frontier']['best_gate_family'], build_summary['headline']['best_gate_family']),
        _check('build_summary_best_qubit_matches_frontier', build_summary['headline']['best_qubit_family'] == artifacts['family_frontier']['best_qubit_family'], artifacts['family_frontier']['best_qubit_family'], build_summary['headline']['best_qubit_family']),
    ]
    return _summarize_checks(checks)


def build_cain_transfer_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    expected = build_cain_transfer_payload(artifacts['family_frontier'])
    checks = [
        _check('cain_transfer_matches_frontier_projection', artifacts['cain_exact_transfer'] == expected, expected, artifacts['cain_exact_transfer']),
    ]
    return _summarize_checks(checks)


def build_azure_seed_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    expected = build_azure_logical_counts_payload(artifacts['family_frontier'])
    checks = [
        _check('azure_seed_matches_frontier_projection', artifacts['azure_resource_estimator_logical_counts'] == expected, expected, artifacts['azure_resource_estimator_logical_counts']),
    ]
    return _summarize_checks(checks)


def build_semantic_replay_checks(semantic_replay: Mapping[str, Any], repo_root: Path, random_case_count: int) -> Dict[str, Any]:
    csv_path = repo_root / 'compiler_verification_project' / 'artifacts' / semantic_replay['csv']
    with csv_path.open(newline='') as handle:
        csv_row_count = sum(1 for _ in csv.reader(handle)) - 1
    structured_case_count = len(structured_raw32_cases())
    checks = [
        _check('semantic_replay_passes_all_cases', semantic_replay['summary']['pass'] == semantic_replay['summary']['total'], semantic_replay['summary']['total'], semantic_replay['summary']['pass']),
        _check('semantic_replay_csv_hash_matches_artifact', semantic_replay['sha256'] == sha256_path(csv_path), sha256_path(csv_path), semantic_replay['sha256']),
        _check('semantic_replay_csv_rows_match_summary_total', csv_row_count == semantic_replay['summary']['total'], semantic_replay['summary']['total'], csv_row_count),
        _check('semantic_replay_includes_structured_cases', semantic_replay['summary']['structured_cases'] == structured_case_count, structured_case_count, semantic_replay['summary']['structured_cases']),
        _check('semantic_replay_random_case_count_matches_request', semantic_replay['summary']['random_cases'] == random_case_count, random_case_count, semantic_replay['summary']['random_cases']),
        _check(
            'semantic_replay_summary_total_matches_case_partition',
            semantic_replay['summary']['total'] == semantic_replay['summary']['structured_cases'] + semantic_replay['summary']['random_cases'],
            semantic_replay['summary']['structured_cases'] + semantic_replay['summary']['random_cases'],
            semantic_replay['summary']['total'],
        ),
        _check('semantic_replay_observes_seed_zero_cases', semantic_replay['summary']['seed_zero_cases'] > 0, '> 0', semantic_replay['summary']['seed_zero_cases']),
        _check('semantic_replay_observes_phase_b_zero_cases', semantic_replay['summary']['phase_b_zero_cases'] > 0, '> 0', semantic_replay['summary']['phase_b_zero_cases']),
        _check('semantic_replay_observes_phase_b_nonzero_cases', semantic_replay['summary']['phase_b_nonzero_cases'] > 0, '> 0', semantic_replay['summary']['phase_b_nonzero_cases']),
    ]
    return _summarize_checks(checks)


def build_integrity_report(repo_root: Path, artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        'canonical_public_point_checks': build_canonical_public_point_checks(artifacts),
        'schedule_checks': build_schedule_checks(artifacts),
        'table_manifest_checks': build_table_manifest_checks(artifacts),
        'arithmetic_kernel_checks': build_arithmetic_kernel_checks(artifacts),
        'lookup_lowering_checks': build_lookup_lowering_checks(artifacts),
        'slot_allocation_checks': build_slot_allocation_checks(artifacts),
        'full_attack_inventory_checks': build_full_attack_inventory_checks(artifacts),
        'primitive_multiplier_checks': build_primitive_multiplier_checks(artifacts),
        'frontier_checks': build_frontier_checks(artifacts),
        'build_summary_checks': build_build_summary_checks(artifacts, repo_root),
        'cain_transfer_checks': build_cain_transfer_checks(artifacts),
        'azure_seed_checks': build_azure_seed_checks(artifacts),
    }


def build_verification_summary(case_count: int = 16, repo_root: Path | None = None) -> Dict[str, Any]:
    effective_root = repo_root or Path(__file__).resolve().parents[2]
    artifacts = load_compiler_artifacts(effective_root)
    semantic = run_full_raw32_semantic_check(case_count=case_count)
    integrity = build_integrity_report(effective_root, artifacts)
    semantic_checks = build_semantic_replay_checks(semantic, effective_root, case_count)
    invariant_groups = {
        **integrity,
        'semantic_replay_checks': semantic_checks,
    }
    invariant_total = sum(group['total'] for group in invariant_groups.values())
    invariant_pass = sum(group['pass'] for group in invariant_groups.values())
    return {
        'schema': 'compiler-project-verification-summary-v4',
        'semantic_replay': semantic,
        **invariant_groups,
        'summary': {
            'semantic_cases': {
                'total': semantic['summary']['total'],
                'pass': semantic['summary']['pass'],
            },
            'invariant_checks': {
                'total': invariant_total,
                'pass': invariant_pass,
            },
            'total': semantic['summary']['total'] + invariant_total,
            'pass': semantic['summary']['pass'] + invariant_pass,
        },
    }


def write_verification_summary(case_count: int = 16, repo_root: Path | None = None) -> Dict[str, Any]:
    effective_root = repo_root or Path(__file__).resolve().parents[2]
    summary = build_verification_summary(case_count=case_count, repo_root=effective_root)
    dump_json(effective_root / 'compiler_verification_project' / 'artifacts' / 'verification_summary.json', summary)
    return summary


def evaluate_mutated_verification_groups(artifacts: Mapping[str, Any], repo_root: Path | None = None) -> Dict[str, Any]:
    effective_root = repo_root or Path(__file__).resolve().parents[2]
    normalized = deepcopy(dict(artifacts))
    return build_integrity_report(effective_root, normalized)


__all__ = [
    'build_verification_summary',
    'write_verification_summary',
    'load_compiler_artifacts',
    'evaluate_mutated_verification_groups',
]
