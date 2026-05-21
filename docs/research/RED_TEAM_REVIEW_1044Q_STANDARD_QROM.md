# Red-Team Review: 1044-Qubit Standard-QROM Frontier

Date: 2026-05-14

Reviewed commit: `4d9fefed41ca0f6b5cf6528ce8366065fc6d557a`

Headline under review:

- `32,879,331` non-Clifford
- `1,044` logical qubits
- family: `folded_standard_qroam_streamed_coordinate_v1__streamed_lookup_tail_leaf_v1__semiclassical_qft_v1`

Current post-remediation checked headline on this branch:

- `34,736,076` non-Clifford
- `1,044` logical qubits
- same family, now with explicit secp256k1 pseudo-Mersenne multiplication
  reduction counted in the arithmetic lowering

This document is intentionally adversarial. It is not a release note and not a
claim that the result is false. It records every major place where an external
reviewer still has to trust the repo authors, the abstraction boundary, or a
hand-built accounting layer instead of trusting a single primitive circuit
engine that emits and counts one flat executable object.

## Executive Verdict

The result is strong inside the repository's current boundary, but it is not yet
as confidence-preserving as Google's disclosure boundary.

After deeper review, the highest-severity issue is in the ZKP binding layer:
the active SP1 program uses the prepared-input path
`run_prepared_attestation`, not the older full-document `run_attestation` path.
The prepared path does **not** recompute the public `claim_sha256`,
`leaf_sha256`, `family_sha256`, or `case_corpus_sha256` from embedded full
documents inside the guest. It checks formulas and executes the prepared leaf
and prepared cases, then copies those hash strings into public values. The
repo-side Python builder and tests currently ensure the checked files agree, but
that agreement is not itself enforced inside the Groth16 statement.

The strongest defensible statement is:

> The repository currently contains a checked standard-QROM compiler-family
> boundary whose artifacts, resource ledger, prepared SP1 public values,
> compressed proof, and Groth16 proof agree on `32,879,331 / 1,044`, with
> sidecar-hash binding currently enforced by repo generation/tests rather than
> fully recomputed inside the active ZKP guest.

That statement is the historical verdict for commit
`4d9fefed41ca0f6b5cf6528ce8366065fc6d557a`. The current branch has since moved
the public claim to `34,736,076 / 1,044` after adding explicit modular-reduction
cost and stronger ZKP resource binding.

The statement that is not yet defensible without more engineering is:

> This is a fully flattened primitive-gate Shor circuit with an independently
> generated exact liveness/resource count and a Google-equivalent hidden-circuit
> ZKP confidence model.

The central red-team concern is not one specific arithmetic bug. It is that the
repo still has several mutually checking generators rather than one authoritative
circuit/liveness engine. Many checks prove that checked JSON artifacts match the
Python generators, but the Python generators themselves encode important
resource semantics and macro boundaries.

## P0 Findings Summary

| ID | Severity | Finding | Why it matters | Required fix |
| --- | --- | --- | --- | --- |
| ZK-1 | P0 | Active SP1 prepared path does not recompute sidecar hashes | Public values can carry hash labels that are trusted from the input builder, not proven from full sidecars inside the circuit | Make the guest hash full claim/leaf/family/case documents, or hash canonical prepared documents whose digests are the published source of truth |
| ZK-2 | P0 | ZKP executes high-level field/macro semantics, not primitive QROAM/arithmetic lowerings | The proof checks point-add behavior for prepared cases, but not that the resource-counted primitive circuit implements that behavior | Feed the same resource IR into the guest or prove a separate lowering certificate |
| RES-1 | P0 | `complete_a0_all_streamed_tail` hides internal liveness behind a macro boundary | The `1,044` qubit result depends on internal temporaries not increasing peak live qubits | Flatten macro into scheduled IR and derive peak from that IR |
| RES-2 | P0 | Modular field arithmetic costs are model-level costs, not a generated modular circuit | Rust semantics applies `% p`; arithmetic lowering counts abstract add/sub/mul kernels whose modular-reduction completeness must be trusted | Generate modular add/sub/mul circuits including reduction and count them |
| RES-3 | P0 | Resource ledger is owner-summed, not global flat-schedule liveness | It proves owner totals agree, not that no hidden wire is live concurrently | One liveness engine over all wires, QROAM target/junk, macro scratch, and phase/control wires |
| ZK-3 | P1 | Checked compressed fixture JSON has `proof: null` while binary proof is separate | Verifiability exists, but the human-readable fixture does not itself contain the proof payload | Put digest/size/path of proof binaries into fixtures and manifest; verify them in tests |
| GOV-1 | P1 | Many release-critical constants are scattered in tests/source/docs | Drift and accidental self-confirming tests remain possible | Versioned parameter/baseline artifacts imported everywhere |

## What Is Actually Strong

- The checked headline is internally consistent across:
  - `compiler_verification_project/artifacts/family_frontier.json`
  - `compiler_verification_project/artifacts/logical_resource_ledger.json`
  - `compiler_verification_project/artifacts/standard_qrom_lookup_assessment.json`
  - `compiler_verification_project/artifacts/zkp_attestation_public_values.json`
  - compressed and Groth16 fixtures/proofs.
- `scripts/refresh_repo.py` rebuilds the repo-level artifacts and reports
  exact compiler verification `287/287`.
- `pytest -q` passed at the reviewed state.
- The proof public values bind the selected family, leaf hash, case corpus hash,
  and the final numbers.
- The earlier "free lookup x/y lane" class of error is not present in the
  current headline. The current resource contract counts `274` lookup workspace
  qubits: `18` folded-control qubits plus a `256`-qubit full-coordinate QROAM
  target at `K = 1`.
- The earlier `15 independent 2-way chunks` lookup model is no longer the
  selected public model. The selected resource model charges `65,536`
  non-Clifford per 256-bit coordinate stream.
- The earlier QROAM block-size inconsistency is not present in the selected row:
  `K = 1` implies no junk registers and `256` target qubits, so the QROAM gate
  and workspace formulas agree for the selected point.

## Critical Trust Assumptions

### 0. The active ZKP does not recompute the sidecar document hashes

This is the most important deeper-review finding.

There are two Rust attestation paths:

- `run_attestation(input: &AttestationInput)` handles schema
  `compiler-project-zkp-attestation-input-v2` and explicitly recomputes
  semantic hashes for full claim, leaf, family, and case-corpus documents.
- `run_prepared_attestation(input: &PreparedAttestationInput)` handles schema
  `compiler-project-zkp-attestation-input-v4`, which is the path used by
  `compiler_verification_project/zkp_attestation/program/src/main.rs`.

The active SP1 program reads `PreparedAttestationInput` and calls
`run_prepared_attestation`. In that path:

- the guest checks `input.schema` and formulas;
- the guest executes `input.prepared_leaf` on `input.prepared_case_corpus`;
- the guest copies `input.claim_sha256`, `input.leaf_sha256`,
  `input.family_sha256`, and `input.case_corpus_sha256` into public values;
- the guest does not recompute those hashes from full sidecar documents, because
  the full sidecar documents are not in the prepared input.

Evidence:

- active entrypoint:
  `compiler_verification_project/zkp_attestation/program/src/main.rs`
- full-document path recomputes hashes:
  `compiler_verification_project/zkp_attestation/lib/src/lib.rs:2316-2359`
- prepared path starts at:
  `compiler_verification_project/zkp_attestation/lib/src/lib.rs:2492`
- prepared path copies public hash labels at:
  `compiler_verification_project/zkp_attestation/lib/src/lib.rs:2610-2617`
- Python builder computes sidecar hashes outside the guest:
  `compiler_verification_project/src/zkp_attestation.py:523-650`

This means the current Groth16 proof does not, by itself, prove:

- `leaf_sha256` is the semantic hash of the checked
  `streamed_lookup_tail_leaf.json`;
- `family_sha256` is the semantic hash of the checked
  `zkp_attestation_family.json`;
- `claim_sha256` is the semantic hash of the checked
  `zkp_attestation_claim.json`;
- `case_corpus_sha256` is the semantic hash of the checked
  `zkp_attestation_cases.json`.

The repo tests and artifact generator do check that the checked files match the
default builder output. That is valuable, but it is an external release-process
check, not an in-circuit proof constraint.

Attack shape against the statement, not necessarily against the current repo
commit:

1. Create a prepared input with a valid easy leaf/case corpus.
2. Put arbitrary `leaf_sha256` / `family_sha256` labels in the input.
3. The prepared guest can still output those labels as public values if formulas
   and prepared cases are internally consistent.

That attack would not pass the repo's checked default-build tests if artifacts
were regenerated honestly, but a third-party verifier receiving only the proof
and public values does not get the same guarantee.

Required hardening:

- Best: use a single full-document input path in the SP1 program and recompute
  all semantic document hashes inside the guest.
- Acceptable: define the prepared input itself as the source-of-truth object,
  publish its canonical hash, and stop saying the proof binds the full JSON
  sidecars.
- Better: include both full sidecars and prepared compiled forms, and have the
  guest prove that the prepared forms are derived from the full sidecars.
- Add negative tests that mutate only `leaf_sha256`, `family_sha256`,
  `claim_sha256`, and `case_corpus_sha256` in `zkp_attestation_input.json` and
  require the SP1 guest to reject.

### 1. The all-streamed tail macro is trusted as a counted liveness boundary

The 1044-qubit result depends on replacing a multi-register leaf body with a
single macro opcode:

- `complete_a0_all_streamed_tail`
- live arithmetic slots: `qx`, `qy`, `qz`
- peak arithmetic register file: `3 * 256 = 768`

The macro is counted with a large internal non-Clifford cost, but its internal
temporaries are not exposed as simultaneous live leaf-owned field registers.
This is plausible as a compiler-family boundary, but it is not the same as
flattening the macro into a scheduled reversible circuit and deriving peak
liveness from that flat circuit.

Where trust enters:

- `compiler_verification_project/src/lookup_fed_leaf.py` defines the executable
  leaf with one macro opcode.
- `compiler_verification_project/src/arithmetic_lowering.py` assigns the macro
  internal work and cost.
- `compiler_verification_project/src/project.py` assigns only three arithmetic
  slots to the leaf.
- `compiler_verification_project/src/integrity.py` checks consistency with those
  same generators.

Required hardening:

- Flatten `complete_a0_all_streamed_tail` into an explicit primitive/lower-level
  IR with named temporary wires.
- Run liveness on the flattened IR, not on the macro-level executable leaf.
- Prove that any temporary scratch inside the macro is either sequentially
  reused inside an already counted owner or explicitly added to peak live
  qubits.

### 2. The resource ledger is still owner-summed, not circuit-derived

The current ledger is much better than previous manual tracked-register lists,
but it still sums named owners:

- arithmetic slot register file: `768`
- control slot register file: `1`
- lookup workspace: `274`
- phase shell live register: `1`
- total: `1044`

The ledger checks numeric decompositions, but it does not derive a global peak
from one time-indexed flat schedule containing arithmetic, lookup target,
lookup junk, phase qubit, MBUC measurement dependencies, and macro scratch.

Where trust enters:

- `compiler_verification_project/src/resource_ledger.py` builds owners from
  selected family fields.
- `compiler_verification_project/artifacts/logical_resource_ledger.json` proves
  internal agreement, not independent extraction from a primitive circuit.

Required hardening:

- Create one resource engine that consumes a flat scheduled IR and computes peak
  live qubits by interval analysis.
- Make owner labels derived outputs of that engine, not input accounting rows.
- Fail if any primitive wire lacks exactly one owner or if any owner capacity is
  below the sum or peak of assigned live intervals.

### 3. The arithmetic cost model is generated, but still handwritten at the block level

The non-Clifford counts are generated from block definitions, but those block
definitions are handwritten models. For example:

- field add/sub costs are encoded as `field_bits - 1`
- field multiplication is encoded as a schoolbook partial-product grid plus
  controlled add/sub paths
- macro tail cost is encoded by composing hand-modeled blocks
- MBUC measurements are counted in some blocks, but Clifford gates and exact
  scheduling constraints are not fully flattened

This is not just a style issue. A reviewer can ask whether the modeled kernel
is actually reversible, scheduled, and compatible with the advertised liveness.

The deeper issue is that the semantic interpreter and the cost model live at
different abstraction levels:

- Rust guest semantics performs BigUint field operations with `% modulus`.
- Python semantic replay also works over mathematical field values.
- `arithmetic_lowering.py` counts abstract temporary-AND ladders and schoolbook
  partial-product blocks.
- The lowering explicitly says its exact scope is non-Clifford and measurement
  inventories for named arithmetic kernels, while Clifford micro-expansions are
  outside the shipped layer.

That leaves several questions for a hostile arithmetic reviewer:

- Does the `field_add`/`field_sub` count include a complete modular reduction
  path for secp256k1's prime, or only an n-bit add/sub ladder?
- Does the `field_mul` count include the full modular multiplication,
  reduction, and cleanup required to implement `% p`, or only a schoolbook
  multiply-family proxy?
- Do measurement-based cleanup paths preserve the exact projective state in a
  way compatible with the macro's internal liveness schedule?
- Does the same arithmetic kernel produce both the semantic value and the
  counted liveness, or are semantic correctness and resource accounting coupled
  only by opcode names?

This is the most likely place where a quantum-arithmetic specialist will push
after the lookup/QROAM fixes.

Required hardening:

- Replace arithmetic block count formulas with a primitive circuit builder.
- Generate the non-Clifford count by walking the generated circuit.
- Generate measurement and feed-forward dependencies in the same IR.
- Keep formulas only as derived explanatory summaries.
- Add a modular-arithmetic certificate per field opcode: inputs, outputs,
  reduction method, ancilla policy, cleanup method, and exact primitive count.
- Add small-prime exhaustive lowered-circuit tests for the arithmetic kernels
  themselves, not just the high-level point-add leaf.

### 4. QROAM standardness is a model assertion, not an imported verified primitive

The selected `K = 1` row avoids the previous QROAMClean junk-register mismatch,
but the repo still encodes QROAM cost formulas itself.

The current claim relies on:

- `domain_size = 32768`
- `field_bits = 256`
- `block_size = 1`
- per coordinate stream non-Clifford: `32768 + 32768 = 65536`
- workspace: `256` target bits plus zero junk bits

The formula is now internally consistent. The remaining trust point is that the
coordinate stream primitive, its target lifetime, its measured cleanup, and its
interaction with the arithmetic consumer are not imported from a formally
verified QROM/QROAM implementation.

Required hardening:

- Add a standalone QROAM primitive IR with selection bits, table entries,
  target register, measurement cleanup, and optional junk registers.
- Instantiate it for every coordinate stream.
- Verify the cost/workspace by traversing that QROAM IR, not by formula.
- Optionally cross-check against a Qualtran-generated QROM/QROAM decomposition
  for the same parameters.

### 5. Boundary no-op semantics are trusted at the system boundary

The current leaf uses `lookup_infinity_policy = boundary_noop`. The hot leaf is
executed for nonzero lookup entries; the boundary keeps the accumulator unchanged
when lookup is infinity.

The repo tests this edge case, but a critic can still ask whether the full raw
oracle schedule actually applies the boundary no-op in exactly the same place
and under exactly the same predicate as the counted leaf family.

Required hardening:

- Make boundary no-op an explicit node in the same full-oracle IR that is used
  for resource counting and ZKP execution.
- Include the boundary no-op control flow in the proof guest, not only in the
  prepared leaf execution model.

### 6. The semiclassical QFT phase shell is counted at a high abstraction level

The qubit improvement depends on `live_phase_bits = 1`. The repo has a
semiclassical-QFT phase-shell artifact and checks its counts, but it does not
ship a fully integrated period-finding circuit with all classical feedback,
latency constraints, and scheduling effects.

This matters because Google's resource lines are for Shor's algorithm circuits,
while this repo's strongest exact layer is a raw-32 oracle plus a phase-shell
family.

Required hardening:

- Build an integrated Shor/control-shell IR that includes the semiclassical
  inverse-QFT measurements and feed-forward.
- Derive phase qubit liveness, measurement count, and depth from that IR.
- State separately what is counted as logical qubits, logical time, rotations,
  and classical feed-forward memory.

### 7. The proof proves an 8-case public corpus, not a 9024-case hidden corpus

The checked public values say:

- `case_count = 8`
- `passed_case_count = 8`

Google's whitepaper appendix states that their proof uses `9024` random inputs
chosen by a Fiat-Shamir process, and that the SP1 guest simulates the circuit on
those 9024 cases. This is a major confidence gap.

The repo has larger deterministic replay tests outside the proof, but those are
not the same as a Groth16 proof over a 9024-case corpus.

Required hardening:

- Produce checked compressed and Groth16 proofs for a much larger corpus,
  ideally `9024` cases for direct comparability.
- Make proof-corpus size explicit in every public comparison table.
- Never phrase `9024-case replay` as equivalent to `9024-case proof`.

### 8. The proof is public-case and deterministic, not hidden-circuit Fiat-Shamir

The repo's ZKP binds public JSON documents and public deterministic cases. This
is better for auditability, but worse if the goal is to match Google's
responsible-disclosure confidence model.

Google's public description says their SP1 guest hashes a private circuit,
derives test inputs from that secret circuit hash stream, simulates the hidden
kickmix circuit, and attests resource bounds without publishing the circuit.
The repo instead publishes the artifact family and proves consistency with a
small public corpus.

A reviewer can reasonably say these are different security statements:

- Google: "I know a hidden circuit under this hash, and I ran many
  Fiat-Shamir-derived tests inside SP1."
- Repo: "These public artifacts and formulas agree, and this public leaf passes
  these public cases inside SP1."

Required hardening:

- Decide whether the repo wants a public-audit proof or a Google-style
  hidden-circuit proof.
- If public-audit proof: stop claiming same confidence model as Google and lean
  into reproducibility.
- If Google-style proof: make the proof input a committed circuit object, derive
  challenge cases from that object, and prove many challenge executions.

### 9. The current proof does not execute the resource-counted lookup or arithmetic lowerings

The SP1 guest executes high-level field semantics:

- `FieldMul` is `(&left * &right) % modulus`.
- `FieldMulLookupX/Y/Sum` multiply by the decoded affine lookup coordinate or
  coordinate sum.
- `CompleteA0AllStreamedTail` directly computes the algebraic intermediate
  values `h`, `a`, `zx`, `c`, `i`, `k`, `l`, `yz`, `e`, `f`, `m`, `n`, then
  writes projective outputs.

It does not execute:

- the generated arithmetic primitive operation list from
  `arithmetic_lowerings.json`;
- the generated QROAM coordinate-stream primitive;
- the generated liveness/owner ledger;
- the FT IR leaf sigma;
- the full raw-32 oracle.

The proof therefore checks:

> The prepared macro-level point-add program produces correct outputs on the
> prepared case corpus, and the prepared family summary's formulas reconstruct
> the claimed numbers.

It does not check:

> The concrete primitive circuit counted by `arithmetic_lowerings.json`,
> `generated_block_inventories.json`, `logical_resource_ledger.json`, and
> `standard_qrom_lookup_assessment.json` implements the same point-add program
> with the claimed peak liveness.

This distinction is subtle and important. The repo's non-ZKP verification layer
tries to bridge the gap, but an external verifier of only the Groth16 proof does
not get that bridge.

Required hardening:

- Put a compact resource certificate into the ZKP input and have the guest walk
  it.
- Or split the public statement into two proofs:
  - semantic proof over point-add cases;
  - resource proof over primitive/liveness IR.
- Bind both proofs to the same circuit digest.

### 10. The compressed proof fixture is not self-contained

Reviewed-state issue:

The checked compressed fixture JSON had `proof: null`; the actual compressed
proof was stored in
`compiler_verification_project/artifacts/zkp_attestation_proof_compressed.bin`.
The Groth16 fixture embeds a short hex proof string, while compressed proof
verification relies on the sidecar binary.

Current remediation:

Every checked fixture now carries explicit sidecar metadata:

- `proof_path`
- `proof_sha256`
- `proof_size_bytes`
- `verifier_key_path`
- `verifier_key_sha256`
- `verifier_key_size_bytes`

`tests/test_zkp_attestation_input.py` verifies those fixture fields against the
checked binary proof bundles and checked Groth16 verifier key.

This is not a mathematical bug. The binary proof verified locally. But it is a
release-packaging weakness:

- a reviewer opening only the JSON fixture cannot verify the compressed proof;
- the fixture does not carry the binary proof's digest and byte length;
- the manifest lists files, but the fixture does not cryptographically point to
  its proof binary.

Required hardening:

- Keep proof and verifier-key sidecar metadata in every fixture and keep tests
  verifying the metadata against checked binary files.

## Hardcoded Numbers And Computations

This section lists major numbers that are still encoded directly in source,
tests, or formulas instead of being derived from one flat circuit engine.

### Public baseline constants

Reviewed-state issue:

- `scripts/verify_all.py` contained `1200`, `90_000_000`, `1450`,
  `70_000_000`.
- `compiler_verification_project/src/project.py` and generated artifacts
  carried the same Google baseline.

Current remediation:

- `data/public_google_baseline.json` is the versioned baseline source.
- `src/baselines.py`, `compiler_verification_project/src/project.py`,
  `src/derived_resources.py`, `scripts/verify_all.py`, and the relevant tests
  import that source instead of restating the numbers.
- `compiler_verification_project/artifacts/public_google_baseline_source.json`
  mirrors the source artifact, and integrity tests require it to match
  `family_frontier.json`.

Risk:

- Drift if the cited baseline changes or if the repo starts comparing against a
  different Google line.

Required hardening:

- Keep the external baseline in the versioned baseline source artifact and make
  generated docs/tests consume it through the shared loader or mirrored checked
  artifact.

### Headline numbers in tests

- `tests/test_zkp_attestation_input.py` asserts `32_879_331` and `1_044`.

Risk:

- This catches accidental drift, but it also hardcodes the answer in a test
  rather than checking only derivation and thresholds.

Required hardening:

- Keep a golden headline test, but also add a derivation-only test that fails if
  any number cannot be traced back to primitive operations and liveness.

### ZKP default corpus size

- `DEFAULT_CASE_COUNT = 8` in `compiler_verification_project/src/zkp_attestation.py`.

Risk:

- The proof defaults to a corpus that is much smaller than Google's disclosed
  proof corpus.

Required hardening:

- Move proof-corpus profiles into config:
  - `smoke = 8`
  - `google_comparable = 9024`
  - `release = selected profile`
- Make public release proofs fail if the selected profile is `smoke`.

### Register list in the proof compiler

The proof compiler starts with:

`['Q.X', 'Q.Y', 'Q.Z', 'k', 'lookup_x', 'lookup_y', 'lookup_meta', 'qx', 'qy', 'qz']`

Risk:

- This is a bespoke register universe for the SP1 guest, not derived from the
  same liveness/resource engine.

Required hardening:

- Generate proof register IDs from the same IR that drives liveness and
  resource accounting.
- Fail if the proof guest sees a register that has no resource owner.

### Field size and curve constants

- Many paths assume `256` field bits, `SECP_P`, `SECP_N`, `SECP_B = 7`,
  `3b = 21`, window width `8`, raw window bits `16`, and folded domain `32768`.

Risk:

- The repo is secp256k1-specific, so this is acceptable, but reviewers will not
  treat it as a generic compiler unless constants are centrally typed and
  propagated.

Required hardening:

- Put all curve, window, table, and field-width parameters in one immutable
  typed parameter object.
- Require every artifact to include the parameter digest.

### QROAM sweep range

- `resource_ledger.py` sweeps candidate block sizes `1..64`.

Risk:

- This is enough for the current argument, but it is not a proof that no better
  QROAM point exists outside the searched range or under another standard
  QROM/QROAM construction.

Required hardening:

- Prove the sweep range analytically for the selected formula.
- Add external QROM/QROAM implementations as cross-checks.

## Circularity And Single-Engine Gaps

The current repo has many consistency checks. That is good. But several checks
compare artifacts to generators that share the same assumptions.

Examples:

- `arithmetic_lowerings_match_generator` proves the artifact equals
  `arithmetic_lowering_library(...)`.
- `frontier_family_rows_reconstruct_from_components` proves the frontier equals
  the same generated component model.
- `logical_resource_ledger` proves selected family fields and resource artifact
  fields agree.
- mutation tests prove that changing a generated artifact is detected, but not
  that the generator's model is physically complete.
- ZKP tests prove checked fixtures/public values match the default prepared
  input, but the active guest does not recompute the full sidecar digests.
- arithmetic tests reconstruct primitive counts from operation lists or
  operation generators, but the operation entries are count tokens such as
  `['ccx', bit_index]`, not a reversible circuit with typed wires and
  dependencies.

This is not enough to convince a hostile reviewer that all resource classes are
derived from a single executable circuit.

Must-have refactoring:

1. Define one typed IR for:
   - registers and bit widths
   - primitive gates
   - measurements
   - classical feed-forward
   - lookup/QROAM primitives
   - macro expansion boundaries
   - ownership/liveness annotations
2. Make all headline artifacts derived from this IR:
   - semantic execution
   - non-Clifford count
   - measurement count
   - phase operations
   - peak live qubits
   - owner ledger
   - ZKP guest input
3. Make formulas secondary generated views, never the primary source.
4. Make the ZKP guest consume the same IR digest and either:
   - execute the IR directly, or
   - execute a formally generated guest program with a checked compiler proof.

## Evidence-Backed Deep Findings

### ZK-1: Prepared proof path can pass through arbitrary sidecar hash labels

Evidence:

- `compiler_verification_project/zkp_attestation/program/src/main.rs` imports
  `run_prepared_attestation` and reads `PreparedAttestationInput`.
- In `run_prepared_attestation`, lines `2492-2622`, no call to
  `semantic_payload_sha256` appears.
- Public values are constructed by copying hash strings from the input at lines
  `2614-2617`.
- The full-document path does recompute hashes at lines `2335-2359`, but that
  is not the active SP1 entrypoint.

Impact:

- A standalone verifier of the proof/public values sees hash-looking public
  values, but the proof does not prove those hashes identify the checked
  sidecars.
- The repo's release process currently supplies the missing binding.

Minimum fix:

- Add hash recomputation to the prepared path or change public values to commit
  to the prepared input itself.

Best fix:

- Make the guest verify a derivation relation:
  `full sidecars -> prepared leaf/cases/family summary -> public values`.

### ZK-2: The SP1 guest does not execute QROAM or primitive arithmetic

Evidence:

- `execute_leaf` uses BigUint field operations with `% modulus`.
- `CompleteA0AllStreamedTail` is one Rust match arm that computes algebraic
  temporaries directly.
- `arithmetic_lowerings.json` and QROAM cost artifacts are not inputs to the
  guest execution loop.

Impact:

- The proof does not rule out a mismatch between the semantic macro and the
  counted primitive lowering.
- This is the main reason the proof is not Google-equivalent resource
  confidence.

Minimum fix:

- Include a resource certificate digest and verify it inside SP1.

Best fix:

- Execute the same lowered IR that is counted.

### RES-1: Arithmetic primitive operations are count tokens, not a circuit graph

Evidence:

- `materialize_arithmetic_primitive_operations` expands `repeated_gate` and
  `repeated_gate_with_measurement` into lists of labels.
- `_ladder_operations` appends `['ccx', bit_index]` and optionally
  `['measurement', bit_index]`.
- `_field_mul_partial_product_operations` appends `['ccx', left_bit, right_bit]`.

Impact:

- There is no typed wire graph, no reversible dependency structure, no explicit
  controls/targets, no uncompute relation, and no global liveness.
- Counts may be right for the intended model, but the artifact is not a
  primitive circuit in the sense most external reviewers will expect.

Minimum fix:

- Rename artifacts honestly as primitive-count inventories, not primitive
  circuits.

Best fix:

- Replace operation labels with a typed circuit DAG.

### RES-2: Modular reduction cost is not visibly proven

Evidence:

- The SP1/Rust semantics uses `% modulus` for field operations.
- The arithmetic lowering uses n-bit carry ladders and schoolbook-product
  formulas.
- The current report artifacts do not expose a full modular reduction schedule
  for secp256k1's prime in each field operation.

Impact:

- A reviewer can object that the counted arithmetic is an arithmetic-kernel
  model, not a complete field-arithmetic circuit.
- This may be a larger concern than QROAM after the QROAM model fix.

Minimum fix:

- Add a document per opcode explaining how modular reduction is represented and
  counted.

Best fix:

- Generate and test the modular arithmetic circuit itself.

### RES-3: QROAM K=1 is consistent but not independently synthesized

Evidence:

- `qroam_clean_stream_cost` computes the QROAM formula directly.
- `logical_resource_ledger.py` then reuses that formula to produce the sweep.
- Integrity checks compare artifacts to the same formula.

Impact:

- The previous mixed-model bug is fixed for `K = 1`, but the repo still relies
  on formula-level QROAM rather than a QROAM circuit/liveness generator.

Minimum fix:

- Cross-check the formula against an external library for all selected rows.

Best fix:

- Generate the QROAM primitive IR locally and count it with the same liveness
  engine as the arithmetic.

### REL-1: Release artifact packaging is not yet reviewer-proof

Evidence:

- `zkp_attestation_fixture_compressed.json` has `proof: null`.
- The actual compressed proof is in a binary file.
- GitHub warned about large historical blobs during push.

Impact:

- Reviewers can verify with the right command, but the artifact package is not
  self-describing enough for high-trust external circulation.

Minimum fix:

- Put proof binary digests and verifier-key digests in the fixture.

Best fix:

- Ship a single release manifest with command transcript, binary digests,
  verifier-key digest, input digest, SP1 version, Rust toolchain digest, and
  container digest.

## Differences Versus Google's ZKP Confidence Model

Sources used for this comparison:

- Google blog, "Safeguarding cryptocurrency by disclosing quantum vulnerabilities responsibly", March 31, 2026:
  https://research.google/blog/safeguarding-cryptocurrency-by-disclosing-quantum-vulnerabilities-responsibly/
- Google whitepaper PDF:
  https://quantumai.google/static/site-assets/downloads/cryptocurrency-whitepaper.pdf

Deep-dive summary:

Google's public description says its SP1 guest receives or reconstructs a
committed circuit, derives fuzz inputs from the secret circuit hash stream,
simulates the circuit, records non-Clifford use over the test runs, and asserts
resource bounds. The repo's current SP1 guest receives a prepared high-level
leaf, a prepared public case corpus, and prepared family/claim summaries; it
then checks formula consistency and case correctness. These are not the same
statement.

### Difference 1: proof corpus size

Google's appendix describes `9024` Fiat-Shamir-derived fuzz inputs inside the
SP1 proof. The repo's checked public values currently prove `8 / 8`.

Expected objection:

> Your proof is a smoke proof. Google's proof is a large fuzz proof.

Response:

- Correct. The repo has larger non-ZKP replay tests, but the shipped Groth16
  public values prove only 8 cases.

Deeper consequence:

- The proof's statistical confidence against semantic bugs is dominated by a
  tiny corpus.
- The repo's stronger deterministic replay suite is transparent and useful, but
  it is not succinctly attested to a third party through the checked Groth16
  public values.
- Any public comparison must have separate rows for `proof_case_count` and
  `repo_replay_case_count`.

### Difference 2: hidden circuit versus public artifacts

Google's proof is designed to avoid publishing attack details. The repo's proof
binds public artifacts and public deterministic cases.

Expected objection:

> This is not the same disclosure model. You made the circuit public and proved
> a different kind of statement.

Response:

- Correct. The repo is stronger for public auditability and weaker for matching
  Google's hidden-circuit responsible-disclosure proof shape.

### Difference 3: approximate-correctness fuzzing versus exact-family semantics

Google explicitly frames the proof as approximate correctness via fuzz testing.
The repo claims exact arithmetic/semantic layers for named families, but the
ZKP itself only checks a small case corpus and formula reconstruction.

Expected objection:

> Your repo has stronger exactness language, but the actual SNARK checks fewer
> cases than Google's approximate proof.

Response:

- Correct. Exactness is supported by public repo tests and artifacts, not by a
  9024-case Groth16 proof.

### Difference 4: kickmix simulator versus repository macro simulator

Google describes a kickmix circuit simulator inside SP1. The repo's SP1 guest
executes a compiled point-add leaf contract with custom macro opcodes such as
`complete_a0_all_streamed_tail`.

Expected objection:

> Google's proof simulates its circuit class. Your proof simulates your
> abstraction contract.

Response:

- Correct. The repo must either flatten the macro into the same circuit class
  it claims, or be explicit that the proof is at the compiler-family boundary.

### Difference 5: resource assertion granularity

Google's public appendix says the guest commits the circuit hash and demanded
resource counts and asserts the private circuit satisfies those bounds. The
repo's guest reconstructs resource formulas from selected family summaries.

Expected objection:

> Your resource proof is a formula consistency check, not a count over the
> executed circuit.

Response:

- Partly correct. The repo has generated inventories and liveness artifacts, but
  the ZKP guest itself does not derive the headline counts by walking a flat
  primitive circuit.

Deeper consequence:

- If a bug exists in `arithmetic_lowering.py` or `resource_ledger.py`, the
  current ZKP can still verify as long as the prepared family summary and formula
  are internally consistent.
- The proof is therefore a claim-consistency and semantic-sample proof, not a
  resource-synthesis proof.

### Difference 7: sidecar hash binding is outside the active proof

The repo's public values include:

- `claim_sha256`
- `leaf_sha256`
- `family_sha256`
- `case_corpus_sha256`

But under the active prepared-input path, those hashes are not recomputed from
full documents inside the guest. They are labels supplied in the prepared input.

Expected objection:

> Your public values look like document commitments, but the active ZKP does not
> prove those commitments correspond to the checked JSON sidecars.

Response:

- Correct for the current prepared-input proof. The repo build/tests check this
  outside the proof. To claim a cryptographic artifact bind, the guest must
  recompute those hashes or publish the prepared input hash as the actual
  commitment.

### Difference 8: verifier key and reproducibility story

The repo ships checked compressed and Groth16 proof bundles and a verifier key.
That is good. The remaining gap is that the proof is tied to a dev/repo
attestation setup, not a public external verifier package with independent
build instructions and reproducible trusted-setup provenance.

Expected objection:

> I can verify your checked bundle, but I cannot easily audit how the verifier
> key was generated and whether it corresponds to the intended release circuit.

Response:

- The repo has local scripts and tests, but the release should include a
  standalone verifier package, key provenance, command transcript, and a
  reproducible build container.

## Historical Repo Errors That Should Shape The Review

These are not merely embarrassing old bugs. They are evidence of error classes
that must be engineered out.

### Error class 1: free interface wires

Earlier attempts treated lookup coordinate lanes as if they could be borrowed
without being counted. The current result fixes that for `lookup_x/y`, but this
class can recur for any macro input/output, QROAM target, junk register, phase
bit, or scratch lane.

Permanent fix:

- Every wire must have exactly one owner.
- Every owner must have numeric capacity.
- Capacity must be derived from the executable IR liveness, not prose or
  manually selected tracked registers.

### Error class 2: fake table-select cost

Earlier lookup lowering effectively treated a 32768-entry lookup as independent
address-bit chunks. That undercounted arbitrary table selection.

Permanent fix:

- Ban lookup models unless the lowering artifact explicitly materializes a
  standard QROM/QROAM primitive or imports a checked external primitive.
- Test arbitrary random table contents, not only structured curve tables.

### Error class 3: mixed QROAM gate/workspace models

An earlier QROAM result used full-coordinate QROAM gate amortization while
keeping one-bit-latch workspace. The current `K = 1` row avoids that, but the
class is dangerous.

Permanent fix:

- One QROAM parameter object must drive both gate count and workspace.
- The engine must reject any artifact where `block_size`, target bits, and junk
  registers are not shared by both cost and liveness.

### Error class 4: green proofs over the wrong semantic boundary

Previous proof bundles could verify while binding a family whose new opcode was
not semantically covered at the same boundary.

Permanent fix:

- Any opcode used in a counted headline must be:
  - executable by the semantic interpreter
  - covered by independent equivalence tests
  - supported by the ZKP guest
  - lowered into resource inventory
  - included in liveness
  - included in mutation tests
- The release pipeline should fail if any headline opcode is missing from any
  of those layers.

### Error class 5: generated artifacts too large or too opaque

The current commit had to compact `arithmetic_lowerings.json` because the full
pretty-printed expanded primitive operation artifact exceeded practical GitHub
review size.

Permanent fix:

- Store large generated traces in a deterministic compressed format with a small
  index and digest tree.
- Keep a human-readable summary plus a separately verifiable machine archive.

## Expected External Objections

### "This is AI-generated. Why should I trust it?"

This is the first objection, and it is fair. The top-level README already says
the repo was created with ChatGPT and that the human maintainer cannot deeply
audit quantum computing claims.

Best response:

- Do not ask for trust.
- Provide deterministic rebuild commands, independent verifier scripts, small
  extracted circuits, and adversarial tests.
- Invite external quantum-circuit reviewers to attack the IR and liveness model.

### "You did not publish a full primitive-gate Shor circuit."

Correct. The repo publishes a standard-QROM compiler-family boundary, not a
Clifford-complete full-Shor netlist.

Best response:

- Keep this boundary in every headline.
- Do not use wording that implies a flattened full algorithm circuit.

### "The 3-slot macro is where the magic is hidden."

This is the strongest technical objection. The tail macro is counted, but peak
qubits are not derived from a flattened internal schedule.

Best response:

- Build the flat macro IR.
- Show internal temporaries are sequentially reused or counted.
- Make a liveness heatmap for the macro.

### "Your ZKP proves only 8 cases."

Correct.

Best response:

- Generate a release proof over a larger corpus.
- At minimum, add a `9024-case` compressed proof and document whether Groth16 is
  feasible locally.

### "Your resource proof is circular."

Partly correct. It is internally cross-checked, but still generator-defined.

Best response:

- Move to one primitive IR engine.
- Make resource totals emerge from walking the IR.
- Keep current formulas only as redundancy checks.

### "You compare against Google numbers but not Google's proof boundary."

Correct. The public numeric comparison uses Google's rounded public resource
lines, while the proof boundary is different.

Best response:

- Maintain two tables:
  - resource-number comparison
  - proof-confidence comparison
- Do not collapse them into one "we beat Google" sentence.

### "QROAM K=1 is space-friendly but gate-heavy; are you cherry-picking?"

The current goal is below `1200` qubits and below `40M` non-Clifford, so `K = 1`
is a legitimate point in the selected model. But reviewers can ask for a full
Pareto frontier.

Best response:

- Publish the QROAM sweep as a first-class chart.
- Show that the selected row is the lowest-qubit row under Google's low-gate
  non-Clifford line.
- State that the `<24M` target is not met under strict standard-QROAM below
  `1700` qubits.

### "The non-Clifford count ignores Clifford depth and routing."

Correct. The repo mostly counts non-Clifford operations, measurements, logical
qubits, and some phase-shell metrics.

Best response:

- Do not imply runtime or physical-qubit superiority without a physical
  estimator layer.
- Add Clifford counts, depth, and routing constraints if making runtime claims.

### "The physical estimates are not central evidence."

Correct. Azure and Cain-transfer artifacts are downstream interpretation, not
the core proof of the logical frontier.

Best response:

- Keep physical estimates secondary.
- Do not use them to validate the logical circuit.

## Must-Have Refactor Roadmap

### P0: Single circuit/resource engine

Build one typed IR and make it the only source for:

- semantic execution
- primitive gate count
- measurement count
- QROAM target/junk wires
- macro-expanded scratch wires
- liveness and owner ledger
- proof guest input

Exit criterion:

- Changing a macro expansion changes liveness, resource counts, artifacts, and
  ZKP input through the same engine.

### P0: Fix ZKP document binding

The active SP1 guest must prove the same document bindings that public values
appear to claim.

Implementation options:

- Full sidecar mode: include full claim, leaf, family, and case corpus documents
  in the SP1 input and recompute semantic hashes inside the guest.
- Prepared-source mode: make `zkp_attestation_input.json` the single committed
  source of truth, publish its hash, and remove sidecar hash fields from public
  values unless they are recomputed.
- Derivation mode: include both full documents and prepared forms, then verify
  inside the guest that the prepared forms are derived from full documents.

Exit criterion:

- Mutating any public hash label without mutating the corresponding document
  makes the SP1 guest fail.
- Mutating `prepared_leaf` while preserving `leaf_sha256` makes the SP1 guest
  fail.
- Mutating `prepared_case_corpus` while preserving `case_corpus_sha256` makes
  the SP1 guest fail.

### P0: Flatten the tail macro

Expand `complete_a0_all_streamed_tail` into a scheduled IR.

Exit criterion:

- Peak live qubits remain below `1200` after internal scratch is included, or
  the headline is revised.

### P0: Prove modular arithmetic lowerings, not only point-add semantics

Generate circuits for:

- modular addition over secp256k1's prime;
- modular subtraction;
- modular multiplication;
- multiplication by `21`;
- table-controlled multiplication by x, y, and x+y streams;
- all macro-internal arithmetic used by `complete_a0_all_streamed_tail`.

Exit criterion:

- The generated modular arithmetic circuits are executable on reduced-width
  fields and exhaustively tested.
- The 256-bit versions produce the existing count as a derived result.
- The same circuit representation feeds resource counting and ZKP execution.

### P0: ZKP over release-size corpus

Produce a proof over a corpus comparable to Google's disclosed 9024 cases, or
stop calling the current ZKP Google-like without a prominent qualifier.

Exit criterion:

- Public values show `case_count = 9024` and `passed_case_count = 9024`, or docs
  explicitly label the checked proof as an 8-case smoke attestation.

### P0: ZKP resource derivation from IR

The SP1 guest should not only reconstruct formulas from family summaries. It
should parse or receive a committed resource IR and derive the headline totals.

Exit criterion:

- The guest computes non-Clifford and qubit totals from the committed circuit
  representation or from a separately proven resource certificate.

### P1: External QROM/QROAM cross-check

Add a cross-check against an external QROM/QROAM implementation or a small
formally specified QROAM primitive.

Exit criterion:

- For selected parameters, internal QROAM cost/workspace matches the external
  primitive, and mismatch fails CI.

### P1: Baseline source package

Move Google baseline numbers and citations into a versioned source artifact.

Exit criterion:

- Docs and tests import baseline data rather than repeating constants.

### P1: Reproducible proof environment

Package proof generation and verification in a container or Nix/uv lock.

Exit criterion:

- A fresh machine can verify compressed and Groth16 proof bundles and reproduce
  public values with one documented command sequence.

### P1: Digest tree for large artifacts

Replace huge flat JSON traces with deterministic compressed archives plus
Merkle/digest indexes.

Exit criterion:

- Git diffs are reviewable, artifacts remain machine-verifiable, and no single
  checked blob approaches GitHub warning limits.

### P2: Better mutation testing

Current mutation tests catch many artifact edits. Add model-level mutations:

- remove a macro scratch wire
- change QROAM block size in only cost or only workspace
- remove boundary no-op from one layer
- change proof corpus size without changing public values
- alter field width in one layer

Exit criterion:

- Each class fails at the earliest relevant layer and in the full release
  pipeline.

## Recommended Public Wording

Avoid:

> We crushed Google's result.

Use:

> Under the repository's checked standard-QROM compiler-family boundary, the
> current artifacts and checked SP1 compressed/Groth16 proofs bind a
> `34,736,076` non-Clifford / `1,044` logical-qubit result. This improves the
> cited public Google 2026 resource lines numerically, but the proof boundary is
> not identical to Google's hidden-circuit 9024-case SP1/Groth16 attestation and
> the repository does not yet ship a Clifford-complete flattened full-Shor
> netlist.

## Bottom Line

The result is worth serious attention. It is not obviously fake, and the latest
resource model fixes the previous lookup/QROAM accounting failures. But the
credible external claim is still narrower than the most excited internal
phrasing:

- strong: checked standard-QROM compiler-family boundary at `34,736,076 / 1,044`
- not yet strong enough: Google-equivalent proof confidence
- not yet strong enough: fully flattened primitive-gate Shor circuit
- most urgent engineering gap: replace model consistency with one flat
  circuit/liveness/resource engine

## Post-Review Remediation Status

This report reviewed commit `4d9fefed41ca0f6b5cf6528ce8366065fc6d557a`.
Later hardening on the same branch changes the status of some findings, but it
does not erase the central architectural criticism.

Fixed after review:

- `ZK-1`: the active SP1 input moved to schema
  `compiler-project-zkp-attestation-input-v5`. The guest now receives the full
  committed claim, leaf, family, case-corpus, and resource-certificate
  documents; recomputes their canonical SHA-256 digests; derives the prepared
  claim summary, family summary, leaf program, and case corpus from those
  documents; and publishes the recomputed hashes as public values.
- The public values now include `resource_certificate_sha256`, binding the
  selected frontier, executable leaf liveness summary, QROAM workspace/cost
  checks, arithmetic lowering inventory, selected-family FT-IR leaf sigma, and
  global resource owner ledger to the proof input.
- Negative guest tests were added for stale claim labels, mutated committed
  claim payloads, mutated prepared leaves, mutated prepared case corpora, and
  mutated resource leaf-sigma primitive counts.
- `RES-2`: the central `field_mul` lowering now carries explicit secp256k1
  pseudo-Mersenne reduction stages for `p = 2^256 - 2^32 - 977`, including the
  first fold, second narrow fold, and two canonical subtract-p passes. This
  moved the checked headline from `32,879,331 / 1,044` to
  `34,736,076 / 1,044` rather than leaving prime-field reduction implicit.

Partially mitigated after review:

- `ZK-2` and `RES-3`: the checked
  `resource_liveness_certificate.json` now carries the selected FT-IR
  leaf-sigma rows. The SP1 guest recomputes primitive totals, live-qubit
  totals, phase counts, and the expanded all-streamed-tail contribution from
  those rows before accepting the public values. This is a real resource
  certificate, not only a headline consistency check. The repo now also emits
  `compiler_verification_project/artifacts/materialized_circuit_manifest.json`,
  a selected-family primitive operation-stream manifest whose stream digest
  `a96f690cd1f4f3888f51dad42b80dcdda840ccfccbb900ed34517d9916355208`
  reconstructs `42,038,711` operations, `34,736,076` CCX, and `7,301,612`
  measurements. The manifest now splits that stream into `43` deterministic
  million-operation-or-smaller digest segments with Merkle root
  `5ff61670bb4d1a394cb15b57b3c917687c092083654bb8738e47f2f0f1589188`.
  That manifest is included in the build summary, curated proof manifest,
  resource liveness certificate, and SP1 guest resource-certificate checks.
  This is still a digest/manifest over the stream rather than a checked
  tens-of-millions-row TSV dump.
- `RES-1`: `complete_a0_all_streamed_tail` is no longer only a single opaque
  resource token in the ZKP-bound resource certificate. The certificate contains
  66 primitive leaf-sigma rows for the macro, and the guest verifies that their
  whole-oracle non-Clifford contribution equals the per-leaf macro lowering
  times the 31 leaf calls. Internal live-wire scheduling below those primitive
  rows is still not a bit-addressed wire netlist.
- `ZK-3`: proof binaries are now included in the curated proof manifest, but
  the checked JSON fixtures still intentionally keep the large binary proof
  payloads out-of-line.

Still open:

- The repository ships a checked segmented digest/Merkle manifest of the
  selected primitive operation stream, but not the tens-of-millions-row TSV gate
  list itself.
- The deepest refactor remains mandatory before claiming Google-equivalent
  hidden-circuit confidence: the same source engine should emit the semantic
  leaf, primitive lowering, liveness peak, artifact digests, and ZKP input
  without maintaining parallel prepared and audit views.
