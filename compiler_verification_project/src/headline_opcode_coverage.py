#!/usr/bin/env python3

from __future__ import annotations

from typing import Any, Dict, List, Mapping


ZKP_PREPARED_KIND_BY_OPCODE = {
    'load_input': 'copy',
    'lookup_meta': 'copy',
    'bool_from_flag': 'bool_from_flag',
    'complete_a0_all_streamed_tail': 'complete_a0_all_streamed_tail',
}

OPCODE_POLICIES = {
    'load_input': {
        'policy': 'field_interface_copy',
        'requires_subcircuit_equivalence': False,
        'requires_arithmetic_lowering': False,
        'requires_edge_case_leaf_equivalence': True,
    },
    'lookup_meta': {
        'policy': 'lookup_metadata_copy',
        'requires_subcircuit_equivalence': False,
        'requires_arithmetic_lowering': False,
        'requires_edge_case_leaf_equivalence': True,
    },
    'bool_from_flag': {
        'policy': 'control_flag_extract',
        'requires_subcircuit_equivalence': True,
        'requires_arithmetic_lowering': False,
        'requires_edge_case_leaf_equivalence': True,
    },
    'complete_a0_all_streamed_tail': {
        'policy': 'counted_arithmetic_macro',
        'requires_subcircuit_equivalence': True,
        'requires_arithmetic_lowering': True,
        'requires_edge_case_leaf_equivalence': True,
    },
}


def _leaf_opcode_histogram(leaf: Mapping[str, Any]) -> Dict[str, int]:
    histogram: Dict[str, int] = {}
    for instruction in leaf['instructions']:
        opcode = str(instruction['op'])
        histogram[opcode] = histogram.get(opcode, 0) + 1
    return dict(sorted(histogram.items()))


def _leaf_pcs_by_opcode(leaf: Mapping[str, Any]) -> Dict[str, List[int]]:
    pcs: Dict[str, List[int]] = {}
    for instruction in leaf['instructions']:
        opcode = str(instruction['op'])
        pcs.setdefault(opcode, []).append(int(instruction['pc']))
    return {opcode: sorted(rows) for opcode, rows in sorted(pcs.items())}


def _subcircuit_opcode_rows(subcircuit_equivalence: Mapping[str, Any]) -> Dict[str, Mapping[str, Any]]:
    rows = subcircuit_equivalence['arithmetic_opcode_equivalence']['per_opcode']
    return {str(row['opcode']): row for row in rows}


def _arithmetic_kernel_rows(arithmetic_lowerings: Mapping[str, Any]) -> Dict[str, Mapping[str, Any]]:
    return {str(row['opcode']): row for row in arithmetic_lowerings['kernels']}


def _edge_case_summary(streamed_lookup_tail_leaf_equivalence: Mapping[str, Any]) -> Dict[str, Any]:
    summary = streamed_lookup_tail_leaf_equivalence['summary']
    return {
        'total': int(summary['total']),
        'pass': int(summary['pass']),
        'categories': {
            category: {'total': int(row['total']), 'pass': int(row['pass'])}
            for category, row in sorted(summary['categories'].items())
        },
    }


def _edge_cases_pass(edge_cases: Mapping[str, Any]) -> bool:
    return (
        int(edge_cases['total']) > 0
        and int(edge_cases['pass']) == int(edge_cases['total'])
        and all(int(row['total']) > 0 and int(row['pass']) == int(row['total']) for row in edge_cases['categories'].values())
    )


def _liveness_opcode_pcs(resource_liveness_certificate: Mapping[str, Any]) -> Dict[str, List[int]]:
    pcs: Dict[str, List[int]] = {}
    for row in resource_liveness_certificate['flat_leaf_liveness']['per_pc']:
        pcs.setdefault(str(row['opcode']), []).append(int(row['pc']))
    return {opcode: sorted(rows) for opcode, rows in sorted(pcs.items())}


def _macro_leaf_sigma_rows(resource_liveness_certificate: Mapping[str, Any], opcode: str) -> Dict[str, Any]:
    prefix = f'arithmetic_opcode__{opcode}__'
    rows = [
        row
        for row in resource_liveness_certificate['primitive_oracle_ir']['leaf_sigma']
        if str(row['leaf_id']).startswith(prefix)
    ]
    return {
        'row_count': len(rows),
        'whole_oracle_non_clifford': sum(int(row['primitive_counts_total']['ccx']) for row in rows),
    }


def build_headline_opcode_coverage(
    *,
    leaf: Mapping[str, Any],
    streamed_lookup_tail_leaf_equivalence: Mapping[str, Any],
    subcircuit_equivalence: Mapping[str, Any],
    arithmetic_lowerings: Mapping[str, Any],
    resource_liveness_certificate: Mapping[str, Any],
) -> Dict[str, Any]:
    histogram = _leaf_opcode_histogram(leaf)
    pcs_by_opcode = _leaf_pcs_by_opcode(leaf)
    subcircuit_rows = _subcircuit_opcode_rows(subcircuit_equivalence)
    arithmetic_rows = _arithmetic_kernel_rows(arithmetic_lowerings)
    liveness_pcs = _liveness_opcode_pcs(resource_liveness_certificate)
    edge_cases = _edge_case_summary(streamed_lookup_tail_leaf_equivalence)
    edge_cases_pass = _edge_cases_pass(edge_cases)
    rows = []
    for opcode, count in histogram.items():
        policy = OPCODE_POLICIES.get(opcode)
        zkp_prepared_kind = ZKP_PREPARED_KIND_BY_OPCODE.get(opcode)
        subcircuit_row = subcircuit_rows.get(opcode)
        arithmetic_row = arithmetic_rows.get(opcode)
        liveness_opcode_pcs = liveness_pcs.get(opcode, [])
        has_policy = policy is not None
        has_zkp_prepared_kind = zkp_prepared_kind is not None
        liveness_covers_all_pcs = liveness_opcode_pcs == pcs_by_opcode[opcode]
        subcircuit_pass = (
            subcircuit_row is not None
            and int(subcircuit_row['total']) > 0
            and int(subcircuit_row['pass']) == int(subcircuit_row['total'])
        )
        arithmetic_lowering_non_clifford = (
            None if arithmetic_row is None else int(arithmetic_row['exact_non_clifford_per_kernel'])
        )
        requires_subcircuit_equivalence = bool(policy and policy['requires_subcircuit_equivalence'])
        requires_arithmetic_lowering = bool(policy and policy['requires_arithmetic_lowering'])
        requires_edge_case_leaf_equivalence = bool(policy and policy['requires_edge_case_leaf_equivalence'])
        resource_lowering_pass = (
            arithmetic_lowering_non_clifford is not None and arithmetic_lowering_non_clifford > 0
        ) if requires_arithmetic_lowering else arithmetic_row is None
        subcircuit_coverage_pass = subcircuit_pass if requires_subcircuit_equivalence else True
        edge_case_coverage_pass = edge_cases_pass if requires_edge_case_leaf_equivalence else True
        macro_leaf_sigma = _macro_leaf_sigma_rows(resource_liveness_certificate, opcode)
        macro_resource_rows_pass = (
            macro_leaf_sigma['row_count'] > 0 and macro_leaf_sigma['whole_oracle_non_clifford'] > 0
        ) if requires_arithmetic_lowering else True
        passes_required_coverage = all((
            has_policy,
            has_zkp_prepared_kind,
            liveness_covers_all_pcs,
            subcircuit_coverage_pass,
            edge_case_coverage_pass,
            resource_lowering_pass,
            macro_resource_rows_pass,
        ))
        rows.append({
            'opcode': opcode,
            'instruction_count': count,
            'pcs': pcs_by_opcode[opcode],
            'policy': None if policy is None else policy['policy'],
            'zkp_prepared_kind': zkp_prepared_kind,
            'liveness_pcs': liveness_opcode_pcs,
            'liveness_covers_all_pcs': liveness_covers_all_pcs,
            'subcircuit_equivalence': None if subcircuit_row is None else {
                'total': int(subcircuit_row['total']),
                'pass': int(subcircuit_row['pass']),
            },
            'requires_subcircuit_equivalence': requires_subcircuit_equivalence,
            'requires_arithmetic_lowering': requires_arithmetic_lowering,
            'arithmetic_lowering_non_clifford_per_kernel': arithmetic_lowering_non_clifford,
            'macro_leaf_sigma': macro_leaf_sigma,
            'requires_edge_case_leaf_equivalence': requires_edge_case_leaf_equivalence,
            'passes_required_coverage': passes_required_coverage,
        })
    return {
        'schema': 'compiler-project-headline-opcode-coverage-v1',
        'leaf_variant': leaf['variant'],
        'headline_opcode_histogram': histogram,
        'edge_case_leaf_equivalence': edge_cases,
        'rows': rows,
        'all_headline_opcodes_have_policy': all(row['policy'] is not None for row in rows),
        'all_headline_opcodes_have_zkp_prepared_kind': all(row['zkp_prepared_kind'] is not None for row in rows),
        'all_headline_opcode_pcs_have_liveness_rows': all(row['liveness_covers_all_pcs'] for row in rows),
        'all_required_opcode_coverage_passes': all(row['passes_required_coverage'] for row in rows),
        'notes': [
            'This artifact is a release guard against adding a headline executable opcode without a declared proof/resource policy.',
            'Interface-copy opcodes are zero-non-Clifford policies but still require ZKP preparation, whole-leaf edge-case equivalence, and liveness rows.',
            'Counted arithmetic opcodes additionally require subcircuit equivalence, arithmetic lowering, and primitive leaf-sigma rows in the resource certificate.',
        ],
    }


__all__ = ['build_headline_opcode_coverage']
