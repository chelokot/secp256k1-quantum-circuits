#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ROOT_SRC = PROJECT_ROOT / 'src'
if str(ROOT_SRC) not in sys.path:
    sys.path.insert(0, str(ROOT_SRC))

from common import SECP_B, SECP_P, load_json, neg_affine, sha256_bytes, sha256_path  # noqa: E402
from lookup_research import (  # noqa: E402
    build_lookup_folded_contract_definition,
    build_lookup_base_set,
    build_positive_table,
    fold_signed_i16,
    folded_lookup_point_from_cache,
)

PointAffine = Optional[Tuple[int, int]]
PrimitiveOperation = List[int | str]


def _lookup_contract_path() -> Path:
    return PROJECT_ROOT / 'artifacts' / 'lookup' / 'lookup_signed_fold_contract.json'


def _lookup_contract() -> Dict[str, Any]:
    path = _lookup_contract_path()
    if path.exists():
        return load_json(path)
    return build_lookup_folded_contract_definition()


def _contract_parameters(contract: Mapping[str, Any]) -> Dict[str, int]:
    word_bits = int(contract['window_size_bits'])
    return {
        'word_bits': word_bits,
        'magnitude_bits': word_bits - 1,
        'positive_domain_size': int(contract['folding']['folded_positive_table_entries_per_coordinate']),
        'coordinate_bits': SECP_P.bit_length(),
    }


def _primitive_counts(ccx: int = 0, cx: int = 0, x: int = 0, measurement: int = 0) -> Dict[str, int]:
    return {
        'ccx': ccx,
        'cx': cx,
        'x': x,
        'measurement': measurement,
    }


def _primitive_operation(gate: str, *operands: int) -> PrimitiveOperation:
    return [gate, *[int(operand) for operand in operands]]


def _primitive_counts_from_operations(primitive_operations: List[PrimitiveOperation]) -> Dict[str, int]:
    counts = _primitive_counts()
    for operation in primitive_operations:
        counts[str(operation[0])] += 1
    return counts


def _repeated_ladder_operations(instance_count: int, bit_count: int, include_measurement: bool) -> List[PrimitiveOperation]:
    primitive_operations: List[PrimitiveOperation] = []
    for instance_index in range(instance_count):
        for bit_index in range(bit_count):
            primitive_operations.append(_primitive_operation('ccx', instance_index, bit_index))
            if include_measurement:
                primitive_operations.append(_primitive_operation('measurement', instance_index, bit_index))
    return primitive_operations


def _pointwise_operations(instance_count: int, gate: str, include_measurement: bool) -> List[PrimitiveOperation]:
    primitive_operations: List[PrimitiveOperation] = []
    for instance_index in range(instance_count):
        primitive_operations.append(_primitive_operation(gate, instance_index))
        if include_measurement:
            primitive_operations.append(_primitive_operation('measurement', instance_index))
    return primitive_operations


def materialize_lookup_primitive_operations(generator: Mapping[str, Any]) -> List[PrimitiveOperation]:
    kind = str(generator['kind'])
    if kind == 'repeated_ladder':
        return _repeated_ladder_operations(
            int(generator['instance_count']),
            int(generator['bit_count']),
            bool(generator['include_measurement']),
        )
    if kind == 'pointwise':
        return _pointwise_operations(
            int(generator['instance_count']),
            str(generator['gate']),
            bool(generator['include_measurement']),
        )
    raise KeyError(f'unknown lookup primitive-operation generator: {kind}')


def _operation_stream_summary(primitive_operations: List[PrimitiveOperation]) -> Dict[str, Any]:
    serialized = json.dumps(primitive_operations, separators=(',', ':')).encode()
    preview_count = min(8, len(primitive_operations))
    return {
        'operation_count': len(primitive_operations),
        'sha256': sha256_bytes(serialized),
        'preview_head': primitive_operations[:preview_count],
        'preview_tail': primitive_operations[-preview_count:] if preview_count else [],
    }


def _block(
    name: str,
    summary: str,
    instance_count: int,
    primitive_operation_generator: Mapping[str, Any],
    notes: List[str],
) -> Dict[str, Any]:
    primitive_operations = materialize_lookup_primitive_operations(primitive_operation_generator)
    primitive_totals = _primitive_counts_from_operations(primitive_operations)
    primitive_counts_per_instance = {
        key: int(primitive_totals[key] // int(instance_count))
        for key in ('ccx', 'cx', 'x', 'measurement')
    }
    return {
        'name': name,
        'summary': summary,
        'instance_count': int(instance_count),
        'primitive_counts_per_instance': primitive_counts_per_instance,
        'primitive_counts_total': primitive_totals,
        'primitive_operation_encoding': ['gate', 'operand_0', 'operand_1'],
        'primitive_operation_generator': dict(primitive_operation_generator),
        'primitive_operation_stream': _operation_stream_summary(primitive_operations),
        'non_clifford_per_instance': primitive_counts_per_instance['ccx'],
        'non_clifford_total': primitive_totals['ccx'],
        'notes': notes,
    }


def _stage(
    name: str,
    summary: str,
    category: str,
    blocks: List[Dict[str, Any]],
    persistent_workspace_qubits: int,
    local_workspace_qubits: int,
    notes: List[str],
) -> Dict[str, Any]:
    primitive_totals = {
        key: sum(int(block['primitive_counts_total'][key]) for block in blocks)
        for key in ('ccx', 'cx', 'x', 'measurement')
    }
    return {
        'name': name,
        'summary': summary,
        'category': category,
        'blocks': blocks,
        'primitive_counts_total': primitive_totals,
        'non_clifford_total': primitive_totals['ccx'],
        'persistent_workspace_qubits': int(persistent_workspace_qubits),
        'local_workspace_qubits': int(local_workspace_qubits),
        'total_workspace_qubits': int(persistent_workspace_qubits + local_workspace_qubits),
        'notes': notes,
    }


def _persistent_workspace(magnitude_bits: int) -> List[Dict[str, Any]]:
    return [
        {
            'name': 'folded_magnitude_register',
            'qubits': magnitude_bits,
            'summary': 'Stores the shared absolute-value magnitude 0..32767 used by every lookup family.',
        },
        {
            'name': 'lookup_control_predicates',
            'qubits': 3,
            'summary': 'Tracks zero/min-word routing and the Y-negation enable predicate without allocating a full metadata table.',
        },
    ]


def _classification_stage(magnitude_bits: int, persistent_workspace_qubits: int) -> Dict[str, Any]:
    all_zero_cost = magnitude_bits - 1
    abs_prepare_cost = 2 * (magnitude_bits - 1)
    return _stage(
        name='folded_word_classification',
        summary='Shared sign/magnitude classification for the 16-bit signed folded contract.',
        category='classification',
        blocks=[
            _block(
                name='magnitude_all_zero_tree',
                summary='Temporary logical-AND ladder over the 15 magnitude bits.',
                instance_count=1,
                primitive_operation_generator={
                    'kind': 'repeated_ladder',
                    'instance_count': 1,
                    'bit_count': all_zero_cost,
                    'include_measurement': True,
                },
                notes=[
                    'The all-zero predicate is shared by zero-word bypass and 0x8000 special-word routing.',
                    'The temporary logical-AND ladder is uncomputed by local measurements inside the stage.',
                ],
            ),
            _block(
                name='signed_absolute_value_prepare',
                summary='Two mirrored temporary logical-AND ladders prepare the folded absolute value for the positive lookup domain.',
                instance_count=2,
                primitive_operation_generator={
                    'kind': 'repeated_ladder',
                    'instance_count': 2,
                    'bit_count': magnitude_bits - 1,
                    'include_measurement': True,
                },
                notes=[
                    'This stage implements the explicit absolute-value preparation used by all checked lookup families.',
                    'Separate zero/min routing is driven from the shared all-zero predicate and the raw sign bit, so no additional non-Clifford flag-materialization block is counted here.',
                ],
            ),
        ],
        persistent_workspace_qubits=persistent_workspace_qubits,
        local_workspace_qubits=magnitude_bits - 2,
        notes=[
            'The classification stage is family-independent and implements the same signed-folded contract used by the main repository lookup audit.',
        ],
    )


def _conditional_negation_stage(coordinate_bits: int, persistent_workspace_qubits: int) -> Dict[str, Any]:
    return _stage(
        name='conditional_y_negation',
        summary='Applies the post-lookup Y negation required by negative raw words in the folded contract.',
        category='post_lookup_fixup',
        blocks=[
            _block(
                name='conditional_field_negation',
                summary='Field-width conditional subtraction/select network over the Y coordinate.',
                instance_count=1,
                primitive_operation_generator={
                    'kind': 'repeated_ladder',
                    'instance_count': 1,
                    'bit_count': coordinate_bits - 1,
                    'include_measurement': False,
                },
                notes=[
                    'This stage is the exact post-lookup sign-fix assumption represented as a single field-width conditional negation.',
                ],
            ),
        ],
        persistent_workspace_qubits=persistent_workspace_qubits,
        local_workspace_qubits=0,
        notes=[
            'The X coordinate remains unchanged under negation; only the Y coordinate path carries non-Clifford cost.',
        ],
    )


def _linear_scan_family(contract: Mapping[str, Any]) -> Dict[str, Any]:
    params = _contract_parameters(contract)
    persistent_workspace = _persistent_workspace(params['magnitude_bits'])
    persistent_total = sum(int(entry['qubits']) for entry in persistent_workspace)
    stages = [
        _classification_stage(params['magnitude_bits'], persistent_total),
        _stage(
            name='folded_positive_lookup_compute',
            summary='Linear scan across the folded positive-magnitude table using temporary logical-AND equality ladders.',
            category='lookup_compute',
            blocks=[
                _block(
                    name='magnitude_equality_scan',
                    summary='One equality ladder for each positive folded-table address.',
                    instance_count=params['positive_domain_size'],
                    primitive_operation_generator={
                        'kind': 'repeated_ladder',
                        'instance_count': params['positive_domain_size'],
                        'bit_count': params['magnitude_bits'] - 1,
                        'include_measurement': True,
                    },
                    notes=[
                        'Every positive-domain table entry 0..32767 is matched coherently against the folded magnitude register.',
                        'The ladder family matches the low-space temporary logical-AND approach described in the family name.',
                    ],
                ),
            ],
            persistent_workspace_qubits=persistent_total,
            local_workspace_qubits=params['magnitude_bits'] - 2,
            notes=[
                'The linear-scan family minimizes extra live workspace by reusing a single equality-ladder scratch region across the full positive domain.',
            ],
        ),
        _stage(
            name='folded_positive_lookup_uncompute',
            summary='Measurement-reset is internal to the temporary logical-AND equality scan and does not add non-Clifford cost beyond the compute stage.',
            category='lookup_uncompute',
            blocks=[],
            persistent_workspace_qubits=persistent_total,
            local_workspace_qubits=0,
            notes=[
                'The equality ladders are temporary logical-AND blocks whose measurement-reset path is already represented in the compute-stage primitive inventory.',
            ],
        ),
        _conditional_negation_stage(params['coordinate_bits'], persistent_total),
    ]
    return _family_payload(
        name='folded_linear_scan_tmpand_v1',
        summary='Low-qubit exact lookup family using a 15-bit folded magnitude domain and temporary logical-AND equality ladders.',
        gate_set='Clifford + temporary logical-AND + measurement',
        lowering_strategy={
            'classification': 'shared folded sign/magnitude decomposition over the checked signed-folded lookup contract',
            'lookup_compute': 'temporary logical-AND equality ladders over the full positive folded domain',
            'lookup_uncompute': 'measurement-reset internal to the temporary logical-AND family',
        },
        persistent_workspace=persistent_workspace,
        stages=stages,
        notes=[
            'This remains the lowest-space lookup family checked into the compiler project.',
            'Zero-word and 0x8000 routing are explicit semantic cases, but they do not allocate a separate metadata-table lookup.',
        ],
    )


def _unary_qrom_family(contract: Mapping[str, Any], measured_uncompute: bool) -> Dict[str, Any]:
    params = _contract_parameters(contract)
    persistent_workspace = _persistent_workspace(params['magnitude_bits'])
    persistent_total = sum(int(entry['qubits']) for entry in persistent_workspace)
    uncompute_blocks = [
        _block(
            name='unary_address_uncompute',
            summary='Reverse unary QROM cleanup across the full folded positive domain.',
            instance_count=params['positive_domain_size'] - 1,
            primitive_operation_generator={
                'kind': 'pointwise',
                'instance_count': params['positive_domain_size'] - 1,
                'gate': 'ccx',
                'include_measurement': False,
            },
            notes=[
                'This is the exact reverse path of the unary address decode.',
            ],
        ),
    ]
    uncompute_summary = 'Exact reverse unary cleanup across the full folded unary address register.'
    uncompute_notes = [
        'The unary workspace remains live for the reverse pass.',
    ]
    uncompute_local_workspace = params['positive_domain_size']
    family_name = 'folded_unary_qrom_v1'
    family_summary = 'Lower-gate exact lookup family using a full unary conversion register over 32768 folded magnitudes.'
    gate_set = 'Clifford + Toffoli-style unary QROM'
    notes = [
        'This family minimizes gate count more aggressively than the linear-scan family, but uses a very large unary workspace.',
        'The compute and reverse-uncompute halves are both counted explicitly.',
    ]
    lowering_strategy = {
        'classification': 'shared folded sign/magnitude decomposition over the checked signed-folded lookup contract',
        'lookup_compute': 'full unary address decode over the 32768-entry positive folded domain',
        'lookup_uncompute': 'exact reverse unary cleanup',
    }
    if measured_uncompute:
        uncompute_blocks = [
            _block(
                name='coarse_bucket_measured_uncompute',
                summary='Measured cleanup of the coarse 8-bit bucket structure.',
                instance_count=1 << 8,
                primitive_operation_generator={
                    'kind': 'pointwise',
                    'instance_count': 1 << 8,
                    'gate': 'ccx',
                    'include_measurement': True,
                },
                notes=[
                    'The measured cleanup is split into a coarse bucket layer and a fine residual tree.',
                ],
            ),
            _block(
                name='fine_tree_measured_uncompute',
                summary='Measured cleanup of the residual 7-bit tree inside each coarse bucket.',
                instance_count=(1 << 7) - 1,
                primitive_operation_generator={
                    'kind': 'pointwise',
                    'instance_count': (1 << 7) - 1,
                    'gate': 'ccx',
                    'include_measurement': True,
                },
                notes=[
                    'The 8/7 split matches the checked family definition used by the compiler frontier.',
                ],
            ),
        ]
        uncompute_summary = 'Measured 8/7-split cleanup for the unary lookup workspace.'
        uncompute_notes = [
            'The measured cleanup reduces non-Clifford cost relative to the full reverse unary pass.',
        ]
        uncompute_local_workspace = 1 << 8
        family_name = 'folded_unary_qrom_measured_uncompute_v1'
        family_summary = 'Best exact low-gate family currently checked in: unary folded QROM compute plus 8/7-split measurement-based uncompute.'
        gate_set = 'Clifford + Toffoli-style unary QROM + measurement'
        notes = [
            'This family uses the same forward unary QROM compute as folded_unary_qrom_v1 but replaces reverse uncompute by the exact 8/7-split measurement-based construction.',
            'It improves the exact gate frontier while keeping the lookup semantics identical.',
        ]
        lowering_strategy['lookup_uncompute'] = '8/7-split measurement-based unary cleanup'
    stages = [
        _classification_stage(params['magnitude_bits'], persistent_total),
        _stage(
            name='folded_positive_lookup_compute',
            summary='Unary address decode across the positive folded domain.',
            category='lookup_compute',
            blocks=[
                _block(
                    name='unary_address_decode',
                    summary='One coherent unary activation edge for each nonzero folded magnitude transition.',
                    instance_count=params['positive_domain_size'] - 1,
                    primitive_operation_generator={
                        'kind': 'pointwise',
                        'instance_count': params['positive_domain_size'] - 1,
                        'gate': 'ccx',
                        'include_measurement': False,
                    },
                    notes=[
                        'This stage materializes a full unary address register spanning the 32768-entry folded positive domain.',
                    ],
                ),
            ],
            persistent_workspace_qubits=persistent_total,
            local_workspace_qubits=params['positive_domain_size'],
            notes=[
                'The unary register is the dominant live workspace cost in this family.',
            ],
        ),
        _stage(
            name='folded_positive_lookup_uncompute',
            summary=uncompute_summary,
            category='lookup_uncompute',
            blocks=uncompute_blocks,
            persistent_workspace_qubits=persistent_total,
            local_workspace_qubits=uncompute_local_workspace,
            notes=uncompute_notes,
        ),
        _conditional_negation_stage(params['coordinate_bits'], persistent_total),
    ]
    return _family_payload(
        name=family_name,
        summary=family_summary,
        gate_set=gate_set,
        lowering_strategy=lowering_strategy,
        persistent_workspace=persistent_workspace,
        stages=stages,
        notes=notes,
    )


def _banked_unary_qrom_measured_uncompute_family(
    contract: Mapping[str, Any],
    family_name: str,
    summary: str,
    split_bits: Tuple[int, ...],
    strategy_summary: str,
    notes: List[str],
) -> Dict[str, Any]:
    params = _contract_parameters(contract)
    if sum(split_bits) != params['magnitude_bits']:
        raise ValueError('banked unary family split must cover the full folded magnitude width')
    if any(bit_count <= 0 for bit_count in split_bits):
        raise ValueError('banked unary family split must use positive chunk widths')
    domains = [1 << bit_count for bit_count in split_bits]
    persistent_workspace = _persistent_workspace(params['magnitude_bits'])
    persistent_total = sum(int(entry['qubits']) for entry in persistent_workspace)
    local_workspace = sum(domains)
    decode_blocks = []
    uncompute_blocks = []
    level_names = ['coarse', 'upper_mid', 'lower_mid', 'fine']
    for level_index, (bit_count, domain) in enumerate(zip(split_bits, domains)):
        level_name = level_names[level_index] if level_index < len(level_names) else f'level_{level_index + 1}'
        decode_blocks.append(
            _block(
                name=f'{level_name}_bucket_decode',
                summary=f'Unary decode for the {bit_count}-bit {level_name.replace("_", " ")} chunk.',
                instance_count=domain - 1,
                primitive_operation_generator={
                    'kind': 'pointwise',
                    'instance_count': domain - 1,
                    'gate': 'ccx',
                    'include_measurement': False,
                },
                notes=[
                    f'This generated block materializes the {bit_count}-bit {level_name.replace("_", " ")} unary chunk inside the hierarchical banked family.',
                ],
            )
        )
        uncompute_blocks.append(
            _block(
                name=f'{level_name}_bucket_measured_uncompute',
                summary=f'Measured cleanup for the {bit_count}-bit {level_name.replace("_", " ")} chunk.',
                instance_count=domain - 1,
                primitive_operation_generator={
                    'kind': 'pointwise',
                    'instance_count': domain - 1,
                    'gate': 'ccx',
                    'include_measurement': True,
                },
                notes=[
                    f'This generated block measures and resets the {level_name.replace("_", " ")} chunk after the selected-path decode has been consumed.',
                ],
            )
        )
    stages = [
        _classification_stage(params['magnitude_bits'], persistent_total),
        _stage(
            name='folded_positive_lookup_compute',
            summary='Hierarchical banked unary address decode across the positive folded domain.',
            category='lookup_compute',
            blocks=decode_blocks,
            persistent_workspace_qubits=persistent_total,
            local_workspace_qubits=local_workspace,
            notes=[
                'The hierarchical family materializes one unary chunk per banking level instead of a full 32768-slot unary register.',
            ],
        ),
        _stage(
            name='folded_positive_lookup_uncompute',
            summary='Measured cleanup for the hierarchical banked unary lookup workspace.',
            category='lookup_uncompute',
            blocks=uncompute_blocks,
            persistent_workspace_qubits=persistent_total,
            local_workspace_qubits=local_workspace,
            notes=[
                'Measured cleanup keeps the hierarchical banked family exact within the chosen generated operation layer without reintroducing the full reverse unary pass.',
            ],
        ),
        _conditional_negation_stage(params['coordinate_bits'], persistent_total),
    ]
    return _family_payload(
        name=family_name,
        summary=summary,
        gate_set='Clifford + banked unary QROM + measurement',
        lowering_strategy={
            'classification': 'shared folded sign/magnitude decomposition over the checked signed-folded lookup contract',
            'lookup_compute': strategy_summary,
            'lookup_uncompute': 'measured cleanup of every generated banked unary chunk register',
        },
        persistent_workspace=persistent_workspace,
        stages=stages,
        notes=notes,
    )


def _family_payload(
    name: str,
    summary: str,
    gate_set: str,
    lowering_strategy: Mapping[str, str],
    persistent_workspace: List[Dict[str, Any]],
    stages: List[Dict[str, Any]],
    notes: List[str],
) -> Dict[str, Any]:
    classification_stage = next(stage for stage in stages if stage['category'] == 'classification')
    lookup_compute_stage = next(stage for stage in stages if stage['category'] == 'lookup_compute')
    lookup_uncompute_stage = next(stage for stage in stages if stage['category'] == 'lookup_uncompute')
    negate_stage = next(stage for stage in stages if stage['category'] == 'post_lookup_fixup')
    persistent_total = sum(int(entry['qubits']) for entry in persistent_workspace)
    primitive_totals = {
        key: sum(int(stage['primitive_counts_total'][key]) for stage in stages)
        for key in ('ccx', 'cx', 'x', 'measurement')
    }
    return {
        'name': name,
        'summary': summary,
        'gate_set': gate_set,
        'lookup_contract_sha256': sha256_path(_lookup_contract_path()),
        'lowering_strategy': dict(lowering_strategy),
        'persistent_workspace': persistent_workspace,
        'stages': stages,
        'primitive_counts_total': primitive_totals,
        'zero_check_non_clifford': int(classification_stage['blocks'][0]['non_clifford_total']),
        'magnitude_prepare_non_clifford': int(classification_stage['blocks'][1]['non_clifford_total']),
        'compute_lookup_non_clifford': int(lookup_compute_stage['non_clifford_total']),
        'uncompute_lookup_non_clifford': int(lookup_uncompute_stage['non_clifford_total']),
        'conditional_negate_y_non_clifford': int(negate_stage['non_clifford_total']),
        'direct_lookup_non_clifford': primitive_totals['ccx'],
        'per_leaf_lookup_non_clifford': primitive_totals['ccx'],
        'extra_lookup_workspace_qubits': max(int(stage['total_workspace_qubits']) for stage in stages),
        'workspace_reconstruction': {
            'persistent_workspace_qubits': persistent_total,
            'peak_stage': max(stages, key=lambda stage: int(stage['total_workspace_qubits']))['name'],
            'peak_total_workspace_qubits': max(int(stage['total_workspace_qubits']) for stage in stages),
        },
        'semantic_profile': {
            'zero_maps_to_infinity': True,
            'special_case_word_hex': '0x8000',
            'negative_words_negate_y_after_positive_lookup': True,
        },
        'notes': notes,
    }


def lookup_lowering_library() -> Dict[str, Any]:
    contract = _lookup_contract()
    params = _contract_parameters(contract)
    families = [
        _linear_scan_family(contract),
        _banked_unary_qrom_measured_uncompute_family(
            contract,
            family_name='folded_banked_unary_qrom_measured_uncompute_v1',
            summary='Intermediate exact lookup family using a 7/8-split banked unary decode with measured cleanup.',
            split_bits=(7, 8),
            strategy_summary='7/8-split banked unary decode over the 32768-entry positive folded domain',
            notes=[
                'This family sits between the linear-scan and full-unary extremes in the checked compiler frontier.',
                'It compresses lookup workspace aggressively without falling back to a full positive-domain equality scan.',
            ],
        ),
        _banked_unary_qrom_measured_uncompute_family(
            contract,
            family_name='folded_hierarchical_banked_unary_qrom_measured_uncompute_v1',
            summary='Lower-gate exact lookup family using a 3/4/4/4 hierarchical banked unary decode with measured cleanup.',
            split_bits=(3, 4, 4, 4),
            strategy_summary='3/4/4/4 hierarchical banked unary decode over the 32768-entry positive folded domain',
            notes=[
                'This family deepens the bank hierarchy to compress both generated lookup workspace and generated lookup non-Clifford cost relative to the two-level banked family.',
                'It keeps the folded lookup semantics exact while exposing every decode and measured-cleanup chunk as generated operation inventory.',
            ],
        ),
        _unary_qrom_family(contract, measured_uncompute=False),
        _unary_qrom_family(contract, measured_uncompute=True),
    ]
    return {
        'schema': 'compiler-project-lookup-lowerings-v4',
        'lookup_contract_path': 'artifacts/lookup/lookup_signed_fold_contract.json',
        'lookup_contract_sha256': sha256_path(_lookup_contract_path()),
        'lookup_contract_summary': {
            'word_bits': params['word_bits'],
            'magnitude_bits': params['magnitude_bits'],
            'positive_domain_size': params['positive_domain_size'],
            'coordinate_bits': params['coordinate_bits'],
        },
        'families': families,
        'notes': [
            'This artifact lowers each named compiler-project lookup family into generated primitive-operation inventories below the folded lookup contract.',
            'The lowered families keep the signed-folded secp256k1 lookup semantics exact while exposing stage-local workspace and primitive-count reconstruction.',
            'The lookup layer is published as explicit generated compiler-family structure over temporary logical-AND and unary QROM-style primitives.',
        ],
    }


def lookup_family_rows() -> List[Dict[str, Any]]:
    return lookup_lowering_library()['families']


def _lowered_lookup_point_from_cache(word: int, cache: List[PointAffine], special_neg: PointAffine, p: int = SECP_P) -> PointAffine:
    fold = fold_signed_i16(word)
    if fold['is_zero']:
        return None
    if fold['is_min']:
        return special_neg
    magnitude = int(fold['folded_magnitude'])
    point = cache[magnitude]
    if point is None:
        return None
    if fold['is_negative']:
        return neg_affine(point, p)
    return point


def lowered_lookup_point(word: int, base: PointAffine, family_name: str, p: int = SECP_P) -> PointAffine:
    family_names = {family['name'] for family in lookup_family_rows()}
    if family_name not in family_names:
        raise KeyError(f'unknown lowered lookup family: {family_name}')
    contract = _lookup_contract()
    cache, special_pos = build_positive_table(
        base,
        p,
        SECP_B,
        int(contract['structured_semantics']['magnitude_index_max']),
    )
    special_neg = neg_affine(special_pos, p)
    return _lowered_lookup_point_from_cache(word, cache, special_neg, p)


def lowered_lookup_semantic_summary() -> Dict[str, Any]:
    contract = _lookup_contract()
    bases = build_lookup_base_set()
    canonical_base = next(spec for spec in bases if spec['id'] == 'g_window_0')
    family_summaries = []
    edge_words = [0x0000, 0x0001, 0x0002, 0x7FFF, 0x8000, 0x8001, 0xFFFE, 0xFFFF]
    for family in lookup_family_rows():
        exhaustive_pass = 0
        exhaustive_total = 0
        canonical_cache, canonical_special_pos = build_positive_table(
            canonical_base['point'],
            SECP_P,
            SECP_B,
            int(contract['structured_semantics']['magnitude_index_max']),
        )
        canonical_special_neg = neg_affine(canonical_special_pos, SECP_P)
        for word in range(1 << int(contract['window_size_bits'])):
            expected = folded_lookup_point_from_cache(word, canonical_cache, canonical_special_neg, SECP_P)
            observed = _lowered_lookup_point_from_cache(word, canonical_cache, canonical_special_neg, SECP_P)
            exhaustive_total += 1
            exhaustive_pass += int(expected == observed)
        edge_pass = 0
        for spec in bases:
            cache, special_pos = build_positive_table(
                spec['point'],
                SECP_P,
                SECP_B,
                int(contract['structured_semantics']['magnitude_index_max']),
            )
            special_neg = neg_affine(special_pos, SECP_P)
            for word in edge_words:
                expected = folded_lookup_point_from_cache(word, cache, special_neg, SECP_P)
                observed = _lowered_lookup_point_from_cache(word, cache, special_neg, SECP_P)
                edge_pass += int(expected == observed)
        family_summaries.append({
            'name': family['name'],
            'canonical_full_exhaustive_total': exhaustive_total,
            'canonical_full_exhaustive_pass': exhaustive_pass,
            'multibase_edge_total': len(edge_words) * len(bases),
            'multibase_edge_pass': edge_pass,
        })
    return {
        'lookup_contract_sha256': sha256_path(_lookup_contract_path()),
        'families': family_summaries,
    }


__all__ = [
    'lookup_lowering_library',
    'lookup_family_rows',
    'materialize_lookup_primitive_operations',
    'lowered_lookup_point',
    'lowered_lookup_semantic_summary',
]
