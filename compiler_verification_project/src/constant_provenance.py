#!/usr/bin/env python3

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


CONSTANT_PROVENANCE_SCHEMA = 'compiler-project-constant-provenance-v1'


@dataclass(frozen=True)
class SourceDocument:
    artifact: str
    payload: Mapping[str, Any]


def _pointer_get(payload: Any, pointer: str) -> Any:
    current = payload
    for raw_part in pointer.strip('/').split('/'):
        part = raw_part.replace('~1', '/').replace('~0', '~')
        if isinstance(current, Sequence) and not isinstance(current, (str, bytes, bytearray)):
            current = current[int(part)]
        elif isinstance(current, Mapping):
            current = current[part]
        else:
            raise KeyError(pointer)
    return current


def _find_named_row(payload: Mapping[str, Any], collection_pointer: str, name: str) -> tuple[int, Mapping[str, Any]]:
    rows = _pointer_get(payload, collection_pointer)
    for index, row in enumerate(rows):
        if row['name'] == name:
            return index, row
    raise KeyError(name)


def _consumer(
    *,
    name: str,
    document: SourceDocument,
    pointer: str,
    expected: Any,
) -> dict[str, Any]:
    observed = _pointer_get(document.payload, pointer)
    return {
        'name': name,
        'artifact': document.artifact,
        'pointer': pointer,
        'expected': expected,
        'observed': observed,
        'pass': observed == expected,
    }


def _source(
    *,
    name: str,
    document: SourceDocument,
    pointer: str,
    consumers: list[dict[str, Any]],
) -> dict[str, Any]:
    value = _pointer_get(document.payload, pointer)
    return {
        'name': name,
        'source_artifact': document.artifact,
        'source_pointer': pointer,
        'value': value,
        'consumers': consumers,
        'pass': all(row['pass'] for row in consumers),
    }


def _forbidden_literal_scan(repo_root: Path) -> list[dict[str, Any]]:
    patterns = [
        {
            'name': 'zkp_phase_shell_hadamards_literal',
            'path': 'compiler_verification_project/src/zkp_attestation.py',
            'regex': r"'phase_shell_hadamards'\s*:\s*512\b",
        },
        {
            'name': 'zkp_phase_shell_measurements_literal',
            'path': 'compiler_verification_project/src/zkp_attestation.py',
            'regex': r"'phase_shell_measurements'\s*:\s*512\b",
        },
        {
            'name': 'zkp_phase_shell_rotations_literal',
            'path': 'compiler_verification_project/src/zkp_attestation.py',
            'regex': r"'phase_shell_rotations'\s*:\s*511\b",
        },
        {
            'name': 'zkp_phase_shell_rotation_depth_literal',
            'path': 'compiler_verification_project/src/zkp_attestation.py',
            'regex': r"'phase_shell_rotation_depth'\s*:\s*511\b",
        },
        {
            'name': 'zkp_total_measurements_zero_literal',
            'path': 'compiler_verification_project/src/zkp_attestation.py',
            'regex': r"'total_measurements'\s*:\s*0\b",
        },
    ]
    scans = []
    for pattern in patterns:
        source = (repo_root / pattern['path']).read_text()
        matches = [
            {'line': source[:match.start()].count('\n') + 1, 'text': match.group(0)}
            for match in re.finditer(pattern['regex'], source)
        ]
        scans.append({
            **pattern,
            'match_count': len(matches),
            'matches': matches,
            'pass': not matches,
        })
    return scans


def _source_ast_literals(repo_root: Path, relative_path: str) -> dict[str, Any]:
    tree = ast.parse((repo_root / relative_path).read_text())
    constants: dict[str, list[dict[str, Any]]] = {}
    tracked = {
        'phase_shell_hadamards',
        'phase_shell_measurements',
        'phase_shell_rotations',
        'phase_shell_rotation_depth',
        'total_measurements',
        'full_oracle_non_clifford',
        'total_logical_qubits',
        'lookup_workspace_qubits',
    }
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key_node, value_node in zip(node.keys, node.values):
            if not isinstance(key_node, ast.Constant) or key_node.value not in tracked:
                continue
            if isinstance(value_node, ast.Constant) and isinstance(value_node.value, int):
                constants.setdefault(str(key_node.value), []).append({
                    'line': value_node.lineno,
                    'value': value_node.value,
                })
    return {
        'path': relative_path,
        'tracked_keys': sorted(tracked),
        'integer_literals': constants,
        'pass': not constants,
    }


def build_constant_provenance(
    *,
    repo_root: Path,
    compiler_parameters: Mapping[str, Any],
    phase_shell_lowerings: Mapping[str, Any],
    reusable_chunk_lowering: Mapping[str, Any],
    zkp_attestation_input: Mapping[str, Any],
    public_headline_result: Mapping[str, Any],
    headline_resource_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    compiler = SourceDocument(
        'compiler_verification_project/artifacts/compiler_parameters.json',
        compiler_parameters,
    )
    phase_shells = SourceDocument(
        'compiler_verification_project/artifacts/phase_shell_lowerings.json',
        phase_shell_lowerings,
    )
    reusable = SourceDocument(
        'compiler_verification_project/artifacts/reusable_chunk_lowering.json',
        reusable_chunk_lowering,
    )
    zkp = SourceDocument(
        'compiler_verification_project/artifacts/zkp_attestation_reusable_chunk_candidate/zkp_attestation_input.json',
        zkp_attestation_input,
    )
    public = SourceDocument(
        'compiler_verification_project/artifacts/public_headline_result.json',
        public_headline_result,
    )
    headline_manifest = SourceDocument(
        'compiler_verification_project/artifacts/headline_resource_manifest.json',
        headline_resource_manifest,
    )
    selected_shell = str(_pointer_get(compiler.payload, '/phase_shell/selected_public_shell'))
    selected_shell_index, selected_shell_row = _find_named_row(phase_shells.payload, '/families', selected_shell)
    shell_base_pointer = f'/families/{selected_shell_index}'
    family_name = str(_pointer_get(zkp.payload, '/selected_family_name'))
    rows = [
        _source(
            name='selected_phase_shell_name',
            document=compiler,
            pointer='/phase_shell/selected_public_shell',
            consumers=[
                _consumer(name='zkp_family_phase_shell', document=zkp, pointer='/family_document/payload/phase_shell', expected=selected_shell),
            ],
        ),
        _source(
            name='phase_register_bits',
            document=compiler,
            pointer='/phase_shell/full_phase_register_bits',
            consumers=[
                _consumer(name='phase_shell_lowering_register_bits', document=phase_shells, pointer='/phase_register_bits', expected=_pointer_get(compiler.payload, '/phase_shell/full_phase_register_bits')),
            ],
        ),
    ]
    for source_key, family_key in (
        ('hadamard_count', 'phase_shell_hadamards'),
        ('measurement_count', 'phase_shell_measurements'),
        ('rotation_count', 'phase_shell_rotations'),
        ('rotation_depth', 'phase_shell_rotation_depth'),
        ('total_measurements', 'total_measurements'),
    ):
        expected = selected_shell_row[source_key]
        rows.append(
            _source(
                name=f'semiclassical_{family_key}',
                document=phase_shells,
                pointer=f'{shell_base_pointer}/{source_key}',
                consumers=[
                    _consumer(name='zkp_family_document', document=zkp, pointer=f'/family_document/payload/{family_key}', expected=expected),
                ],
            )
        )
    rows.extend([
        _source(
            name='candidate_total_non_clifford',
            document=reusable,
            pointer='/non_clifford_derivation/candidate_total_non_clifford',
            consumers=[
                _consumer(name='zkp_family_document', document=zkp, pointer='/family_document/payload/full_oracle_non_clifford', expected=_pointer_get(reusable.payload, '/non_clifford_derivation/candidate_total_non_clifford')),
                _consumer(name='public_headline_result', document=public, pointer='/selected_result/non_clifford', expected=_pointer_get(reusable.payload, '/non_clifford_derivation/candidate_total_non_clifford')),
                _consumer(name='headline_resource_manifest', document=headline_manifest, pointer='/public_totals/non_clifford', expected=_pointer_get(reusable.payload, '/non_clifford_derivation/candidate_total_non_clifford')),
            ],
        ),
        _source(
            name='candidate_total_logical_qubits',
            document=reusable,
            pointer='/qubit_derivation/candidate_total_logical_qubits',
            consumers=[
                _consumer(name='zkp_family_document', document=zkp, pointer='/family_document/payload/total_logical_qubits', expected=_pointer_get(reusable.payload, '/qubit_derivation/candidate_total_logical_qubits')),
                _consumer(name='public_headline_result', document=public, pointer='/selected_result/logical_qubits', expected=_pointer_get(reusable.payload, '/qubit_derivation/candidate_total_logical_qubits')),
                _consumer(name='headline_resource_manifest', document=headline_manifest, pointer='/public_totals/logical_qubits', expected=_pointer_get(reusable.payload, '/qubit_derivation/candidate_total_logical_qubits')),
            ],
        ),
        _source(
            name='candidate_family_name',
            document=zkp,
            pointer='/selected_family_name',
            consumers=[
                _consumer(name='zkp_family_document', document=zkp, pointer='/family_document/payload/name', expected=family_name),
                _consumer(name='public_headline_result', document=public, pointer='/selected_result/name', expected=family_name),
                _consumer(name='headline_resource_manifest', document=headline_manifest, pointer='/selected_family_name', expected=family_name),
            ],
        ),
        _source(
            name='non_clifford_public_limit',
            document=compiler,
            pointer='/public_headline_policy/non_clifford_limit_exclusive',
            consumers=[
                _consumer(name='public_selection_policy', document=public, pointer='/selection_policy/limits/non_clifford_limit_exclusive', expected=_pointer_get(compiler.payload, '/public_headline_policy/non_clifford_limit_exclusive')),
            ],
        ),
        _source(
            name='logical_qubit_public_limit',
            document=compiler,
            pointer='/public_headline_policy/logical_qubit_limit_exclusive',
            consumers=[
                _consumer(name='public_selection_policy', document=public, pointer='/selection_policy/limits/logical_qubit_limit_exclusive', expected=_pointer_get(compiler.payload, '/public_headline_policy/logical_qubit_limit_exclusive')),
            ],
        ),
    ])
    forbidden_literals = _forbidden_literal_scan(repo_root)
    ast_literal_audits = [
        _source_ast_literals(repo_root, 'compiler_verification_project/src/zkp_attestation.py'),
    ]
    checks = {
        'all_source_rows_match_consumers': all(row['pass'] for row in rows),
        'forbidden_historic_literals_absent': all(row['pass'] for row in forbidden_literals),
        'tracked_zkp_family_resource_fields_are_not_integer_literals': all(row['pass'] for row in ast_literal_audits),
        'candidate_beats_public_limits': (
            _pointer_get(reusable.payload, '/non_clifford_derivation/candidate_total_non_clifford')
            < _pointer_get(compiler.payload, '/public_headline_policy/non_clifford_limit_exclusive')
            and _pointer_get(reusable.payload, '/qubit_derivation/candidate_total_logical_qubits')
            < _pointer_get(compiler.payload, '/public_headline_policy/logical_qubit_limit_exclusive')
        ),
    }
    return {
        'schema': CONSTANT_PROVENANCE_SCHEMA,
        'scope': 'release-critical constants and headline resource counts',
        'source_rows': rows,
        'forbidden_literal_scan': forbidden_literals,
        'ast_literal_audits': ast_literal_audits,
        'checks': checks,
        'pass': all(checks.values()),
        'boundary': {
            'purpose': 'This artifact prevents release-critical ZKP/headline constants from drifting into unchecked literals.',
            'not_a_replacement_for': [
                'primitive Clifford-complete circuit generation',
                'fresh compressed or Groth16 proof generation',
            ],
        },
    }


__all__ = [
    'CONSTANT_PROVENANCE_SCHEMA',
    'build_constant_provenance',
]
