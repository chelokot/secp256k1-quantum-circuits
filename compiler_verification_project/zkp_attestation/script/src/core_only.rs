use std::{borrow::Borrow, sync::Arc};

use anyhow::{anyhow, Result};
use secp256k1_zkp_attestation_lib::PreparedAttestationInput;
use sp1_core_executor::{ExecutionRecord, Program, SP1CoreOpts, SplitOpts};
use sp1_core_machine::{
    executor::{trace_chunk, ExecutionOutput},
    io::SP1Stdin,
};
use sp1_hypercube::{
    air::PublicValues,
    prover::{AirProver, CpuShardProver, ProverSemaphore},
    SP1PcsProofInner, ShardProof, DIGEST_SIZE,
};
use sp1_jit::TraceChunk;
use sp1_primitives::{io::SP1PublicValues, SP1Field, SP1GlobalContext};
use sp1_prover::{
    verify::{SP1Verifier, VerifierRecursionVks},
    worker::{
        CommonProverInput, CoreExecuteTaskRequest, DeferredEvents, GlobalMemoryShard,
        LocalWorkerClient, MessageReceiver, PrecompileArtifactSlice, ProofData, ProofId,
        ProveShardTaskRequest, RequesterId, SP1Controller, SP1WorkerConfig, TaskContext,
        TaskError, TaskId, TaskMetadata, TraceData, WorkerClient,
    },
    CpuSP1ProverComponents, SP1ProverComponents, SP1VerifyingKey, SP1_CIRCUIT_VERSION,
};
use sp1_prover_types::{
    network_base_types::ProofMode, ArtifactClient, ArtifactType, InMemoryArtifactClient,
    TaskStatus,
};
use sp1_sdk::{SP1Proof, SP1ProofWithPublicValues};
use tokio::runtime::Runtime;

type CpuCoreProver = <CpuSP1ProverComponents as SP1ProverComponents>::CoreProver;

pub struct CoreOnlyBlockingProver {
    runtime: Runtime,
    inner: CoreOnlyAsyncProver,
}

impl CoreOnlyBlockingProver {
    pub fn new() -> Result<Self> {
        let runtime = tokio::runtime::Builder::new_current_thread().enable_all().build()?;
        let inner = runtime.block_on(CoreOnlyAsyncProver::new())?;
        Ok(Self { runtime, inner })
    }

    pub fn setup(&self, elf: &[u8]) -> Result<SP1VerifyingKey> {
        self.runtime.block_on(self.inner.setup(elf))
    }

    pub fn prove_core(
        &self,
        elf: &[u8],
        input: &PreparedAttestationInput,
        vk: SP1VerifyingKey,
    ) -> Result<SP1ProofWithPublicValues> {
        self.runtime.block_on(self.inner.prove_core(elf, input, vk))
    }
}

struct CoreOnlyAsyncProver {
    artifact_client: InMemoryArtifactClient,
    worker_client: LocalWorkerClient,
    core_air_prover: Arc<CpuCoreProver>,
    permits: ProverSemaphore,
}

impl CoreOnlyAsyncProver {
    async fn new() -> Result<Self> {
        let worker_config = SP1WorkerConfig::default();
        let mut controller_config = worker_config.controller_config.clone();
        controller_config.opts = SP1CoreOpts::default();

        let artifact_client = InMemoryArtifactClient::new();
        let (worker_client, mut channels) = LocalWorkerClient::init();

        let core_verifier = CpuSP1ProverComponents::core_verifier();
        let core_air_prover = Arc::new(CpuShardProver::new(core_verifier.shard_verifier().clone()));
        let permits = ProverSemaphore::new(
            worker_config
                .prover_config
                .core_prover_config
                .num_core_workers
                .max(1),
        );

        let controller = Arc::new(SP1Controller::new(
            controller_config,
            artifact_client.clone(),
            worker_client.clone(),
            SP1Verifier::new(VerifierRecursionVks::default()),
        ));

        spawn_prove_shard_service(
            channels.task_receivers.remove(&sp1_prover_types::TaskType::ProveShard).unwrap(),
            artifact_client.clone(),
            worker_client.clone(),
            core_air_prover.clone(),
            permits.clone(),
            SP1CoreOpts::default(),
        );
        spawn_core_execute_service(
            channels
                .task_receivers
                .remove(&sp1_prover_types::TaskType::CoreExecute)
                .unwrap(),
            worker_client.clone(),
            controller.clone(),
        );
        spawn_marker_drain_service(
            channels
                .task_receivers
                .remove(&sp1_prover_types::TaskType::MarkerDeferredRecord)
                .unwrap(),
        );

        Ok(Self {
            artifact_client,
            worker_client,
            core_air_prover,
            permits,
        })
    }

    async fn setup(&self, elf: &[u8]) -> Result<SP1VerifyingKey> {
        let program = Arc::new(
            Program::from(elf)
                .map_err(|error| anyhow!("failed to disassemble program during setup: {error}"))?,
        );
        let (_, vk) = self.core_air_prover.setup(program, self.permits.clone()).await;
        Ok(SP1VerifyingKey { vk })
    }

    async fn prove_core(
        &self,
        elf: &[u8],
        input: &PreparedAttestationInput,
        vk: SP1VerifyingKey,
    ) -> Result<SP1ProofWithPublicValues> {
        let mut stdin = SP1Stdin::new();
        stdin.write(input);
        if !stdin.proofs.is_empty() {
            return Err(anyhow!(
                "core-only prover path does not support deferred stdin proofs"
            ));
        }

        let elf_artifact = self.artifact_client.create_artifact()?;
        self.artifact_client.upload_program(&elf_artifact, elf.to_vec()).await?;

        let stdin_artifact = self.artifact_client.create_artifact()?;
        self.artifact_client
            .upload_with_type(&stdin_artifact, ArtifactType::Stdin, stdin.clone())
            .await?;

        let common_input = CommonProverInput {
            vk,
            mode: ProofMode::Core,
            deferred_digest: [0u32; DIGEST_SIZE],
            num_deferred_proofs: 0,
            nonce: [0u32; 4],
        };
        let common_input_artifact = self.artifact_client.create_artifact()?;
        self.artifact_client.upload(&common_input_artifact, common_input).await?;

        let execution_output_artifact = self.artifact_client.create_artifact()?;
        let context = TaskContext {
            proof_id: ProofId::new(unique_id("core-proof")),
            parent_id: None,
            parent_context: None,
            requester_id: RequesterId::new(format!("core-only-{}", std::process::id())),
        };
        let executor_request = CoreExecuteTaskRequest {
            elf: elf_artifact.clone(),
            stdin: stdin_artifact.clone(),
            common_input: common_input_artifact.clone(),
            execution_output: execution_output_artifact.clone(),
            num_deferred_proofs: 0,
            cycle_limit: None,
            context: context.clone(),
        };

        let executor_task_id = self
            .worker_client
            .submit_task(sp1_prover_types::TaskType::CoreExecute, executor_request.into_raw()?)
            .await?;
        let core_proof_rx = MessageReceiver::<ProofData>::new(
            self.worker_client.subscribe_task_messages(&executor_task_id).await?,
        );
        let proof_result = collect_core_proofs_direct(
            self.worker_client.clone(),
            self.artifact_client.clone(),
            context.clone(),
            core_proof_rx,
        );
        let execution_status = self
            .worker_client
            .subscriber(context.proof_id.clone())
            .await
            .map_err(TaskError::from)?
            .per_task();
        let wait_executor = async {
            let status = execution_status.wait_task(executor_task_id).await?;
            if status != TaskStatus::Succeeded {
                return Err(TaskError::Fatal(anyhow!("CoreExecute task failed")));
            }
            self.artifact_client
                .download::<ExecutionOutput>(&execution_output_artifact)
                .await
                .map_err(TaskError::from)
        };
        let (execution_output, shard_proofs) = tokio::try_join!(wait_executor, proof_result)?;

        self.artifact_client
            .try_delete(&elf_artifact, ArtifactType::Program)
            .await?;
        self.artifact_client
            .try_delete(&stdin_artifact, ArtifactType::Stdin)
            .await?;
        self.artifact_client
            .try_delete(&common_input_artifact, ArtifactType::UnspecifiedArtifactType)
            .await?;
        self.artifact_client
            .try_delete(&execution_output_artifact, ArtifactType::UnspecifiedArtifactType)
            .await?;

        Ok(SP1ProofWithPublicValues::new(
            SP1Proof::Core(shard_proofs),
            SP1PublicValues::from(&execution_output.public_value_stream),
            SP1_CIRCUIT_VERSION.to_string(),
        ))
    }
}

fn spawn_prove_shard_service(
    mut prove_shard_rx: tokio::sync::mpsc::Receiver<(TaskId, sp1_prover::worker::RawTaskRequest)>,
    artifact_client: InMemoryArtifactClient,
    worker_client: LocalWorkerClient,
    core_air_prover: Arc<CpuCoreProver>,
    permits: ProverSemaphore,
    opts: SP1CoreOpts,
) {
    tokio::spawn(async move {
        while let Some((task_id, request)) = prove_shard_rx.recv().await {
            let proof_id = request.context.proof_id.clone();
            match prove_core_shard_only(
                artifact_client.clone(),
                worker_client.clone(),
                core_air_prover.clone(),
                permits.clone(),
                opts.clone(),
                request,
            )
            .await
            {
                Ok(()) => {
                    if let Err(error) = worker_client
                        .complete_task(proof_id, task_id, TaskMetadata::default())
                        .await
                    {
                        eprintln!("[zkp-attestation] failed to complete ProveShard task: {error:?}");
                    }
                }
                Err(TaskError::Retryable(error)) => {
                    eprintln!("[zkp-attestation] retryable ProveShard failure: {error:?}");
                    if let Err(status_error) = worker_client
                        .update_task_status(task_id, TaskStatus::FailedRetryable)
                        .await
                    {
                        eprintln!(
                            "[zkp-attestation] failed to mark ProveShard retryable: {status_error:?}"
                        );
                    }
                }
                Err(error) => {
                    eprintln!("[zkp-attestation] fatal ProveShard failure: {error:?}");
                    if let Err(status_error) = worker_client
                        .update_task_status(task_id, TaskStatus::FailedFatal)
                        .await
                    {
                        eprintln!(
                            "[zkp-attestation] failed to mark ProveShard fatal: {status_error:?}"
                        );
                    }
                }
            }
        }
    });
}

fn spawn_core_execute_service(
    mut core_execute_rx: tokio::sync::mpsc::Receiver<(TaskId, sp1_prover::worker::RawTaskRequest)>,
    worker_client: LocalWorkerClient,
    controller: Arc<SP1Controller<InMemoryArtifactClient, LocalWorkerClient>>,
) {
    tokio::spawn(async move {
        while let Some((task_id, request)) = core_execute_rx.recv().await {
            let proof_id = request.context.proof_id.clone();
            match CoreExecuteTaskRequest::from_raw(request) {
                Ok(parsed_request) => {
                    if let Err(error) = controller.execute(task_id.clone(), parsed_request).await {
                        eprintln!("[zkp-attestation] CoreExecute failure: {error:?}");
                        let _ = worker_client
                            .update_task_status(task_id, TaskStatus::FailedFatal)
                            .await;
                        continue;
                    }
                    if let Err(error) = worker_client
                        .complete_task(proof_id, task_id, TaskMetadata::default())
                        .await
                    {
                        eprintln!("[zkp-attestation] failed to complete CoreExecute task: {error:?}");
                    }
                }
                Err(error) => {
                    eprintln!("[zkp-attestation] failed to parse CoreExecute request: {error:?}");
                    let _ = worker_client
                        .update_task_status(task_id, TaskStatus::FailedFatal)
                        .await;
                }
            }
        }
    });
}

fn spawn_marker_drain_service(
    mut marker_rx: tokio::sync::mpsc::Receiver<(TaskId, sp1_prover::worker::RawTaskRequest)>,
) {
    tokio::spawn(async move {
        while marker_rx.recv().await.is_some() {}
    });
}

async fn collect_core_proofs_direct(
    worker_client: LocalWorkerClient,
    artifact_client: InMemoryArtifactClient,
    context: TaskContext,
    mut core_proof_rx: MessageReceiver<ProofData>,
) -> Result<Vec<ShardProof<SP1GlobalContext, SP1PcsProofInner>>, TaskError> {
    let subscriber = worker_client.subscriber(context.proof_id.clone()).await?.per_task();
    let mut shard_proofs = Vec::new();
    while let Some(proof_data) = core_proof_rx.recv().await {
        let ProofData { task_id, proof, .. } = proof_data;
        let status = subscriber.wait_task(task_id.clone()).await?;
        if status != TaskStatus::Succeeded {
            return Err(TaskError::Fatal(anyhow!("core proof task failed: {task_id:?}")));
        }
        shard_proofs.push(
            artifact_client
                .download::<ShardProof<SP1GlobalContext, SP1PcsProofInner>>(&proof)
                .await?,
        );
    }
    shard_proofs.sort_by_key(|shard_proof| {
        let public_values: &PublicValues<[_; 4], [_; 3], [_; 4], _> =
            shard_proof.public_values.as_slice().borrow();
        public_values.range()
    });
    Ok(shard_proofs)
}

async fn prove_core_shard_only(
    artifact_client: InMemoryArtifactClient,
    worker_client: LocalWorkerClient,
    core_air_prover: Arc<CpuCoreProver>,
    permits: ProverSemaphore,
    opts: SP1CoreOpts,
    request: sp1_prover::worker::RawTaskRequest,
) -> Result<(), TaskError> {
    let task = ProveShardTaskRequest::from_raw(request.clone())?;
    let ProveShardTaskRequest {
        elf,
        common_input,
        record: record_artifact,
        output,
        deferred_marker_task,
        deferred_output,
        context,
    } = task;

    let (elf_bytes, common_input, record_data) = tokio::try_join!(
        artifact_client.download_program(&elf),
        artifact_client.download::<CommonProverInput>(&common_input),
        artifact_client.download::<TraceData>(&record_artifact),
    )?;

    if common_input.mode != ProofMode::Core {
        return Err(TaskError::Fatal(anyhow!(
            "core-only prove shard worker received non-core mode"
        )));
    }

    let precompile_artifacts = match &record_data {
        TraceData::Precompile(artifacts, _) => Some(artifacts.clone()),
        _ => None,
    };

    let program = Arc::new(
        Program::from(&elf_bytes)
            .map_err(|error| TaskError::Fatal(anyhow!("failed to disassemble program: {error}")))?,
    );
    let (mut record, deferred_record) = match record_data {
        TraceData::Core(chunk_bytes) => tokio::task::spawn_blocking({
            let program = program.clone();
            let opts = opts.clone();
            let nonce = common_input.nonce;
            move || {
                let chunk: TraceChunk = bincode::deserialize(&chunk_bytes).map_err(|error| {
                    TaskError::Fatal(anyhow!("failed to deserialize chunk: {error}"))
                })?;
                let record = ExecutionRecord::new_preallocated(
                    program.clone(),
                    nonce,
                    opts.global_dependencies_opt,
                    opts.shard_size >> 3,
                );
                let (_, mut record, _) =
                    trace_chunk::<SP1Field>(program, opts.clone(), chunk, nonce, record).map_err(
                        |error| TaskError::Fatal(anyhow!("failed to trace chunk: {error}")),
                    )?;
                let deferred_record = record.defer(&opts.retained_events_presets);
                Ok::<_, TaskError>((record, Some(deferred_record)))
            }
        })
        .await
        .map_err(|error| TaskError::Fatal(error.into()))??,
        TraceData::Memory(shard) => {
            let GlobalMemoryShard {
                final_state,
                initialize_events,
                finalize_events,
                previous_init_addr,
                previous_finalize_addr,
                previous_init_page_idx,
                previous_finalize_page_idx,
                last_init_addr,
                last_finalize_addr,
                last_init_page_idx,
                last_finalize_page_idx,
            } = *shard;
            let mut record =
                ExecutionRecord::new(program.clone(), common_input.nonce, opts.global_dependencies_opt);
            record.global_memory_initialize_events = initialize_events;
            record.global_memory_finalize_events = finalize_events;
            let enable_untrusted_programs =
                common_input.vk.vk.enable_untrusted_programs != SP1Field::default();
            record.public_values.update_finalized_state(
                final_state.timestamp,
                final_state.pc,
                final_state.exit_code,
                enable_untrusted_programs as u32,
                final_state.public_value_digest,
                common_input.deferred_digest,
                final_state.proof_nonce,
            );
            record.public_values.previous_init_addr = previous_init_addr;
            record.public_values.previous_finalize_addr = previous_finalize_addr;
            record.public_values.previous_init_page_idx = previous_init_page_idx;
            record.public_values.previous_finalize_page_idx = previous_finalize_page_idx;
            record.public_values.last_init_addr = last_init_addr;
            record.public_values.last_finalize_addr = last_finalize_addr;
            record.public_values.last_init_page_idx = last_init_page_idx;
            record.public_values.last_finalize_page_idx = last_finalize_page_idx;
            record.finalize_public_values::<SP1Field>(false);
            (record, None)
        }
        TraceData::Precompile(artifacts, code) => {
            let mut main_record =
                ExecutionRecord::new(program.clone(), common_input.nonce, opts.global_dependencies_opt);
            let total_events: usize = artifacts
                .iter()
                .map(|slice| slice.end_idx.saturating_sub(slice.start_idx))
                .sum();
            main_record
                .precompile_events
                .events
                .insert(code, Vec::with_capacity(total_events));

            let downloads = artifacts
                .iter()
                .map(|slice| {
                    let artifact_client = artifact_client.clone();
                    let artifact = slice.artifact.clone();
                    async move {
                        artifact_client
                            .download::<Vec<(
                                sp1_core_executor::events::SyscallEvent,
                                sp1_core_executor::events::PrecompileEvent,
                            )>>(&artifact)
                            .await
                    }
                })
                .collect::<Vec<_>>();
            let results = sp1_prover_types::await_scoped_vec(downloads)
                .await
                .map_err(|error| {
                    TaskError::Fatal(anyhow!("failed to download precompile events: {error}"))
                })?;

            for (index, events) in results.into_iter().enumerate() {
                let events = events?;
                let PrecompileArtifactSlice {
                    start_idx,
                    end_idx,
                    ..
                } = artifacts[index].clone();
                main_record
                    .precompile_events
                    .events
                    .get_mut(&code)
                    .unwrap()
                    .extend(events.into_iter().skip(start_idx).take(end_idx - start_idx));
            }

            main_record.public_values.update_initialized_state(
                program.pc_start_abs,
                program.enable_untrusted_programs,
            );
            (main_record, None)
        }
    };

    let deferred_upload_handle = deferred_record.map({
        let artifact_client = artifact_client.clone();
        let worker_client = worker_client.clone();
        let deferred_output = deferred_output.clone();
        let proof_id = context.proof_id.clone();
        let deferred_marker_task_id = TaskId::new(deferred_marker_task.to_id());
        let opts = opts.clone();
        let deferred_program = program.clone();
        move |deferred_record| {
            let artifact_client = artifact_client.clone();
            let worker_client = worker_client.clone();
            let program = deferred_program.clone();
            let proof_id = proof_id.clone();
            let deferred_output = deferred_output.clone();
            let opts = opts.clone();
            tokio::spawn(async move {
                let program_len = program.instructions.len();
                let split_opts = tokio::task::spawn_blocking(move || {
                    SplitOpts::new(&opts, program_len, false)
                })
                .await
                .map_err(|error| TaskError::Fatal(error.into()))?;
                let deferred_data =
                    DeferredEvents::defer_record(deferred_record, &artifact_client, split_opts)
                        .await?;
                artifact_client.upload(&deferred_output, &deferred_data).await?;
                worker_client
                    .complete_task(proof_id, deferred_marker_task_id, TaskMetadata::default())
                    .await?;
                Ok::<(), TaskError>(())
            })
        }
    });

    let machine = CpuSP1ProverComponents::core_verifier().machine().clone();
    record = tokio::task::spawn_blocking(move || {
        machine.generate_dependencies(std::iter::once(&mut record), None);
        record
    })
    .await
    .map_err(|error| TaskError::Fatal(error.into()))?;

    let (_, proof, permit) = core_air_prover
        .setup_and_prove_shard(program, record, Some(common_input.vk.vk.clone()), permits)
        .await;
    let _ = permit.release();

    artifact_client.upload(&output, proof).await?;
    artifact_client
        .try_delete(&record_artifact, ArtifactType::UnspecifiedArtifactType)
        .await
        .ok();

    if let Some(artifacts) = precompile_artifacts {
        for PrecompileArtifactSlice {
            artifact,
            start_idx,
            end_idx,
        } in artifacts
        {
            let _ = artifact_client
                .remove_ref(
                    &artifact,
                    ArtifactType::UnspecifiedArtifactType,
                    &format!("{}_{}", start_idx, end_idx),
                )
                .await;
        }
    }

    if let Some(handle) = deferred_upload_handle {
        handle.await.map_err(|error| TaskError::Fatal(error.into()))??;
    }

    Ok(())
}

fn unique_id(prefix: &str) -> String {
    let nanos = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .expect("system clock before unix epoch")
        .as_nanos();
    format!("{prefix}-{}-{nanos}", std::process::id())
}
