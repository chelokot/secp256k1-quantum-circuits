# Optimization frontiers

This file describes which exact parts of the repository are already checked and
which implementation gaps remain open.

## Checked exact layers

- ISA-level secp256k1 point-add leaf semantics
- retained-window scaffold metadata and replay
- signed lookup-folding contract semantics
- exact ISA-level coherent flag cleanup
- exact arithmetic-kernel generated primitive-operation inventories for the named compiler family
- exact lookup-family generated primitive-operation inventories for the named compiler families
- exact phase-shell generated operation inventories for the named full-register and semiclassical inverse-QFT families
- compositional FT-style call graphs and leaf sigma for the named compiler
  families
- independent exact whole-oracle recount over the FT IR leaf sigma
- internal subcircuit-equivalence witnesses for traced ISA arithmetic/flag
  opcodes, lowered lookup families, the cleanup window, and generated
  whole-oracle composition
- exact compiler-family raw-32 whole-oracle frontier
- exact slot allocation and exact phase-shell lowering
- checked standard-QROM lookup assessment binding the selected family to a
  standard-QROAM coordinate-stream primitive rather than the rejected
  bitwise-banked path-select model
- unpromoted semantic six-slot tail candidate in `tail_macro_engine.json`,
  using `(I,F) -> (M,N)` and `(E,K) -> (X3,Z3)` pair transforms with checked
  determinant/replay evidence
- repo-wide baseline gate in `current_baseline_status.json`, which keeps the
  `36,973,222 / 1,968` strict candidate and the `36,973,222 / 2,222`
  guard-corrected hardening target out of accepted physical-baseline status
  until every primitive-stream and liveness blocker is closed

The main open directions are therefore:

1. promote the guard-corrected `2,222` capacity into the same scheduled
   primitive liveness model or prove a concrete alias/no-ancilla guard
   construction
2. replace the remaining synthetic modular-arithmetic scratch rows with a
   physical compute-consume-cleanup primitive stream
3. primitive resource lowering for the six-slot variable 2x2 in-place output matrix
4. Clifford-complete arithmetic and lookup micro-expansion below the shipped generated compiler-family operation inventories
5. external equivalence checking below the named arithmetic, lookup, and phase-shell blocks
6. flatter end-to-end Shor fragments with external equivalence checking

## What would be overclaim

It would be inaccurate to describe the repository as already having:

- a Clifford-complete primitive-gate full-oracle implementation,
- an accepted Clifford-complete physical baseline at either `36,973,222 /
  1,968` or `36,973,222 / 2,222`,
- a standard-QROM primitive-circuit realization with lower cost than the
  conservative `36,973,222 / 2,222` hardening target,
- a primitive-gate cleanup proof,
- a fully flattened Shor circuit,
- a globally optimal primitive-gate total.

## Separate hypothesis layer

Lower-exact budgeting and implementation hypotheses are isolated in
`docs/research/MODELED_IMPLEMENTATION_HYPOTHESES.md`.
