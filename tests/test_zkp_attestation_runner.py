from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = REPO_ROOT / 'compiler_verification_project' / 'scripts' / 'run_zkp_attestation_guarded.py'
SPEC = importlib.util.spec_from_file_location('zkp_attestation_runner', RUNNER_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_guarded_env_applies_safe_defaults() -> None:
    env = MODULE.guarded_env('safe')
    assert env['SP1_WORKER_NUM_CORE_WORKERS'] == '1'
    assert env['SP1_WORKER_NUM_RECURSION_PROVER_WORKERS'] == '1'
    assert env['TRACE_CHUNK_SLOTS'] == '2'
    assert env['MEMORY_LIMIT'] == str(16 * 1024 * 1024 * 1024)
    assert env['CARGO_BUILD_JOBS'] == '1'
    assert env['GOFLAGS'] == '-p=1'


def test_guarded_env_applies_balanced_defaults() -> None:
    env = MODULE.guarded_env('balanced')
    assert env['SP1_WORKER_NUM_CORE_WORKERS'] == '4'
    assert env['SP1_WORKER_NUM_RECURSION_PROVER_WORKERS'] == '4'
    assert env['TRACE_CHUNK_SLOTS'] == '2'
    assert env['MEMORY_LIMIT'] == str(16 * 1024 * 1024 * 1024)


def test_guarded_env_applies_throughput_defaults() -> None:
    env = MODULE.guarded_env('throughput')
    assert env['SP1_WORKER_NUM_CORE_WORKERS'] == '8'
    assert env['SP1_WORKER_NUM_RECURSION_PROVER_WORKERS'] == '8'
    assert env['SP1_WORKER_NUM_SETUP_WORKERS'] == '4'
    assert env['TRACE_CHUNK_SLOTS'] == '2'
    assert env['MEMORY_LIMIT'] == str(16 * 1024 * 1024 * 1024)


def test_guarded_env_applies_explicit_overrides() -> None:
    env = MODULE.guarded_env(
        'balanced',
        ['MINIMAL_TRACE_CHUNK_THRESHOLD=65536', 'SP1_WORKER_NUM_CORE_WORKERS=3'],
    )
    assert env['MINIMAL_TRACE_CHUNK_THRESHOLD'] == '65536'
    assert env['SP1_WORKER_NUM_CORE_WORKERS'] == '3'


def test_build_command_targets_script_package() -> None:
    command = MODULE.build_command()
    assert command == [
        'cargo',
        'build',
        '-p',
        'secp256k1-zkp-attestation-script',
        '--release',
        '--manifest-path',
        str(MODULE.MANIFEST_PATH),
    ]


def test_host_command_targets_guarded_host_binary() -> None:
    class Args:
        execute = False
        prove = True
        write_core_fixture = False
        system = 'groth16'
        resource_profile = 'safe'
        input = 'compiler_verification_project/artifacts/zkp_attestation_input.json'
        output_dir = None

    command = MODULE.host_command(Args())
    assert command[0] == str(MODULE.HOST_BINARY_PATH)
    assert command[-7:] == [
        '--prove',
        '--system',
        'groth16',
        '--resource-profile',
        'safe',
        '--input',
        str(MODULE.PROJECT_ROOT / 'compiler_verification_project' / 'artifacts' / 'zkp_attestation_input.json'),
    ]


def test_host_command_accepts_compressed_mode() -> None:
    class Args:
        execute = False
        prove = True
        write_core_fixture = False
        system = 'compressed'
        resource_profile = 'balanced'
        input = 'compiler_verification_project/artifacts/zkp_attestation_input.json'
        output_dir = None

    command = MODULE.host_command(Args())
    assert command[-7:] == [
        '--prove',
        '--system',
        'compressed',
        '--resource-profile',
        'balanced',
        '--input',
        str(MODULE.PROJECT_ROOT / 'compiler_verification_project' / 'artifacts' / 'zkp_attestation_input.json'),
    ]


def test_host_command_passes_compressed_proof_input() -> None:
    class Args:
        execute = False
        prove = True
        write_core_fixture = False
        system = 'groth16'
        resource_profile = 'balanced'
        input = 'compiler_verification_project/artifacts/zkp_attestation_input.json'
        output_dir = None
        compressed_proof_input = 'tmp/zkp_attestation_proof_compressed.bin'

    command = MODULE.host_command(Args())
    assert '--compressed-proof-input' in command
    flag_index = command.index('--compressed-proof-input')
    assert command[flag_index + 1] == str(
        MODULE.PROJECT_ROOT / 'tmp' / 'zkp_attestation_proof_compressed.bin'
    )


def test_host_command_passes_wrap_proof_input() -> None:
    class Args:
        execute = False
        prove = True
        write_core_fixture = False
        system = 'groth16'
        resource_profile = 'balanced'
        input = 'compiler_verification_project/artifacts/zkp_attestation_input.json'
        output_dir = None
        compressed_proof_input = None
        wrap_proof_input = 'tmp/zkp_attestation_wrap_proof.bin'

    command = MODULE.host_command(Args())
    assert '--wrap-proof-input' in command
    flag_index = command.index('--wrap-proof-input')
    assert command[flag_index + 1] == str(
        MODULE.PROJECT_ROOT / 'tmp' / 'zkp_attestation_wrap_proof.bin'
    )


def test_host_command_passes_verify_proof_input() -> None:
    class Args:
        execute = False
        prove = False
        verify_proof_input = 'tmp/zkp_attestation_proof_groth16.bin'
        groth16_verify_dir = 'tmp/zkp_attestation_groth16_verifier'
        write_core_fixture = False
        system = 'groth16'
        resource_profile = 'balanced'
        input = 'compiler_verification_project/artifacts/zkp_attestation_input.json'
        output_dir = None
        compressed_proof_input = None
        wrap_proof_input = None

    command = MODULE.host_command(Args())
    assert '--verify-proof-input' in command
    flag_index = command.index('--verify-proof-input')
    assert command[flag_index + 1] == str(
        MODULE.PROJECT_ROOT / 'tmp' / 'zkp_attestation_proof_groth16.bin'
    )
    assert '--groth16-verify-dir' in command
    dir_index = command.index('--groth16-verify-dir')
    assert command[dir_index + 1] == str(
        MODULE.PROJECT_ROOT / 'tmp' / 'zkp_attestation_groth16_verifier'
    )


def test_host_command_supports_output_dir_override() -> None:
    class Args:
        execute = True
        prove = False
        write_core_fixture = True
        system = 'core'
        resource_profile = 'safe'
        input = 'tmp/zkp_attestation_input.json'
        output_dir = 'tmp/zkp_case1'

    command = MODULE.host_command(Args())
    assert command[-10:] == [
        '--execute',
        '--write-core-fixture',
        '--system',
        'core',
        '--resource-profile',
        'safe',
        '--input',
        str(MODULE.PROJECT_ROOT / 'tmp' / 'zkp_attestation_input.json'),
        '--output-dir',
        str(MODULE.PROJECT_ROOT / 'tmp' / 'zkp_case1'),
    ]


def test_host_command_maps_throughput_profile_to_full_host_flag() -> None:
    class Args:
        execute = False
        prove = True
        write_core_fixture = False
        system = 'core'
        resource_profile = 'throughput'
        input = '/tmp/zkp_attestation_input.json'
        output_dir = None

    command = MODULE.host_command(Args())
    assert command[-7:] == [
        '--prove',
        '--system',
        'core',
        '--resource-profile',
        'full',
        '--input',
        '/tmp/zkp_attestation_input.json',
    ]


def test_parse_args_accepts_skip_build_flag() -> None:
    original_argv = sys.argv
    try:
        sys.argv = [
            'run_zkp_attestation_guarded.py',
            '--prove',
            '--skip-build',
            '--resource-profile',
            'throughput',
            '--compressed-proof-input',
            '/tmp/zkp_attestation_proof_compressed.bin',
            '--wrap-proof-input',
            '/tmp/zkp_attestation_wrap_proof.bin',
            '--verify-proof-input',
            '/tmp/zkp_attestation_proof_groth16.bin',
            '--groth16-verify-dir',
            '/tmp/zkp_attestation_groth16_verifier',
            '--sp1-env',
            'ELEMENT_THRESHOLD=201326592',
            '--systemd-property',
            'MemoryMax=12G',
        ]
        args = MODULE.parse_args()
    finally:
        sys.argv = original_argv
    assert args.prove is True
    assert args.skip_build is True
    assert args.resource_profile == 'throughput'
    assert args.compressed_proof_input == '/tmp/zkp_attestation_proof_compressed.bin'
    assert args.wrap_proof_input == '/tmp/zkp_attestation_wrap_proof.bin'
    assert args.verify_proof_input == '/tmp/zkp_attestation_proof_groth16.bin'
    assert args.groth16_verify_dir == '/tmp/zkp_attestation_groth16_verifier'
    assert args.sp1_env == ['ELEMENT_THRESHOLD=201326592']
    assert args.systemd_property == ['MemoryMax=12G']


def test_parse_args_accepts_compressed_system() -> None:
    original_argv = sys.argv
    try:
        sys.argv = ['run_zkp_attestation_guarded.py', '--prove', '--system', 'compressed']
        args = MODULE.parse_args()
    finally:
        sys.argv = original_argv
    assert args.prove is True
    assert args.system == 'compressed'


def test_parse_args_uses_absolute_defaults() -> None:
    original_argv = sys.argv
    try:
        sys.argv = ['run_zkp_attestation_guarded.py', '--execute']
        args = MODULE.parse_args()
    finally:
        sys.argv = original_argv
    assert args.input == str(MODULE.DEFAULT_INPUT_PATH)
    assert args.output_dir == str(MODULE.DEFAULT_OUTPUT_DIR)


def test_normalize_host_path_resolves_relative_to_invocation_cwd() -> None:
    original_cwd = Path.cwd()
    try:
        os.chdir(MODULE.PROJECT_ROOT)
        resolved = MODULE.normalize_host_path('compiler_verification_project/artifacts/zkp_attestation_input.json')
    finally:
        os.chdir(original_cwd)
    assert resolved == str(MODULE.PROJECT_ROOT / 'compiler_verification_project' / 'artifacts' / 'zkp_attestation_input.json')


def test_systemd_wrapper_applies_limits_when_available() -> None:
    wrapped = MODULE.with_host_limits(['cargo', 'run'], disabled=False, resource_profile='safe')
    assert wrapped[0] == 'systemd-run'
    assert '--property' in wrapped
    assert 'CPUQuota=150%' in wrapped
    assert 'nice' in wrapped


def test_systemd_wrapper_passes_explicit_unit_name() -> None:
    wrapped = MODULE.with_host_limits(
        ['cargo', 'run'],
        disabled=False,
        resource_profile='safe',
        unit_base_name='zkp-attestation-test',
    )
    assert '--unit' in wrapped
    unit_index = wrapped.index('--unit')
    assert wrapped[unit_index + 1] == 'zkp-attestation-test'


def test_systemd_wrapper_uses_profile_specific_limits() -> None:
    wrapped = MODULE.with_host_limits(['cargo', 'run'], disabled=False, resource_profile='throughput')
    assert 'CPUQuota=500%' in wrapped
    assert 'TasksMax=96' in wrapped


def test_systemd_wrapper_allows_explicit_property_overrides() -> None:
    wrapped = MODULE.with_host_limits(
        ['cargo', 'run'],
        disabled=False,
        resource_profile='balanced',
        extra_properties=['CPUQuota=250%', 'MemoryMax=12G'],
    )
    assert 'CPUQuota=250%' in wrapped
    assert 'MemoryMax=12G' in wrapped
    assert 'CPUQuota=300%' not in wrapped
    assert 'MemoryMax=16G' not in wrapped


def test_parse_assignment_requires_name_value_shape() -> None:
    try:
        MODULE.parse_assignment('BROKEN')
    except SystemExit as exc:
        assert "invalid NAME=VALUE assignment" in str(exc)
        return
    raise AssertionError('expected parse_assignment to reject malformed override')


def test_parse_size_to_kib_supports_systemd_suffixes() -> None:
    assert MODULE.parse_size_to_kib('12G') == 12 * 1024 * 1024
    assert MODULE.parse_size_to_kib('512M') == 512 * 1024
    assert MODULE.parse_size_to_kib('1024K') == 1024


def test_host_memory_pressure_warning_reports_tight_host() -> None:
    original = MODULE.read_meminfo
    try:
        MODULE.read_meminfo = lambda: {'MemAvailable': 6 * 1024 * 1024, 'SwapFree': 128 * 1024}
        warning = MODULE.host_memory_pressure_warning('balanced', [])
    finally:
        MODULE.read_meminfo = original
    assert warning is not None
    assert 'MemAvailable=6.0 GiB' in warning
    assert 'RequestedMemoryHigh=12.0 GiB' in warning


def test_host_memory_pressure_warning_skips_healthy_host() -> None:
    original = MODULE.read_meminfo
    try:
        MODULE.read_meminfo = lambda: {'MemAvailable': 20 * 1024 * 1024, 'SwapFree': 2 * 1024 * 1024}
        warning = MODULE.host_memory_pressure_warning('balanced', [])
    finally:
        MODULE.read_meminfo = original
    assert warning is None


def test_systemd_unit_base_name_reflects_requested_mode() -> None:
    class Args:
        execute = False
        prove = True
        system = 'core'
        resource_profile = 'balanced'

    original_time = MODULE.time.time
    original_pid = MODULE.os.getpid
    try:
        MODULE.time.time = lambda: 1234567890
        MODULE.os.getpid = lambda: 4321
        unit_name = MODULE.systemd_unit_base_name(Args())
    finally:
        MODULE.time.time = original_time
        MODULE.os.getpid = original_pid
    assert unit_name == 'zkp-attestation-prove-core-balanced-4321-1234567890'
    assert MODULE.systemd_scope_name(unit_name) == f'{unit_name}.scope'


def test_systemd_postmortem_formats_summary_and_journal() -> None:
    class CompletedProcess:
        def __init__(self, stdout: str, returncode: int = 0) -> None:
            self.stdout = stdout
            self.returncode = returncode

    original_run = MODULE.subprocess.run

    def fake_run(command, capture_output, text, check):
        if command[0] == 'systemctl':
            return CompletedProcess(
                'Result=oom-kill\nMemoryPeak=6657199308\nCPUUsageNSec=113688000000\n'
            )
        if command[0] == 'journalctl':
            return CompletedProcess('started scope\nkilled by OOM killer')
        raise AssertionError(f'unexpected command: {command}')

    try:
        MODULE.subprocess.run = fake_run
        summary = MODULE.systemd_postmortem('zkp-attestation.scope', -9)
    finally:
        MODULE.subprocess.run = original_run

    assert summary is not None
    assert 'ExitStatus=-9' in summary
    assert 'Result=oom-kill' in summary
    assert 'MemoryPeak=6.2 GiB' in summary
    assert 'CPUUsage=113.69s' in summary
    assert 'killed by OOM killer' in summary


def test_systemd_postmortem_skips_tiny_resource_counters() -> None:
    class CompletedProcess:
        def __init__(self, stdout: str, returncode: int = 0) -> None:
            self.stdout = stdout
            self.returncode = returncode

    original_run = MODULE.subprocess.run

    def fake_run(command, capture_output, text, check):
        if command[0] == 'systemctl':
            return CompletedProcess(
                'Result=success\nMemoryPeak=4096\nCPUUsageNSec=12000\n'
            )
        if command[0] == 'journalctl':
            return CompletedProcess('')
        raise AssertionError(f'unexpected command: {command}')

    try:
        MODULE.subprocess.run = fake_run
        summary = MODULE.systemd_postmortem('zkp-attestation.scope', 101)
    finally:
        MODULE.subprocess.run = original_run

    assert summary == '[zkp-attestation] systemd scope zkp-attestation.scope: ExitStatus=101'
