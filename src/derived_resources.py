#!/usr/bin/env python3
"""Derived structural and backend-resource accounting helpers.

This module strengthens the repository's modeled layer in three ways:

1. It builds an exact whole-scaffold **expanded ISA artifact** by replaying the
   checked-in retained-window scaffold over the checked-in point-add leaf.
2. It computes structural counts, opcode histograms, and ISA-slot liveness
   directly from repository artifacts instead of relying on whole-circuit
   headline constants.
3. It applies one or more **versioned backend models** to those derived
   structural counts, making every modeled total traceable to source artifacts.

The exact boundary still ends at the kickmix ISA.  The backend models below do
not claim to be primitive-gate proofs.  They do, however, avoid inheriting
whole-leaf or whole-circuit calibration constants. Every opcode family in the
current bundle is priced either from exact structural counts or from explicit
closed-form backend assumptions tied to the checked-in artifact family.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Sequence

from common import artifact_circuits_path, artifact_lookup_path, artifact_projection_path, dump_json, load_json, sha256_path

FIELD_ARITH_OPS = {'field_mul', 'field_add', 'field_sub', 'mul_const', 'select_field_if_flag'}
LOOKUP_OPS = {'lookup_affine_x', 'lookup_affine_y', 'lookup_meta'}
CONTROL_OPS = {'bool_from_flag', 'clear_bool_from_flag'}
ZERO_COST_OPS = {'load_input'}


def _tracked_slots(register_map: Mapping[str, Any]) -> List[str]:
    tracked = list(register_map.get('arithmetic_slots', []))
    tracked.extend(register_map.get('auxiliary_control_slots', []))
    return tracked


def _iter_register_references(ins: Mapping[str, Any], tracked: set[str]) -> Iterable[str]:
    dst = ins.get('dst')
    if isinstance(dst, str) and dst in tracked:
        yield dst

    src = ins.get('src')
    if isinstance(src, str):
        if src in tracked:
            yield src
    elif isinstance(src, Sequence) and not isinstance(src, (str, bytes, bytearray)):
        for item in src:
            if isinstance(item, str) and item in tracked:
                yield item
    elif isinstance(src, Mapping):
        for key in ('flags', 'key', 'table'):
            value = src.get(key)
            if isinstance(value, str) and value in tracked:
                yield value

    flag = ins.get('flag')
    if isinstance(flag, str) and flag in tracked:
        yield flag


def minimal_addition_chain(target: int) -> List[int]:
    """Return a minimal monotone addition chain ending at ``target``.

    The constants used in this repository are tiny (currently just 21), so a BFS
    is simple, exact, and fully deterministic.
    """
    if target < 1:
        raise ValueError('addition chains require a positive target')
    if target == 1:
        return [1]

    frontier: List[List[int]] = [[1]]
    while frontier:
        next_frontier: List[List[int]] = []
        for chain in frontier:
            last = chain[-1]
            for i in range(len(chain) - 1, -1, -1):
                nxt = last + chain[i]
                if nxt <= last or nxt > target:
                    continue
                extended = chain + [nxt]
                if nxt == target:
                    return extended
                next_frontier.append(extended)
        frontier = next_frontier
    raise RuntimeError(f'failed to build addition chain for {target}')


def load_core_artifacts(repo_root: Path) -> Dict[str, Any]:
    package_root = repo_root / 'artifacts'
    leaf_path = artifact_circuits_path(package_root, 'optimized_pointadd_secp256k1.json')
    scaffold_path = artifact_circuits_path(package_root, 'ecdlp_scaffold_optimized.json')
    folded_scaffold_path = artifact_circuits_path(package_root, 'ecdlp_scaffold_lookup_folded.json')
    register_map_path = artifact_circuits_path(package_root, 'register_map.json')
    lookup_contract_path = artifact_lookup_path(package_root, 'lookup_signed_fold_contract.json')
    return {
        'leaf_path': leaf_path,
        'scaffold_path': scaffold_path,
        'folded_scaffold_path': folded_scaffold_path,
        'register_map_path': register_map_path,
        'lookup_contract_path': lookup_contract_path,
        'leaf': load_json(leaf_path),
        'scaffold': load_json(scaffold_path),
        'folded_scaffold': load_json(folded_scaffold_path),
        'register_map': load_json(register_map_path),
        'lookup_contract': load_json(lookup_contract_path),
    }


def compute_leaf_liveness(leaf: Mapping[str, Any], register_map: Mapping[str, Any]) -> Dict[str, Any]:
    tracked = set(_tracked_slots(register_map))
    intervals: Dict[str, Dict[str, int]] = {}
    instructions = leaf['instructions']

    for ins in instructions:
        pc = int(ins['pc'])
        for name in _iter_register_references(ins, tracked):
            entry = intervals.setdefault(name, {'first_pc': pc, 'last_pc': pc})
            entry['first_pc'] = min(entry['first_pc'], pc)
            entry['last_pc'] = max(entry['last_pc'], pc)

    per_pc: List[Dict[str, Any]] = []
    for pc in range(len(instructions)):
        active = sorted(name for name, interval in intervals.items() if interval['first_pc'] <= pc <= interval['last_pc'])
        arithmetic = [name for name in active if name in register_map.get('arithmetic_slots', [])]
        controls = [name for name in active if name in register_map.get('auxiliary_control_slots', [])]
        per_pc.append({
            'pc': pc,
            'active_slots': active,
            'active_arithmetic_slots': arithmetic,
            'active_control_slots': controls,
            'active_slot_count': len(active),
            'active_arithmetic_slot_count': len(arithmetic),
            'active_control_slot_count': len(controls),
        })

    peak_total = max(per_pc, key=lambda row: row['active_slot_count'])
    peak_arith = max(per_pc, key=lambda row: row['active_arithmetic_slot_count'])
    peak_control = max(per_pc, key=lambda row: row['active_control_slot_count'])
    return {
        'tracked_slots': sorted(tracked),
        'intervals': intervals,
        'per_pc': per_pc,
        'peak_total_slots': peak_total,
        'peak_arithmetic_slots': peak_arith,
        'peak_control_slots': peak_control,
    }


def expand_scaffold_isa(repo_root: Path) -> Dict[str, Any]:
    data = load_core_artifacts(repo_root)
    leaf = data['leaf']
    folded_scaffold = data['folded_scaffold']

    leaf_sha = sha256_path(data['leaf_path'])
    scaffold_sha = sha256_path(data['scaffold_path'])
    folded_scaffold_sha = sha256_path(data['folded_scaffold_path'])
    lookup_contract_sha = sha256_path(data['lookup_contract_path'])

    expanded_instructions: List[Dict[str, Any]] = []
    marker_pc = 0
    expanded_instructions.append({
        'pc': marker_pc,
        'kind': 'direct_seed_marker',
        **deepcopy(folded_scaffold['base_scaffold_sha256'] and data['scaffold']['direct_lookup_seed']),
        'comment': 'Direct seed step retained as exact scaffold metadata; the repeated leaf body begins after this marker.',
    })
    marker_pc += 1

    flat_leaf_count = 0
    phase_hist = Counter()
    for call in folded_scaffold['retained_window_additions']:
        phase_hist[call['phase_register']] += 1
        for ins in leaf['instructions']:
            out = deepcopy(ins)
            out['pc'] = marker_pc
            out['kind'] = 'leaf_op'
            out['call_index'] = call['call_index']
            out['phase_register'] = call['phase_register']
            out['raw_window_index'] = call['raw_window_index']
            out['window_index_within_register'] = call['window_index_within_register']
            out['bit_start'] = call['bit_start']
            out['bit_width'] = call['bit_width']
            out['leaf_pc'] = ins['pc']
            expanded_instructions.append(out)
            marker_pc += 1
            flat_leaf_count += 1

    for tail in data['scaffold']['classical_tail_elisions']:
        expanded_instructions.append({
            'pc': marker_pc,
            'kind': 'tail_elision_marker',
            **deepcopy(tail),
            'comment': 'Classical tail reconstruction metadata; no leaf body is attached here.',
        })
        marker_pc += 1

    opcode_hist = Counter(ins['op'] for ins in expanded_instructions if ins.get('kind') == 'leaf_op')
    result = {
        'schema': 'kickmix-expanded-isa-v1',
        'curve': 'secp256k1',
        'leaf_source': {'path': 'artifacts/circuits/optimized_pointadd_secp256k1.json', 'sha256': leaf_sha},
        'scaffold_source': {'path': 'artifacts/circuits/ecdlp_scaffold_optimized.json', 'sha256': scaffold_sha},
        'folded_scaffold_source': {'path': 'artifacts/circuits/ecdlp_scaffold_lookup_folded.json', 'sha256': folded_scaffold_sha},
        'lookup_contract_source': {'path': 'artifacts/lookup/lookup_signed_fold_contract.json', 'sha256': lookup_contract_sha},
        'window_size': int(data['scaffold']['window_size']),
        'retained_window_additions': len(folded_scaffold['retained_window_additions']),
        'phase_register_histogram': dict(phase_hist),
        'expanded_leaf_instruction_count': flat_leaf_count,
        'expanded_instruction_count_total': len(expanded_instructions),
        'leaf_opcode_histogram': dict(opcode_hist),
        'expanded_instructions': expanded_instructions,
        'notes': [
            'This file is an exact hierarchical-to-flat replay of the checked-in leaf over the checked-in retained-window scaffold.',
            'It is still a kickmix-ISA artifact, not a primitive-gate flattening of the full Shor period-finding stack.',
            'The signed folded lookup contract is recorded as the lookup boundary for these retained leaf calls.',
        ],
    }
    out_path = artifact_circuits_path(repo_root / 'artifacts', 'ecdlp_expanded_isa_optimized.json')
    dump_json(out_path, result)
    result['sha256'] = sha256_path(out_path)
    result['path'] = 'artifacts/circuits/ecdlp_expanded_isa_optimized.json'
    return result


def build_backend_model_bundle(repo_root: Path) -> Dict[str, Any]:
    data = load_core_artifacts(repo_root)
    field_bits = int(data['leaf']['field_modulus_hex'], 16).bit_length()
    window_bits = int(data['lookup_contract']['window_size_bits'])
    positive_entries = int(data['lookup_contract']['table_shape']['x_coordinate_table_entries'])
    add_chain = minimal_addition_chain(int(data['leaf']['b3']))
    add_chain_ops = len(add_chain) - 1
    n = field_bits
    add_cost = n - 1
    select_cost = n - 1
    mul_const_cost = add_chain_ops * add_cost
    explicit_field_mul = n * n + 2 * n - 1

    def common_lookup_model() -> Dict[str, Any]:
        return {
            'kind': 'folded_domain_linear',
            'non_clifford_per_channel_per_window': positive_entries,
            'special_case_constant_overhead': 0,
            'channels_source': 'artifacts/circuits/ecdlp_scaffold_lookup_folded.json:retained_window_additions[*].lookup_channels',
        }

    def common_easy_ops() -> Dict[str, Any]:
        return {
            'field_add': {
                'kind': 'gidney_style_modular_add_without_carryout',
                'formula': 'n - 1',
                'field_bits': n,
                'non_clifford': add_cost,
            },
            'field_sub': {
                'kind': 'gidney_style_modular_sub_without_carryout',
                'formula': 'n - 1',
                'field_bits': n,
                'non_clifford': add_cost,
            },
            'select_field_if_flag': {
                'kind': 'bitwise_select_without_extra_carry',
                'formula': 'n - 1',
                'field_bits': n,
                'non_clifford': select_cost,
            },
            'mul_const': {
                'kind': 'addition_chain_modular_add',
                'const_value': int(data['leaf']['b3']),
                'addition_chain': add_chain,
                'modular_add_count': add_chain_ops,
                'adder_non_clifford': add_cost,
                'non_clifford': mul_const_cost,
            },
            'bool_from_flag': {'kind': 'clifford_or_classical_extract', 'non_clifford': 0},
            'clear_bool_from_flag': {
                'kind': 'exact_isa_flag_uncompute',
                'non_clifford': 0,
                'comment': 'The shipped leaf clears the one-bit no-op flag by XORing the same metadata bit back out of the control slot.',
            },
            'lookup_affine_x': {'kind': 'lookup_channel', 'non_clifford': 0},
            'lookup_affine_y': {'kind': 'lookup_channel', 'non_clifford': 0},
            'lookup_meta': {'kind': 'lookup_channel', 'non_clifford': 0},
            'load_input': {'kind': 'alias', 'non_clifford': 0},
        }

    default_ops = common_easy_ops()
    default_ops['field_mul'] = {
        'kind': 'controlled_add_sub_modular_multiplication',
        'formula': 'n^2 + 2n - 1',
        'field_bits': n,
        'non_clifford': explicit_field_mul,
        'comment': 'This is an explicit arithmetic-backend formula applied uniformly to the exact leaf histogram. It remains a backend model, not a primitive-gate lowering of the shipped leaf.',
    }

    liveness_ops = common_easy_ops()
    liveness_ops['field_mul'] = {
        'kind': 'controlled_add_sub_modular_multiplication',
        'formula': 'n^2 + 2n - 1',
        'field_bits': n,
        'non_clifford': explicit_field_mul,
        'comment': 'Arithmetic backend identical to the default explicit model; only the slot-accounting rule changes.',
    }

    bundle = {
        'schema': 'kickmix-backend-model-bundle-v2',
        'default_model': 'addsub_modmul_named_slots_v2',
        'field_bits': field_bits,
        'window_bits': window_bits,
        'lookup_contract_positive_entries': positive_entries,
        'models': [
            {
                'name': 'addsub_modmul_named_slots_v2',
                'status': 'default',
                'summary': 'Default explicit backend model derived from exact source artifacts plus closed-form opcode costs and conservative named-slot qubit accounting.',
                'logical_qubit_model': {
                    'field_slot_logical_qubits': 72,
                    'live_window_key_qubits': window_bits,
                    'slot_accounting_mode': 'allocated_named_slots',
                    'include_auxiliary_control_slots_in_qubit_total': False,
                    'comment': 'The field-slot width remains a backend assumption; the total is derived from source artifacts using the checked-in named scratch-slot allocation.',
                },
                'lookup_model': common_lookup_model(),
                'opcode_models': default_ops,
            },
            {
                'name': 'addsub_modmul_liveness_v2',
                'status': 'experimental',
                'summary': 'Experimental low-qubit transfer that keeps the default explicit arithmetic backend but prices qubits from exact ISA liveness instead of named-slot allocation.',
                'logical_qubit_model': {
                    'field_slot_logical_qubits': 72,
                    'live_window_key_qubits': window_bits,
                    'slot_accounting_mode': 'peak_live_isa_slots',
                    'include_auxiliary_control_slots_in_qubit_total': False,
                    'comment': 'This scenario reuses dead ISA slots across the leaf schedule. It is more aggressive than the default named-slot allocation and should be read as a backend register-allocation experiment.',
                },
                'lookup_model': common_lookup_model(),
                'opcode_models': liveness_ops,
            },
        ],
    }
    out_path = artifact_projection_path(repo_root / 'artifacts', 'backend_model_bundle.json')
    dump_json(out_path, bundle)
    return bundle


def compute_structural_accounting(repo_root: Path, expanded_schedule: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    data = load_core_artifacts(repo_root)
    leaf = data['leaf']
    register_map = data['register_map']
    folded_scaffold = data['folded_scaffold']
    expanded = expanded_schedule or expand_scaffold_isa(repo_root)
    leaf_hist = Counter(ins['op'] for ins in leaf['instructions'])
    liveness = compute_leaf_liveness(leaf, register_map)
    lookup_channels = sorted({int(entry['lookup_channels']) for entry in folded_scaffold['retained_window_additions']})

    result = {
        'schema': 'kickmix-structural-accounting-v1',
        'sources': {
            'leaf_path': 'artifacts/circuits/optimized_pointadd_secp256k1.json',
            'leaf_sha256': sha256_path(data['leaf_path']),
            'scaffold_path': 'artifacts/circuits/ecdlp_scaffold_optimized.json',
            'scaffold_sha256': sha256_path(data['scaffold_path']),
            'folded_scaffold_path': 'artifacts/circuits/ecdlp_scaffold_lookup_folded.json',
            'folded_scaffold_sha256': sha256_path(data['folded_scaffold_path']),
            'register_map_path': 'artifacts/circuits/register_map.json',
            'register_map_sha256': sha256_path(data['register_map_path']),
            'lookup_contract_path': 'artifacts/lookup/lookup_signed_fold_contract.json',
            'lookup_contract_sha256': sha256_path(data['lookup_contract_path']),
            'expanded_isa_path': expanded['path'],
            'expanded_isa_sha256': expanded['sha256'],
        },
        'field_bits': int(leaf['field_modulus_hex'], 16).bit_length(),
        'window_bits': int(data['lookup_contract']['window_size_bits']),
        'leaf': {
            'instruction_count': len(leaf['instructions']),
            'allocated_field_slot_count': int(register_map.get('scratch_slot_count', len(register_map.get('arithmetic_slots', [])))),
            'opcode_histogram': dict(leaf_hist),
            'arithmetic_signature': {
                'field_mul': leaf_hist.get('field_mul', 0),
                'field_add': leaf_hist.get('field_add', 0),
                'field_sub': leaf_hist.get('field_sub', 0),
                'field_add_sub': leaf_hist.get('field_add', 0) + leaf_hist.get('field_sub', 0),
                'mul_const': leaf_hist.get('mul_const', 0),
                'select_field_if_flag': leaf_hist.get('select_field_if_flag', 0),
                'lookup_ops': sum(leaf_hist.get(op, 0) for op in LOOKUP_OPS),
            },
            'liveness': liveness,
        },
        'expanded_scaffold': {
            'retained_window_additions': len(folded_scaffold['retained_window_additions']),
            'phase_register_histogram': expanded['phase_register_histogram'],
            'leaf_instruction_count': expanded['expanded_leaf_instruction_count'],
            'instruction_count_total_including_markers': expanded['expanded_instruction_count_total'],
            'opcode_histogram': expanded['leaf_opcode_histogram'],
        },
        'lookup_contract': {
            'positive_table_entries_per_coordinate': int(data['lookup_contract']['table_shape']['x_coordinate_table_entries']),
            'metadata_table_needed': bool(data['lookup_contract']['table_shape']['separate_metadata_table_needed']),
            'effective_lookup_channels_per_call': lookup_channels[0] if len(lookup_channels) == 1 else lookup_channels,
            'special_case_constant_points_per_window': int(data['lookup_contract']['table_shape']['per_window_special_constant_points']),
        },
        'notes': [
            'All counts in this file are derived from checked-in source artifacts.',
            'The leaf liveness section measures exact ISA-slot activity, not primitive-gate ancilla usage.',
        ],
    }
    out_path = artifact_projection_path(repo_root / 'artifacts', 'structural_accounting.json')
    dump_json(out_path, result)
    return result


def _project_from_model(
    model: Mapping[str, Any],
    structural: Mapping[str, Any],
    public_google_baseline: Mapping[str, Any],
) -> Dict[str, Any]:
    leaf_hist = structural['leaf']['opcode_histogram']
    retained = int(structural['expanded_scaffold']['retained_window_additions'])
    field_bits = int(structural['field_bits'])
    peak_live_field_slots = int(structural['leaf']['liveness']['peak_arithmetic_slots']['active_arithmetic_slot_count'])
    peak_live_control_slots = int(structural['leaf']['liveness']['peak_control_slots']['active_control_slot_count'])
    allocated_field_slots = int(structural['leaf']['allocated_field_slot_count'])

    per_opcode_costs = {
        op: int(model['opcode_models'].get(op, {}).get('non_clifford', 0))
        for op in leaf_hist.keys()
    }
    leaf_non_clifford_ex_lookup = sum(
        int(count) * per_opcode_costs.get(op, 0)
        for op, count in leaf_hist.items()
        if op not in LOOKUP_OPS and op not in ZERO_COST_OPS and op not in CONTROL_OPS
    )
    # add the explicit low-cost control families that were skipped above if they carry a nonzero cost
    leaf_non_clifford_ex_lookup += sum(
        int(count) * per_opcode_costs.get(op, 0)
        for op, count in leaf_hist.items()
        if op in CONTROL_OPS
    )

    lookup_channels = structural['lookup_contract']['effective_lookup_channels_per_call']
    if isinstance(lookup_channels, list):
        if len(set(lookup_channels)) != 1:
            raise ValueError(f'inconsistent lookup-channel counts: {lookup_channels}')
        lookup_channels = int(lookup_channels[0])
    else:
        lookup_channels = int(lookup_channels)
    per_lookup_channel_cost = int(model['lookup_model']['non_clifford_per_channel_per_window'])
    lookup_overhead = int(model['lookup_model'].get('special_case_constant_overhead', 0))
    per_window_lookup_cost = lookup_channels * per_lookup_channel_cost + lookup_overhead

    field_slot_qubits = int(model['logical_qubit_model']['field_slot_logical_qubits'])
    live_key_qubits = int(model['logical_qubit_model']['live_window_key_qubits'])
    slot_mode = model['logical_qubit_model'].get('slot_accounting_mode', 'allocated_named_slots')
    include_controls = bool(model['logical_qubit_model'].get('include_auxiliary_control_slots_in_qubit_total', False))
    if slot_mode == 'peak_live_isa_slots':
        effective_field_slots = peak_live_field_slots
    elif slot_mode == 'allocated_named_slots':
        effective_field_slots = allocated_field_slots
    else:
        raise ValueError(f'unknown slot accounting mode: {slot_mode}')
    scratch_logical_qubits = effective_field_slots * field_slot_qubits
    logical_qubits_total = scratch_logical_qubits + live_key_qubits
    if include_controls:
        logical_qubits_total += peak_live_control_slots

    total_2lookup = retained * (leaf_non_clifford_ex_lookup + 2 * per_lookup_channel_cost + lookup_overhead)
    total_3lookup = retained * (leaf_non_clifford_ex_lookup + 3 * per_lookup_channel_cost + lookup_overhead)

    low_qubit = public_google_baseline['low_qubit']
    low_gate = public_google_baseline['low_gate']
    return {
        'model_name': model['name'],
        'status': model['status'],
        'summary': model['summary'],
        'logical_qubit_model': model['logical_qubit_model'],
        'lookup_model': {
            **model['lookup_model'],
            'effective_lookup_channels_per_call': lookup_channels,
            'per_window_lookup_cost_2channel': 2 * per_lookup_channel_cost + lookup_overhead,
            'per_window_lookup_cost_3channel': 3 * per_lookup_channel_cost + lookup_overhead,
        },
        'per_opcode_non_clifford': per_opcode_costs,
        'leaf': {
            'field_bits': field_bits,
            'instruction_count': int(structural['leaf']['instruction_count']),
            'arithmetic_signature': structural['leaf']['arithmetic_signature'],
            'scratch_logical_qubits': scratch_logical_qubits,
            'allocated_field_slots': allocated_field_slots,
            'effective_field_slots': effective_field_slots,
            'peak_live_field_slots': peak_live_field_slots,
            'peak_live_control_slots': peak_live_control_slots,
            'modeled_non_clifford_excluding_lookup': leaf_non_clifford_ex_lookup,
        },
        'ecdlp': {
            'retained_window_additions': retained,
            'logical_qubits_total': logical_qubits_total,
            'lookup_model_2channel': {
                'lookup_channels': 2,
                'per_window_lookup_cost': 2 * per_lookup_channel_cost + lookup_overhead,
                'total_non_clifford': total_2lookup,
            },
            'lookup_model_3channel': {
                'lookup_channels': 3,
                'per_window_lookup_cost': 3 * per_lookup_channel_cost + lookup_overhead,
                'total_non_clifford': total_3lookup,
            },
        },
        'improvement_vs_google': {
            'versus_low_qubit': {
                'qubit_gain': low_qubit['logical_qubits'] / logical_qubits_total,
                'toffoli_gain_2lookup': low_qubit['non_clifford'] / total_2lookup,
                'toffoli_gain_3lookup': low_qubit['non_clifford'] / total_3lookup,
            },
            'versus_low_gate': {
                'qubit_gain': low_gate['logical_qubits'] / logical_qubits_total,
                'toffoli_gain_2lookup': low_gate['non_clifford'] / total_2lookup,
                'toffoli_gain_3lookup': low_gate['non_clifford'] / total_3lookup,
            },
        },
    }


PUBLIC_GOOGLE_BASELINE = {
    'source': 'Google/Babbush et al. 2026 rounded published secp256k1 estimates',
    'window_size': 16,
    'retained_window_additions': 28,
    'low_qubit': {
        'logical_qubits': 1200,
        'non_clifford': 90_000_000,
    },
    'low_gate': {
        'logical_qubits': 1450,
        'non_clifford': 70_000_000,
    },
}


def build_derived_resource_family(repo_root: Path) -> Dict[str, Any]:
    expanded = expand_scaffold_isa(repo_root)
    structural = compute_structural_accounting(repo_root, expanded)
    backend_bundle = build_backend_model_bundle(repo_root)
    models = {model['name']: model for model in backend_bundle['models']}

    default_model = models[backend_bundle['default_model']]
    primary = _project_from_model(default_model, structural, PUBLIC_GOOGLE_BASELINE)
    alternatives = [
        _project_from_model(model, structural, PUBLIC_GOOGLE_BASELINE)
        for name, model in models.items()
        if name != backend_bundle['default_model']
    ]

    family = {
        'model_name': primary['model_name'],
        'honesty_note': 'Semantic correctness is exact at the kickmix-ISA level. The logical-qubit and non-Clifford totals below are versioned backend projections derived from source artifacts, not theorem-proved primitive-gate counts.',
        'public_google_baseline': PUBLIC_GOOGLE_BASELINE,
        'source_artifacts': structural['sources'],
        'expanded_isa_schedule': {
            'path': expanded['path'],
            'sha256': expanded['sha256'],
            'expanded_leaf_instruction_count': expanded['expanded_leaf_instruction_count'],
            'expanded_instruction_count_total': expanded['expanded_instruction_count_total'],
        },
        'backend_model_bundle': {
            'path': 'artifacts/projections/backend_model_bundle.json',
            'default_model': backend_bundle['default_model'],
            'model_names': [model['name'] for model in backend_bundle['models']],
        },
        'structural_accounting': {
            'path': 'artifacts/projections/structural_accounting.json',
            'leaf_instruction_count': structural['leaf']['instruction_count'],
            'retained_window_additions': structural['expanded_scaffold']['retained_window_additions'],
            'leaf_opcode_histogram': structural['leaf']['opcode_histogram'],
            'allocated_field_slots': structural['leaf']['allocated_field_slot_count'],
            'peak_live_field_slots': structural['leaf']['liveness']['peak_arithmetic_slots']['active_arithmetic_slot_count'],
        },
        'optimized_leaf_projection': primary['leaf'],
        'optimized_ecdlp_projection': primary['ecdlp'],
        'default_model_details': {
            'summary': primary['summary'],
            'logical_qubit_model': primary['logical_qubit_model'],
            'lookup_model': primary['lookup_model'],
            'per_opcode_non_clifford': primary['per_opcode_non_clifford'],
        },
        'alternative_backend_scenarios': alternatives,
        'improvement_vs_google': primary['improvement_vs_google'],
    }
    return family


def write_derived_resource_family(repo_root: Path) -> Dict[str, Any]:
    family = build_derived_resource_family(repo_root)
    dump_json(artifact_projection_path(repo_root / 'artifacts', 'resource_projection.json'), family)
    return family
