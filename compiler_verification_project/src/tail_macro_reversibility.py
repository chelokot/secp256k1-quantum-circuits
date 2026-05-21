#!/usr/bin/env python3

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


Point = Optional[Tuple[int, int]]
TOY_CURVES = (
    {'name': 'toy61_b2', 'p': 61, 'b': 2, 'order': 61, 'generator': (1, 8)},
    {'name': 'toy127_b11', 'p': 109, 'b': 11, 'order': 127, 'generator': (1, 11)},
    {'name': 'toy181_b3', 'p': 163, 'b': 3, 'order': 181, 'generator': (1, 2)},
    {'name': 'toy241_b29', 'p': 211, 'b': 29, 'order': 241, 'generator': (1, 36)},
)


def _inverse(value: int, modulus: int) -> int:
    return pow(value % modulus, -1, modulus)


def _add_points(left: Point, right: Point, modulus: int) -> Point:
    if left is None:
        return right
    if right is None:
        return left
    left_x, left_y = left
    right_x, right_y = right
    if left_x == right_x and (left_y + right_y) % modulus == 0:
        return None
    if left == right:
        slope = (3 * left_x * left_x * _inverse(2 * left_y, modulus)) % modulus
    else:
        slope = ((right_y - left_y) * _inverse(right_x - left_x, modulus)) % modulus
    out_x = (slope * slope - left_x - right_x) % modulus
    out_y = (slope * (left_x - out_x) - left_y) % modulus
    return (out_x, out_y)


def _subgroup_points(modulus: int, generator: Tuple[int, int], order: int) -> List[Point]:
    points = []
    point: Point = None
    for _ in range(order):
        points.append(point)
        point = _add_points(point, generator, modulus)
    return points


def _tail_map(
    modulus: int,
    curve_b: int,
    lookup_x: int,
    lookup_y: int,
    accum_x: int,
    accum_y: int,
    accum_z: int,
) -> Tuple[int, int, int]:
    b3 = (3 * curve_b) % modulus
    h_value = ((accum_x + accum_y) * ((lookup_x + lookup_y) % modulus)) % modulus
    a_value = (accum_x * lookup_x) % modulus
    zx_value = (accum_z * lookup_x) % modulus
    c_value = (b3 * (accum_x + zx_value)) % modulus
    i_value = (accum_y * lookup_y) % modulus
    k_value = (h_value - a_value - i_value) % modulus
    l_value = (3 * a_value) % modulus
    yz_value = (lookup_y * accum_z) % modulus
    e_value = (accum_y + yz_value) % modulus
    f_value = (b3 * accum_z) % modulus
    m_value = (i_value + f_value) % modulus
    n_value = (i_value - f_value) % modulus
    return (
        (k_value * n_value - e_value * c_value) % modulus,
        (n_value * m_value + c_value * l_value) % modulus,
        (m_value * e_value + l_value * k_value) % modulus,
    )


def _full_domain_collision(curve: Dict[str, Any]) -> Dict[str, Any]:
    modulus = int(curve['p'])
    curve_b = int(curve['b'])
    lookup_x, lookup_y = curve['generator']
    seen: Dict[Tuple[int, int, int], Tuple[int, int, int]] = {}
    for accum_x in range(modulus):
        for accum_y in range(modulus):
            for accum_z in range(modulus):
                input_triple = (accum_x, accum_y, accum_z)
                output_triple = _tail_map(modulus, curve_b, lookup_x, lookup_y, accum_x, accum_y, accum_z)
                previous = seen.get(output_triple)
                if previous is not None and previous != input_triple:
                    return {
                        'domain_size': modulus ** 3,
                        'injective': False,
                        'collision': {
                            'first_input': list(previous),
                            'second_input': list(input_triple),
                            'shared_output': list(output_triple),
                        },
                    }
                seen[output_triple] = input_triple
    return {'domain_size': modulus ** 3, 'injective': True, 'collision': None}


def _canonical_subgroup_injectivity(curve: Dict[str, Any]) -> Dict[str, Any]:
    modulus = int(curve['p'])
    curve_b = int(curve['b'])
    lookup_x, lookup_y = curve['generator']
    seen: Dict[Tuple[int, int, int], Tuple[int, int, int]] = {}
    for point in _subgroup_points(modulus, curve['generator'], int(curve['order'])):
        input_triple = (0, 1, 0) if point is None else (point[0], point[1], 1)
        output_triple = _tail_map(modulus, curve_b, lookup_x, lookup_y, *input_triple)
        previous = seen.get(output_triple)
        if previous is not None and previous != input_triple:
            return {
                'curve': curve['name'],
                'representative_count': int(curve['order']),
                'injective': False,
                'collision': {
                    'first_input': list(previous),
                    'second_input': list(input_triple),
                    'shared_output': list(output_triple),
                },
            }
        seen[output_triple] = input_triple
    return {
        'curve': curve['name'],
        'representative_count': int(curve['order']),
        'injective': True,
        'collision': None,
    }


def _all_projective_representative_collision(curve: Dict[str, Any]) -> Dict[str, Any]:
    modulus = int(curve['p'])
    curve_b = int(curve['b'])
    lookup_x, lookup_y = curve['generator']
    seen: Dict[Tuple[int, int, int], Tuple[int, int, int]] = {}
    full_representative_count = 1 + (int(curve['order']) - 1) * (modulus - 1)
    searched_representatives = 0
    for point in _subgroup_points(modulus, curve['generator'], int(curve['order'])):
        if point is None:
            representative_rows = [(0, 1, 0)]
        else:
            representative_rows = [
                ((point[0] * accum_z) % modulus, (point[1] * accum_z) % modulus, accum_z)
                for accum_z in range(1, modulus)
            ]
        for input_triple in representative_rows:
            searched_representatives += 1
            output_triple = _tail_map(modulus, curve_b, lookup_x, lookup_y, *input_triple)
            previous = seen.get(output_triple)
            if previous is not None and previous != input_triple:
                return {
                    'curve': curve['name'],
                    'full_representative_count': full_representative_count,
                    'searched_representatives_until_collision': searched_representatives,
                    'injective': False,
                    'collision': {
                        'first_input': list(previous),
                        'second_input': list(input_triple),
                        'shared_output': list(output_triple),
                    },
                }
            seen[output_triple] = input_triple
    return {
        'curve': curve['name'],
        'full_representative_count': full_representative_count,
        'searched_representatives_until_collision': searched_representatives,
        'injective': True,
        'collision': None,
    }


def _fixed_lookup_reachable_orbit_injectivity(curve: Dict[str, Any]) -> Dict[str, Any]:
    modulus = int(curve['p'])
    curve_b = int(curve['b'])
    lookup_x, lookup_y = curve['generator']
    state = (0, 1, 0)
    orbit = []
    for _ in range(int(curve['order'])):
        orbit.append(state)
        state = _tail_map(modulus, curve_b, lookup_x, lookup_y, *state)
    seen: Dict[Tuple[int, int, int], Tuple[int, int, int]] = {}
    for input_triple in orbit:
        output_triple = _tail_map(modulus, curve_b, lookup_x, lookup_y, *input_triple)
        previous = seen.get(output_triple)
        if previous is not None and previous != input_triple:
            return {
                'curve': curve['name'],
                'reachable_state_count': len(orbit),
                'unique_reachable_state_count': len(set(orbit)),
                'returns_to_projective_infinity_after_group_order_steps': state[2] % modulus == 0,
                'injective': False,
                'collision': {
                    'first_input': list(previous),
                    'second_input': list(input_triple),
                    'shared_output': list(output_triple),
                },
            }
        seen[output_triple] = input_triple
    return {
        'curve': curve['name'],
        'reachable_state_count': len(orbit),
        'unique_reachable_state_count': len(set(orbit)),
        'returns_to_projective_infinity_after_group_order_steps': state[2] % modulus == 0,
        'injective': True,
        'collision': None,
    }


def build_tail_macro_reversibility() -> Dict[str, Any]:
    full_domain_curve = TOY_CURVES[0]
    canonical_rows = [_canonical_subgroup_injectivity(curve) for curve in TOY_CURVES]
    projective_rows = [_all_projective_representative_collision(curve) for curve in TOY_CURVES]
    reachable_rows = [_fixed_lookup_reachable_orbit_injectivity(curve) for curve in TOY_CURVES]
    full_domain = {
        'curve': full_domain_curve['name'],
        **_full_domain_collision(full_domain_curve),
    }
    return {
        'schema': 'compiler-project-tail-macro-reversibility-v1',
        'opcode': 'complete_a0_all_streamed_tail',
        'semantic_map': '(X,Y,Z) -> complete_a0_all_streamed_tail(X,Y,Z,lookup_x,lookup_y)',
        'full_raw_field_domain': full_domain,
        'canonical_subgroup_domain': {
            'lookup_point_policy': 'generator_point_as_nonzero_lookup_entry',
            'rows': canonical_rows,
            'all_checked_rows_injective': all(bool(row['injective']) for row in canonical_rows),
        },
        'all_projective_representatives_domain': {
            'projective_representation': 'plain_projective_x_over_z_y_over_z',
            'rows': projective_rows,
            'all_checked_rows_injective': all(bool(row['injective']) for row in projective_rows),
        },
        'fixed_lookup_reachable_orbit_domain': {
            'lookup_point_policy': 'repeat_generator_point_as_nonzero_lookup_entry',
            'rows': reachable_rows,
            'all_checked_rows_injective': all(bool(row['injective']) for row in reachable_rows),
            'all_checked_rows_return_to_projective_infinity': all(
                bool(row['returns_to_projective_infinity_after_group_order_steps'])
                for row in reachable_rows
            ),
        },
        'status': 'three_slot_tail_requires_valid_subspace_permutation_extension',
        'notes': [
            'The polynomial tail formula is not injective over the full raw field-register domain, so it cannot itself be a no-ancilla in-place reversible map on arbitrary field triples.',
            'The same formula is injective on canonical subgroup representatives and on the fixed-lookup reachable orbit for the curated toy curves.',
            'It is not injective on all plain-projective representatives of the subgroup, so a future three-slot primitive schedule must specify the exact reachable/encoded subspace instead of saying all valid projective triples.',
            'A future three-slot primitive schedule must prove a reversible permutation extension or an explicit valid-subspace encoding; semantic point-add tests alone are not enough.',
        ],
    }


__all__ = ['build_tail_macro_reversibility']
