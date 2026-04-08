#!/usr/bin/env python3

from __future__ import annotations

from typing import Any, Dict, List, Mapping


def _primitive_counts(ccx: int = 0, cx: int = 0, x: int = 0, measurement: int = 0) -> Dict[str, int]:
    return {
        'ccx': int(ccx),
        'cx': int(cx),
        'x': int(x),
        'measurement': int(measurement),
    }


def _primitive_block(
    block_id: str,
    summary: str,
    category: str,
    source_artifact: str,
    primitive_counts_per_instance: Mapping[str, int],
    base_instance_count: int,
    schedule_multiplier: int,
    metadata: Mapping[str, Any],
) -> Dict[str, Any]:
    primitive_totals = {
        key: int(schedule_multiplier) * int(base_instance_count) * int(primitive_counts_per_instance.get(key, 0))
        for key in ('ccx', 'cx', 'x', 'measurement')
    }
    return {
        'block_id': block_id,
        'summary': summary,
        'category': category,
        'source_artifact': source_artifact,
        'primitive_counts_per_instance': dict(primitive_counts_per_instance),
        'base_instance_count': int(base_instance_count),
        'schedule_multiplier': int(schedule_multiplier),
        'whole_oracle_instance_count': int(schedule_multiplier) * int(base_instance_count),
        'primitive_counts_total': primitive_totals,
        'non_clifford_total': primitive_totals['ccx'],
        'metadata': dict(metadata),
    }


def _qubit_block(
    block_id: str,
    summary: str,
    source_artifact: str,
    logical_qubits: int,
    metadata: Mapping[str, Any],
) -> Dict[str, Any]:
    return {
        'block_id': block_id,
        'summary': summary,
        'category': 'live_qubits',
        'source_artifact': source_artifact,
        'logical_qubits': int(logical_qubits),
        'metadata': dict(metadata),
    }


def _count_block(
    block_id: str,
    summary: str,
    category: str,
    source_artifact: str,
    count: int,
    metadata: Mapping[str, Any],
) -> Dict[str, Any]:
    return {
        'block_id': block_id,
        'summary': summary,
        'category': category,
        'source_artifact': source_artifact,
        'count': int(count),
        'metadata': dict(metadata),
    }


def _arithmetic_opcode_blocks(schedule: Mapping[str, Any], arithmetic_lowerings: Mapping[str, Any]) -> List[Dict[str, Any]]:
    leaf_calls = int(schedule['summary']['leaf_call_count_total'])
    hist = arithmetic_lowerings['leaf_reconstruction']['leaf_opcode_histogram']
    blocks = []
    for kernel in arithmetic_lowerings['kernels']:
        per_leaf_instances = int(hist.get(kernel['opcode'], 0))
        if per_leaf_instances == 0:
            continue
        for stage in kernel['stages']:
            for stage_block in stage['blocks']:
                blocks.append(
                    _primitive_block(
                        block_id=f'repeated_leaf_arithmetic__{kernel["opcode"]}__{stage["name"]}__{stage_block["name"]}',
                        summary=stage_block['summary'],
                        category='arithmetic_non_clifford',
                        source_artifact='compiler_verification_project/artifacts/arithmetic_lowerings.json',
                        primitive_counts_per_instance=stage_block['primitive_counts_per_instance'],
                        base_instance_count=per_leaf_instances * int(stage_block['instance_count']),
                        schedule_multiplier=leaf_calls,
                        metadata={
                            'opcode': kernel['opcode'],
                            'kernel_summary': kernel['summary'],
                            'kernel_non_clifford_per_instance': int(kernel['exact_non_clifford_per_kernel']),
                            'per_leaf_instance_count': per_leaf_instances,
                            'stage': stage['name'],
                            'stage_category': stage['category'],
                            'arithmetic_kernel_family': arithmetic_lowerings['family']['name'],
                        },
                    )
                )
    return blocks


def _lookup_blocks(schedule: Mapping[str, Any], lookup_family: Mapping[str, Any]) -> List[Dict[str, Any]]:
    leaf_calls = int(schedule['summary']['leaf_call_count_total'])
    blocks = []
    for invocation_scope, schedule_multiplier in (
        ('direct_seed', 1),
        ('repeated_leaf_calls', leaf_calls),
    ):
        for stage in lookup_family['stages']:
            for stage_block in stage['blocks']:
                blocks.append(
                    _primitive_block(
                        block_id=f'{invocation_scope}__{stage["name"]}__{stage_block["name"]}',
                        summary=stage_block['summary'],
                        category='lookup_non_clifford',
                        source_artifact='compiler_verification_project/artifacts/lookup_lowerings.json',
                        primitive_counts_per_instance=stage_block['primitive_counts_per_instance'],
                        base_instance_count=int(stage_block['instance_count']),
                        schedule_multiplier=schedule_multiplier,
                        metadata={
                            'lookup_family': lookup_family['name'],
                            'invocation_scope': invocation_scope,
                            'stage': stage['name'],
                            'stage_category': stage['category'],
                        },
                    )
                )
    return blocks


def _qubit_blocks(
    slot_allocation: Mapping[str, Any],
    lookup_family: Mapping[str, Any],
    phase_shell: Mapping[str, Any],
    field_bits: int,
) -> List[Dict[str, Any]]:
    arithmetic_slots = int(slot_allocation['allocator_summary']['exact_arithmetic_slot_count'])
    control_slots = int(slot_allocation['allocator_summary']['exact_control_slot_count'])
    return [
        _qubit_block(
            block_id='arithmetic_slot_register_file',
            summary='Exact live arithmetic slot register file for the checked ISA leaf.',
            source_artifact='compiler_verification_project/artifacts/exact_leaf_slot_allocation.json',
            logical_qubits=arithmetic_slots * int(field_bits),
            metadata={'arithmetic_slot_count': arithmetic_slots, 'field_bits': int(field_bits)},
        ),
        _qubit_block(
            block_id='control_slot_register_file',
            summary='Exact live control-slot register file for the checked ISA leaf.',
            source_artifact='compiler_verification_project/artifacts/exact_leaf_slot_allocation.json',
            logical_qubits=control_slots,
            metadata={'control_slot_count': control_slots},
        ),
        _qubit_block(
            block_id='lookup_workspace',
            summary='Peak explicit lookup workspace required by the named lowered lookup family.',
            source_artifact='compiler_verification_project/artifacts/lookup_lowerings.json',
            logical_qubits=int(lookup_family['extra_lookup_workspace_qubits']),
            metadata={'lookup_family': lookup_family['name']},
        ),
        _qubit_block(
            block_id='phase_shell_live_register',
            summary='Live phase-shell quantum register required by the named phase-shell family.',
            source_artifact='compiler_verification_project/artifacts/phase_shell_families.json',
            logical_qubits=int(phase_shell['live_quantum_bits']),
            metadata={'phase_shell': phase_shell['name']},
        ),
    ]


def _phase_shell_count_blocks(phase_shell: Mapping[str, Any]) -> List[Dict[str, Any]]:
    return [
        _count_block(
            block_id='phase_shell_measurements',
            summary='Adaptive phase-shell measurements recorded by the named phase-shell family.',
            category='phase_measurements',
            source_artifact='compiler_verification_project/artifacts/phase_shell_families.json',
            count=int(phase_shell['total_measurements']),
            metadata={'phase_shell': phase_shell['name']},
        ),
        _count_block(
            block_id='phase_shell_rotations',
            summary='Adaptive phase-shell rotations recorded by the named phase-shell family.',
            category='phase_rotations',
            source_artifact='compiler_verification_project/artifacts/phase_shell_families.json',
            count=int(phase_shell['adaptive_rotations']),
            metadata={'phase_shell': phase_shell['name']},
        ),
    ]


def _reconstruct_family(
    arithmetic_blocks: List[Dict[str, Any]],
    lookup_blocks: List[Dict[str, Any]],
    qubit_blocks: List[Dict[str, Any]],
    phase_count_blocks: List[Dict[str, Any]],
    schedule: Mapping[str, Any],
    slot_allocation: Mapping[str, Any],
    arithmetic_lowerings: Mapping[str, Any],
    lookup_family: Mapping[str, Any],
    phase_shell: Mapping[str, Any],
) -> Dict[str, Any]:
    leaf_calls = int(schedule['summary']['leaf_call_count_total'])
    primitive_totals = {
        key: sum(int(block['primitive_counts_total'][key]) for block in [*arithmetic_blocks, *lookup_blocks])
        for key in ('ccx', 'cx', 'x', 'measurement')
    }
    direct_seed_non_clifford = sum(
        int(block['primitive_counts_total']['ccx'])
        for block in lookup_blocks
        if block['metadata']['invocation_scope'] == 'direct_seed'
    )
    repeated_lookup_non_clifford = sum(
        int(block['primitive_counts_total']['ccx'])
        for block in lookup_blocks
        if block['metadata']['invocation_scope'] == 'repeated_leaf_calls'
    )
    total_measurements = primitive_totals['measurement'] + sum(
        int(block['count']) for block in phase_count_blocks if block['category'] == 'phase_measurements'
    )
    total_rotations = sum(int(block['count']) for block in phase_count_blocks if block['category'] == 'phase_rotations')
    return {
        'arithmetic_leaf_non_clifford': int(arithmetic_lowerings['leaf_reconstruction']['arithmetic_leaf_non_clifford']),
        'direct_seed_non_clifford': direct_seed_non_clifford,
        'per_leaf_lookup_non_clifford': repeated_lookup_non_clifford // leaf_calls,
        'full_oracle_non_clifford': primitive_totals['ccx'],
        'primitive_totals': primitive_totals,
        'total_measurements': total_measurements,
        'phase_shell_measurements': int(phase_shell['total_measurements']),
        'phase_shell_rotations': total_rotations,
        'arithmetic_slot_count': int(slot_allocation['allocator_summary']['exact_arithmetic_slot_count']),
        'control_slot_count': int(slot_allocation['allocator_summary']['exact_control_slot_count']),
        'lookup_workspace_qubits': int(lookup_family['extra_lookup_workspace_qubits']),
        'live_phase_bits': int(phase_shell['live_quantum_bits']),
        'total_logical_qubits': sum(int(block['logical_qubits']) for block in qubit_blocks),
    }


def build_generated_block_inventories(
    schedule: Mapping[str, Any],
    slot_allocation: Mapping[str, Any],
    kernel: Mapping[str, Any],
    arithmetic_lowerings: Mapping[str, Any],
    lookup_lowerings: Mapping[str, Any],
    phase_shells: List[Mapping[str, Any]],
    field_bits: int,
    public_google_baseline: Mapping[str, Any],
) -> Dict[str, Any]:
    arithmetic_blocks = _arithmetic_opcode_blocks(schedule, arithmetic_lowerings)
    family_inventories = []
    for lookup_family in lookup_lowerings['families']:
        for phase_shell in phase_shells:
            lookup_blocks = _lookup_blocks(schedule, lookup_family)
            qubit_blocks = _qubit_blocks(slot_allocation, lookup_family, phase_shell, field_bits)
            phase_count_blocks = _phase_shell_count_blocks(phase_shell)
            reconstruction = _reconstruct_family(
                arithmetic_blocks=arithmetic_blocks,
                lookup_blocks=lookup_blocks,
                qubit_blocks=qubit_blocks,
                phase_count_blocks=phase_count_blocks,
                schedule=schedule,
                slot_allocation=slot_allocation,
                arithmetic_lowerings=arithmetic_lowerings,
                lookup_family=lookup_family,
                phase_shell=phase_shell,
            )
            family_inventories.append(
                {
                    'name': f"{lookup_family['name']}__{phase_shell['name']}",
                    'summary': f"{lookup_family['summary']} / {phase_shell['summary']}",
                    'arithmetic_kernel_family': kernel['name'],
                    'lookup_family': lookup_family['name'],
                    'phase_shell': phase_shell['name'],
                    'non_clifford_blocks': arithmetic_blocks + lookup_blocks,
                    'qubit_blocks': qubit_blocks,
                    'phase_count_blocks': phase_count_blocks,
                    'reconstruction': reconstruction,
                }
            )
    best_gate = min(
        family_inventories,
        key=lambda row: (
            int(row['reconstruction']['full_oracle_non_clifford']),
            int(row['reconstruction']['total_logical_qubits']),
        ),
    )
    best_qubit = min(
        family_inventories,
        key=lambda row: (
            int(row['reconstruction']['total_logical_qubits']),
            int(row['reconstruction']['full_oracle_non_clifford']),
        ),
    )
    return {
        'schema': 'compiler-project-generated-block-inventories-v1',
        'public_google_baseline': dict(public_google_baseline),
        'schedule_summary': dict(schedule['summary']),
        'arithmetic_lowering_family': arithmetic_lowerings['family'],
        'shared_arithmetic_blocks': arithmetic_blocks,
        'families': family_inventories,
        'best_gate_family': {
            'name': best_gate['name'],
            'reconstruction': best_gate['reconstruction'],
        },
        'best_qubit_family': {
            'name': best_qubit['name'],
            'reconstruction': best_qubit['reconstruction'],
        },
        'notes': [
            'This artifact records generated whole-oracle block inventories for every named compiler family and reconstructs totals from those inventories.',
            'The structure follows a compositional call-graph style accounting layer: shared arithmetic blocks, family-specific lookup blocks, qubit contributors, and phase-shell counts.',
        ],
    }
