#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Mapping

from modular_accumulator_full_adder_stream import (
    FULL_ADDER_STREAM_UNPROMOTED_STATUS,
    MODULAR_ACCUMULATOR_FULL_ADDER_STREAM_SCHEMA,
    iter_full_adder_stream_rows,
)


MODULAR_ACCUMULATOR_FULL_ADDER_LIVENESS_SCHEMA = 'compiler-project-modular-accumulator-full-adder-liveness-v1'
FULL_ADDER_LIVENESS_UNPROMOTED_STATUS = 'full_adder_liveness_not_promoted_to_global_resource_contract'


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def _sha256_payload(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode('ascii')).hexdigest()


def _empty_counts(keys: Mapping[str, Any]) -> Dict[str, int]:
    return {str(key): 0 for key in keys}


def build_modular_accumulator_full_adder_liveness(
    *,
    modular_accumulator_carry_save_candidate: Mapping[str, Any],
    modular_accumulator_full_adder_stream: Mapping[str, Any],
) -> Dict[str, Any]:
    field_bits = int(modular_accumulator_full_adder_stream['field_bits'])
    grid_count = int(modular_accumulator_full_adder_stream['schoolbook_grid_count'])
    observed_counts = _empty_counts(modular_accumulator_full_adder_stream['primitive_counts_total'])
    operation_count = 0
    scanned_cell_count = 0
    retained_input_observations = 0
    output_wire_observations = 0
    current_grid = None
    current_cell = None
    grid_initial_wires = field_bits * field_bits
    grid_forward_live = 0
    grid_forward_peak = 0
    grid_optimistic_consumed_live = 0
    grid_optimistic_consumed_peak = 0
    grid_cell_count = 0
    grid_output_count = 0
    per_grid: List[Dict[str, int]] = []

    def close_grid() -> None:
        if current_grid is None:
            return
        per_grid.append({
            'grid_index': int(current_grid),
            'initial_partial_product_wires': grid_initial_wires,
            'full_adder_cells': grid_cell_count,
            'sum_carry_output_wires': grid_output_count,
            'forward_only_peak_live_wires': grid_forward_peak,
            'forward_only_final_live_wires': grid_forward_live,
            'optimistic_consumed_peak_live_wires': grid_optimistic_consumed_peak,
            'optimistic_consumed_final_live_wires': grid_optimistic_consumed_live,
        })

    for row in iter_full_adder_stream_rows(
        field_bits=field_bits,
        grid_count=grid_count,
        gate_sequence=list(modular_accumulator_full_adder_stream['cell_gate_sequence']),
    ):
        row_grid = int(row['grid_index'])
        if current_grid != row_grid:
            close_grid()
            current_grid = row_grid
            current_cell = None
            grid_forward_live = grid_initial_wires
            grid_forward_peak = grid_initial_wires
            grid_optimistic_consumed_live = grid_initial_wires
            grid_optimistic_consumed_peak = grid_initial_wires
            grid_cell_count = 0
            grid_output_count = 0

        operation_count += 1
        observed_counts[str(row['gate'])] += 1
        cell_key = (
            int(row['grid_index']),
            int(row['layer_index']),
            int(row['column_index']),
            int(row['cell_index']),
        )
        if current_cell != cell_key:
            current_cell = cell_key
            scanned_cell_count += 1
            grid_cell_count += 1
            retained_input_observations += len(row['cell_input_wires'])
            output_wire_observations += 2
            grid_output_count += 2
            grid_forward_live += 2
            grid_forward_peak = max(grid_forward_peak, grid_forward_live)
            grid_optimistic_consumed_peak = max(grid_optimistic_consumed_peak, grid_optimistic_consumed_live + 2)
            grid_optimistic_consumed_live = grid_optimistic_consumed_live + 2 - len(row['cell_input_wires'])

    close_grid()

    forward_sequential_peak = max(row['forward_only_peak_live_wires'] for row in per_grid)
    forward_all_grids_peak = sum(row['forward_only_final_live_wires'] for row in per_grid)
    optimistic_consumed_sequential_peak = max(row['optimistic_consumed_peak_live_wires'] for row in per_grid)
    optimistic_consumed_all_grids_final = sum(row['optimistic_consumed_final_live_wires'] for row in per_grid)
    expected_final_live_per_grid = int(modular_accumulator_carry_save_candidate['single_grid']['final_live_column_bits'])
    checks = {
        'source_carry_save_candidate_passes': modular_accumulator_carry_save_candidate['pass'] is True,
        'source_full_adder_stream_passes': modular_accumulator_full_adder_stream['pass'] is True,
        'source_full_adder_stream_schema_is_current': modular_accumulator_full_adder_stream['schema'] == MODULAR_ACCUMULATOR_FULL_ADDER_STREAM_SCHEMA,
        'source_full_adder_stream_is_unpromoted': modular_accumulator_full_adder_stream['promotion_status']['status'] == FULL_ADDER_STREAM_UNPROMOTED_STATUS,
        'scanned_operation_count_matches_stream': operation_count == int(modular_accumulator_full_adder_stream['operation_count']),
        'scanned_gate_counts_match_stream': observed_counts == {
            str(key): int(value)
            for key, value in modular_accumulator_full_adder_stream['primitive_counts_total'].items()
        },
        'scanned_cell_count_matches_stream': scanned_cell_count == int(modular_accumulator_full_adder_stream['full_adder_cell_count']),
        'retained_input_observations_match_stream': retained_input_observations == int(modular_accumulator_full_adder_stream['retained_input_obligation_bits']),
        'output_wire_observations_match_stream': output_wire_observations == int(modular_accumulator_full_adder_stream['output_obligation_bits']),
        'per_grid_count_matches_stream_grid_count': len(per_grid) == grid_count,
        'optimistic_consumed_final_matches_candidate': all(row['optimistic_consumed_final_live_wires'] == expected_final_live_per_grid for row in per_grid),
        'forward_only_retained_wires_exceed_optimistic_consumed_wires': forward_sequential_peak > optimistic_consumed_sequential_peak,
        'liveness_not_promoted_to_global_resource_contract': True,
    }
    return {
        'schema': MODULAR_ACCUMULATOR_FULL_ADDER_LIVENESS_SCHEMA,
        'definition': 'Derived liveness and owner-capacity pressure for the exact carry-save full-adder stream. The forward-only reversible interpretation keeps cell inputs live and therefore counts retained wires instead of treating 3-to-2 compression as free; the optimistic consumed model is recorded only as a non-promoted lower bound.',
        'source_digests': {
            'modular_accumulator_carry_save_candidate_sha256': _sha256_payload(modular_accumulator_carry_save_candidate),
            'modular_accumulator_full_adder_stream_sha256': _sha256_payload(modular_accumulator_full_adder_stream),
        },
        'field_bits': field_bits,
        'schoolbook_grid_count': grid_count,
        'operation_count': operation_count,
        'full_adder_cell_count': scanned_cell_count,
        'primitive_counts_total': observed_counts,
        'retained_input_observation_count': retained_input_observations,
        'sum_carry_output_wire_count': output_wire_observations,
        'forward_only': {
            'sequential_grid_peak_live_wires': forward_sequential_peak,
            'all_grids_peak_live_wires': forward_all_grids_peak,
            'status': 'not_promoted_hidden_retained_inputs_must_be_uncomputed_or_counted',
        },
        'optimistic_consumed_lower_bound': {
            'sequential_grid_peak_live_wires': optimistic_consumed_sequential_peak,
            'all_grids_final_live_wires': optimistic_consumed_all_grids_final,
            'status': 'not_reversible_without_source_uncompute_proof',
        },
        'per_grid': per_grid,
        'promotion_status': {
            'status': FULL_ADDER_LIVENESS_UNPROMOTED_STATUS,
            'required_to_promote': [
                'Choose a concrete cleanup/uncompute schedule or count the forward-only retained inputs in global owner capacity.',
                'Assign every live carry-save wire to exactly one counted owner in the same liveness engine as the public headline.',
                'Replace scheduled arithmetic_scratch placeholders with this owner-capacity schedule.',
                'Recompute public qubits and non-Clifford from the promoted global primitive schedule.',
            ],
        },
        'checks': checks,
        'pass': all(checks.values()),
    }


__all__ = [
    'FULL_ADDER_LIVENESS_UNPROMOTED_STATUS',
    'MODULAR_ACCUMULATOR_FULL_ADDER_LIVENESS_SCHEMA',
    'build_modular_accumulator_full_adder_liveness',
]
