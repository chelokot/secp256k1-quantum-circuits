#!/usr/bin/env python3

from __future__ import annotations

import json
import hashlib
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ROOT_SRC = PROJECT_ROOT / 'src'
if str(ROOT_SRC) not in sys.path:
    sys.path.insert(0, str(ROOT_SRC))

from common import (  # noqa: E402
    SECP_B,
    SECP_G,
    SECP_N,
    SECP_P,
    affine_to_proj,
    deterministic_scalars,
    dump_json,
    mul_fixed_window,
    precompute_window_tables,
    proj_to_affine,
    sha256_bytes,
)
from lookup_fed_leaf import build_lookup_fed_leaf  # noqa: E402
from project import compiler_family_frontier, project_artifact_path, raw32_schedule  # noqa: E402
from verifier import exec_netlist  # noqa: E402

DEFAULT_CASE_COUNT = 8
DIGEST_SCHEME = 'compiler-project-semantic-json-sha256-v1'
CASE_SEED_SCHEME = 'compiler-project-leaf-canonical-json-sha256-v1'


def _canonical_json(payload: Mapping[str, Any] | List[Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def _semantic_hash_feed(hasher: 'hashlib._Hash', value: Any) -> None:
    if value is None:
        hasher.update(b'n')
        return
    if isinstance(value, bool):
        hasher.update(b't' if value else b'f')
        return
    if isinstance(value, int):
        encoded = str(value).encode('ascii')
        hasher.update(b'i')
        hasher.update(len(encoded).to_bytes(8, 'big'))
        hasher.update(encoded)
        return
    if isinstance(value, float):
        encoded = json.dumps(value, allow_nan=False, ensure_ascii=True, separators=(',', ':')).encode('ascii')
        hasher.update(b'i')
        hasher.update(len(encoded).to_bytes(8, 'big'))
        hasher.update(encoded)
        return
    if isinstance(value, str):
        encoded = value.encode('utf-8')
        hasher.update(b's')
        hasher.update(len(encoded).to_bytes(8, 'big'))
        hasher.update(encoded)
        return
    if isinstance(value, list):
        hasher.update(b'l')
        hasher.update(len(value).to_bytes(8, 'big'))
        for item in value:
            _semantic_hash_feed(hasher, item)
        return
    if isinstance(value, dict):
        hasher.update(b'o')
        keys = sorted(value)
        hasher.update(len(keys).to_bytes(8, 'big'))
        for key in keys:
            _semantic_hash_feed(hasher, str(key))
            _semantic_hash_feed(hasher, value[key])
        return
    raise TypeError(f'unsupported semantic hash value: {type(value)!r}')


def _semantic_payload_sha256(document_type: str, payload: Mapping[str, Any] | List[Any]) -> str:
    hasher = hashlib.sha256()
    hasher.update(DIGEST_SCHEME.encode('ascii'))
    hasher.update(b'\0')
    hasher.update(document_type.encode('utf-8'))
    hasher.update(b'\0')
    _semantic_hash_feed(hasher, payload)
    return hasher.hexdigest()


def _committed_payload(
    *,
    document_type: str,
    artifact_path: str,
    payload: Mapping[str, Any] | List[Any],
) -> Dict[str, Any]:
    return {
        'document_type': document_type,
        'artifact_path': artifact_path,
        'digest_scheme': DIGEST_SCHEME,
        'sha256': _semantic_payload_sha256(document_type, payload),
        'payload': payload,
    }


def _resolve_family(frontier: Mapping[str, Any], family_name: str) -> Dict[str, Any]:
    if family_name == 'best-gate':
        return dict(frontier['best_gate_family'])
    if family_name == 'best-qubit':
        return dict(frontier['best_qubit_family'])
    for row in frontier['families']:
        if row['name'] == family_name:
            return dict(row)
    raise KeyError(f'unknown compiler family: {family_name}')


def _family_proof_payload(family: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        'name': str(family['name']),
        'summary': str(family['summary']),
        'gate_set': str(family['gate_set']),
        'phase_shell': str(family['phase_shell']),
        'slot_allocation_family': str(family['slot_allocation_family']),
        'arithmetic_kernel_family': str(family['arithmetic_kernel_family']),
        'lookup_family': str(family['lookup_family']),
        'arithmetic_leaf_non_clifford': int(family['arithmetic_leaf_non_clifford']),
        'direct_seed_non_clifford': int(family['direct_seed_non_clifford']),
        'per_leaf_lookup_non_clifford': int(family['per_leaf_lookup_non_clifford']),
        'full_oracle_non_clifford': int(family['full_oracle_non_clifford']),
        'arithmetic_slot_count': int(family['arithmetic_slot_count']),
        'control_slot_count': int(family['control_slot_count']),
        'borrowed_interface_qubits': int(family.get('borrowed_interface_qubits', 0)),
        'lookup_workspace_qubits': int(family['lookup_workspace_qubits']),
        'live_phase_bits': int(family['live_phase_bits']),
        'total_logical_qubits': int(family['total_logical_qubits']),
        'phase_shell_hadamards': int(family['phase_shell_hadamards']),
        'phase_shell_measurements': int(family['phase_shell_measurements']),
        'phase_shell_rotations': int(family['phase_shell_rotations']),
        'phase_shell_rotation_depth': int(family['phase_shell_rotation_depth']),
        'total_measurements': int(family['total_measurements']),
        'notes': list(family['notes']),
    }


def _leaf_for_family(family: Mapping[str, Any]) -> Dict[str, Any]:
    slot_family = str(family['slot_allocation_family'])
    if slot_family == 'lookup_fed_leaf_v1':
        return build_lookup_fed_leaf()
    if slot_family == 'materialized_lookup_leaf_v1':
        return build_lookup_fed_leaf()
    raise KeyError(f'unsupported attested leaf slot family: {slot_family}')


def _leaf_commitment_metadata(family: Mapping[str, Any]) -> tuple[str, str]:
    slot_family = str(family['slot_allocation_family'])
    if slot_family == 'lookup_fed_leaf_v1':
        return 'lookup_fed_leaf', 'compiler_verification_project/artifacts/lookup_fed_leaf.json'
    if slot_family == 'materialized_lookup_leaf_v1':
        return 'lookup_fed_leaf', 'compiler_verification_project/artifacts/lookup_fed_leaf.json'
    raise KeyError(f'unsupported attested leaf slot family: {slot_family}')


def _point_payload(point: Optional[tuple[int, int]]) -> Optional[Dict[str, str]]:
    if point is None:
        return None
    return {
        'x_hex': format(point[0], '064x'),
        'y_hex': format(point[1], '064x'),
    }


def _source_as_pair(source: Any) -> tuple[str, str]:
    if isinstance(source, list) and len(source) == 2 and all(isinstance(item, str) for item in source):
        return source[0], source[1]
    raise TypeError(f'expected pair source, got {source!r}')


def _source_as_register(source: Any) -> str:
    if isinstance(source, str):
        return source
    raise TypeError(f'expected register source, got {source!r}')


def _source_as_flag(source: Any) -> tuple[str, int]:
    if isinstance(source, dict) and set(source) == {'flags', 'bit'}:
        return str(source['flags']), int(source['bit'])
    raise TypeError(f'expected flag source, got {source!r}')


def _source_as_lookup(source: Any) -> tuple[str, str]:
    if isinstance(source, dict) and set(source) == {'table', 'key'}:
        return str(source['table']), str(source['key'])
    raise TypeError(f'expected lookup source, got {source!r}')


def _ensure_defined_register(
    register_ids: Dict[str, int],
    defined: set[str],
    name: str,
    context: str,
) -> int:
    if name not in defined:
        raise KeyError(f'missing {context} register: {name}')
    return register_ids[name]


def _compile_leaf_for_proof(leaf: Mapping[str, Any]) -> Dict[str, Any]:
    register_ids = {
        name: index
        for index, name in enumerate(
            ['Q.X', 'Q.Y', 'Q.Z', 'k', 'lookup_x', 'lookup_y', 'lookup_meta', 'qx', 'qy', 'qz']
        )
    }
    defined = {'Q.X', 'Q.Y', 'Q.Z', 'k', 'lookup_x', 'lookup_y', 'lookup_meta'}
    compiled_instructions: List[Dict[str, Any]] = []
    for instruction in sorted(leaf['instructions'], key=lambda row: int(row['pc'])):
        dst_name = str(instruction['dst'])
        dst = register_ids.setdefault(dst_name, len(register_ids))
        op = str(instruction['op'])
        source = instruction.get('src')
        if op == 'load_input':
            src_name = _source_as_register(source)
            compiled_instructions.append({
                'kind': 'copy',
                'dst': dst,
                'src': _ensure_defined_register(register_ids, defined, src_name, 'load_input source'),
            })
        elif op == 'lookup_affine_x':
            table, key = _source_as_lookup(source)
            assert table == 'T.x'
            assert key == 'k'
            compiled_instructions.append({
                'kind': 'copy',
                'dst': dst,
                'src': register_ids['lookup_x'],
            })
        elif op == 'lookup_affine_y':
            table, key = _source_as_lookup(source)
            assert table == 'T.y'
            assert key == 'k'
            compiled_instructions.append({
                'kind': 'copy',
                'dst': dst,
                'src': register_ids['lookup_y'],
            })
        elif op == 'lookup_meta':
            table, key = _source_as_lookup(source)
            assert table == 'T.meta'
            assert key == 'k'
            compiled_instructions.append({
                'kind': 'copy',
                'dst': dst,
                'src': register_ids['lookup_meta'],
            })
        elif op == 'bool_from_flag':
            flags_name, bit = _source_as_flag(source)
            compiled_instructions.append({
                'kind': 'bool_from_flag',
                'dst': dst,
                'flags': _ensure_defined_register(register_ids, defined, flags_name, 'bool_from_flag flags'),
                'bit': bit,
            })
        elif op == 'clear_bool_from_flag':
            if dst_name not in defined:
                raise KeyError(f'missing clear_bool_from_flag destination register: {dst_name}')
            flags_name, bit = _source_as_flag(source)
            compiled_instructions.append({
                'kind': 'clear_bool_from_flag',
                'dst': dst,
                'flags': _ensure_defined_register(register_ids, defined, flags_name, 'clear_bool_from_flag flags'),
                'bit': bit,
            })
        elif op == 'field_mul':
            left_name, right_name = _source_as_pair(source)
            compiled_instructions.append({
                'kind': 'field_mul',
                'dst': dst,
                'left': _ensure_defined_register(register_ids, defined, left_name, 'field_mul lhs'),
                'right': _ensure_defined_register(register_ids, defined, right_name, 'field_mul rhs'),
            })
        elif op == 'field_add':
            left_name, right_name = _source_as_pair(source)
            compiled_instructions.append({
                'kind': 'field_add',
                'dst': dst,
                'left': _ensure_defined_register(register_ids, defined, left_name, 'field_add lhs'),
                'right': _ensure_defined_register(register_ids, defined, right_name, 'field_add rhs'),
            })
        elif op == 'field_sub':
            left_name, right_name = _source_as_pair(source)
            compiled_instructions.append({
                'kind': 'field_sub',
                'dst': dst,
                'left': _ensure_defined_register(register_ids, defined, left_name, 'field_sub lhs'),
                'right': _ensure_defined_register(register_ids, defined, right_name, 'field_sub rhs'),
            })
        elif op == 'mul_const':
            src_name = _source_as_register(source)
            compiled_instructions.append({
                'kind': 'mul_const',
                'dst': dst,
                'src': _ensure_defined_register(register_ids, defined, src_name, 'mul_const source'),
                'constant': int(instruction['const']),
            })
        elif op == 'select_field_if_flag':
            when_nonzero_name, when_zero_name = _source_as_pair(source)
            flag_name = str(instruction['flag'])
            compiled_instructions.append({
                'kind': 'select_field_if_flag',
                'dst': dst,
                'flag': _ensure_defined_register(register_ids, defined, flag_name, 'select_field_if_flag flag'),
                'when_nonzero': _ensure_defined_register(
                    register_ids, defined, when_nonzero_name, 'select_field_if_flag nonzero source'
                ),
                'when_zero': _ensure_defined_register(
                    register_ids, defined, when_zero_name, 'select_field_if_flag zero source'
                ),
            })
        else:
            raise ValueError(f'unsupported instruction opcode: {op}')
        defined.add(dst_name)
    for output_name in ['qx', 'qy', 'qz']:
        if output_name not in defined:
            raise KeyError(f'missing output register: {output_name}')
    return {
        'register_count': len(register_ids),
        'input_qx': register_ids['Q.X'],
        'input_qy': register_ids['Q.Y'],
        'input_qz': register_ids['Q.Z'],
        'input_k': register_ids['k'],
        'input_lookup_x': register_ids['lookup_x'],
        'input_lookup_y': register_ids['lookup_y'],
        'input_lookup_meta': register_ids['lookup_meta'],
        'output_qx': register_ids['qx'],
        'output_qy': register_ids['qy'],
        'output_qz': register_ids['qz'],
        'instructions': compiled_instructions,
    }


def _prepared_case_corpus(case_corpus: Mapping[str, Any]) -> Dict[str, Any]:
    prepared = {
        'field_modulus_hex': str(case_corpus['field_modulus_hex']),
        'case_count': int(case_corpus['case_count']),
        'cases': list(case_corpus['cases']),
    }
    if 'case_start_index' in case_corpus:
        prepared['case_start_index'] = int(case_corpus['case_start_index'])
    return prepared


def build_pointadd_case_corpus(
    *,
    leaf: Mapping[str, Any],
    leaf_case_seed_sha256: str,
    case_count: int = DEFAULT_CASE_COUNT,
    case_start: int = 0,
) -> Dict[str, Any]:
    tables = precompute_window_tables(SECP_G, SECP_P, SECP_B, width=8, bits=256)
    seed = bytes.fromhex(leaf_case_seed_sha256)
    scalars = deterministic_scalars(seed + b'compiler-project-zkp-attestation', (case_start + case_count) * 2, SECP_N)
    cases: List[Dict[str, Any]] = []
    category_counts: Dict[str, int] = {}
    for offset in range(case_count):
        case_index = case_start + offset
        accumulator_scalar = scalars[2 * case_index]
        lookup_scalar = scalars[2 * case_index + 1]
        category = 'random'
        if case_index % 16 == 0:
            category = 'zero_zero'
            accumulator_scalar = 0
            lookup_scalar = 0
        elif case_index % 16 == 1:
            category = 'accumulator_infinity'
            accumulator_scalar = 0
        elif case_index % 16 == 2:
            category = 'lookup_infinity'
            lookup_scalar = 0
        elif case_index % 16 == 3:
            category = 'doubling'
            lookup_scalar = accumulator_scalar
        elif case_index % 16 == 4:
            category = 'inverse'
            lookup_scalar = (-accumulator_scalar) % SECP_N
        accumulator = mul_fixed_window(accumulator_scalar, tables, SECP_P, SECP_B, width=8, order=SECP_N)
        lookup = mul_fixed_window(lookup_scalar, tables, SECP_P, SECP_B, width=8, order=SECP_N)
        observed = proj_to_affine(
            exec_netlist(
                list(leaf['instructions']),
                SECP_P,
                affine_to_proj(accumulator, SECP_P),
                lookup,
                0 if lookup is None else 1,
            ),
            SECP_P,
        )
        category_counts[category] = category_counts.get(category, 0) + 1
        cases.append({
            'case_id': f'{category}_{case_index:04d}',
            'category': category,
            'accumulator': _point_payload(accumulator),
            'lookup': _point_payload(lookup),
            'expected': _point_payload(observed),
        })
    corpus = {
        'schema': 'compiler-project-zkp-attestation-cases-v1',
        'curve': 'secp256k1',
        'field_modulus_hex': format(SECP_P, '064x'),
        'curve_b': SECP_B,
        'seed_sha256': leaf_case_seed_sha256,
        'seed_hash_scheme': CASE_SEED_SCHEME,
        'case_count': len(cases),
        'category_counts': category_counts,
        'cases': cases,
        'notes': [
            'These point-add challenge cases are deterministic and public, derived from the lookup-fed leaf hash stream.',
            'The categories intentionally force neutral-entry, doubling, inverse, and ordinary mixed-add paths.',
        ],
    }
    if case_start != 0:
        corpus['case_start_index'] = case_start
    return corpus


def _build_zkp_attestation_materials(
    *,
    family_name: str = 'best-gate',
    case_count: int = DEFAULT_CASE_COUNT,
    case_start: int = 0,
) -> Dict[str, Any]:
    frontier = compiler_family_frontier()
    family = _resolve_family(frontier, family_name)
    family_payload = _family_proof_payload(family)
    leaf = _leaf_for_family(family)
    leaf_document_type, leaf_artifact_path = _leaf_commitment_metadata(family)
    schedule = raw32_schedule()
    leaf_case_seed_sha256 = sha256_bytes(_canonical_json(leaf).encode())
    leaf_blob = _committed_payload(
        document_type=leaf_document_type,
        artifact_path=leaf_artifact_path,
        payload=leaf,
    )
    case_corpus = build_pointadd_case_corpus(
        leaf=leaf,
        leaf_case_seed_sha256=leaf_case_seed_sha256,
        case_count=case_count,
        case_start=case_start,
    )
    case_blob = _committed_payload(
        document_type='pointadd_case_corpus',
        artifact_path='compiler_verification_project/artifacts/zkp_attestation_cases.json',
        payload=case_corpus,
    )
    family_blob = _committed_payload(
        document_type='compiler_family_summary',
        artifact_path='compiler_verification_project/artifacts/zkp_attestation_family.json',
        payload=family_payload,
    )
    leaf_call_count_total = int(schedule['summary']['leaf_call_count_total'])
    arithmetic_component = int(family['arithmetic_leaf_non_clifford']) * leaf_call_count_total
    lookup_component = int(family['per_leaf_lookup_non_clifford']) * leaf_call_count_total
    full_oracle_non_clifford = arithmetic_component + lookup_component + int(family['direct_seed_non_clifford'])
    arithmetic_qubits = int(family['arithmetic_slot_count']) * 256
    borrowed_interface_qubits = int(family_payload.get('borrowed_interface_qubits', 0))
    total_logical_qubits = (
        arithmetic_qubits
        + int(family['control_slot_count'])
        + borrowed_interface_qubits
        + int(family['lookup_workspace_qubits'])
        + int(family['live_phase_bits'])
    )
    public_claim = {
        'schema': 'compiler-project-zkp-attestation-claim-v1',
        'selected_family_alias': family_name,
        'selected_family_name': family_payload['name'],
        'field_bits': 256,
        'leaf_call_count_total': leaf_call_count_total,
        'expected_full_oracle_non_clifford': int(family_payload['full_oracle_non_clifford']),
        'expected_total_logical_qubits': int(family_payload['total_logical_qubits']),
        'expected_case_count': int(case_corpus['case_count']),
        'non_clifford_formula': {
            'arithmetic_leaf_non_clifford': int(family_payload['arithmetic_leaf_non_clifford']),
            'per_leaf_lookup_non_clifford': int(family_payload['per_leaf_lookup_non_clifford']),
            'direct_seed_non_clifford': int(family_payload['direct_seed_non_clifford']),
            'leaf_call_count_total': leaf_call_count_total,
            'arithmetic_component': arithmetic_component,
            'lookup_component': lookup_component,
            'reconstructed_total': full_oracle_non_clifford,
        },
        'logical_qubit_formula': {
            'field_bits': 256,
            'arithmetic_slot_count': int(family_payload['arithmetic_slot_count']),
            'control_slot_count': int(family_payload['control_slot_count']),
            'borrowed_interface_qubits': borrowed_interface_qubits,
            'lookup_workspace_qubits': int(family_payload['lookup_workspace_qubits']),
            'live_phase_bits': int(family_payload['live_phase_bits']),
            'arithmetic_component': arithmetic_qubits,
            'reconstructed_total': total_logical_qubits,
        },
        'notes': [
            'This claim intentionally stays at the repository exact-family boundary: exact point-add witness semantics plus exact compiler-family resource derivation.',
            'It is similar in shape to the Google disclosure model, but it proves a public deterministic point-add corpus instead of Fiat-Shamir-generated hidden tests.',
        ],
    }
    claim_blob = _committed_payload(
        document_type='attestation_claim',
        artifact_path='compiler_verification_project/artifacts/zkp_attestation_claim.json',
        payload=public_claim,
    )
    prepared_leaf = _compile_leaf_for_proof(leaf)
    prepared_case_corpus = _prepared_case_corpus(case_corpus)
    return {
        'input': {
            'schema': 'compiler-project-zkp-attestation-input-v3',
            'document_digest_scheme': DIGEST_SCHEME,
            'selected_family_name': family_payload['name'],
            'claim_sha256': claim_blob['sha256'],
            'leaf_sha256': leaf_blob['sha256'],
            'family_sha256': family_blob['sha256'],
            'case_corpus_sha256': case_blob['sha256'],
            'claim_summary': {
                'field_bits': int(public_claim['field_bits']),
                'leaf_call_count_total': int(public_claim['leaf_call_count_total']),
                'expected_full_oracle_non_clifford': int(public_claim['expected_full_oracle_non_clifford']),
                'expected_total_logical_qubits': int(public_claim['expected_total_logical_qubits']),
                'expected_case_count': int(public_claim['expected_case_count']),
                'non_clifford_formula': dict(public_claim['non_clifford_formula']),
                'logical_qubit_formula': dict(public_claim['logical_qubit_formula']),
            },
            'family_summary': {
                'name': family_payload['name'],
                'arithmetic_leaf_non_clifford': int(family_payload['arithmetic_leaf_non_clifford']),
                'direct_seed_non_clifford': int(family_payload['direct_seed_non_clifford']),
                'per_leaf_lookup_non_clifford': int(family_payload['per_leaf_lookup_non_clifford']),
                'full_oracle_non_clifford': int(family_payload['full_oracle_non_clifford']),
                'arithmetic_slot_count': int(family_payload['arithmetic_slot_count']),
                'control_slot_count': int(family_payload['control_slot_count']),
                'borrowed_interface_qubits': borrowed_interface_qubits,
                'lookup_workspace_qubits': int(family_payload['lookup_workspace_qubits']),
                'live_phase_bits': int(family_payload['live_phase_bits']),
                'total_logical_qubits': int(family_payload['total_logical_qubits']),
            },
            'prepared_leaf': prepared_leaf,
            'prepared_case_corpus': prepared_case_corpus,
            'notes': [
                'The proof input is a prepared attestation bundle: it carries the public document digests plus a proof-ready compiled leaf and deterministic public cases.',
                'The checked JSON claim, family summary, and case corpus remain the source-of-truth sidecars for audit and regeneration.',
            ],
        },
        'claim': public_claim,
        'family': family_payload,
        'cases': case_corpus,
    }


def build_zkp_attestation_input(
    *,
    family_name: str = 'best-gate',
    case_count: int = DEFAULT_CASE_COUNT,
    case_start: int = 0,
) -> Dict[str, Any]:
    return _build_zkp_attestation_materials(
        family_name=family_name,
        case_count=case_count,
        case_start=case_start,
    )['input']


def write_zkp_attestation_inputs(
    *,
    family_name: str = 'best-gate',
    case_count: int = DEFAULT_CASE_COUNT,
    case_start: int = 0,
    output_dir: Path | None = None,
) -> Dict[str, Any]:
    materials = _build_zkp_attestation_materials(
        family_name=family_name,
        case_count=case_count,
        case_start=case_start,
    )
    payload = materials['input']
    claim_payload = materials['claim']
    family_payload = materials['family']
    case_payload = materials['cases']
    target_dir = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts' if output_dir is None else Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    dump_json(target_dir / 'zkp_attestation_input.json', payload)
    dump_json(target_dir / 'zkp_attestation_claim.json', claim_payload)
    dump_json(target_dir / 'zkp_attestation_family.json', family_payload)
    dump_json(target_dir / 'zkp_attestation_cases.json', case_payload)
    return payload


__all__ = [
    'DIGEST_SCHEME',
    'DEFAULT_CASE_COUNT',
    'build_pointadd_case_corpus',
    'build_zkp_attestation_input',
    'write_zkp_attestation_inputs',
]
