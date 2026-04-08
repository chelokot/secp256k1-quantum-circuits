#!/usr/bin/env python3

from __future__ import annotations

from typing import Any, Dict, List, Mapping


def _count_profile(
    hadamard: int = 0,
    measurement: int = 0,
    single_qubit_rotation: int = 0,
    controlled_rotation: int = 0,
    rotation_depth: int = 0,
) -> Dict[str, int]:
    return {
        'hadamard': int(hadamard),
        'measurement': int(measurement),
        'single_qubit_rotation': int(single_qubit_rotation),
        'controlled_rotation': int(controlled_rotation),
        'rotation_depth': int(rotation_depth),
    }


def _block(
    name: str,
    summary: str,
    instance_count: int,
    count_profile_per_instance: Mapping[str, int],
    notes: List[str],
) -> Dict[str, Any]:
    count_profile = {
        key: int(count_profile_per_instance.get(key, 0))
        for key in ('hadamard', 'measurement', 'single_qubit_rotation', 'controlled_rotation', 'rotation_depth')
    }
    count_profile_total = {
        key: int(instance_count) * value
        for key, value in count_profile.items()
    }
    return {
        'name': name,
        'summary': summary,
        'instance_count': int(instance_count),
        'count_profile_per_instance': count_profile,
        'count_profile_total': count_profile_total,
        'notes': notes,
    }


def _stage(
    name: str,
    summary: str,
    category: str,
    blocks: List[Dict[str, Any]],
    notes: List[str],
) -> Dict[str, Any]:
    totals = {
        key: sum(int(block['count_profile_total'][key]) for block in blocks)
        for key in ('hadamard', 'measurement', 'single_qubit_rotation', 'controlled_rotation', 'rotation_depth')
    }
    return {
        'name': name,
        'summary': summary,
        'category': category,
        'blocks': blocks,
        'count_profile_total': totals,
        'notes': notes,
    }


def _family_payload(
    name: str,
    summary: str,
    gate_set: str,
    live_quantum_bits: int,
    lowering_strategy: Mapping[str, str],
    stages: List[Dict[str, Any]],
    notes: List[str],
) -> Dict[str, Any]:
    totals = {
        key: sum(int(stage['count_profile_total'][key]) for stage in stages)
        for key in ('hadamard', 'measurement', 'single_qubit_rotation', 'controlled_rotation', 'rotation_depth')
    }
    return {
        'name': name,
        'summary': summary,
        'gate_set': gate_set,
        'live_quantum_bits': int(live_quantum_bits),
        'lowering_strategy': dict(lowering_strategy),
        'stages': stages,
        'hadamard_count': totals['hadamard'],
        'total_measurements': totals['measurement'],
        'measurement_count': totals['measurement'],
        'total_rotations': totals['single_qubit_rotation'] + totals['controlled_rotation'],
        'rotation_count': totals['single_qubit_rotation'] + totals['controlled_rotation'],
        'rotation_depth': totals['rotation_depth'],
        'single_qubit_rotation_count': totals['single_qubit_rotation'],
        'controlled_rotation_count': totals['controlled_rotation'],
        'notes': notes,
    }


def _full_phase_register_family(phase_bits: int) -> Dict[str, Any]:
    controlled_rotation_count = phase_bits * (phase_bits - 1) // 2
    stages = [
        _stage(
            name='coherent_dyadic_rotation_ladder',
            summary='Exact coherent inverse-QFT dyadic phase ladder over the full live phase register.',
            category='coherent_phase_rotations',
            blocks=[
                _block(
                    name='controlled_dyadic_rotations',
                    summary='One coherent controlled dyadic phase rotation for each strict bit-order pair in the inverse-QFT ladder.',
                    instance_count=controlled_rotation_count,
                    count_profile_per_instance=_count_profile(controlled_rotation=1, rotation_depth=1),
                    notes=[
                        'The lowering keeps the register coherent and counts every controlled dyadic phase separately.',
                        'The reported rotation depth follows the same serial bit-order schedule as the counted ladder blocks.',
                    ],
                ),
            ],
            notes=[
                'This family keeps the entire 512-bit phase register live and lowers the inverse QFT as a coherent dyadic rotation ladder.',
            ],
        ),
        _stage(
            name='basis_change_and_measurement',
            summary='Terminal Hadamard basis changes followed by one computational-basis measurement per phase bit.',
            category='basis_change_and_measurement',
            blocks=[
                _block(
                    name='terminal_hadamards',
                    summary='One Hadamard basis change for each live phase bit before measurement.',
                    instance_count=phase_bits,
                    count_profile_per_instance=_count_profile(hadamard=1),
                    notes=[
                        'The Hadamards are part of the exact inverse-QFT shell rather than of the oracle core.',
                    ],
                ),
                _block(
                    name='terminal_measurements',
                    summary='One computational-basis measurement for each phase bit after the inverse-QFT basis change.',
                    instance_count=phase_bits,
                    count_profile_per_instance=_count_profile(measurement=1),
                    notes=[
                        'The shell ends in terminal measurements over the full phase register.',
                    ],
                ),
            ],
            notes=[
                'The coherent shell measures only after the full inverse-QFT ladder completes.',
            ],
        ),
    ]
    return _family_payload(
        name='full_phase_register_v1',
        summary='Conservative shell that keeps the full 512-bit phase register live and lowers the inverse QFT as a coherent dyadic ladder.',
        gate_set='Clifford + coherent controlled dyadic phase + measurement',
        live_quantum_bits=phase_bits,
        lowering_strategy={
            'phase_register_policy': 'keep all phase-estimation bits live until the coherent inverse-QFT ladder finishes',
            'phase_rotation_policy': 'one explicit controlled dyadic phase per strict ordered bit pair',
            'basis_change_policy': 'one Hadamard and one terminal measurement per phase bit',
        },
        stages=stages,
        notes=[
            'This family is exact for the chosen serial coherent inverse-QFT schedule over the live phase register.',
            'Its rotation ladder is much heavier than the semiclassical family because quantum-controlled dyadic phases cannot be collapsed into one classical feed-forward update per bit.',
        ],
    )


def _semiclassical_qft_family(phase_bits: int) -> Dict[str, Any]:
    adaptive_rotation_count = phase_bits - 1
    stages = [
        _stage(
            name='adaptive_basis_updates',
            summary='One classically aggregated dyadic phase update before each noninitial semiclassical inverse-QFT measurement.',
            category='adaptive_phase_rotations',
            blocks=[
                _block(
                    name='aggregated_classical_phase_updates',
                    summary='One classically controlled dyadic Z rotation per noninitial phase bit, after aggregating all prior measurement bits into a single update angle.',
                    instance_count=adaptive_rotation_count,
                    count_profile_per_instance=_count_profile(single_qubit_rotation=1, rotation_depth=1),
                    notes=[
                        'This follows the Griffiths–Niu semiclassical QFT pattern in which prior measured bits determine the next one-qubit basis update.',
                        'All prior dyadic corrections for a given target bit are classically aggregated into one rotation before the Hadamard and measurement.',
                    ],
                ),
            ],
            notes=[
                'The first measured bit has no prior feed-forward correction, so the explicit adaptive-rotation count is phase_bits - 1.',
            ],
        ),
        _stage(
            name='basis_change_and_measurement',
            summary='One Hadamard basis change and one terminal measurement per phase bit in the semiclassical shell.',
            category='basis_change_and_measurement',
            blocks=[
                _block(
                    name='terminal_hadamards',
                    summary='One Hadamard before each semiclassical inverse-QFT measurement.',
                    instance_count=phase_bits,
                    count_profile_per_instance=_count_profile(hadamard=1),
                    notes=[
                        'The single live phase qubit is reused across the full bit schedule.',
                    ],
                ),
                _block(
                    name='terminal_measurements',
                    summary='One computational-basis measurement per phase bit in the semiclassical shell.',
                    instance_count=phase_bits,
                    count_profile_per_instance=_count_profile(measurement=1),
                    notes=[
                        'Each measured bit is committed to classical state before the next adaptive basis update.',
                    ],
                ),
            ],
            notes=[
                'The shell keeps only one phase qubit live and relies on classical feed-forward between measurements.',
            ],
        ),
    ]
    return _family_payload(
        name='semiclassical_qft_v1',
        summary='Space-compressed shell that uses a Griffiths–Niu-style semiclassical inverse QFT and reuses a single phase qubit.',
        gate_set='Clifford + classically controlled dyadic phase + measurement',
        live_quantum_bits=1,
        lowering_strategy={
            'phase_register_policy': 'reuse one live phase qubit across the full bit schedule',
            'phase_rotation_policy': 'aggregate all prior measured-bit corrections for each target into one classically controlled dyadic rotation',
            'basis_change_policy': 'one Hadamard and one terminal measurement per phase bit',
        },
        stages=stages,
        notes=[
            'This family is exact for the chosen semiclassical inverse-QFT schedule with one aggregated classical basis update per noninitial bit.',
            'It preserves the oracle family while collapsing the live quantum phase register from 512 qubits to one qubit.',
        ],
    )


def phase_shell_lowering_library(phase_bits: int) -> Dict[str, Any]:
    families = [
        _full_phase_register_family(phase_bits),
        _semiclassical_qft_family(phase_bits),
    ]
    return {
        'schema': 'compiler-project-phase-shell-lowerings-v1',
        'phase_register_bits': int(phase_bits),
        'families': families,
        'notes': [
            'This artifact lowers each named phase-shell family into exact stage/block inventories over explicit pre-layout phase-shell primitives.',
            'The shell inventory is tracked separately from the arithmetic and lookup CCX totals because Azure logicalCounts accepts rotations and measurements as separate exact pre-layout inputs.',
        ],
    }


def phase_shell_family_summary(lowerings: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        'schema': 'compiler-project-phase-shells-v2',
        'families': [
            {
                'name': family['name'],
                'summary': family['summary'],
                'gate_set': family['gate_set'],
                'live_quantum_bits': int(family['live_quantum_bits']),
                'hadamard_count': int(family['hadamard_count']),
                'total_measurements': int(family['measurement_count']),
                'total_rotations': int(family['rotation_count']),
                'rotation_depth': int(family['rotation_depth']),
                'single_qubit_rotation_count': int(family['single_qubit_rotation_count']),
                'controlled_rotation_count': int(family['controlled_rotation_count']),
                'notes': list(family['notes']),
            }
            for family in lowerings['families']
        ],
        'notes': [
            'This compact summary is derived from the exact phase-shell lowering library and is used by frontier and handoff artifacts.',
        ],
    }


__all__ = ['phase_shell_family_summary', 'phase_shell_lowering_library']
