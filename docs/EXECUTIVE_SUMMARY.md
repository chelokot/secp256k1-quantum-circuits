# Executive summary

This repository publishes exact arithmetic artifacts for a secp256k1 point-add
stack and explicit modeled projections below that arithmetic boundary.

## What is in scope

- exact machine-readable point-add schedules at the kickmix ISA boundary
- deterministic secp256k1 replay audits
- exhaustive toy-curve family checks
- explicit retained-window scaffold metadata and deterministic scaffold replay
- explicit lookup contracts, including a signed folded variant
- modeled logical-qubit and non-Clifford projections

## Primary headline

The primary optimized projection stored in
`artifacts/out/resource_projection.json` is:

- **880 logical qubits**
- **29.163M non-Clifford** under the 2-channel lookup model
- **30.081M non-Clifford** under the conservative 3-channel lookup model

## Public baseline

The comparison baseline is the rounded public secp256k1 estimate from Babbush
et al. 2026, recorded in the same JSON file:

- **1200 logical qubits / 90.0M non-Clifford** for the low-qubit line
- **1450 logical qubits / 70.0M non-Clifford** for the low-gate line

This repository compares against those published estimates. It does not claim
recovery of any unpublished Google circuit.

## Signed lookup contract merged into the mainline

The repository's optimized mainline already includes the exact signed
two's-complement lookup-folding optimization. Its checked summaries report:

- **65,536 / 65,536** exhaustive words passed for the canonical secp256k1 base
- **15,906 / 15,906** multibase semantic samples passed

The supporting folded-lookup provenance file still records the merged totals and
their delta versus the pre-folding baseline:

- **29.163M non-Clifford** under the folded 2-channel line
- **30.081M non-Clifford** under the folded conservative 3-channel line

## What remains modeled

- lookup memory / qRAM lowering
- primitive-gate cleanup for `mbuc_*`
- full flat Shor gate stack
- backend lowering into logical-qubit and non-Clifford totals
- physical-machine transfer studies

## Safe one-paragraph description

This repository publishes exact ISA-level arithmetic artifacts for a
secp256k1-specialized point-add leaf, deterministic replay audits, exhaustive
finite-model checks, explicit retained-window scaffold metadata, an exact signed
lookup-contract variant, and modeled backend resource projections against the
published 2026 secp256k1 estimates of Babbush et al. 2026.
