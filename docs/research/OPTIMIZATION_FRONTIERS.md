# Optimization frontiers

This file describes which exact parts of the repository are already checked and
which implementation gaps remain open.

## Checked exact layers

- ISA-level secp256k1 point-add leaf semantics
- retained-window scaffold metadata and replay
- signed lookup-folding contract semantics
- exact ISA-level coherent flag cleanup
- exact arithmetic-kernel stage/block inventories for the named compiler family
- internal subcircuit-equivalence witnesses for traced ISA arithmetic/flag
  opcodes, lowered lookup families, the cleanup window, and generated
  whole-oracle composition
- exact compiler-family raw-32 whole-oracle frontier
- exact slot allocation and exact phase-shell family accounting

The main open directions are therefore:

1. explicit primitive-gate lookup realization for the named compiler families
2. Clifford-complete arithmetic micro-expansion and external equivalence checking below the named arithmetic and lookup blocks
3. flatter end-to-end Shor fragments with external equivalence checking

## What would be overclaim

It would be inaccurate to describe the repository as already having:

- a primitive-gate lookup implementation,
- a primitive-gate cleanup proof,
- a fully flattened Shor circuit,
- a globally optimal primitive-gate total.

## Separate hypothesis layer

Lower-exact budgeting and implementation hypotheses are isolated in
`docs/research/MODELED_IMPLEMENTATION_HYPOTHESES.md`.
