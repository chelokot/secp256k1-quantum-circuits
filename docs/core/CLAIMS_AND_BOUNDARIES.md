# Claims and boundaries

This file defines the strongest claims supported by the checked-in artifacts.

## Strongest defensible claim

The repository publishes exact kickmix-ISA arithmetic schedules for a
secp256k1-specialized point-add leaf and explicit retained-window scaffold
metadata, together with deterministic audits, finite-model checks, and a
separate exact compiler-family oracle subproject that closes the
classical-tail-elision gap for a fully quantum raw-32 schedule. It now also
ships an SP1 attestation bundle for one selected standard-QROM family claim at
that same boundary. The current primary strict headline is the reusable-chunk
standard-QROAM family with the guarded fused-output seven-slot tail at
`36,973,222` non-Clifford operations and `1,968` logical qubits. That primary
public resource result is selected in
`compiler_verification_project/artifacts/primary_strict_result.json`, with the
replayed-tail source in
`compiler_verification_project/artifacts/strict_replayed_tail_headline.json`.
The old four-slot macro contract remains checked as a ZKP/publication wrapper reference in
`compiler_verification_project/artifacts/public_headline_result.json`, but it
is not the primary strict resource headline. The older `34,925,796 / 1,044`
family remains checked as a reference boundary, not as the promoted public
claim. The generated QROAMClean tradeoff ledger still records the higher-space
rows needed for the older `<24M` non-Clifford target; the repository headline
is the single checked central family bound by the executable leaf, resource
ledger, and replayed-tail owner capacity. The materialized public-candidate
manifest now includes a strict replayed-tail capacity overlay that binds the
flat operation stream's non-Clifford count to that seven-slot capacity result,
and a strict run-length liveness projection that scans arithmetic-tail rows to
the `1,968`-qubit peak while leaving non-tail rows unchanged. It still does not
make the fully materialized flat-netlist segment hashes include that projected
liveness. The ZKP guest/input still binds the old macro wrapper until it is
rebuilt around the strict seven-slot contract.

## Exact layers

### 1. Optimized arithmetic leaf

`artifacts/circuits/optimized_pointadd_secp256k1.json` is the primary
machine-readable leaf schedule for:

`Q <- Q + L`

where:

- `Q` is the accumulator in the repository's projective representation
- `L` is an externally supplied affine lookup point
- field arithmetic is over the secp256k1 prime field

This layer is checked by:

- `artifacts/verification/core/optimized_pointadd_audit_16384.csv`
- `artifacts/verification/core/toy_curve_exhaustive_19850.csv`
- `artifacts/verification/extended/toy_curve_family_extended_110692.csv`

### 2. Retained-window scaffold metadata

`artifacts/circuits/ecdlp_scaffold_optimized.json` is a machine-readable
retained-window schedule with:

- one direct seed,
- `28` retained point-add leaf calls,
- `3` classical tail elisions,
- window size `16`.

Its internal coherence is checked by
`artifacts/verification/extended/scaffold_schedule_audit_256.csv`.

### 3. Exact lookup contracts

The repository exposes lookup words, structured folding rules, and audited
semantic points explicitly.
Two exact contract layers are checked:

- the base lookup contract in
  `artifacts/verification/extended/lookup_contract_summary.json`
- the signed folded lookup contract in
  `artifacts/lookup/lookup_signed_fold_contract.json`

The signed folded variant is audited by:

- `artifacts/lookup/lookup_signed_fold_exhaustive_g.csv`
- `artifacts/lookup/lookup_signed_fold_multibase_sampled.csv`


### 4. Exact compiler-family whole-oracle layer

The root-level `compiler_verification_project/` adds the strongest exact layer
below the ISA boundary. It publishes:

- `compiler_verification_project/artifacts/full_raw32_oracle.json`
- `compiler_verification_project/artifacts/family_frontier.json`
- `compiler_verification_project/artifacts/standard_qrom_lookup_assessment.json`
- `compiler_verification_project/artifacts/exact_leaf_slot_allocation.json`
- `compiler_verification_project/artifacts/phase_shell_lowerings.json`
- `compiler_verification_project/artifacts/ft_ir_compositions.json`
- `compiler_verification_project/artifacts/whole_oracle_recount.json`
- `compiler_verification_project/artifacts/subcircuit_equivalence.json`
- `compiler_verification_project/artifacts/verification_summary.json`

This layer is exact for the **named compiler families** checked into that
subproject. In particular, it fixes:

- a fully quantum raw-32 schedule with no classical tail elisions,
- generated folded lookup-family operation inventories,
- generated arithmetic-kernel operation inventories,
- an embedded executable modular arithmetic IR that generates the modular
  add/sub/mul kernels, plus a proof-bound modular arithmetic certificate that
  executes reduced-width pseudo-Mersenne analogues and binds the 256-bit
  field-multiplication reduction stage counts back to that same arithmetic
  lowering artifact,
- explicit standard-QROAM streamed table-controlled multiplier data-selection
  inventories,
- a checked standard-QROM lookup assessment that binds the selected family to a
  full 32768-entry coordinate-stream QROAM primitive instead of the rejected
  bitwise-banked path-select boundary,
- exact leaf slot allocation, and
- generated phase-shell operation inventories for the selected semiclassical inverse-QFT shell,
- compositional FT-style call graphs plus traversed leaf sigma for the named
  compiler families,
- independent exact whole-oracle recount derived from that FT IR leaf sigma,
- internal subcircuit-equivalence witnesses across traced ISA opcodes, lowered
  lookup families, boundary no-op semantics, no-free-wire ownership, and
  generated whole-oracle composition, and
- compact phase-shell summaries derived from those exact lowerings, including a semiclassical-QFT shell.

### 5. Exact SP1 attestation at the compiler-family boundary

The repository also ships a checked SP1 attestation bundle:

- `compiler_verification_project/artifacts/zkp_attestation_input.json`
- `compiler_verification_project/artifacts/zkp_attestation_claim.json`
- `compiler_verification_project/artifacts/zkp_attestation_family.json`
- `compiler_verification_project/artifacts/zkp_attestation_cases.json`
- `compiler_verification_project/artifacts/resource_liveness_certificate.json`
- `compiler_verification_project/artifacts/zkp_attestation_public_values.json`
- `compiler_verification_project/artifacts/zkp_attestation_fixture_core.json`
- `compiler_verification_project/artifacts/zkp_attestation_fixture_compressed.json`
- `compiler_verification_project/artifacts/zkp_attestation_fixture_groth16.json`
- `compiler_verification_project/artifacts/zkp_attestation_proof_compressed.bin`
- `compiler_verification_project/artifacts/zkp_attestation_proof_groth16.bin`
- `compiler_verification_project/artifacts/zkp_attestation_groth16_verifier/groth16_vk.bin`

That bundle is exact at the same boundary as the selected compiler-family
summary and streamed lookup tail point-add leaf. The guest:

- re-hashes the public claim, leaf document, selected family summary,
  deterministic case corpus, and resource liveness certificate,
- replays the exact streamed lookup tail point-add contract on every public case,
- checks the affine group law for every case, and
- checks that the public claim summary matches the resource-engine totals,
  including derived owner-capacity obligations, before committing public values.

The no-ZKP public engine layer is the audit-first source of the current resource
claim. `public_candidate_materialized_circuit_manifest.json` stores the
run-length primitive rows and liveness/owner rows, then scans the full
materialized primitive stream for the macro reusable-chunk candidate. Every
emitted primitive operation has concrete operand wires, counted parent-wire
bindings, liveness interval, and total live-qubit value. The checked stream
covers `39,370,727` primitive operations over deterministic segments and binds
that stream with a full SHA-256 digest plus segment Merkle root.
`public_engine_manifest.json` binds the materialized stream alongside the
instruction, wire, schedule, owner-capacity, resource-term, semantic-boundary,
arithmetic-IR, QROAM, and phase-shell evidence. The materialized manifest also
executes representative flat operation indices through the same netlist API
used for full export, checking concrete operand wires, segment and liveness
bindings, QROAM target-domain widths, and a reduced schoolbook Cartesian
operand grid. Its strict primitive-completeness report requires every
run-length primitive row to expose gate-arity operand domains, so QROAM `ccx`,
arithmetic `ccx`, measurement, and phase rows all expand through the same
concrete-operand iterator. Its operand-parent binding report additionally
checks that every operand domain maps to counted live parent wires with matching
owners and enough parent-wire capacity. Its operand-source binding report
checks that every row binds to a concrete arithmetic block, lookup block, QROAM
segment, or phase-shell block, and that lookup-family aggregate counts still
match their block streams. The public engine manifest derives the public
non-Clifford count and public qubit count from `materialized_flat_netlist`;
reusable-resource totals are checked against those values as snapshots. The
materialized/public engine layer is generated from compiler parameters and
resource artifacts, not from the ZKP input, leaving ZKP as a downstream
publication wrapper rather than an upstream claim source.

`engine_completion_audit.json` is the current machine-readable answer to
"is this already the full Clifford-complete engine?". It is generated from the
materialized/public engine artifacts and passes only when the headline totals,
source binding, operand ownership, QROAM primitive cost, modular arithmetic IR
generation, semantic corpus, and tail auxiliary evidence are coherent. It
deliberately keeps `clifford_complete_goal_achieved = false` while the tail
macro in-place schedule and the final ZKP input bundle are not yet direct
single-engine products. Modular arithmetic is no longer a separate formula
source: the arithmetic lowering embeds `executable_modular_circuit_ir`, emits
the modular kernels from it, and the modular certificate consumes that same IR.
The selected tail macro is also no longer only prose plus a stage inventory:
`tail_macro_engine.json` expands the formula into a 23-operation field-kernel
stream, binds that stream's opcode histogram to the counted tail kernel, and
records that live-after liveness peaks at eight field values while the strict
operation-concurrent single-assignment slot schedule peaks at nine field-sized
lanes against the older three-slot tail budget. The engine now also emits a
cost-equivalent fused-output stream for `X3`, `Y3`, and `Z3`. That stream
replaces the six materialized pair-product lanes with three double-product
output rows, preserves the same tail non-Clifford total, reaches seven field
slots, replays on 110,082 non-infinity toy boundary pairs, checks 610
lookup-infinity no-op boundary pairs, and derives a seven-slot owner-capacity
ledger from the generated slot assignment. Its lowering contract explicitly
rejects the old unguarded `Y3` over `N` reuse with a concrete secp256k1
`M == 0` witness, then names the selected zero-lifted in-place `Y3` over `C`
field permutation required to stay at seven slots. The selected reuse counts
one `L == 0` guard qubit and 510 non-Clifford guard operations per tail, proves
that `L == 0` implies accumulator infinity on the valid non-infinity lookup
domain, and keeps lookup-infinity rows on the checked external bypass path.
`strict_replayed_tail_headline.json` promotes that replayed
seven-slot tail into the primary strict resource headline. The remaining
optimization target is reducing the tail below seven field slots and then
making the ZKP guest/input bind that same strict resource contract.
The same `tail_macro_engine.json` artifact now records an unpromoted semantic
six-slot candidate using the pair transforms `(I,F) -> (M,N)` and
`(E,K) -> (X3,Z3)`. Its determinant certificate proves the pair-output matrix
precondition `det = -Y3 != 0` on the checked secp256k1 boundary and the toy
boundary replay passes, but the candidate remains below the claims line until
the variable 2x2 in-place matrix has a finalized primitive resource lowering.
That artifact prevents the repository from silently promoting a materialized
boundary result into a stronger full-engine claim.

The checked JSON sidecars remain the audit-friendly source-of-truth inputs for
that bundle. The candidate directory records core, compressed, and Groth16
fixtures plus the shipped Groth16 proof bundle and verifying key. Those files
allow cheap local re-verification when `proof_status.py` reports they still bind
the current candidate input; after resource-certificate source changes, final
compressed/Groth16 rebuild is required before publishing proof freshness.
`python compiler_verification_project/scripts/proof_status.py` is the cheap
freshness preflight: it does not invoke a prover, and it reports whether the
checked proof layers still bind the current candidate input, public values,
proof binaries, and Groth16 verifier key.
For the macro reusable-chunk ZKP/publication wrapper, run
`python compiler_verification_project/scripts/verify_public_headline.py` to
validate the checked headline artifact, candidate input, public values,
source-document semantic hashes, fixture records, proof-binary digests, wrap
proof, and Groth16 verifier key from the checked branch state. The default
output is a compact blocker report; pass `--verbose` when a reviewer needs the
full per-check JSON payload. The macro candidate resource certificate also
carries executable interval liveness for
the reusable-chunk leaf, and the guest recomputes the peak live-qubit total from
those intervals before accepting the public values. It also validates the
embedded generated QROAM primitive certificate and modular arithmetic
certificate, so changes to those certificates stale the proof input rather than
silently changing the claim.

This is similar in shape to Google's disclosure model, but it proves a public
deterministic point-add corpus at the repository exact-family boundary rather
than a hidden primitive-gate Shor circuit.

## Modeled or non-exact layers

### A. Primitive-gate lookup realization

The repository does not lower lookup memory into a physical-layout qRAM or full
period-finding stack. It does now bind the counted lookup-data path to a
standard QROAM coordinate-stream primitive over the 32768-entry folded
coordinate domain and materializes the selected compiler-family primitive
stream used for the public non-Clifford and peak-live-qubit counts.

For the streamed lookup tail result, the table-controlled arithmetic boundary
is no longer free: `streamed_lookup_table_multiplier_resource.json` counts the
QROAMClean target and junk-register capacity in lookup workspace. The selected
public reusable-chunk point uses `K = 1` and 155-bit coordinate chunks, so each
chunk stream pays `65,536` non-Clifford operations, the live QROAM target is
`155` qubits, and the total counted lookup workspace is `173` qubits after the
18 folded-control qubits are included. The remaining boundary is below the
compiler-family primitive stream: arithmetic and lookup macro semantics are
still represented by generated primitive-operation IR and certificates rather
than by a physical-layout fault-tolerant schedule with routing, timing, and
error-correction overheads.

### B. Boundary no-op and cleanup

The central streamed lookup tail family handles the neutral lookup entry as a
boundary no-op instead of a leaf-internal XYZ select window. The hot leaf still
binds and traces the lookup-infinity predicate, and the public equivalence
corpus covers random, doubling, inverse, accumulator-infinity, and
lookup-infinity cases.

The repository still does not claim a primitive-gate proof below the named
boundary no-op and arithmetic macro contracts.

### C. Fully flattened Shor gate list

The mainline repository still provides a retained-window scaffold description,
not a single flat primitive-gate circuit for the complete period-finding stack.
The compiler subproject closes more of that gap by publishing an exact raw-32
whole-oracle family, but it still stops short of a globally optimized complete
primitive-gate Shor implementation.

### D. Modeled implementation hypotheses

Lower-exact budgeting artifacts are intentionally isolated in
`docs/research/MODELED_IMPLEMENTATION_HYPOTHESES.md`. They are not the
repository's headline result.

## Public baseline boundary

When this repository refers to the **public Google baseline**, it means the
rounded published lines stored in
`data/public_google_baseline.json` and mirrored into
`compiler_verification_project/artifacts/public_google_baseline_source.json`
and `compiler_verification_project/artifacts/family_frontier.json`:

- `1200 logical qubits / 90,000,000 non-Clifford`
- `1450 logical qubits / 70,000,000 non-Clifford`

These are the rounded public estimate lines from Babbush et al. 2026.

## Bottom line

Exact arithmetic leaf semantics: yes.

Exact lookup-contract semantics: yes.

Mainline exact primitive-gate lookup, cleanup, and full Shor flattening: no.

Exact compiler-family whole-oracle standard-QROM counts: yes, in `compiler_verification_project/`, but only for the named compiler families checked into that subproject.

Exact compiler-family SP1 attestation for one selected family claim and public deterministic point-add corpus: yes.

Standard-QROM compiler-family comparison against the public Google baseline: yes.

Clifford-complete full-Shor primitive-gate comparison against the public Google baseline: no.
