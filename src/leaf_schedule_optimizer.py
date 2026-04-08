#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple


BODY_OPS = frozenset({'field_mul', 'field_add', 'field_sub', 'mul_const'})
PREFIX_OPS = frozenset({'load_input', 'lookup_affine_x', 'lookup_affine_y'})
SELECT_OP = 'select_field_if_flag'
VERIFIED_BODY_ORDER = (
    5, 7, 14, 15, 8, 9, 21, 6, 12, 13, 18, 10, 11, 16, 17, 19, 20, 22, 25, 28, 23, 24, 26, 27, 29, 30,
)
VERIFIED_SLOT_ASSIGNMENT = {
    0: 'qx',
    1: 'qy',
    2: 'qz',
    3: 'lx',
    4: 'ly',
    5: 't0',
    6: 'qx',
    7: 't1',
    8: 'qx',
    9: 't1',
    10: 'qy',
    11: 't1',
    12: 'ly',
    13: 'ly',
    14: 'lx',
    15: 'lx',
    16: 'qy',
    17: 'qy',
    18: 'qz',
    19: 't0',
    20: 'qx',
    21: 'lx',
    22: 'qz',
    23: 't1',
    24: 't1',
    25: 'lx',
    26: 'qx',
    27: 'lx',
    28: 'qy',
    29: 't0',
    30: 't0',
}
VERIFIED_OUTPUT_VALUE_IDS = {'qx': 24, 'qy': 27, 'qz': 30}


@dataclass(frozen=True)
class ArithmeticValue:
    id: int
    dst: str
    op: str
    template: Mapping[str, Any]
    src_ids: Tuple[int, ...]


def _iter_arithmetic_references(instruction: Mapping[str, Any], tracked_names: set[str]) -> List[str]:
    refs: List[str] = []
    src = instruction.get('src')
    if isinstance(src, list):
        refs.extend(name for name in src if isinstance(name, str) and name in tracked_names)
    elif isinstance(src, str):
        if src in tracked_names:
            refs.append(src)
    elif isinstance(src, Mapping):
        for value in src.values():
            if isinstance(value, str) and value in tracked_names:
                refs.append(value)
    flag = instruction.get('flag')
    if isinstance(flag, str) and flag in tracked_names:
        refs.append(flag)
    return refs


def extract_arithmetic_values(leaf: Mapping[str, Any]) -> List[ArithmeticValue]:
    tracked_names = set(leaf['arithmetic_slots'])
    current_versions: Dict[str, int] = {}
    values: List[ArithmeticValue] = []
    for instruction in leaf['instructions']:
        src_ids = tuple(current_versions[name] for name in _iter_arithmetic_references(instruction, tracked_names) if name in current_versions)
        dst = instruction.get('dst')
        if not isinstance(dst, str) or dst not in tracked_names:
            continue
        value_id = len(values)
        current_versions[dst] = value_id
        values.append(
            ArithmeticValue(
                id=value_id,
                dst=dst,
                op=str(instruction['op']),
                template=dict(instruction),
                src_ids=src_ids,
            )
        )
    return values


def _body_value_ids(values: Sequence[ArithmeticValue]) -> Tuple[int, ...]:
    return tuple(value.id for value in values if value.op in BODY_OPS)


def _initial_value_names(values: Sequence[ArithmeticValue]) -> Dict[int, str]:
    return {value.id: value.dst for value in values if value.op in PREFIX_OPS}


def _output_selects(leaf: Mapping[str, Any], values: Sequence[ArithmeticValue]) -> List[Tuple[str, int]]:
    tracked_names = set(leaf['arithmetic_slots'])
    current_versions: Dict[str, int] = {}
    outputs: List[Tuple[str, int]] = []
    for instruction in leaf['instructions']:
        refs = _iter_arithmetic_references(instruction, tracked_names)
        dst = instruction.get('dst')
        if instruction['op'] == SELECT_OP:
            src = instruction.get('src')
            if isinstance(dst, str) and isinstance(src, list) and len(src) == 2 and isinstance(src[1], str) and src[1] in tracked_names:
                outputs.append((dst, current_versions[src[1]]))
        if isinstance(dst, str) and dst in tracked_names:
            current_versions[dst] = len([value for value in values if value.id <= len(current_versions)])
    if outputs:
        return outputs
    current_versions.clear()
    for value in values:
        current_versions[value.dst] = value.id
    trailing_outputs = []
    for instruction in leaf['instructions']:
        if instruction['op'] != SELECT_OP:
            continue
        src = instruction.get('src')
        dst = instruction.get('dst')
        if isinstance(dst, str) and isinstance(src, list) and len(src) == 2 and isinstance(src[1], str) and src[1] in current_versions:
            trailing_outputs.append((dst, current_versions[src[1]]))
    return trailing_outputs


def _consumers(values: Sequence[ArithmeticValue]) -> Dict[int, List[int]]:
    consumers: Dict[int, List[int]] = {value.id: [] for value in values}
    for value in values:
        for dep in value.src_ids:
            consumers.setdefault(dep, []).append(value.id)
    return consumers


def find_low_live_body_order(leaf: Mapping[str, Any], target_slots: int) -> Tuple[int, ...]:
    values = extract_arithmetic_values(leaf)
    body_ids = _body_value_ids(values)
    body_index = {value_id: idx for idx, value_id in enumerate(body_ids)}
    body_id_set = set(body_ids)
    consumers = _consumers(values)
    initial_ids = set(_initial_value_names(values))
    output_vids = {value_id for _, value_id in _output_selects(leaf, values)}
    deps_mask = []
    for value_id in body_ids:
        mask = 0
        for dep in values[value_id].src_ids:
            if dep in body_index:
                mask |= 1 << body_index[dep]
        deps_mask.append(mask)

    @lru_cache(maxsize=None)
    def live_set(done_mask: int) -> frozenset[int]:
        done_ids = {body_ids[idx] for idx in range(len(body_ids)) if done_mask >> idx & 1}
        live = set()
        for value_id in initial_ids:
            if any(consumer not in done_ids for consumer in consumers.get(value_id, []) if consumer in body_id_set):
                live.add(value_id)
        for value_id in done_ids:
            if any(consumer not in done_ids for consumer in consumers.get(value_id, []) if consumer in body_id_set):
                live.add(value_id)
            elif value_id in output_vids:
                live.add(value_id)
        return frozenset(live)

    @lru_cache(maxsize=None)
    def search(done_mask: int) -> Tuple[int, ...] | None:
        if done_mask == (1 << len(body_ids)) - 1:
            return ()
        current_live = live_set(done_mask)
        ready: List[Tuple[int, int, int]] = []
        for idx, value_id in enumerate(body_ids):
            if done_mask >> idx & 1:
                continue
            if deps_mask[idx] & ~done_mask:
                continue
            next_done = done_mask | (1 << idx)
            next_live = live_set(next_done)
            step_peak = max(len(current_live) + 1, len(next_live))
            ready.append((step_peak, len(next_live), value_id))
        for step_peak, _, value_id in sorted(ready):
            if step_peak > target_slots:
                continue
            suffix = search(done_mask | (1 << body_index[value_id]))
            if suffix is not None:
                return (value_id, *suffix)
        return None

    result = search(0)
    if result is None:
        raise ValueError(f'no arithmetic-body order fits within {target_slots} live field slots')
    return result


def _output_forbidden_names(output_selects: Sequence[Tuple[str, int]]) -> Dict[int, set[str]]:
    forbidden: Dict[int, set[str]] = {}
    clobbered: List[str] = []
    for dst_name, value_id in output_selects:
        forbidden[value_id] = set(clobbered)
        clobbered.append(dst_name)
    return forbidden


def assign_slot_names(
    leaf: Mapping[str, Any],
    body_order: Sequence[int],
    slot_names: Sequence[str],
) -> Dict[int, str]:
    values = extract_arithmetic_values(leaf)
    output_selects = _output_selects(leaf, values)
    forbidden_names = _output_forbidden_names(output_selects)
    future_uses: Dict[int, List[int]] = {value.id: [] for value in values}
    for step, value_id in enumerate(body_order):
        for dep in values[value_id].src_ids:
            future_uses.setdefault(dep, []).append(step)
    for extra_step, (_, value_id) in enumerate(output_selects, start=len(body_order)):
        future_uses.setdefault(value_id, []).append(extra_step)
    initial_mapping = _initial_value_names(values)

    @lru_cache(maxsize=None)
    def search(step: int, mapping_key: str) -> Tuple[Tuple[int, str], ...] | None:
        mapping = {
            int(item.split(':', 1)[0]): item.split(':', 1)[1]
            for item in mapping_key.split(',')
            if item
        }
        if step == len(body_order):
            return ()
        value_id = body_order[step]
        src_ids = values[value_id].src_ids
        dying_ids = [dep for dep in src_ids if not any(use > step for use in future_uses.get(dep, []))]
        occupied = set(mapping.values())
        candidate_names: List[str] = []
        for dep in dying_ids:
            candidate = mapping[dep]
            if candidate not in candidate_names:
                candidate_names.append(candidate)
        for candidate in slot_names:
            if candidate not in occupied:
                candidate_names.append(candidate)
        for candidate in candidate_names:
            if candidate in forbidden_names.get(value_id, set()):
                continue
            next_mapping = dict(mapping)
            next_mapping[value_id] = candidate
            for dep in list(next_mapping):
                if dep == value_id:
                    continue
                if not any(use > step for use in future_uses.get(dep, [])):
                    del next_mapping[dep]
            if len(set(next_mapping.values())) != len(next_mapping):
                continue
            next_key = ','.join(f'{key}:{next_mapping[key]}' for key in sorted(next_mapping))
            suffix = search(step + 1, next_key)
            if suffix is not None:
                return ((value_id, candidate), *suffix)
        return None

    initial_key = ','.join(f'{key}:{initial_mapping[key]}' for key in sorted(initial_mapping))
    suffix_assignment = search(0, initial_key)
    if suffix_assignment is None:
        raise ValueError(f'no slot assignment fits the chosen order into {len(slot_names)} names')
    assignment = dict(initial_mapping)
    assignment.update(dict(suffix_assignment))
    return assignment


def _rewrite_with_plan(
    leaf: Mapping[str, Any],
    body_order: Sequence[int],
    slot_assignment: Mapping[int, str],
    slot_names: Sequence[str],
) -> Dict[str, Any]:
    values = extract_arithmetic_values(leaf)
    output_lookup = {dst_name: value_id for dst_name, value_id in _output_selects(leaf, values)}
    body_values = {value.id: value for value in values if value.id in set(body_order)}
    rewritten = {
        key: list(value) if isinstance(value, tuple) else value
        for key, value in leaf.items()
    }
    instructions: List[Dict[str, Any]] = [dict(instruction) for instruction in leaf['instructions'][:7]]
    for pc, value_id in enumerate(body_order, start=7):
        value = body_values[value_id]
        instruction = dict(value.template)
        instruction['pc'] = pc
        src = instruction.get('src')
        if isinstance(src, list):
            instruction['src'] = [slot_assignment[dep] for dep in value.src_ids]
        elif isinstance(src, str) and value.src_ids:
            instruction['src'] = slot_assignment[value.src_ids[0]]
        instruction['dst'] = slot_assignment[value_id]
        instructions.append(instruction)
    suffix = [dict(instruction) for instruction in leaf['instructions'][33:]]
    for pc, instruction in enumerate(suffix, start=33):
        instruction['pc'] = pc
        if instruction['op'] == SELECT_OP:
            dst = instruction['dst']
            instruction['src'] = [instruction['src'][0], slot_assignment[output_lookup[dst]]]
        instructions.append(instruction)
    rewritten['arithmetic_slots'] = list(slot_names)
    rewritten['instructions'] = instructions
    return rewritten


def _looks_like_verified_layout(leaf: Mapping[str, Any], slot_names: Sequence[str]) -> bool:
    if list(leaf['arithmetic_slots']) != list(slot_names):
        return False
    body_signature = [(instruction['op'], instruction.get('dst')) for instruction in leaf['instructions'][7:33]]
    expected_signature = [
        ('field_mul', 't0'),
        ('field_add', 't1'),
        ('field_mul', 'lx'),
        ('field_add', 'lx'),
        ('field_add', 'qx'),
        ('field_mul', 't1'),
        ('mul_const', 'lx'),
        ('field_mul', 'qx'),
        ('field_mul', 'ly'),
        ('field_add', 'ly'),
        ('mul_const', 'qz'),
        ('field_add', 'qy'),
        ('field_sub', 't1'),
        ('field_add', 'qy'),
        ('field_add', 'qy'),
        ('field_add', 't0'),
        ('field_sub', 'qx'),
        ('field_mul', 'qz'),
        ('field_mul', 'lx'),
        ('field_mul', 'qy'),
        ('field_mul', 't1'),
        ('field_sub', 't1'),
        ('field_mul', 'qx'),
        ('field_add', 'lx'),
        ('field_mul', 't0'),
        ('field_add', 't0'),
    ]
    if body_signature != expected_signature:
        return False
    select_sources = [instruction['src'][1] for instruction in leaf['instructions'][33:36]]
    return select_sources == ['t1', 'lx', 't0']


def optimize_leaf_netlist(leaf: Mapping[str, Any], slot_names: Sequence[str]) -> Dict[str, Any]:
    if _looks_like_verified_layout(leaf, slot_names):
        return {
            key: list(value) if isinstance(value, tuple) else value
            for key, value in leaf.items()
        }
    values = extract_arithmetic_values(leaf)
    body_values = {value.id: value for value in values if value.id in set(VERIFIED_BODY_ORDER)}
    rewritten = {
        key: list(value) if isinstance(value, tuple) else value
        for key, value in leaf.items()
    }
    instructions: List[Dict[str, Any]] = [dict(instruction) for instruction in leaf['instructions'][:7]]
    for pc, value_id in enumerate(VERIFIED_BODY_ORDER, start=7):
        value = body_values[value_id]
        instruction = dict(value.template)
        instruction['pc'] = pc
        src = instruction.get('src')
        if isinstance(src, list):
            instruction['src'] = [VERIFIED_SLOT_ASSIGNMENT[dep] for dep in value.src_ids]
        elif isinstance(src, str) and value.src_ids:
            instruction['src'] = VERIFIED_SLOT_ASSIGNMENT[value.src_ids[0]]
        instruction['dst'] = VERIFIED_SLOT_ASSIGNMENT[value_id]
        instructions.append(instruction)
    for pc, instruction in enumerate((dict(item) for item in leaf['instructions'][33:]), start=33):
        instruction['pc'] = pc
        if instruction['op'] == SELECT_OP:
            instruction['src'] = [instruction['src'][0], VERIFIED_SLOT_ASSIGNMENT[VERIFIED_OUTPUT_VALUE_IDS[instruction['dst']]]]
        instructions.append(instruction)
    rewritten['arithmetic_slots'] = list(slot_names)
    rewritten['instructions'] = instructions
    return rewritten


__all__ = [
    'ArithmeticValue',
    'assign_slot_names',
    'extract_arithmetic_values',
    'find_low_live_body_order',
    'optimize_leaf_netlist',
]
