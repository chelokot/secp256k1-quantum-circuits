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
- checked standard-QROM lookup assessment marking the current bitwise-banked
  lookup lowering as a named boundary model rather than a proven arbitrary
  table-select primitive

The main open directions are therefore:

1. real arbitrary-table QROM/select lowering for the secp256k1 coordinate tables, or a proof of exploitable table structure
2. Clifford-complete arithmetic and lookup micro-expansion below the shipped generated compiler-family operation inventories
3. external equivalence checking below the named arithmetic, lookup, and phase-shell blocks
4. flatter end-to-end Shor fragments with external equivalence checking

## What would be overclaim

It would be inaccurate to describe the repository as already having:

- a Clifford-complete primitive-gate lookup implementation,
- a standard-QROM primitive-circuit realization of the `23,912,611 / 1,587`
  named-boundary result,
- a primitive-gate cleanup proof,
- a fully flattened Shor circuit,
- a globally optimal primitive-gate total.

## Separate hypothesis layer

Lower-exact budgeting and implementation hypotheses are isolated in
`docs/research/MODELED_IMPLEMENTATION_HYPOTHESES.md`.
