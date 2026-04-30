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
7. packages one selected exact-family claim into an SP1 attestation bundle
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
- exact lookup-family choices with generated lowered primitive-operation inventories,
- exact leaf slot allocation,
- exact phase-shell families, and
- exact whole-oracle counts relative to the chosen arithmetic kernel family.

## Main checked-in artifacts

- `family_frontier.json` — exact whole-oracle frontier for the named compiler families
- `full_raw32_oracle.json` — exact fully quantum schedule: 1 direct seed + 31 leaf calls
- `exact_leaf_slot_allocation.json` — exact versioned live-range allocation of the checked leaf
- `arithmetic_lowerings.json` — generated primitive-operation inventories for the named arithmetic-kernel family
- `module_library.json` — arithmetic-kernel summary used by the frontier
- `lookup_lowerings.json` — generated primitive-operation inventories for the named folded lookup families
- `phase_shell_lowerings.json` — generated phase-operation inventories for the named full-register and semiclassical inverse-QFT shells
- `generated_block_inventories.json` — generated whole-oracle block inventories for the supporting decomposition layer
- `ft_ir_compositions.json` — compositional FT-style call graphs and leaf sigma reconstructions for every named compiler family
- `whole_oracle_recount.json` — independent exact whole-oracle recount derived from the FT IR leaf sigma
- `qubit_breakthrough_analysis.json` — exact qubit bottleneck decomposition, Google break-even thresholds, and counterfactual slot/field-width sweeps around the internal lowest-qubit family
- `subcircuit_equivalence.json` — cross-layer equivalence witnesses for traced ISA opcodes, lowered lookup families, the coherent cleanup window, and generated whole-oracle composition
- `primitive_multiplier_library.json` — auditable manifest for all 341 multiplier instances in the raw-32 oracle
- `phase_shell_families.json` — compact summary of the exact phase-shell lowering families
- `table_manifests.json` — exact folded-table dimensions and canonical window bases
- `full_attack_inventory.json` — structural inventory for the completed oracle
- `verification_summary.json` — deterministic semantic replay plus cross-artifact integrity checks for schedule, slot allocation, FT IR composition, lowered inventories, frontier, physical-estimator integrations, and transfer handoffs
- `azure_resource_estimator_targets.json` — exact-family Microsoft Resource Estimator target profiles built from the official predefined presets
- `azure_resource_estimator_results.json` — recorded Microsoft Resource Estimator outputs for every exact family under every checked target profile
- `cain_exact_transfer.json` — heuristic physical transfer for the exact families
- `azure_resource_estimator_logical_counts.json` — logicalCounts-style handoff artifact for physical estimators
- `zkp_attestation_input.json` — prepared SP1 attestation bundle carrying the public document digests, a compiled point-add leaf, and the deterministic public cases for the selected exact-family claim
- `zkp_attestation_claim.json` — standalone public claim derived from the selected exact family
- `zkp_attestation_family.json` — selected exact-family summary bound by the checked SP1 guest
- `zkp_attestation_cases.json` — deterministic public point-add cases used by the checked SP1 guest
- `zkp_attestation_public_values.json` — committed public values from the checked SP1 run
- `zkp_attestation_fixture_core.json` — checked SP1 core fixture for the attested bundle
- `zkp_attestation_fixture_compressed.json` — checked SP1 compressed fixture for the attested bundle
- `zkp_attestation_fixture_groth16.json` — checked SP1 Groth16 fixture for the attested bundle
- `zkp_attestation_proof_groth16.bin` — checked binary Groth16 proof bundle for the attested bundle
- `zkp_attestation_groth16_verifier/groth16_vk.bin` — checked Groth16 verifying key for cheap local re-verification of the checked proof bundle
- local proof runs also emit reusable binary proof bundles such as `zkp_attestation_proof_compressed.bin`, `zkp_attestation_wrap_proof.bin`, and `zkp_attestation_proof_groth16.bin` into the selected output directory

## Current central exact result

- **central exact family:** `22,753,831 non-Clifford`, `1,586 logical qubits`

The central family uses a fully bitwise banked unary QROM decode with measured
uncompute, an exact semiclassical-QFT phase shell, and an interface-borrowed
leaf contract that reuses `lookup_x` as scratch after its final lookup-coordinate
read. The resulting live-qubit formula is:

`6 * 256 + 1 control + 48 lookup workspace + 1 phase = 1,586 logical qubits`

The lower-space linear-scan family remains in the internal frontier table, but
it is not the public headline because it is above the 24M non-Clifford target.
`qubit_breakthrough_analysis.json` isolates the remaining break-even thresholds
against the cited Google qubit lines.

## Interpreting the results

This subproject is strongest when read as a **compiler-family exact oracle**,
not as a claim of hidden-Google reconstruction or global optimality.

Its defining exact features are:

- exact slot allocation cuts the checked lookup-fed leaf from **8 tracked
  arithmetic registers** to a **7-slot physical arithmetic peak**;
- the interface-borrowed contract reuses the consumed `lookup_x` coordinate
  wire as scratch, cutting the public headline family to a **6-slot persistent
  arithmetic register file**;
- explicit arithmetic lowerings reconstruct the leaf-side non-Clifford totals
  from generated primitive-operation inventories instead of from naked opcode formulas;
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
  lowered lookup-family semantics, the coherent cleanup window, and generated
  whole-oracle composition back to the checked source artifacts;
- exact logicalCounts are bound to explicit Microsoft Resource Estimator target
  profiles and recorded estimator outputs instead of stopping at a seed-only
  handoff layer;
- generated whole-oracle block inventories reconstruct each family total from
  arithmetic blocks, lookup blocks, qubit contributors, and explicit
  phase-shell lowering blocks;
- a semiclassical-QFT phase-shell family removes the fixed **512 live phase
  qubits** assumption; and
- those ingredients place the central exact family at **1,586 logical qubits**
  while keeping **22,753,831 non-Clifford**.

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
Its public values bind the current central exact-family claim and the `8 / 8`
deterministic public cases in
`compiler_verification_project/artifacts/zkp_attestation_cases.json`.

This is similar in shape to Google's disclosure model, but it is still a proof
at the repository exact-family boundary, not a primitive-gate full-Shor proof.

## Quick start

From the repository root:

```bash
python compiler_verification_project/scripts/build.py
python compiler_verification_project/scripts/verify.py --cases 16
python compiler_verification_project/scripts/build_zkp_attestation_input.py --cases 8
python compiler_verification_project/scripts/materialize_exact_circuits.py
```

`materialize_exact_circuits.py` writes ignored whole-oracle operation streams
for the selected exact compiler families under
`compiler_verification_project/generated_circuits/`. With no family arguments it
materializes the central public exact family and the internal minimum-qubit
comparison family; use `--all-families` to dump every checked exact family or
`--list-families` to inspect the available names.

The SP1 workspace requires `sp1up` or `cargo-prove`, plus `protoc` and a
working `libclang` for bindgen. The checked attestation bundle can be replayed
with:

```bash
python compiler_verification_project/scripts/run_zkp_attestation_guarded.py --execute
python compiler_verification_project/scripts/run_zkp_attestation_guarded.py --execute --write-core-fixture
python compiler_verification_project/scripts/run_zkp_attestation_guarded.py --prove --system core
python compiler_verification_project/scripts/run_zkp_attestation_guarded.py --prove --system compressed
python compiler_verification_project/scripts/run_zkp_attestation_guarded.py --prove --system groth16
python compiler_verification_project/scripts/run_zkp_attestation_guarded.py --prove --system groth16 --compressed-proof-input /tmp/zkp_attestation_proof_compressed.bin
python compiler_verification_project/scripts/run_zkp_attestation_guarded.py --prove --system groth16 --wrap-proof-input /tmp/zkp_attestation_wrap_proof.bin
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
  --prove --system compressed \
  --output-dir /tmp/zkp-attestation-compressed

python compiler_verification_project/scripts/run_zkp_attestation_guarded.py \
  --skip-build \
  --resource-profile safe \
  --prove --system groth16 \
  --compressed-proof-input /tmp/zkp-attestation-compressed/zkp_attestation_proof_compressed.bin \
  --output-dir /tmp/zkp-attestation-groth16

python compiler_verification_project/scripts/run_zkp_attestation_guarded.py \
  --skip-build \
  --resource-profile safe \
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
