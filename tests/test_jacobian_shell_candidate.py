#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from common import SECP_N  # noqa: E402
from jacobian_shell_candidate import (  # noqa: E402
    CURRENT_EXACT_BEST_GATE,
    FIELD_MUL_NON_CLIFFORD,
    RETAINED_CALLS,
    RETAINED_PHASE_A_WINDOWS,
    RETAINED_PHASE_B_COUNT,
    build_delayed_lookup_cached_z_power_skeleton,
    build_prefix_loaded_cached_z_power_skeleton,
    count_phase_specialized_zero_tests,
    count_staged_shell_selects,
    estimate_hybrid_gate_proxy,
    fixed_order_peak_slots,
    phase_a_exception_profile,
    rondepierre_core_product_profile,
    staged_shell_select_schedule,
)
from leaf_schedule_optimizer import find_low_live_body_order  # noqa: E402


def test_phase_a_exception_profile_is_safe_except_for_top_inverse_window() -> None:
    profiles = phase_a_exception_profile(SECP_N)
    assert [profile.window_index for profile in profiles] == list(RETAINED_PHASE_A_WINDOWS)
    assert all(profile.doubling_witness_count == 0 for profile in profiles)
    inverse_windows = [profile.window_index for profile in profiles if profile.inverse_witness_count > 0]
    assert inverse_windows == [15]
    top_window = next(profile for profile in profiles if profile.window_index == 15)
    assert top_window.inverse_witness_count == 1


def test_phase_specialized_zero_test_count_matches_current_hybrid_screen() -> None:
    profiles = phase_a_exception_profile(SECP_N)
    assert count_phase_specialized_zero_tests(profiles, retained_phase_b_count=RETAINED_PHASE_B_COUNT) == 27


def test_staged_shell_select_schedule_uses_twelve_field_selects() -> None:
    stages = staged_shell_select_schedule()
    assert [stage.name for stage in stages] == [
        'exceptional_output_from_f0',
        'core_or_exceptional_from_e0',
        'passthrough_p_from_q_inf',
        'passthrough_q_from_p_inf',
    ]
    assert count_staged_shell_selects(stages) == 12


def test_hybrid_gate_proxy_matches_current_research_screen() -> None:
    proxy = estimate_hybrid_gate_proxy()
    assert proxy.base_non_clifford == CURRENT_EXACT_BEST_GATE
    assert proxy.arithmetic_saving == RETAINED_CALLS * 2 * FIELD_MUL_NON_CLIFFORD
    assert proxy.zero_test_overhead == 27 * 1024
    assert proxy.select_overhead == RETAINED_CALLS * 12 * 255
    assert proxy.projected_non_clifford == 19168527


def test_rondepierre_product_profile_exposes_cached_z_power_requirement() -> None:
    cached = rondepierre_core_product_profile(cached_z_powers=True)
    uncached = rondepierre_core_product_profile(cached_z_powers=False)
    assert cached.multiplication_count == 7
    assert cached.squaring_count == 2
    assert cached.total_field_products == 9
    assert uncached.multiplication_count == 8
    assert uncached.squaring_count == 3
    assert uncached.total_field_products == 11


def test_prefix_loaded_cached_z_power_contract_blocks_seven_slot_target() -> None:
    skeleton = build_prefix_loaded_cached_z_power_skeleton()
    try:
        find_low_live_body_order(skeleton, 7)
    except ValueError as exc:
        assert 'fits within 7 live field slots' in str(exc)
    else:
        raise AssertionError('expected 7-slot search to fail for a seven-input prefix-loaded skeleton')
    order = find_low_live_body_order(skeleton, 8)
    assert len(order) == 4
    assert set(order) == {7, 8, 9, 10}


def test_delayed_lookup_loading_returns_strengthened_skeleton_to_seven_slot_class() -> None:
    eager = build_prefix_loaded_cached_z_power_skeleton()
    delayed = build_delayed_lookup_cached_z_power_skeleton()
    assert fixed_order_peak_slots(eager) == 8
    assert fixed_order_peak_slots(delayed) == 7
