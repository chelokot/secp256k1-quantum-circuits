use std::{
    env,
    fs,
    path::{Path, PathBuf},
    time::Instant,
};

use anyhow::{anyhow, Result};
use num_bigint::BigUint;
use serde::{Deserialize, Serialize};
use slop_algebra::PrimeField;
use sp1_prover::{
    build::{build_constraints_and_witness, build_groth16_bn254_artifacts, try_build_groth16_artifacts_dir},
    verify::{SP1Verifier, VerifierRecursionVks},
    worker::{cpu_worker_builder, SP1LocalNode, SP1LocalNodeBuilder},
    SP1VerifyingKey, SP1_CIRCUIT_VERSION,
};
use sp1_hypercube::{koalabears_to_bn254, HashableKey};
use sp1_primitives::{io::SP1PublicValues, SP1OuterGlobalContext};
use sp1_hypercube::{SP1PcsProofOuter, SP1WrapProof};
use sp1_recursion_gnark_ffi::{Groth16Bn254Proof, Groth16Bn254Prover};
use sp1_sdk::{SP1Proof, SP1ProofWithPublicValues};
use tokio::runtime::Runtime;

type WrapProofData = SP1WrapProof<SP1OuterGlobalContext, SP1PcsProofOuter>;

#[derive(Serialize, Deserialize)]
struct WrapProofBundle {
    public_values: SP1PublicValues,
    wrap_proof: WrapProofData,
}

pub struct WrapOnlyBlockingProver {
    runtime: Runtime,
    node: SP1LocalNode,
}

fn log_stage_start(stage: &str) -> Instant {
    eprintln!("[zkp-attestation-wrap] starting {stage}");
    Instant::now()
}

fn log_stage_done(stage: &str, started_at: Instant) {
    eprintln!(
        "[zkp-attestation-wrap] finished {stage} in {:.2}s",
        started_at.elapsed().as_secs_f64()
    );
}

fn use_development_mode() -> bool {
    env::var("SP1_CIRCUIT_MODE").unwrap_or_else(|_| "release".to_string()) == "dev"
}

fn hex_prefix(hash: &[u8]) -> String {
    format!("{:016x}", u64::from_be_bytes(hash[..8].try_into().expect("prefix slice")))
}

fn groth16_dev_artifacts_dir(
    wrap_vk: &sp1_hypercube::MachineVerifyingKey<sp1_primitives::SP1OuterGlobalContext>,
) -> Result<PathBuf> {
    let serialized_vk = bincode::serialize(wrap_vk)?;
    let digest = sp1_primitives::io::sha256_hash(&serialized_vk);
    let base_dir = match env::var("SP1_GROTH16_CIRCUIT_PATH") {
        Ok(path) => PathBuf::from(path),
        Err(_) => PathBuf::from(
            env::var("HOME").map_err(|_| anyhow!("HOME is not set for groth16 dev artifacts"))?,
        )
        .join(".sp1")
        .join("circuits"),
    };
    Ok(base_dir
        .join(format!("{}-groth16-dev", hex_prefix(&digest))))
}

fn groth16_artifacts_complete(build_dir: &Path) -> bool {
    [
        "groth16_circuit.bin",
        "groth16_pk.bin",
        "groth16_vk.bin",
        "constraints.json",
        "groth16_witness.json",
    ]
    .iter()
    .all(|file_name| build_dir.join(file_name).is_file())
}

fn ensure_groth16_build_dir(
    runtime: &Runtime,
    wrap_vk: &sp1_hypercube::MachineVerifyingKey<SP1OuterGlobalContext>,
    wrap_proof: &sp1_hypercube::ShardProof<SP1OuterGlobalContext, SP1PcsProofOuter>,
) -> Result<PathBuf> {
    if !use_development_mode() {
        return Ok(runtime.block_on(try_build_groth16_artifacts_dir(wrap_vk, wrap_proof))?);
    }

    let build_dir = groth16_dev_artifacts_dir(wrap_vk)?;
    if groth16_artifacts_complete(&build_dir) {
        return Ok(build_dir);
    }

    eprintln!(
        "[zkp-attestation-wrap] groth16 dev artifact dir is incomplete, rebuilding {}",
        build_dir.display()
    );
    build_groth16_bn254_artifacts(wrap_vk, wrap_proof, &build_dir)?;
    Ok(build_dir)
}

fn load_wrap_proof_bundle(path: &Path) -> Result<WrapProofBundle> {
    let bytes = fs::read(path)?;
    Ok(bincode::deserialize(&bytes)?)
}

fn save_wrap_proof_bundle(path: &Path, bundle: &WrapProofBundle) -> Result<()> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    let bytes = bincode::serialize(bundle)?;
    fs::write(path, bytes)?;
    Ok(())
}

fn parse_bn254_public_input(input: &str) -> Result<BigUint> {
    Ok(input.parse()?)
}

fn verify_groth16_locally(
    proof: &Groth16Bn254Proof,
    vk: &SP1VerifyingKey,
    verifier: &SP1Verifier,
    build_dir: &Path,
) -> Result<()> {
    let prover = Groth16Bn254Prover::new();
    let vkey_hash = parse_bn254_public_input(&proof.public_inputs[0])?;
    let committed_values_digest = parse_bn254_public_input(&proof.public_inputs[1])?;
    let exit_code = parse_bn254_public_input(&proof.public_inputs[2])?;
    let vk_root = parse_bn254_public_input(&proof.public_inputs[3])?;
    let proof_nonce = parse_bn254_public_input(&proof.public_inputs[4])?;
    let expected_vk_root = koalabears_to_bn254(&verifier.recursion_vks.root());

    if vk_root != expected_vk_root.as_canonical_biguint() {
        return Err(anyhow!("vk_root mismatch"));
    }

    if vk.hash_bn254().as_canonical_biguint() != vkey_hash {
        return Err(anyhow!("groth16 verification key mismatch"));
    }

    prover.verify(
        proof,
        &vkey_hash,
        &committed_values_digest,
        &exit_code,
        &vk_root,
        &proof_nonce,
        build_dir,
    )
}

pub fn verify_groth16_bundle_path_with_default_vks(
    proof_bundle_path: impl AsRef<Path>,
    vk: &SP1VerifyingKey,
    build_dir: impl AsRef<Path>,
) -> Result<SP1ProofWithPublicValues> {
    let load_started_at = log_stage_start("load_groth16_bundle");
    let bundle = SP1ProofWithPublicValues::load(proof_bundle_path.as_ref())?;
    log_stage_done("load_groth16_bundle", load_started_at);

    let verifier = SP1Verifier::new(VerifierRecursionVks::default());
    let verify_started_at = log_stage_start("verify_groth16_bundle");
    let groth16_proof = match &bundle.proof {
        SP1Proof::Groth16(groth16_proof) => groth16_proof,
        _ => return Err(anyhow!("proof bundle does not contain a groth16 proof")),
    };
    verify_groth16_locally(groth16_proof, vk, &verifier, build_dir.as_ref())?;
    log_stage_done("verify_groth16_bundle", verify_started_at);
    Ok(bundle)
}

impl WrapOnlyBlockingProver {
    pub fn new() -> Result<Self> {
        let runtime = tokio::runtime::Builder::new_current_thread().enable_all().build()?;
        let node =
            runtime.block_on(SP1LocalNodeBuilder::from_worker_client_builder(cpu_worker_builder()).build())?;
        Ok(Self { runtime, node })
    }

    pub fn setup(&self, elf: &[u8]) -> Result<SP1VerifyingKey> {
        self.runtime.block_on(self.node.setup(elf))
    }

    pub fn groth16_from_compressed_path(
        &self,
        compressed_proof_path: impl AsRef<Path>,
        vk: &SP1VerifyingKey,
        wrap_proof_output_path: impl AsRef<Path>,
    ) -> Result<SP1ProofWithPublicValues> {
        let load_started_at = log_stage_start("load_compressed_bundle");
        let compressed_bundle = SP1ProofWithPublicValues::load(compressed_proof_path.as_ref())?;
        log_stage_done("load_compressed_bundle", load_started_at);
        self.groth16_from_compressed_bundle(compressed_bundle, vk, wrap_proof_output_path.as_ref())
    }

    pub fn groth16_from_wrap_path(
        &self,
        wrap_proof_path: impl AsRef<Path>,
        vk: &SP1VerifyingKey,
    ) -> Result<SP1ProofWithPublicValues> {
        let load_started_at = log_stage_start("load_wrap_bundle");
        let wrap_bundle = load_wrap_proof_bundle(wrap_proof_path.as_ref())?;
        log_stage_done("load_wrap_bundle", load_started_at);
        self.groth16_from_wrap_bundle(wrap_bundle, vk)
    }

    fn groth16_from_compressed_bundle(
        &self,
        compressed_bundle: SP1ProofWithPublicValues,
        vk: &SP1VerifyingKey,
        wrap_proof_output_path: &Path,
    ) -> Result<SP1ProofWithPublicValues> {
        match &compressed_bundle.proof {
            SP1Proof::Compressed(_) => {}
            _ => {
                return Err(anyhow!(
                    "compressed-proof-input must contain an SP1 compressed proof bundle"
                ));
            }
        }

        let verify_compressed_started_at = log_stage_start("verify_compressed_bundle");
        self.node.verify(vk, &compressed_bundle.proof)?;
        log_stage_done("verify_compressed_bundle", verify_compressed_started_at);

        let shrink_wrap_started_at = log_stage_start("shrink_wrap");
        let wrap_proof = self.runtime.block_on(self.node.shrink_wrap(&compressed_bundle.proof))?;
        log_stage_done("shrink_wrap", shrink_wrap_started_at);
        let wrap_bundle = WrapProofBundle {
            public_values: compressed_bundle.public_values,
            wrap_proof,
        };

        let save_started_at = log_stage_start("save_wrap_bundle");
        save_wrap_proof_bundle(wrap_proof_output_path, &wrap_bundle)?;
        log_stage_done("save_wrap_bundle", save_started_at);

        self.groth16_from_wrap_bundle(wrap_bundle, vk)
    }

    fn groth16_from_wrap_bundle(
        &self,
        wrap_bundle: WrapProofBundle,
        vk: &SP1VerifyingKey,
    ) -> Result<SP1ProofWithPublicValues> {
        let verify_wrap_started_at = log_stage_start("verify_wrap_bundle");
        let verifier = SP1Verifier::new(self.node.core().recursion_vks());
        verifier.verify_wrap_bn254(&wrap_bundle.wrap_proof, vk)?;
        log_stage_done("verify_wrap_bundle", verify_wrap_started_at);

        let build_artifacts_started_at = log_stage_start("build_groth16_artifacts");
        let build_dir = ensure_groth16_build_dir(
            &self.runtime,
            &wrap_bundle.wrap_proof.vk,
            &wrap_bundle.wrap_proof.proof,
        )?;
        log_stage_done("build_groth16_artifacts", build_artifacts_started_at);

        let witness_started_at = log_stage_start("build_constraints_and_witness");
        let (_, witness) = build_constraints_and_witness(
            &wrap_bundle.wrap_proof.vk,
            &wrap_bundle.wrap_proof.proof,
        )?;
        log_stage_done("build_constraints_and_witness", witness_started_at);

        let groth16_started_at = log_stage_start("groth16_prove");
        let groth16 = Groth16Bn254Prover::new().prove(witness, &build_dir);
        log_stage_done("groth16_prove", groth16_started_at);

        let proof = SP1ProofWithPublicValues::new(
            SP1Proof::Groth16(groth16),
            wrap_bundle.public_values,
            SP1_CIRCUIT_VERSION.to_string(),
        );

        let verify_groth16_started_at = log_stage_start("verify_groth16_bundle");
        let verifier = SP1Verifier::new(self.node.core().recursion_vks());
        let groth16_proof = match &proof.proof {
            SP1Proof::Groth16(groth16_proof) => groth16_proof,
            _ => return Err(anyhow!("expected groth16 proof")),
        };
        verify_groth16_locally(groth16_proof, vk, &verifier, &build_dir)?;
        log_stage_done("verify_groth16_bundle", verify_groth16_started_at);
        Ok(proof)
    }

    pub fn verify_groth16_bundle_path(
        &self,
        proof_bundle_path: impl AsRef<Path>,
        vk: &SP1VerifyingKey,
        build_dir_override: Option<&Path>,
    ) -> Result<SP1ProofWithPublicValues> {
        let load_started_at = log_stage_start("load_groth16_bundle");
        let bundle = SP1ProofWithPublicValues::load(proof_bundle_path.as_ref())?;
        log_stage_done("load_groth16_bundle", load_started_at);

        let verifier = SP1Verifier::new(self.node.core().recursion_vks());
        let build_dir = if let Some(path) = build_dir_override {
            path.to_path_buf()
        } else if use_development_mode() {
            groth16_dev_artifacts_dir(&verifier.wrap_vk)?
        } else {
            return Err(anyhow!(
                "verify_groth16_bundle_path requires either --groth16-verify-dir or SP1_CIRCUIT_MODE=dev"
            ));
        };

        let verify_started_at = log_stage_start("verify_groth16_bundle");
        let groth16_proof = match &bundle.proof {
            SP1Proof::Groth16(groth16_proof) => groth16_proof,
            _ => return Err(anyhow!("proof bundle does not contain a groth16 proof")),
        };
        verify_groth16_locally(groth16_proof, vk, &verifier, &build_dir)?;
        log_stage_done("verify_groth16_bundle", verify_started_at);
        Ok(bundle)
    }
}
