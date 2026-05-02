# Claims and boundaries

This file defines the strongest claims supported by the checked-in artifacts.

## Strongest defensible claim

The repository publishes exact kickmix-ISA arithmetic schedules for a
secp256k1-specialized point-add leaf and explicit retained-window scaffold
metadata, together with deterministic audits, finite-model checks, and a
separate exact compiler-family oracle subproject that closes the
classical-tail-elision gap for a fully quantum raw-32 schedule. It now also
ships an SP1 attestation bundle for one selected standard-QROM family claim at
that same boundary. The current `23,953,656 / 5,652` result is a standard-QROM
compiler-family result at the counted lookup boundary. It is not a
below-1700-qubit standard-QROM result.

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
- `compiler_verification_project/artifacts/zkp_attestation_public_values.json`
- `compiler_verification_project/artifacts/zkp_attestation_fixture_core.json`
- `compiler_verification_project/artifacts/zkp_attestation_fixture_compressed.json`
- `compiler_verification_project/artifacts/zkp_attestation_fixture_groth16.json`
- `compiler_verification_project/artifacts/zkp_attestation_proof_compressed.bin`
- `compiler_verification_project/artifacts/zkp_attestation_proof_groth16.bin`
- `compiler_verification_project/artifacts/zkp_attestation_groth16_verifier/groth16_vk.bin`

That bundle is exact at the same boundary as the selected compiler-family
summary and streamed lookup tail point-add leaf. The guest:

- re-hashes the public claim, leaf document, selected family summary, and
  deterministic case corpus,
- replays the exact streamed lookup tail point-add contract on every public case,
- checks the affine group law for every case, and
- reconstructs the claimed full-oracle non-Clifford and logical-qubit totals
  from the selected family summary before committing public values.

The checked JSON sidecars remain the audit-friendly source-of-truth inputs for
that bundle. The core, compressed, and Groth16 fixtures are checked proof-layer
outputs for the same public claim, and the shipped Groth16 proof bundle plus
verifying key allow cheap local re-verification from the repository without
rebuilding the large vk-specific dev artifact tree.

This is similar in shape to Google's disclosure model, but it proves a public
deterministic point-add corpus at the repository exact-family boundary rather
than a hidden primitive-gate Shor circuit.

## Modeled or non-exact layers

### A. Primitive-gate lookup realization

The repository does not lower lookup memory into a bit-for-bit
Clifford-complete qRAM or full Shor circuit. It does now bind the counted
lookup-data path to a standard QROAM coordinate-stream primitive over the
32768-entry folded coordinate domain.

For the streamed lookup tail result, the table-controlled arithmetic boundary
is no longer free: `streamed_lookup_table_multiplier_resource.json` counts the
QROAMClean full-coordinate target and junk-register capacity in lookup
workspace and adds `7,951` non-Clifford operations for every 256-bit coordinate
stream consumed by `field_mul_lookup_*` or the streamed tail. The remaining boundary is
that the repository does not ship a Clifford-complete flattened netlist for
every arithmetic and lookup block.

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
`compiler_verification_project/artifacts/family_frontier.json`:

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
