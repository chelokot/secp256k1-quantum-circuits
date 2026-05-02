#!/usr/bin/env python3
"""Exact compiler-family build and verification helpers.

This subproject lives beside the repository mainline and deliberately tightens
one specific boundary: instead of stopping at an ISA-level leaf plus a modeled
backend bundle, it chooses *named exact compiler families* and derives whole-
oracle counts for those families from checked-in artifacts.

Two ideas drive the current pass:

* **exact schedule completion** — the compiler project closes the classical-tail
  elision gap and builds a fully quantum raw-32 oracle (1 direct seed + 31 leaf
  calls);
* **exact qubit tightening inside the chosen family** — qubit counts are no
  longer taken from a coarse “10 live field slots + 512 phase bits” policy. The
  compiler project uses (a) exact versioned leaf live ranges with register
  reuse and (b) an explicit phase-shell family that includes a semiclassical-QFT
  option.

The resulting counts are exact for the chosen family. They are *not* claims of
hidden-Google reconstruction or global optimality.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from importlib import import_module
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ROOT_SRC = PROJECT_ROOT / 'src'
if str(ROOT_SRC) not in sys.path:
    sys.path.insert(0, str(ROOT_SRC))

from common import (  # noqa: E402
    SECP_B,
    SECP_G,
    SECP_N,
    SECP_P,
    add_affine,
    affine_to_proj,
    artifact_circuits_path,
    deterministic_scalars,
    dump_json,
    hex_or_inf,
    load_json,
    mul_fixed_window,
    precompute_window_tables,
    proj_to_affine,
    sha256_bytes,
    sha256_path,
)
from arithmetic_lowering import arithmetic_kernel_summary, arithmetic_lowering_library  # noqa: E402
from ft_ir import build_ft_ir_compositions as build_ft_ir_compositions_single  # noqa: E402
from generated_block_inventory import build_generated_block_inventories as build_generated_block_inventories_single  # noqa: E402
from lookup_fed_leaf import (  # noqa: E402
    LOOKUP_FED_ARITHMETIC_SLOTS,
    LOOKUP_FED_CONTROL_SLOTS,
    STREAMED_LOOKUP_TAIL_ARITHMETIC_SLOTS,
    STREAMED_LOOKUP_TAIL_CONTROL_SLOTS,
    build_lookup_fed_leaf,
    build_lookup_fed_leaf_equivalence,
    build_streamed_lookup_tail_leaf,
    build_streamed_lookup_tail_leaf_equivalence,
    execute_leaf_contract,
)
from lookup_lowering import lookup_lowering_library  # noqa: E402
from phase_shell_lowering import phase_shell_family_summary, phase_shell_lowering_library  # noqa: E402
from physical_estimator import (  # noqa: E402
    build_azure_estimator_target_payload,
    build_or_load_azure_estimator_results_payload,
)
from subcircuit_equivalence import build_subcircuit_equivalence_artifact  # noqa: E402
from whole_oracle_recount import build_whole_oracle_recount as build_whole_oracle_recount_single  # noqa: E402

PointAffine = Optional[Tuple[int, int]]

FIELD_BITS = 256
RAW_WINDOW_BITS = 16
FOLDED_MAG_BITS = 15
FOLDED_MAG_DOMAIN = 1 << FOLDED_MAG_BITS  # 32768 magnitudes 0..32767
FULL_RAW_WINDOWS = 32
FULL_PHASE_REGISTER_BITS = 512
PUBLIC_GOOGLE_BASELINE = {
    'low_qubit': {'logical_qubits': 1200, 'non_clifford': 90_000_000},
    'low_gate': {'logical_qubits': 1450, 'non_clifford': 70_000_000},
}
CENTRAL_LOOKUP_FAMILY = 'folded_standard_qroam_streamed_coordinate_v1'
CENTRAL_PHASE_SHELL = 'semiclassical_qft_v1'


@dataclass(frozen=True)
class LookupFamily:
    name: str
    summary: str
    gate_set: str
    compute_lookup_non_clifford: int
    uncompute_lookup_non_clifford: int
    zero_check_non_clifford: int
    magnitude_prepare_non_clifford: int
    conditional_negate_y_non_clifford: int
    direct_lookup_non_clifford: int
    per_leaf_lookup_non_clifford: int
    extra_lookup_workspace_qubits: int
    notes: List[str]


@dataclass(frozen=True)
class PhaseShellFamily:
    name: str
    summary: str
    gate_set: str
    live_quantum_bits: int
    hadamard_count: int
    total_measurements: int
    total_rotations: int
    rotation_depth: int
    single_qubit_rotation_count: int
    controlled_rotation_count: int
    notes: List[str]


@dataclass(frozen=True)
class SlotAllocationFamily:
    name: str
    summary: str
    source_artifact: str
    leaf_source_artifact: str
    slot_allocation: Dict[str, Any]
    notes: List[str]


@dataclass(frozen=True)
class CompilerFamilyResult:
    name: str
    summary: str
    gate_set: str
    phase_shell: str
    slot_allocation_family: str
    arithmetic_kernel_family: str
    lookup_family: str
    arithmetic_leaf_non_clifford: int
    direct_seed_non_clifford: int
    per_leaf_lookup_non_clifford: int
    full_oracle_non_clifford: int
    arithmetic_slot_count: int
    control_slot_count: int
    borrowed_interface_qubits: int
    lookup_workspace_qubits: int
    live_phase_bits: int
    total_logical_qubits: int
    phase_shell_hadamards: int
    phase_shell_measurements: int
    phase_shell_rotations: int
    phase_shell_rotation_depth: int
    total_measurements: int
    improvement_vs_google_low_qubit: float
    improvement_vs_google_low_gate: float
    qubit_ratio_vs_google_low_qubit: float
    qubit_ratio_vs_google_low_gate: float
    notes: List[str]


# ---------------------------------------------------------------------------
# Paths and checked-in artifacts
# ---------------------------------------------------------------------------


def project_artifact_path(name: str) -> Path:
    path = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    return path



def _leaf() -> Dict[str, Any]:
    return load_json(artifact_circuits_path(PROJECT_ROOT / 'artifacts', 'optimized_pointadd_secp256k1.json'))


def central_executable_leaf() -> Dict[str, Any]:
    return build_streamed_lookup_tail_leaf(_leaf())

def _scaffold() -> Dict[str, Any]:
    return load_json(artifact_circuits_path(PROJECT_ROOT / 'artifacts', 'ecdlp_scaffold_optimized.json'))


# ---------------------------------------------------------------------------
# Canonical public point and raw-32 schedule
# ---------------------------------------------------------------------------


def canonical_public_point() -> Dict[str, Any]:
    leaf_path = artifact_circuits_path(PROJECT_ROOT / 'artifacts', 'optimized_pointadd_secp256k1.json')
    scaffold_path = artifact_circuits_path(PROJECT_ROOT / 'artifacts', 'ecdlp_scaffold_optimized.json')
    leaf_sha = sha256_path(leaf_path)
    scaffold_sha = sha256_path(scaffold_path)
    seed = bytes.fromhex(sha256_bytes(bytes.fromhex(leaf_sha) + bytes.fromhex(scaffold_sha)))
    h_scalar = deterministic_scalars(seed + b'compiler-project-public-point', 1, SECP_N)[0]
    g_tables = precompute_window_tables(SECP_G, SECP_P, SECP_B, width=8, bits=256)
    h_point = mul_fixed_window(h_scalar, g_tables, SECP_P, SECP_B, width=8, order=SECP_N)
    assert h_point is not None
    return {
        'derivation': 'first deterministic public-point base from the checked-in leaf/scaffold hash stream',
        'leaf_sha256': leaf_sha,
        'scaffold_sha256': scaffold_sha,
        'h_scalar_hex': format(h_scalar, '064x'),
        'point': {
            'x_hex': format(h_point[0], '064x'),
            'y_hex': format(h_point[1], '064x'),
        },
    }



def window_bases(base: PointAffine, width: int = RAW_WINDOW_BITS, windows: int = 16) -> List[PointAffine]:
    arr: List[PointAffine] = [None] * windows
    arr[0] = base
    for i in range(1, windows):
        q = arr[i - 1]
        for _ in range(width):
            q = add_affine(q, q, SECP_P, SECP_B)
        arr[i] = q
    return arr



def raw32_schedule() -> Dict[str, Any]:
    calls: List[Dict[str, Any]] = []
    call_index = 0
    for idx in range(1, 16):
        calls.append({
            'call_index': call_index,
            'phase_register': 'phase_a',
            'window_index_within_register': idx,
            'bit_start': 16 * idx,
            'bit_width': 16,
        })
        call_index += 1
    for idx in range(16):
        calls.append({
            'call_index': call_index,
            'phase_register': 'phase_b',
            'window_index_within_register': idx,
            'bit_start': 16 * idx,
            'bit_width': 16,
        })
        call_index += 1
    return {
        'schema': 'compiler-project-full-raw32-v2',
        'curve': 'secp256k1',
        'raw_window_bits': RAW_WINDOW_BITS,
        'raw_window_count': FULL_RAW_WINDOWS,
        'phase_register_bits_total': FULL_PHASE_REGISTER_BITS,
        'direct_seed': {
            'phase_register': 'phase_a',
            'window_index_within_register': 0,
            'bit_start': 0,
            'bit_width': 16,
            'comment': 'This exact compiler path closes the mainline classical-tail-elision gap.',
        },
        'leaf_calls': calls,
        'summary': {
            'phase_a_leaf_calls': 15,
            'phase_b_leaf_calls': 16,
            'leaf_call_count_total': 31,
            'classical_tail_elisions_removed': 3,
            'lookup_invocations_total': 32,
        },
    }


# ---------------------------------------------------------------------------
# Exact leaf slot allocation
# ---------------------------------------------------------------------------


def _iter_register_references(ins: Mapping[str, Any], tracked: set[str]) -> Iterable[str]:
    src = ins.get('src')
    if isinstance(src, list):
        for value in src:
            if isinstance(value, str) and value in tracked:
                yield value
    elif isinstance(src, dict):
        for value in src.values():
            if isinstance(value, str) and value in tracked:
                yield value
    elif isinstance(src, str) and src in tracked:
        yield src
    flag = ins.get('flag')
    if isinstance(flag, str) and flag in tracked:
        yield flag


def _instruction_dsts(ins: Mapping[str, Any], tracked: set[str]) -> List[str]:
    dst = ins.get('dst')
    if isinstance(dst, str):
        return [dst] if dst in tracked else []
    if isinstance(dst, list):
        return [value for value in dst if isinstance(value, str) and value in tracked]
    return []


def _resource_ownership_contract(
    *,
    exact_arithmetic_slot_count: int,
    exact_control_slot_count: int,
    exact_borrowed_field_slot_count: int,
    peak_arithmetic_slots: int,
    peak_control_slots: int,
    arithmetic_version_count: int,
    control_version_count: int,
    source_artifact: str,
) -> Dict[str, Any]:
    owners = [
        {
            'owner': 'arithmetic_slot_register_file',
            'wire_class': 'field',
            'logical_qubit_budget': int(exact_arithmetic_slot_count * FIELD_BITS),
            'required_logical_qubits': int(peak_arithmetic_slots * FIELD_BITS),
            'live_wire_peak': int(peak_arithmetic_slots),
            'assigned_register_versions': int(arithmetic_version_count),
            'source_artifact': source_artifact,
        },
        {
            'owner': 'control_slot_register_file',
            'wire_class': 'control',
            'logical_qubit_budget': int(exact_control_slot_count),
            'required_logical_qubits': int(peak_control_slots),
            'live_wire_peak': int(peak_control_slots),
            'assigned_register_versions': int(control_version_count),
            'source_artifact': source_artifact,
        },
        {
            'owner': 'borrowed_lookup_interface_field_lanes',
            'wire_class': 'field',
            'logical_qubit_budget': int(exact_borrowed_field_slot_count * FIELD_BITS),
            'required_logical_qubits': int(exact_borrowed_field_slot_count * FIELD_BITS),
            'live_wire_peak': int(exact_borrowed_field_slot_count),
            'assigned_register_versions': 0,
            'source_artifact': source_artifact,
        },
    ]
    return {
        'schema': 'compiler-project-resource-ownership-v1',
        'field_bits': FIELD_BITS,
        'derived_from': 'executable leaf instruction liveness and assigned register versions',
        'owners': owners,
        'lookup_interface_policy': {
            'coordinate_field_lanes_materialized_by_leaf': 0,
            'coordinate_field_lanes_counted_in_lookup_workspace': 0,
            'qroam_coordinate_target_and_junk_counted_in_lookup_workspace': True,
            'qroam_clean_target_register_qubits_per_live_stream': FIELD_BITS,
            'qroam_clean_junk_register_qubits_per_live_stream': 15 * FIELD_BITS,
            'table_fed_coordinate_operands': ['lookup_x', 'lookup_y', 'lookup_x_plus_y'],
            'statement': 'The streamed lookup contract consumes table coordinates inside table-fed arithmetic kernels; for the standard-QROAM counted family the full coordinate target and required QROAMClean junk registers are assigned to lookup workspace rather than treated as free borrowed field lanes.',
        },
        'no_free_quantum_wire_invariant': {
            'passes': all(owner['logical_qubit_budget'] >= owner['required_logical_qubits'] for owner in owners),
            'capacity_rule': 'Each counted owner budget must cover the peak live wires assigned to that owner; lookup coordinate output lanes are not part of lookup_workspace_qubits unless explicitly materialized.',
        },
    }


def _slot_allocation_for_leaf(
    leaf: Mapping[str, Any],
    arithmetic_slots: Sequence[str],
    control_slots: Sequence[str],
    source_artifact: str,
    notes: Sequence[str],
    borrowed_field_slots: Sequence[str] = (),
) -> Dict[str, Any]:
    arithmetic_slot_set = set(arithmetic_slots)
    control_slot_set = set(control_slots)
    tracked = arithmetic_slot_set | control_slot_set
    versions: List[Dict[str, Any]] = []
    current: Dict[str, int] = {}
    uses: Dict[int, List[int]] = defaultdict(list)
    for pc, ins in enumerate(leaf['instructions']):
        for name in _iter_register_references(ins, tracked):
            if name in current:
                uses[current[name]].append(pc)
        for dst in _instruction_dsts(ins, tracked):
            vid = len(versions)
            current[dst] = vid
            versions.append({'id': vid, 'reg': dst, 'def_pc': pc})
    for version in versions:
        version['last_use'] = max(uses[version['id']]) if uses[version['id']] else version['def_pc']

    free_arithmetic: set[int] = set()
    free_control: set[int] = set()
    next_arithmetic = 0
    next_control = 0
    assigned: Dict[int, int] = {}
    live: set[int] = set()
    per_pc: List[Dict[str, Any]] = []
    for pc, ins in enumerate(leaf['instructions']):
        dsts = _instruction_dsts(ins, tracked)
        new_vids = [version['id'] for version in versions if version['def_pc'] == pc]
        dying_by_type: Dict[str, List[int]] = {
            'arithmetic': [
                old_vid
                for old_vid in list(live)
                if versions[old_vid]['last_use'] == pc and versions[old_vid]['reg'] in arithmetic_slot_set
            ],
            'control': [
                old_vid
                for old_vid in list(live)
                if versions[old_vid]['last_use'] == pc and versions[old_vid]['reg'] in control_slot_set
            ],
        }
        reuse_slots: Dict[int, int] = {}
        for new_vid in new_vids:
            reg_type = 'arithmetic' if versions[new_vid]['reg'] in arithmetic_slot_set else 'control'
            candidates = dying_by_type[reg_type]
            if candidates:
                old_vid = candidates.pop(0)
                reuse_slots[new_vid] = assigned[old_vid]

        live_arithmetic = sorted({assigned[vid] for vid in live if versions[vid]['reg'] in arithmetic_slot_set})
        live_control = sorted({assigned[vid] for vid in live if versions[vid]['reg'] in control_slot_set})
        arithmetic_new_count = sum(1 for new_vid in new_vids if versions[new_vid]['reg'] in arithmetic_slot_set)
        control_new_count = sum(1 for new_vid in new_vids if versions[new_vid]['reg'] in control_slot_set)
        arithmetic_reuse_count = sum(1 for new_vid in reuse_slots if versions[new_vid]['reg'] in arithmetic_slot_set)
        control_reuse_count = sum(1 for new_vid in reuse_slots if versions[new_vid]['reg'] in control_slot_set)
        arithmetic_during = len(live_arithmetic) + arithmetic_new_count - arithmetic_reuse_count
        control_during = len(live_control) + control_new_count - control_reuse_count
        per_pc.append({
            'pc': pc,
            'opcode': ins['op'],
            'arithmetic_slots_live_before_write': len(live_arithmetic),
            'control_slots_live_before_write': len(live_control),
            'arithmetic_slots_needed_during_write': arithmetic_during,
            'control_slots_needed_during_write': control_during,
            'dst': dsts[0] if len(dsts) == 1 else dsts,
            'reuses_existing_slot': bool(reuse_slots),
        })

        for new_vid in new_vids:
            dst = versions[new_vid]['reg']
            if new_vid in reuse_slots:
                slot = reuse_slots[new_vid]
            elif dst in arithmetic_slot_set:
                slot = min(free_arithmetic) if free_arithmetic else next_arithmetic
                if slot == next_arithmetic:
                    next_arithmetic += 1
                else:
                    free_arithmetic.remove(slot)
            else:
                slot = min(free_control) if free_control else next_control
                if slot == next_control:
                    next_control += 1
                else:
                    free_control.remove(slot)
            assigned[new_vid] = slot
            live.add(new_vid)

        to_free = [vid for vid in list(live) if versions[vid]['last_use'] == pc]
        for vid in to_free:
            slot = assigned[vid]
            live.remove(vid)
            if any(assigned[other_vid] == slot for other_vid in live):
                continue
            if versions[vid]['reg'] in arithmetic_slot_set:
                free_arithmetic.add(slot)
            else:
                free_control.add(slot)

        live_arithmetic_slots = [assigned[vid] for vid in live if versions[vid]['reg'] in arithmetic_slot_set]
        live_control_slots = [assigned[vid] for vid in live if versions[vid]['reg'] in control_slot_set]
        assert len(live_arithmetic_slots) == len(set(live_arithmetic_slots))
        assert len(live_control_slots) == len(set(live_control_slots))

    peak_arithmetic = max(per_pc, key=lambda row: row['arithmetic_slots_needed_during_write'])
    peak_control = max(per_pc, key=lambda row: row['control_slots_needed_during_write'])
    peak_total = max(per_pc, key=lambda row: row['arithmetic_slots_needed_during_write'] + row['control_slots_needed_during_write'])
    version_table = []
    for version in versions:
        version_table.append({
            'version_id': version['id'],
            'register': version['reg'],
            'reg_type': 'arithmetic' if version['reg'] in arithmetic_slot_set else 'control',
            'def_pc': version['def_pc'],
            'last_use_pc': version['last_use'],
            'assigned_slot': assigned[version['id']],
        })
    return {
        'schema': 'compiler-project-slot-allocation-v1',
        'field_bits': FIELD_BITS,
        'source_artifact': source_artifact,
        'tracked_arithmetic_registers': sorted(arithmetic_slot_set),
        'tracked_control_registers': sorted(control_slot_set),
        'borrowed_field_registers': sorted(borrowed_field_slots),
        'peak_arithmetic_slots': {
            'count': int(peak_arithmetic['arithmetic_slots_needed_during_write']),
            'pc': int(peak_arithmetic['pc']),
            'opcode': peak_arithmetic['opcode'],
        },
        'peak_control_slots': {
            'count': int(peak_control['control_slots_needed_during_write']),
            'pc': int(peak_control['pc']),
            'opcode': peak_control['opcode'],
        },
        'peak_total_slots': {
            'count': int(peak_total['arithmetic_slots_needed_during_write'] + peak_total['control_slots_needed_during_write']),
            'pc': int(peak_total['pc']),
            'opcode': peak_total['opcode'],
        },
        'allocator_summary': {
            'exact_arithmetic_slot_count': int(next_arithmetic),
            'exact_control_slot_count': int(next_control),
            'exact_borrowed_field_slot_count': len(borrowed_field_slots),
            'arithmetic_bits': int(next_arithmetic * FIELD_BITS),
            'control_bits': int(next_control),
            'borrowed_field_bits': int(len(borrowed_field_slots) * FIELD_BITS),
        },
        'per_pc': per_pc,
        'versions': version_table,
        'resource_ownership': _resource_ownership_contract(
            exact_arithmetic_slot_count=next_arithmetic,
            exact_control_slot_count=next_control,
            exact_borrowed_field_slot_count=len(borrowed_field_slots),
            peak_arithmetic_slots=int(peak_arithmetic['arithmetic_slots_needed_during_write']),
            peak_control_slots=int(peak_control['control_slots_needed_during_write']),
            arithmetic_version_count=sum(1 for version in versions if version['reg'] in arithmetic_slot_set),
            control_version_count=sum(1 for version in versions if version['reg'] in control_slot_set),
            source_artifact=source_artifact,
        ),
        'notes': list(notes),
    }



def exact_leaf_slot_allocation() -> Dict[str, Any]:
    leaf = central_executable_leaf()
    return _slot_allocation_for_leaf(
        leaf=leaf,
        arithmetic_slots=STREAMED_LOOKUP_TAIL_ARITHMETIC_SLOTS,
        control_slots=STREAMED_LOOKUP_TAIL_CONTROL_SLOTS,
        source_artifact='compiler_verification_project/artifacts/exact_leaf_slot_allocation.json',
        notes=[
            'This artifact allocates versioned leaf values to physical slots using exact live ranges plus same-register overwrite reuse.',
            'For the central standard-QROM family it is the streamed lookup tail leaf allocation; lookup coordinate lanes are standard-QROAM streams rather than borrowed field wires.',
        ],
    )


def lookup_fed_leaf_slot_allocation() -> Dict[str, Any]:
    return _slot_allocation_for_leaf(
        leaf=build_lookup_fed_leaf(),
        arithmetic_slots=LOOKUP_FED_ARITHMETIC_SLOTS,
        control_slots=LOOKUP_FED_CONTROL_SLOTS,
        source_artifact='compiler_verification_project/artifacts/lookup_fed_leaf_slot_allocation.json',
        notes=[
            'This artifact allocates the compiler-project lookup-fed leaf interface, where the initial lookup outputs are carried on explicit lookup wires instead of occupying persistent arithmetic slots.',
            'The reordered lookup-fed leaf preserves the checked point-add semantics while reducing the persistent arithmetic register file to seven field slots and the live control register file to one bit.',
        ],
    )


def streamed_lookup_tail_leaf_slot_allocation() -> Dict[str, Any]:
    return _slot_allocation_for_leaf(
        leaf=build_streamed_lookup_tail_leaf(),
        arithmetic_slots=STREAMED_LOOKUP_TAIL_ARITHMETIC_SLOTS,
        control_slots=STREAMED_LOOKUP_TAIL_CONTROL_SLOTS,
        source_artifact='compiler_verification_project/artifacts/streamed_lookup_tail_leaf_slot_allocation.json',
        notes=[
            'This artifact allocates the streamed lookup tail contract directly from executable leaf liveness.',
            'Lookup x/y coordinates are not materialized as field-sized interface lanes; table-fed arithmetic kernels consume them as constants, and the resource ownership contract records zero borrowed lookup field lanes.',
            'The complete_a0_streamed_tail multi-output instruction consumes C/K/L/I/Y/Z and derives E/F/M/N internally, so the peak arithmetic register file is six field slots.',
        ],
    )


def streamed_lookup_table_multiplier_resource(
    arithmetic_lowerings: Optional[Mapping[str, Any]] = None,
    lookup_lowerings: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    arithmetic = arithmetic_lowerings if arithmetic_lowerings is not None else arithmetic_lowering_library(
        FIELD_BITS,
        leaf_opcode_histogram(),
    )
    lookup = lookup_lowerings if lookup_lowerings is not None else lookup_lowering_library()
    kernel_lookup = {kernel['opcode']: kernel for kernel in arithmetic['kernels']}
    lookup_family = next(row for row in lookup['families'] if row['name'] == CENTRAL_LOOKUP_FAMILY)
    bit_sources = [
        ('lookup_x', 'field_mul_lookup_x', int(leaf_opcode_histogram().get('field_mul_lookup_x', 0))),
        ('lookup_y', 'field_mul_lookup_y', int(leaf_opcode_histogram().get('field_mul_lookup_y', 0))),
        ('lookup_x_plus_y', 'field_mul_lookup_sum', int(leaf_opcode_histogram().get('field_mul_lookup_sum', 0))),
        ('lookup_y', 'complete_a0_streamed_tail', int(leaf_opcode_histogram().get('complete_a0_streamed_tail', 0))),
    ]
    source_rows = []
    per_leaf_streamed_kernel_count = 0
    per_leaf_data_select_non_clifford = 0
    for bit_source, opcode, count in bit_sources:
        kernel = kernel_lookup[opcode]
        data_select_stages = [
            stage for stage in kernel['stages'] if stage['category'] == 'streamed_lookup_data_select'
        ]
        data_select_non_clifford = sum(int(stage['non_clifford_total']) for stage in data_select_stages)
        source_rows.append({
            'bit_source': bit_source,
            'consumer_opcode': opcode,
            'per_leaf_kernel_count': count,
            'field_bits_streamed_per_kernel': FIELD_BITS,
            'data_select_non_clifford_per_kernel': data_select_non_clifford,
            'data_select_non_clifford_per_leaf': data_select_non_clifford * count,
            'stage_names': [stage['name'] for stage in data_select_stages],
        })
        per_leaf_streamed_kernel_count += count
        per_leaf_data_select_non_clifford += data_select_non_clifford * count
    leaf_calls = int(raw32_schedule()['summary']['leaf_call_count_total'])
    total_workspace = int(lookup_family['extra_lookup_workspace_qubits'])
    persistent_workspace = int(lookup_family['workspace_reconstruction']['persistent_workspace_qubits'])
    local_qroam_workspace = total_workspace - persistent_workspace
    per_kernel_costs = sorted({
        int(row['data_select_non_clifford_per_kernel'])
        for row in source_rows
        if int(row['data_select_non_clifford_per_kernel']) > 0
    })
    return {
        'schema': 'compiler-project-standard-qroam-streamed-lookup-table-resource-v1',
        'field_bits': FIELD_BITS,
        'selected_lookup_family': CENTRAL_LOOKUP_FAMILY,
        'selected_leaf_family': 'streamed_lookup_tail_leaf_v1',
        'source_artifacts': {
            'arithmetic_lowerings': 'compiler_verification_project/artifacts/arithmetic_lowerings.json',
            'lookup_lowerings': 'compiler_verification_project/artifacts/lookup_lowerings.json',
            'streamed_lookup_tail_leaf': 'compiler_verification_project/artifacts/streamed_lookup_tail_leaf.json',
            'streamed_lookup_tail_leaf_slot_allocation': 'compiler_verification_project/artifacts/streamed_lookup_tail_leaf_slot_allocation.json',
        },
        'coordinate_bit_sources': source_rows,
        'streamed_data_selection_model': {
            'standard_qrom_equivalent': True,
            'primitive': 'standard_qroam_clean_full_coordinate_stream',
            'folded_magnitude_bits': 15,
            'folded_coordinate_domain_size': FOLDED_MAG_DOMAIN,
            'qroam_block_size': 16,
            'qroam_target_bitsize': FIELD_BITS,
            'table_controlled_coordinate_bits': ['lookup_x', 'lookup_y', 'lookup_x_plus_y'],
            'decomposition': {
                'lookup_compute_non_clifford': 5_888,
                'measured_uncompute_non_clifford': 2_063,
            },
            'per_kernel_non_clifford': 7_951,
            'per_leaf_streamed_kernel_count': per_leaf_streamed_kernel_count,
            'per_leaf_data_select_non_clifford': per_leaf_data_select_non_clifford,
            'leaf_call_count_total': leaf_calls,
            'whole_oracle_data_select_non_clifford': per_leaf_data_select_non_clifford * leaf_calls,
        },
        'workspace_contract': {
            'lookup_workspace_qubits': total_workspace,
            'folded_control_workspace_qubits': persistent_workspace,
            'standard_qroam_local_workspace_qubits': local_qroam_workspace,
            'qroam_clean_target_register_qubits': FIELD_BITS,
            'qroam_clean_junk_register_count': 15,
            'qroam_clean_junk_register_bitsize': FIELD_BITS,
            'qroam_clean_junk_register_qubits': 15 * FIELD_BITS,
            'qroam_clean_target_plus_junk_qubits': 16 * FIELD_BITS,
            'coordinate_field_lanes_materialized': 0,
            'coordinate_field_lane_qubits_materialized': 0,
            'passes': (
                total_workspace == persistent_workspace + 16 * FIELD_BITS
                and persistent_workspace == 18
                and local_qroam_workspace == 16 * FIELD_BITS
            ),
        },
        'capacity_check': {
            'per_kernel_costs_seen': per_kernel_costs,
            'all_coordinate_streams_use_standard_qroam_cost': per_kernel_costs == [7_951],
            'qroam_clean_capacity_matches_cost_model': local_qroam_workspace == 16 * FIELD_BITS,
            'whole_oracle_stream_count': per_leaf_streamed_kernel_count * leaf_calls,
        },
        'notes': [
            'This artifact keeps the standard-QROM table-controlled multiplier resource model consistent: every coordinate stream pays a standard QROAMClean compute plus measured-uncompute primitive and the workspace counts the matching full-coordinate target plus junk registers.',
            'No field-sized lookup x/y output lane is free; the coordinate target and QROAMClean junk capacity are explicitly assigned to lookup_workspace_qubits while the consuming arithmetic kernel runs.',
        ],
    }


def standard_qrom_lookup_assessment(
    frontier: Optional[Mapping[str, Any]] = None,
    lookup_lowerings: Optional[Mapping[str, Any]] = None,
    streamed_resource: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    effective_frontier = frontier if frontier is not None else compiler_family_frontier()
    lookup = lookup_lowerings if lookup_lowerings is not None else lookup_lowering_library()
    resource = streamed_resource if streamed_resource is not None else streamed_lookup_table_multiplier_resource(
        lookup_lowerings=lookup,
    )
    family = dict(effective_frontier['best_qubit_family'])
    lookup_family = next(row for row in lookup['families'] if row['name'] == CENTRAL_LOOKUP_FAMILY)
    positive_domain_size = int(lookup['lookup_contract_summary']['positive_domain_size'])
    coordinate_bits = int(lookup['lookup_contract_summary']['coordinate_bits'])
    materialized_coordinate_lane_qubits = 2 * coordinate_bits
    current_total_qubits = int(family['total_logical_qubits'])
    current_lookup_workspace = int(family['lookup_workspace_qubits'])
    full_coordinate_qrom_qubit_proxy = (
        current_total_qubits
        - current_lookup_workspace
        + int(lookup_family['extra_lookup_workspace_qubits'])
        + materialized_coordinate_lane_qubits
    )
    standard_unary_qrom_compute_toffoli = positive_domain_size - 1
    current_compute_toffoli = int(lookup_family['compute_lookup_non_clifford'])
    current_uncompute_toffoli = int(lookup_family['uncompute_lookup_non_clifford'])
    streamed_model = resource['streamed_data_selection_model']
    standard_qroam_per_stream_toffoli = int(streamed_model['per_kernel_non_clifford'])
    standard_unary_qrom_per_output_bit_toffoli = standard_unary_qrom_compute_toffoli
    standard_unary_qrom_per_coordinate_toffoli = (
        coordinate_bits * standard_unary_qrom_per_output_bit_toffoli
    )
    streamed_bit_standard_lower_bound_per_leaf = (
        int(streamed_model['per_leaf_streamed_kernel_count']) * standard_unary_qrom_per_coordinate_toffoli
    )
    return {
        'schema': 'compiler-project-standard-qrom-lookup-assessment-v2',
        'status': 'standard_qrom_primitive_circuit_proven_for_counted_family_with_high_workspace',
        'selected_boundary_family': family['name'],
        'source_artifacts': {
            'family_frontier': 'compiler_verification_project/artifacts/family_frontier.json',
            'lookup_lowerings': 'compiler_verification_project/artifacts/lookup_lowerings.json',
            'streamed_lookup_table_multiplier_resource': 'compiler_verification_project/artifacts/streamed_lookup_table_multiplier_resource.json',
        },
        'external_reference_model': {
            'gidney_2019_windowed_quantum_arithmetic': {
                'url': 'https://arxiv.org/abs/1905.07682',
                'lookup_compute_rule': 'table lookup over L classical entries has Toffoli count L - 1, independent of output width at this abstraction layer',
            },
            'qualtran_unary_iteration_qrom': {
                'url': 'https://qualtran.readthedocs.io/en/latest/bloqs/data_loading/qrom.html',
                'lookup_compute_rule': 'T/Toffoli cost scales linearly with the product of selection-space iteration lengths',
            },
            'qualtran_qroam_clean': {
                'url': 'https://qualtran.readthedocs.io/en/latest/bloqs/data_loading/qroam_clean.html',
                'lookup_compute_rule': 'QROAMClean uses N/K + (K - 1)b Toffoli gates and requires (K - 1) junk registers of bitsize b, in addition to the b-bit target register.',
            },
        },
        'current_boundary_lookup_model': {
            'positive_domain_size': positive_domain_size,
            'folded_magnitude_bits': int(lookup['lookup_contract_summary']['magnitude_bits']),
            'standard_qroam_block_size': int(streamed_model['qroam_block_size']),
            'standard_qroam_target_bitsize': int(streamed_model['qroam_target_bitsize']),
            'compute_lookup_non_clifford': current_compute_toffoli,
            'uncompute_lookup_non_clifford': current_uncompute_toffoli,
            'standard_qroam_coordinate_stream_non_clifford': standard_qroam_per_stream_toffoli,
            'standard_qroam_target_plus_junk_qubits': int(resource['workspace_contract']['qroam_clean_target_plus_junk_qubits']),
            'diagnosis': 'The selected family no longer uses independent address-bit chunk predicates as table data selection. Every coordinate stream is charged as a standard QROAMClean primitive over the full folded 32768-entry coordinate domain, and the matching full-coordinate target plus junk-register workspace is counted.',
        },
        'standard_qrom_gap': {
            'standard_unary_qrom_compute_toffoli_for_full_table': standard_unary_qrom_compute_toffoli,
            'standard_qroam_coordinate_stream_toffoli': standard_qroam_per_stream_toffoli,
            'standard_qroam_coordinate_stream_target_plus_junk_qubits': int(resource['workspace_contract']['qroam_clean_target_plus_junk_qubits']),
            'current_compute_toffoli_shortfall': 0,
            'current_streamed_bit_toffoli_shortfall': 0,
            'current_qroam_workspace_shortfall': 0,
            'standard_qrom_equivalent': True,
        },
        'conservative_implications': {
            'boundary_model_non_clifford': int(family['full_oracle_non_clifford']),
            'boundary_model_logical_qubits': current_total_qubits,
            'stream_each_output_bit_with_standard_qrom_non_clifford_per_kernel': standard_unary_qrom_per_output_bit_toffoli,
            'stream_one_coordinate_with_standard_qrom_non_clifford_per_kernel': standard_unary_qrom_per_coordinate_toffoli,
            'stream_all_leaf_coordinate_streams_with_standard_qrom_non_clifford_per_leaf': streamed_bit_standard_lower_bound_per_leaf,
            'materialize_x_y_with_standard_full_coordinate_qrom_logical_qubit_proxy': full_coordinate_qrom_qubit_proxy,
            'materialized_coordinate_lane_qubits': materialized_coordinate_lane_qubits,
        },
        'public_claim_boundary': {
            'claim': 'The checked family is a standard-QROM primitive-circuit result only with the high QROAMClean workspace included: every table-controlled coordinate stream pays the standard QROAM data-select cost and the matching target plus junk registers are counted in peak live qubits.',
            'required_to_keep_published': [
                'keep the executable leaf, QROAM resource artifact, no-free-wire ownership artifact, generated inventories, ZKP public values, and checked proof bundle on the same selected family',
                'do not substitute the rejected bitwise-banked lookup family into public standard-QROM claims',
                'do not publish a below-1700-qubit standard-QROAM claim unless a different primitive proves both the lower workspace and its data-selection cost',
            ],
        },
    }


def slot_allocation_families() -> List[SlotAllocationFamily]:
    return [
        SlotAllocationFamily(
            name='streamed_lookup_tail_leaf_v1',
            summary='Executable streamed lookup leaf with table-fed coordinate multipliers, boundary no-op semantics, and a counted multi-output complete-add tail.',
            source_artifact='compiler_verification_project/artifacts/streamed_lookup_tail_leaf_slot_allocation.json',
            leaf_source_artifact='compiler_verification_project/artifacts/streamed_lookup_tail_leaf.json',
            slot_allocation=streamed_lookup_tail_leaf_slot_allocation(),
            notes=[
                'This is the repository central standard-QROM leaf contract: no field-sized lookup x/y output lanes are free, and the six-slot arithmetic peak is derived from executable liveness while QROAM target/junk capacity is counted separately in lookup workspace.',
            ],
        ),
    ]


# ---------------------------------------------------------------------------
# Exact arithmetic kernel family and primitive inventory
# ---------------------------------------------------------------------------


def leaf_opcode_histogram() -> Dict[str, int]:
    hist: Dict[str, int] = {}
    for ins in central_executable_leaf()['instructions']:
        hist[ins['op']] = hist.get(ins['op'], 0) + 1
    return hist



def arithmetic_kernel_library() -> Dict[str, Any]:
    return arithmetic_kernel_summary(
        arithmetic_lowering_library(
            field_bits=FIELD_BITS,
            leaf_opcode_histogram=leaf_opcode_histogram(),
        )
    )



def primitive_multiplier_library() -> Dict[str, Any]:
    kernel = arithmetic_kernel_library()
    arithmetic_lowerings = arithmetic_lowering_library(
        field_bits=FIELD_BITS,
        leaf_opcode_histogram=kernel['leaf_opcode_histogram'],
    )
    field_mul_kernel = next(row for row in arithmetic_lowerings['kernels'] if row['opcode'] == 'field_mul')
    leaf = central_executable_leaf()
    schedule = raw32_schedule()
    per_leaf = []
    for instruction in leaf['instructions']:
        opcode = str(instruction['op'])
        if opcode in {'field_mul', 'field_mul_lookup_x', 'field_mul_lookup_y', 'field_mul_lookup_sum'}:
            per_leaf.append({
                'leaf_multiplier_index': len(per_leaf),
                'leaf_pc': int(instruction['pc']),
                'opcode': opcode,
                'family': kernel['name'],
                'field_bits': FIELD_BITS,
                'exact_non_clifford': field_mul_kernel['exact_non_clifford_per_kernel'],
                'gate_set': kernel['gate_set'],
                'arithmetic_lowering_artifact': 'compiler_verification_project/artifacts/arithmetic_lowerings.json',
            })
        elif opcode == 'complete_a0_streamed_tail':
            for tail_product in ('KN', 'EC', 'NM', 'CL', 'ME', 'LK'):
                per_leaf.append({
                    'leaf_multiplier_index': len(per_leaf),
                    'leaf_pc': int(instruction['pc']),
                    'opcode': opcode,
                    'tail_product': tail_product,
                    'family': kernel['name'],
                    'field_bits': FIELD_BITS,
                    'exact_non_clifford': field_mul_kernel['exact_non_clifford_per_kernel'],
                    'gate_set': kernel['gate_set'],
                    'arithmetic_lowering_artifact': 'compiler_verification_project/artifacts/arithmetic_lowerings.json',
                })
    full_instances = []
    for call in schedule['leaf_calls']:
        for entry in per_leaf:
            full_instances.append({
                'call_index': call['call_index'],
                'phase_register': call['phase_register'],
                'window_index_within_register': call['window_index_within_register'],
                **entry,
            })
    total_non_clifford = len(full_instances) * int(field_mul_kernel['exact_non_clifford_per_kernel'])
    return {
        'schema': 'compiler-project-primitive-multiplier-library-v2',
        'family': kernel['name'],
        'field_bits': FIELD_BITS,
        'per_leaf_multiplier_instances': per_leaf,
        'whole_oracle_multiplier_instance_count': len(full_instances),
        'whole_oracle_multiplier_non_clifford_total': total_non_clifford,
        'example_instances': full_instances[:8],
        'notes': [
            'This is an auditable manifest for every 256-bit multiplier instance in the completed raw-32 oracle.',
            'The manifest is flat at the multiplier-instance level. The internal primitive CX/CCX decomposition of the 256-bit arithmetic kernel remains an imported family boundary rather than a checked-in giant gate list.',
        ],
    }


# ---------------------------------------------------------------------------
# Exact lookup families and exact phase-shell families
# ---------------------------------------------------------------------------


def lookup_families() -> List[LookupFamily]:
    rows = []
    for row in lookup_lowering_library()['families']:
        if row['name'] != CENTRAL_LOOKUP_FAMILY:
            continue
        rows.append(
            LookupFamily(
                name=row['name'],
                summary=row['summary'],
                gate_set=row['gate_set'],
                compute_lookup_non_clifford=row['compute_lookup_non_clifford'],
                uncompute_lookup_non_clifford=row['uncompute_lookup_non_clifford'],
                zero_check_non_clifford=row['zero_check_non_clifford'],
                magnitude_prepare_non_clifford=row['magnitude_prepare_non_clifford'],
                conditional_negate_y_non_clifford=row['conditional_negate_y_non_clifford'],
                direct_lookup_non_clifford=row['direct_lookup_non_clifford'],
                per_leaf_lookup_non_clifford=row['per_leaf_lookup_non_clifford'],
                extra_lookup_workspace_qubits=row['extra_lookup_workspace_qubits'],
                notes=row['notes'],
            )
        )
    return rows



def phase_shell_families() -> List[PhaseShellFamily]:
    summary = phase_shell_family_summary(phase_shell_lowering_library(FULL_PHASE_REGISTER_BITS))
    return [
        PhaseShellFamily(
            name=row['name'],
            summary=row['summary'],
            gate_set=row['gate_set'],
            live_quantum_bits=row['live_quantum_bits'],
            hadamard_count=row['hadamard_count'],
            total_measurements=row['total_measurements'],
            total_rotations=row['total_rotations'],
            rotation_depth=row['rotation_depth'],
            single_qubit_rotation_count=row['single_qubit_rotation_count'],
            controlled_rotation_count=row['controlled_rotation_count'],
            notes=row['notes'],
        )
        for row in summary['families']
        if row['name'] == CENTRAL_PHASE_SHELL
    ]


def _central_lookup_lowerings(lookup_lowerings: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        **lookup_lowerings,
        'families': [row for row in lookup_lowerings['families'] if row['name'] == CENTRAL_LOOKUP_FAMILY],
    }


def _central_phase_shell_rows(phase_shells: Sequence[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
    return [row for row in phase_shells if row['name'] == CENTRAL_PHASE_SHELL]


def _rename_family_payload_name(payload: Dict[str, Any], slot_family: SlotAllocationFamily) -> Dict[str, Any]:
    renamed = json.loads(json.dumps(payload))
    for family in renamed['families']:
        family['slot_allocation_family'] = slot_family.name
        family['name'] = f"{family['lookup_family']}__{slot_family.name}__{family['phase_shell']}"
        family['summary'] = f"{family['summary']} / {slot_family.summary}"
    renamed['source_artifacts']['exact_leaf_slot_allocation'] = slot_family.source_artifact
    best_gate = min(
        renamed['families'],
        key=lambda row: (
            int(row['reconstruction']['full_oracle_non_clifford']),
            int(row['reconstruction']['total_logical_qubits']),
        ),
    )
    best_qubit = min(
        renamed['families'],
        key=lambda row: (
            int(row['reconstruction']['total_logical_qubits']),
            int(row['reconstruction']['full_oracle_non_clifford']),
        ),
    )
    renamed['best_gate_family'] = {
        'name': best_gate['name'],
        'reconstruction': best_gate['reconstruction'],
    }
    renamed['best_qubit_family'] = {
        'name': best_qubit['name'],
        'reconstruction': best_qubit['reconstruction'],
    }
    return renamed


def build_generated_block_inventories_payload(
    schedule: Mapping[str, Any],
    kernel: Mapping[str, Any],
    arithmetic_lowerings: Mapping[str, Any],
    lookup_lowerings: Mapping[str, Any],
    phase_shells: List[Mapping[str, Any]],
    field_bits: int,
    public_google_baseline: Mapping[str, Any],
) -> Dict[str, Any]:
    central_lookup_lowerings = _central_lookup_lowerings(lookup_lowerings)
    central_phase_shells = _central_phase_shell_rows(phase_shells)
    partial_payloads = [
        _rename_family_payload_name(
            build_generated_block_inventories_single(
                schedule=schedule,
                slot_allocation={**slot_family.slot_allocation, 'source_artifact': slot_family.source_artifact},
                kernel=kernel,
                arithmetic_lowerings=arithmetic_lowerings,
                lookup_lowerings=central_lookup_lowerings,
                phase_shells=central_phase_shells,
                field_bits=field_bits,
                public_google_baseline=public_google_baseline,
            ),
            slot_family,
        )
        for slot_family in slot_allocation_families()
    ]
    families = [family for payload in partial_payloads for family in payload['families']]
    best_gate = min(
        families,
        key=lambda row: (
            int(row['reconstruction']['full_oracle_non_clifford']),
            int(row['reconstruction']['total_logical_qubits']),
        ),
    )
    best_qubit = min(
        families,
        key=lambda row: (
            int(row['reconstruction']['total_logical_qubits']),
            int(row['reconstruction']['full_oracle_non_clifford']),
        ),
    )
    return {
        'schema': 'compiler-project-generated-block-inventories-v2',
        'source_artifacts': {
            'full_raw32_oracle': 'compiler_verification_project/artifacts/full_raw32_oracle.json',
            'slot_allocations': [slot_family.source_artifact for slot_family in slot_allocation_families()],
            'arithmetic_lowerings': 'compiler_verification_project/artifacts/arithmetic_lowerings.json',
            'lookup_lowerings': 'compiler_verification_project/artifacts/lookup_lowerings.json',
            'phase_shell_lowerings': 'compiler_verification_project/artifacts/phase_shell_lowerings.json',
        },
        'public_google_baseline': dict(public_google_baseline),
        'schedule_summary': dict(schedule['summary']),
        'arithmetic_lowering_family': arithmetic_lowerings['family'],
        'shared_arithmetic_blocks': partial_payloads[0]['shared_arithmetic_blocks'],
        'families': families,
        'best_gate_family': {
            'name': best_gate['name'],
            'reconstruction': best_gate['reconstruction'],
        },
        'best_qubit_family': {
            'name': best_qubit['name'],
            'reconstruction': best_qubit['reconstruction'],
        },
        'notes': [
            'This artifact records the generated whole-oracle block inventory for the repository central standard-QROM compiler family.',
            'The structure follows a compositional call-graph style accounting layer: shared arithmetic blocks, family-specific lookup blocks, qubit contributors, and explicit phase-shell lowering blocks.',
        ],
    }


def build_ft_ir_compositions_payload(
    schedule: Mapping[str, Any],
    arithmetic_lowerings: Mapping[str, Any],
    lookup_lowerings: Mapping[str, Any],
    phase_shells: List[Mapping[str, Any]],
    generated_block_inventories: Mapping[str, Any],
    frontier: Optional[Mapping[str, Any]],
    field_bits: int,
) -> Dict[str, Any]:
    central_lookup_lowerings = _central_lookup_lowerings(lookup_lowerings)
    central_phase_shells = _central_phase_shell_rows(phase_shells)
    generated_lookup = {family['slot_allocation_family']: [] for family in generated_block_inventories['families']}
    for family in generated_block_inventories['families']:
        generated_lookup[family['slot_allocation_family']].append(family)
    frontier_lookup = None if frontier is None else {'families': [dict(row) for row in frontier['families']]}
    payloads = []
    for slot_family in slot_allocation_families():
        partial_generated = {
            'families': generated_lookup[slot_family.name],
            'best_gate_family': min(
                generated_lookup[slot_family.name],
                key=lambda row: (
                    int(row['reconstruction']['full_oracle_non_clifford']),
                    int(row['reconstruction']['total_logical_qubits']),
                ),
            ),
            'best_qubit_family': min(
                generated_lookup[slot_family.name],
                key=lambda row: (
                    int(row['reconstruction']['total_logical_qubits']),
                    int(row['reconstruction']['full_oracle_non_clifford']),
                ),
            ),
        }
        partial = build_ft_ir_compositions_single(
            schedule=schedule,
            slot_allocation={**slot_family.slot_allocation, 'source_artifact': slot_family.source_artifact},
            arithmetic_lowerings=arithmetic_lowerings,
            lookup_lowerings=central_lookup_lowerings,
            phase_shells=central_phase_shells,
            generated_block_inventories=partial_generated,
            frontier=frontier_lookup,
            field_bits=field_bits,
        )
        payloads.append(partial)
    families = [family for payload in payloads for family in payload['families']]
    best_gate = min(
        families,
        key=lambda row: (
            int(row['reconstruction']['full_oracle_non_clifford']),
            int(row['reconstruction']['total_logical_qubits']),
        ),
    )
    best_qubit = min(
        families,
        key=lambda row: (
            int(row['reconstruction']['total_logical_qubits']),
            int(row['reconstruction']['full_oracle_non_clifford']),
        ),
    )
    return {
        'schema': 'compiler-project-ft-ir-v2',
        'source_artifacts': {
            'full_raw32_oracle': 'compiler_verification_project/artifacts/full_raw32_oracle.json',
            'slot_allocations': [slot_family.source_artifact for slot_family in slot_allocation_families()],
            'arithmetic_lowerings': 'compiler_verification_project/artifacts/arithmetic_lowerings.json',
            'lookup_lowerings': 'compiler_verification_project/artifacts/lookup_lowerings.json',
            'phase_shell_lowerings': 'compiler_verification_project/artifacts/phase_shell_lowerings.json',
            'generated_block_inventories': 'compiler_verification_project/artifacts/generated_block_inventories.json',
            'family_frontier': 'compiler_verification_project/artifacts/family_frontier.json',
        },
        'source_references': payloads[0]['source_references'],
        'schedule_summary': dict(schedule['summary']),
        'families': families,
        'best_gate_family': {
            'name': best_gate['name'],
            'reconstruction': best_gate['reconstruction'],
        },
        'best_qubit_family': {
            'name': best_qubit['name'],
            'reconstruction': best_qubit['reconstruction'],
        },
        'notes': [
            'This artifact expresses each named compiler family as a compositional FT-style call graph with hierarchical bundles and a traversed leaf sigma.',
            'The FT IR spans the exact leaf interfaces checked into the compiler project.',
        ],
    }


def build_whole_oracle_recount_payload(
    ft_ir_compositions: Mapping[str, Any],
    public_google_baseline: Mapping[str, Any],
) -> Dict[str, Any]:
    recount = build_whole_oracle_recount_single(
        ft_ir_compositions=ft_ir_compositions,
        public_google_baseline=public_google_baseline,
    )
    recount['schema'] = 'compiler-project-whole-oracle-recount-v2'
    recount['source_artifacts'] = {
        'ft_ir_compositions': 'compiler_verification_project/artifacts/ft_ir_compositions.json',
        'family_frontier': 'compiler_verification_project/artifacts/family_frontier.json',
    }
    recount['notes'] = [
        'This artifact performs a full exact whole-oracle recount by aggregating the FT IR leaf sigma for each named compiler family.',
        'The recount is independent of the flattened generated block inventory totals and serves as the primary exact total source for the compiler frontier across all exact leaf interfaces.',
    ]
    return recount


# ---------------------------------------------------------------------------
# Whole-oracle frontier and physical transfers
# ---------------------------------------------------------------------------


def compiler_family_frontier() -> Dict[str, Any]:
    schedule = raw32_schedule()
    kernel = arithmetic_kernel_library()
    arithmetic_lowerings = arithmetic_lowering_library(
        field_bits=FIELD_BITS,
        leaf_opcode_histogram=kernel['leaf_opcode_histogram'],
    )
    lookup_lowerings = lookup_lowering_library()
    phase_shell_lowerings = phase_shell_lowering_library(FULL_PHASE_REGISTER_BITS)
    phase_shell_rows = _central_phase_shell_rows(phase_shell_family_summary(phase_shell_lowerings)['families'])
    generated_inventories = build_generated_block_inventories_payload(
        schedule=schedule,
        kernel=kernel,
        arithmetic_lowerings=arithmetic_lowerings,
        lookup_lowerings=lookup_lowerings,
        phase_shells=phase_shell_lowerings['families'],
        field_bits=FIELD_BITS,
        public_google_baseline=PUBLIC_GOOGLE_BASELINE,
    )
    ft_ir = build_ft_ir_compositions_payload(
        schedule=schedule,
        arithmetic_lowerings=arithmetic_lowerings,
        lookup_lowerings=lookup_lowerings,
        phase_shells=phase_shell_lowerings['families'],
        generated_block_inventories=generated_inventories,
        frontier=None,
        field_bits=FIELD_BITS,
    )
    recount = build_whole_oracle_recount_payload(
        ft_ir_compositions=ft_ir,
        public_google_baseline=PUBLIC_GOOGLE_BASELINE,
    )
    families: List[CompilerFamilyResult] = []
    lookup_rows = {row.name: row for row in lookup_families()}
    phase_rows = {row.name: row for row in phase_shell_families()}
    recount_rows = {row['name']: row for row in recount['families']}
    for inventory in generated_inventories['families']:
        lookup = lookup_rows[inventory['lookup_family']]
        phase_shell = phase_rows[inventory['phase_shell']]
        reconstruction = inventory['reconstruction']
        recount_row = recount_rows[inventory['name']]
        total_nc = int(recount_row['full_oracle_non_clifford'])
        total_qubits = int(recount_row['total_logical_qubits'])
        families.append(
            CompilerFamilyResult(
                name=inventory['name'],
                summary=inventory['summary'],
                gate_set=f'{lookup.gate_set}; {phase_shell.gate_set}',
                phase_shell=phase_shell.name,
                slot_allocation_family=inventory['slot_allocation_family'],
                arithmetic_kernel_family=kernel['name'],
                lookup_family=lookup.name,
                arithmetic_leaf_non_clifford=int(reconstruction['arithmetic_leaf_non_clifford']),
                direct_seed_non_clifford=int(reconstruction['direct_seed_non_clifford']),
                per_leaf_lookup_non_clifford=int(reconstruction['per_leaf_lookup_non_clifford']),
                full_oracle_non_clifford=total_nc,
                arithmetic_slot_count=int(reconstruction['arithmetic_slot_count']),
                control_slot_count=int(reconstruction['control_slot_count']),
                borrowed_interface_qubits=int(reconstruction.get('borrowed_interface_qubits', 0)),
                lookup_workspace_qubits=int(reconstruction['lookup_workspace_qubits']),
                live_phase_bits=int(reconstruction['live_phase_bits']),
                total_logical_qubits=total_qubits,
                phase_shell_hadamards=int(recount_row['phase_shell_hadamards']),
                phase_shell_measurements=int(recount_row['phase_shell_measurements']),
                phase_shell_rotations=int(recount_row['phase_shell_rotations']),
                phase_shell_rotation_depth=int(recount_row['phase_shell_rotation_depth']),
                total_measurements=int(recount_row['total_measurements']),
                improvement_vs_google_low_qubit=recount_row['improvement_vs_google_low_qubit'],
                improvement_vs_google_low_gate=recount_row['improvement_vs_google_low_gate'],
                qubit_ratio_vs_google_low_qubit=recount_row['qubit_ratio_vs_google_low_qubit'],
                qubit_ratio_vs_google_low_gate=recount_row['qubit_ratio_vs_google_low_gate'],
                notes=[*lookup.notes, *phase_shell.notes],
            )
        )
    best_gate = min(families, key=lambda row: (row.full_oracle_non_clifford, row.total_logical_qubits))
    best_qubit = min(families, key=lambda row: (row.total_logical_qubits, row.full_oracle_non_clifford))
    best_sub30m_qubit = min(
        (row for row in families if row.full_oracle_non_clifford < 30_000_000),
        key=lambda row: (row.total_logical_qubits, row.full_oracle_non_clifford),
    )
    return {
        'schema': 'compiler-project-frontier-v10',
        'public_google_baseline': PUBLIC_GOOGLE_BASELINE,
        'schedule': schedule,
        'slot_allocation': exact_leaf_slot_allocation(),
        'slot_allocation_families': [
            {
                'name': slot_family.name,
                'summary': slot_family.summary,
                'source_artifact': slot_family.source_artifact,
                'leaf_source_artifact': slot_family.leaf_source_artifact,
                'slot_allocation': slot_family.slot_allocation,
                'notes': slot_family.notes,
            }
            for slot_family in slot_allocation_families()
        ],
        'arithmetic_kernel_family': arithmetic_kernel_library(),
        'arithmetic_lowering_artifact': 'compiler_verification_project/artifacts/arithmetic_lowerings.json',
        'lookup_lowering_artifact': 'compiler_verification_project/artifacts/lookup_lowerings.json',
        'phase_shell_lowering_artifact': 'compiler_verification_project/artifacts/phase_shell_lowerings.json',
        'generated_block_inventory_artifact': 'compiler_verification_project/artifacts/generated_block_inventories.json',
        'whole_oracle_recount_artifact': 'compiler_verification_project/artifacts/whole_oracle_recount.json',
        'lookup_families': [asdict(row) for row in lookup_families()],
        'phase_shell_families': phase_shell_rows,
        'families': [asdict(row) for row in families],
        'best_gate_family': asdict(best_gate),
        'best_qubit_family': asdict(best_qubit),
        'best_sub30m_qubit_family': asdict(best_sub30m_qubit),
        'notes': [
            'These are exact whole-oracle counts for named compiler families over an explicit arithmetic-lowering family, an explicit lookup-lowering family, two explicit leaf-interface families, a generated block-inventory layer, and a fully quantum raw-32 schedule.',
            'The qubit frontier uses exact slot allocation and an explicit phase-shell lowering layer rather than a fixed 512-bit phase-register policy plus shell-level placeholder counters.',
            'The arithmetic kernels, lookup families, and phase-shell families are bound to explicit internal subcircuit-equivalence or lowering witnesses at the checked ISA and generated-inventory layers; the remaining open gap is external equivalence checking below the named blocks.',
            'The compiler frontier totals are sourced from the independent whole-oracle recount over the FT IR leaf sigma rather than directly from the generated block inventory.',
        ],
    }


# ---------------------------------------------------------------------------
# Qubit breakthrough analysis
# ---------------------------------------------------------------------------


def build_qubit_breakthrough_analysis(
    frontier: Optional[Mapping[str, Any]] = None,
    slot_allocation: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    effective_frontier = dict(frontier) if frontier is not None else compiler_family_frontier()
    best_qubit = dict(effective_frontier['best_qubit_family'])
    if slot_allocation is not None:
        effective_slot_allocation = dict(slot_allocation)
    else:
        slot_family_name = str(best_qubit['slot_allocation_family'])
        effective_slot_allocation = next(
            dict(row['slot_allocation'])
            for row in effective_frontier['slot_allocation_families']
            if row['name'] == slot_family_name
        )
    arithmetic_slot_count = int(best_qubit['arithmetic_slot_count'])
    control_slot_count = int(best_qubit['control_slot_count'])
    lookup_workspace_qubits = int(best_qubit['lookup_workspace_qubits'])
    borrowed_interface_qubits = int(best_qubit.get('borrowed_interface_qubits', 0))
    live_phase_bits = int(best_qubit['live_phase_bits'])
    arithmetic_register_file_qubits = arithmetic_slot_count * FIELD_BITS
    fixed_non_arithmetic_overhead_qubits = (
        control_slot_count + borrowed_interface_qubits + lookup_workspace_qubits + live_phase_bits
    )
    total_logical_qubits = int(best_qubit['total_logical_qubits'])
    public_google_baseline = dict(effective_frontier['public_google_baseline'])

    slot_sweep = []
    for slots in range(arithmetic_slot_count, 3, -1):
        derived_total = slots * FIELD_BITS + fixed_non_arithmetic_overhead_qubits
        slot_sweep.append({
            'arithmetic_slot_count': slots,
            'derived_total_logical_qubits': derived_total,
            'qubit_reduction_vs_current': total_logical_qubits - derived_total,
            'qubit_reduction_fraction_vs_current': (total_logical_qubits - derived_total) / total_logical_qubits,
            'beats_google_low_qubit': derived_total <= int(public_google_baseline['low_qubit']['logical_qubits']),
            'beats_google_low_gate': derived_total <= int(public_google_baseline['low_gate']['logical_qubits']),
        })

    target_widths = {
        FIELD_BITS,
        192,
        160,
        157,
        144,
        129,
        128,
        112,
        96,
        80,
        72,
    }
    field_width_sweep = []
    for field_slot_width in sorted(target_widths, reverse=True):
        derived_total = arithmetic_slot_count * field_slot_width + fixed_non_arithmetic_overhead_qubits
        field_width_sweep.append({
            'field_slot_logical_qubits': field_slot_width,
            'derived_total_logical_qubits': derived_total,
            'qubit_reduction_vs_current': total_logical_qubits - derived_total,
            'qubit_reduction_fraction_vs_current': (total_logical_qubits - derived_total) / total_logical_qubits,
            'beats_google_low_qubit': derived_total <= int(public_google_baseline['low_qubit']['logical_qubits']),
            'beats_google_low_gate': derived_total <= int(public_google_baseline['low_gate']['logical_qubits']),
        })

    baseline_thresholds = {}
    for baseline_name, baseline in public_google_baseline.items():
        target_qubits = int(baseline['logical_qubits'])
        baseline_thresholds[baseline_name] = {
            'baseline_logical_qubits': target_qubits,
            'max_arithmetic_slots_at_current_field_width': (target_qubits - fixed_non_arithmetic_overhead_qubits) // FIELD_BITS,
            'max_field_slot_logical_qubits_at_current_exact_slot_count': (target_qubits - fixed_non_arithmetic_overhead_qubits) // arithmetic_slot_count,
        }

    projection = load_json(PROJECT_ROOT / 'artifacts' / 'projections' / 'resource_projection.json')
    default_projection = projection['optimized_ecdlp_projection']
    default_model = projection['default_model_details']
    alternative_projection = next(
        row
        for row in projection['alternative_backend_scenarios']
        if row['model_name'] == 'addsub_modmul_liveness_v2'
    )
    modeled_reference_points = {
        projection['model_name']: {
            'model_name': projection['model_name'],
            'slot_accounting_mode': default_model['logical_qubit_model']['slot_accounting_mode'],
            'field_slot_logical_qubits': int(default_model['logical_qubit_model']['field_slot_logical_qubits']),
            'logical_qubits_total': int(default_projection['logical_qubits_total']),
            'scratch_logical_qubits': int(projection['optimized_leaf_projection']['scratch_logical_qubits']),
        },
        alternative_projection['model_name']: {
            'model_name': alternative_projection['model_name'],
            'slot_accounting_mode': alternative_projection['logical_qubit_model']['slot_accounting_mode'],
            'field_slot_logical_qubits': int(alternative_projection['logical_qubit_model']['field_slot_logical_qubits']),
            'logical_qubits_total': int(alternative_projection['ecdlp']['logical_qubits_total']),
            'scratch_logical_qubits': int(alternative_projection['leaf']['scratch_logical_qubits']),
        },
    }

    lookup_tradeoffs = []
    for row in sorted(
        (
            family
            for family in effective_frontier['families']
            if family['phase_shell'] == best_qubit['phase_shell']
        ),
        key=lambda family: (int(family['total_logical_qubits']), int(family['full_oracle_non_clifford'])),
    ):
        lookup_tradeoffs.append({
            'name': row['name'],
            'lookup_family': row['lookup_family'],
            'lookup_workspace_qubits': int(row['lookup_workspace_qubits']),
            'total_logical_qubits': int(row['total_logical_qubits']),
            'full_oracle_non_clifford': int(row['full_oracle_non_clifford']),
            'delta_qubits_vs_best_qubit': int(row['total_logical_qubits']) - total_logical_qubits,
            'delta_non_clifford_vs_best_qubit': int(row['full_oracle_non_clifford']) - int(best_qubit['full_oracle_non_clifford']),
        })

    peak_pc = int(effective_slot_allocation['peak_arithmetic_slots']['pc'])
    leaf_instructions = central_executable_leaf()['instructions']
    peak_versions = [
        entry
        for entry in effective_slot_allocation['versions']
        if entry['reg_type'] == 'arithmetic' and int(entry['def_pc']) <= peak_pc <= int(entry['last_use_pc'])
    ]
    peak_instruction_window = [
        {
            'pc': int(instruction['pc']),
            'op': instruction['op'],
            'dst': instruction.get('dst'),
            'src': instruction.get('src'),
            'flag': instruction.get('flag'),
            'comment': instruction.get('comment'),
        }
        for instruction in leaf_instructions
        if peak_pc - 3 <= int(instruction['pc']) <= peak_pc + 3
    ]

    return {
        'schema': 'compiler-project-qubit-breakthrough-analysis-v1',
        'public_google_baseline': public_google_baseline,
        'best_exact_qubit_family': best_qubit,
        'exact_component_breakdown': {
            'arithmetic_register_file_qubits': arithmetic_register_file_qubits,
            'lookup_workspace_qubits': lookup_workspace_qubits,
            'control_slot_qubits': control_slot_count,
            'live_phase_qubits': live_phase_bits,
            'fixed_non_arithmetic_overhead_qubits': fixed_non_arithmetic_overhead_qubits,
            'arithmetic_register_file_share_fraction': arithmetic_register_file_qubits / total_logical_qubits,
            'fixed_non_arithmetic_overhead_share_fraction': fixed_non_arithmetic_overhead_qubits / total_logical_qubits,
        },
        'baseline_thresholds': baseline_thresholds,
        'counterfactual_slot_sweep': slot_sweep,
        'counterfactual_field_width_sweep': field_width_sweep,
        'modeled_reference_points': modeled_reference_points,
        'semiclassical_lookup_tradeoffs': lookup_tradeoffs,
        'peak_live_hotspot': {
            'peak_pc': peak_pc,
            'peak_opcode': effective_slot_allocation['peak_arithmetic_slots']['opcode'],
            'peak_arithmetic_slot_count': int(effective_slot_allocation['peak_arithmetic_slots']['count']),
            'active_arithmetic_versions': sorted(peak_versions, key=lambda row: (int(row['assigned_slot']), int(row['def_pc']))),
            'instruction_window': peak_instruction_window,
        },
        'notes': [
            'This artifact isolates the dominant qubit bottleneck inside the exact compiler frontier and quantifies the break-even thresholds against the cited Google qubit lines.',
            'The slot sweep and field-width sweep are counterfactual threshold budgets around the current exact best-qubit family, not new exact compiler-family claims.',
            'Modeled reference points are copied from the quarantined backend projection layer and kept separate from the exact frontier.',
        ],
    }


# ---------------------------------------------------------------------------
# Additional exact structural artifacts
# ---------------------------------------------------------------------------


def table_manifests() -> Dict[str, Any]:
    canon = canonical_public_point()
    h_point = (int(canon['point']['x_hex'], 16), int(canon['point']['y_hex'], 16))
    g_bases = window_bases(SECP_G)
    h_bases = window_bases(h_point)
    phase_a = []
    phase_b = []
    for idx, base in enumerate(g_bases):
        phase_a.append({
            'phase_register': 'phase_a',
            'window_index_within_register': idx,
            'base_x_hex': format(base[0], '064x') if base is not None else None,
            'base_y_hex': format(base[1], '064x') if base is not None else None,
            'folded_positive_entries': FOLDED_MAG_DOMAIN,
            'special_min_entry': '[-2^15]U',
            'record_coordinate_bits': 2 * FIELD_BITS,
        })
    for idx, base in enumerate(h_bases):
        phase_b.append({
            'phase_register': 'phase_b',
            'window_index_within_register': idx,
            'base_x_hex': format(base[0], '064x') if base is not None else None,
            'base_y_hex': format(base[1], '064x') if base is not None else None,
            'folded_positive_entries': FOLDED_MAG_DOMAIN,
            'special_min_entry': '[-2^15]U',
            'record_coordinate_bits': 2 * FIELD_BITS,
        })
    return {
        'schema': 'compiler-project-table-manifests-v1',
        'canonical_public_point': canon,
        'folded_contract': {
            'word_bits': RAW_WINDOW_BITS,
            'magnitude_bits': FOLDED_MAG_BITS,
            'positive_domain_size': FOLDED_MAG_DOMAIN,
            'coordinate_bits_per_record': 2 * FIELD_BITS,
        },
        'phase_a_bases': phase_a,
        'phase_b_bases': phase_b,
        'notes': [
            'This artifact materializes the exact window bases and table dimensions used by the compiler project.',
            'The classical table data vary with the canonical public point only on the phase_b side; the compiler-family non-Clifford counts themselves are public-point independent.',
        ],
    }



def full_attack_inventory() -> Dict[str, Any]:
    frontier = compiler_family_frontier()
    schedule = raw32_schedule()
    kernel = arithmetic_kernel_library()
    hist = kernel['leaf_opcode_histogram']
    leaf_calls = schedule['summary']['leaf_call_count_total']
    arithmetic_lowerings = arithmetic_lowering_library(
        field_bits=FIELD_BITS,
        leaf_opcode_histogram=kernel['leaf_opcode_histogram'],
    )
    phase_shell_lowerings = phase_shell_lowering_library(FULL_PHASE_REGISTER_BITS)
    generated_block_inventories = build_generated_block_inventories_payload(
        schedule=schedule,
        kernel=kernel,
        arithmetic_lowerings=arithmetic_lowerings,
        lookup_lowerings=lookup_lowering_library(),
        phase_shells=phase_shell_lowerings['families'],
        field_bits=FIELD_BITS,
        public_google_baseline=PUBLIC_GOOGLE_BASELINE,
    )
    return {
        'schema': 'compiler-project-full-attack-inventory-v6',
        'schedule': schedule,
        'inventory': {
            'direct_seed_count': 1,
            'phase_a_leaf_calls': schedule['summary']['phase_a_leaf_calls'],
            'phase_b_leaf_calls': schedule['summary']['phase_b_leaf_calls'],
            'total_leaf_calls': leaf_calls,
            'classical_tail_elisions_removed': schedule['summary']['classical_tail_elisions_removed'],
            'whole_oracle_field_mul_count': leaf_calls * hist.get('field_mul', 0),
            'whole_oracle_field_add_count': leaf_calls * hist.get('field_add', 0),
            'whole_oracle_field_sub_count': leaf_calls * hist.get('field_sub', 0),
            'whole_oracle_field_sub_sum_count': leaf_calls * hist.get('field_sub_sum', 0),
            'whole_oracle_field_triple_count': leaf_calls * hist.get('field_triple', 0),
            'whole_oracle_field_mul_lookup_x_count': leaf_calls * hist.get('field_mul_lookup_x', 0),
            'whole_oracle_field_mul_lookup_y_count': leaf_calls * hist.get('field_mul_lookup_y', 0),
            'whole_oracle_field_mul_lookup_sum_count': leaf_calls * hist.get('field_mul_lookup_sum', 0),
            'whole_oracle_complete_a0_streamed_tail_count': leaf_calls * hist.get('complete_a0_streamed_tail', 0),
            'whole_oracle_mul_const_count': leaf_calls * hist.get('mul_const', 0),
            'whole_oracle_select_count': leaf_calls * hist.get('select_field_if_flag', 0),
            'whole_oracle_lookup_count': schedule['summary']['lookup_invocations_total'],
        },
        'generated_block_inventory_artifact': 'compiler_verification_project/artifacts/generated_block_inventories.json',
        'whole_oracle_recount_artifact': 'compiler_verification_project/artifacts/whole_oracle_recount.json',
        'arithmetic_lowering_artifact': 'compiler_verification_project/artifacts/arithmetic_lowerings.json',
        'phase_shell_lowering_artifact': 'compiler_verification_project/artifacts/phase_shell_lowerings.json',
        'generated_block_inventory_summary': {
            'best_gate_family': generated_block_inventories['best_gate_family'],
            'best_qubit_family': generated_block_inventories['best_qubit_family'],
            'family_reconstructed_totals': [
                {
                    'name': row['name'],
                    'full_oracle_non_clifford': row['reconstruction']['full_oracle_non_clifford'],
                    'total_logical_qubits': row['reconstruction']['total_logical_qubits'],
                }
                for row in generated_block_inventories['families']
            ],
        },
        'whole_oracle_recount_summary': {
            'best_gate_family': frontier['best_gate_family'],
            'best_qubit_family': frontier['best_qubit_family'],
            'family_recount_totals': [
                {
                    'name': row['name'],
                    'full_oracle_non_clifford': row['full_oracle_non_clifford'],
                    'total_logical_qubits': row['total_logical_qubits'],
                }
                for row in frontier['families']
            ],
        },
        'best_gate_family': frontier['best_gate_family'],
        'best_qubit_family': frontier['best_qubit_family'],
    }



def build_azure_logical_counts_payload(frontier: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if frontier is None:
        frontier = compiler_family_frontier()
    out = []
    for family in frontier['families']:
        phase_shell_row = next(
            row
            for row in frontier['phase_shell_families']
            if row['name'] == family['phase_shell']
        )
        out.append({
            'family': family['name'],
            'logicalCounts': {
                'numQubits': family['total_logical_qubits'],
                'tCount': 0,
                'cczCount': family['full_oracle_non_clifford'],
                'ccixCount': 0,
                'rotationCount': phase_shell_row['total_rotations'],
                'rotationDepth': phase_shell_row['rotation_depth'],
                'measurementCount': family['total_measurements'],
            },
            'notes': 'Azure-style logicalCounts seed. The oracle CCZ total, phase-shell rotation inventory, and total measurement inventory are all sourced from exact compiler-family artifacts.',
        })
    payload = {
        'schema': 'compiler-project-azure-logical-counts-v2',
        'families': out,
        'notes': [
            'This file is not a claimed Azure output. It is a machine-readable logicalCounts seed suitable for exact-family handoff into a physical estimator.',
            'The rotationCount and rotationDepth fields are sourced from the exact phase-shell lowering artifact for each named compiler family.',
        ],
    }
    return payload


def _physical_estimator_runtime_available() -> bool:
    try:
        import_module('qsharp.estimator')
    except ModuleNotFoundError:
        return False
    return True


def _recorded_physical_estimator_family_names() -> List[str]:
    path = project_artifact_path('azure_resource_estimator_results.json')
    if not path.exists():
        return []
    payload = load_json(path)
    return [str(row['family']) for row in payload.get('families', [])]


def _filter_azure_logical_counts_payload(payload: Dict[str, Any], family_names: Sequence[str]) -> Dict[str, Any]:
    family_name_set = set(family_names)
    filtered_rows = [row for row in payload['families'] if row['family'] in family_name_set]
    filtered_payload = {
        **payload,
        'families': filtered_rows,
        'notes': [
            *payload['notes'],
            'When qsharp/qdk is unavailable, this artifact is filtered to the subset of families that have checked recorded estimator outputs in the repository.',
        ],
    }
    return filtered_payload


def write_azure_logical_counts() -> Dict[str, Any]:
    frontier = load_json(project_artifact_path('family_frontier.json')) if project_artifact_path('family_frontier.json').exists() else compiler_family_frontier()
    payload = build_azure_logical_counts_payload(frontier=frontier)
    if not _physical_estimator_runtime_available():
        recorded_family_names = _recorded_physical_estimator_family_names()
        if recorded_family_names:
            payload = _filter_azure_logical_counts_payload(payload, recorded_family_names)
    dump_json(project_artifact_path('azure_resource_estimator_logical_counts.json'), payload)
    return payload


def write_azure_estimator_targets(logical_counts_payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    logical_counts = logical_counts_payload or (
        load_json(project_artifact_path('azure_resource_estimator_logical_counts.json'))
        if project_artifact_path('azure_resource_estimator_logical_counts.json').exists()
        else write_azure_logical_counts()
    )
    payload = build_azure_estimator_target_payload(logical_counts)
    dump_json(project_artifact_path('azure_resource_estimator_targets.json'), payload)
    return payload


def write_azure_estimator_results(
    logical_counts_payload: Optional[Dict[str, Any]] = None,
    target_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    logical_counts = logical_counts_payload or (
        load_json(project_artifact_path('azure_resource_estimator_logical_counts.json'))
        if project_artifact_path('azure_resource_estimator_logical_counts.json').exists()
        else write_azure_logical_counts()
    )
    targets = target_payload or (
        load_json(project_artifact_path('azure_resource_estimator_targets.json'))
        if project_artifact_path('azure_resource_estimator_targets.json').exists()
        else write_azure_estimator_targets(logical_counts_payload=logical_counts)
    )
    payload = build_or_load_azure_estimator_results_payload(
        logical_counts_payload=logical_counts,
        target_payload=targets,
        artifact_path=project_artifact_path('azure_resource_estimator_results.json'),
    )
    dump_json(project_artifact_path('azure_resource_estimator_results.json'), payload)
    return payload


# ---------------------------------------------------------------------------
# Exact raw-32 semantic verification
# ---------------------------------------------------------------------------


def window_digit_u16(value: int, idx: int) -> int:
    return (value >> (16 * idx)) & 0xFFFF



def _lookup_from_precomputed(tables: List[List[Any]], idx: int, digit: int) -> PointAffine:
    if digit == 0:
        return None
    return mul_fixed_window(digit, tables[idx], SECP_P, SECP_B, width=8, order=SECP_N)


def structured_raw32_cases() -> List[Dict[str, Any]]:
    cases = [
        {'case_id': 'zero_zero', 'kind': 'structured', 'a_scalar': 0, 'b_scalar': 0},
        {'case_id': 'seed_only_unit', 'kind': 'structured', 'a_scalar': 1, 'b_scalar': 0},
        {'case_id': 'seed_zero_phase_b_unit', 'kind': 'structured', 'a_scalar': 0, 'b_scalar': 1},
        {'case_id': 'phase_a_second_window', 'kind': 'structured', 'a_scalar': 1 << 16, 'b_scalar': 0},
        {'case_id': 'phase_b_second_window', 'kind': 'structured', 'a_scalar': 0, 'b_scalar': 1 << 16},
        {'case_id': 'phase_a_high_window', 'kind': 'structured', 'a_scalar': 1 << (16 * 15), 'b_scalar': 0},
        {'case_id': 'phase_b_high_window', 'kind': 'structured', 'a_scalar': 0, 'b_scalar': 1 << (16 * 15)},
        {'case_id': 'phase_a_low_full_word', 'kind': 'structured', 'a_scalar': 0xFFFF, 'b_scalar': 0},
        {'case_id': 'phase_b_low_full_word', 'kind': 'structured', 'a_scalar': 0, 'b_scalar': 0xFFFF},
        {'case_id': 'mixed_sparse_windows', 'kind': 'structured', 'a_scalar': (1 << (16 * 15)) + (1 << 16) + 1, 'b_scalar': (1 << (16 * 14)) + (1 << 32) + 1},
        {'case_id': 'phase_a_half_order', 'kind': 'structured', 'a_scalar': SECP_N >> 1, 'b_scalar': 0},
        {'case_id': 'phase_b_half_order', 'kind': 'structured', 'a_scalar': 0, 'b_scalar': SECP_N >> 1},
        {'case_id': 'phase_a_order_minus_one', 'kind': 'structured', 'a_scalar': SECP_N - 1, 'b_scalar': 0},
        {'case_id': 'phase_b_order_minus_one', 'kind': 'structured', 'a_scalar': 0, 'b_scalar': SECP_N - 1},
    ]
    for case in cases:
        assert 0 <= case['a_scalar'] < SECP_N
        assert 0 <= case['b_scalar'] < SECP_N
    return cases


def raw32_semantic_cases(case_count: int) -> List[Dict[str, Any]]:
    secp_path = artifact_circuits_path(PROJECT_ROOT / 'artifacts', 'optimized_pointadd_secp256k1.json')
    seed = bytes.fromhex(sha256_path(secp_path))
    stream = deterministic_scalars(seed + b'compiler_project_raw32', case_count * 2, SECP_N)
    cases = structured_raw32_cases()
    for index in range(case_count):
        cases.append({
            'case_id': f'random_{index:04d}',
            'kind': 'random',
            'a_scalar': stream[2 * index],
            'b_scalar': stream[2 * index + 1],
        })
    return cases



def run_full_raw32_semantic_check(case_count: int = 16) -> Dict[str, Any]:
    leaf = _leaf()
    schedule = raw32_schedule()
    canon = canonical_public_point()
    h_point = (int(canon['point']['x_hex'], 16), int(canon['point']['y_hex'], 16))

    g_tables = precompute_window_tables(SECP_G, SECP_P, SECP_B, width=8, bits=256)
    h_tables = precompute_window_tables(h_point, SECP_P, SECP_B, width=8, bits=256)
    g_window_tables = [precompute_window_tables(base, SECP_P, SECP_B, width=8, bits=256) for base in window_bases(SECP_G)]
    h_window_tables = [precompute_window_tables(base, SECP_P, SECP_B, width=8, bits=256) for base in window_bases(h_point)]

    out_csv = project_artifact_path(f'raw32_semantic_audit_{case_count}.csv')
    summary = {
        'total': 0,
        'pass': 0,
        'structured_cases': 0,
        'random_cases': 0,
        'seed_zero_cases': 0,
        'phase_b_zero_cases': 0,
        'phase_b_nonzero_cases': 0,
    }
    cases = raw32_semantic_cases(case_count)
    with out_csv.open('w', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow([
            'case_id', 'case_kind', 'a_scalar_hex', 'b_scalar_hex',
            'seed_x', 'seed_y', 'expected_x', 'expected_y', 'actual_x', 'actual_y', 'status'
        ])
        for case in cases:
            a_scalar = case['a_scalar']
            b_scalar = case['b_scalar']
            summary[f"{case['kind']}_cases"] += 1

            seed_digit = window_digit_u16(a_scalar, 0)
            seed_point = _lookup_from_precomputed(g_window_tables, 0, seed_digit)
            summary['seed_zero_cases'] += int(seed_digit == 0)
            acc = seed_point

            for entry in schedule['leaf_calls']:
                idx = entry['window_index_within_register']
                if entry['phase_register'] == 'phase_a':
                    digit = window_digit_u16(a_scalar, idx)
                    lookup = _lookup_from_precomputed(g_window_tables, idx, digit)
                else:
                    digit = window_digit_u16(b_scalar, idx)
                    lookup = _lookup_from_precomputed(h_window_tables, idx, digit)
                acc_proj = affine_to_proj(acc, SECP_P)
                got_proj = execute_leaf_contract(leaf, SECP_P, acc_proj, lookup, 0 if lookup is None else 1)
                acc = proj_to_affine(got_proj, SECP_P)

            if any(window_digit_u16(b_scalar, idx) != 0 for idx in range(16)):
                summary['phase_b_nonzero_cases'] += 1
            else:
                summary['phase_b_zero_cases'] += 1

            expected = add_affine(
                mul_fixed_window(a_scalar, g_tables, SECP_P, SECP_B, width=8, order=SECP_N),
                mul_fixed_window(b_scalar, h_tables, SECP_P, SECP_B, width=8, order=SECP_N),
                SECP_P,
                SECP_B,
            )
            ok = acc == expected
            summary['total'] += 1
            summary['pass'] += int(ok)
            writer.writerow([case['case_id'], case['kind'], format(a_scalar, '064x'), format(b_scalar, '064x'), *hex_or_inf(seed_point), *hex_or_inf(expected), *hex_or_inf(acc), 'PASS' if ok else 'FAIL'])

    return {
        'schema': 'compiler-project-raw32-semantic-check-v2',
        'canonical_public_point': canon,
        'csv': out_csv.name,
        'sha256': sha256_path(out_csv),
        'summary': summary,
        'notes': [
            'This check executes the exact same ISA leaf 31 times over a fully quantum raw-32 schedule: 1 direct seed, 15 phase_a leaf calls, and 16 phase_b leaf calls.',
            'It intentionally removes the mainline retained schedule\'s three classical tail elisions.',
        ],
    }


# ---------------------------------------------------------------------------
# Build / verification summaries / physical transfer
# ---------------------------------------------------------------------------


def build_all_artifacts() -> Dict[str, Any]:
    arithmetic_lowerings = arithmetic_lowering_library(
        field_bits=FIELD_BITS,
        leaf_opcode_histogram=leaf_opcode_histogram(),
    )
    phase_shell_lowerings = phase_shell_lowering_library(FULL_PHASE_REGISTER_BITS)
    phase_shell_rows = phase_shell_family_summary(phase_shell_lowerings)
    lookup_lowerings = lookup_lowering_library()
    generated_block_inventories = build_generated_block_inventories_payload(
        schedule=raw32_schedule(),
        kernel=arithmetic_kernel_library(),
        arithmetic_lowerings=arithmetic_lowerings,
        lookup_lowerings=lookup_lowerings,
        phase_shells=phase_shell_lowerings['families'],
        field_bits=FIELD_BITS,
        public_google_baseline=PUBLIC_GOOGLE_BASELINE,
    )
    ft_ir_compositions = build_ft_ir_compositions_payload(
        schedule=raw32_schedule(),
        arithmetic_lowerings=arithmetic_lowerings,
        lookup_lowerings=lookup_lowerings,
        phase_shells=phase_shell_lowerings['families'],
        generated_block_inventories=generated_block_inventories,
        frontier=None,
        field_bits=FIELD_BITS,
    )
    whole_oracle_recount = build_whole_oracle_recount_payload(
        ft_ir_compositions=ft_ir_compositions,
        public_google_baseline=PUBLIC_GOOGLE_BASELINE,
    )
    out = {
        'canonical_public_point': canonical_public_point(),
        'raw32_schedule': raw32_schedule(),
        'slot_allocation': exact_leaf_slot_allocation(),
        'lookup_fed_leaf': build_lookup_fed_leaf(),
        'lookup_fed_leaf_equivalence': build_lookup_fed_leaf_equivalence(),
        'lookup_fed_slot_allocation': lookup_fed_leaf_slot_allocation(),
        'streamed_lookup_tail_leaf': build_streamed_lookup_tail_leaf(),
        'streamed_lookup_tail_leaf_equivalence': build_streamed_lookup_tail_leaf_equivalence(),
        'streamed_lookup_tail_slot_allocation': streamed_lookup_tail_leaf_slot_allocation(),
        'arithmetic_lowerings': arithmetic_lowerings,
        'streamed_lookup_table_multiplier_resource': streamed_lookup_table_multiplier_resource(
            arithmetic_lowerings=arithmetic_lowerings,
            lookup_lowerings=lookup_lowerings,
        ),
        'arithmetic_kernel_library': arithmetic_kernel_library(),
        'primitive_multiplier_library': primitive_multiplier_library(),
        'phase_shell_lowerings': phase_shell_lowerings,
        'phase_shell_families': phase_shell_rows,
        'table_manifests': table_manifests(),
        'lookup_lowerings': lookup_lowerings,
        'generated_block_inventories': generated_block_inventories,
        'ft_ir_compositions': ft_ir_compositions,
        'whole_oracle_recount': whole_oracle_recount,
    }
    out['frontier'] = compiler_family_frontier()
    out['standard_qrom_lookup_assessment'] = standard_qrom_lookup_assessment(
        frontier=out['frontier'],
        lookup_lowerings=out['lookup_lowerings'],
        streamed_resource=out['streamed_lookup_table_multiplier_resource'],
    )
    out['qubit_breakthrough_analysis'] = build_qubit_breakthrough_analysis(frontier=out['frontier'])
    out['full_attack_inventory'] = full_attack_inventory()
    out['subcircuit_equivalence'] = build_subcircuit_equivalence_artifact(
        arithmetic_lowerings=out['arithmetic_lowerings'],
        lookup_lowerings=out['lookup_lowerings'],
        generated_block_inventories=out['generated_block_inventories'],
        frontier=out['frontier'],
        full_attack_inventory=out['full_attack_inventory'],
    )
    dump_json(project_artifact_path('canonical_public_point.json'), out['canonical_public_point'])
    dump_json(project_artifact_path('full_raw32_oracle.json'), out['raw32_schedule'])
    dump_json(project_artifact_path('exact_leaf_slot_allocation.json'), out['slot_allocation'])
    dump_json(project_artifact_path('lookup_fed_leaf.json'), out['lookup_fed_leaf'])
    dump_json(project_artifact_path('lookup_fed_leaf_equivalence.json'), out['lookup_fed_leaf_equivalence'])
    dump_json(project_artifact_path('lookup_fed_leaf_slot_allocation.json'), out['lookup_fed_slot_allocation'])
    dump_json(project_artifact_path('streamed_lookup_tail_leaf.json'), out['streamed_lookup_tail_leaf'])
    dump_json(project_artifact_path('streamed_lookup_tail_leaf_equivalence.json'), out['streamed_lookup_tail_leaf_equivalence'])
    dump_json(project_artifact_path('streamed_lookup_tail_leaf_slot_allocation.json'), out['streamed_lookup_tail_slot_allocation'])
    dump_json(project_artifact_path('arithmetic_lowerings.json'), out['arithmetic_lowerings'])
    dump_json(project_artifact_path('streamed_lookup_table_multiplier_resource.json'), out['streamed_lookup_table_multiplier_resource'])
    dump_json(project_artifact_path('module_library.json'), out['arithmetic_kernel_library'])
    dump_json(project_artifact_path('primitive_multiplier_library.json'), out['primitive_multiplier_library'])
    dump_json(project_artifact_path('phase_shell_lowerings.json'), out['phase_shell_lowerings'])
    dump_json(project_artifact_path('phase_shell_families.json'), out['phase_shell_families'])
    dump_json(project_artifact_path('table_manifests.json'), out['table_manifests'])
    dump_json(project_artifact_path('lookup_lowerings.json'), out['lookup_lowerings'])
    dump_json(project_artifact_path('generated_block_inventories.json'), out['generated_block_inventories'])
    dump_json(project_artifact_path('ft_ir_compositions.json'), out['ft_ir_compositions'])
    dump_json(project_artifact_path('whole_oracle_recount.json'), out['whole_oracle_recount'])
    dump_json(project_artifact_path('family_frontier.json'), out['frontier'])
    dump_json(project_artifact_path('standard_qrom_lookup_assessment.json'), out['standard_qrom_lookup_assessment'])
    dump_json(project_artifact_path('qubit_breakthrough_analysis.json'), out['qubit_breakthrough_analysis'])
    dump_json(project_artifact_path('full_attack_inventory.json'), out['full_attack_inventory'])
    dump_json(project_artifact_path('subcircuit_equivalence.json'), out['subcircuit_equivalence'])
    out['azure_resource_estimator_logical_counts'] = write_azure_logical_counts()
    out['azure_resource_estimator_targets'] = write_azure_estimator_targets(
        logical_counts_payload=out['azure_resource_estimator_logical_counts']
    )
    out['azure_resource_estimator_results'] = write_azure_estimator_results(
        logical_counts_payload=out['azure_resource_estimator_logical_counts'],
        target_payload=out['azure_resource_estimator_targets'],
    )

    build_summary = {
        'schema': 'compiler-project-build-summary-v17',
        'artifacts': {
            'canonical_public_point': 'compiler_verification_project/artifacts/canonical_public_point.json',
            'full_raw32_oracle': 'compiler_verification_project/artifacts/full_raw32_oracle.json',
            'exact_leaf_slot_allocation': 'compiler_verification_project/artifacts/exact_leaf_slot_allocation.json',
            'lookup_fed_leaf': 'compiler_verification_project/artifacts/lookup_fed_leaf.json',
            'lookup_fed_leaf_equivalence': 'compiler_verification_project/artifacts/lookup_fed_leaf_equivalence.json',
            'lookup_fed_leaf_slot_allocation': 'compiler_verification_project/artifacts/lookup_fed_leaf_slot_allocation.json',
            'streamed_lookup_tail_leaf': 'compiler_verification_project/artifacts/streamed_lookup_tail_leaf.json',
            'streamed_lookup_tail_leaf_equivalence': 'compiler_verification_project/artifacts/streamed_lookup_tail_leaf_equivalence.json',
            'streamed_lookup_tail_leaf_slot_allocation': 'compiler_verification_project/artifacts/streamed_lookup_tail_leaf_slot_allocation.json',
            'arithmetic_lowerings': 'compiler_verification_project/artifacts/arithmetic_lowerings.json',
            'streamed_lookup_table_multiplier_resource': 'compiler_verification_project/artifacts/streamed_lookup_table_multiplier_resource.json',
            'module_library': 'compiler_verification_project/artifacts/module_library.json',
            'primitive_multiplier_library': 'compiler_verification_project/artifacts/primitive_multiplier_library.json',
            'phase_shell_lowerings': 'compiler_verification_project/artifacts/phase_shell_lowerings.json',
            'phase_shell_families': 'compiler_verification_project/artifacts/phase_shell_families.json',
            'table_manifests': 'compiler_verification_project/artifacts/table_manifests.json',
            'lookup_lowerings': 'compiler_verification_project/artifacts/lookup_lowerings.json',
            'generated_block_inventories': 'compiler_verification_project/artifacts/generated_block_inventories.json',
            'ft_ir_compositions': 'compiler_verification_project/artifacts/ft_ir_compositions.json',
            'whole_oracle_recount': 'compiler_verification_project/artifacts/whole_oracle_recount.json',
            'family_frontier': 'compiler_verification_project/artifacts/family_frontier.json',
            'standard_qrom_lookup_assessment': 'compiler_verification_project/artifacts/standard_qrom_lookup_assessment.json',
            'qubit_breakthrough_analysis': 'compiler_verification_project/artifacts/qubit_breakthrough_analysis.json',
            'full_attack_inventory': 'compiler_verification_project/artifacts/full_attack_inventory.json',
            'subcircuit_equivalence': 'compiler_verification_project/artifacts/subcircuit_equivalence.json',
            'azure_resource_estimator_logical_counts': 'compiler_verification_project/artifacts/azure_resource_estimator_logical_counts.json',
            'azure_resource_estimator_targets': 'compiler_verification_project/artifacts/azure_resource_estimator_targets.json',
            'azure_resource_estimator_results': 'compiler_verification_project/artifacts/azure_resource_estimator_results.json',
        },
        'headline': {
            'best_gate_family': out['frontier']['best_gate_family'],
            'best_qubit_family': out['frontier']['best_qubit_family'],
            'best_sub30m_qubit_family': out['frontier']['best_sub30m_qubit_family'],
        },
        'notes': [
            'The compiler project closes the classical-tail-elision gap and publishes exact whole-oracle counts for named compiler families with explicit arithmetic, lookup, and phase-shell lowerings, generated block inventories, a compositional FT IR layer, a full whole-oracle recount, internal subcircuit-equivalence witnesses, and exact leaf-interface families.',
            'Its qubit accounting uses exact slot allocation and exact phase-shell lowering instead of a fixed 10-slot/512-phase policy.',
            'The physical-estimator layer binds those exact logical counts to explicit Microsoft Resource Estimator target profiles and recorded estimator outputs.',
        ],
    }
    dump_json(project_artifact_path('build_summary.json'), build_summary)
    return out



def build_cain_transfer_payload(frontier: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if frontier is None:
        frontier = load_json(project_artifact_path('family_frontier.json')) if project_artifact_path('family_frontier.json').exists() else compiler_family_frontier()
    out_rows = []
    for family in frontier['families']:
        nc = int(family['full_oracle_non_clifford'])
        logical = int(family['total_logical_qubits'])
        out_rows.append({
            'family': family['name'],
            'heuristic_time_efficient_days_if_90M_maps_to_10d': (10.0 * nc) / 90_000_000,
            'heuristic_time_efficient_days_if_70M_maps_to_10d': (10.0 * nc) / 70_000_000,
            'same_density_physical_qubits_if_1200_maps_to_26k': (26_000.0 * logical) / 1200.0,
            'same_density_physical_qubits_if_1450_maps_to_26k': (26_000.0 * logical) / 1450.0,
        })
    payload = {
        'schema': 'compiler-project-cain-transfer-v2',
        'families': out_rows,
        'notes': [
            'This is a heuristic transfer, not a compiled hardware estimate.',
            'The qubit-side transfer reflects exact slot allocation and the explicit semiclassical phase-shell family instead of a fixed 512-bit phase register.',
            'Cain et al. target P-256 and a neutral-atom architecture; these transfers are only a structured comparison aid.',
        ],
    }
    return payload


def write_cain_transfer() -> Dict[str, Any]:
    payload = build_cain_transfer_payload()
    dump_json(project_artifact_path('cain_exact_transfer.json'), payload)
    return payload


__all__ = [
    'build_all_artifacts',
    'write_cain_transfer',
    'build_cain_transfer_payload',
    'build_azure_logical_counts_payload',
    'write_azure_estimator_targets',
    'write_azure_estimator_results',
    'build_ft_ir_compositions_payload',
    'build_generated_block_inventories_payload',
    'build_whole_oracle_recount_payload',
    'structured_raw32_cases',
    'compiler_family_frontier',
    'central_executable_leaf',
    'lookup_fed_leaf_slot_allocation',
    'streamed_lookup_tail_leaf_slot_allocation',
    'streamed_lookup_table_multiplier_resource',
    'standard_qrom_lookup_assessment',
    'slot_allocation_families',
    'raw32_schedule',
]
