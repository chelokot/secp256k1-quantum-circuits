#!/usr/bin/env python3

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Mapping, Optional, Tuple


def _node(node_id: str, kind: str, category: str, summary: str, metadata: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        'id': node_id,
        'kind': kind,
        'category': category,
        'summary': summary,
        'metadata': dict(metadata),
    }


def _edge(src: str, dst: str, count: int, category: str, summary: str) -> Dict[str, Any]:
    return {
        'src': src,
        'dst': dst,
        'count': int(count),
        'category': category,
        'summary': summary,
    }


def _primitive_leaf_profile(block: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        'resource_semantics': 'additive_primitive',
        'primitive_counts_per_instance': dict(block['primitive_counts_per_instance']),
        'base_instance_count': int(block['instance_count']),
    }


def _qubit_leaf_profile(logical_qubits: int) -> Dict[str, Any]:
    return {
        'resource_semantics': 'peak_live_qubits',
        'logical_qubits': int(logical_qubits),
    }


def _count_leaf_profile(count: int, category: str) -> Dict[str, Any]:
    return {
        'resource_semantics': f'additive_{category}',
        'count': int(count),
    }


def _traverse_graph(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]], root_id: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    node_lookup = {node['id']: node for node in nodes}
    outgoing: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    incoming: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for edge in edges:
        outgoing[edge['src']].append(edge)
        incoming[edge['dst']].append(edge)
    leaf_sigma: List[Dict[str, Any]] = []
    max_depth = 0
    seen_nodes = set()
    stack = set()

    def visit(node_id: str, multiplicity: int, depth: int, path: Tuple[str, ...]) -> None:
        nonlocal max_depth
        if node_id in stack:
            raise ValueError(f'cycle detected at {node_id}')
        stack.add(node_id)
        seen_nodes.add(node_id)
        node = node_lookup[node_id]
        max_depth = max(max_depth, depth)
        if node['kind'] == 'leaf':
            profile = node['metadata']['resource_profile']
            entry = {
                'leaf_id': node_id,
                'category': node['category'],
                'path': list(path + (node_id,)),
                'path_multiplicity': int(multiplicity),
                'resource_profile': profile,
            }
            semantics = profile['resource_semantics']
            if semantics == 'additive_primitive':
                totals = {
                    key: int(multiplicity) * int(profile['base_instance_count']) * int(profile['primitive_counts_per_instance'].get(key, 0))
                    for key in ('ccx', 'cx', 'x', 'measurement')
                }
                entry['primitive_counts_total'] = totals
                entry['non_clifford_total'] = totals['ccx']
            elif semantics == 'peak_live_qubits':
                entry['logical_qubits_total'] = int(multiplicity) * int(profile['logical_qubits'])
            else:
                entry['count_total'] = int(multiplicity) * int(profile['count'])
            leaf_sigma.append(entry)
        else:
            for edge in outgoing.get(node_id, []):
                visit(edge['dst'], int(multiplicity) * int(edge['count']), depth + 1, path + (node_id,))
        stack.remove(node_id)

    visit(root_id, 1, 0, tuple())
    primitive_totals = {'ccx': 0, 'cx': 0, 'x': 0, 'measurement': 0}
    logical_qubits_total = 0
    phase_shell_hadamards = 0
    phase_shell_measurements = 0
    phase_shell_rotations = 0
    phase_shell_rotation_depth = 0
    for entry in leaf_sigma:
        profile = entry['resource_profile']
        semantics = profile['resource_semantics']
        if semantics == 'additive_primitive':
            for key in primitive_totals:
                primitive_totals[key] += int(entry['primitive_counts_total'][key])
        elif semantics == 'peak_live_qubits':
            logical_qubits_total += int(entry['logical_qubits_total'])
        elif semantics == 'additive_phase_hadamards':
            phase_shell_hadamards += int(entry['count_total'])
        elif semantics == 'additive_phase_measurements':
            phase_shell_measurements += int(entry['count_total'])
        elif semantics == 'additive_phase_rotations':
            phase_shell_rotations += int(entry['count_total'])
        elif semantics == 'additive_phase_rotation_depth':
            phase_shell_rotation_depth += int(entry['count_total'])
    return leaf_sigma, {
        'node_count': len(nodes),
        'edge_count': len(edges),
        'leaf_node_count': sum(1 for node in nodes if node['kind'] == 'leaf'),
        'reachable_node_count': len(seen_nodes),
        'max_depth': max_depth,
        'root_in_degree': len(incoming[root_id]),
        'primitive_totals': primitive_totals,
        'logical_qubits_total': logical_qubits_total,
        'phase_shell_hadamards': phase_shell_hadamards,
        'phase_shell_measurements': phase_shell_measurements,
        'phase_shell_rotations': phase_shell_rotations,
        'phase_shell_rotation_depth': phase_shell_rotation_depth,
    }


def _arithmetic_branch(
    arithmetic_lowerings: Mapping[str, Any],
    leaf_call_count: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], str]:
    hist = arithmetic_lowerings['leaf_reconstruction']['leaf_opcode_histogram']
    nodes = [
        _node(
            'repeated_leaf_calls',
            'composite',
            'schedule_bundle',
            'Bundle covering the 31 repeated raw-window leaf invocations after the direct seed.',
            {'leaf_call_count': int(leaf_call_count)},
        ),
        _node(
            'leaf_arithmetic_cluster',
            'composite',
            'arithmetic_cluster',
            'Per-leaf arithmetic cluster composed from opcode bundles and explicit stage/block lowerings.',
            {'arithmetic_kernel_family': arithmetic_lowerings['family']['name']},
        ),
    ]
    edges = [
        _edge('full_oracle', 'repeated_leaf_calls', leaf_call_count, 'schedule_call', 'Repeat the leaf-call bundle once for each non-seed raw window.'),
        _edge('repeated_leaf_calls', 'leaf_arithmetic_cluster', 1, 'cluster_call', 'Each repeated leaf invocation includes one arithmetic cluster.'),
    ]
    for kernel in arithmetic_lowerings['kernels']:
        per_leaf_instances = int(hist.get(kernel['opcode'], 0))
        if per_leaf_instances == 0:
            continue
        opcode_id = f'arithmetic_opcode__{kernel["opcode"]}'
        nodes.append(
            _node(
                opcode_id,
                'composite',
                'opcode_bundle',
                kernel['summary'],
                {
                    'opcode': kernel['opcode'],
                    'per_leaf_instance_count': per_leaf_instances,
                    'exact_non_clifford_per_kernel': int(kernel['exact_non_clifford_per_kernel']),
                },
            )
        )
        edges.append(
            _edge(
                'leaf_arithmetic_cluster',
                opcode_id,
                per_leaf_instances,
                'opcode_call',
                f'Invoke the {kernel["opcode"]} kernel once for each occurrence inside the checked leaf.',
            )
        )
        for stage in kernel['stages']:
            stage_id = f'{opcode_id}__stage__{stage["name"]}'
            nodes.append(
                _node(
                    stage_id,
                    'composite',
                    'stage_bundle',
                    stage['summary'],
                    {
                        'opcode': kernel['opcode'],
                        'stage': stage['name'],
                        'stage_category': stage['category'],
                    },
                )
            )
            edges.append(
                _edge(opcode_id, stage_id, 1, 'stage_call', 'Invoke the stage once inside each kernel instance.')
            )
            for block in stage['blocks']:
                leaf_id = f'{stage_id}__leaf__{block["name"]}'
                nodes.append(
                    _node(
                        leaf_id,
                        'leaf',
                        'primitive_block',
                        block['summary'],
                        {
                            'source_artifact': 'compiler_verification_project/artifacts/arithmetic_lowerings.json',
                            'opcode': kernel['opcode'],
                            'stage': stage['name'],
                            'resource_profile': _primitive_leaf_profile(block),
                        },
                    )
                )
                edges.append(
                    _edge(stage_id, leaf_id, 1, 'leaf_block', 'Emit the primitive counted leaf block for this lowered stage.')
                )
    return nodes, edges, 'repeated_leaf_calls'


def _lookup_branch(
    lookup_family: Mapping[str, Any],
    leaf_call_count: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
    scope_rows = [
        ('direct_seed_lookup', 1, 'direct_seed'),
        ('repeated_lookup_cluster', leaf_call_count, 'repeated_leaf_calls'),
    ]
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    roots: List[str] = []
    for scope_id, scope_count, invocation_scope in scope_rows:
        nodes.append(
            _node(
                scope_id,
                'composite',
                'lookup_scope',
                f'{lookup_family["summary"]} for the {invocation_scope} invocation scope.',
                {
                    'lookup_family': lookup_family['name'],
                    'invocation_scope': invocation_scope,
                },
            )
        )
        roots.append(scope_id)
        edges.append(
            _edge(
                'full_oracle' if invocation_scope == 'direct_seed' else 'repeated_leaf_calls',
                scope_id,
                scope_count if invocation_scope == 'direct_seed' else 1,
                'lookup_scope_call',
                'Apply the lowered lookup family within this oracle scope.',
            )
        )
        for stage in lookup_family['stages']:
            stage_id = f'{scope_id}__stage__{stage["name"]}'
            nodes.append(
                _node(
                    stage_id,
                    'composite',
                    'stage_bundle',
                    stage['summary'],
                    {
                        'lookup_family': lookup_family['name'],
                        'invocation_scope': invocation_scope,
                        'stage': stage['name'],
                        'stage_category': stage['category'],
                    },
                )
            )
            edges.append(
                _edge(scope_id, stage_id, 1, 'stage_call', 'Invoke the stage once per lookup invocation in this scope.')
            )
            for block in stage['blocks']:
                leaf_id = f'{stage_id}__leaf__{block["name"]}'
                nodes.append(
                    _node(
                        leaf_id,
                        'leaf',
                        'primitive_block',
                        block['summary'],
                        {
                            'source_artifact': 'compiler_verification_project/artifacts/lookup_lowerings.json',
                            'lookup_family': lookup_family['name'],
                            'invocation_scope': invocation_scope,
                            'stage': stage['name'],
                            'resource_profile': _primitive_leaf_profile(block),
                        },
                    )
                )
                edges.append(
                    _edge(stage_id, leaf_id, 1, 'leaf_block', 'Emit the primitive counted leaf block for this lowered lookup stage.')
                )
    return nodes, edges, roots


def _qubit_and_phase_branches(
    slot_allocation: Mapping[str, Any],
    lookup_family: Mapping[str, Any],
    phase_shell: Mapping[str, Any],
    field_bits: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
    arithmetic_slots = int(slot_allocation['allocator_summary']['exact_arithmetic_slot_count'])
    control_slots = int(slot_allocation['allocator_summary']['exact_control_slot_count'])
    borrowed_field_slots = int(slot_allocation['allocator_summary'].get('exact_borrowed_field_slot_count', 0))
    slot_source_artifact = str(
        slot_allocation.get('source_artifact', 'compiler_verification_project/artifacts/exact_leaf_slot_allocation.json')
    )
    nodes = [
        _node(
            'live_qubit_contributors',
            'composite',
            'peak_live_qubits',
            'Peak live logical-qubit contributors for the named compiler family.',
            {},
        ),
        _node(
            'phase_shell_counts',
            'composite',
            'phase_shell_counts',
            'Additive phase-shell counts for the named phase-shell family.',
            {'phase_shell': phase_shell['name']},
        ),
        _node(
            'live_qubit_contributors__arithmetic_slots',
            'leaf',
            'live_qubits',
            'Exact live arithmetic slot register file for the checked ISA leaf.',
            {
                'source_artifact': slot_source_artifact,
                'resource_profile': _qubit_leaf_profile(arithmetic_slots * int(field_bits)),
            },
        ),
        _node(
            'live_qubit_contributors__control_slots',
            'leaf',
            'live_qubits',
            'Exact live control-slot register file for the checked ISA leaf.',
            {
                'source_artifact': slot_source_artifact,
                'resource_profile': _qubit_leaf_profile(control_slots),
            },
        ),
        *(
            [
                _node(
                    'live_qubit_contributors__borrowed_lookup_interface_field_lanes',
                    'leaf',
                    'live_qubits',
                    'Counted field-width lookup interface lanes borrowed by the selected leaf contract.',
                    {
                        'source_artifact': slot_source_artifact,
                        'resource_profile': _qubit_leaf_profile(borrowed_field_slots * int(field_bits)),
                    },
                )
            ]
            if borrowed_field_slots
            else []
        ),
        _node(
            'live_qubit_contributors__lookup_workspace',
            'leaf',
            'live_qubits',
            'Peak explicit lookup workspace required by the named lowered lookup family.',
            {
                'source_artifact': 'compiler_verification_project/artifacts/lookup_lowerings.json',
                'resource_profile': _qubit_leaf_profile(int(lookup_family['extra_lookup_workspace_qubits'])),
            },
        ),
        _node(
            'live_qubit_contributors__phase_shell_live_register',
            'leaf',
            'live_qubits',
            'Live phase-shell quantum register required by the named phase-shell family.',
            {
                'source_artifact': 'compiler_verification_project/artifacts/phase_shell_lowerings.json',
                'resource_profile': _qubit_leaf_profile(int(phase_shell['live_quantum_bits'])),
            },
        ),
        _node(
            'phase_shell_counts__hadamards',
            'leaf',
            'phase_hadamards',
            'Phase-shell Hadamard basis changes recorded by the named phase-shell family.',
            {
                'source_artifact': 'compiler_verification_project/artifacts/phase_shell_lowerings.json',
                'resource_profile': _count_leaf_profile(int(phase_shell['hadamard_count']), 'phase_hadamards'),
            },
        ),
        _node(
            'phase_shell_counts__measurements',
            'leaf',
            'phase_measurements',
            'Phase-shell terminal measurements recorded by the named phase-shell family.',
            {
                'source_artifact': 'compiler_verification_project/artifacts/phase_shell_lowerings.json',
                'resource_profile': _count_leaf_profile(int(phase_shell['total_measurements']), 'phase_measurements'),
            },
        ),
        _node(
            'phase_shell_counts__rotations',
            'leaf',
            'phase_rotations',
            'Phase-shell dyadic rotations recorded by the named phase-shell family.',
            {
                'source_artifact': 'compiler_verification_project/artifacts/phase_shell_lowerings.json',
                'resource_profile': _count_leaf_profile(int(phase_shell['total_rotations']), 'phase_rotations'),
            },
        ),
        _node(
            'phase_shell_counts__rotation_depth',
            'leaf',
            'phase_rotation_depth',
            'Phase-shell rotation-depth contribution recorded by the named phase-shell family.',
            {
                'source_artifact': 'compiler_verification_project/artifacts/phase_shell_lowerings.json',
                'resource_profile': _count_leaf_profile(int(phase_shell['rotation_depth']), 'phase_rotation_depth'),
            },
        ),
    ]
    edges = [
        _edge('full_oracle', 'live_qubit_contributors', 1, 'qubit_contributor_bundle', 'Collect the simultaneous live-qubit contributors for the named compiler family.'),
        _edge('full_oracle', 'phase_shell_counts', 1, 'phase_count_bundle', 'Collect the additive phase-shell counters for the named compiler family.'),
        _edge('live_qubit_contributors', 'live_qubit_contributors__arithmetic_slots', 1, 'live_qubit_leaf', 'Include the arithmetic slot register file once.'),
        _edge('live_qubit_contributors', 'live_qubit_contributors__control_slots', 1, 'live_qubit_leaf', 'Include the control slot register file once.'),
        *(
            [
                _edge(
                    'live_qubit_contributors',
                    'live_qubit_contributors__borrowed_lookup_interface_field_lanes',
                    1,
                    'live_qubit_leaf',
                    'Include counted borrowed lookup interface field lanes once.',
                )
            ]
            if borrowed_field_slots
            else []
        ),
        _edge('live_qubit_contributors', 'live_qubit_contributors__lookup_workspace', 1, 'live_qubit_leaf', 'Include the lookup workspace once.'),
        _edge('live_qubit_contributors', 'live_qubit_contributors__phase_shell_live_register', 1, 'live_qubit_leaf', 'Include the live phase-shell register once.'),
        _edge('phase_shell_counts', 'phase_shell_counts__hadamards', 1, 'phase_count_leaf', 'Emit the phase-shell Hadamard total once.'),
        _edge('phase_shell_counts', 'phase_shell_counts__measurements', 1, 'phase_count_leaf', 'Emit the phase-shell measurement total once.'),
        _edge('phase_shell_counts', 'phase_shell_counts__rotations', 1, 'phase_count_leaf', 'Emit the phase-shell rotation total once.'),
        _edge('phase_shell_counts', 'phase_shell_counts__rotation_depth', 1, 'phase_count_leaf', 'Emit the phase-shell rotation-depth total once.'),
    ]
    return nodes, edges, ['live_qubit_contributors', 'phase_shell_counts']


def _family_ft_ir(
    schedule: Mapping[str, Any],
    slot_allocation: Mapping[str, Any],
    arithmetic_lowerings: Mapping[str, Any],
    lookup_family: Mapping[str, Any],
    phase_shell: Mapping[str, Any],
    generated_family: Mapping[str, Any],
    frontier_family: Optional[Mapping[str, Any]],
    field_bits: int,
) -> Dict[str, Any]:
    leaf_call_count = int(schedule['summary']['leaf_call_count_total'])
    nodes = [
        _node(
            'full_oracle',
            'composite',
            'oracle_root',
            generated_family['summary'],
            {
                'family_name': generated_family['name'],
                'lookup_family': lookup_family['name'],
                'phase_shell': phase_shell['name'],
                'arithmetic_kernel_family': arithmetic_lowerings['family']['name'],
            },
        ),
    ]
    edges: List[Dict[str, Any]] = []
    arithmetic_nodes, arithmetic_edges, _ = _arithmetic_branch(arithmetic_lowerings, leaf_call_count)
    lookup_nodes, lookup_edges, _ = _lookup_branch(lookup_family, leaf_call_count)
    qubit_nodes, qubit_edges, _ = _qubit_and_phase_branches(slot_allocation, lookup_family, phase_shell, field_bits)
    nodes.extend(arithmetic_nodes)
    nodes.extend(lookup_nodes)
    nodes.extend(qubit_nodes)
    edges.extend(arithmetic_edges)
    edges.extend(lookup_edges)
    edges.extend(qubit_edges)
    leaf_sigma, graph_summary = _traverse_graph(nodes, edges, 'full_oracle')
    reconstruction = {
        'full_oracle_non_clifford': int(graph_summary['primitive_totals']['ccx']),
        'primitive_totals': graph_summary['primitive_totals'],
        'total_logical_qubits': int(graph_summary['logical_qubits_total']),
        'phase_shell_hadamards': int(graph_summary['phase_shell_hadamards']),
        'phase_shell_measurements': int(graph_summary['phase_shell_measurements']),
        'phase_shell_rotations': int(graph_summary['phase_shell_rotations']),
        'phase_shell_rotation_depth': int(graph_summary['phase_shell_rotation_depth']),
    }
    return {
        'name': generated_family['name'],
        'summary': generated_family['summary'],
        'lookup_family': lookup_family['name'],
        'phase_shell': phase_shell['name'],
        'arithmetic_kernel_family': arithmetic_lowerings['family']['name'],
        'graph': {
            'root': 'full_oracle',
            'nodes': nodes,
            'edges': edges,
            'summary': graph_summary,
        },
        'leaf_sigma': leaf_sigma,
        'reconstruction': reconstruction,
        'generated_block_inventory_reconstruction': {
            'full_oracle_non_clifford': int(generated_family['reconstruction']['full_oracle_non_clifford']),
            'primitive_totals': generated_family['reconstruction']['primitive_totals'],
            'total_logical_qubits': int(generated_family['reconstruction']['total_logical_qubits']),
            'phase_shell_hadamards': int(generated_family['reconstruction']['phase_shell_hadamards']),
            'phase_shell_measurements': int(generated_family['reconstruction']['phase_shell_measurements']),
            'phase_shell_rotations': int(generated_family['reconstruction']['phase_shell_rotations']),
            'phase_shell_rotation_depth': int(generated_family['reconstruction']['phase_shell_rotation_depth']),
        },
        'frontier_reconstruction': {
            'full_oracle_non_clifford': int(
                generated_family['reconstruction']['full_oracle_non_clifford']
                if frontier_family is None
                else frontier_family['full_oracle_non_clifford']
            ),
            'total_logical_qubits': int(
                generated_family['reconstruction']['total_logical_qubits']
                if frontier_family is None
                else frontier_family['total_logical_qubits']
            ),
        },
    }


def build_ft_ir_compositions(
    schedule: Mapping[str, Any],
    slot_allocation: Mapping[str, Any],
    arithmetic_lowerings: Mapping[str, Any],
    lookup_lowerings: Mapping[str, Any],
    phase_shells: List[Mapping[str, Any]],
    generated_block_inventories: Mapping[str, Any],
    frontier: Optional[Mapping[str, Any]],
    field_bits: int,
) -> Dict[str, Any]:
    lookup_family_rows = {row['name']: row for row in lookup_lowerings['families']}
    phase_shell_rows = {row['name']: row for row in phase_shells}
    frontier_rows = {} if frontier is None else {row['name']: row for row in frontier['families']}
    families = []
    for generated_family in generated_block_inventories['families']:
        lookup_family = lookup_family_rows[generated_family['lookup_family']]
        phase_shell = phase_shell_rows[generated_family['phase_shell']]
        families.append(
            _family_ft_ir(
                schedule=schedule,
                slot_allocation=slot_allocation,
                arithmetic_lowerings=arithmetic_lowerings,
                lookup_family=lookup_family,
                phase_shell=phase_shell,
                generated_family=generated_family,
                frontier_family=frontier_rows.get(generated_family['name']),
                field_bits=field_bits,
            )
        )
    return {
        'schema': 'compiler-project-ft-ir-v1',
        'source_artifacts': {
            'full_raw32_oracle': 'compiler_verification_project/artifacts/full_raw32_oracle.json',
            'exact_leaf_slot_allocation': str(
                slot_allocation.get('source_artifact', 'compiler_verification_project/artifacts/exact_leaf_slot_allocation.json')
            ),
            'arithmetic_lowerings': 'compiler_verification_project/artifacts/arithmetic_lowerings.json',
            'lookup_lowerings': 'compiler_verification_project/artifacts/lookup_lowerings.json',
            'phase_shell_lowerings': 'compiler_verification_project/artifacts/phase_shell_lowerings.json',
            'generated_block_inventories': 'compiler_verification_project/artifacts/generated_block_inventories.json',
            'family_frontier': 'compiler_verification_project/artifacts/family_frontier.json',
        },
        'source_references': [
            {
                'title': 'Qualtran call graph protocol',
                'url': 'https://qualtran.readthedocs.io/en/latest/resource_counting/call_graph.html',
                'reason': 'Reference design for hierarchical subroutine accounting and leaf-count sigma extraction.',
            },
            {
                'title': 'Qualtran protocols overview',
                'url': 'https://qualtran.readthedocs.io/en/latest/Protocols.html',
                'reason': 'Reference for decomposition plus call-graph style composition over named quantum subroutines.',
            },
        ],
        'schedule_summary': dict(schedule['summary']),
        'families': families,
        'best_gate_family': generated_block_inventories['best_gate_family'],
        'best_qubit_family': generated_block_inventories['best_qubit_family'],
        'notes': [
            'This artifact expresses each named compiler family as a compositional FT-style call graph with hierarchical bundles and a traversed leaf sigma.',
            'The leaf sigma reconstructs primitive totals, live-qubit contributors, and exact phase-shell lowering counts from the FT IR rather than from the flattened generated block inventory.',
        ],
    }


__all__ = ['build_ft_ir_compositions']
