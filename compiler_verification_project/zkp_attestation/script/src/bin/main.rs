#[path = "../core_only.rs"]
mod core_only;
#[path = "../wrap_only.rs"]
mod wrap_only;

use clap::{Parser, ValueEnum};
use core_only::CoreOnlyBlockingProver;
use secp256k1_zkp_attestation_lib::{
    fixture_json, PreparedAttestationInput, PublicValues,
};
use sp1_sdk::{
    blocking::{LightProver, ProveRequest, Prover, ProverClient},
    include_elf, Elf, HashableKey, SP1ProofWithPublicValues, SP1Stdin,
};
use sp1_sdk::ProvingKey;
use std::{
    env, fs, io::Write,
    path::{Path, PathBuf},
    time::Instant,
};
use wrap_only::{verify_groth16_bundle_path_with_default_vks, WrapOnlyBlockingProver};

const ATTESTATION_ELF: Elf = include_elf!("secp256k1-zkp-attestation-program");
const SAFE_RESOURCE_DEFAULTS: [(&str, &str); 15] = [
    ("SP1_WORKER_NUM_SPLICING_WORKERS", "1"),
    ("SP1_WORKER_SPLICING_BUFFER_SIZE", "1"),
    ("SP1_WORKER_NUM_CORE_WORKERS", "1"),
    ("SP1_WORKER_CORE_BUFFER_SIZE", "1"),
    ("SP1_WORKER_NUM_SETUP_WORKERS", "1"),
    ("SP1_WORKER_SETUP_BUFFER_SIZE", "1"),
    ("SP1_WORKER_NUM_PREPARE_REDUCE_WORKERS", "1"),
    ("SP1_WORKER_PREPARE_REDUCE_BUFFER_SIZE", "1"),
    ("SP1_WORKER_NUM_RECURSION_EXECUTOR_WORKERS", "1"),
    ("SP1_WORKER_RECURSION_EXECUTOR_BUFFER_SIZE", "1"),
    ("SP1_WORKER_NUM_RECURSION_PROVER_WORKERS", "1"),
    ("SP1_WORKER_RECURSION_PROVER_BUFFER_SIZE", "1"),
    ("SP1_WORKER_NUM_DEFERRED_WORKERS", "1"),
    ("SP1_WORKER_DEFERRED_BUFFER_SIZE", "1"),
    ("SP1_WORKER_NUMBER_OF_GAS_EXECUTORS", "1"),
];
const BALANCED_RESOURCE_DEFAULTS: [(&str, &str); 15] = [
    ("SP1_WORKER_NUM_SPLICING_WORKERS", "4"),
    ("SP1_WORKER_SPLICING_BUFFER_SIZE", "4"),
    ("SP1_WORKER_NUM_CORE_WORKERS", "4"),
    ("SP1_WORKER_CORE_BUFFER_SIZE", "4"),
    ("SP1_WORKER_NUM_SETUP_WORKERS", "2"),
    ("SP1_WORKER_SETUP_BUFFER_SIZE", "2"),
    ("SP1_WORKER_NUM_PREPARE_REDUCE_WORKERS", "4"),
    ("SP1_WORKER_PREPARE_REDUCE_BUFFER_SIZE", "4"),
    ("SP1_WORKER_NUM_RECURSION_EXECUTOR_WORKERS", "4"),
    ("SP1_WORKER_RECURSION_EXECUTOR_BUFFER_SIZE", "4"),
    ("SP1_WORKER_NUM_RECURSION_PROVER_WORKERS", "4"),
    ("SP1_WORKER_RECURSION_PROVER_BUFFER_SIZE", "4"),
    ("SP1_WORKER_NUM_DEFERRED_WORKERS", "2"),
    ("SP1_WORKER_DEFERRED_BUFFER_SIZE", "2"),
    ("SP1_WORKER_NUMBER_OF_GAS_EXECUTORS", "2"),
];
const THROUGHPUT_RESOURCE_DEFAULTS: [(&str, &str); 15] = [
    ("SP1_WORKER_NUM_SPLICING_WORKERS", "8"),
    ("SP1_WORKER_SPLICING_BUFFER_SIZE", "8"),
    ("SP1_WORKER_NUM_CORE_WORKERS", "8"),
    ("SP1_WORKER_CORE_BUFFER_SIZE", "8"),
    ("SP1_WORKER_NUM_SETUP_WORKERS", "4"),
    ("SP1_WORKER_SETUP_BUFFER_SIZE", "4"),
    ("SP1_WORKER_NUM_PREPARE_REDUCE_WORKERS", "8"),
    ("SP1_WORKER_PREPARE_REDUCE_BUFFER_SIZE", "8"),
    ("SP1_WORKER_NUM_RECURSION_EXECUTOR_WORKERS", "8"),
    ("SP1_WORKER_RECURSION_EXECUTOR_BUFFER_SIZE", "8"),
    ("SP1_WORKER_NUM_RECURSION_PROVER_WORKERS", "8"),
    ("SP1_WORKER_RECURSION_PROVER_BUFFER_SIZE", "8"),
    ("SP1_WORKER_NUM_DEFERRED_WORKERS", "4"),
    ("SP1_WORKER_DEFERRED_BUFFER_SIZE", "4"),
    ("SP1_WORKER_NUMBER_OF_GAS_EXECUTORS", "4"),
];
const SAFE_GROTH16_DEFAULTS: [(&str, &str); 2] = [
    ("TRACE_CHUNK_SLOTS", "2"),
    ("MEMORY_LIMIT", "17179869184"),
];

#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    #[arg(long)]
    execute: bool,

    #[arg(long)]
    prove: bool,

    #[arg(
        long,
        help = "Verify an existing binary proof bundle against the current program verification key."
    )]
    verify_proof_input: Option<String>,

    #[arg(
        long,
        help = "When used with --execute --system core, also emit zkp_attestation_fixture_core.json using the current program verification key."
    )]
    write_core_fixture: bool,

    #[arg(long, value_enum, default_value = "core")]
    system: ProofSystem,

    #[arg(long, value_enum, default_value = "balanced")]
    resource_profile: ResourceProfile,

    #[arg(
        long,
        default_value = "../../artifacts/zkp_attestation_input.json",
        help = "Path to the compiler-project ZK attestation input bundle."
    )]
    input: String,

    #[arg(
        long,
        default_value = "../../artifacts",
        help = "Directory where public values and proof fixtures are written."
    )]
    output_dir: String,

    #[arg(
        long,
        help = "When used with --prove --system groth16, wrap a previously saved compressed proof bundle instead of recomputing compression."
    )]
    compressed_proof_input: Option<String>,

    #[arg(
        long,
        help = "When used with --prove --system groth16, resume from a previously saved wrap proof bundle instead of recomputing shrink_wrap."
    )]
    wrap_proof_input: Option<String>,

    #[arg(
        long,
        help = "Directory containing groth16 verification artifacts such as groth16_vk.bin for standalone bundle verification."
    )]
    groth16_verify_dir: Option<String>,
}

#[derive(Copy, Clone, PartialEq, Eq, PartialOrd, Ord, ValueEnum, Debug)]
enum ProofSystem {
    Core,
    Compressed,
    Groth16,
    Plonk,
}

#[derive(Copy, Clone, PartialEq, Eq, PartialOrd, Ord, ValueEnum, Debug)]
enum ResourceProfile {
    Safe,
    Balanced,
    Throughput,
    Full,
}

fn resolve_path(path: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join(path)
}

fn load_input(path: &str) -> PreparedAttestationInput {
    let absolute = resolve_path(path);
    let bytes = fs::read(&absolute).unwrap_or_else(|error| panic!("failed to read {:?}: {error}", absolute));
    serde_json::from_slice(&bytes).expect("failed to deserialize attestation input")
}

fn load_compressed_proof_path(path: &str) -> PathBuf {
    resolve_path(path)
}

fn prepare_output_dir(path: &str) -> PathBuf {
    let absolute = resolve_path(path);
    fs::create_dir_all(&absolute).unwrap_or_else(|error| panic!("failed to create {:?}: {error}", absolute));
    absolute
}

fn write_public_values(public_values: &PublicValues, output_dir: &PathBuf) {
    let public_values_path = output_dir.join("zkp_attestation_public_values.json");
    fs::write(
        public_values_path,
        serde_json::to_string_pretty(public_values).expect("failed to serialize public values"),
    )
    .expect("failed to write public values");
}

fn proof_bundle_path(output_dir: &PathBuf, system: ProofSystem) -> PathBuf {
    output_dir.join(format!(
        "zkp_attestation_proof_{}.bin",
        proof_system_name(system),
    ))
}

fn wrap_proof_bundle_path(output_dir: &PathBuf) -> PathBuf {
    output_dir.join("zkp_attestation_wrap_proof.bin")
}

fn infer_groth16_verify_dir(proof_bundle_path: &Path) -> Option<PathBuf> {
    let candidate = proof_bundle_path
        .parent()?
        .join("zkp_attestation_groth16_verifier");
    if candidate.join("groth16_vk.bin").is_file() {
        Some(candidate)
    } else {
        None
    }
}

fn log_stage_start(stage: &str) -> Instant {
    eprintln!("[zkp-attestation] starting {stage}");
    let _ = std::io::stderr().flush();
    Instant::now()
}

fn stage_seconds(started_at: Instant) -> f64 {
    started_at.elapsed().as_secs_f64()
}

fn log_stage_done(stage: &str, started_at: Instant) -> f64 {
    let seconds = stage_seconds(started_at);
    eprintln!("[zkp-attestation] finished {stage} in {:.2}s", seconds);
    let _ = std::io::stderr().flush();
    seconds
}

fn proof_system_name(system: ProofSystem) -> &'static str {
    match system {
        ProofSystem::Core => "core",
        ProofSystem::Compressed => "compressed",
        ProofSystem::Groth16 => "groth16",
        ProofSystem::Plonk => "plonk",
    }
}

fn set_env_default(name: &str, value: &str) {
    if env::var_os(name).is_none() {
        env::set_var(name, value);
    }
}

fn apply_resource_profile(args: &Args) {
    match args.resource_profile {
        ResourceProfile::Safe => {
            for (name, value) in SAFE_RESOURCE_DEFAULTS {
                set_env_default(name, value);
            }
        }
        ResourceProfile::Balanced => {
            for (name, value) in BALANCED_RESOURCE_DEFAULTS {
                set_env_default(name, value);
            }
        }
        ResourceProfile::Throughput => {
            for (name, value) in THROUGHPUT_RESOURCE_DEFAULTS {
                set_env_default(name, value);
            }
        }
        ResourceProfile::Full => return,
    }
    if args.prove && matches!(args.system, ProofSystem::Groth16 | ProofSystem::Plonk) {
        for (name, value) in SAFE_GROTH16_DEFAULTS {
            set_env_default(name, value);
        }
    }
}

fn main() {
    sp1_sdk::utils::setup_logger();
    dotenv::dotenv().ok();

    let args = Args::parse();
    let selected_modes = usize::from(args.execute)
        + usize::from(args.prove)
        + usize::from(args.verify_proof_input.is_some());
    if selected_modes != 1 {
        eprintln!("Error: specify exactly one of --execute, --prove, or --verify-proof-input");
        std::process::exit(1);
    }
    if args.compressed_proof_input.is_some() && !args.prove {
        eprintln!("Error: --compressed-proof-input requires --prove");
        std::process::exit(1);
    }
    if args.compressed_proof_input.is_some() && !matches!(args.system, ProofSystem::Groth16) {
        eprintln!("Error: --compressed-proof-input only supports --system groth16");
        std::process::exit(1);
    }
    if args.wrap_proof_input.is_some() && !args.prove {
        eprintln!("Error: --wrap-proof-input requires --prove");
        std::process::exit(1);
    }
    if args.wrap_proof_input.is_some() && !matches!(args.system, ProofSystem::Groth16) {
        eprintln!("Error: --wrap-proof-input only supports --system groth16");
        std::process::exit(1);
    }
    if args.compressed_proof_input.is_some() && args.wrap_proof_input.is_some() {
        eprintln!("Error: use at most one of --compressed-proof-input and --wrap-proof-input");
        std::process::exit(1);
    }
    if args.verify_proof_input.is_some()
        && (args.compressed_proof_input.is_some() || args.wrap_proof_input.is_some())
    {
        eprintln!("Error: --verify-proof-input cannot be combined with wrap/compressed proof inputs");
        std::process::exit(1);
    }
    apply_resource_profile(&args);

    let needs_input = args.execute
        || !matches!(args.system, ProofSystem::Groth16)
        || (args.compressed_proof_input.is_none() && args.wrap_proof_input.is_none());
    let input = if needs_input {
        Some(load_input(&args.input))
    } else {
        None
    };
    let output_dir = prepare_output_dir(&args.output_dir);

    if args.execute {
        let input = input.as_ref().expect("execute path requires attestation input");
        let prover_init_started_at = log_stage_start("prover_init");
        let client = build_execute_client();
        log_stage_done("prover_init", prover_init_started_at);
        let mut stdin = SP1Stdin::new();
        stdin.write(input);
        let execute_started_at = log_stage_start("execute");
        let (mut output, report) =
            client.execute(ATTESTATION_ELF, stdin).run().expect("failed to execute attestation guest");
        let execute_seconds = log_stage_done("execute", execute_started_at);
        let public_values: PublicValues = output.read();
        write_public_values(&public_values, &output_dir);
        if args.write_core_fixture {
            assert!(matches!(args.system, ProofSystem::Core), "--write-core-fixture requires --system core");
            let setup_started_at = log_stage_start("setup");
            let pk = client.setup(ATTESTATION_ELF).expect("failed to setup guest for core fixture");
            let setup_seconds = log_stage_done("setup", setup_started_at);
            let fixture = fixture_json(
                &public_values,
                &pk.verifying_key().bytes32().to_string(),
                None,
                proof_system_name(args.system),
            );
            let fixture_path = output_dir.join("zkp_attestation_fixture_core.json");
            fs::write(&fixture_path, fixture).expect("failed to write core fixture");
            eprintln!("[zkp-attestation] wrote core fixture after {:.2}s setup", setup_seconds);
        }
        println!(
            "{}",
            serde_json::to_string_pretty(&serde_json::json!({
                "public_values": public_values,
                "total_instruction_count": report.total_instruction_count(),
                "stage_seconds": {
                    "execute": execute_seconds,
                },
            }))
            .expect("failed to serialize execute summary")
        );
        return;
    }

    if let Some(verify_proof_input) = args.verify_proof_input.as_ref() {
        let proof_bundle_path = load_compressed_proof_path(verify_proof_input);
        let groth16_verify_dir = args
            .groth16_verify_dir
            .as_ref()
            .map(|path| resolve_path(path))
            .or_else(|| infer_groth16_verify_dir(&proof_bundle_path));
        let proof_bundle;
        let verifying_key;
        let prover_init_seconds;
        let setup_seconds;
        let verify_seconds;

        if matches!(args.system, ProofSystem::Groth16) && env::var("SP1_CIRCUIT_MODE").ok().as_deref() == Some("dev") {
            let prover_init_started_at = log_stage_start("prover_init");
            let client =
                WrapOnlyBlockingProver::new().expect("failed to initialize wrap-only prover");
            prover_init_seconds = log_stage_done("prover_init", prover_init_started_at);

            let setup_started_at = log_stage_start("setup");
            let vk = client
                .setup(&ATTESTATION_ELF)
                .expect("failed to setup guest for groth16 verification");
            setup_seconds = log_stage_done("setup", setup_started_at);

            let verify_started_at = log_stage_start("verify");
            proof_bundle = client
                .verify_groth16_bundle_path(
                    &proof_bundle_path,
                    &vk,
                    groth16_verify_dir.as_deref(),
                )
                .expect("failed to verify groth16 proof bundle");
            verify_seconds = log_stage_done("verify", verify_started_at);
            verifying_key = vk.bytes32().to_string();
        } else if matches!(args.system, ProofSystem::Groth16) && groth16_verify_dir.is_some() {
            let groth16_verify_dir = groth16_verify_dir
                .as_ref()
                .expect("groth16_verify_dir must exist in this branch");
            let prover_init_started_at = log_stage_start("prover_init");
            let client = build_execute_client();
            prover_init_seconds = log_stage_done("prover_init", prover_init_started_at);

            let setup_started_at = log_stage_start("setup");
            let pk = client
                .setup(ATTESTATION_ELF)
                .expect("failed to setup guest for groth16 verification");
            setup_seconds = log_stage_done("setup", setup_started_at);

            let verify_started_at = log_stage_start("verify");
            proof_bundle = verify_groth16_bundle_path_with_default_vks(
                &proof_bundle_path,
                pk.verifying_key(),
                &groth16_verify_dir,
            )
                .expect("failed to verify groth16 proof bundle");
            verify_seconds = log_stage_done("verify", verify_started_at);
            verifying_key = pk.verifying_key().bytes32().to_string();
        } else {
            let prover_init_started_at = log_stage_start("prover_init");
            let client = build_execute_client();
            prover_init_seconds = log_stage_done("prover_init", prover_init_started_at);

            let setup_started_at = log_stage_start("setup");
            let pk = client.setup(ATTESTATION_ELF).expect("failed to setup guest for verification");
            setup_seconds = log_stage_done("setup", setup_started_at);

            let verify_started_at = log_stage_start("verify");
            proof_bundle = SP1ProofWithPublicValues::load(&proof_bundle_path)
                .expect("failed to load proof bundle");
            client
                .verify(&proof_bundle, pk.verifying_key(), None)
                .expect("failed to verify proof bundle");
            verify_seconds = log_stage_done("verify", verify_started_at);
            verifying_key = pk.verifying_key().bytes32().to_string();
        }

        let mut proof_public_values = proof_bundle.public_values.clone();
        let public_values: PublicValues = proof_public_values.read();
        println!(
            "{}",
            serde_json::to_string_pretty(&serde_json::json!({
                "proof_system": proof_system_name(args.system),
                "verification_key": verifying_key,
                "proof_bundle_path": proof_bundle_path,
                "public_values": public_values,
                "stage_seconds": {
                    "prover_init": prover_init_seconds,
                    "setup": setup_seconds,
                    "verify": verify_seconds,
                },
            }))
            .expect("failed to serialize verification summary")
        );
        return;
    }

    let (
        proof,
        verifying_key,
        prover_init_seconds,
        setup_seconds,
        prove_seconds,
        verify_seconds,
        wrap_proof_bundle,
    ) = if matches!(args.system, ProofSystem::Core) {
            let input = input.as_ref().expect("core prove path requires attestation input");
            let prover_init_started_at = log_stage_start("prover_init");
            let client = CoreOnlyBlockingProver::new().expect("failed to initialize core-only prover");
            let prover_init_seconds = log_stage_done("prover_init", prover_init_started_at);

            let setup_started_at = log_stage_start("setup");
            let vk = client.setup(&ATTESTATION_ELF).expect("failed to setup guest");
            let setup_seconds = log_stage_done("setup", setup_started_at);

            let prove_started_at = log_stage_start("prove");
            let proof = client
                .prove_core(&ATTESTATION_ELF, input, vk.clone())
                .expect("failed to generate core proof");
            let prove_seconds = log_stage_done("prove", prove_started_at);

            let verify_started_at = log_stage_start("verify");
            build_execute_client()
                .verify(&proof, &vk, None)
                .expect("failed to verify core proof");
            let verify_seconds = log_stage_done("verify", verify_started_at);

            (
                proof,
                vk.bytes32().to_string(),
                prover_init_seconds,
                setup_seconds,
                prove_seconds,
                verify_seconds,
                None,
            )
        } else if let Some(wrap_proof_input) = args.wrap_proof_input.as_ref() {
            let prover_init_started_at = log_stage_start("prover_init");
            let client =
                WrapOnlyBlockingProver::new().expect("failed to initialize wrap-only prover");
            let prover_init_seconds = log_stage_done("prover_init", prover_init_started_at);

            let setup_started_at = log_stage_start("setup");
            let vk = client
                .setup(&ATTESTATION_ELF)
                .expect("failed to setup guest for wrap-only proving");
            let setup_seconds = log_stage_done("setup", setup_started_at);

            let prove_started_at = log_stage_start("prove");
            let proof = client
                .groth16_from_wrap_path(load_compressed_proof_path(wrap_proof_input), &vk)
                .expect("failed to generate groth16 proof from wrap bundle");
            let prove_seconds = log_stage_done("prove", prove_started_at);

            let verify_started_at = log_stage_start("verify");
            let verify_seconds = log_stage_done("verify", verify_started_at);

            (
                proof,
                vk.bytes32().to_string(),
                prover_init_seconds,
                setup_seconds,
                prove_seconds,
                verify_seconds,
                Some(load_compressed_proof_path(wrap_proof_input)),
            )
        } else if let Some(compressed_proof_input) = args.compressed_proof_input.as_ref() {
            let prover_init_started_at = log_stage_start("prover_init");
            let client =
                WrapOnlyBlockingProver::new().expect("failed to initialize wrap-only prover");
            let prover_init_seconds = log_stage_done("prover_init", prover_init_started_at);

            let setup_started_at = log_stage_start("setup");
            let vk = client
                .setup(&ATTESTATION_ELF)
                .expect("failed to setup guest for wrap-only proving");
            let setup_seconds = log_stage_done("setup", setup_started_at);

            let prove_started_at = log_stage_start("prove");
            let wrap_proof_bundle_path = wrap_proof_bundle_path(&output_dir);
            let proof = client
                .groth16_from_compressed_path(
                    load_compressed_proof_path(compressed_proof_input),
                    &vk,
                    &wrap_proof_bundle_path,
                )
                .expect("failed to generate groth16 proof from compressed bundle");
            let prove_seconds = log_stage_done("prove", prove_started_at);

            let verify_started_at = log_stage_start("verify");
            let verify_seconds = log_stage_done("verify", verify_started_at);

            (
                proof,
                vk.bytes32().to_string(),
                prover_init_seconds,
                setup_seconds,
                prove_seconds,
                verify_seconds,
                Some(wrap_proof_bundle_path),
            )
        } else {
            let input = input.as_ref().expect("prove path requires attestation input");
            let prover_init_started_at = log_stage_start("prover_init");
            let client = ProverClient::from_env();
            let prover_init_seconds = log_stage_done("prover_init", prover_init_started_at);

            let mut stdin = SP1Stdin::new();
            stdin.write(input);
            let setup_started_at = log_stage_start("setup");
            let pk = client.setup(ATTESTATION_ELF).expect("failed to setup guest");
            let setup_seconds = log_stage_done("setup", setup_started_at);

            let prove_started_at = log_stage_start("prove");
            let proof = match args.system {
                ProofSystem::Core => unreachable!("core handled in lightweight branch"),
                ProofSystem::Compressed => client.prove(&pk, stdin).compressed().run(),
                ProofSystem::Groth16 => client.prove(&pk, stdin).groth16().run(),
                ProofSystem::Plonk => client.prove(&pk, stdin).plonk().run(),
            }
            .expect("failed to generate proof");
            let prove_seconds = log_stage_done("prove", prove_started_at);

            let verify_started_at = log_stage_start("verify");
            client
                .verify(&proof, pk.verifying_key(), None)
                .expect("failed to verify proof");
            let verify_seconds = log_stage_done("verify", verify_started_at);

            (
                proof,
                pk.verifying_key().bytes32().to_string(),
                prover_init_seconds,
                setup_seconds,
                prove_seconds,
                verify_seconds,
                None,
            )
        };

    let mut proof_public_values = proof.public_values.clone();
    let public_values: PublicValues = proof_public_values.read();
    write_public_values(&public_values, &output_dir);
    let proof_bundle_path = match args.system {
        ProofSystem::Core => None,
        ProofSystem::Compressed | ProofSystem::Groth16 | ProofSystem::Plonk => {
            let bundle_path = proof_bundle_path(&output_dir, args.system);
            proof
                .save(&bundle_path)
                .expect("failed to write binary proof bundle");
            Some(bundle_path)
        }
    };
    let proof_hex = match args.system {
        ProofSystem::Core | ProofSystem::Compressed => None,
        ProofSystem::Groth16 | ProofSystem::Plonk => Some(format!("0x{}", hex::encode(proof.bytes()))),
    };
    let fixture = fixture_json(
        &public_values,
        &verifying_key,
        proof_hex.as_deref(),
        proof_system_name(args.system),
    );
    let fixture_path = output_dir.join(format!(
        "zkp_attestation_fixture_{}.json",
        proof_system_name(args.system),
    ));
    fs::write(&fixture_path, fixture).expect("failed to write proof fixture");

    println!(
        "{}",
        serde_json::to_string_pretty(&serde_json::json!({
                "proof_system": proof_system_name(args.system),
                "verification_key": verifying_key,
                "fixture_path": fixture_path,
                "proof_bundle_path": proof_bundle_path,
                "wrap_proof_bundle_path": wrap_proof_bundle,
                "public_values": public_values,
                "stage_seconds": {
                    "prover_init": prover_init_seconds,
                "setup": setup_seconds,
                "prove": prove_seconds,
                "verify": verify_seconds,
            },
        }))
        .expect("failed to serialize proof summary")
    );
}

#[cfg(test)]
mod tests {
    use super::infer_groth16_verify_dir;
    use crate::ATTESTATION_ELF;
    use secp256k1_zkp_attestation_lib::PublicValues;
    use sp1_sdk::{
        blocking::Prover,
        HashableKey, SP1ProofWithPublicValues,
    };
    use sp1_sdk::ProvingKey;
    use std::{
        fs,
        path::PathBuf,
        time::{SystemTime, UNIX_EPOCH},
    };

    fn temp_path(name: &str) -> PathBuf {
        let suffix = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("system time before unix epoch")
            .as_nanos();
        std::env::temp_dir().join(format!("secp256k1-zkp-attestation-{name}-{suffix}"))
    }

    #[test]
    fn infer_groth16_verify_dir_returns_sibling_verifier_dir() {
        let base_dir = temp_path("verify-dir");
        let proof_dir = base_dir.join("proofs");
        let verifier_dir = proof_dir.join("zkp_attestation_groth16_verifier");
        fs::create_dir_all(&verifier_dir).expect("failed to create verifier dir");
        fs::write(
            verifier_dir.join("groth16_vk.bin"),
            [0_u8, 1_u8, 2_u8, 3_u8],
        )
        .expect("failed to write vk");

        let inferred = infer_groth16_verify_dir(
            &proof_dir.join("zkp_attestation_proof_groth16.bin"),
        );
        assert_eq!(inferred, Some(verifier_dir));

        let _ = fs::remove_dir_all(base_dir);
    }

    #[test]
    fn infer_groth16_verify_dir_returns_none_without_vk() {
        let base_dir = temp_path("missing-vk");
        let proof_dir = base_dir.join("proofs");
        fs::create_dir_all(&proof_dir).expect("failed to create proof dir");

        let inferred = infer_groth16_verify_dir(
            &proof_dir.join("zkp_attestation_proof_groth16.bin"),
        );
        assert_eq!(inferred, None);

        let _ = fs::remove_dir_all(base_dir);
    }

    #[test]
    fn checked_groth16_bundle_matches_checked_fixture() {
        let artifact_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("../../artifacts");
        let fixture = serde_json::from_slice::<serde_json::Value>(
            &fs::read(artifact_dir.join("zkp_attestation_fixture_groth16.json"))
                .expect("failed to read checked groth16 fixture"),
        )
        .expect("failed to parse checked groth16 fixture");
        let bundle = SP1ProofWithPublicValues::load(
            artifact_dir.join("zkp_attestation_proof_groth16.bin"),
        )
        .expect("failed to load checked groth16 bundle");

        let client = super::build_execute_client();
        let pk = client
            .setup(ATTESTATION_ELF)
            .expect("failed to setup guest for checked fixture verification");
        let expected_verification_key = pk.verifying_key().bytes32().to_string();

        let mut proof_public_values = bundle.public_values.clone();
        let public_values: PublicValues = proof_public_values.read();

        assert_eq!(fixture["proof_system"], "groth16");
        assert_eq!(fixture["verification_key"], expected_verification_key);
        assert_eq!(
            fixture["proof"],
            format!("0x{}", hex::encode(bundle.bytes()))
        );
        assert_eq!(
            fixture["public_values"],
            serde_json::to_value(public_values).expect("failed to encode public values")
        );
    }
}

fn build_execute_client() -> LightProver {
    ProverClient::builder().light().build()
}
