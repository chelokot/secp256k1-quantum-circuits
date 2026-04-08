#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Sequence, Set, Tuple


FIELD_BITS = 256
WINDOW_BITS = 16
CURRENT_EXACT_BEST_GATE = 22753831
CURRENT_COMPLETE_MULS_PER_LEAF = 11
CANDIDATE_CORE_MULS_PER_LEAF = 9
RETAINED_PHASE_A_WINDOWS = tuple(range(1, 16))
RETAINED_PHASE_B_COUNT = 13
RETAINED_CALLS = len(RETAINED_PHASE_A_WINDOWS) + RETAINED_PHASE_B_COUNT
SELECT_NON_CLIFFORD = FIELD_BITS - 1
ZERO_TEST_COMPUTE_UNCOMPUTE = 4 * FIELD_BITS
FIELD_MUL_NON_CLIFFORD = FIELD_BITS * FIELD_BITS + 2 * FIELD_BITS - 1


@dataclass(frozen=True)
class WindowExceptionProfile:
    window_index: int
    doubling_witness_count: int
    inverse_witness_count: int


@dataclass(frozen=True)
class ShellSelectStage:
    name: str
    field_select_count: int


@dataclass(frozen=True)
class HybridGateProxy:
    base_non_clifford: int
    arithmetic_saving: int
    zero_test_overhead: int
    select_overhead: int
    projected_non_clifford: int


@dataclass(frozen=True)
class CoreProductProfile:
    cached_z_powers: bool
    multiplication_count: int
    squaring_count: int

    @property
    def total_field_products(self) -> int:
        return self.multiplication_count + self.squaring_count


def phase_a_exception_profile(
    order: int,
    retained_windows: Sequence[int] = RETAINED_PHASE_A_WINDOWS,
    window_bits: int = WINDOW_BITS,
) -> List[WindowExceptionProfile]:
    profiles: List[WindowExceptionProfile] = []
    for window_index in retained_windows:
        weight = 1 << (window_bits * window_index)
        doubling_witness_count = 0
        inverse_witness_count = 0
        for digit in range(1, 1 << window_bits):
            residue = (digit * weight) % order
            if residue < weight:
                doubling_witness_count += 1
            lower = order - digit * weight
            if 0 <= lower < weight:
                inverse_witness_count += 1
        profiles.append(
            WindowExceptionProfile(
                window_index=window_index,
                doubling_witness_count=doubling_witness_count,
                inverse_witness_count=inverse_witness_count,
            )
        )
    return profiles


def count_phase_specialized_zero_tests(profiles: Iterable[WindowExceptionProfile], retained_phase_b_count: int = RETAINED_PHASE_B_COUNT) -> int:
    phase_a_zero_tests = 0
    for profile in profiles:
        if profile.doubling_witness_count > 0:
            phase_a_zero_tests += 2
        elif profile.inverse_witness_count > 0:
            phase_a_zero_tests += 1
    phase_b_zero_tests = retained_phase_b_count * 2
    return phase_a_zero_tests + phase_b_zero_tests


def staged_shell_select_schedule() -> List[ShellSelectStage]:
    return [
        ShellSelectStage(name='exceptional_output_from_f0', field_select_count=3),
        ShellSelectStage(name='core_or_exceptional_from_e0', field_select_count=3),
        ShellSelectStage(name='passthrough_p_from_q_inf', field_select_count=3),
        ShellSelectStage(name='passthrough_q_from_p_inf', field_select_count=3),
    ]


def count_staged_shell_selects(stages: Iterable[ShellSelectStage] | None = None) -> int:
    active_stages = list(stages) if stages is not None else staged_shell_select_schedule()
    return sum(stage.field_select_count for stage in active_stages)


def rondepierre_core_product_profile(cached_z_powers: bool) -> CoreProductProfile:
    if cached_z_powers:
        return CoreProductProfile(cached_z_powers=True, multiplication_count=7, squaring_count=2)
    return CoreProductProfile(cached_z_powers=False, multiplication_count=8, squaring_count=3)


def build_prefix_loaded_cached_z_power_skeleton() -> Dict[str, Any]:
    arithmetic_slots = ['qx', 'qy', 'qz', 'qzz', 'qzzz', 'lx', 'ly']
    instructions = [
        {'pc': 0, 'op': 'load_input', 'dst': 'qx', 'src': 'Q.X'},
        {'pc': 1, 'op': 'load_input', 'dst': 'qy', 'src': 'Q.Y'},
        {'pc': 2, 'op': 'load_input', 'dst': 'qz', 'src': 'Q.Z'},
        {'pc': 3, 'op': 'load_input', 'dst': 'qzz', 'src': 'Q.Z2'},
        {'pc': 4, 'op': 'load_input', 'dst': 'qzzz', 'src': 'Q.Z3'},
        {'pc': 5, 'op': 'lookup_affine_x', 'dst': 'lx', 'src': {'table': 'T.x', 'key': 'k'}},
        {'pc': 6, 'op': 'lookup_affine_y', 'dst': 'ly', 'src': {'table': 'T.y', 'key': 'k'}},
        {'pc': 7, 'op': 'field_mul', 'dst': 'qzz', 'src': ['lx', 'qzz']},
        {'pc': 8, 'op': 'field_mul', 'dst': 'ly', 'src': ['ly', 'qzzz']},
        {'pc': 9, 'op': 'field_add', 'dst': 'qz', 'src': ['qy', 'qz']},
        {'pc': 10, 'op': 'field_sub', 'dst': 'qx', 'src': ['qzz', 'qx']},
        {'pc': 11, 'op': 'select_field_if_flag', 'dst': 'qx', 'src': ['qx', 'qx'], 'flag': 'f_out'},
        {'pc': 12, 'op': 'select_field_if_flag', 'dst': 'qy', 'src': ['qy', 'ly'], 'flag': 'f_out'},
        {'pc': 13, 'op': 'select_field_if_flag', 'dst': 'qz', 'src': ['qz', 'qz'], 'flag': 'f_out'},
    ]
    return {
        'schema': 'experimental-leaf-skeleton-v1',
        'arithmetic_slots': arithmetic_slots,
        'instructions': instructions,
    }


def build_delayed_lookup_cached_z_power_skeleton() -> Dict[str, Any]:
    arithmetic_slots = ['qx', 'qy', 'qz', 'qzz', 'qzzz', 'lx', 'tmp']
    instructions = [
        {'pc': 0, 'op': 'load_input', 'dst': 'qx', 'src': 'Q.X'},
        {'pc': 1, 'op': 'load_input', 'dst': 'qy', 'src': 'Q.Y'},
        {'pc': 2, 'op': 'load_input', 'dst': 'qz', 'src': 'Q.Z'},
        {'pc': 3, 'op': 'load_input', 'dst': 'qzz', 'src': 'Q.Z2'},
        {'pc': 4, 'op': 'load_input', 'dst': 'qzzz', 'src': 'Q.Z3'},
        {'pc': 5, 'op': 'lookup_affine_x', 'dst': 'lx', 'src': {'table': 'T.x', 'key': 'k'}},
        {'pc': 6, 'op': 'field_mul', 'dst': 'qzz', 'src': ['lx', 'qzz']},
        {'pc': 7, 'op': 'field_sub', 'dst': 'qx', 'src': ['qzz', 'qx']},
        {'pc': 8, 'op': 'lookup_affine_y', 'dst': 'lx', 'src': {'table': 'T.y', 'key': 'k'}},
        {'pc': 9, 'op': 'field_mul', 'dst': 'tmp', 'src': ['lx', 'qzzz']},
        {'pc': 10, 'op': 'field_add', 'dst': 'qz', 'src': ['qy', 'qz']},
        {'pc': 11, 'op': 'field_sub', 'dst': 'qy', 'src': ['tmp', 'qy']},
        {'pc': 12, 'op': 'select_field_if_flag', 'dst': 'qx', 'src': ['qx', 'qx'], 'flag': 'f_out'},
        {'pc': 13, 'op': 'select_field_if_flag', 'dst': 'qy', 'src': ['qy', 'qy'], 'flag': 'f_out'},
        {'pc': 14, 'op': 'select_field_if_flag', 'dst': 'qz', 'src': ['qz', 'qz'], 'flag': 'f_out'},
    ]
    return {
        'schema': 'experimental-leaf-skeleton-v1',
        'arithmetic_slots': arithmetic_slots,
        'instructions': instructions,
    }


def _tracked_refs(instruction: Dict[str, Any], tracked_names: Set[str]) -> List[str]:
    refs: List[str] = []
    src = instruction.get('src')
    if isinstance(src, list):
        refs.extend(name for name in src if isinstance(name, str) and name in tracked_names)
    elif isinstance(src, str):
        if src in tracked_names:
            refs.append(src)
    return refs


def fixed_order_peak_slots(leaf: Dict[str, Any], output_names: Sequence[str] = ('qx', 'qy', 'qz')) -> int:
    tracked_names = set(leaf['arithmetic_slots'])
    values: List[Tuple[int, Tuple[int, ...]]] = []
    current_versions: Dict[str, int] = {}
    for instruction in leaf['instructions']:
        dst = instruction.get('dst')
        if not isinstance(dst, str) or dst not in tracked_names:
            continue
        src_ids = tuple(current_versions[name] for name in _tracked_refs(instruction, tracked_names))
        value_id = len(values)
        values.append((value_id, src_ids))
        current_versions[dst] = value_id
    future_uses: Dict[int, List[int]] = {value_id: [] for value_id, _ in values}
    for step, (_, src_ids) in enumerate(values):
        for dep in src_ids:
            future_uses[dep].append(step)
    output_versions = {
        current_versions[name]
        for name in output_names
        if name in current_versions
    }
    peak = 0
    for step, (value_id, _) in enumerate(values):
        live_before = {
            candidate_id
            for candidate_id, _ in values[:step]
            if any(use >= step for use in future_uses.get(candidate_id, [])) or candidate_id in output_versions
        }
        peak = max(peak, len(live_before) + 1)
    return peak


def estimate_hybrid_gate_proxy(
    base_non_clifford: int = CURRENT_EXACT_BEST_GATE,
    field_mul_non_clifford: int = FIELD_MUL_NON_CLIFFORD,
    current_muls_per_leaf: int = CURRENT_COMPLETE_MULS_PER_LEAF,
    candidate_muls_per_leaf: int = CANDIDATE_CORE_MULS_PER_LEAF,
    retained_calls: int = RETAINED_CALLS,
    zero_test_count: int = 27,
    zero_test_non_clifford: int = ZERO_TEST_COMPUTE_UNCOMPUTE,
    selects_per_leaf: int = 12,
    select_non_clifford: int = SELECT_NON_CLIFFORD,
) -> HybridGateProxy:
    arithmetic_saving = retained_calls * (current_muls_per_leaf - candidate_muls_per_leaf) * field_mul_non_clifford
    zero_test_overhead = zero_test_count * zero_test_non_clifford
    select_overhead = retained_calls * selects_per_leaf * select_non_clifford
    projected_non_clifford = base_non_clifford - arithmetic_saving + zero_test_overhead + select_overhead
    return HybridGateProxy(
        base_non_clifford=base_non_clifford,
        arithmetic_saving=arithmetic_saving,
        zero_test_overhead=zero_test_overhead,
        select_overhead=select_overhead,
        projected_non_clifford=projected_non_clifford,
    )


__all__ = [
    'CANDIDATE_CORE_MULS_PER_LEAF',
    'CoreProductProfile',
    'CURRENT_COMPLETE_MULS_PER_LEAF',
    'CURRENT_EXACT_BEST_GATE',
    'FIELD_BITS',
    'FIELD_MUL_NON_CLIFFORD',
    'HybridGateProxy',
    'RETAINED_CALLS',
    'RETAINED_PHASE_A_WINDOWS',
    'RETAINED_PHASE_B_COUNT',
    'SELECT_NON_CLIFFORD',
    'ShellSelectStage',
    'WINDOW_BITS',
    'WindowExceptionProfile',
    'ZERO_TEST_COMPUTE_UNCOMPUTE',
    'build_delayed_lookup_cached_z_power_skeleton',
    'build_prefix_loaded_cached_z_power_skeleton',
    'count_phase_specialized_zero_tests',
    'count_staged_shell_selects',
    'estimate_hybrid_gate_proxy',
    'fixed_order_peak_slots',
    'phase_a_exception_profile',
    'rondepierre_core_product_profile',
    'staged_shell_select_schedule',
]
