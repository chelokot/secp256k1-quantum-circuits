# Executive summary

## What this repository claims

This repository publishes an **exact ISA-level arithmetic reconstruction** for a
secp256k1 point-add leaf, a tested retained-window scaffold compatible with the
**public** Google appendix counts, deterministic secp256k1 audits, exhaustive
finite-model family checks on several prime-order toy curves, and an explicit
backend projection that beats the **public** Google appendix envelope.

## Main headline numbers

Optimized backend projection:

- **880 logical qubits**
- **30.998M non-Clifford** (2-lookup model)
- **32.833M non-Clifford** (3-lookup model)

## New result in this revision

This revision adds a **lookup-focused research pass** and corrects an internal
cost-model mistake.

New exact lookup-contract branch:

- signed 16-bit two's-complement lookup folding
- exhaustive secp256k1 audit: **65,536 / 65,536 pass**
- multibase semantic audit: **15,906 / 15,906 pass**

Modeled impact of that new branch:

- **29.163M** in the folded 2-channel line
- **30.081M** in the conservative folded 3-channel line
- about **5.9% to 8.4%** lower than the current modeled totals

## Why this matters

The repository is stronger after this pass for two reasons:

1. it no longer relies on an incorrect “lookup is 97% of the total” story,
2. it now contains one concrete, exact, audited lookup optimization instead of
   only heuristic lookup-frontier speculation.

## What remains modeled

Still modeled rather than primitive-gate proved:

- lookup memory / qRAM lowering,
- cleanup (`mbuc_*`),
- full flat Shor gate stack,
- backend lowering into logical-qubit and non-Clifford totals.

## Safe public wording

Good:

- “exact ISA-level arithmetic artifact”
- “exact signed lookup-contract improvement”
- “public-envelope comparison”
- “modeled backend projection”

Unsafe:

- “fully verified primitive-gate quantum circuit”
- “Google's hidden exact circuit”
- “final physical machine cost proven exactly”
