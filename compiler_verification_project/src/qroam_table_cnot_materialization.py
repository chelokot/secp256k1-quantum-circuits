#!/usr/bin/env python3

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Mapping, Optional, Tuple

from common import SECP_B, SECP_P, add_affine, sha256_bytes

PointAffine = Optional[Tuple[int, int]]

QROAM_TABLE_CNOT_MATERIALIZATION_SCHEMA = 'compiler-project-qroam-table-cnot-materialization-v3'
TABLE_NAMES = ('lookup_x', 'lookup_y', 'lookup_x_plus_y')
RANK_CHECKPOINT_STRIDE = 256


def _merkle_parent(left_hex: str, right_hex: str) -> str:
    digest = hashlib.sha256()
    digest.update(bytes.fromhex(left_hex))
    digest.update(bytes.fromhex(right_hex))
    return digest.hexdigest()


def _merkle_root(hashes: List[str]) -> str:
    if not hashes:
        return sha256_bytes(b'')
    level = list(hashes)
    while len(level) > 1:
        next_level: List[str] = []
        for index in range(0, len(level), 2):
            left = level[index]
            right = level[index + 1] if index + 1 < len(level) else left
            next_level.append(_merkle_parent(left, right))
        level = next_level
    return level[0]


def _chunk_effective_bits(*, field_bits: int, chunk_bits: int, chunk_index: int) -> int:
    bit_start = int(chunk_bits) * int(chunk_index)
    return max(0, min(int(chunk_bits), int(field_bits) - bit_start))


def _chunk_value(*, value: int, field_bits: int, chunk_bits: int, chunk_index: int) -> int:
    effective_bits = _chunk_effective_bits(
        field_bits=field_bits,
        chunk_bits=chunk_bits,
        chunk_index=chunk_index,
    )
    if effective_bits == 0:
        return 0
    return (int(value) >> (int(chunk_bits) * int(chunk_index))) & ((1 << effective_bits) - 1)


def _select_set_bit(value: int, rank: int) -> int:
    remaining = int(value)
    for _ in range(int(rank)):
        remaining &= remaining - 1
    return (remaining & -remaining).bit_length() - 1


def _table_value(point: PointAffine, table: str) -> int:
    if point is None:
        return 0
    if table == 'lookup_x':
        return int(point[0]) % SECP_P
    if table == 'lookup_y':
        return int(point[1]) % SECP_P
    if table == 'lookup_x_plus_y':
        return (int(point[0]) + int(point[1])) % SECP_P
    raise KeyError(f'unknown QROAM table: {table}')


def _base_point(row: Mapping[str, Any]) -> Tuple[int, int]:
    return int(str(row['base_x_hex']), 16), int(str(row['base_y_hex']), 16)


def _call_base(raw32_call: Mapping[str, Any], table_manifests: Mapping[str, Any]) -> Tuple[int, int]:
    phase_register = str(raw32_call['phase_register'])
    window_index = int(raw32_call['window_index_within_register'])
    if phase_register == 'phase_a':
        return _base_point(table_manifests['phase_a_bases'][window_index])
    if phase_register == 'phase_b':
        return _base_point(table_manifests['phase_b_bases'][window_index])
    raise KeyError(f'unknown phase register: {phase_register}')


def _iter_positive_domain_points(*, base: Tuple[int, int], domain_size: int) -> Any:
    current: PointAffine = None
    for address in range(int(domain_size)):
        if address == 0:
            current = None
        elif address == 1:
            current = base
        else:
            current = add_affine(current, base, SECP_P, SECP_B)
        yield address, current


def _new_segment_accumulator(
    *,
    call_index: int,
    phase_register: str,
    window_index: int,
    table: str,
    chunk_index: int,
    segment_index: int,
    start_address: int,
    end_address_exclusive: int,
    target_capacity_bits: int,
    effective_constant_bits: int,
) -> Dict[str, Any]:
    digest = hashlib.sha256()
    digest.update(b'compiler-project-qroam-table-cnot-segment-v1\n')
    digest.update(f'{call_index}:{phase_register}:{window_index}:{table}:{chunk_index}:{segment_index}:'.encode('ascii'))
    digest.update(f'{start_address}:{end_address_exclusive}:{target_capacity_bits}:{effective_constant_bits}\n'.encode('ascii'))
    address_count = int(end_address_exclusive) - int(start_address)
    return {
        'call_index': int(call_index),
        'phase_register': phase_register,
        'window_index_within_register': int(window_index),
        'table': table,
        'chunk_index': int(chunk_index),
        'segment_index': int(segment_index),
        'start_address': int(start_address),
        'end_address_exclusive': int(end_address_exclusive),
        'address_count': address_count,
        'target_capacity_bits': int(target_capacity_bits),
        'effective_constant_bits': int(effective_constant_bits),
        'zero_padded_target_bits': int(target_capacity_bits) - int(effective_constant_bits),
        'potential_target_bit_sites': address_count * int(target_capacity_bits),
        'effective_target_bit_sites': address_count * int(effective_constant_bits),
        'zero_padded_target_bit_sites': address_count * (int(target_capacity_bits) - int(effective_constant_bits)),
        'emitted_cx_count': 0,
        '_rank_checkpoints': [{
            'address': int(start_address),
            'local_emitted_cx_index': 0,
        }],
        '_first_emitted_cx': None,
        '_last_emitted_cx': None,
        '_digest': digest,
    }


def _finalize_segment(segment: Mapping[str, Any], phase: str) -> Dict[str, Any]:
    digest = hashlib.sha256()
    digest.update(b'compiler-project-qroam-table-cnot-phased-segment-v1\n')
    digest.update(str(phase).encode('ascii'))
    digest.update(b'\n')
    digest.update(segment['_digest'].hexdigest().encode('ascii'))
    public_fields = {
        key: value
        for key, value in segment.items()
        if not key.startswith('_')
    }
    public_fields['first_emitted_cx'] = segment['_first_emitted_cx']
    public_fields['last_emitted_cx'] = segment['_last_emitted_cx']
    public_fields['rank_checkpoints'] = list(segment['_rank_checkpoints'])
    return {
        key: value
        for key, value in {
            **public_fields,
            'phase': phase,
            'sha256': digest.hexdigest(),
        }.items()
    }


def _preview_rows_for_segment(segment: Mapping[str, Any], rows: List[Mapping[str, int]]) -> List[Dict[str, int]]:
    wanted = {
        int(segment['start_address']),
        min(int(segment['end_address_exclusive']) - 1, int(segment['start_address'])),
    }
    return [
        {
            'address': int(row['address']),
            'chunk_value': int(row['chunk_value']),
            'emitted_cx_count': int(row['emitted_cx_count']),
        }
        for row in rows
        if int(row['address']) in wanted
    ]


def _call_segments(
    *,
    raw32_call: Mapping[str, Any],
    base: Tuple[int, int],
    domain_size: int,
    segment_size: int,
    field_bits: int,
    chunk_bits: int,
    chunk_count: int,
) -> List[Dict[str, Any]]:
    call_index = int(raw32_call['call_index'])
    phase_register = str(raw32_call['phase_register'])
    window_index = int(raw32_call['window_index_within_register'])
    segment_rows: Dict[Tuple[str, int, int], Dict[str, Any]] = {}
    preview_rows_by_segment: Dict[Tuple[str, int, int], List[Mapping[str, int]]] = {}
    for table in TABLE_NAMES:
        for chunk_index in range(int(chunk_count)):
            effective_bits = _chunk_effective_bits(
                field_bits=field_bits,
                chunk_bits=chunk_bits,
                chunk_index=chunk_index,
            )
            for segment_index, start_address in enumerate(range(0, int(domain_size), int(segment_size))):
                key = (table, chunk_index, segment_index)
                segment_rows[key] = _new_segment_accumulator(
                    call_index=call_index,
                    phase_register=phase_register,
                    window_index=window_index,
                    table=table,
                    chunk_index=chunk_index,
                    segment_index=segment_index,
                    start_address=start_address,
                    end_address_exclusive=min(start_address + int(segment_size), int(domain_size)),
                    target_capacity_bits=int(chunk_bits),
                    effective_constant_bits=effective_bits,
                )
                preview_rows_by_segment[key] = []
    for address, point in _iter_positive_domain_points(base=base, domain_size=domain_size):
        segment_index = int(address) // int(segment_size)
        values = {
            table: _table_value(point, table)
            for table in TABLE_NAMES
        }
        for table, value in values.items():
            for chunk_index in range(int(chunk_count)):
                key = (table, chunk_index, segment_index)
                segment = segment_rows[key]
                effective_bits = int(segment['effective_constant_bits'])
                chunk_value = _chunk_value(
                    value=value,
                    field_bits=field_bits,
                    chunk_bits=chunk_bits,
                    chunk_index=chunk_index,
                )
                local_emitted_start = int(segment['emitted_cx_count'])
                emitted_cx = int(chunk_value).bit_count()
                if emitted_cx:
                    first_bit = (int(chunk_value) & -int(chunk_value)).bit_length() - 1
                    last_bit = int(chunk_value).bit_length() - 1
                    first_row = {
                        'local_emitted_cx_index': local_emitted_start,
                        'address': int(address),
                        'target_bit_index': first_bit,
                        'chunk_value': int(chunk_value),
                    }
                    last_row = {
                        'local_emitted_cx_index': local_emitted_start + emitted_cx - 1,
                        'address': int(address),
                        'target_bit_index': last_bit,
                        'chunk_value': int(chunk_value),
                    }
                    if segment['_first_emitted_cx'] is None:
                        segment['_first_emitted_cx'] = first_row
                    segment['_last_emitted_cx'] = last_row
                segment['emitted_cx_count'] += emitted_cx
                next_address = int(address) + 1
                if (
                    next_address == int(segment['end_address_exclusive'])
                    or (next_address - int(segment['start_address'])) % RANK_CHECKPOINT_STRIDE == 0
                ):
                    segment['_rank_checkpoints'].append({
                        'address': next_address,
                        'local_emitted_cx_index': int(segment['emitted_cx_count']),
                    })
                segment['_digest'].update(int(address).to_bytes(2, 'big'))
                segment['_digest'].update(int(chunk_value).to_bytes((effective_bits + 7) // 8, 'little'))
                segment['_digest'].update(int(emitted_cx).to_bytes(2, 'big'))
                if address in {
                    int(segment['start_address']),
                    int(segment['end_address_exclusive']) - 1,
                }:
                    preview_rows_by_segment[key].append({
                        'address': address,
                        'chunk_value': chunk_value,
                        'emitted_cx_count': emitted_cx,
                    })
    finalized = []
    for table in TABLE_NAMES:
        for chunk_index in range(int(chunk_count)):
            for segment_index, _ in enumerate(range(0, int(domain_size), int(segment_size))):
                key = (table, chunk_index, segment_index)
                segment = segment_rows[key]
                common = {
                    **segment,
                    'preview_rows': _preview_rows_for_segment(segment, preview_rows_by_segment[key]),
                }
                finalized.append(_finalize_segment(common, 'compute'))
                finalized.append(_finalize_segment(common, 'measured_uncompute'))
    return finalized


def _rank_checkpoint_sha256(segment: Mapping[str, Any]) -> str:
    digest = hashlib.sha256()
    digest.update(b'compiler-project-qroam-table-cnot-rank-checkpoints-v1\n')
    for checkpoint in segment['rank_checkpoints']:
        digest.update(int(checkpoint['address']).to_bytes(2, 'big'))
        digest.update(int(checkpoint['local_emitted_cx_index']).to_bytes(4, 'big'))
    return digest.hexdigest()


def _checkpoint_for_local_index(segment: Mapping[str, Any], local_emitted_cx_index: int) -> Mapping[str, Any]:
    selected = segment['rank_checkpoints'][0]
    for checkpoint in segment['rank_checkpoints']:
        if int(checkpoint['local_emitted_cx_index']) > int(local_emitted_cx_index):
            break
        selected = checkpoint
    return selected


def decode_segment_emitted_cx(
    *,
    segment: Mapping[str, Any],
    base: Tuple[int, int],
    local_emitted_cx_index: int,
    field_bits: int,
    chunk_bits: int,
) -> Dict[str, Any]:
    if not 0 <= int(local_emitted_cx_index) < int(segment['emitted_cx_count']):
        raise IndexError('local emitted-CNOT index outside segment')
    checkpoint = _checkpoint_for_local_index(segment, local_emitted_cx_index)
    cursor = int(checkpoint['local_emitted_cx_index'])
    start_address = int(checkpoint['address'])
    table = str(segment['table'])
    chunk_index = int(segment['chunk_index'])
    for address, point in _iter_positive_domain_points(base=base, domain_size=int(segment['end_address_exclusive'])):
        if int(address) < start_address:
            continue
        chunk_value = _chunk_value(
            value=_table_value(point, table),
            field_bits=field_bits,
            chunk_bits=chunk_bits,
            chunk_index=chunk_index,
        )
        emitted = int(chunk_value).bit_count()
        if int(local_emitted_cx_index) < cursor + emitted:
            set_bit_rank = int(local_emitted_cx_index) - cursor
            target_bit_index = _select_set_bit(chunk_value, set_bit_rank)
            global_index = int(segment['emitted_cx_operation_start']) + int(local_emitted_cx_index)
            return {
                'operation': 'cx',
                'global_emitted_cx_index': global_index,
                'local_emitted_cx_index': int(local_emitted_cx_index),
                'address': int(address),
                'set_bit_rank_at_address': set_bit_rank,
                'target_bit_index': target_bit_index,
                'chunk_value': int(chunk_value),
                'control_wire': f"qroam_unary_match_control[{int(address)}]",
                'target_wire': f"qroam_target.bit[{target_bit_index}]",
                'checkpoint_address': start_address,
                'checkpoint_local_emitted_cx_index': int(checkpoint['local_emitted_cx_index']),
            }
        cursor += emitted
    raise AssertionError('rank checkpoints and emitted-CNOT count disagree')


def _row_decoder_samples_for_segment(
    *,
    segment: Mapping[str, Any],
    field_bits: int,
    chunk_bits: int,
) -> List[Dict[str, Any]]:
    del field_bits, chunk_bits
    samples = []
    for sample in (segment.get('first_emitted_cx'), segment.get('last_emitted_cx')):
        if sample is None:
            continue
        checkpoint = _checkpoint_for_local_index(segment, int(sample['local_emitted_cx_index']))
        target_bit_index = int(sample['target_bit_index'])
        samples.append({
            'operation': 'cx',
            'global_emitted_cx_index': int(sample['global_emitted_cx_index']),
            'local_emitted_cx_index': int(sample['local_emitted_cx_index']),
            'address': int(sample['address']),
            'set_bit_rank_at_address': (int(sample['chunk_value']) & ((1 << target_bit_index) - 1)).bit_count(),
            'target_bit_index': target_bit_index,
            'chunk_value': int(sample['chunk_value']),
            'control_wire': str(sample['control_wire']),
            'target_wire': str(sample['target_wire']),
            'checkpoint_address': int(checkpoint['address']),
            'checkpoint_local_emitted_cx_index': int(checkpoint['local_emitted_cx_index']),
        })
    return samples


def _row_decoder_sample_sha256(samples: List[Mapping[str, Any]]) -> str:
    digest = hashlib.sha256()
    digest.update(b'compiler-project-qroam-table-cnot-row-decoder-samples-v1\n')
    for sample in samples:
        digest.update(str(int(sample['global_emitted_cx_index'])).encode('ascii'))
        digest.update(b':')
        digest.update(str(int(sample['address'])).encode('ascii'))
        digest.update(b':')
        digest.update(str(int(sample['target_bit_index'])).encode('ascii'))
        digest.update(b':')
        digest.update(str(int(sample['chunk_value'])).encode('ascii'))
        digest.update(b'\n')
    return digest.hexdigest()


def _with_global_emitted_cx_ranges(segments: List[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    cursor = 0
    ranged_segments: List[Dict[str, Any]] = []
    for segment in segments:
        emitted_cx_count = int(segment['emitted_cx_count'])
        row = dict(segment)
        row['emitted_cx_operation_start'] = cursor
        row['emitted_cx_operation_end_exclusive'] = cursor + emitted_cx_count
        for key in ('first_emitted_cx', 'last_emitted_cx'):
            sample = row.get(key)
            if sample is None:
                continue
            row[key] = {
                **dict(sample),
                'global_emitted_cx_index': cursor + int(sample['local_emitted_cx_index']),
                'control_wire': f"qroam_unary_match_control[{int(sample['address'])}]",
                'target_wire': f"qroam_target.bit[{int(sample['target_bit_index'])}]",
            }
        ranged_segments.append(row)
        cursor += emitted_cx_count
    return ranged_segments


def _with_row_index_contract(
    *,
    segments: List[Mapping[str, Any]],
    raw32_schedule: Mapping[str, Any],
    table_manifests: Mapping[str, Any],
    field_bits: int,
    chunk_bits: int,
) -> List[Dict[str, Any]]:
    del raw32_schedule, table_manifests
    indexed_segments: List[Dict[str, Any]] = []
    for segment in segments:
        samples = _row_decoder_samples_for_segment(
            segment=segment,
            field_bits=field_bits,
            chunk_bits=chunk_bits,
        )
        row = dict(segment)
        row['row_index_contract'] = {
            'operation': 'cx',
            'global_index_domain_start': int(segment['emitted_cx_operation_start']),
            'global_index_domain_end_exclusive': int(segment['emitted_cx_operation_end_exclusive']),
            'rank_checkpoint_stride_addresses': RANK_CHECKPOINT_STRIDE,
            'rank_checkpoint_count': len(segment['rank_checkpoints']),
            'rank_checkpoint_sha256': _rank_checkpoint_sha256(segment),
            'decoder': 'segment-range -> rank checkpoint -> folded table chunk replay -> selected set bit',
            'max_replay_addresses_after_checkpoint': RANK_CHECKPOINT_STRIDE - 1,
            'sample_count': len(samples),
            'sample_sha256': _row_decoder_sample_sha256(samples),
        }
        row['row_decoder_samples'] = samples
        indexed_segments.append(row)
    return indexed_segments


def _rank_checkpoints_are_valid(segment: Mapping[str, Any]) -> bool:
    checkpoints = segment['rank_checkpoints']
    if not checkpoints:
        return False
    if int(checkpoints[0]['address']) != int(segment['start_address']):
        return False
    if int(checkpoints[0]['local_emitted_cx_index']) != 0:
        return False
    if int(checkpoints[-1]['address']) != int(segment['end_address_exclusive']):
        return False
    if int(checkpoints[-1]['local_emitted_cx_index']) != int(segment['emitted_cx_count']):
        return False
    return all(
        int(left['address']) < int(right['address'])
        and int(left['local_emitted_cx_index']) <= int(right['local_emitted_cx_index'])
        and int(right['address']) - int(left['address']) <= RANK_CHECKPOINT_STRIDE
        for left, right in zip(checkpoints, checkpoints[1:])
    )


def build_qroam_table_cnot_materialization(
    *,
    table_manifests: Mapping[str, Any],
    raw32_schedule: Mapping[str, Any],
    reusable_chunk_lowering: Mapping[str, Any],
    qroam_primitive_certificate: Mapping[str, Any],
    field_bits: int,
) -> Dict[str, Any]:
    domain_size = int(qroam_primitive_certificate['parameters']['domain_size'])
    segment_size = int(qroam_primitive_certificate['parameters']['segment_size'])
    chunk_bits = int(reusable_chunk_lowering['stream_plan']['chunk_bits'])
    chunk_count = int(reusable_chunk_lowering['stream_plan']['chunk_count'])
    segments: List[Dict[str, Any]] = []
    for raw32_call in raw32_schedule['leaf_calls']:
        base = _call_base(raw32_call, table_manifests)
        segments.extend(_call_segments(
            raw32_call=raw32_call,
            base=base,
            domain_size=domain_size,
            segment_size=segment_size,
            field_bits=field_bits,
            chunk_bits=chunk_bits,
            chunk_count=chunk_count,
        ))
    segments = _with_global_emitted_cx_ranges(segments)
    segments = _with_row_index_contract(
        segments=segments,
        raw32_schedule=raw32_schedule,
        table_manifests=table_manifests,
        field_bits=field_bits,
        chunk_bits=chunk_bits,
    )
    full_oracle_chunk_streams = int(reusable_chunk_lowering['stream_plan']['whole_oracle_chunk_streams'])
    per_stream_potential_sites = int(qroam_primitive_certificate['target_bit_load_site_stream']['potential_cnot_site_count'])
    total_potential_sites = sum(int(segment['potential_target_bit_sites']) for segment in segments)
    total_effective_sites = sum(int(segment['effective_target_bit_sites']) for segment in segments)
    total_zero_padded_sites = sum(int(segment['zero_padded_target_bit_sites']) for segment in segments)
    total_emitted_cx = sum(int(segment['emitted_cx_count']) for segment in segments)
    checks = {
        'leaf_call_count_matches_schedule': len(raw32_schedule['leaf_calls']) == int(reusable_chunk_lowering['stream_plan']['leaf_call_count_total']),
        'chunk_stream_count_matches_resource_contract': len(raw32_schedule['leaf_calls']) * len(TABLE_NAMES) * chunk_count == full_oracle_chunk_streams,
        'segment_count_matches_qroam_stream_segments': len(segments) == full_oracle_chunk_streams * int(qroam_primitive_certificate['operation_stream']['segment_count']),
        'potential_sites_match_target_bit_site_stream': total_potential_sites == full_oracle_chunk_streams * per_stream_potential_sites,
        'zero_padding_is_explicit_for_high_chunks': all(
            int(segment['zero_padded_target_bits']) == 0
            if int(segment['chunk_index']) == 0
            else int(segment['zero_padded_target_bits']) == chunk_bits - (int(field_bits) - chunk_bits)
            for segment in segments
        ),
        'emitted_cx_count_is_within_effective_sites': 0 <= total_emitted_cx <= total_effective_sites,
        'emitted_cx_operation_ranges_cover_total': (
            segments[0]['emitted_cx_operation_start'] == 0
            and segments[-1]['emitted_cx_operation_end_exclusive'] == total_emitted_cx
            and all(
                int(left['emitted_cx_operation_end_exclusive']) == int(right['emitted_cx_operation_start'])
                for left, right in zip(segments, segments[1:])
            )
        ),
        'emitted_cx_probes_are_within_effective_target_bits': all(
            sample is None
            or (
                0 <= int(sample['local_emitted_cx_index']) < int(segment['emitted_cx_count'])
                and int(segment['start_address']) <= int(sample['address']) < int(segment['end_address_exclusive'])
                and 0 <= int(sample['target_bit_index']) < int(segment['effective_constant_bits'])
                and ((int(sample['chunk_value']) >> int(sample['target_bit_index'])) & 1) == 1
                and int(segment['emitted_cx_operation_start']) <= int(sample['global_emitted_cx_index']) < int(segment['emitted_cx_operation_end_exclusive'])
            )
            for segment in segments
            for sample in (segment.get('first_emitted_cx'), segment.get('last_emitted_cx'))
        ),
        'rank_checkpoints_cover_every_segment': all(
            _rank_checkpoints_are_valid(segment)
            for segment in segments
        ),
        'row_index_contract_domains_match_ranges': all(
            int(segment['row_index_contract']['global_index_domain_start']) == int(segment['emitted_cx_operation_start'])
            and int(segment['row_index_contract']['global_index_domain_end_exclusive']) == int(segment['emitted_cx_operation_end_exclusive'])
            and int(segment['row_index_contract']['sample_count']) == len(segment['row_decoder_samples'])
            for segment in segments
        ),
        'row_decoder_samples_are_exact_table_cnot_rows': all(
            int(segment['emitted_cx_operation_start']) <= int(sample['global_emitted_cx_index']) < int(segment['emitted_cx_operation_end_exclusive'])
            and int(segment['start_address']) <= int(sample['address']) < int(segment['end_address_exclusive'])
            and 0 <= int(sample['target_bit_index']) < int(segment['effective_constant_bits'])
            and ((int(sample['chunk_value']) >> int(sample['target_bit_index'])) & 1) == 1
            and sample['control_wire'] == f"qroam_unary_match_control[{int(sample['address'])}]"
            and sample['target_wire'] == f"qroam_target.bit[{int(sample['target_bit_index'])}]"
            for segment in segments
            for sample in segment['row_decoder_samples']
        ),
    }
    row_index_hashes = [
        segment['row_index_contract']['rank_checkpoint_sha256']
        for segment in segments
    ]
    row_decoder_sample_hashes = [
        segment['row_index_contract']['sample_sha256']
        for segment in segments
    ]
    return {
        'schema': QROAM_TABLE_CNOT_MATERIALIZATION_SCHEMA,
        'definition': 'Concrete table-bit Clifford CNOT materialization for the checked raw32 retained lookup calls; each segment hashes the selected folded table chunk values and counts emitted CNOTs for one-valued bits.',
        'source_artifacts': {
            'table_manifests': 'compiler_verification_project/artifacts/table_manifests.json',
            'reusable_chunk_lowering': 'compiler_verification_project/artifacts/reusable_chunk_lowering.json',
            'qroam_primitive_certificate': 'compiler_verification_project/artifacts/qroam_primitive_certificate.json',
        },
        'parameters': {
            'domain_size': domain_size,
            'segment_size': segment_size,
            'field_bits': int(field_bits),
            'chunk_bits': chunk_bits,
            'chunk_count': chunk_count,
            'tables': list(TABLE_NAMES),
            'leaf_call_count': len(raw32_schedule['leaf_calls']),
        },
        'totals': {
            'chunk_stream_count': full_oracle_chunk_streams,
            'segment_count': len(segments),
            'full_oracle_potential_target_bit_sites': total_potential_sites,
            'full_oracle_effective_target_bit_sites': total_effective_sites,
            'full_oracle_zero_padded_target_bit_sites': total_zero_padded_sites,
            'full_oracle_emitted_clifford_cx': total_emitted_cx,
            'rank_checkpoint_count': sum(int(segment['row_index_contract']['rank_checkpoint_count']) for segment in segments),
            'row_decoder_sample_count': sum(int(segment['row_index_contract']['sample_count']) for segment in segments),
        },
        'segments': segments,
        'segment_merkle_root_sha256': _merkle_root([segment['sha256'] for segment in segments]),
        'row_index_contract_merkle_root_sha256': _merkle_root(row_index_hashes),
        'row_decoder_sample_merkle_root_sha256': _merkle_root(row_decoder_sample_hashes),
        'checks': checks,
        'pass': all(checks.values()),
        'notes': [
            'This artifact affects Clifford CNOT materialization evidence, not the public non-Clifford headline.',
            'The artifact records global emitted-CNOT operation ranges, rank checkpoints, and an executable per-CNOT row decoder for each segment; the remaining QROAM work is to splice the indexed virtual CNOT rows into the canonical global flat stream.',
        ],
    }


__all__ = [
    'QROAM_TABLE_CNOT_MATERIALIZATION_SCHEMA',
    'build_qroam_table_cnot_materialization',
    'decode_segment_emitted_cx',
]
