from __future__ import annotations

import json
from pathlib import Path

from support import ensure_compiler_project_build_summary, ensure_compiler_project_verification_summary


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_ft_ir() -> dict:
    ensure_compiler_project_build_summary()
    ensure_compiler_project_verification_summary()
    path = REPO_ROOT / 'compiler_verification_project' / 'artifacts' / 'ft_ir_compositions.json'
    return json.loads(path.read_text())


def test_ft_ir_graphs_are_rooted_and_reconstruct_counts() -> None:
    ft_ir = _load_ft_ir()
    for family in ft_ir['families']:
        graph = family['graph']
        summary = graph['summary']
        assert graph['root'] == 'full_oracle'
        assert summary['root_in_degree'] == 0
        assert summary['reachable_node_count'] == summary['node_count']
        assert summary['leaf_node_count'] > 0
        assert summary['max_depth'] > 0
        assert family['reconstruction'] == family['generated_block_inventory_reconstruction']
        assert family['reconstruction']['full_oracle_non_clifford'] == family['frontier_reconstruction']['full_oracle_non_clifford']
        assert family['reconstruction']['total_logical_qubits'] == family['frontier_reconstruction']['total_logical_qubits']


def test_ft_ir_leaf_sigma_has_all_resource_kinds() -> None:
    ft_ir = _load_ft_ir()
    family = ft_ir['families'][0]
    semantics = {entry['resource_profile']['resource_semantics'] for entry in family['leaf_sigma']}
    assert 'additive_primitive' in semantics
    assert 'peak_live_qubits' in semantics
    assert 'additive_phase_measurements' in semantics
    assert 'additive_phase_rotations' in semantics
