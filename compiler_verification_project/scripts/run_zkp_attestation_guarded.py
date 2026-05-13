#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = PROJECT_ROOT / 'compiler_verification_project' / 'zkp_attestation' / 'Cargo.toml'
HOST_BINARY_PATH = (
    PROJECT_ROOT
    / 'compiler_verification_project'
    / 'zkp_attestation'
    / 'target'
    / 'release'
    / 'secp256k1-zkp-attestation'
)
DEFAULT_INPUT_PATH = (
    PROJECT_ROOT / 'compiler_verification_project' / 'artifacts' / 'zkp_attestation_input.json'
)
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / 'compiler_verification_project' / 'artifacts'
HOST_MEMORY_WARNING_SWAP_FREE_KIB = 512 * 1024
POSTMORTEM_MIN_MEMORY_BYTES = 128 * 1024 * 1024
POSTMORTEM_MIN_CPU_NSEC = 100_000_000
SYSTEMD_SHOW_PROPERTIES = (
    'Result',
    'MemoryPeak',
    'CPUUsageNSec',
)
SYSTEMD_JOURNAL_LINES = 12

SAFE_ENV_DEFAULTS = {
    'SP1_WORKER_NUM_SPLICING_WORKERS': '1',
    'SP1_WORKER_SPLICING_BUFFER_SIZE': '1',
    'SP1_WORKER_NUM_CORE_WORKERS': '1',
    'SP1_WORKER_CORE_BUFFER_SIZE': '1',
    'SP1_WORKER_NUM_SETUP_WORKERS': '1',
    'SP1_WORKER_SETUP_BUFFER_SIZE': '1',
    'SP1_WORKER_NUM_PREPARE_REDUCE_WORKERS': '1',
    'SP1_WORKER_PREPARE_REDUCE_BUFFER_SIZE': '1',
    'SP1_WORKER_NUM_RECURSION_EXECUTOR_WORKERS': '1',
    'SP1_WORKER_RECURSION_EXECUTOR_BUFFER_SIZE': '1',
    'SP1_WORKER_NUM_RECURSION_PROVER_WORKERS': '1',
    'SP1_WORKER_RECURSION_PROVER_BUFFER_SIZE': '1',
    'SP1_WORKER_NUM_DEFERRED_WORKERS': '1',
    'SP1_WORKER_DEFERRED_BUFFER_SIZE': '1',
    'SP1_WORKER_NUMBER_OF_GAS_EXECUTORS': '1',
    'TRACE_CHUNK_SLOTS': '2',
    'MEMORY_LIMIT': str(16 * 1024 * 1024 * 1024),
}

BALANCED_ENV_DEFAULTS = {
    'SP1_WORKER_NUM_SPLICING_WORKERS': '4',
    'SP1_WORKER_SPLICING_BUFFER_SIZE': '4',
    'SP1_WORKER_NUM_CORE_WORKERS': '4',
    'SP1_WORKER_CORE_BUFFER_SIZE': '4',
    'SP1_WORKER_NUM_SETUP_WORKERS': '2',
    'SP1_WORKER_SETUP_BUFFER_SIZE': '2',
    'SP1_WORKER_NUM_PREPARE_REDUCE_WORKERS': '4',
    'SP1_WORKER_PREPARE_REDUCE_BUFFER_SIZE': '4',
    'SP1_WORKER_NUM_RECURSION_EXECUTOR_WORKERS': '4',
    'SP1_WORKER_RECURSION_EXECUTOR_BUFFER_SIZE': '4',
    'SP1_WORKER_NUM_RECURSION_PROVER_WORKERS': '4',
    'SP1_WORKER_RECURSION_PROVER_BUFFER_SIZE': '4',
    'SP1_WORKER_NUM_DEFERRED_WORKERS': '2',
    'SP1_WORKER_DEFERRED_BUFFER_SIZE': '2',
    'SP1_WORKER_NUMBER_OF_GAS_EXECUTORS': '2',
    'TRACE_CHUNK_SLOTS': '2',
    'MEMORY_LIMIT': str(16 * 1024 * 1024 * 1024),
}

THROUGHPUT_ENV_DEFAULTS = {
    'SP1_WORKER_NUM_SPLICING_WORKERS': '8',
    'SP1_WORKER_SPLICING_BUFFER_SIZE': '8',
    'SP1_WORKER_NUM_CORE_WORKERS': '8',
    'SP1_WORKER_CORE_BUFFER_SIZE': '8',
    'SP1_WORKER_NUM_SETUP_WORKERS': '4',
    'SP1_WORKER_SETUP_BUFFER_SIZE': '4',
    'SP1_WORKER_NUM_PREPARE_REDUCE_WORKERS': '8',
    'SP1_WORKER_PREPARE_REDUCE_BUFFER_SIZE': '8',
    'SP1_WORKER_NUM_RECURSION_EXECUTOR_WORKERS': '8',
    'SP1_WORKER_RECURSION_EXECUTOR_BUFFER_SIZE': '8',
    'SP1_WORKER_NUM_RECURSION_PROVER_WORKERS': '8',
    'SP1_WORKER_RECURSION_PROVER_BUFFER_SIZE': '8',
    'SP1_WORKER_NUM_DEFERRED_WORKERS': '4',
    'SP1_WORKER_DEFERRED_BUFFER_SIZE': '4',
    'SP1_WORKER_NUMBER_OF_GAS_EXECUTORS': '4',
    'TRACE_CHUNK_SLOTS': '2',
    'MEMORY_LIMIT': str(16 * 1024 * 1024 * 1024),
}

SAFE_SYSTEMD_PROPERTIES = (
    'CPUQuota=150%',
    'MemoryHigh=12G',
    'MemoryMax=16G',
    'IOWeight=20',
    'TasksMax=32',
)

BALANCED_SYSTEMD_PROPERTIES = (
    'CPUQuota=300%',
    'MemoryHigh=12G',
    'MemoryMax=16G',
    'IOWeight=20',
    'TasksMax=64',
)

THROUGHPUT_SYSTEMD_PROPERTIES = (
    'CPUQuota=500%',
    'MemoryHigh=12G',
    'MemoryMax=16G',
    'IOWeight=20',
    'TasksMax=96',
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run the SP1 attestation host under guarded local resource limits.')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--prove', action='store_true')
    parser.add_argument('--verify-proof-input')
    parser.add_argument('--groth16-verify-dir')
    parser.add_argument('--system', choices=('core', 'compressed', 'groth16', 'plonk'), default='core')
    parser.add_argument('--input', default=str(DEFAULT_INPUT_PATH))
    parser.add_argument('--output-dir', default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument(
        '--compressed-proof-input',
        help='Optional path to a saved compressed proof bundle for Groth16 wrap-only retries.',
    )
    parser.add_argument(
        '--wrap-proof-input',
        help='Optional path to a saved wrap proof bundle for Groth16 retries that skip shrink_wrap.',
    )
    parser.add_argument('--resource-profile', choices=('safe', 'balanced', 'throughput', 'full'), default='balanced')
    parser.add_argument('--write-core-fixture', action='store_true')
    parser.add_argument('--skip-build', action='store_true')
    parser.add_argument('--unsafe-no-host-limits', action='store_true')
    parser.add_argument(
        '--sp1-env',
        action='append',
        default=[],
        metavar='NAME=VALUE',
        help='Extra SP1 environment override to inject into the host process. May be repeated.',
    )
    parser.add_argument(
        '--systemd-property',
        action='append',
        default=[],
        metavar='NAME=VALUE',
        help='Extra systemd-run property override to apply around the host binary. May be repeated.',
    )
    parser.add_argument('--print-command', action='store_true')
    return parser.parse_args()


def default_tool_env(env: dict[str, str]) -> None:
    sp1_bin = Path.home() / '.sp1' / 'bin'
    if sp1_bin.exists():
        env['PATH'] = f'{sp1_bin}:{env.get("PATH", "")}'
    protoc = Path('/tmp/protoc-34.1/bin/protoc')
    if protoc.exists() and 'PROTOC' not in env:
        env['PROTOC'] = str(protoc)
    libclang = Path.home() / '.local' / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages' / 'clang' / 'native'
    if libclang.exists() and 'LIBCLANG_PATH' not in env:
        env['LIBCLANG_PATH'] = str(libclang)
    env.setdefault(
        'BINDGEN_EXTRA_CLANG_ARGS',
        '-I/usr/lib/gcc/x86_64-redhat-linux/15/include -I/usr/include',
    )
    env.setdefault('CARGO_BUILD_JOBS', '1')
    env.setdefault('GOFLAGS', '-p=1')


def parse_assignment(assignment: str) -> tuple[str, str]:
    name, separator, value = assignment.partition('=')
    if not separator or not name or not value:
        raise SystemExit(f'invalid NAME=VALUE assignment: {assignment!r}')
    return name, value


def parse_size_to_kib(size: str) -> int:
    normalized = size.strip().upper()
    if normalized.endswith('G'):
        return int(float(normalized[:-1]) * 1024 * 1024)
    if normalized.endswith('M'):
        return int(float(normalized[:-1]) * 1024)
    if normalized.endswith('K'):
        return int(float(normalized[:-1]))
    return int(int(normalized) / 1024)


def format_kib_as_gib(kib: int) -> str:
    return f'{kib / (1024 * 1024):.1f} GiB'


def merge_properties(defaults: Sequence[str], overrides: Sequence[str]) -> tuple[str, ...]:
    merged: dict[str, str] = {}
    for assignment in defaults:
        name, value = parse_assignment(assignment)
        merged[name] = value
    for assignment in overrides:
        name, value = parse_assignment(assignment)
        merged[name] = value
    return tuple(f'{name}={value}' for name, value in merged.items())


def guarded_env(resource_profile: str, extra_assignments: Sequence[str] = ()) -> dict[str, str]:
    env = os.environ.copy()
    default_tool_env(env)
    if resource_profile == 'safe':
        for name, value in SAFE_ENV_DEFAULTS.items():
            env.setdefault(name, value)
    if resource_profile == 'balanced':
        for name, value in BALANCED_ENV_DEFAULTS.items():
            env.setdefault(name, value)
    if resource_profile == 'throughput':
        for name, value in THROUGHPUT_ENV_DEFAULTS.items():
            env.setdefault(name, value)
    for assignment in extra_assignments:
        name, value = parse_assignment(assignment)
        env[name] = value
    return env


def read_meminfo() -> Mapping[str, int]:
    meminfo: dict[str, int] = {}
    with Path('/proc/meminfo').open() as file:
        for line in file:
            name, _, value = line.partition(':')
            if not value:
                continue
            amount = value.strip().split()[0]
            meminfo[name] = int(amount)
    return meminfo


def build_command() -> list[str]:
    return [
        'cargo',
        'build',
        '-p',
        'secp256k1-zkp-attestation-script',
        '--release',
        '--manifest-path',
        str(MANIFEST_PATH),
    ]


def normalize_host_path(raw_path: str) -> str:
    candidate = Path(raw_path).expanduser()
    if candidate.is_absolute():
        return str(candidate)
    return str((Path.cwd() / candidate).resolve())


def host_command(args: argparse.Namespace) -> list[str]:
    host_resource_profile = 'full' if args.resource_profile == 'throughput' else args.resource_profile
    command = [str(HOST_BINARY_PATH)]
    if args.execute:
        command.append('--execute')
    if args.prove:
        command.append('--prove')
    verify_proof_input = getattr(args, 'verify_proof_input', None)
    if verify_proof_input:
        command.extend(['--verify-proof-input', normalize_host_path(verify_proof_input)])
    groth16_verify_dir = getattr(args, 'groth16_verify_dir', None)
    if groth16_verify_dir:
        command.extend(['--groth16-verify-dir', normalize_host_path(groth16_verify_dir)])
    if args.write_core_fixture:
        command.append('--write-core-fixture')
    command.extend([
        '--system',
        args.system,
        '--resource-profile',
        host_resource_profile,
        '--input',
        normalize_host_path(args.input),
    ])
    compressed_proof_input = getattr(args, 'compressed_proof_input', None)
    if compressed_proof_input:
        command.extend(['--compressed-proof-input', normalize_host_path(compressed_proof_input)])
    wrap_proof_input = getattr(args, 'wrap_proof_input', None)
    if wrap_proof_input:
        command.extend(['--wrap-proof-input', normalize_host_path(wrap_proof_input)])
    if args.output_dir:
        command.extend(['--output-dir', normalize_host_path(args.output_dir)])
    return command


def with_priority(command: Sequence[str]) -> list[str]:
    priority_prefix: list[str] = []
    if shutil.which('nice') is not None:
        priority_prefix.extend(['nice', '-n', '15'])
    if shutil.which('ionice') is not None:
        priority_prefix.extend(['ionice', '-c', '3'])
    return priority_prefix + list(command)


def systemd_properties(resource_profile: str, overrides: Sequence[str] = ()) -> Sequence[str]:
    if resource_profile == 'safe':
        return merge_properties(SAFE_SYSTEMD_PROPERTIES, overrides)
    if resource_profile == 'balanced':
        return merge_properties(BALANCED_SYSTEMD_PROPERTIES, overrides)
    if resource_profile == 'throughput':
        return merge_properties(THROUGHPUT_SYSTEMD_PROPERTIES, overrides)
    return merge_properties((), overrides)


def with_host_limits(
    command: Sequence[str],
    disabled: bool,
    resource_profile: str,
    extra_properties: Sequence[str] = (),
    unit_base_name: str | None = None,
) -> list[str]:
    priority_command = with_priority(command)
    if disabled or shutil.which('systemd-run') is None:
        return priority_command
    wrapped = ['systemd-run', '--user', '--scope', '--quiet']
    if unit_base_name is not None:
        wrapped.extend(['--unit', unit_base_name])
    for prop in systemd_properties(resource_profile, extra_properties):
        wrapped.extend(['--property', prop])
    wrapped.extend(priority_command)
    return wrapped


def host_memory_pressure_warning(resource_profile: str, extra_properties: Sequence[str]) -> str | None:
    properties = systemd_properties(resource_profile, extra_properties)
    memory_high = next((value for name, value in (parse_assignment(prop) for prop in properties) if name == 'MemoryHigh'), None)
    if memory_high is None:
        return None
    meminfo = read_meminfo()
    available_kib = meminfo.get('MemAvailable')
    swap_free_kib = meminfo.get('SwapFree')
    if available_kib is None or swap_free_kib is None:
        return None
    requested_high_kib = parse_size_to_kib(memory_high)
    if available_kib >= requested_high_kib and swap_free_kib >= HOST_MEMORY_WARNING_SWAP_FREE_KIB:
        return None
    return (
        '[zkp-attestation] host memory pressure warning: '
        f'MemAvailable={format_kib_as_gib(available_kib)}, '
        f'SwapFree={format_kib_as_gib(swap_free_kib)}, '
        f'RequestedMemoryHigh={format_kib_as_gib(requested_high_kib)}. '
        'Scoped proof runs may be OOM-killed by external pressure before they hit the wrapper caps.'
    )


def systemd_unit_base_name(args: argparse.Namespace) -> str:
    if args.execute:
        action = 'execute'
    elif getattr(args, 'verify_proof_input', None):
        action = f'verify-{args.system}'
    else:
        action = f'prove-{args.system}'
    return f'zkp-attestation-{action}-{args.resource_profile}-{os.getpid()}-{int(time.time())}'


def systemd_scope_name(unit_base_name: str) -> str:
    return f'{unit_base_name}.scope'


def systemd_show(unit_name: str) -> dict[str, str]:
    try:
        result = subprocess.run(
            [
                'systemctl',
                '--user',
                'show',
                unit_name,
                *[f'--property={name}' for name in SYSTEMD_SHOW_PROPERTIES],
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return {}
    if result.returncode != 0:
        return {}
    details: dict[str, str] = {}
    for line in result.stdout.splitlines():
        name, separator, value = line.partition('=')
        if not separator or name not in SYSTEMD_SHOW_PROPERTIES or not value:
            continue
        details[name] = value.strip()
    return details


def systemd_journal(unit_name: str) -> str:
    try:
        result = subprocess.run(
            [
                'journalctl',
                '--user',
                '-u',
                unit_name,
                '--no-pager',
                '-n',
                str(SYSTEMD_JOURNAL_LINES),
                '-o',
                'cat',
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return ''
    if result.returncode != 0:
        return ''
    return result.stdout.strip()


def format_bytes_as_gib(raw_value: str) -> str:
    return f'{int(raw_value) / (1024 ** 3):.1f} GiB'


def format_nsec_as_seconds(raw_value: str) -> str:
    return f'{int(raw_value) / 1_000_000_000:.2f}s'


def systemd_postmortem(unit_name: str, exit_status: int | None = None) -> str | None:
    details = systemd_show(unit_name)
    journal = systemd_journal(unit_name)
    if not details and not journal:
        return None
    fields: list[str] = []
    if exit_status is not None:
        fields.append(f'ExitStatus={exit_status}')
    result = details.get('Result')
    if result and result != 'success':
        fields.append(f'Result={result}')
    memory_peak = details.get('MemoryPeak')
    if (
        memory_peak
        and memory_peak != '[not set]'
        and int(memory_peak) >= POSTMORTEM_MIN_MEMORY_BYTES
    ):
        fields.append(f'MemoryPeak={format_bytes_as_gib(memory_peak)}')
    cpu_usage_nsec = details.get('CPUUsageNSec')
    if (
        cpu_usage_nsec
        and cpu_usage_nsec != '[not set]'
        and int(cpu_usage_nsec) >= POSTMORTEM_MIN_CPU_NSEC
    ):
        fields.append(f'CPUUsage={format_nsec_as_seconds(cpu_usage_nsec)}')
    summary = f'[zkp-attestation] systemd scope {unit_name}'
    if fields:
        summary = f'{summary}: ' + ', '.join(fields)
    if not journal:
        return summary
    return f'{summary}\n[zkp-attestation] recent journal:\n{journal}'


def main() -> None:
    args = parse_args()
    if sum(bool(flag) for flag in (args.execute, args.prove, args.verify_proof_input)) != 1:
        raise SystemExit('specify exactly one of --execute, --prove, or --verify-proof-input')
    env = guarded_env(args.resource_profile, args.sp1_env)
    if args.prove and 'RUST_LOG' not in env:
        env['RUST_LOG'] = 'sp1_prover=info,sp1_sdk=info'
    memory_warning = host_memory_pressure_warning(args.resource_profile, args.systemd_property)
    unit_base_name = None
    scope_name = None
    if not args.unsafe_no_host_limits and shutil.which('systemd-run') is not None:
        unit_base_name = systemd_unit_base_name(args)
        scope_name = systemd_scope_name(unit_base_name)
    build = with_priority(build_command())
    command = with_host_limits(
        host_command(args),
        args.unsafe_no_host_limits,
        args.resource_profile,
        args.systemd_property,
        unit_base_name,
    )
    if args.print_command:
        if memory_warning:
            print(memory_warning, file=sys.stderr)
        if scope_name is not None:
            print(f'[zkp-attestation] systemd scope {scope_name}', file=sys.stderr)
        if not args.skip_build:
            print(' '.join(build))
        print(' '.join(command))
        return
    if memory_warning:
        print(memory_warning, file=sys.stderr)
    if scope_name is not None:
        print(f'[zkp-attestation] systemd scope {scope_name}', file=sys.stderr)
    if not args.skip_build:
        subprocess.run(build, cwd=PROJECT_ROOT, env=env, check=True)
    try:
        subprocess.run(command, cwd=PROJECT_ROOT, env=env, check=True)
    except subprocess.CalledProcessError as error:
        if scope_name is not None:
            postmortem = systemd_postmortem(scope_name, error.returncode)
            if postmortem:
                print(postmortem, file=sys.stderr)
        raise SystemExit(error.returncode) from None


if __name__ == '__main__':
    main()
