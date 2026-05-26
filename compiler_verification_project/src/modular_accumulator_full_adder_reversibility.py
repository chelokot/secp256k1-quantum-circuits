#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
from itertools import product
from math import ceil, log2
from typing import Any, Dict, List, Mapping

from modular_accumulator_full_adder_liveness import FULL_ADDER_LIVENESS_UNPROMOTED_STATUS


MODULAR_ACCUMULATOR_FULL_ADDER_REVERSIBILITY_SCHEMA = 'compiler-project-modular-accumulator-full-adder-reversibility-v1'
FULL_ADDER_REVERSIBILITY_UNPROMOTED_STATUS = 'full_adder_reversibility_lower_bound_not_promoted_to_global_resource_contract'


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def _sha256_payload(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode('ascii')).hexdigest()


def _full_adder_output(input_bits: tuple[int, int, int]) -> tuple[int, int]:
    weight = sum(input_bits)
    return weight & 1, 1 if weight >= 2 else 0


def _output_classes() -> Dict[str, List[Dict[str, Any]]]:
    classes: Dict[str, List[Dict[str, Any]]] = {}
    for input_bits in product((0, 1), repeat=3):
        output = _full_adder_output(input_bits)
        key = f'sum={output[0]},carry={output[1]}'
        classes.setdefault(key, []).append({
            'a': input_bits[0],
            'b': input_bits[1],
            'c': input_bits[2],
            'sum': output[0],
            'carry': output[1],
        })
    return {
        key: rows
        for key, rows in sorted(classes.items())
    }


def _one_bit_witness_search(classes: Mapping[str, List[Mapping[str, Any]]]) -> Dict[str, Any]:
    collision_free_count = 0
    best_distinct_tag_count = 0
    best_witness_index = 0
    for witness_index in range(1 << 8):
        collision_free = True
        distinct_tag_count = 0
        cursor = 0
        for rows in classes.values():
            tags = set()
            for _row in rows:
                tags.add((witness_index >> cursor) & 1)
                cursor += 1
            distinct_tag_count += len(tags)
            if len(tags) < len(rows):
                collision_free = False
        if distinct_tag_count > best_distinct_tag_count:
            best_distinct_tag_count = distinct_tag_count
            best_witness_index = witness_index
        if collision_free:
            collision_free_count += 1
    return {
        'candidate_function_count': 1 << 8,
        'collision_free_function_count': collision_free_count,
        'best_distinct_tag_count': best_distinct_tag_count,
        'best_witness_truth_table_index': best_witness_index,
    }


def _two_bit_witness_assignment(classes: Mapping[str, List[Mapping[str, Any]]]) -> Dict[str, List[int]]:
    return {
        key: list(range(len(rows)))
        for key, rows in classes.items()
    }


def build_modular_accumulator_full_adder_reversibility(
    *,
    modular_accumulator_full_adder_liveness: Mapping[str, Any],
) -> Dict[str, Any]:
    classes = _output_classes()
    class_sizes = {
        key: len(rows)
        for key, rows in classes.items()
    }
    max_preimage_size = max(class_sizes.values())
    minimum_witness_bits = ceil(log2(max_preimage_size))
    one_bit_search = _one_bit_witness_search(classes)
    two_bit_assignment = _two_bit_witness_assignment(classes)
    cell_count = int(modular_accumulator_full_adder_liveness['full_adder_cell_count'])
    minimum_witness_bits_total = cell_count * minimum_witness_bits
    checks = {
        'source_full_adder_liveness_passes': modular_accumulator_full_adder_liveness['pass'] is True,
        'source_full_adder_liveness_is_unpromoted': modular_accumulator_full_adder_liveness['promotion_status']['status'] == FULL_ADDER_LIVENESS_UNPROMOTED_STATUS,
        'full_adder_output_classes_cover_all_inputs': sum(class_sizes.values()) == 8,
        'full_adder_has_three_input_preimage_class': max_preimage_size == 3,
        'minimum_witness_bits_is_two': minimum_witness_bits == 2,
        'one_bit_witness_is_impossible_by_exhaustive_function_search': one_bit_search['collision_free_function_count'] == 0,
        'two_bit_witness_assignment_is_sufficient_locally': all(len(set(tags)) == len(classes[key]) for key, tags in two_bit_assignment.items()),
        'minimum_witness_total_matches_cell_count': minimum_witness_bits_total == 2 * cell_count,
        'reversibility_lower_bound_not_promoted_to_global_resource_contract': True,
    }
    return {
        'schema': MODULAR_ACCUMULATOR_FULL_ADDER_REVERSIBILITY_SCHEMA,
        'definition': 'Local reversibility lower bound for using a full-adder as a carry-save compression cell. The map from three input bits to sum/carry has output classes of size three, so no one-bit witness can make the transformation injective; any local reversible embedding that exposes sum and carry needs at least two witness bits unless a separate source-uncompute proof is supplied.',
        'source_digests': {
            'modular_accumulator_full_adder_liveness_sha256': _sha256_payload(modular_accumulator_full_adder_liveness),
        },
        'output_classes': classes,
        'output_class_sizes': class_sizes,
        'max_preimage_size': max_preimage_size,
        'minimum_witness_bits_per_cell': minimum_witness_bits,
        'minimum_witness_bits_total': minimum_witness_bits_total,
        'one_bit_witness_exhaustive_search': one_bit_search,
        'two_bit_witness_assignment': two_bit_assignment,
        'promotion_status': {
            'status': FULL_ADDER_REVERSIBILITY_UNPROMOTED_STATUS,
            'required_to_promote': [
                'Either count at least two local witness bits per full-adder cell in the global owner-capacity model, or provide a concrete source-uncompute schedule that removes the need for local witnesses.',
                'Bind the selected witness or uncompute schedule into the same primitive stream and liveness engine as the public resource headline.',
                'Reject one-bit in-place carry-save rewrites unless a separate non-local reversible construction proves injectivity.',
            ],
        },
        'checks': checks,
        'pass': all(checks.values()),
    }


__all__ = [
    'FULL_ADDER_REVERSIBILITY_UNPROMOTED_STATUS',
    'MODULAR_ACCUMULATOR_FULL_ADDER_REVERSIBILITY_SCHEMA',
    'build_modular_accumulator_full_adder_reversibility',
]
