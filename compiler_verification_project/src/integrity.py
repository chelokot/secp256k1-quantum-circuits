#!/usr/bin/env python3

from __future__ import annotations

import csv
import json
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
from arithmetic_lowering import arithmetic_kernel_summary, arithmetic_lowering_library
from lookup_lowering import lookup_lowering_library, lowered_lookup_semantic_summary, materialize_lookup_primitive_operations
from phase_shell_lowering import materialize_phase_operations, phase_shell_family_summary, phase_shell_lowering_library
from physical_estimator import (
    build_azure_estimator_target_payload,
    build_or_load_azure_estimator_results_payload,
)
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
    build_ft_ir_compositions_payload,
    build_generated_block_inventories_payload,
    build_qubit_breakthrough_analysis,
    exact_leaf_slot_allocation,
    full_attack_inventory,
    leaf_opcode_histogram,
    lookup_fed_leaf_slot_allocation,
    phase_shell_families,
    primitive_multiplier_library,
    raw32_schedule,
    slot_allocation_families,
    run_full_raw32_semantic_check,
    arithmetic_kernel_library,
    lookup_families,
    structured_raw32_cases,
    table_manifests,
    build_whole_oracle_recount_payload,
)
from subcircuit_equivalence import build_subcircuit_equivalence_artifact


def _check(name: str, passed: bool, expected: Any, observed: Any) -> Dict[str, Any]:
    def _compact_payload(payload: Any) -> Any:
        serialized = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        if len(serialized) <= 4096:
            return payload
        return {
            'summary': 'payload omitted from verification summary because it exceeds the inline size limit',
            'sha256': sha256_bytes(serialized.encode()),
            'size_bytes': len(serialized.encode()),
        }

    return {
        'name': name,
        'pass': int(passed),
        'expected': _compact_payload(expected),
        'observed': _compact_payload(observed),
    }


def _summarize_checks(checks: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        'pass': sum(check['pass'] for check in checks),
        'total': len(checks),
        'checks': checks,
    }


def _load_artifact(path: Path) -> Dict[str, Any]:
    return load_json(path)


def _primitive_counts_from_operations(primitive_operations: List[List[Any]]) -> Dict[str, int]:
    counts = {'ccx': 0, 'cx': 0, 'x': 0, 'measurement': 0}
    for operation in primitive_operations:
        counts[str(operation[0])] += 1
    return counts


def _phase_counts_from_operations(phase_operations: List[List[Any]]) -> Dict[str, int]:
    counts = {
        'hadamard': 0,
        'measurement': 0,
        'single_qubit_rotation': 0,
        'controlled_rotation': 0,
        'rotation_depth': 0,
    }
    for operation in phase_operations:
        gate = str(operation[0])
        counts[gate] += 1
        if gate in ('single_qubit_rotation', 'controlled_rotation'):
            counts['rotation_depth'] += 1
    return counts


def load_compiler_artifacts(repo_root: Path) -> Dict[str, Any]:
    artifact_root = repo_root / 'compiler_verification_project' / 'artifacts'
    required = {
        'canonical_public_point': artifact_root / 'canonical_public_point.json',
        'full_raw32_oracle': artifact_root / 'full_raw32_oracle.json',
        'exact_leaf_slot_allocation': artifact_root / 'exact_leaf_slot_allocation.json',
        'lookup_fed_leaf': artifact_root / 'lookup_fed_leaf.json',
        'lookup_fed_leaf_equivalence': artifact_root / 'lookup_fed_leaf_equivalence.json',
        'lookup_fed_leaf_slot_allocation': artifact_root / 'lookup_fed_leaf_slot_allocation.json',
        'interface_borrowed_leaf': artifact_root / 'interface_borrowed_leaf.json',
        'interface_borrowed_leaf_equivalence': artifact_root / 'interface_borrowed_leaf_equivalence.json',
        'interface_borrowed_leaf_slot_allocation': artifact_root / 'interface_borrowed_leaf_slot_allocation.json',
        'arithmetic_lowerings': artifact_root / 'arithmetic_lowerings.json',
        'module_library': artifact_root / 'module_library.json',
        'primitive_multiplier_library': artifact_root / 'primitive_multiplier_library.json',
        'phase_shell_lowerings': artifact_root / 'phase_shell_lowerings.json',
        'phase_shell_families': artifact_root / 'phase_shell_families.json',
        'table_manifests': artifact_root / 'table_manifests.json',
        'lookup_lowerings': artifact_root / 'lookup_lowerings.json',
        'generated_block_inventories': artifact_root / 'generated_block_inventories.json',
        'family_frontier': artifact_root / 'family_frontier.json',
        'qubit_breakthrough_analysis': artifact_root / 'qubit_breakthrough_analysis.json',
        'full_attack_inventory': artifact_root / 'full_attack_inventory.json',
        'ft_ir_compositions': artifact_root / 'ft_ir_compositions.json',
        'whole_oracle_recount': artifact_root / 'whole_oracle_recount.json',
        'subcircuit_equivalence': artifact_root / 'subcircuit_equivalence.json',
        'build_summary': artifact_root / 'build_summary.json',
        'cain_exact_transfer': artifact_root / 'cain_exact_transfer.json',
        'azure_resource_estimator_logical_counts': artifact_root / 'azure_resource_estimator_logical_counts.json',
        'azure_resource_estimator_targets': artifact_root / 'azure_resource_estimator_targets.json',
        'azure_resource_estimator_results': artifact_root / 'azure_resource_estimator_results.json',
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
    arithmetic_lowerings = artifacts['arithmetic_lowerings']
    expected_lowerings = arithmetic_lowering_library(
        field_bits=FIELD_BITS,
        leaf_opcode_histogram=leaf_opcode_histogram(),
    )
    expected_kernel = arithmetic_kernel_summary(expected_lowerings)
    kernel_lookup = {row['opcode']: row for row in arithmetic_lowerings['kernels']}
    reconstruction = arithmetic_lowerings['leaf_reconstruction']
    expected_leaf_non_clifford = (
        leaf_opcode_histogram().get('field_mul', 0) * kernel_lookup['field_mul']['exact_non_clifford_per_kernel']
        + leaf_opcode_histogram().get('field_add', 0) * kernel_lookup['field_add']['exact_non_clifford_per_kernel']
        + leaf_opcode_histogram().get('field_sub', 0) * kernel_lookup['field_sub']['exact_non_clifford_per_kernel']
        + leaf_opcode_histogram().get('mul_const', 0) * kernel_lookup['mul_const']['exact_non_clifford_per_kernel']
        + leaf_opcode_histogram().get('select_field_if_flag', 0) * kernel_lookup['select_field_if_flag']['exact_non_clifford_per_kernel']
    )
    block_operation_reconstruction = []
    stage_operation_reconstruction = []
    kernel_operation_reconstruction = []
    for lowering_kernel in arithmetic_lowerings['kernels']:
        for stage in lowering_kernel['stages']:
            stage_counts = {'ccx': 0, 'cx': 0, 'x': 0, 'measurement': 0}
            for block in stage['blocks']:
                block_counts = _primitive_counts_from_operations(block['primitive_operations'])
                block_operation_reconstruction.append({
                    'kernel': lowering_kernel['opcode'],
                    'stage': stage['name'],
                    'block': block['name'],
                    'expected': block['primitive_counts_total'],
                    'reconstructed': block_counts,
                })
                for key in stage_counts:
                    stage_counts[key] += int(block_counts[key])
            stage_operation_reconstruction.append({
                'kernel': lowering_kernel['opcode'],
                'stage': stage['name'],
                'expected': stage['primitive_counts_total'],
                'reconstructed': stage_counts,
            })
            kernel_operation_reconstruction.append({
                'kernel': lowering_kernel['opcode'],
                'stage': stage['name'],
                'primitive_counts_total': stage_counts,
            })
    kernel_totals_from_stages: Dict[str, Dict[str, int]] = defaultdict(lambda: {'ccx': 0, 'cx': 0, 'x': 0, 'measurement': 0})
    for row in kernel_operation_reconstruction:
        for key in kernel_totals_from_stages[row['kernel']]:
            kernel_totals_from_stages[row['kernel']][key] += int(row['primitive_counts_total'][key])
    checks = [
        _check('arithmetic_lowerings_match_generator', arithmetic_lowerings == expected_lowerings, expected_lowerings, arithmetic_lowerings),
        _check('module_library_matches_lowering_summary', kernel == expected_kernel, expected_kernel, kernel),
        _check('module_library_matches_project_summary', kernel == arithmetic_kernel_library(), arithmetic_kernel_library(), kernel),
        _check(
            'arithmetic_block_totals_reconstruct_from_generated_operations',
            all(row['expected'] == row['reconstructed'] for row in block_operation_reconstruction),
            [row['expected'] for row in block_operation_reconstruction],
            [row['reconstructed'] for row in block_operation_reconstruction],
        ),
        _check(
            'arithmetic_stage_totals_reconstruct_from_block_operations',
            all(row['expected'] == row['reconstructed'] for row in stage_operation_reconstruction),
            [row['expected'] for row in stage_operation_reconstruction],
            [row['reconstructed'] for row in stage_operation_reconstruction],
        ),
        _check(
            'arithmetic_kernel_totals_reconstruct_from_stage_operations',
            all(kernel_lookup[opcode]['primitive_counts_total'] == totals for opcode, totals in kernel_totals_from_stages.items()),
            {opcode: kernel_lookup[opcode]['primitive_counts_total'] for opcode in kernel_totals_from_stages},
            dict(kernel_totals_from_stages),
        ),
        _check('field_add_cost_matches_lowering_kernel', kernel['field_add_non_clifford'] == kernel_lookup['field_add']['exact_non_clifford_per_kernel'], kernel_lookup['field_add']['exact_non_clifford_per_kernel'], kernel['field_add_non_clifford']),
        _check('field_mul_cost_matches_lowering_kernel', kernel['field_mul_non_clifford'] == kernel_lookup['field_mul']['exact_non_clifford_per_kernel'], kernel_lookup['field_mul']['exact_non_clifford_per_kernel'], kernel['field_mul_non_clifford']),
        _check('mul_const_cost_matches_lowering_kernel', kernel['mul_const_non_clifford'] == kernel_lookup['mul_const']['exact_non_clifford_per_kernel'], kernel_lookup['mul_const']['exact_non_clifford_per_kernel'], kernel['mul_const_non_clifford']),
        _check('leaf_opcode_histogram_matches_lowering_reconstruction', kernel['leaf_opcode_histogram'] == reconstruction['leaf_opcode_histogram'], reconstruction['leaf_opcode_histogram'], kernel['leaf_opcode_histogram']),
        _check(
            'arithmetic_leaf_non_clifford_matches_lowering_reconstruction',
            kernel['arithmetic_leaf_non_clifford'] == reconstruction['arithmetic_leaf_non_clifford'] == expected_leaf_non_clifford,
            expected_leaf_non_clifford,
            kernel['arithmetic_leaf_non_clifford'],
        ),
    ]
    return _summarize_checks(checks)


def build_cleanup_pair_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    leaf = _leaf()
    hist = artifacts['module_library']['leaf_opcode_histogram']
    extract_ops = [ins for ins in leaf['instructions'] if ins['op'] == 'bool_from_flag']
    cleanup_ops = [ins for ins in leaf['instructions'] if ins['op'] == 'clear_bool_from_flag']
    select_ops = [ins for ins in leaf['instructions'] if ins['op'] == 'select_field_if_flag' and ins.get('flag') == 'f_lookup_inf']
    extract = extract_ops[0] if extract_ops else None
    cleanup = cleanup_ops[0] if cleanup_ops else None
    cleanup_window = (
        [extract['pc'], cleanup['pc']]
        if extract is not None and cleanup is not None
        else None
    )
    expected_select_pcs = [33, 34, 35]
    observed_select_pcs = [ins['pc'] for ins in select_ops]
    checks = [
        _check('single_flag_extract_exists', len(extract_ops) == 1, 1, len(extract_ops)),
        _check('single_flag_cleanup_exists', len(cleanup_ops) == 1, 1, len(cleanup_ops)),
        _check(
            'cleanup_reuses_same_flag_source_and_destination',
            extract is not None and cleanup is not None and extract['dst'] == cleanup['dst'] and extract['src'] == cleanup['src'],
            {
                'dst': extract['dst'] if extract is not None else None,
                'src': extract['src'] if extract is not None else None,
            },
            {
                'dst': cleanup['dst'] if cleanup is not None else None,
                'src': cleanup['src'] if cleanup is not None else None,
            },
        ),
        _check('neutral_entry_selects_cover_xyz', observed_select_pcs == expected_select_pcs, expected_select_pcs, observed_select_pcs),
        _check(
            'cleanup_brackets_only_the_neutral_entry_select_window',
            extract is not None and cleanup is not None and all(extract['pc'] < ins['pc'] < cleanup['pc'] for ins in select_ops),
            'extract pc < select pcs < cleanup pc',
            cleanup_window,
        ),
        _check('leaf_histogram_uses_explicit_cleanup_opcode', hist.get('clear_bool_from_flag', 0) == 1, 1, hist.get('clear_bool_from_flag', 0)),
        _check('legacy_cleanup_opcode_is_absent', 'mbuc_clear_bool' not in hist, False, 'mbuc_clear_bool' in hist),
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
    block_operation_reconstruction = []
    stage_operation_reconstruction = []
    for family in families:
        stages = family['stages']
        persistent_total = sum(int(entry['qubits']) for entry in family['persistent_workspace'])
        family_primitive_totals = {'ccx': 0, 'cx': 0, 'x': 0, 'measurement': 0}
        for stage in stages:
            stage_counts = {'ccx': 0, 'cx': 0, 'x': 0, 'measurement': 0}
            for block in stage['blocks']:
                block_counts = _primitive_counts_from_operations(materialize_lookup_primitive_operations(block['primitive_operation_generator']))
                block_operation_reconstruction.append({
                    'family': family['name'],
                    'stage': stage['name'],
                    'block': block['name'],
                    'expected': block['primitive_counts_total'],
                    'reconstructed': block_counts,
                })
                for key in stage_counts:
                    stage_counts[key] += int(block_counts[key])
            stage_operation_reconstruction.append({
                'family': family['name'],
                'stage': stage['name'],
                'expected': stage['primitive_counts_total'],
                'reconstructed': stage_counts,
            })
            for key in family_primitive_totals:
                family_primitive_totals[key] += int(stage_counts[key])
        reconstructed_non_clifford = family_primitive_totals['ccx']
        reconstructed_workspace = max(int(stage['total_workspace_qubits']) for stage in stages)
        reconstructed_family_totals.append({
            'name': family['name'],
            'direct_lookup_non_clifford': reconstructed_non_clifford,
            'per_leaf_lookup_non_clifford': reconstructed_non_clifford,
            'primitive_counts_total': family_primitive_totals,
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
            'lookup_block_totals_reconstruct_from_generated_operations',
            all(row['expected'] == row['reconstructed'] for row in block_operation_reconstruction),
            [row['expected'] for row in block_operation_reconstruction],
            [row['reconstructed'] for row in block_operation_reconstruction],
        ),
        _check(
            'lookup_stage_totals_reconstruct_from_block_operations',
            all(row['expected'] == row['reconstructed'] for row in stage_operation_reconstruction),
            [row['expected'] for row in stage_operation_reconstruction],
            [row['reconstructed'] for row in stage_operation_reconstruction],
        ),
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
                and family_lookup[row['name']]['primitive_counts_total'] == row['primitive_counts_total']
                for row in reconstructed_family_totals
            ),
            reconstructed_family_totals,
            [
                {
                    'name': family['name'],
                    'direct_lookup_non_clifford': family['direct_lookup_non_clifford'],
                    'per_leaf_lookup_non_clifford': family['per_leaf_lookup_non_clifford'],
                    'primitive_counts_total': family['primitive_counts_total'],
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


def build_phase_shell_lowering_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    lowerings = artifacts['phase_shell_lowerings']
    summary = artifacts['phase_shell_families']
    expected_lowerings = phase_shell_lowering_library(FULL_PHASE_REGISTER_BITS)
    expected_summary = phase_shell_family_summary(expected_lowerings)
    families = {row['name']: row for row in lowerings['families']}
    full_family = families['full_phase_register_v1']
    semiclassical_family = families['semiclassical_qft_v1']
    expected_full_rotations = FULL_PHASE_REGISTER_BITS * (FULL_PHASE_REGISTER_BITS - 1) // 2
    expected_semiclassical_rotations = FULL_PHASE_REGISTER_BITS - 1
    block_operation_reconstruction = []
    stage_operation_reconstruction = []
    family_operation_reconstruction = []
    for family in lowerings['families']:
        family_counts = {
            'hadamard': 0,
            'measurement': 0,
            'single_qubit_rotation': 0,
            'controlled_rotation': 0,
            'rotation_depth': 0,
        }
        for stage in family['stages']:
            stage_counts = {
                'hadamard': 0,
                'measurement': 0,
                'single_qubit_rotation': 0,
                'controlled_rotation': 0,
                'rotation_depth': 0,
            }
            for block in stage['blocks']:
                block_counts = _phase_counts_from_operations(materialize_phase_operations(block['phase_operation_generator']))
                block_operation_reconstruction.append({
                    'family': family['name'],
                    'stage': stage['name'],
                    'block': block['name'],
                    'expected': block['count_profile_total'],
                    'reconstructed': block_counts,
                })
                for key in stage_counts:
                    stage_counts[key] += int(block_counts[key])
            stage_operation_reconstruction.append({
                'family': family['name'],
                'stage': stage['name'],
                'expected': stage['count_profile_total'],
                'reconstructed': stage_counts,
            })
            for key in family_counts:
                family_counts[key] += int(stage_counts[key])
        family_operation_reconstruction.append({
            'name': family['name'],
            'hadamard_count': family_counts['hadamard'],
            'measurement_count': family_counts['measurement'],
            'rotation_count': family_counts['single_qubit_rotation'] + family_counts['controlled_rotation'],
            'rotation_depth': family_counts['rotation_depth'],
            'single_qubit_rotation_count': family_counts['single_qubit_rotation'],
            'controlled_rotation_count': family_counts['controlled_rotation'],
        })
    checks = [
        _check('phase_shell_lowerings_match_generator', lowerings == expected_lowerings, expected_lowerings, lowerings),
        _check('phase_shell_family_summary_matches_lowerings', summary == expected_summary, expected_summary, summary),
        _check(
            'phase_shell_block_totals_reconstruct_from_generated_operations',
            all(row['expected'] == row['reconstructed'] for row in block_operation_reconstruction),
            [row['expected'] for row in block_operation_reconstruction],
            [row['reconstructed'] for row in block_operation_reconstruction],
        ),
        _check(
            'phase_shell_stage_totals_reconstruct_from_block_operations',
            all(row['expected'] == row['reconstructed'] for row in stage_operation_reconstruction),
            [row['expected'] for row in stage_operation_reconstruction],
            [row['reconstructed'] for row in stage_operation_reconstruction],
        ),
        _check(
            'phase_shell_family_totals_reconstruct_from_generated_operations',
            all(
                families[row['name']]['hadamard_count'] == row['hadamard_count']
                and families[row['name']]['measurement_count'] == row['measurement_count']
                and families[row['name']]['rotation_count'] == row['rotation_count']
                and families[row['name']]['rotation_depth'] == row['rotation_depth']
                and families[row['name']]['single_qubit_rotation_count'] == row['single_qubit_rotation_count']
                and families[row['name']]['controlled_rotation_count'] == row['controlled_rotation_count']
                for row in family_operation_reconstruction
            ),
            family_operation_reconstruction,
            [
                {
                    'name': family['name'],
                    'hadamard_count': family['hadamard_count'],
                    'measurement_count': family['measurement_count'],
                    'rotation_count': family['rotation_count'],
                    'rotation_depth': family['rotation_depth'],
                    'single_qubit_rotation_count': family['single_qubit_rotation_count'],
                    'controlled_rotation_count': family['controlled_rotation_count'],
                }
                for family in lowerings['families']
            ],
        ),
        _check(
            'full_phase_register_rotation_ladder_matches_bit_pair_count',
            full_family['rotation_count'] == expected_full_rotations and full_family['controlled_rotation_count'] == expected_full_rotations,
            expected_full_rotations,
            {
                'rotation_count': full_family['rotation_count'],
                'controlled_rotation_count': full_family['controlled_rotation_count'],
            },
        ),
        _check(
            'semiclassical_phase_updates_match_noninitial_bit_count',
            semiclassical_family['rotation_count'] == expected_semiclassical_rotations and semiclassical_family['single_qubit_rotation_count'] == expected_semiclassical_rotations,
            expected_semiclassical_rotations,
            {
                'rotation_count': semiclassical_family['rotation_count'],
                'single_qubit_rotation_count': semiclassical_family['single_qubit_rotation_count'],
            },
        ),
        _check(
            'phase_shell_hadamards_and_measurements_match_phase_bits',
            all(
                family['hadamard_count'] == FULL_PHASE_REGISTER_BITS
                and family['measurement_count'] == FULL_PHASE_REGISTER_BITS
                for family in lowerings['families']
            ),
            FULL_PHASE_REGISTER_BITS,
            [
                {
                    'name': family['name'],
                    'hadamard_count': family['hadamard_count'],
                    'measurement_count': family['measurement_count'],
                }
                for family in lowerings['families']
            ],
        ),
        _check(
            'semiclassical_phase_shell_uses_strictly_fewer_live_qubits_and_rotations',
            semiclassical_family['live_quantum_bits'] < full_family['live_quantum_bits']
            and semiclassical_family['rotation_count'] < full_family['rotation_count'],
            {
                'live_quantum_bits': full_family['live_quantum_bits'],
                'rotation_count': full_family['rotation_count'],
            },
            {
                'live_quantum_bits': semiclassical_family['live_quantum_bits'],
                'rotation_count': semiclassical_family['rotation_count'],
            },
        ),
    ]
    return _summarize_checks(checks)


def build_generated_block_inventory_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    generated = artifacts['generated_block_inventories']
    expected = build_generated_block_inventories_payload(
        schedule=artifacts['full_raw32_oracle'],
        kernel=artifacts['module_library'],
        arithmetic_lowerings=artifacts['arithmetic_lowerings'],
        lookup_lowerings=artifacts['lookup_lowerings'],
        phase_shells=artifacts['phase_shell_lowerings']['families'],
        field_bits=FIELD_BITS,
        public_google_baseline=artifacts['family_frontier']['public_google_baseline'],
    )
    families = generated['families']
    frontier_lookup = {row['name']: row for row in artifacts['family_frontier']['families']}
    reconstruction_rows = []
    arithmetic_whole_oracle_non_clifford = sum(
        int(block['primitive_counts_total']['ccx'])
        for block in generated['shared_arithmetic_blocks']
    )
    for family in families:
        primitive_totals = {
            key: sum(int(block['primitive_counts_total'][key]) for block in family['non_clifford_blocks'])
            for key in ('ccx', 'cx', 'x', 'measurement')
        }
        qubit_total = sum(int(block['logical_qubits']) for block in family['qubit_blocks'])
        phase_hadamards = sum(int(block['count']) for block in family['phase_count_blocks'] if block['category'] == 'phase_hadamards')
        phase_measurements = sum(int(block['count']) for block in family['phase_count_blocks'] if block['category'] == 'phase_measurements')
        phase_rotations = sum(
            int(block['count'])
            for block in family['phase_count_blocks']
            if block['category'] in ('phase_single_qubit_rotations', 'phase_controlled_rotations')
        )
        phase_rotation_depth = sum(int(block['count']) for block in family['phase_count_blocks'] if block['category'] == 'phase_rotation_depth')
        direct_seed_non_clifford = sum(
            int(block['primitive_counts_total']['ccx'])
            for block in family['non_clifford_blocks']
            if block['metadata'].get('invocation_scope') == 'direct_seed'
        )
        repeated_leaf_lookup_non_clifford = sum(
            int(block['primitive_counts_total']['ccx'])
            for block in family['non_clifford_blocks']
            if block['metadata'].get('invocation_scope') == 'repeated_leaf_calls'
            and block['category'] == 'lookup_non_clifford'
        )
        reconstruction_rows.append(
            {
                'name': family['name'],
                'full_oracle_non_clifford': primitive_totals['ccx'],
                'total_logical_qubits': qubit_total,
                'direct_seed_non_clifford': direct_seed_non_clifford,
                'per_leaf_lookup_non_clifford': repeated_leaf_lookup_non_clifford // artifacts['full_raw32_oracle']['summary']['leaf_call_count_total'],
                'phase_shell_hadamards': phase_hadamards,
                'phase_shell_measurements': phase_measurements,
                'phase_shell_rotations': phase_rotations,
                'phase_shell_rotation_depth': phase_rotation_depth,
            }
        )
    checks = [
        _check('generated_block_inventories_match_generator', generated == expected, expected, generated),
        _check(
            'generated_block_inventory_schema_matches_current_version',
            generated['schema'] == 'compiler-project-generated-block-inventories-v2',
            'compiler-project-generated-block-inventories-v2',
            generated['schema'],
        ),
        _check(
            'generated_block_inventory_source_paths_match_expected',
            generated['source_artifacts'] == {
                'full_raw32_oracle': 'compiler_verification_project/artifacts/full_raw32_oracle.json',
                'slot_allocations': [row.source_artifact for row in slot_allocation_families()],
                'arithmetic_lowerings': 'compiler_verification_project/artifacts/arithmetic_lowerings.json',
                'lookup_lowerings': 'compiler_verification_project/artifacts/lookup_lowerings.json',
                'phase_shell_lowerings': 'compiler_verification_project/artifacts/phase_shell_lowerings.json',
            },
            {
                'full_raw32_oracle': 'compiler_verification_project/artifacts/full_raw32_oracle.json',
                'slot_allocations': [row.source_artifact for row in slot_allocation_families()],
                'arithmetic_lowerings': 'compiler_verification_project/artifacts/arithmetic_lowerings.json',
                'lookup_lowerings': 'compiler_verification_project/artifacts/lookup_lowerings.json',
                'phase_shell_lowerings': 'compiler_verification_project/artifacts/phase_shell_lowerings.json',
            },
            generated['source_artifacts'],
        ),
        _check(
            'generated_block_inventory_arithmetic_family_matches_arithmetic_lowerings',
            generated['arithmetic_lowering_family'] == artifacts['arithmetic_lowerings']['family'],
            artifacts['arithmetic_lowerings']['family'],
            generated['arithmetic_lowering_family'],
        ),
        _check(
            'shared_arithmetic_blocks_match_leaf_reconstruction_times_schedule',
            arithmetic_whole_oracle_non_clifford
            == artifacts['arithmetic_lowerings']['leaf_reconstruction']['arithmetic_leaf_non_clifford']
            * artifacts['full_raw32_oracle']['summary']['leaf_call_count_total'],
            artifacts['arithmetic_lowerings']['leaf_reconstruction']['arithmetic_leaf_non_clifford']
            * artifacts['full_raw32_oracle']['summary']['leaf_call_count_total'],
            arithmetic_whole_oracle_non_clifford,
        ),
        _check(
            'generated_block_inventory_family_reconstruction_matches_blocks',
            all(
                next(row for row in reconstruction_rows if row['name'] == family['name'])['full_oracle_non_clifford'] == family['reconstruction']['full_oracle_non_clifford']
                and next(row for row in reconstruction_rows if row['name'] == family['name'])['total_logical_qubits'] == family['reconstruction']['total_logical_qubits']
                and next(row for row in reconstruction_rows if row['name'] == family['name'])['direct_seed_non_clifford'] == family['reconstruction']['direct_seed_non_clifford']
                and next(row for row in reconstruction_rows if row['name'] == family['name'])['per_leaf_lookup_non_clifford'] == family['reconstruction']['per_leaf_lookup_non_clifford']
                and next(row for row in reconstruction_rows if row['name'] == family['name'])['phase_shell_hadamards'] == family['reconstruction']['phase_shell_hadamards']
                and next(row for row in reconstruction_rows if row['name'] == family['name'])['phase_shell_measurements'] == family['reconstruction']['phase_shell_measurements']
                and next(row for row in reconstruction_rows if row['name'] == family['name'])['phase_shell_rotations'] == family['reconstruction']['phase_shell_rotations']
                and next(row for row in reconstruction_rows if row['name'] == family['name'])['phase_shell_rotation_depth'] == family['reconstruction']['phase_shell_rotation_depth']
                for family in families
            ),
            reconstruction_rows,
            [family['reconstruction'] for family in families],
        ),
        _check(
            'frontier_family_totals_match_generated_block_reconstruction',
            all(
                frontier_lookup[family['name']]['full_oracle_non_clifford'] == family['reconstruction']['full_oracle_non_clifford']
                and frontier_lookup[family['name']]['total_logical_qubits'] == family['reconstruction']['total_logical_qubits']
                for family in families
            ),
            [family['reconstruction'] for family in families],
            [
                {
                    'name': family['name'],
                    'full_oracle_non_clifford': frontier_lookup[family['name']]['full_oracle_non_clifford'],
                    'total_logical_qubits': frontier_lookup[family['name']]['total_logical_qubits'],
                }
                for family in families
            ],
        ),
        _check(
            'generated_block_inventory_best_families_match_frontier',
            generated['best_gate_family']['name'] == artifacts['family_frontier']['best_gate_family']['name']
            and generated['best_qubit_family']['name'] == artifacts['family_frontier']['best_qubit_family']['name'],
            {
                'best_gate_family': artifacts['family_frontier']['best_gate_family']['name'],
                'best_qubit_family': artifacts['family_frontier']['best_qubit_family']['name'],
            },
            generated['best_gate_family'] | {'best_qubit_family': generated['best_qubit_family']['name']},
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


def _build_slot_allocation_checks(
    slot_alloc: Mapping[str, Any],
    expected_slot_alloc: Mapping[str, Any],
    leaf: Mapping[str, Any],
    arithmetic_registers: List[str],
    control_registers: List[str],
) -> Dict[str, Any]:
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
    assigned_arithmetic_span = 1 + max(entry['assigned_slot'] for entry in slot_alloc['versions'] if entry['reg_type'] == 'arithmetic')
    assigned_control_span = 1 + max(entry['assigned_slot'] for entry in slot_alloc['versions'] if entry['reg_type'] == 'control')
    checks = [
        _check('slot_allocation_matches_generator', slot_alloc == expected_slot_alloc, expected_slot_alloc, slot_alloc),
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
            'peak_arithmetic_slots_match_reconstructed_live_set',
            slot_alloc['peak_arithmetic_slots']['count'] == reconstructed_peak_arithmetic,
            reconstructed_peak_arithmetic,
            slot_alloc['peak_arithmetic_slots']['count'],
        ),
        _check(
            'allocator_summary_arithmetic_slot_span_matches_assigned_versions',
            slot_alloc['allocator_summary']['exact_arithmetic_slot_count'] == assigned_arithmetic_span,
            assigned_arithmetic_span,
            slot_alloc['allocator_summary']['exact_arithmetic_slot_count'],
        ),
        _check(
            'peak_control_slots_match_reconstructed_live_set',
            slot_alloc['peak_control_slots']['count'] == reconstructed_peak_control,
            reconstructed_peak_control,
            slot_alloc['peak_control_slots']['count'],
        ),
        _check(
            'allocator_summary_control_slot_span_matches_assigned_versions',
            slot_alloc['allocator_summary']['exact_control_slot_count'] == assigned_control_span,
            assigned_control_span,
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


def build_slot_allocation_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    register_map = _register_map()
    return _build_slot_allocation_checks(
        slot_alloc=artifacts['exact_leaf_slot_allocation'],
        expected_slot_alloc=exact_leaf_slot_allocation(),
        leaf=_leaf(),
        arithmetic_registers=sorted(register_map['arithmetic_slots']),
        control_registers=sorted(register_map['auxiliary_control_slots']),
    )


def build_lookup_fed_slot_allocation_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    slot_alloc = artifacts['lookup_fed_leaf_slot_allocation']
    return _build_slot_allocation_checks(
        slot_alloc=slot_alloc,
        expected_slot_alloc=lookup_fed_leaf_slot_allocation(),
        leaf=artifacts['lookup_fed_leaf'],
        arithmetic_registers=sorted(slot_alloc['tracked_arithmetic_registers']),
        control_registers=sorted(slot_alloc['tracked_control_registers']),
    )


def build_qubit_breakthrough_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    analysis = artifacts['qubit_breakthrough_analysis']
    best_qubit = artifacts['family_frontier']['best_qubit_family']
    fixed_non_arithmetic_overhead = (
        int(best_qubit['lookup_workspace_qubits'])
        + int(best_qubit['control_slot_count'])
        + int(best_qubit['live_phase_bits'])
    )
    slot_family_name = best_qubit['slot_allocation_family']
    slot_alloc = next(
        row['slot_allocation']
        for row in artifacts['family_frontier']['slot_allocation_families']
        if row['name'] == slot_family_name
    )
    expected = build_qubit_breakthrough_analysis(
        frontier=artifacts['family_frontier'],
        slot_allocation=slot_alloc,
    )
    checks = [
        _check(
            'qubit_breakthrough_analysis_matches_generator',
            analysis == expected,
            expected,
            analysis,
        ),
        _check(
            'qubit_breakthrough_exact_breakdown_matches_frontier_best_qubit_family',
            analysis['exact_component_breakdown']['arithmetic_register_file_qubits']
            == int(best_qubit['arithmetic_slot_count']) * FIELD_BITS
            and analysis['exact_component_breakdown']['fixed_non_arithmetic_overhead_qubits'] == fixed_non_arithmetic_overhead,
            {
                'arithmetic_register_file_qubits': int(best_qubit['arithmetic_slot_count']) * FIELD_BITS,
                'fixed_non_arithmetic_overhead_qubits': fixed_non_arithmetic_overhead,
            },
            {
                'arithmetic_register_file_qubits': analysis['exact_component_breakdown']['arithmetic_register_file_qubits'],
                'fixed_non_arithmetic_overhead_qubits': analysis['exact_component_breakdown']['fixed_non_arithmetic_overhead_qubits'],
            },
        ),
        _check(
            'qubit_breakthrough_google_thresholds_match_exact_frontier_math',
            analysis['baseline_thresholds'] == {
                name: {
                    'baseline_logical_qubits': int(row['logical_qubits']),
                    'max_arithmetic_slots_at_current_field_width': (int(row['logical_qubits']) - fixed_non_arithmetic_overhead) // FIELD_BITS,
                    'max_field_slot_logical_qubits_at_current_exact_slot_count': (int(row['logical_qubits']) - fixed_non_arithmetic_overhead) // int(best_qubit['arithmetic_slot_count']),
                }
                for name, row in artifacts['family_frontier']['public_google_baseline'].items()
            },
            {
                name: {
                    'baseline_logical_qubits': int(row['logical_qubits']),
                    'max_arithmetic_slots_at_current_field_width': (int(row['logical_qubits']) - fixed_non_arithmetic_overhead) // FIELD_BITS,
                    'max_field_slot_logical_qubits_at_current_exact_slot_count': (int(row['logical_qubits']) - fixed_non_arithmetic_overhead) // int(best_qubit['arithmetic_slot_count']),
                }
                for name, row in artifacts['family_frontier']['public_google_baseline'].items()
            },
            analysis['baseline_thresholds'],
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
        _check(
            'full_attack_inventory_phase_shell_lowering_path_matches_expected',
            inventory['phase_shell_lowering_artifact'] == 'compiler_verification_project/artifacts/phase_shell_lowerings.json',
            'compiler_verification_project/artifacts/phase_shell_lowerings.json',
            inventory['phase_shell_lowering_artifact'],
        ),
        _check(
            'full_attack_inventory_generated_block_summary_matches_generated_block_inventory',
            inventory['generated_block_inventory_summary'] == {
                'best_gate_family': artifacts['generated_block_inventories']['best_gate_family'],
                'best_qubit_family': artifacts['generated_block_inventories']['best_qubit_family'],
                'family_reconstructed_totals': [
                    {
                        'name': row['name'],
                        'full_oracle_non_clifford': row['reconstruction']['full_oracle_non_clifford'],
                        'total_logical_qubits': row['reconstruction']['total_logical_qubits'],
                    }
                    for row in artifacts['generated_block_inventories']['families']
                ],
            },
            {
                'best_gate_family': artifacts['generated_block_inventories']['best_gate_family'],
                'best_qubit_family': artifacts['generated_block_inventories']['best_qubit_family'],
                'family_reconstructed_totals': [
                    {
                        'name': row['name'],
                        'full_oracle_non_clifford': row['reconstruction']['full_oracle_non_clifford'],
                        'total_logical_qubits': row['reconstruction']['total_logical_qubits'],
                    }
                    for row in artifacts['generated_block_inventories']['families']
                ],
            },
            inventory['generated_block_inventory_summary'],
        ),
        _check(
            'full_attack_inventory_recount_summary_matches_frontier',
            inventory['whole_oracle_recount_summary'] == {
                'best_gate_family': artifacts['family_frontier']['best_gate_family'],
                'best_qubit_family': artifacts['family_frontier']['best_qubit_family'],
                'family_recount_totals': [
                    {
                        'name': row['name'],
                        'full_oracle_non_clifford': row['full_oracle_non_clifford'],
                        'total_logical_qubits': row['total_logical_qubits'],
                    }
                    for row in artifacts['family_frontier']['families']
                ],
            },
            {
                'best_gate_family': artifacts['family_frontier']['best_gate_family'],
                'best_qubit_family': artifacts['family_frontier']['best_qubit_family'],
                'family_recount_totals': [
                    {
                        'name': row['name'],
                        'full_oracle_non_clifford': row['full_oracle_non_clifford'],
                        'total_logical_qubits': row['total_logical_qubits'],
                    }
                    for row in artifacts['family_frontier']['families']
                ],
            },
            inventory['whole_oracle_recount_summary'],
        ),
        _check('inventory_best_gate_family_matches_frontier', inventory['best_gate_family'] == artifacts['family_frontier']['best_gate_family'], artifacts['family_frontier']['best_gate_family'], inventory['best_gate_family']),
        _check('inventory_best_qubit_family_matches_frontier', inventory['best_qubit_family'] == artifacts['family_frontier']['best_qubit_family'], artifacts['family_frontier']['best_qubit_family'], inventory['best_qubit_family']),
    ]
    return _summarize_checks(checks)


def build_ft_ir_checks(artifacts: Mapping[str, Any], repo_root: Path) -> Dict[str, Any]:
    ft_ir = artifacts['ft_ir_compositions']
    expected = build_ft_ir_compositions_payload(
        schedule=artifacts['full_raw32_oracle'],
        arithmetic_lowerings=artifacts['arithmetic_lowerings'],
        lookup_lowerings=artifacts['lookup_lowerings'],
        phase_shells=artifacts['phase_shell_lowerings']['families'],
        generated_block_inventories=artifacts['generated_block_inventories'],
        frontier=artifacts['family_frontier'],
        field_bits=FIELD_BITS,
    )
    family_failures = []
    root_failures = []
    source_path_failures = []
    for path in ft_ir['source_artifacts'].values():
        path_rows = path if isinstance(path, list) else [path]
        for path_row in path_rows:
            if not (repo_root / path_row).exists():
                source_path_failures.append(path_row)
    for family in ft_ir['families']:
        graph = family['graph']
        summary = graph['summary']
        leaf_sigma = family['leaf_sigma']
        if not (
            graph['root'] == 'full_oracle'
            and summary['root_in_degree'] == 0
            and summary['reachable_node_count'] == summary['node_count']
        ):
            root_failures.append(family['name'])
        primitive_from_sigma = {'ccx': 0, 'cx': 0, 'x': 0, 'measurement': 0}
        logical_qubits_from_sigma = 0
        phase_hadamards_from_sigma = 0
        phase_measurements_from_sigma = 0
        phase_rotations_from_sigma = 0
        phase_rotation_depth_from_sigma = 0
        for entry in leaf_sigma:
            semantics = entry['resource_profile']['resource_semantics']
            if semantics == 'additive_primitive':
                for key in primitive_from_sigma:
                    primitive_from_sigma[key] += int(entry['primitive_counts_total'][key])
            elif semantics == 'peak_live_qubits':
                logical_qubits_from_sigma += int(entry['logical_qubits_total'])
            elif semantics == 'additive_phase_hadamards':
                phase_hadamards_from_sigma += int(entry['count_total'])
            elif semantics == 'additive_phase_measurements':
                phase_measurements_from_sigma += int(entry['count_total'])
            elif semantics == 'additive_phase_rotations':
                phase_rotations_from_sigma += int(entry['count_total'])
            elif semantics == 'additive_phase_rotation_depth':
                phase_rotation_depth_from_sigma += int(entry['count_total'])
        reconstruction = family['reconstruction']
        if not (
            primitive_from_sigma == reconstruction['primitive_totals']
            and primitive_from_sigma['ccx'] == reconstruction['full_oracle_non_clifford']
            and logical_qubits_from_sigma == reconstruction['total_logical_qubits']
            and phase_hadamards_from_sigma == reconstruction['phase_shell_hadamards']
            and phase_measurements_from_sigma == reconstruction['phase_shell_measurements']
            and phase_rotations_from_sigma == reconstruction['phase_shell_rotations']
            and phase_rotation_depth_from_sigma == reconstruction['phase_shell_rotation_depth']
            and reconstruction == family['generated_block_inventory_reconstruction']
            and reconstruction['full_oracle_non_clifford'] == family['frontier_reconstruction']['full_oracle_non_clifford']
            and reconstruction['total_logical_qubits'] == family['frontier_reconstruction']['total_logical_qubits']
        ):
            family_failures.append(family['name'])
    checks = [
        _check('ft_ir_compositions_match_generator', ft_ir == expected, expected, ft_ir),
        _check(
            'ft_ir_schema_matches_current_version',
            ft_ir['schema'] == 'compiler-project-ft-ir-v2',
            'compiler-project-ft-ir-v2',
            ft_ir['schema'],
        ),
        _check(
            'ft_ir_source_paths_match_expected',
            ft_ir['source_artifacts'] == {
                'full_raw32_oracle': 'compiler_verification_project/artifacts/full_raw32_oracle.json',
                'slot_allocations': [row.source_artifact for row in slot_allocation_families()],
                'arithmetic_lowerings': 'compiler_verification_project/artifacts/arithmetic_lowerings.json',
                'lookup_lowerings': 'compiler_verification_project/artifacts/lookup_lowerings.json',
                'phase_shell_lowerings': 'compiler_verification_project/artifacts/phase_shell_lowerings.json',
                'generated_block_inventories': 'compiler_verification_project/artifacts/generated_block_inventories.json',
                'family_frontier': 'compiler_verification_project/artifacts/family_frontier.json',
            },
            {
                'full_raw32_oracle': 'compiler_verification_project/artifacts/full_raw32_oracle.json',
                'slot_allocations': [row.source_artifact for row in slot_allocation_families()],
                'arithmetic_lowerings': 'compiler_verification_project/artifacts/arithmetic_lowerings.json',
                'lookup_lowerings': 'compiler_verification_project/artifacts/lookup_lowerings.json',
                'phase_shell_lowerings': 'compiler_verification_project/artifacts/phase_shell_lowerings.json',
                'generated_block_inventories': 'compiler_verification_project/artifacts/generated_block_inventories.json',
                'family_frontier': 'compiler_verification_project/artifacts/family_frontier.json',
            },
            ft_ir['source_artifacts'],
        ),
        _check('ft_ir_source_paths_exist_on_disk', len(source_path_failures) == 0, [], source_path_failures),
        _check('ft_ir_family_graphs_are_rooted_and_reachable', len(root_failures) == 0, [], root_failures),
        _check('ft_ir_leaf_sigma_reconstructs_generated_totals', len(family_failures) == 0, [], family_failures),
        _check(
            'ft_ir_best_families_match_generated_inventory',
            ft_ir['best_gate_family']['name'] == artifacts['generated_block_inventories']['best_gate_family']['name']
            and ft_ir['best_qubit_family']['name'] == artifacts['generated_block_inventories']['best_qubit_family']['name']
            and ft_ir['best_gate_family']['reconstruction']['full_oracle_non_clifford']
            == artifacts['generated_block_inventories']['best_gate_family']['reconstruction']['full_oracle_non_clifford']
            and ft_ir['best_qubit_family']['reconstruction']['total_logical_qubits']
            == artifacts['generated_block_inventories']['best_qubit_family']['reconstruction']['total_logical_qubits'],
            {
                'best_gate_family': artifacts['generated_block_inventories']['best_gate_family'],
                'best_qubit_family': artifacts['generated_block_inventories']['best_qubit_family'],
            },
            {
                'best_gate_family': ft_ir['best_gate_family'],
                'best_qubit_family': ft_ir['best_qubit_family'],
            },
        ),
    ]
    return _summarize_checks(checks)


def build_whole_oracle_recount_checks(artifacts: Mapping[str, Any], repo_root: Path) -> Dict[str, Any]:
    recount = artifacts['whole_oracle_recount']
    expected = build_whole_oracle_recount_payload(
        ft_ir_compositions=artifacts['ft_ir_compositions'],
        public_google_baseline=artifacts['family_frontier']['public_google_baseline'],
    )
    source_path_failures = [
        path
        for path in recount['source_artifacts'].values()
        if not (repo_root / path).exists()
    ]
    ft_ir_lookup = {row['name']: row for row in artifacts['ft_ir_compositions']['families']}
    frontier_lookup = {row['name']: row for row in artifacts['family_frontier']['families']}
    family_failures = []
    for family in recount['families']:
        ft_ir_row = ft_ir_lookup[family['name']]
        frontier_row = frontier_lookup[family['name']]
        if not (
            family['primitive_totals'] == ft_ir_row['reconstruction']['primitive_totals']
            and family['full_oracle_non_clifford'] == ft_ir_row['reconstruction']['full_oracle_non_clifford'] == frontier_row['full_oracle_non_clifford']
            and family['total_logical_qubits'] == ft_ir_row['reconstruction']['total_logical_qubits'] == frontier_row['total_logical_qubits']
            and family['phase_shell_hadamards'] == ft_ir_row['reconstruction']['phase_shell_hadamards'] == frontier_row['phase_shell_hadamards']
            and family['total_measurements'] == frontier_row['total_measurements']
            and family['phase_shell_measurements'] == ft_ir_row['reconstruction']['phase_shell_measurements']
            and family['phase_shell_rotations'] == ft_ir_row['reconstruction']['phase_shell_rotations']
            and family['phase_shell_rotation_depth'] == ft_ir_row['reconstruction']['phase_shell_rotation_depth'] == frontier_row['phase_shell_rotation_depth']
        ):
            family_failures.append(family['name'])
    checks = [
        _check('whole_oracle_recount_matches_generator', recount == expected, expected, recount),
        _check(
            'whole_oracle_recount_schema_matches_current_version',
            recount['schema'] == 'compiler-project-whole-oracle-recount-v2',
            'compiler-project-whole-oracle-recount-v2',
            recount['schema'],
        ),
        _check(
            'whole_oracle_recount_source_paths_match_expected',
            recount['source_artifacts'] == {
                'ft_ir_compositions': 'compiler_verification_project/artifacts/ft_ir_compositions.json',
                'family_frontier': 'compiler_verification_project/artifacts/family_frontier.json',
            },
            {
                'ft_ir_compositions': 'compiler_verification_project/artifacts/ft_ir_compositions.json',
                'family_frontier': 'compiler_verification_project/artifacts/family_frontier.json',
            },
            recount['source_artifacts'],
        ),
        _check('whole_oracle_recount_source_paths_exist_on_disk', len(source_path_failures) == 0, [], source_path_failures),
        _check('whole_oracle_recount_rows_match_ft_ir_and_frontier', len(family_failures) == 0, [], family_failures),
        _check(
            'whole_oracle_recount_best_families_match_frontier',
            recount['best_gate_family']['name'] == artifacts['family_frontier']['best_gate_family']['name']
            and recount['best_qubit_family']['name'] == artifacts['family_frontier']['best_qubit_family']['name'],
            {
                'best_gate_family': artifacts['family_frontier']['best_gate_family']['name'],
                'best_qubit_family': artifacts['family_frontier']['best_qubit_family']['name'],
            },
            {
                'best_gate_family': recount['best_gate_family']['name'],
                'best_qubit_family': recount['best_qubit_family']['name'],
            },
        ),
    ]
    return _summarize_checks(checks)


def build_subcircuit_equivalence_checks(artifacts: Mapping[str, Any], repo_root: Path) -> Dict[str, Any]:
    equivalence = artifacts['subcircuit_equivalence']
    expected = build_subcircuit_equivalence_artifact(
        arithmetic_lowerings=artifacts['arithmetic_lowerings'],
        lookup_lowerings=artifacts['lookup_lowerings'],
        generated_block_inventories=artifacts['generated_block_inventories'],
        frontier=artifacts['family_frontier'],
        full_attack_inventory=artifacts['full_attack_inventory'],
    )
    arithmetic = equivalence['arithmetic_opcode_equivalence']
    cleanup = equivalence['cleanup_window_equivalence']
    lookup = equivalence['lookup_family_equivalence']
    composition = equivalence['whole_oracle_composition_equivalence']
    reduced_width_failures = []
    for width_row in arithmetic['reduced_width_family_shape_witnesses']['widths']:
        for opcode in ('field_add', 'field_sub', 'field_mul', 'mul_const', 'select_field_if_flag'):
            if width_row[opcode]['pass'] != width_row[opcode]['total']:
                reduced_width_failures.append({'field_bits': width_row['field_bits'], 'opcode': opcode})
    composition_failures = []
    for family in composition['families']:
        if not (
            family['generated_full_oracle_non_clifford'] == family['frontier_full_oracle_non_clifford'] == family['inventory_full_oracle_non_clifford']
            and family['generated_total_logical_qubits'] == family['frontier_total_logical_qubits'] == family['inventory_total_logical_qubits']
        ):
            composition_failures.append(family['name'])
    lookup_failures = [
        row['name']
        for row in lookup['families']
        if not (
            row['direct_lookup_non_clifford'] == row['stage_reconstructed_non_clifford']
            and row['workspace_qubits'] == row['stage_reconstructed_workspace_qubits']
            and row['canonical_full_exhaustive_pass'] == row['canonical_full_exhaustive_total']
            and row['multibase_edge_pass'] == row['multibase_edge_total']
        )
    ]
    arithmetic_per_pc_failures = [row['pc'] for row in arithmetic['per_pc'] if row['pass'] != row['total']]
    arithmetic_per_opcode_failures = [row['opcode'] for row in arithmetic['per_opcode'] if row['pass'] != row['total']]
    expected_source_artifacts = {
        'leaf': 'compiler_verification_project/artifacts/interface_borrowed_leaf.json',
        'lookup_fed_leaf_equivalence': 'compiler_verification_project/artifacts/lookup_fed_leaf_equivalence.json',
        'interface_borrowed_leaf_equivalence': 'compiler_verification_project/artifacts/interface_borrowed_leaf_equivalence.json',
        'cleanup_summary': 'artifacts/verification/extended/coherent_cleanup_summary.json',
        'arithmetic_lowerings': 'compiler_verification_project/artifacts/arithmetic_lowerings.json',
        'lookup_lowerings': 'compiler_verification_project/artifacts/lookup_lowerings.json',
        'generated_block_inventories': 'compiler_verification_project/artifacts/generated_block_inventories.json',
        'family_frontier': 'compiler_verification_project/artifacts/family_frontier.json',
        'full_attack_inventory': 'compiler_verification_project/artifacts/full_attack_inventory.json',
    }
    checks = [
        _check('subcircuit_equivalence_artifact_matches_generator', equivalence == expected, expected, equivalence),
        _check(
            'subcircuit_equivalence_source_paths_match_expected',
            equivalence['source_artifacts'] == expected_source_artifacts,
            expected_source_artifacts,
            equivalence['source_artifacts'],
        ),
        _check(
            'subcircuit_equivalence_source_paths_exist_on_disk',
            all((repo_root / path).exists() for path in equivalence['source_artifacts'].values()),
            sorted(equivalence['source_artifacts'].values()),
            sorted(path for path in equivalence['source_artifacts'].values() if (repo_root / path).exists()),
        ),
        _check('arithmetic_opcode_trace_equivalence_passes_all_traced_pcs', len(arithmetic_per_pc_failures) == 0, [], arithmetic_per_pc_failures),
        _check('arithmetic_opcode_trace_equivalence_passes_all_opcodes', len(arithmetic_per_opcode_failures) == 0, [], arithmetic_per_opcode_failures),
        _check(
            'cleanup_trace_zero_after_clear_passes_all_cases',
            cleanup['trace_cleanup_zero_pass'] == cleanup['trace_cleanup_zero_total'],
            cleanup['trace_cleanup_zero_total'],
            cleanup['trace_cleanup_zero_pass'],
        ),
        _check(
            'cleanup_summary_hash_matches_checked_artifact',
            cleanup['cleanup_summary_sha256'] == sha256_path(repo_root / cleanup['cleanup_summary_path']),
            sha256_path(repo_root / cleanup['cleanup_summary_path']),
            cleanup['cleanup_summary_sha256'],
        ),
        _check(
            'cleanup_imported_audit_passes_all_cases',
            cleanup['imported_cleanup_audit']['pass'] == cleanup['imported_cleanup_audit']['total'],
            cleanup['imported_cleanup_audit']['total'],
            cleanup['imported_cleanup_audit']['pass'],
        ),
        _check('lookup_family_equivalence_passes_all_semantic_witnesses', len(lookup_failures) == 0, [], lookup_failures),
        _check('reduced_width_family_shape_witnesses_pass', len(reduced_width_failures) == 0, [], reduced_width_failures),
        _check('whole_oracle_composition_equivalence_rows_match_all_layers', len(composition_failures) == 0, [], composition_failures),
        _check(
            'whole_oracle_best_families_match_generated_inventory',
            composition['best_gate_family'] == artifacts['generated_block_inventories']['best_gate_family']
            and composition['best_qubit_family'] == artifacts['generated_block_inventories']['best_qubit_family'],
            {
                'best_gate_family': artifacts['generated_block_inventories']['best_gate_family'],
                'best_qubit_family': artifacts['generated_block_inventories']['best_qubit_family'],
            },
            {
                'best_gate_family': composition['best_gate_family'],
                'best_qubit_family': composition['best_qubit_family'],
            },
        ),
    ]
    return _summarize_checks(checks)


def build_primitive_multiplier_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    primitive = artifacts['primitive_multiplier_library']
    schedule = artifacts['full_raw32_oracle']
    kernel = artifacts['module_library']
    field_mul_kernel = next(row for row in artifacts['arithmetic_lowerings']['kernels'] if row['opcode'] == 'field_mul')
    field_mul_pcs = [instruction['pc'] for instruction in _leaf()['instructions'] if instruction['op'] == 'field_mul']
    expected_per_leaf = [
        {
            'leaf_multiplier_index': ordinal,
            'leaf_pc': pc,
            'family': kernel['name'],
            'field_bits': FIELD_BITS,
            'exact_non_clifford': field_mul_kernel['exact_non_clifford_per_kernel'],
            'gate_set': kernel['gate_set'],
            'arithmetic_lowering_artifact': 'compiler_verification_project/artifacts/arithmetic_lowerings.json',
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
            primitive['whole_oracle_multiplier_non_clifford_total'] == primitive['whole_oracle_multiplier_instance_count'] * field_mul_kernel['exact_non_clifford_per_kernel'],
            primitive['whole_oracle_multiplier_instance_count'] * field_mul_kernel['exact_non_clifford_per_kernel'],
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
    expected_slot_families = [
        {
            'name': row.name,
            'summary': row.summary,
            'source_artifact': row.source_artifact,
            'leaf_source_artifact': row.leaf_source_artifact,
            'slot_allocation': row.slot_allocation,
            'notes': row.notes,
        }
        for row in slot_allocation_families()
    ]
    families = frontier['families']
    recount_lookup = {row['name']: row for row in artifacts['whole_oracle_recount']['families']}
    expected_families = []
    for slot_family in expected_slot_families:
        for lookup in frontier['lookup_families']:
            for phase_shell in frontier['phase_shell_families']:
                family_name = f"{lookup['name']}__{slot_family['name']}__{phase_shell['name']}"
                inventory = next(
                    row['reconstruction']
                    for row in artifacts['generated_block_inventories']['families']
                    if row['name'] == family_name
                )
                recount = recount_lookup[family_name]
                expected_families.append({
                    'name': family_name,
                    'summary': f"{lookup['summary']} / {phase_shell['summary']} / {slot_family['summary']}",
                    'gate_set': f"{lookup['gate_set']}; {phase_shell['gate_set']}",
                    'phase_shell': phase_shell['name'],
                    'slot_allocation_family': slot_family['name'],
                    'arithmetic_kernel_family': kernel['name'],
                    'lookup_family': lookup['name'],
                    'arithmetic_leaf_non_clifford': inventory['arithmetic_leaf_non_clifford'],
                    'direct_seed_non_clifford': inventory['direct_seed_non_clifford'],
                    'per_leaf_lookup_non_clifford': inventory['per_leaf_lookup_non_clifford'],
                    'full_oracle_non_clifford': recount['full_oracle_non_clifford'],
                    'arithmetic_slot_count': inventory['arithmetic_slot_count'],
                    'control_slot_count': inventory['control_slot_count'],
                    'lookup_workspace_qubits': inventory['lookup_workspace_qubits'],
                    'live_phase_bits': inventory['live_phase_bits'],
                    'total_logical_qubits': recount['total_logical_qubits'],
                    'phase_shell_hadamards': recount['phase_shell_hadamards'],
                    'phase_shell_measurements': recount['phase_shell_measurements'],
                    'phase_shell_rotations': recount['phase_shell_rotations'],
                    'phase_shell_rotation_depth': recount['phase_shell_rotation_depth'],
                    'total_measurements': recount['total_measurements'],
                    'improvement_vs_google_low_qubit': recount['improvement_vs_google_low_qubit'],
                    'improvement_vs_google_low_gate': recount['improvement_vs_google_low_gate'],
                    'qubit_ratio_vs_google_low_qubit': recount['qubit_ratio_vs_google_low_qubit'],
                    'qubit_ratio_vs_google_low_gate': recount['qubit_ratio_vs_google_low_gate'],
                    'notes': [*lookup['notes'], *phase_shell['notes']],
                })
    expected_best_gate = min(expected_families, key=lambda row: (row['full_oracle_non_clifford'], row['total_logical_qubits']))
    expected_best_qubit = min(expected_families, key=lambda row: (row['total_logical_qubits'], row['full_oracle_non_clifford']))
    expected_best_sub30m_qubit = min(
        (row for row in expected_families if row['full_oracle_non_clifford'] < 30_000_000),
        key=lambda row: (row['total_logical_qubits'], row['full_oracle_non_clifford']),
    )
    checks = [
        _check('public_google_baseline_matches_constant', frontier['public_google_baseline'] == PUBLIC_GOOGLE_BASELINE, PUBLIC_GOOGLE_BASELINE, frontier['public_google_baseline']),
        _check('frontier_schedule_matches_standalone_schedule', frontier['schedule'] == schedule, schedule, frontier['schedule']),
        _check('frontier_slot_allocation_matches_standalone_slot_allocation', frontier['slot_allocation'] == slot_alloc, slot_alloc, frontier['slot_allocation']),
        _check('frontier_slot_allocation_families_match_expected', frontier['slot_allocation_families'] == expected_slot_families, expected_slot_families, frontier['slot_allocation_families']),
        _check('frontier_arithmetic_kernel_matches_module_library', frontier['arithmetic_kernel_family'] == kernel, kernel, frontier['arithmetic_kernel_family']),
        _check(
            'frontier_arithmetic_lowering_artifact_path_matches_expected',
            frontier['arithmetic_lowering_artifact'] == 'compiler_verification_project/artifacts/arithmetic_lowerings.json',
            'compiler_verification_project/artifacts/arithmetic_lowerings.json',
            frontier['arithmetic_lowering_artifact'],
        ),
        _check(
            'frontier_lookup_lowering_artifact_path_matches_expected',
            frontier['lookup_lowering_artifact'] == 'compiler_verification_project/artifacts/lookup_lowerings.json',
            'compiler_verification_project/artifacts/lookup_lowerings.json',
            frontier['lookup_lowering_artifact'],
        ),
        _check(
            'frontier_phase_shell_lowering_artifact_path_matches_expected',
            frontier['phase_shell_lowering_artifact'] == 'compiler_verification_project/artifacts/phase_shell_lowerings.json',
            'compiler_verification_project/artifacts/phase_shell_lowerings.json',
            frontier['phase_shell_lowering_artifact'],
        ),
        _check(
            'frontier_generated_block_inventory_path_matches_expected',
            frontier['generated_block_inventory_artifact'] == 'compiler_verification_project/artifacts/generated_block_inventories.json',
            'compiler_verification_project/artifacts/generated_block_inventories.json',
            frontier['generated_block_inventory_artifact'],
        ),
        _check(
            'frontier_whole_oracle_recount_path_matches_expected',
            frontier['whole_oracle_recount_artifact'] == 'compiler_verification_project/artifacts/whole_oracle_recount.json',
            'compiler_verification_project/artifacts/whole_oracle_recount.json',
            frontier['whole_oracle_recount_artifact'],
        ),
        _check('lookup_family_library_matches_named_lookup_families', frontier['lookup_families'] == expected_lookup_families, expected_lookup_families, frontier['lookup_families']),
        _check('phase_shell_library_matches_named_phase_shells', frontier['phase_shell_families'] == expected_phase_shells, expected_phase_shells, frontier['phase_shell_families']),
        _check('frontier_family_rows_reconstruct_from_components', families == expected_families, expected_families, families),
        _check('best_gate_family_is_minimum_over_family_rows', frontier['best_gate_family'] == expected_best_gate, expected_best_gate, frontier['best_gate_family']),
        _check('best_qubit_family_is_minimum_over_family_rows', frontier['best_qubit_family'] == expected_best_qubit, expected_best_qubit, frontier['best_qubit_family']),
        _check(
            'best_sub30m_qubit_family_is_minimum_over_sub30m_rows',
            frontier['best_sub30m_qubit_family'] == expected_best_sub30m_qubit,
            expected_best_sub30m_qubit,
            frontier['best_sub30m_qubit_family'],
        ),
    ]
    return _summarize_checks(checks)


def build_build_summary_checks(artifacts: Mapping[str, Any], repo_root: Path) -> Dict[str, Any]:
    build_summary = artifacts['build_summary']
    expected_paths = {
        'canonical_public_point': 'compiler_verification_project/artifacts/canonical_public_point.json',
        'full_raw32_oracle': 'compiler_verification_project/artifacts/full_raw32_oracle.json',
        'exact_leaf_slot_allocation': 'compiler_verification_project/artifacts/exact_leaf_slot_allocation.json',
        'lookup_fed_leaf': 'compiler_verification_project/artifacts/lookup_fed_leaf.json',
        'lookup_fed_leaf_equivalence': 'compiler_verification_project/artifacts/lookup_fed_leaf_equivalence.json',
        'lookup_fed_leaf_slot_allocation': 'compiler_verification_project/artifacts/lookup_fed_leaf_slot_allocation.json',
        'interface_borrowed_leaf': 'compiler_verification_project/artifacts/interface_borrowed_leaf.json',
        'interface_borrowed_leaf_equivalence': 'compiler_verification_project/artifacts/interface_borrowed_leaf_equivalence.json',
        'interface_borrowed_leaf_slot_allocation': 'compiler_verification_project/artifacts/interface_borrowed_leaf_slot_allocation.json',
        'arithmetic_lowerings': 'compiler_verification_project/artifacts/arithmetic_lowerings.json',
        'module_library': 'compiler_verification_project/artifacts/module_library.json',
        'primitive_multiplier_library': 'compiler_verification_project/artifacts/primitive_multiplier_library.json',
        'phase_shell_lowerings': 'compiler_verification_project/artifacts/phase_shell_lowerings.json',
        'phase_shell_families': 'compiler_verification_project/artifacts/phase_shell_families.json',
        'table_manifests': 'compiler_verification_project/artifacts/table_manifests.json',
        'lookup_lowerings': 'compiler_verification_project/artifacts/lookup_lowerings.json',
        'generated_block_inventories': 'compiler_verification_project/artifacts/generated_block_inventories.json',
        'family_frontier': 'compiler_verification_project/artifacts/family_frontier.json',
        'qubit_breakthrough_analysis': 'compiler_verification_project/artifacts/qubit_breakthrough_analysis.json',
        'full_attack_inventory': 'compiler_verification_project/artifacts/full_attack_inventory.json',
        'ft_ir_compositions': 'compiler_verification_project/artifacts/ft_ir_compositions.json',
        'whole_oracle_recount': 'compiler_verification_project/artifacts/whole_oracle_recount.json',
        'subcircuit_equivalence': 'compiler_verification_project/artifacts/subcircuit_equivalence.json',
        'azure_resource_estimator_logical_counts': 'compiler_verification_project/artifacts/azure_resource_estimator_logical_counts.json',
        'azure_resource_estimator_targets': 'compiler_verification_project/artifacts/azure_resource_estimator_targets.json',
        'azure_resource_estimator_results': 'compiler_verification_project/artifacts/azure_resource_estimator_results.json',
    }
    checks = [
        _check('build_summary_schema_matches_current_version', build_summary['schema'] == 'compiler-project-build-summary-v14', 'compiler-project-build-summary-v14', build_summary['schema']),
        _check('build_summary_artifact_paths_match_expected_set', build_summary['artifacts'] == expected_paths, expected_paths, build_summary['artifacts']),
        _check(
            'build_summary_paths_exist_on_disk',
            all((repo_root / path).exists() for path in build_summary['artifacts'].values()),
            sorted(build_summary['artifacts'].values()),
            sorted(path for path in build_summary['artifacts'].values() if (repo_root / path).exists()),
        ),
        _check('build_summary_best_gate_matches_frontier', build_summary['headline']['best_gate_family'] == artifacts['family_frontier']['best_gate_family'], artifacts['family_frontier']['best_gate_family'], build_summary['headline']['best_gate_family']),
        _check('build_summary_best_qubit_matches_frontier', build_summary['headline']['best_qubit_family'] == artifacts['family_frontier']['best_qubit_family'], artifacts['family_frontier']['best_qubit_family'], build_summary['headline']['best_qubit_family']),
        _check(
            'build_summary_best_sub30m_qubit_matches_frontier',
            build_summary['headline']['best_sub30m_qubit_family'] == artifacts['family_frontier']['best_sub30m_qubit_family'],
            artifacts['family_frontier']['best_sub30m_qubit_family'],
            build_summary['headline']['best_sub30m_qubit_family'],
        ),
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
    observed = artifacts['azure_resource_estimator_logical_counts']
    observed_family_names = [row['family'] for row in observed['families']]
    expected_family_names = [row['family'] for row in expected['families']]
    if observed_family_names != expected_family_names:
        observed_name_set = set(observed_family_names)
        expected = {
            **expected,
            'families': [row for row in expected['families'] if row['family'] in observed_name_set],
            'notes': [
                *expected['notes'],
                'When qsharp/qdk is unavailable, this artifact is filtered to the subset of families that have checked recorded estimator outputs in the repository.',
            ],
        }
    checks = [
        _check(
            'azure_seed_family_names_are_frontier_subset',
            set(observed_family_names).issubset(set(expected_family_names)),
            sorted(expected_family_names),
            sorted(observed_family_names),
        ),
        _check('azure_seed_matches_frontier_projection', observed == expected, expected, observed),
    ]
    return _summarize_checks(checks)


def build_physical_estimator_target_checks(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    expected = build_azure_estimator_target_payload(artifacts['azure_resource_estimator_logical_counts'])
    checks = [
        _check(
            'physical_estimator_targets_match_expected_profiles',
            artifacts['azure_resource_estimator_targets'] == expected,
            expected,
            artifacts['azure_resource_estimator_targets'],
        ),
    ]
    return _summarize_checks(checks)


def build_physical_estimator_result_checks(artifacts: Mapping[str, Any], repo_root: Path) -> Dict[str, Any]:
    expected = build_or_load_azure_estimator_results_payload(
        logical_counts_payload=artifacts['azure_resource_estimator_logical_counts'],
        target_payload=artifacts['azure_resource_estimator_targets'],
        artifact_path=repo_root / 'compiler_verification_project' / 'artifacts' / 'azure_resource_estimator_results.json',
    )
    results = artifacts['azure_resource_estimator_results']
    target_names = [target['name'] for target in artifacts['azure_resource_estimator_targets']['targets']]
    family_rows = results['families']
    logical_count_family_names = [row['family'] for row in artifacts['azure_resource_estimator_logical_counts']['families']]
    checks = [
        _check(
            'physical_estimator_results_match_recorded_projection',
            results == expected,
            expected,
            results,
        ),
        _check(
            'physical_estimator_result_family_count_matches_logical_counts',
            (
                set(row['family'] for row in family_rows).issubset(set(logical_count_family_names))
                if logical_count_family_names
                else len(family_rows) == len(expected['families'])
            ),
            sorted(logical_count_family_names) if logical_count_family_names else len(expected['families']),
            sorted(row['family'] for row in family_rows) if logical_count_family_names else len(family_rows),
        ),
        _check(
            'physical_estimator_result_target_summary_count_matches_target_profiles',
            len(results['target_summaries']) == len(target_names),
            len(target_names),
            len(results['target_summaries']),
        ),
        _check(
            'physical_estimator_source_bindings_match_input_hashes',
            results['source_bindings'] == expected['source_bindings'],
            expected['source_bindings'],
            results['source_bindings'],
        ),
    ]
    for family in family_rows:
        estimate_targets = [estimate['target'] for estimate in family['estimates']]
        checks.append(
            _check(
                f"physical_estimator_{family['family']}_covers_every_target_exactly_once",
                estimate_targets == target_names,
                target_names,
                estimate_targets,
            )
        )
        best_space = min(
            family['estimates'],
            key=lambda row: (
                row['physical_counts']['physicalQubits'],
                row['physical_counts']['runtime'],
                row['physical_counts']['rqops'],
            ),
        )
        best_runtime = min(
            family['estimates'],
            key=lambda row: (
                row['physical_counts']['runtime'],
                row['physical_counts']['physicalQubits'],
                -row['physical_counts']['rqops'],
            ),
        )
        checks.extend([
            _check(
                f"physical_estimator_{family['family']}_summary_best_space_matches_estimates",
                family['summary']['lowest_physical_qubits_target'] == {
                    'target': best_space['target'],
                    'physical_qubits': best_space['physical_counts']['physicalQubits'],
                    'runtime': best_space['physical_counts']['runtime'],
                },
                {
                    'target': best_space['target'],
                    'physical_qubits': best_space['physical_counts']['physicalQubits'],
                    'runtime': best_space['physical_counts']['runtime'],
                },
                family['summary']['lowest_physical_qubits_target'],
            ),
            _check(
                f"physical_estimator_{family['family']}_summary_best_runtime_matches_estimates",
                family['summary']['fastest_runtime_target'] == {
                    'target': best_runtime['target'],
                    'runtime': best_runtime['physical_counts']['runtime'],
                    'physical_qubits': best_runtime['physical_counts']['physicalQubits'],
                },
                {
                    'target': best_runtime['target'],
                    'runtime': best_runtime['physical_counts']['runtime'],
                    'physical_qubits': best_runtime['physical_counts']['physicalQubits'],
                },
                family['summary']['fastest_runtime_target'],
            ),
        ])
        for estimate in family['estimates']:
            target = next(row for row in artifacts['azure_resource_estimator_targets']['targets'] if row['name'] == estimate['target'])
            checks.extend([
                _check(
                    f"physical_estimator_{family['family']}_{estimate['target']}_requested_params_match_target_profile",
                    estimate['requested_params'] == target['requested_params'],
                    target['requested_params'],
                    estimate['requested_params'],
                ),
                _check(
                    f"physical_estimator_{family['family']}_{estimate['target']}_reported_logical_counts_match_input",
                    estimate['reported_logical_counts'] == family['logical_counts'],
                    family['logical_counts'],
                    estimate['reported_logical_counts'],
                ),
                _check(
                    f"physical_estimator_{family['family']}_{estimate['target']}_physical_qubits_positive",
                    estimate['physical_counts']['physicalQubits'] > 0,
                    '> 0',
                    estimate['physical_counts']['physicalQubits'],
                ),
                _check(
                    f"physical_estimator_{family['family']}_{estimate['target']}_runtime_positive",
                    estimate['physical_counts']['runtime'] > 0,
                    '> 0',
                    estimate['physical_counts']['runtime'],
                ),
                _check(
                    f"physical_estimator_{family['family']}_{estimate['target']}_job_params_qubit_model_matches_target",
                    estimate['job_params']['qubitParams']['name'] == target['requested_params']['qubitParams']['name'],
                    target['requested_params']['qubitParams']['name'],
                    estimate['job_params']['qubitParams']['name'],
                ),
                _check(
                    f"physical_estimator_{family['family']}_{estimate['target']}_job_params_qec_matches_target",
                    estimate['job_params']['qecScheme']['name'] == target['requested_params']['qecScheme']['name'],
                    target['requested_params']['qecScheme']['name'],
                    estimate['job_params']['qecScheme']['name'],
                ),
            ])
    for target_name in target_names:
        target_estimates = [
            next(estimate for estimate in family['estimates'] if estimate['target'] == target_name)
            for family in family_rows
        ]
        best_space = min(
            target_estimates,
            key=lambda row: (
                row['physical_counts']['physicalQubits'],
                row['physical_counts']['runtime'],
                row['physical_counts']['rqops'],
            ),
        )
        best_runtime = min(
            target_estimates,
            key=lambda row: (
                row['physical_counts']['runtime'],
                row['physical_counts']['physicalQubits'],
                -row['physical_counts']['rqops'],
            ),
        )
        summary_row = next(row for row in results['target_summaries'] if row['target'] == target_name)
        checks.extend([
            _check(
                f'physical_estimator_target_{target_name}_summary_best_space_matches_families',
                summary_row['lowest_physical_qubits_family'] == {
                    'family': best_space['family'],
                    'physical_qubits': best_space['physical_counts']['physicalQubits'],
                    'runtime': best_space['physical_counts']['runtime'],
                },
                {
                    'family': best_space['family'],
                    'physical_qubits': best_space['physical_counts']['physicalQubits'],
                    'runtime': best_space['physical_counts']['runtime'],
                },
                summary_row['lowest_physical_qubits_family'],
            ),
            _check(
                f'physical_estimator_target_{target_name}_summary_best_runtime_matches_families',
                summary_row['fastest_runtime_family'] == {
                    'family': best_runtime['family'],
                    'runtime': best_runtime['physical_counts']['runtime'],
                    'physical_qubits': best_runtime['physical_counts']['physicalQubits'],
                },
                {
                    'family': best_runtime['family'],
                    'runtime': best_runtime['physical_counts']['runtime'],
                    'physical_qubits': best_runtime['physical_counts']['physicalQubits'],
                },
                summary_row['fastest_runtime_family'],
            ),
        ])
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
        'cleanup_pair_checks': build_cleanup_pair_checks(artifacts),
        'lookup_lowering_checks': build_lookup_lowering_checks(artifacts),
        'phase_shell_lowering_checks': build_phase_shell_lowering_checks(artifacts),
        'generated_block_inventory_checks': build_generated_block_inventory_checks(artifacts),
        'slot_allocation_checks': build_slot_allocation_checks(artifacts),
        'lookup_fed_slot_allocation_checks': build_lookup_fed_slot_allocation_checks(artifacts),
        'qubit_breakthrough_checks': build_qubit_breakthrough_checks(artifacts),
        'full_attack_inventory_checks': build_full_attack_inventory_checks(artifacts),
        'ft_ir_checks': build_ft_ir_checks(artifacts, repo_root),
        'whole_oracle_recount_checks': build_whole_oracle_recount_checks(artifacts, repo_root),
        'subcircuit_equivalence_checks': build_subcircuit_equivalence_checks(artifacts, repo_root),
        'primitive_multiplier_checks': build_primitive_multiplier_checks(artifacts),
        'frontier_checks': build_frontier_checks(artifacts),
        'build_summary_checks': build_build_summary_checks(artifacts, repo_root),
        'cain_transfer_checks': build_cain_transfer_checks(artifacts),
        'azure_seed_checks': build_azure_seed_checks(artifacts),
        'physical_estimator_target_checks': build_physical_estimator_target_checks(artifacts),
        'physical_estimator_result_checks': build_physical_estimator_result_checks(artifacts, repo_root),
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
        'schema': 'compiler-project-verification-summary-v11',
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
