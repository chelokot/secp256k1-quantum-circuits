# compiler + verification project

This root-level subproject exists to answer the strongest version of the review:
not “what does the ISA artifact suggest?”, but “what exact whole-oracle counts
can be derived once the schedule is completed into a fully quantum compiler
family?”.

It is intentionally separate from the repository mainline.

## What this subproject does

1. completes the schedule into a **fully quantum raw-32 oracle** with no
   classical tail elisions;
2. fixes **named exact compiler families** for folded lookup, phase-shell, and
   schedule orchestration;
3. lowers each named lookup family into a generated primitive-operation
   inventory below the folded lookup contract;
4. lowers the named arithmetic-kernel family into a generated
   primitive-operation inventory instead of treating leaf arithmetic as bare
   scalar opcode costs;
5. derives **whole-oracle non-Clifford and logical-qubit counts** for those
   families; and
6. verifies the completed raw-32 schedule semantically on deterministic
   secp256k1 basis-state cases; and
7. packages one selected standard-QROM family claim into an SP1 attestation bundle
   backed by a deterministic public point-add corpus.

## Strongest exact claim here

The artifacts in `compiler_verification_project/artifacts/` are exact for the
**chosen compiler families**.

That is a stricter boundary than the repository's quarantined hypothesis layer,
but still
short of a globally optimal primitive-gate proof. In particular, the arithmetic
lowerings stop at generated non-Clifford and measurement inventories; this
subproject still does **not** ship bit-for-bit Clifford-complete netlists for
every 256-bit field multiplier.
What it does ship is:

- an exact whole-oracle schedule,
- exact arithmetic-kernel generated primitive-operation inventories,
- compact arithmetic operation-stream digests for block/stage/kernel/leaf totals,
- exact lookup-family choices with generated lowered primitive-operation inventories,
- exact leaf slot allocation,
- exact phase-shell families, and
- exact whole-oracle counts relative to the chosen arithmetic kernel family.

## Main checked-in artifacts

- `family_frontier.json` — exact whole-oracle frontier for the named compiler families
- `full_raw32_oracle.json` — exact fully quantum schedule: 1 direct seed + 31 leaf calls
- `exact_leaf_slot_allocation.json` — exact versioned live-range allocation of the checked leaf
- `compiler_parameters.json` — versioned curve/window/QROAM/reusable-chunk parameter source with a stable digest
- `proof_corpus_profiles.json` — versioned ZKP case-corpus profiles: current public smoke profile and Google-comparable release target
- `release_corpus_preflight.json` — fast deterministic 9024-case Google-comparable semantic preflight over the executable leaf, with edge-category counts and a rolling case-stream digest
- `arithmetic_lowerings.json` — generated primitive-operation inventories for the named arithmetic-kernel family
- `arithmetic_operation_ir.json` — compact arithmetic operation-stream IR: every arithmetic lowering block is materialized into a canonical primitive-operation stream with per-block digests and reconstructed stage/kernel/leaf totals; modular add/sub/mul kernels are generated from the embedded `executable_modular_circuit_ir`, and drift between that IR and emitted arithmetic kernels is a fast-check failure
- `modular_arithmetic_certificate.json` — proof-bound reduced-width executable pseudo-Mersenne arithmetic certificate plus 256-bit field-mul stage-count binding
- `tail_macro_liveness.json` — generated diagnostic liveness pressure test for the `complete_a0_all_streamed_tail` formula DAG and the remaining three-slot schedule obligation
- `tail_macro_reversibility.json` — generated raw-domain and valid-projective-subspace injectivity check for the tail macro's reversible boundary
- `streamed_lookup_table_multiplier_resource.json` — explicit table-controlled multiplier resource contract for streamed lookup coordinate bits
- `standard_qrom_lookup_assessment.json` — machine-checked assessment showing that the selected lookup/resource contract is a standard-QROM primitive-circuit result
- `logical_resource_ledger.json` — generated peak-live-qubit owner ledger and QROAMClean block-size tradeoff sweep
- `qroam_primitive_certificate.json` — generated QROAMClean `K=1` primitive-count certificate for the selected reusable chunk stream, including traversed compute/cleanup segment counts and target/junk workspace
- `qroam_reference_crosscheck.json` — independent QROAMClean gate/workspace reference calculation plus reduced-domain table-select semantics; it separately checks the actual 155-bit reusable chunk stream and the full-field 256-bit ledger sweep before binding into the reusable-chunk resource document
- `release_corpus_preflight.json` — fast 9024-case semantic preflight over the Google-comparable release target corpus, with forced edge-category counts and a rolling case-stream digest; this is release-size semantic evidence, not a ZKP proof
- `resource_liveness_certificate.json` — ZKP-bound liveness certificate deriving owner-capacity requirements from executable leaf liveness, QROAMClean workspace, and phase-shell lowering artifacts
- `public_candidate_materialized_circuit_manifest.json` — no-ZKP public-candidate primitive-stream manifest binding the reusable-chunk headline to deterministic base, QROAM-segment, phase-shell rows, concrete operand wires, liveness/owner bindings, and a full materialized flat-netlist digest derived by scanning every emitted primitive operation
- `public_engine_manifest.json` — no-ZKP public engine manifest deriving public totals from the public-candidate `materialized_flat_netlist`, then binding executable instruction/wire/schedule/owner/resource-term streams, the flat execution probe, compiler parameters, semantic-boundary evidence, and primitive-operation evidence from arithmetic operation IR, QROAM primitive certificate, and phase-shell lowering; this artifact no longer consumes the ZKP input
- `engine_completion_audit.json` — no-ZKP completion/status audit generated from the materialized public engine artifacts; it passes only when public totals, source bindings, QROAM costs, owner/liveness probes, modular arithmetic IR generation, and semantic boundary evidence are coherent, and it keeps `clifford_complete_goal_achieved` false while tail macro/global schedule and single-engine ZKP-input derivation remain explicit macro boundaries
- `artifact_digest_tree.json` — chunked SHA-256/Merkle manifest for tracked large artifacts, generated from the checked tree so reviewers can verify large JSON/CSV/proof blobs by chunks rather than by one opaque file hash
- `proof_environment_contract.json` — checked proof-environment contract binding required tools, no-prover edit-loop gates, publication freshness gates, direct compressed/Groth16 verifier commands, public-headline artifact digests, and curated proof-manifest records
- `proof_publication_status.json` — checked publication-readiness artifact derived from the shared proof-status engine; it keeps `publication_ready` separate from resource-contract `pass`, records stale systems/blockers, and binds the public headline, proof manifest, and proof-environment contract
- `constant_provenance.json` — release-critical constant provenance manifest binding the selected phase shell, headline resource totals, public limits, ZKP family document, public headline JSON, and counted-resource manifest back to their source artifacts while scanning for the previous hardcoded ZKP count pattern
- `module_library.json` — arithmetic-kernel summary used by the frontier
- `lookup_lowerings.json` — generated primitive-operation inventories for the named folded lookup families
- `phase_shell_lowerings.json` — generated phase-operation inventories for the named full-register and semiclassical inverse-QFT shells
- `generated_block_inventories.json` — generated whole-oracle block inventories for the supporting decomposition layer
- `ft_ir_compositions.json` — compositional FT-style call graphs and leaf sigma reconstructions for every named compiler family
- `whole_oracle_recount.json` — independent exact whole-oracle recount derived from the FT IR leaf sigma
- `qubit_breakthrough_analysis.json` — exact qubit bottleneck decomposition, Google break-even thresholds, and counterfactual slot/field-width sweeps around the internal lowest-qubit family
- `subcircuit_equivalence.json` — cross-layer equivalence witnesses for traced ISA opcodes, lowered lookup families, boundary no-op semantics, resource ownership, and generated whole-oracle composition
- `primitive_multiplier_library.json` — auditable manifest for all 341 multiplier instances in the raw-32 oracle
- `phase_shell_families.json` — compact summary of the exact phase-shell lowering families
- `table_manifests.json` — exact folded-table dimensions and canonical window bases
- `full_attack_inventory.json` — structural inventory for the completed oracle
- `verification_summary.json` — deterministic semantic replay plus cross-artifact integrity checks for schedule, slot allocation, FT IR composition, lowered inventories, frontier, physical-estimator integrations, and transfer handoffs
- `azure_resource_estimator_targets.json` — exact-family Microsoft Resource Estimator target profiles built from the official predefined presets
- `azure_resource_estimator_results.json` — recorded Microsoft Resource Estimator outputs for every exact family under every checked target profile
- `cain_exact_transfer.json` — heuristic physical transfer for the exact families
- `azure_resource_estimator_logical_counts.json` — logicalCounts-style handoff artifact for physical estimators
- `zkp_attestation_input.json` — prepared SP1 attestation bundle carrying the public document digests, committed compiler parameters, a compiled point-add leaf, a proof-register/resource-owner contract, and the deterministic public cases for the selected standard-QROM family claim
- `zkp_attestation_claim.json` — standalone public claim derived from the selected exact family
- `zkp_attestation_family.json` — selected standard-QROM family summary bound by the checked SP1 guest
- `zkp_attestation_cases.json` — deterministic public point-add cases used by the checked SP1 guest
- `zkp_attestation_public_values.json` — committed public values from the checked SP1 run
- `zkp_attestation_fixture_core.json` — checked SP1 core fixture for the attested bundle
- `zkp_attestation_fixture_compressed.json` — checked SP1 compressed fixture for the attested bundle
- `zkp_attestation_fixture_groth16.json` — checked SP1 Groth16 fixture for the attested bundle
- `zkp_attestation_proof_compressed.bin` — checked compressed SP1 proof bundle for local re-verification
- `zkp_attestation_proof_groth16.bin` — checked binary Groth16 proof bundle for the attested bundle
- `zkp_attestation_groth16_verifier/groth16_vk.bin` — checked Groth16 verifying key for cheap local re-verification of the checked proof bundle
- local proof runs also emit reusable binary proof bundles such as `zkp_attestation_proof_compressed.bin`, `zkp_attestation_wrap_proof.bin`, and `zkp_attestation_proof_groth16.bin` into the selected output directory

## Current central boundary result

- **public standard-QROAM headline:** `36,957,412 non-Clifford`, `1,199 logical qubits`

The public headline is selected in
`compiler_verification_project/artifacts/public_headline_result.json`. It uses
a reusable-chunk standard QROAMClean `K = 1` lookup boundary, an exact
semiclassical-QFT phase shell, and the executable reusable-chunk point-add leaf.
The resulting live-qubit formula is:

`4 * 256 + 1 control + 173 lookup workspace + 1 phase = 1,199 logical qubits`

The `173` lookup-workspace term is `18` folded-control qubits plus one live
155-bit QROAMClean chunk target for `K = 1`; there are no junk registers at
this low-workspace block size. Each chunk stream pays `65,536` non-Clifford
operations: `32,768` for standard QROAM compute and `32,768` for measured
uncompute. No full field-sized lookup x/y output lane is free or borrowed from
the interface.

The older `34,925,796 / 1,044` three-slot family remains checked as a reference
boundary in `family_frontier.json`, `logical_resource_ledger.json`, and the
root attestation bundle. The reusable-chunk candidate directory contains the
core/compressed/Groth16 fixtures and proof bundles for the public
`36,957,412 / 1,199` candidate result; use `proof_status.py --require-all-current` as the
freshness gate after any resource-certificate or guest change.
`headline_resource_manifest.json` is the current-headline counted-resource
stream manifest. It expands the reusable-chunk counted-resource IR into term
rows and liveness rows, reconstructs `36,957,412 / 1,199`, and prevents the
older three-slot `materialized_circuit_manifest.json` from being mistaken for
the promoted result. `public_candidate_materialized_circuit_manifest.json`
adds the current public candidate's own primitive-stream boundary: one
non-QROAM base run, all expanded QROAM segment runs, the selected phase-shell
rows, and a materialized flat stream whose public totals are computed from the
emitted primitive operations rather than from side formulas. Lookup-base rows
are source-bound per lowering block, not just by family-level totals, and the
operand-source binding report rejects block-stream or aggregate-count drift.
`constant_provenance.json` separately binds the release
critical phase-shell counts, headline totals, and publication limits from their
source artifacts into the ZKP candidate input and public headline document, and
fails if those ZKP-family resource fields become integer literals again.

`standard_qrom_lookup_assessment.json` records the standard-QROM status and
rejects the old bitwise-banked path-select boundary as a public standard-QROM
claim.

The compiler frontier intentionally publishes one repository result here rather
than separate low-qubit and low-gate branches. Historical family lowerings
remain auditable in the lowering artifacts, but the checked frontier, proof
input, public values, and docs are centered on this one executable boundary
contract.

## Interpreting the results

This subproject is strongest when read as a **compiler-family exact oracle**,
not as a claim of hidden-Google reconstruction, global optimality, or a
Clifford-complete full-Shor primitive-gate netlist.

Its defining exact features are:

- exact slot allocation cuts the checked streamed lookup tail leaf to a
  **3-slot arithmetic peak**;
- explicit arithmetic lowerings reconstruct the leaf-side non-Clifford totals
  from generated primitive-operation inventories instead of from naked opcode formulas;
- the modular arithmetic certificate executes reduced-width pseudo-Mersenne
  analogues exhaustively and binds the 256-bit field-mul reduction stage counts
  back to the arithmetic lowering artifact;
- explicit lookup lowerings reconstruct each lookup-family count from generated
  primitive-operation inventories instead of from naked family formulas;
- explicit phase-shell lowerings reconstruct Hadamard, rotation, measurement,
  and rotation-depth counts from generated phase-operation inventories instead of
  from shell-level placeholders;
- FT IR compositions reconstruct each family from hierarchical bundles plus a
  traversed leaf sigma instead of only from flattened generated blocks;
- whole-oracle recount reconstructs the frontier totals from the FT IR leaf
  sigma rather than directly from the generated block inventory layer;
- subcircuit-equivalence witnesses bind traced ISA arithmetic/flag opcodes,
  lowered lookup-family semantics, boundary no-op behavior, and generated
  whole-oracle composition back to the checked source artifacts;
- exact logicalCounts are bound to explicit Microsoft Resource Estimator target
  profiles and recorded estimator outputs instead of stopping at a seed-only
  handoff layer;
- generated whole-oracle block inventories reconstruct each family total from
  arithmetic blocks, lookup blocks, qubit contributors, and explicit
  phase-shell lowering blocks;
- a semiclassical-QFT phase-shell family removes the fixed **512 live phase
  qubits** assumption; and
- the no-free-wire resource contract proves counted owner capacity at the
  executable leaf/interface boundary, with zero borrowed lookup coordinate field
  lanes and an explicit remaining macro-internal liveness boundary; and
- the streamed table-multiplier resource contract proves that lookup coordinate
  targets and QROAMClean junk registers are counted together with the
  corresponding standard-QROAM table-data selection gates included in the
  arithmetic leaf total; and
- the standard-QROM lookup assessment binds those same numbers to the selected
  standard-QROAM primitive-circuit resource contract.

## SP1 attestation layer

This subproject now also ships an SP1 workspace under
`compiler_verification_project/zkp_attestation/`. It stays at the same exact
boundary as the compiler-family artifacts:

- the checked JSON claim, family summary, and case corpus remain the
  source-of-truth sidecars for audit and regeneration
- the proof input carries their public digests plus a prepared compiled leaf
  and deterministic public cases, so the guest does not spend proof time
  re-hashing and compiling the raw documents
- it replays the exact point-add leaf on every public case
- it checks the affine group law for every case
- it reconstructs the claimed full-oracle non-Clifford and logical-qubit
  formulas from compact public summaries derived from the selected family

The checked core fixture is
`compiler_verification_project/artifacts/zkp_attestation_fixture_core.json`.
The checked compressed fixture is
`compiler_verification_project/artifacts/zkp_attestation_fixture_compressed.json`.
The checked Groth16 fixture is
`compiler_verification_project/artifacts/zkp_attestation_fixture_groth16.json`.
The checked compressed proof bundle is
`compiler_verification_project/artifacts/zkp_attestation_proof_compressed.bin`.
The checked Groth16 proof bundle is
`compiler_verification_project/artifacts/zkp_attestation_proof_groth16.bin`,
and the repo ships the matching verifying key at
`compiler_verification_project/artifacts/zkp_attestation_groth16_verifier/groth16_vk.bin`
so the checked proof can be re-verified locally without rebuilding the large
vk-specific Groth16 dev artifacts. The JSON fixture stores the backend proof
bytes, while the `.bin` file stores the full SP1 proof bundle plus public
values.
The checked Groth16 proving path is pinned to the vendored
`compiler_verification_project/zkp_attestation/vendor/sp1-recursion-gnark-ffi`
patch set, which is also part of the curated proof manifest.
The root proof bundle binds the older three-slot reference family. The public
headline proof bundle lives in
`compiler_verification_project/artifacts/zkp_attestation_reusable_chunk_candidate/`
and must be rebuilt before it can bind the reusable-chunk `36,957,412 / 1,199`
result with `8 / 8` deterministic public cases.

This is similar in shape to Google's disclosure model, but it is still a proof
at the repository exact-family boundary, not a primitive-gate full-Shor proof.

## Quick start

From the repository root:

```bash
python compiler_verification_project/scripts/build.py
python compiler_verification_project/scripts/build.py --target composition-artifacts
python compiler_verification_project/scripts/build.py --target materialized-circuit-manifest
python compiler_verification_project/scripts/build.py --target proof-environment-contract
python compiler_verification_project/scripts/build.py --target proof-publication-status
python compiler_verification_project/scripts/build.py --target constant-provenance
python compiler_verification_project/scripts/build.py --target resource-zkp-and-public
python compiler_verification_project/scripts/build.py --target zkp-and-public
python compiler_verification_project/scripts/build.py --target release-candidate-zkp
python compiler_verification_project/scripts/verify.py --cases 16
python compiler_verification_project/scripts/proof_status.py
python compiler_verification_project/scripts/fast_zkp_preflight.py
python compiler_verification_project/scripts/release_candidate_preproof.py --dry-run-json
python compiler_verification_project/scripts/proof_environment_report.py
python compiler_verification_project/scripts/verify_public_headline.py
python compiler_verification_project/scripts/build_zkp_attestation_input.py --cases 8
python compiler_verification_project/scripts/build_zkp_attestation_input.py --profile release --output-dir compiler_verification_project/artifacts/zkp_attestation_release_candidate
python compiler_verification_project/scripts/materialize_exact_circuits.py
```

Use `build.py --target resource-zkp-and-public` for the normal reusable-chunk
resource edit loop: it refreshes `reusable_chunk_lowering.json`, the candidate
ZKP input bundle, and the public headline JSON without rebuilding every compiler
artifact. Use `build.py --target composition-artifacts` after changing resource
or frontier accounting that feeds the composition layer; it refreshes
`full_attack_inventory.json`, `subcircuit_equivalence.json`, and
`headline_opcode_coverage.json` without touching any prover. Use
`build.py --target materialized-circuit-manifest` to refresh the segmented
operation-stream digest/Merkle manifest without a full rebuild. Use
`build.py --target proof-environment-contract` after changing proof paths,
runbook commands, proof manifest membership, or public-headline verification
commands. Use `build.py --target proof-publication-status` after changing
proof-status logic, public-headline pass/freshness semantics, or publication
gate wiring. Use `build.py --target zkp-and-public` when only attestation
wrapping metadata changed.
Checked artifact tests reuse existing build/verification summaries by default;
set `SECP256K1_OPEN_AUDIT_FORCE_REBUILD=1` only when you intentionally want a
test run to regenerate those summaries.
Use `build.py --target release-candidate-zkp` or
`build_zkp_attestation_input.py --profile release` to prepare the 9024-case
Google-comparable input bundle without invoking SP1 proving.
Use `release_candidate_preproof.py` to build that release input in an isolated
directory, and add `--execute` to run the SP1 guest execute path over all 9024
cases without invoking compressed or Groth16 proving.
Use `fast_zkp_preflight.py` for the ordinary resource/ZKP edit loop. It runs
`proof_status.py`, the targeted integrity groups, focused pytest coverage, and
the attestation-library Rust unit tests, and it rejects any command plan that
would invoke a prover. The targeted integrity groups include the 9024-case
release-corpus preflight, so corpus drift is caught before spending prover time.
For a publication gate after proof rebuilds, add `--require-current-proofs`;
this changes only the freshness check to `proof_status.py --require-all-current`
and still does not invoke a prover.
Use `proof_environment_report.py` before a compressed/Groth16 rebuild; it emits
a JSON readiness report for the local Rust/SP1/protobuf/clang/Go toolchain and
can fail closed with `--require-ready`.
`proof_environment_contract.json` is the checked runbook companion: integrity
tests regenerate it, require proof-manifest records for all public-headline
checked artifacts, require no `--prove` in fast/publication gates, and require
direct compressed/Groth16 verification commands to point at the checked input,
proof bundles, and Groth16 verifier-key directory.
`proof_publication_status.json` is the checked freshness companion: it is
generated from the same library used by `proof_status.py`, records the exact
stale systems and blockers, and lets integrity tests verify that the public
headline `pass` flag agrees with proof freshness without treating a stale proof
bundle as a resource-count failure.

For a tight loop on one integrity layer, use `--groups` to avoid the semantic
replay and artifact rewrite:

```bash
python compiler_verification_project/scripts/verify.py --summary --groups modular_arithmetic_certificate_checks qroam_primitive_certificate_checks qroam_reference_crosscheck_checks
```

The reusable-chunk SP1 resource contract also embeds the modular-arithmetic,
QROAM primitive, and independent QROAM reference certificates, so changing any
of them invalidates the proof input until the proof layers are rebuilt.
For the no-prover engine loop, `public_engine_manifest.json` and
`engine_completion_audit.json` are the tighter artifacts:
`fast_engine_verify.py` regenerates them, checks the public-candidate
materialized flat stream and semantic evidence, and rejects
arithmetic-operation, QROAM-cost/workspace, or phase-shell drift before
compressed or Groth16 proof work is relevant. The completion audit also rejects
false full-completion claims: a passing audit currently means the public claim
is materialized and source-bound with explicit remaining macro boundaries, not
that the full Clifford-complete engine goal is done.
Proof fixtures are also expected to bind the exact prepared input by
`input_path`, `input_sha256`, and `input_size_bytes`; `proof_status.py` treats
fixtures that explicitly declare no input metadata, or that omit those fields,
as stale even if their proof binary digests still match. It also cross-checks
fixture JSON, proof bundles, and the Groth16 verifier key against
`artifacts/package/proof_manifest.json`, so the cheap freshness gate catches
release-manifest drift without invoking a verifier or prover.

`materialize_exact_circuits.py` writes ignored whole-oracle operation streams
for the selected exact compiler families under
`compiler_verification_project/generated_circuits/`. With no family arguments it
materializes the central public standard-QROM family; use `--all-families` to dump every checked exact family or
`--list-families` to inspect the available names.

The SP1 workspace requires `sp1up` or `cargo-prove`, plus `protoc` and a
working `libclang` for bindgen. The checked attestation bundle can be replayed
with:

```bash
python compiler_verification_project/scripts/verify_public_headline.py
python compiler_verification_project/scripts/verify_public_headline.py --verify-compressed
python compiler_verification_project/scripts/verify_public_headline.py --verify-groth16
```

During development, run
`python compiler_verification_project/scripts/proof_status.py` before any heavy
prover command. It reports whether core, compressed, and Groth16 fixtures still
bind the current candidate input and checked proof binaries. The
`--require-all-current` flag is a final-gate check: it exits nonzero when any
proof layer is stale, without trying to rebuild it.
Compressed and Groth16 proving are deliberately gated out of the ordinary
development loop: `run_zkp_attestation_guarded.py` refuses those proof systems
unless `--allow-heavy-proof` is present. Use that flag only after the fast
build, targeted `verify.py --groups ...`, `proof_status.py`, and metadata
checks are already clean enough to justify spending prover time.

The first command is metadata-only and validates the public headline, checked
input, public values, committed source-document semantic hashes, fixtures,
proof-binary digests, wrap proof, and Groth16 verifier key from the checked
branch state. The latter two commands additionally invoke the compressed or
Groth16 verifier against the checked proof bundle. While source artifacts are
ahead of the checked proof bundles, the metadata command is expected to fail on
freshness and fixture-input binding checks; `proof_status.py` gives the cheap
diagnostic without invoking a verifier or prover.

The lower-level guarded runner is:

```bash
python compiler_verification_project/scripts/run_zkp_attestation_guarded.py --execute
python compiler_verification_project/scripts/run_zkp_attestation_guarded.py --execute --write-core-fixture
python compiler_verification_project/scripts/run_zkp_attestation_guarded.py --prove --system core
python compiler_verification_project/scripts/run_zkp_attestation_guarded.py --verify-proof-input /tmp/zkp_attestation_proof_groth16.bin --system groth16
python compiler_verification_project/scripts/run_zkp_attestation_guarded.py --verify-proof-input compiler_verification_project/artifacts/zkp_attestation_proof_groth16.bin --system groth16
```

The guarded runner now defaults to `--resource-profile balanced`, which keeps
`systemd-run` CPU, memory, and I/O caps but allows bounded multi-worker SP1
parallelism. Use `--resource-profile safe` for the old single-worker floor, or
`--resource-profile throughput` if the local machine has spare cores and you
want the fastest bounded local profile. The raw cargo entrypoint still exists
for manual use; pass `--resource-profile full` only if you explicitly want to
remove the in-process SP1 worker throttling. Pass `--skip-build` to reuse the
current host binary when you are profiling repeated local proof runs and do not
want to pay the Cargo rebuild cost each time. Use repeated `--sp1-env
NAME=VALUE` flags to tune executor or prover settings such as
`MINIMAL_TRACE_CHUNK_THRESHOLD`, `ELEMENT_THRESHOLD`, or `MEMORY_LIMIT`, and
use repeated `--systemd-property NAME=VALUE` flags when you need to override
the wrapper's local `systemd-run` limits for a single run. For example:

The execute path now uses SP1's blocking `LightProver`, so local `--execute`
replays avoid initializing the full proving stack while `--prove` still uses
the normal prover path.

Each non-core proof run now writes a binary proof bundle next to the JSON
fixture. Groth16 retries can either reuse a completed compressed proof or, once
`shrink_wrap` has completed once, jump straight back in from the cached wrap
bundle without paying that stage again. Finished proof bundles can also be
re-verified cheaply with `--verify-proof-input`. A typical local flow is:

```bash
python compiler_verification_project/scripts/run_zkp_attestation_guarded.py \
  --skip-build \
  --resource-profile safe \
  --allow-heavy-proof \
  --prove --system compressed \
  --output-dir /tmp/zkp-attestation-compressed

python compiler_verification_project/scripts/run_zkp_attestation_guarded.py \
  --skip-build \
  --resource-profile safe \
  --allow-heavy-proof \
  --prove --system groth16 \
  --compressed-proof-input /tmp/zkp-attestation-compressed/zkp_attestation_proof_compressed.bin \
  --output-dir /tmp/zkp-attestation-groth16

python compiler_verification_project/scripts/run_zkp_attestation_guarded.py \
  --skip-build \
  --resource-profile safe \
  --allow-heavy-proof \
  --prove --system groth16 \
  --wrap-proof-input /tmp/zkp-attestation-groth16/zkp_attestation_wrap_proof.bin \
  --output-dir /tmp/zkp-attestation-groth16-retry

python compiler_verification_project/scripts/run_zkp_attestation_guarded.py \
  --skip-build \
  --resource-profile balanced \
  --verify-proof-input compiler_verification_project/artifacts/zkp_attestation_proof_groth16.bin \
  --system groth16
```

```bash
python compiler_verification_project/scripts/run_zkp_attestation_guarded.py \
  --skip-build \
  --resource-profile balanced \
  --prove --system core \
  --sp1-env ELEMENT_THRESHOLD=201326592 \
  --sp1-env MINIMAL_TRACE_CHUNK_THRESHOLD=65536 \
  --systemd-property CPUQuota=250% \
  --systemd-property MemoryMax=12G
```

The wrapper also prints a host-memory-pressure warning before the run when the
current machine has less free RAM than the requested `MemoryHigh` budget or
swap is nearly exhausted. That warning is advisory, but it is a good sign that
local proof attempts may die by `oom-kill` before they hit the configured
wrapper limits. Scoped runs now also print their deterministic systemd scope
name up front, and on failure the wrapper emits a short postmortem with
`Result`, `MemoryPeak`, `CPUUsage`, and the recent unit journal so local OOM
failures are visible without a separate `journalctl` lookup.
