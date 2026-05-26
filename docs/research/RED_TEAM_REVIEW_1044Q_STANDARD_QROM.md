# Red-Team Review: 1044-Qubit Standard-QROM Frontier

Date: 2026-05-14

Reviewed commit: `4d9fefed41ca0f6b5cf6528ce8366065fc6d557a`

Headline under review:

- `32,879,331` non-Clifford
- `1,044` logical qubits
- family: `folded_standard_qroam_streamed_coordinate_v1__streamed_lookup_tail_leaf_v1__semiclassical_qft_v1`

Historical macro/ZKP wrapper reviewed before the guarded replayed-tail promotion:

- `36,957,412` non-Clifford
- `1,199` logical qubits
- family:
  `folded_standard_qroam_reusable_chunked_coordinate_v1__reusable_chunk_tail_leaf_v1__semiclassical_qft_v1`
- no longer selected as the current public headline

Current primary strict replayed-tail headline on this branch:

- `36,973,222` non-Clifford
- `1,968` logical qubits
- formula: `7 * 256 + 173 + 2 + 1`
- selected by `compiler_verification_project/artifacts/strict_replayed_tail_headline.json`
- evidence: `tail_macro_engine.json` fused-output replay passes 110,082
  non-infinity toy boundary pairs, 610 lookup-infinity no-op pairs, generated
  seven-slot owner capacity, and a strict materialized flat-netlist stream
  whose segment hashes include the projected `1,968`-qubit liveness

This document is intentionally adversarial. It is not a release note and not a
claim that the result is false. It records every major place where an external
reviewer still has to trust the repo authors, the abstraction boundary, or a
hand-built accounting layer instead of trusting a single primitive circuit
engine that emits and counts one flat executable object.

## Executive Verdict

The result is strong inside the repository's current boundary, but it is not yet
as confidence-preserving as Google's disclosure boundary.

The reviewed commit's highest-severity issue was in the ZKP binding layer: the
active SP1 program used a prepared-input path that did not recompute public
document hashes from embedded full sidecars inside the guest. The current branch
has remediated that specific binding bug. The active
`run_prepared_attestation` path now carries committed claim, leaf, family,
case-corpus, and resource-certificate documents; recomputes their semantic
SHA-256 digests inside the guest; derives the prepared leaf and case reductions
from those committed documents; and rejects stale digest labels, mutated
committed payloads, mutated prepared reductions, and mutated resource
leaf-sigma rows.

The strongest defensible statement is:

> The repository currently contains a checked standard-QROM compiler-family
> boundary whose primary strict resource headline is the replayed-tail
> `36,973,222 / 1,968` artifact, including a strict materialized flat-netlist
> commitment with the projected `1,968`-qubit liveness in its segment hashes.
> The older `36,957,412 / 1,199` artifact is now only a macro/ZKP wrapper
> reference whose claim/leaf/family/case/resource document hashes are recomputed
> inside the active ZKP guest. The ZKP guest and public values must be rebuilt
> around the strict seven-slot contract before the proof layer can be described
> as binding the primary strict headline.

The weaker `32,879,331 / 1,044` statement is the historical verdict for commit
`4d9fefed41ca0f6b5cf6528ce8366065fc6d557a`. The current branch has since moved
the macro wrapper to `36,957,412 / 1,199` after adding explicit modular-reduction
cost for field multiplication and canonical modular add/sub correction costs,
stronger ZKP resource binding, in-guest committed-document hash binding, and
the reusable-chunk four-slot candidate proof bundle with explicit freshness
checks. The current primary strict presentation then demotes that macro wrapper
and counts the replayed fused-output seven-slot tail instead, giving
`36,973,222 / 1,968`.

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
| ZK-1 | P0 reviewed-state; remediated on current branch | Reviewed SP1 prepared path did not recompute sidecar hashes; current path now recomputes committed claim/leaf/family/case/resource hashes in guest | This used to let public values carry hash labels trusted from the input builder; current tests reject stale digest labels and mutated committed payloads | Keep full committed documents in the guest input and keep negative digest/payload tests |
| ZK-2 | P0 | ZKP executes high-level field/macro semantics, not primitive QROAM/arithmetic lowerings | The proof checks point-add behavior for prepared cases, but not that the resource-counted primitive circuit implements that behavior | Feed the same resource IR into the guest or prove a separate lowering certificate |
| RES-1 | P0 partially mitigated | The public reusable-chunk leaf now traces the counted `qchunk` scratch lane, and the primary headline counts the replayed fused-output seven-slot tail instead of the old four-slot macro tail | The `1,968` qubit result removes the old tail-slot fantasy from the public headline, the ZKP input binds the canonical public engine manifest, local modular streams are bound to public arithmetic engine rows, `modular_execution_trace.json` schedules the tail into modular sub-operations with slot/liveness ownership, `scheduled_modular_primitive_netlist.json` scans the strict public leaf into `1,270,134` primitive rows, and the public engine binds a global splice over the grouped arithmetic+QROAM rows | Make the ZKP guest and exported full physical stream consume that spliced global physical boundary directly |
| RES-2 | P0 partially mitigated | Modular field arithmetic costs are now digest-bound operation streams, but still not a generated modular circuit | Rust semantics applies `% p`; arithmetic lowering counts abstract add/sub/mul kernels whose modular-reduction completeness must still be trusted below the compact operation IR | Generate modular add/sub/mul circuits including reduction and count them |
| RES-3 | P0 materially improved; still below physical-layout FT schedule | The public reusable-chunk resource ledger now has a guest-checked contract engine and a materialized flat primitive stream over counted IR, executable liveness, owner capacity, QROAM target/chunk wires, arithmetic rows, lookup rows, and phase rows | It now catches counted/executable liveness drift, owner-capacity underprovisioning, and missing full-stream materialization, but the deepest arithmetic macro semantics are still certified by generated IR/certificates rather than a routed physical FT schedule | Keep reducing the remaining macro boundary by lowering modular arithmetic certificates into the same flat primitive stream |
| ZK-3 | P1 remediated for out-of-line proof binding | Checked compressed fixture JSON keeps `proof: null` while binary proof is separate | Large compressed proof bytes remain out-of-line, but fixtures now bind proof/verifier-key path, size, digest, and curated proof-manifest records | Keep `proof_status.py` manifest cross-checks and fixture metadata tests in the release gate |
| GOV-1 | P1 partially mitigated | Release-critical constants now have compiler-parameter and constant-provenance artifacts, but older support layers still contain some historical wording and derived summaries | The selected headline/ZKP path has drift checks, but a single flat circuit engine would still be stronger than cross-artifact provenance | Keep importing versioned parameter/provenance artifacts and remove remaining repeated constants opportunistically |

## What Is Actually Strong

- The checked strict headline is internally consistent across:
  - `compiler_verification_project/artifacts/strict_replayed_tail_headline.json`
  - `compiler_verification_project/artifacts/tail_macro_engine.json`
  - `compiler_verification_project/artifacts/reusable_chunk_lowering.json`
- The older macro/ZKP wrapper remains internally consistent across:
  - `compiler_verification_project/artifacts/family_frontier.json`
  - `compiler_verification_project/artifacts/logical_resource_ledger.json`
  - `compiler_verification_project/artifacts/standard_qrom_lookup_assessment.json`
  - `compiler_verification_project/artifacts/zkp_attestation_public_values.json`
  - compressed and Groth16 fixtures/proofs.
- `compiler_verification_project/artifacts/verification_summary.json` currently
  reports exact compiler verification `452/452`: `30/30` semantic cases and
  `422/422` invariant checks.
- `pytest -q` passed at the reviewed state.
- The proof public values bind the selected family, leaf hash, case corpus hash,
  and the final numbers.
- The earlier "free lookup x/y lane" class of error is not present in the
  current headline. The current reusable-chunk resource contract counts `173`
  lookup workspace qubits: `18` folded-control qubits plus a live `155`-qubit
  chunk QROAM target at `K = 1`.
- The earlier `15 independent 2-way chunks` lookup model is no longer the
  selected public model. The selected resource model charges `65,536`
  non-Clifford per 155-bit reusable chunk stream.
- The earlier QROAM block-size inconsistency is not present in the selected row:
  `K = 1` implies no junk registers and a `155`-qubit chunk target, so the QROAM
  gate and workspace formulas agree for the selected public point.

## Critical Trust Assumptions

### 0. The active ZKP sidecar-hash binding bug is remediated

Reviewed-state issue:

The reviewed commit used `run_prepared_attestation` without embedded full
sidecar documents. The guest executed prepared cases and copied public hash
labels, so a verifier of only the Groth16 proof had to trust the repo-side
builder to connect those labels to the checked JSON sidecars.

Current remediation:

The active SP1 program still calls `run_prepared_attestation`, but the prepared
input schema is now `compiler-project-zkp-attestation-input-v5` and carries:

- committed claim document;
- committed streamed leaf document;
- committed selected-family document;
- committed point-add case-corpus document;
- committed resource-liveness certificate document;
- proof-ready prepared leaf and case reductions.

Inside the guest, `run_prepared_attestation` now:

- checks every committed document digest scheme;
- recomputes each semantic SHA-256 digest from the committed payload;
- requires the recomputed digest to equal the public digest label in the input;
- decodes the committed documents;
- derives the claim summary, family summary, prepared case corpus, and prepared
  leaf from those committed documents;
- requires those derived prepared forms to equal the supplied prepared forms;
- validates the resource certificate before publishing public values.

Evidence:

- active entrypoint:
  `compiler_verification_project/zkp_attestation/program/src/main.rs`
- committed-document validation:
  `compiler_verification_project/zkp_attestation/lib/src/lib.rs:3136-3144`
- prepared path document binding:
  `compiler_verification_project/zkp_attestation/lib/src/lib.rs:3486-3544`
- negative tests:
  `compiler_verification_project/zkp_attestation/lib/src/lib.rs:3769-3828`

The old attack shape no longer works: mutating only a public digest label,
mutating only a committed payload, or mutating only a prepared reduction causes
the guest to reject. The checked tests explicitly cover stale claim, leaf,
family, case-corpus, and resource-certificate digests.

Remaining trust boundary:

This fix binds the proof to the committed source documents and prepared
reductions. It does not by itself make the proof a full primitive-gate Shor
circuit proof; the remaining high-severity issues are the resource/lowering
and flat-liveness boundaries below.

### 1. The reusable tail is still partly trusted as a counted liveness boundary

The historical 1044-qubit result depended on replacing a multi-register leaf
body with one macro opcode:

- `complete_a0_all_streamed_tail`
- live arithmetic slots: `qx`, `qy`, `qz`
- peak arithmetic register file: `3 * 256 = 768`

The current public headline no longer uses that three-slot leaf as the public
claim. It uses `complete_a0_reusable_chunk_tail` with four arithmetic slots:
`qx`, `qy`, `qz`, and `qchunk`. The `qchunk` lane is now semantically traced in
the executable leaf and counted live concurrently with the QROAM target. That
closes the named-only/free-scratch version of this issue, but the reusable tail
still relies on compact modular-arithmetic and tail-macro contracts rather than
a single flattened Clifford-complete schedule.

Where trust enters:

- `compiler_verification_project/src/reusable_chunk_tail_candidate.py` defines
  the current executable reusable-chunk leaf and its traced `qchunk` contract.
- `compiler_verification_project/src/arithmetic_lowering.py` assigns the macro
  internal work and cost.
- `compiler_verification_project/src/reusable_chunk_lowering.py` assigns four
  arithmetic slots and derives the public `1,199`-qubit peak.
- `compiler_verification_project/src/integrity.py` checks consistency with those
  same generators.

Required hardening:

- Flatten `complete_a0_reusable_chunk_tail` and the modular field kernels into
  an explicit primitive/lower-level IR with named temporary wires.
- Run liveness on the flattened IR, not on the macro-level executable leaf.
- Prove that any temporary scratch inside the macro is either sequentially
  reused inside an already counted owner or explicitly added to peak live
  qubits.

Current additional diagnostic:

- `compiler_verification_project/artifacts/tail_macro_liveness.json` is now a
  generated pressure test for the macro formula DAG. It records the exact
  `complete_a0_all_streamed_tail` formula dependencies from the executable
  semantic boundary, including `yZ = lookup_y * Z`, and computes a
  single-assignment/no-recompute liveness peak plus a conservative
  non-destructive recomputation pebble search.
- The diagnostic deliberately does not close RES-1. It exposes the remaining
  proof obligation: the naive formula DAG peaks above the counted three
  arithmetic slots, even non-destructive recomputation fails below eight
  live-after field values, and the strict operation-concurrent single-assignment
  fallback schedule generated by `tail_macro_engine.json` requires nine
  field-sized slots. The repository still needs a generated
  destructive/in-place schedule certificate before `3 * 256` can be treated as
  primitive liveness rather than a macro contract.
- `tail_macro_engine.json` also emits a fused-output seven-slot schedule. The
  counted 23-row field stream remains the cost source; the fused stream proves
  that `X3 = K*N - E*C`, `Y3 = N*M + C*L`, and `Z3 = M*E + L*K` can be executed
  without materializing `KN/EC/NM/CL/ME/LK` as six separate live field lanes.
  The fused stream has the same tail non-Clifford total as the expanded stream,
  passes the operand injectivity screen for its chosen overwrites, replays across
  110,082 non-infinity toy boundary pairs, checks 610 lookup-infinity no-op
  boundary pairs, and derives a seven-slot owner-capacity ledger from generated
  slot assignment. The new `fused_output_lowering_contract` rejects the old
  unguarded `Y3` over `N` reuse with a concrete secp256k1 `M == 0` witness and
  exposes the selected zero-lifted in-place `Y3` over `C` field permutation,
  including the counted `L == 0` guard and cost reconstruction. It is now the
  primary strict resource headline, while the ZKP guest/input still needs to be
  kept bound to the canonical public engine manifest and regenerated when the
  checked artifacts change.
- `compiler_verification_project/artifacts/tail_macro_schedule_search.json`
  adds a stricter destructive-schedule search for the current formula DAG. It
  permits computing a formula value and dropping old values whenever the
  remaining live tuple is still injective over the canonical toy accumulator
  domain. Even under that permissive model, the counted three-slot budget finds
  no schedule for any curated toy generator lookup. This is negative evidence
  for the current formula DAG, not a proof against a different formula or a
  concrete permutation-extension implementation.
- `compiler_verification_project/artifacts/tail_macro_reversibility.json` adds
  the matching reversible-boundary check. The macro polynomial is not injective
  over the full raw field-register domain and is also not injective over all
  plain-projective representatives of the subgroup. It is injective over
  canonical subgroup representatives and over fixed-lookup reachable toy orbits.
  The same artifact now exhausts all canonical accumulator-state by lookup-state
  toy boundary pairs across the curated groups: `110,692` total pairs, including
  ordinary addition, doubling, inverse, accumulator-infinity, and lookup-infinity
  no-op cases. Every checked pair matches affine group addition, and every fixed
  lookup acts injectively on the canonical accumulator domain. This substantially
  narrows the semantic/reversible-boundary risk, but it still does not prove the
  missing destructive three-slot primitive schedule. A future three-slot
  implementation must therefore prove either a concrete reversible permutation
  extension or an explicit reachable-subspace encoding.

### 2. The resource ledger is still owner-summed, not circuit-derived

Reviewed-state issue:

The reviewed ledger was much better than previous manual tracked-register
lists, but it still summed named owners:

- arithmetic slot register file: `768`
- control slot register file: `1`
- lookup workspace: `274`
- phase shell live register: `1`
- total: `1044`

Current remediation:

`resource_liveness_certificate.json` now carries a
`derived_owner_capacity` section. It derives each owner requirement from the
source that creates the live quantum obligation:

- arithmetic slot register file: max arithmetic slots over executable leaf
  `per_pc` liveness times `field_bits`;
- control slot register file: max control slots over executable leaf `per_pc`
  liveness;
- lookup workspace: folded-control workspace plus QROAMClean
  target-plus-junk capacity;
- phase shell live register: selected phase-shell lowering
  `live_quantum_bits`.

For the current reusable-chunk public headline,
`reusable_chunk_lowering.json` additionally carries an executable interval
liveness certificate. It recomputes the `1,199`-qubit global peak from the live
wire intervals, proves the `155`-qubit QROAM target and `qchunk` are counted
concurrently, proves no full-coordinate lookup lane is live, and requires every
owner peak to match its numeric capacity. The Rust SP1 guest walks this section
and rejects underprovisioned owner capacity or forged QROAM-target liveness.

The same artifact now includes `resource_contract_engine`, a separately
recomputed contract layer over `counted_resource_ir`, `counted_resource_engine`,
`executable_liveness`, and `owner_capacity`. The contract requires the counted
wire catalog and live intervals to match the executable liveness certificate,
recomputes the global peak and owner peaks, checks that each owner has explicit
numeric capacity for its peak, and is validated by the SP1 guest before the
resource digest is accepted.

Remaining boundary:

This is stronger than owner-summed prose, but it is still not a fully
bit-addressed global schedule over every temporary wire in a complete
primitive-gate Shor circuit. The unresolved part is the same lower boundary as
RES-1/RES-2: internal macro scratch is represented by lowering inventories and
resource owners rather than by a single complete time-indexed netlist.

Where trust enters:

- `compiler_verification_project/src/resource_ledger.py` builds owners from
  selected family fields.
- `compiler_verification_project/artifacts/logical_resource_ledger.json` proves
  internal agreement, not independent extraction from a primitive circuit.

Required hardening still open:

- Keep moving toward one resource engine that consumes a flat scheduled IR and
  computes peak live qubits by interval analysis.
- Keep owner labels as derived outputs of that engine. The reusable-chunk public
  headline now does this for the checked executable-liveness interval boundary;
  the remaining work is pushing the same derivation below the macro/arithmetic
  model boundary.
- Extend the current derived owner-capacity checks down to bit-addressed macro
  scratch intervals when the macro lowering is flattened further.

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

Current hardening narrows, but does not eliminate, this trust boundary. The
repo now emits
`compiler_verification_project/artifacts/arithmetic_operation_ir.json`, a
compact arithmetic operation-stream IR whose block, stage, kernel, and selected
leaf totals are reconstructed from canonical primitive-operation streams and
SHA-256 digests instead of copied totals. The checked
`resource_liveness_certificate.json` embeds the full compact arithmetic IR, and
the SP1 guest recomputes block totals, stage totals, kernel totals, and the
selected leaf arithmetic total before accepting the resource certificate. Guest
tests reject forged arithmetic leaf rows and forged block-level totals even
when the resource-certificate digest is refreshed. This is a useful guard
against another manually summed arithmetic ledger, but it is still not a full
Clifford-complete reversible modular-arithmetic netlist.

Current additional hardening:

- Generated repeated-ladder arithmetic blocks now use bit-index operands rather
  than monotone operation ordinals. The arithmetic operation IR records a
  generator operand contract for every generated block, and
  `arithmetic_operation_ir_checks` plus the SP1 guest reject ladder streams
  whose operand-domain profile no longer matches bit-index semantics. A Rust
  negative test mutates this contract while refreshing the resource digest and
  still fails in the guest.
- The SP1 guest now validates the embedded
  `executable_modular_circuit_ir` and
  `executable_circuit_ir_count_certificate` directly: it reconstructs per-step,
  per-operation, and per-opcode non-Clifford counts from the modular IR and
  rejects forged IR step counts or forged executable-IR count certificates.

Required hardening:

- Replace arithmetic block count formulas with a primitive circuit builder.
- Generate the non-Clifford count by walking the generated circuit.
- Generate measurement and feed-forward dependencies in the same IR.
- Keep formulas only as derived explanatory summaries.
- Add a modular-arithmetic certificate per field opcode: inputs, outputs,
  reduction method, ancilla policy, cleanup method, and exact primitive count.
- Add small-prime exhaustive lowered-circuit tests for the arithmetic kernels
  themselves, not just the high-level point-add leaf.

### 4. QROAM standardness now has an internal generated primitive-count certificate, but not an external implementation import

The selected `K = 1` row avoids the previous QROAMClean junk-register mismatch,
and the current branch no longer relies only on a manually read formula for the
public reusable-chunk stream. It now emits
`compiler_verification_project/artifacts/qroam_primitive_certificate.json`,
emits an independent
`compiler_verification_project/artifacts/qroam_reference_crosscheck.json`,
embeds both payloads into `reusable_chunk_lowering.json`, and makes the SP1
guest validate the embedded certificates before accepting the public resource
digest.

The public reusable-chunk claim relies on:

- `domain_size = 32768`
- `target_bits = 155`
- `block_size = 1`
- per chunk stream non-Clifford: `32768 + 32768 = 65536`
- workspace: `155` target bits plus zero junk bits

The certificate traverses deterministic compute and measured-uncompute
unary-iteration segments and checks those traversed counts against the
QROAMClean `K = 1` parameter object. The separate reference cross-check does
not import the production `resource_ledger.qroam_clean_stream_cost` helper; it
recomputes the QROAMClean gate/workspace equations, keeps the `155`-bit
reusable chunk stream separate from the `256`-bit full-field ledger sweep, and
includes reduced-domain table-select/uncompute semantic cases. This is stronger
than a single local formula, and it directly guards the previous
gate/workspace-width mix-up, but still not a Clifford-complete QROAM netlist and
not an imported third-party formal implementation. The remaining trust point is
therefore narrower: reviewers still have to accept the locally specified
`qroamclean_k1_unary_iteration_step` primitive model, or ask for an external
Qualtran/QROM synthesis cross-check.

Required hardening:

- Extend the current primitive-count certificate into a full QROAM primitive IR
  with selection bits, table entries, target register, measurement cleanup, and
  optional junk registers.
- Instantiate or reference the certificate for every coordinate stream.
- Keep verifying the cost/workspace by traversing the generated certificate,
  not by comparing two hand-written constants.
- Add an external Qualtran-generated QROM/QROAM decomposition cross-check for
  the same parameters.

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

The repo now also ships
`compiler_verification_project/artifacts/release_corpus_preflight.json`, a fast
semantic preflight over the Google-comparable `9024`-case public release
profile. It executes the same point-add leaf contract outside the proof,
records forced edge-category counts, and binds the full case stream by rolling
canonical-JSON SHA-256. That is useful release-size evidence, but it is still
not the same as a compressed or Groth16 proof over a 9024-case corpus.

Required hardening:

- Produce checked compressed and Groth16 proofs for a much larger corpus,
  ideally `9024` cases for direct comparability.
- Make proof-corpus size explicit in every public comparison table.
- Never phrase `9024-case replay` as equivalent to `9024-case proof`.
- Keep the 9024-case preflight in the fast gate so corpus drift is caught before
  spending prover time.

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
`compiler_verification_project/scripts/proof_status.py` also reports
`input_binding_status` and `stale_reasons` per proof system, so stale checked
fixtures cannot look fresh merely because the sidecar proof/key digests match.
The current stale fixtures explicitly declare null input metadata and correctly
report `fixture_declares_no_input_metadata` until a real proof rebuild emits
proof-time input hashes.
The proof-status engine is now shared code in
`compiler_verification_project/src/proof_status_report.py`, and
`compiler_verification_project/artifacts/proof_publication_status.json` records
the same verdict as a checked artifact. Its `pass` flag means the publication
status was derived consistently; its `publication_ready` flag remains false
while core/compressed/Groth16 fixtures are stale.

This is not a mathematical bug. The binary proof verified locally. But it is a
release-packaging weakness:

- a reviewer opening only the JSON fixture cannot verify the compressed proof;
- the fixture does not carry the binary proof's digest and byte length;
- the manifest lists files, but the fixture does not cryptographically point to
  its proof binary.

Required hardening:

- Keep proof and verifier-key sidecar metadata in every fixture and keep tests
  verifying the metadata against checked binary files.
- Do not backfill stale fixtures with the current input hash. A fixture may
  claim `matches_current_input` only after the proof was actually generated or
  verified against that input.

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

Reviewed-state issue:

- `DEFAULT_CASE_COUNT = 8` lived directly in
  `compiler_verification_project/src/zkp_attestation.py`.

Risk:

- The proof defaults to a corpus that is much smaller than Google's disclosed
  proof corpus.

Current remediation:

- `compiler_verification_project/artifacts/proof_corpus_profiles.json` now
  records the selected public profile as `smoke_public_8` and the release target
  as `google_comparable_9024`.
- `DEFAULT_CASE_COUNT` is derived from that profile source rather than being a
  standalone source literal.
- `proof_corpus_profile_checks` requires the current public candidate case
  count to match the selected smoke profile and keeps the 9024-case profile as
  the explicit Google-comparable release target.

Remaining boundary:

- The current public proof is still an 8-case smoke attestation. Final
  Google-comparable confidence requires building and proving the 9024-case
  profile.

### Public headline/resource constants

Reviewed-state issue:

- Headline totals, reusable-chunk QROAM width, lookup workspace, and modular
  multiplier counts were repeated in tests and integrity checks.

Current remediation:

- `reusable_chunk_lowering_checks` now derives stream counts from
  `stream_plan`, QROAM target/workspace from the embedded QROAM model,
  high/low chunk widths from the field width and chunk count, non-Clifford
  totals from the stream count and per-stream QROAM cost, and logical qubits
  from the owner-capacity/liveness certificate.
- ZKP input tests now derive reusable-chunk headline totals, QROAM parameters,
  modular arithmetic stage totals, and liveness peaks from the bound resource
  document and public values instead of restating `36,957,412`, `1,199`,
  `65,536`, `173`, or `71,492` as independent magic constants.
- The SP1 guest reusable-chunk validator now derives chunk width, chunk count,
  QROAM target/junk capacity, per-stream non-Clifford totals, effective
  high/low chunk widths, and table-multiplier partial-product sums from the
  embedded resource document instead of pinning `155`, `65,536`, `71,492`, or
  `327,680` as validator literals.
- `public_headline_result_checks` now checks that the artifact's `pass` flag
  matches its internal freshness/resource checks. During source churn, stale
  proofs are therefore a detected state rather than a hidden test failure.
- `compiler_verification_project/artifacts/compiler_parameters.json` now records
  the curve, field, raw-window, folded-domain, phase-shell, QROAM block-size,
  and reusable-chunk policy in one versioned artifact with a stable parameter
  digest. `compiler_parameter_checks` ties that artifact back to the schedule,
  logical-resource ledger, and reusable-chunk lowering.
- The prepared ZKP input now carries a committed `compiler_parameters_document`
  plus `compiler_parameters_sha256`; the SP1 guest validates that document's
  semantic digest, schema, internal checks, and stable parameter digest before
  accepting the attestation.
- `compiler_verification_project/artifacts/constant_provenance.json` now binds
  release-critical phase-shell counts, selected headline resource totals, and
  public limits from their source artifacts into the ZKP family document,
  public headline JSON, and counted-resource manifest. The corresponding
  `constant_provenance_checks` group also scans the ZKP input generator for the
  previous hardcoded `512 / 511 / total_measurements = 0` family-count pattern
  and fails if those resource fields become integer literals again.

Remaining boundary:

- The provenance manifest is a guard against repeated release-critical
  constants and source drift; it is not a substitute for a single
  Clifford-complete circuit generator.
- `proof_status.py` now also requires each fixture to bind the exact prepared
  input by `input_sha256` and `input_size_bytes`. A proof-only input change, such
  as adding the compiler-parameter document, therefore cannot look current only
  because the old public values still match.

### Register list in the proof compiler

The proof compiler used to start from a bespoke hardcoded register universe.
The current branch derives proof register IDs from the leaf interface,
lookup-interface slots, arithmetic slots, and resource wire catalog, then emits
`proof_register_contract` into the SP1 input.

Current hardening:

- The contract classifies every prepared proof register as a counted quantum
  wire, carried input alias, semantic lookup constant, or lookup metadata
  interface.
- The SP1 guest recomputes the set of written registers from `prepared_leaf`,
  rejects unclassified registers, rejects unowned written quantum registers, and
  requires counted registers to carry a positive qubit capacity and owner.
- `lookup_x` and `lookup_y` are explicitly semantic lookup constants, not hidden
  full-coordinate quantum lanes.

Remaining boundary:

- This is still a proof-register contract around the prepared leaf, not a
  single primitive-circuit IR that also executes the arithmetic and QROAM gates.

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
- The SP1 input now carries resource certificates, QROAM certificates,
  counted-resource IR, and a proof-register contract, and the guest validates
  them. The guest execution loop still executes high-level field/macro
  semantics rather than the primitive arithmetic/QROAM gate list itself.

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

### RES-2: Field-multiplication reduction now has an executable certificate, but full arithmetic netlists are still not complete

Evidence:

- The SP1/Rust semantics uses `% modulus` for field operations.
- The arithmetic lowering uses n-bit carry ladders, schoolbook-product formulas,
  and an explicit pseudo-Mersenne reduction schedule for `field_mul`.
- `compiler_verification_project/artifacts/modular_arithmetic_certificate.json`
  now binds that `field_mul` schedule to secp256k1's
  `p = 2^256 - 2^32 - 977` shape, reconstructs the 256-bit stage counts from
  `arithmetic_lowerings.json`, and exhaustively executes reduced-width
  pseudo-Mersenne analogues for add/sub/mul/mul-by-21.
- `reusable_chunk_lowering.json` embeds the modular certificate, its internal
  check must pass, and the SP1 guest validates the embedded certificate,
  executable modular IR, and executable-IR count certificate before accepting
  the reusable-chunk resource digest.

Impact:

- The largest previous blind spot, whether the counted multiplier includes a
  concrete mod-p reduction schedule, is narrowed by an executable certificate
  and forged-stage-count/reduced-case tests in both the Python integrity layer
  and the SP1 guest.
- Forging the modular executable IR itself or the executable-IR count
  certificate is now covered by Rust guest negative tests, not only by Python
  artifact-regeneration checks.
- A reviewer can still object that the counted arithmetic is an
  arithmetic-kernel model, not a Clifford-complete reversible netlist for every
  field opcode.

Minimum fix:

- Extend the proof-bound modular arithmetic certificate from the current
  `field_mul` reduction focus to every field opcode.

Best fix:

- Generate and test the modular arithmetic circuit itself, with typed
  reversible wires, cleanup, and liveness.

### RES-3: QROAM K=1 has an internal generated certificate, but not an external synthesis cross-check

Evidence:

- `qroam_primitive_certificate.json` is generated from the selected public
  parameters and records the traversed compute/uncompute segment counts,
  target-register capacity, junk-register capacity, and certificate checks.
- `qroam_reference_crosscheck.json` independently recomputes the QROAMClean
  compute, measured-uncompute, target, and junk equations, checks every
  full-field ledger sweep row, separately checks the selected 155-bit chunk
  stream, and includes reduced-domain table-select/uncompute semantic cases.
- `reusable_chunk_lowering.json` embeds both certificates and checks that they
  match the QROAMClean `K = 1` model used by the public candidate.
- The SP1 guest validates the embedded certificates, recomputes segment CCX
  totals by phase, rebuilds the segment Merkle root from the embedded segment
  hashes, recomputes each deterministic segment digest from its phase/address
  range, checks target/junk workspace fields against the public QROAM model and
  independent reference row, and rejects count/workspace/root/segment-digest
  mutations in negative tests.

Impact:

- The previous mixed-model bug is fixed for `K = 1`, and the selected public
  QROAM stream is no longer only a formula-level assertion. The remaining gap is
  that the certificates are still compact local count/reference certificates,
  not an external QROAM synthesis or Clifford-complete bit-level circuit.

Minimum fix:

- Cross-check the generated certificate against an external library for all
  selected rows.

Best fix:

- Expand the certificate into a full QROAM primitive IR and count it with the
  same liveness engine as the arithmetic.

### REL-1: Release artifact packaging is not fully containerized, but the public headline has a single verifier

Evidence:

- `compiler_verification_project/scripts/verify_public_headline.py` now gives a
  single fast reviewer entrypoint for the checked public headline.
- The script validates `public_headline_result.json`, checked input/public
  values, source-document semantic hashes, fixture records, compressed proof
  digest, Groth16 proof digest, wrap proof digest, and Groth16 verifier-key
  digest from the checked branch state. The normal CLI output is now a compact
  blocker report, with the full per-check JSON kept behind `--verbose`, so stale
  proof failures surface as a short audit list rather than a huge payload dump.
- Optional `--verify-compressed` and `--verify-groth16` flags invoke the
  corresponding checked proof verifier against the checked proof bundle.
- `zkp_attestation_fixture_compressed.json` still keeps the large proof payload
  out-of-line; this is now an explicit digest-bound packaging choice rather
  than an untracked binary sidecar.

Impact:

- Reviewers no longer need to assemble the artifact-binding check by hand.
- This does not yet solve reproducible proof environment packaging; a fresh
  machine still needs the SP1/Rust/Go/protoc/libclang stack to run the optional
  proof verifiers.

Minimum fix:

- Done for proof binary and verifier-key digests, plus the one-command metadata
  verifier.

Best fix:

- Ship a single release manifest with command transcript, binary digests,
  verifier-key digest, input digest, SP1 version, Rust toolchain digest, and
  container digest; or package proof verification in a container/Nix/uv lock so
  a fresh machine can run metadata, compressed, and Groth16 verification
  without local toolchain archaeology.

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

This remains the strongest technical objection, but it is now narrower. The
tail macro cost is bound to `tail_macro_engine.json`, which expands
`complete_a0_all_streamed_tail` into 23 field operations and checks the opcode
histogram against the counted tail kernel. The unresolved part is the counted
three-slot live-field claim: the expanded live-after stream peaks at eight
field values, and the strict operation-concurrent single-assignment fallback
schedule peaks at nine field-sized slots. A real in-place/permutation-extension
schedule is still required before the three-slot headline should be treated as
a full-engine primitive-circuit claim. A fused-output seven-slot schedule now
exists as checked strict resource evidence, but it still does not make the
three-slot macro wrapper a physical result.

Best response:

- Build the in-place tail schedule or count the extra field slots.
- Make the executable schedule, liveness, and cost come from `tail_macro_engine`.
- Keep the slot-gap check in the fast gate until this is closed.

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

`tail_macro_engine.json` now expands `complete_a0_all_streamed_tail` into a
field-operation IR and binds the non-Clifford total to the selected tail kernel.
The remaining P0 is stricter: turn that expanded contract into an executable
in-place schedule whose live field values fit the counted slots, or revise the
headline resource budget.

Exit criterion:

- Peak live qubits remain below `1200` after internal scratch and all tail
  temporaries are included, or the headline is revised.

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

Current remediation:

- `compiler_verification_project/artifacts/release_corpus_preflight.json` now
  runs the executable point-add leaf over the Google-comparable 9024-case profile
  without invoking SP1 proving. It records edge-category counts, preview
  head/tail cases, and a length-prefixed canonical-JSON rolling digest of the
  whole case stream.
- `release_corpus_preflight_checks` regenerates that digest from the checked
  leaf and proof-corpus profile, so a release-size semantic-corpus drift fails a
  fast integrity group before any compressed/Groth16 work starts.
- `build_zkp_attestation_input.py --profile release` now resolves the 9024-case
  target from `proof_corpus_profiles.json` and writes a release candidate input
  bundle without invoking SP1 proving. This removes another manual `--cases
  9024` step from the final proof rebuild path.
- `build.py --target release-candidate-zkp` now exposes the same 9024-case
  release candidate bundle as a first-class no-prover build target, so the final
  proof rebuild input is produced by the checked build system rather than by an
  ad hoc command line.
- `release_candidate_preproof.py --execute` is now the intended pre-proof gate
  for this item: it builds the 9024-case release input in an isolated directory
  and runs the SP1 guest execute path over that input without invoking
  compressed or Groth16 proving. This catches guest/input/public-value failures
  before spending prover time.
- The SP1 public-values stream is now committed as explicit JSON bytes and the
  host decoder accepts both that stable format and legacy checked bincode proof
  bundles. This removes the previous execute-only host decode fragility from the
  fast release-candidate gate.

Still open:

- The checked public proof remains an explicit 8-case smoke attestation until
  compressed and Groth16 are rebuilt over the 9024-case release profile.
- Until then, `release_corpus_preflight.json` is only release-size semantic
  evidence and must not be described as a ZKP.

### P0: ZKP resource derivation from IR

The SP1 guest should not only reconstruct formulas from family summaries. It
should parse or receive a committed resource IR and derive the headline totals.

Exit criterion:

- The guest computes non-Clifford and qubit totals from the committed circuit
  representation or from a separately proven resource certificate.

Current remediation:

- `compiler_verification_project/artifacts/reusable_chunk_lowering.json` now
  carries `counted_resource_engine`, an independently recomputed report over
  `counted_resource_ir`. The engine canonical-hashes the counted IR, recomputes
  every non-Clifford term product and sum, walks interval live wires through the
  wire catalog, rejects duplicate or unknown live wires, derives owner peaks,
  and derives the global peak interval.
- The SP1 guest validates the same counted-resource engine fields before
  accepting the resource digest. Rust negative tests now reject both a forged
  engine peak and an interval that double-counts a live wire.
- The reusable-chunk artifact now also carries `resource_contract_engine`, which
  checks that `counted_resource_ir` and executable liveness have the same wire
  catalog and same interval rows, then checks owner-capacity rows against the
  engine-derived owner peaks. Rust guest tests reject a counted/executable
  liveness drift and counted/resource-contract engine digest drift even when the
  resource-certificate digest is refreshed.
- `executable_liveness` is now derived from an embedded
  `executable_schedule_ir` event stream. The schedule records the ordered
  carried-input, lookup-metadata, lookup-infinity, and per-chunk QROAM
  load/consume/uncompute events with live wires; integrity checks, the public
  headline verifier, and the SP1 guest verify that liveness intervals come from
  those events. This is not a Clifford-complete macro netlist yet, but it
  removes another hand-maintained interval-only boundary.
- The reusable schedule now binds each event to executable leaf instruction
  PCs/opcodes, and QROAM stream events are required to bind to the tail opcode
  they are counting. Integrity checks, the public headline verifier, and the
  SP1 guest reject source-instruction drift even if the resource-certificate
  digest is refreshed.
- The schedule/liveness/counting helpers were moved out of the reusable lowering
  script into `compiler_verification_project/src/executable_resource_engine.py`.
  The lowering now calls a single `build_reusable_chunk_resource_engine(...)`
  entrypoint, and the artifact carries an `executable_resource_engine` summary
  binding public totals to counted-IR, executable-liveness, owner-capacity, and
  resource-contract digests. Integrity checks, the public headline verifier, and
  the SP1 guest reject drift in that engine summary. Remaining P0 work is to
  feed the engine a Clifford-complete flattened instruction stream rather than
  the current compact leaf/macro boundary.
- The public-headline verifier now independently recomputes the
  `counted_resource_ir`, executable-liveness, and owner-capacity digests recorded
  by the resource contract engine, so this digest-drift class is visible in the
  reviewer CLI before running SP1.
- `compiler_verification_project/artifacts/public_engine_manifest.json` now
  binds the current public engine layer into a no-ZKP artifact: executable
  instruction rows, wire rows, schedule rows, owner-capacity rows, resource-term
  rows, public totals, and the engine/resource-contract digests are regenerated
  from `reusable_chunk_lowering.json`. `public_headline_result.json` records this
  artifact as checked evidence, and `fast_engine_verify.py` exercises the
  no-prover edit-loop checks plus mutation tests.
- The same public engine manifest now binds semantic-boundary evidence into the
  no-ZKP gate: the 80/80 streamed-tail edge-case equivalence, the reusable-tail
  toy semantic/scratch trace over 110,692 boundary pairs, the 9,024-case release
  corpus preflight, and the checked smoke corpus must all cover random,
  doubling, inverse, accumulator-infinity, and lookup-infinity categories.
- The public engine manifest also binds primitive-operation evidence into the
  no-ZKP gate: the selected arithmetic tail opcode must match the generated
  arithmetic operation IR counts, the QROAMClean stream cost/workspace must
  match the selected compiler policy and reusable-chunk stream terms, and the
  phase shell must match the compiler-parameter and family-document payloads.
  Focused mutation tests now reject forged arithmetic counts, forged QROAM
  stream costs, and phase-shell count drift without invoking SP1.
- `compiler_verification_project/artifacts/public_candidate_materialized_circuit_manifest.json`
  now gives the promoted reusable-chunk candidate its own deterministic
  run-length primitive stream boundary plus a materialized flat primitive
  stream with concrete operand wires and row liveness. It keeps the legacy
  wrapper stream at `36,957,412 / 1,199`, and separately emits the primary strict
  materialized stream at `36,973,222 / 1,968`. The strict stream stores all
  source-bound run-length rows and matching liveness/owner rows, expands all
  public QROAM streams through the generated QROAM segment certificate, and
  derives totals by scanning `39,386,537` primitive operations over
  deterministic full-stream segments. `public_engine_manifest.json` binds the
  strict materialized flat-stream digest and Merkle root while treating formula
  rows and the legacy wrapper stream as consistency snapshots. The remaining
  caveat is narrower: the checked flat-index stream is an expandable
  primitive-instruction commitment with macro/source-row liveness binding, not a
  physical placement/routing schedule or a multi-gigabyte checked-in TSV with
  one line per primitive operation.
- `compiler_verification_project/artifacts/engine_completion_audit.json` now
  makes that caveat machine-readable. It regenerates the public totals from the
  strict materialized flat netlist, checks that all run-length rows are
  source-bound by kind, rechecks the standard-QROAM cost link, checks that
  modular arithmetic kernels derive from `executable_modular_circuit_ir` and
  the local modular primitive-stream certificate, binds those local streams to
  public arithmetic engine rows and strict liveness, binds the selected tail
  macro to `tail_macro_engine`, binds `modular_execution_trace.json`, binds
  `scheduled_modular_primitive_netlist.json`, binds the public-engine global
  splice over grouped arithmetic+QROAM rows, and keeps
  `clifford_complete_goal_achieved = false` while the ZKP guest and exported
  full physical stream still do not consume that spliced global physical
  boundary directly.
  The fast engine loop now includes this audit, so a future patch
  cannot silently promote the current boundary result into a stronger
  full-engine claim by editing prose alone.
- `compiler_verification_project/artifacts/arithmetic_operation_ir.json` now
  reconstructs arithmetic block/stage/kernel/selected-leaf primitive counts from
  materialized operation streams and digests. Modular add/sub/mul kernels are
  generated from the embedded `executable_modular_circuit_ir`; the modular
  arithmetic certificate consumes that same IR for reduced-width semantic
  execution and local primitive-stream hashing instead of being an independent
  formula source. The public materialized-engine manifest binds those streams
  to concrete public arithmetic rows and strict liveness. The modular execution
  trace then schedules the selected tail into modular sub-operations, lookup
  interface rows, and the zero-lift guard. The scheduled modular primitive
  netlist scans those sub-operations into primitive row segments and derives the
  tail CCX/measurement totals from that row stream. The resource-liveness certificate
  embeds the full compact arithmetic IR, and fast integrity checks regenerate it.
  The generated-block operand contract also distinguishes bit-index ladder
  operands from operation ordinals, so the IR's operand-capacity profile is no
  longer inflated by generator event numbering. The SP1 guest now validates
  those generator contracts instead of trusting the artifact's `pass` field.
- `qroam_primitive_certificate_checks` is now part of the fast ZKP preflight,
  and the SP1 guest reconstructs the QROAM primitive segment Merkle root from
  the embedded segment hashes before accepting the reusable-chunk resource
  certificate.
- `modular_arithmetic_certificate.json` now also carries an executable
  modular-circuit IR for canonical add/sub, double-sub, triple, multiplication
  by 21, and pseudo-Mersenne multiplication. Reduced-width exhaustive tests run
  through that IR, the 256-bit IR opcode counts are checked against
  `arithmetic_lowerings.json`, and the local 256-bit modular primitive streams
  are generated and SHA-256-bound before accepting the resource certificate.

Still open:

- The repo now has a single public flat-index primitive-operation commitment for
  counting and liveness, but the semantic executor still runs the point-add
  boundary contract rather than simulating every one of the `39,370,727`
  primitive instructions. The next confidence jump is to make the same flat
  stream executable at the primitive-op layer, at least under a reduced-width
  test harness.
- The checked flat-index stream binds liveness/owner rows per contribution and
  recomputes owner sums from the wire catalog, but arithmetic rows still inherit
  macro/stage wire scopes. A reviewer can still ask for per-Toffoli operand
  wires for every arithmetic primitive, not only stage-level source rows.
- The ZKP still proves the semantic point-add boundary plus resource-engine
  consistency. It is stronger than handwritten formula trust and now references
  the flat-index engine output, but it is not yet the same confidence class as a
  proof that executes the full resource-counted primitive circuit.

### P1: QROM/QROAM reference cross-check

Add a cross-check against an external QROM/QROAM implementation or a small
formally specified QROAM primitive.

Exit criterion:

- For selected parameters, internal QROAM cost/workspace matches an independent
  reference primitive, the 155-bit chunk stream is not conflated with the
  256-bit full-field ledger sweep, and mismatch fails CI.

Current remediation:

- The QROAM reference tests now import the selected domain size, K=1 block size,
  field width, reusable chunk width, and ledger selected row from
  `compiler_parameters.json`, `qroam_primitive_certificate.json`, and
  `logical_resource_ledger.json` instead of restating those values as separate
  test constants. This does not replace an external implementation, but it
  removes another self-confirming hardcoded-parameter path from the selected
  QROAM checks.
- The arithmetic lowering generator now requires its QROAM domain size from the
  compiler parameter source. The old hidden `32768` default was removed from
  `_standard_qroam_coordinate_stream_cost`, so changing the folded magnitude
  domain must flow through the project constants and integrity checks rather
  than silently preserving the old table size inside arithmetic lowering.

### P1: Baseline source package

Move Google baseline numbers and citations into a versioned source artifact.

Exit criterion:

- Docs and tests import baseline data rather than repeating constants.

Current remediation:

- `data/public_google_baseline.json` is already the versioned source artifact
  for the public Google low-qubit and low-gate rows. The Cain transfer payload
  now also carries normalized `baseline_transfers` keyed by those baseline row
  names, and `results/cain_2026_integration_summary.json` exposes
  `baseline_transfer_ranges`. The Cain tests validate formulas through those
  named baseline rows instead of using the legacy `90M`, `70M`, `1200`, or
  `1450` key names as independent sources of truth. Legacy keys remain in the
  artifact only as compatibility views.
- Release-corpus build tests now derive the 9024-case target from
  `proof_corpus_profiles.json`, release-candidate build tests use the same
  profile resolver as the build script, public-headline policy mutation tests
  mutate the checked policy value rather than restating `1199`, and IBM context
  tests derive headline strings from `public_headline_result.json`.
- The release preproof unit tests no longer restate the current
  `36,957,412 / 1,199` macro/ZKP-wrapper claim or the release case count. They derive the
  mocked execute public values from `public_headline_result.json` and the
  release proof-corpus resolver, and the active `tests/`, `src/`, and
  `scripts/` gates no longer contain those headline literals as independent
  pass conditions.
- The reusable-family ZKP input builder no longer carries a local
  `direct_seed_non_clifford = 297` literal. It derives that value from the
  generated block-inventory reconstruction consensus, and the ZKP input test
  verifies the reusable family document uses that generated source.

### P1: Reproducible proof environment

Package proof generation and verification in a container or Nix/uv lock.

Exit criterion:

- A fresh machine can verify compressed and Groth16 proof bundles and reproduce
  public values with one documented command sequence.

Current remediation:

- `compiler_verification_project/scripts/proof_environment_report.py` now emits a
  machine-readable local readiness report for Python, Cargo, Rust, `protoc`,
  clang/libclang-facing bindgen, Go, and optional SP1 helper tools. This catches
  missing prerequisites, such as absent `protoc`, before a long proof rebuild.
- `fast_zkp_preflight.py` is the default no-prover edit-loop gate and refuses a
  command plan that would invoke `--prove` or the guarded prover wrapper.
- The same preflight now has `--require-current-proofs`, which switches the
  freshness step to `proof_status.py --require-all-current` while preserving the
  no-prover command guard. This gives a single publication-gate command after
  proof rebuilds and a nonblocking edit-loop command before proof rebuilds.
- `compiler_verification_project/artifacts/proof_environment_contract.json` is
  now a checked runbook contract, not prose. It binds required proof-tool
  descriptors, no-prover edit-loop commands, publication freshness gates,
  direct compressed/Groth16 verifier commands, public-headline checked artifact
  digests, and the curated `proof_manifest.json` records. The integrity group
  `proof_environment_contract_checks` regenerates this artifact, rejects
  manifest drift, rejects publication gates that no longer require current
  proofs, and rejects accidental `--prove` in the fast command contract.
- `compiler_verification_project/artifacts/proof_publication_status.json` is a
  checked freshness artifact generated from the shared proof-status engine. The
  integrity group `proof_publication_status_checks` rejects forged
  `publication_ready` values, removed compressed/Groth16 publication gates,
  stale public-headline pass semantics, and source-artifact digest drift. It
  intentionally records the curated proof manifest by path and file count, not
  by full-manifest SHA, and the curated proof manifest excludes
  `verification_summary.json`; this keeps the manifest/summary/publication
  status stack acyclic while `MANIFEST.sha256` still covers the checked summary.

Still open:

- This is a deterministic preflight plus checked runbook contract, not yet a
  pinned container/Nix environment.

### P1: Digest tree for large artifacts

Replace huge flat JSON traces with deterministic compressed archives plus
Merkle/digest indexes.

Exit criterion:

- Git diffs are reviewable, artifacts remain machine-verifiable, and no single
  checked blob approaches GitHub warning limits.

Current remediation:

- `compiler_verification_project/artifacts/artifact_digest_tree.json` now
  records every tracked file at or above the large-artifact threshold, split
  into deterministic 1MiB chunks with per-chunk SHA-256, full-file SHA-256, and
  a Merkle root.
- `artifact_digest_tree_checks` regenerates that manifest from the checked tree
  and fails on omitted files, changed chunk bytes, changed file sizes, or stale
  Merkle roots.

Still open:

- This is a reviewability and verification manifest, not yet a replacement of
  the largest flat JSON/CSV artifacts with compressed archive payloads.

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

Current remediation:

- `tests/test_compiler_verification_project.py` now includes model-level
  mutation tests for two previously listed drift classes: changing the selected
  proof-corpus case count without updating public values fails
  `proof_corpus_profile_checks`, and altering the field width in only
  `compiler_parameters.json` fails `compiler_parameter_checks`.
- The same mutation suite now covers the remaining listed drift classes:
  removing the reusable `qchunk` macro scratch wire, changing QROAM block size
  in only the reusable lowering model, deleting lookup-infinity boundary
  coverage from the reusable tail candidate, and changing the boundary no-op
  policy in the subcircuit equivalence artifact all fail their corresponding
  integrity groups.
- The build script now has a fast `composition-artifacts` target for the
  previously easy-to-miss downstream resource artifacts:
  `full_attack_inventory.json`, `subcircuit_equivalence.json`, and
  `headline_opcode_coverage.json`. It gives resource-accounting edits a prover-free
  refresh path before any compressed/Groth16 rebuild is considered.

## Recommended Public Wording

Avoid:

> We crushed Google's result.

Use:

> Under the repository's checked standard-QROM compiler-family boundary, the
> current primary strict artifacts define a `36,973,222` non-Clifford / `1,968`
> logical-qubit result; the older `1,199` artifact is only a macro/ZKP wrapper.
> `proof_status.py --require-all-current` is the release gate for checked SP1
> compressed/Groth16 proof freshness. This improves the cited public Google
> 2026 non-Clifford lines numerically, but no longer beats Google's published
> logical-qubit lines under the strict tail count, and the proof boundary is not
> identical to Google's hidden-circuit 9024-case SP1/Groth16 attestation. The
> repository now ships a flat-index primitive-operation commitment for the
> public candidate, but it still does not prove a physical full-Shor execution
> schedule or SP1 execution of every primitive operation.

## Bottom Line

The result is worth serious attention. It is not obviously fake, and the latest
resource model fixes the previous lookup/QROAM accounting failures. But the
credible external claim is still narrower than the most excited internal
phrasing:

- strong: checked standard-QROM compiler-family boundary at `36,973,222 / 1,968`
- not yet strong enough: Google-equivalent proof confidence
- not yet strong enough: fully flattened primitive-gate Shor circuit
- most urgent engineering gap: allocate modular arithmetic into the same global
  Clifford-complete schedule and keep reducing the tail below seven field slots

## Post-Review Remediation Status

This report reviewed commit `4d9fefed41ca0f6b5cf6528ce8366065fc6d557a`.
Later hardening on the same branch changes the status of some findings, but it
does not erase the central architectural criticism.

Fixed after review:

- `ZK-1`: the active SP1 input moved to schema
  `compiler-project-zkp-attestation-input-v5`. The guest now receives the full
  committed claim, leaf, family, case-corpus, resource-certificate, and
  compiler-parameter documents; recomputes their canonical SHA-256 digests;
  derives the prepared claim summary, family summary, leaf program, and case
  corpus from those documents; and publishes the recomputed public claim hashes.
- The public values now include `resource_certificate_sha256`, binding the
  selected frontier, executable leaf liveness summary, QROAM workspace/cost
  checks, arithmetic lowering inventory, selected-family FT-IR leaf sigma, and
  global resource owner ledger to the proof input.
- Negative guest tests were added for stale claim labels, mutated committed
  claim payloads, mutated prepared leaves, mutated prepared case corpora, and
  mutated resource leaf-sigma primitive counts.
- `RES-3`: the public reusable-chunk input now binds
  `qroam_primitive_certificate.json` and `qroam_reference_crosscheck.json`
  through `reusable_chunk_lowering.json`.
  That certificate traverses generated QROAMClean `K=1` compute and measured
  cleanup segments for the selected `32768`-entry, `155`-target-bit stream,
  reconstructs the `65,536` non-Clifford per-stream cost and `155`
  target-plus-junk workspace, cross-checks it against an independent reference
  artifact that also validates the full-field ledger sweep, and is validated by
  the SP1 guest. New negative guest tests reject forged QROAM primitive counts,
  forged target workspace, and forged reference rows.
- `RES-2`: the central `field_mul` lowering now carries explicit secp256k1
  pseudo-Mersenne reduction stages for `p = 2^256 - 2^32 - 977`, including the
  first fold, second narrow fold, and two canonical subtract-p passes. This
  moved the checked headline from `32,879,331 / 1,044` to
  `34,736,076 / 1,044` rather than leaving prime-field reduction implicit; the
  later canonical modular add/sub correction moved the checked three-slot
  reference to `34,925,796 / 1,044`.
- `RES-2`: `modular_arithmetic_certificate.json` now carries an
  `executable_modular_circuit_ir` for add, sub, sub-sum, triple, multiplication
  by `21`, and pseudo-Mersenne multiplication. The 256-bit IR derives the
  opcode non-Clifford counts checked against `arithmetic_lowerings.json`, and
  the same IR is executed exhaustively on reduced-width pseudo-Mersenne
  analogues over `23^2` and `53^2` input pairs. The certificate now also
  materializes and hashes local 256-bit primitive streams for each modular
  opcode: `89,688` local rows, including `77,612` CCX rows, are bound back to
  the lowering kernels. Integrity checks and narrow tests reject forged IR count
  bindings, forged primitive-stream counts, forged reduction-stage counts, and
  forged reduced-width results. The reusable-chunk resource certificate embeds
  this certificate, and the SP1 guest validates it before accepting the public
  resource digest.
- `RES-2`: `arithmetic_operation_ir.json` now provides a compact typed
  arithmetic operation-stream layer. It materializes every arithmetic lowering
  block into canonical primitive-operation streams, records per-block stream
  digests, reconstructs stage/kernel/selected-leaf primitive totals from those
  streams, separates non-arithmetic leaf opcodes explicitly, and is embedded in
  full compact form in the resource liveness certificate. Integrity checks
  validate the artifact, and new guest negative tests reject both a forged
  arithmetic operation-IR leaf row and a forged block-level total after
  refreshing the resource-certificate digest. This closes another
  copied-total/manual-ledger path, while leaving the deeper full-netlist
  arithmetic objection open.
- `ZK-2` / resource-IR binding: `reusable_chunk_lowering.json` now includes
  `counted_resource_ir`, a committed counted-resource representation containing
  the non-Clifford terms and liveness intervals used for the public
  reusable-chunk public engine. Integrity checks, `verify_public_headline.py`, and the
  SP1 guest recompute `36,973,222` non-Clifford operations and the `1,968`
  live-qubit peak from the current strict public engine input; guest tests reject forged counted-resource
  terms. The new `resource_contract_engine` additionally proves that the counted
  resource IR uses exactly the same wire catalog and interval liveness rows as
  executable liveness, and that owner-capacity rows equal the engine-derived
  owner peaks. This does not make the repository a Clifford-complete full-Shor
  primitive netlist, but it removes another parallel formula-only path from the
  macro wrapper.
- `ZK-2` / current-headline stream manifest: the repo now emits
  `compiler_verification_project/artifacts/headline_resource_manifest.json`
  for the reusable-chunk result. It expands the ZKP-bound
  `counted_resource_ir` into counted term rows and liveness rows, while the
  current strict public engine recomputes `36,973,222` non-Clifford operations
  and the `1,968`-qubit peak, and is bound by `public_headline_result.json` plus
  integrity checks. The repo also emits
  `public_candidate_materialized_circuit_manifest.json` for the current
  result, so the public candidate has its own checked run-length primitive
  stream and flat-index segment commitment instead of relying on the older
  `34,925,796 / 1,044` materialized frontier family. The current artifact
  commits to the complete public operation-index range and segment roots; the
  remaining red-team ask is per-primitive arithmetic operand wires and primitive
  execution, not another resource formula.

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
  reconstructs `42,417,128` operations, `34,925,796` CCX, and `7,491,332`
  measurements. The manifest now splits that stream into `43` deterministic
  million-operation-or-smaller digest segments with Merkle root
  `5ff61670bb4d1a394cb15b57b3c917687c092083654bb8738e47f2f0f1589188`.
  That manifest is schema-versioned, has a no-prover
  `build.py --target materialized-circuit-manifest` refresh path, and is
  included in the build summary, curated proof manifest, resource liveness
  certificate, and SP1 guest resource-certificate checks.
  This is still a digest/manifest over the stream rather than a checked
  tens-of-millions-row TSV dump.
- `RES-1`: `complete_a0_all_streamed_tail` is no longer only a single opaque
  resource token in the ZKP-bound resource certificate. The certificate contains
  66 primitive leaf-sigma rows for the macro, and the guest verifies that their
  whole-oracle non-Clifford contribution equals the per-leaf macro lowering
  times the 31 leaf calls. The tail reversibility artifact now also checks
  `110,692` exhaustive canonical toy boundary translations, including the edge
  cases that historically produced semantic blind spots. A destructive
  formula-DAG search now also fails to fit the current tail formula into the
  counted three field slots on curated toy generator lookups, even when old
  values may be dropped after injectivity-preserving transitions. Internal
  live-wire scheduling below those primitive rows is still not a bit-addressed
  wire netlist.
- Error class 4: `compiler_verification_project/artifacts/headline_opcode_coverage.json`
  is now a generated coverage matrix for every opcode in the selected executable
  leaf. It requires a declared opcode policy, a ZKP-prepared kind, flat-liveness
  rows for every executable pc, whole-leaf edge-case equivalence, and additional
  subcircuit/lowering/leaf-sigma evidence for counted arithmetic opcodes. This
  prevents a future headline opcode from entering the selected leaf as an
  unreviewed semantic/resource side path.
- Fallback stress: `compiler_verification_project/artifacts/fallback_frontier_stress.json`
  checks the strict `<40M / <1200` escape route if the tail needs four field
  slots. With the current full-coordinate QROAM workspace, four field slots
  reach `1,300` logical qubits. Chunking the coordinate target enough to fit
  strictly below `1,200` qubits gives a `1,199`-qubit counterfactual but raises
  the count to `44,894,156` non-Clifford operations. Under current lowerings, a
  four-slot fallback therefore needs either a new lookup primitive or at least
  `4,894,156` non-QROAM non-Clifford savings.
- The same fallback stress now records the main plausible escape route rather
  than hiding it in discussion: reusable chunked coordinate targets. If a
  155-bit QROAM target chunk can be loaded once per `lookup_x`, `lookup_y`, and
  `lookup_x_plus_y` chunk and reused across the matching consumers inside a
  four-slot tail, the stress model gives `36,957,412` non-Clifford operations
  and `1,199` logical qubits. This is not a headline result until the chunked
  table-controlled multiplier lowering, executable four-slot contract,
  liveness, resource certificate, and ZKP binding are built.
- `compiler_verification_project/artifacts/reusable_chunk_tail_candidate.json`
  now checks the semantic half of that escape route. It splits table coordinates
  into chunks, reuses each chunk across matching consumers, and exhaustively
  verifies the chunked tail against the unchunked complete-add tail and affine
  group addition over the same `110,692` curated toy boundary pairs. The artifact
  now also contains an executable candidate leaf using
  `complete_a0_reusable_chunk_tail` with a fourth scratch slot `qchunk`, and the
  toy check executes that leaf through `exec_netlist`.
- The executable candidate leaf now also traces the `qchunk` scratch contract:
  for every non-lookup-infinity boundary pair it records each table-controlled
  chunk load into `qchunk`, requires the expected low/high chunks for
  `lookup_x`, `lookup_y`, and `lookup_x + lookup_y`, and verifies that `qchunk`
  resets to zero after each consumer. Integrity mutation tests reject a forged
  scratch-trace pass bit, so `qchunk` is no longer only a named liveness owner.
- `compiler_verification_project/artifacts/reusable_chunk_lowering.json` now
  records the candidate's generated lowering/resource contract. It derives the
  The demoted macro wrapper uses 6 chunk streams per leaf from the executable leaf's three coordinate tables
  and two chunks, prices each stream with standard QROAMClean `K=1` (`65,536`
  non-Clifford, `155` target qubits, zero junk), reconstructs `36,957,412`
  non-Clifford operations and `1,199` logical qubits, assigns numeric capacity
  to every counted owner, and now carries an executable interval-liveness
  certificate. That certificate derives the peak from live wires, not a
  hand-picked register list: it keeps the fourth field slot `qchunk` live
  concurrently with the QROAM chunk target, proves no full-coordinate
  `lookup_x`/`lookup_y` lane is live, and reconstructs the owner peaks
  `1024 + 173 + 1 + 1 = 1199`. It also closes the
  inherited-arithmetic-base objection at the counted primitive-block level:
  each table-controlled multiplier has low/high effective chunk widths
  `155 + 101 = 256`, so its partial-product grid is exactly the inherited
  full-width `65,536` non-Clifford grid, while the high chunk's 54 zero-padded
  QROAM target lanes are still charged in lookup workspace/cost. This fixes the
  previous class of width/workspace mix-ups for the reusable-chunk candidate.
  The primary strict headline does not reuse the `1199` macro total; it replaces
  the four-slot arithmetic term with the replayed fused-output seven-slot tail
  term and publishes `7 * 256 + 173 + 2 + 1 = 1968`.
- `compiler_verification_project/artifacts/zkp_attestation_reusable_chunk_candidate/`
  now contains a checked candidate ZKP input bundle, and the Rust guest library
  accepts it in `run_prepared_attestation`. This means the native guest path
  binds and executes `complete_a0_reusable_chunk_tail`, commits
  `reusable_chunk_lowering.json`, recomputes the executable-liveness peak from
  the certificate's interval rows, rejects failing liveness checks, and returns
  strict public-engine claim `36,973,222 / 1,968`. The candidate directory also contains
  checked core, compressed, and Groth16 fixtures, the compressed proof bundle,
  the Groth16 proof bundle, the wrap proof bundle, and the matching Groth16
  verifier key. After the modular-arithmetic certificate was bound into the
  reusable-chunk resource document, `proof_status.py` correctly marks those
  proof layers stale until the final compressed/Groth16 rebuild is run.
- `compiler_verification_project/artifacts/primary_strict_result.json` selects
  `36,973,222 / 1,968` as the single current public resource headline.
  `compiler_verification_project/artifacts/public_headline_result.json` remains
  the legacy macro/ZKP publication-wrapper reference. It records the checked
  proof files, verifier key, input/public-value hashes, exact comparison ratios
  against the public Google baseline, and a failing `pass` flag while checked
  proofs are stale against the current resource digest. The old `34,925,796 / 1,044` three-slot
  family remains checked as a reference boundary, not the public headline.
- `ZK-3`: proof binaries are now included in the curated proof manifest, and
  `proof_status.py` cross-checks fixture JSON, proof binaries, Groth16 verifier
  keys, and `artifacts/package/proof_manifest.json`. The checked JSON fixtures
  still intentionally keep large compressed proof bytes out-of-line, but path,
  size, and digest binding is now part of the cheap freshness gate.
- The proof freshness verdict is no longer only a CLI report:
  `proof_status.py` is a thin wrapper around `proof_status_report.py`, and
  `proof_publication_status.json` binds the stale systems, blockers,
  public-headline pass flag, proof-manifest digest, and publication gate
  commands into the checked artifact set.

Still open:

- The repository ships a checked segmented digest/Merkle manifest of the
  selected primitive operation stream, but not the tens-of-millions-row TSV gate
  list itself.
- The deepest refactor remains mandatory before claiming Google-equivalent
  hidden-circuit confidence: `counted_resource_ir` and `resource_contract_engine`
  now tie public resource totals to executable liveness and owner capacity inside
  integrity checks and the SP1 guest, but the same source engine still should
  emit the semantic leaf, primitive lowering, artifact digests, and ZKP input
  without maintaining parallel prepared and audit views.
- Final publication still requires rebuilding core/compressed/Groth16 artifacts
  from the current checked input and making `proof_status.py --require-all-current`
  pass.
