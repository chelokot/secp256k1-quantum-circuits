#!/usr/bin/env python3

from __future__ import annotations

import json
from copy import deepcopy
from importlib import import_module
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Dict, List, Mapping

from common import load_json, sha256_bytes


AZURE_ESTIMATOR_DOCS = {
    'target_parameters': 'https://learn.microsoft.com/en-us/azure/quantum/overview-resources-estimator',
    'resource_estimator_usage': 'https://learn.microsoft.com/en-us/azure/quantum/how-to-submit-re-jobs',
}

DEFAULT_ERROR_BUDGET = 0.001


def _canonical_json_sha256(payload: Any) -> str:
    return sha256_bytes(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode())


def _estimator_versions() -> Dict[str, str] | None:
    try:
        return {
            'qdk': version('qdk'),
            'qsharp': version('qsharp'),
        }
    except PackageNotFoundError:
        return None


def estimator_backend_metadata() -> Dict[str, Any]:
    return {
        'engine': 'Microsoft Quantum Resource Estimator',
        'required_python_packages': ['qdk', 'qsharp'],
        'official_docs': AZURE_ESTIMATOR_DOCS,
    }


def azure_estimator_target_profiles() -> List[Dict[str, Any]]:
    return [
        {
            'name': 'gate_us_e3_surface_code',
            'summary': 'Gate-based microsecond preset with 1e-3 physical error rates and the surface code.',
            'requested_params': {
                'qubitParams': {'name': 'qubit_gate_us_e3'},
                'qecScheme': {'name': 'surface_code'},
                'errorBudget': DEFAULT_ERROR_BUDGET,
                'estimateType': 'singlePoint',
            },
        },
        {
            'name': 'gate_us_e4_surface_code',
            'summary': 'Gate-based microsecond preset with 1e-4 physical error rates and the surface code.',
            'requested_params': {
                'qubitParams': {'name': 'qubit_gate_us_e4'},
                'qecScheme': {'name': 'surface_code'},
                'errorBudget': DEFAULT_ERROR_BUDGET,
                'estimateType': 'singlePoint',
            },
        },
        {
            'name': 'gate_ns_e3_surface_code',
            'summary': 'Gate-based nanosecond preset with 1e-3 physical error rates and the surface code.',
            'requested_params': {
                'qubitParams': {'name': 'qubit_gate_ns_e3'},
                'qecScheme': {'name': 'surface_code'},
                'errorBudget': DEFAULT_ERROR_BUDGET,
                'estimateType': 'singlePoint',
            },
        },
        {
            'name': 'gate_ns_e4_surface_code',
            'summary': 'Gate-based nanosecond preset with 1e-4 physical error rates and the surface code.',
            'requested_params': {
                'qubitParams': {'name': 'qubit_gate_ns_e4'},
                'qecScheme': {'name': 'surface_code'},
                'errorBudget': DEFAULT_ERROR_BUDGET,
                'estimateType': 'singlePoint',
            },
        },
        {
            'name': 'maj_ns_e4_floquet_code',
            'summary': 'Majorana nanosecond preset with 1e-4 physical error rates and the Floquet code.',
            'requested_params': {
                'qubitParams': {'name': 'qubit_maj_ns_e4'},
                'qecScheme': {'name': 'floquet_code'},
                'errorBudget': DEFAULT_ERROR_BUDGET,
                'estimateType': 'singlePoint',
            },
        },
        {
            'name': 'maj_ns_e6_floquet_code',
            'summary': 'Majorana nanosecond preset with 1e-6 physical error rates and the Floquet code.',
            'requested_params': {
                'qubitParams': {'name': 'qubit_maj_ns_e6'},
                'qecScheme': {'name': 'floquet_code'},
                'errorBudget': DEFAULT_ERROR_BUDGET,
                'estimateType': 'singlePoint',
            },
        },
    ]


def build_azure_estimator_target_payload(logical_counts_payload: Mapping[str, Any]) -> Dict[str, Any]:
    targets = azure_estimator_target_profiles()
    return {
        'schema': 'compiler-project-azure-estimator-targets-v1',
        'source_artifacts': {
            'logical_counts': 'compiler_verification_project/artifacts/azure_resource_estimator_logical_counts.json',
            'family_frontier': 'compiler_verification_project/artifacts/family_frontier.json',
        },
        'estimator_backend': estimator_backend_metadata(),
        'logical_counts_binding': {
            'family_names': [row['family'] for row in logical_counts_payload['families']],
            'logical_counts_sha256': _canonical_json_sha256(logical_counts_payload),
        },
        'targets': targets,
        'notes': [
            'These target profiles mirror the official predefined qubit/QEC presets documented for the Microsoft Quantum Resource Estimator.',
            'Every target uses exact compiler-family logicalCounts as pre-layout input and keeps the estimator error budget fixed at 1e-3 for apples-to-apples comparison across target models.',
        ],
    }


def _import_logical_counts_class():
    try:
        estimator = import_module('qsharp.estimator')
    except ModuleNotFoundError:
        return None
    return getattr(estimator, 'LogicalCounts', None)


def _normalize_estimator_run(
    family_name: str,
    family_logical_counts: Mapping[str, Any],
    target: Mapping[str, Any],
    result: Mapping[str, Any],
) -> Dict[str, Any]:
    return {
        'family': family_name,
        'target': target['name'],
        'requested_params': deepcopy(target['requested_params']),
        'job_params': deepcopy(result['jobParams']),
        'reported_logical_counts': deepcopy(result['logicalCounts']),
        'physical_counts': deepcopy(result['physicalCounts']),
        'physical_counts_formatted': deepcopy(result['physicalCountsFormatted']),
        'logical_qubit': deepcopy(result['logicalQubit']),
        'tfactory': deepcopy(result['tfactory']),
        'bindings': {
            'input_logical_counts_sha256': _canonical_json_sha256(family_logical_counts),
            'target_params_sha256': _canonical_json_sha256(target['requested_params']),
        },
    }


def _family_estimator_summary(family_name: str, estimates: List[Dict[str, Any]]) -> Dict[str, Any]:
    best_space = min(
        estimates,
        key=lambda row: (
            row['physical_counts']['physicalQubits'],
            row['physical_counts']['runtime'],
            row['physical_counts']['rqops'],
        ),
    )
    best_runtime = min(
        estimates,
        key=lambda row: (
            row['physical_counts']['runtime'],
            row['physical_counts']['physicalQubits'],
            -row['physical_counts']['rqops'],
        ),
    )
    return {
        'family': family_name,
        'lowest_physical_qubits_target': {
            'target': best_space['target'],
            'physical_qubits': best_space['physical_counts']['physicalQubits'],
            'runtime': best_space['physical_counts']['runtime'],
        },
        'fastest_runtime_target': {
            'target': best_runtime['target'],
            'runtime': best_runtime['physical_counts']['runtime'],
            'physical_qubits': best_runtime['physical_counts']['physicalQubits'],
        },
    }


def _target_estimator_summary(target_name: str, family_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    estimates = [next(row for row in family['estimates'] if row['target'] == target_name) for family in family_rows]
    best_space = min(
        estimates,
        key=lambda row: (
            row['physical_counts']['physicalQubits'],
            row['physical_counts']['runtime'],
            row['physical_counts']['rqops'],
        ),
    )
    best_runtime = min(
        estimates,
        key=lambda row: (
            row['physical_counts']['runtime'],
            row['physical_counts']['physicalQubits'],
            -row['physical_counts']['rqops'],
        ),
    )
    return {
        'target': target_name,
        'lowest_physical_qubits_family': {
            'family': best_space['family'],
            'physical_qubits': best_space['physical_counts']['physicalQubits'],
            'runtime': best_space['physical_counts']['runtime'],
        },
        'fastest_runtime_family': {
            'family': best_runtime['family'],
            'runtime': best_runtime['physical_counts']['runtime'],
            'physical_qubits': best_runtime['physical_counts']['physicalQubits'],
        },
    }


def build_azure_estimator_results_payload(
    logical_counts_payload: Mapping[str, Any],
    target_payload: Mapping[str, Any],
) -> Dict[str, Any]:
    logical_counts_class = _import_logical_counts_class()
    if logical_counts_class is None:
        raise RuntimeError('qsharp.estimator.LogicalCounts is unavailable')

    family_rows: List[Dict[str, Any]] = []
    for family in logical_counts_payload['families']:
        estimates = []
        for target in target_payload['targets']:
            logical_counts = logical_counts_class(deepcopy(family['logicalCounts']))
            result = logical_counts.estimate(params=deepcopy(target['requested_params']))
            estimates.append(
                _normalize_estimator_run(
                    family_name=family['family'],
                    family_logical_counts=family['logicalCounts'],
                    target=target,
                    result=result,
                )
            )
        family_rows.append({
            'family': family['family'],
            'logical_counts': deepcopy(family['logicalCounts']),
            'logical_counts_notes': family['notes'],
            'estimates': estimates,
            'summary': _family_estimator_summary(family['family'], estimates),
        })

    target_summaries = [
        _target_estimator_summary(target['name'], family_rows)
        for target in target_payload['targets']
    ]
    return {
        'schema': 'compiler-project-azure-estimator-results-v1',
        'source_artifacts': {
            'logical_counts': 'compiler_verification_project/artifacts/azure_resource_estimator_logical_counts.json',
            'target_profiles': 'compiler_verification_project/artifacts/azure_resource_estimator_targets.json',
            'family_frontier': 'compiler_verification_project/artifacts/family_frontier.json',
        },
        'source_bindings': {
            'logical_counts_sha256': _canonical_json_sha256(logical_counts_payload),
            'target_profiles_sha256': _canonical_json_sha256(target_payload),
        },
        'estimator_backend': {
            **estimator_backend_metadata(),
            'package_versions': _estimator_versions(),
        },
        'families': family_rows,
        'target_summaries': target_summaries,
        'notes': [
            'These are recorded Microsoft Resource Estimator outputs for the exact compiler-family logicalCounts payload under the checked target profiles.',
            'The outputs are exact relative to the estimator model, the requested target parameters, and the checked logicalCounts input; they are not hardware-independent physical truths.',
            'The target summaries deliberately remain grouped by target profile instead of collapsing different hardware models into a single headline.',
        ],
    }


def build_or_load_azure_estimator_results_payload(
    logical_counts_payload: Mapping[str, Any],
    target_payload: Mapping[str, Any],
    artifact_path: Path,
) -> Dict[str, Any]:
    if _import_logical_counts_class() is not None:
        return build_azure_estimator_results_payload(logical_counts_payload, target_payload)
    if artifact_path.exists():
        return load_json(artifact_path)
    raise RuntimeError(
        'Physical estimator results require qsharp/qdk or an existing checked-in '
        f'artifact at {artifact_path}'
    )


__all__ = [
    'AZURE_ESTIMATOR_DOCS',
    'azure_estimator_target_profiles',
    'build_azure_estimator_results_payload',
    'build_azure_estimator_target_payload',
    'build_or_load_azure_estimator_results_payload',
    'estimator_backend_metadata',
]
