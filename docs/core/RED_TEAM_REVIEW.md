# Internal red-team review

This file lists the strongest objections a skeptical reader can raise and the
repository-supported answer to each one.

## Severity-ranked objections

| Objection | Severity if hidden | Repository-supported answer | Still open? |
|---|---:|---|---|
| “This is not a primitive-gate circuit because lookup is abstracted.” | High | Still true at the primitive-gate layer, but the lookup boundary is explicit: the folded contract is machine-readable and audited exhaustively for a canonical secp256k1 base plus deterministic multibase samples. | Yes |
| “`mbuc_*` cleanup is not a primitive-gate verified coherent subcircuit.” | High | True. The repository checks basis-state semantics at the ISA boundary. | Yes |
| “The scaffold is metadata, not a full Shor gate list.” | High | This is true for the mainline, and the compiler subproject publishes an exact fully quantum raw-32 oracle family with explicit whole-oracle counts. It is still not a globally optimized complete Shor implementation. | Partly |
| “The exact compiler frontier still does not reconstruct a hidden Google circuit.” | High | True. The repository compares against Google's public rounded lines, not against an unpublished circuit. | Yes |
| “Toy-curve proofs are not universal proofs over all prime fields.” | Medium | True. They are finite-model support for the family story. | Yes |
| “No primitive-gate qRAM or QROM is shipped.” | Medium | True. The repository keeps lookup as an explicit contract boundary. | Yes |
| “No end-to-end physical machine proof is shipped.” | Medium | True. Physical studies are separate transfer analyses. | Yes |

## Statements the repository can defend directly

- the optimized leaf's basis-state arithmetic semantics
- deterministic secp256k1 replay for that leaf
- exhaustive finite-model family checks on the toy-curve set
- deterministic scaffold replay for the retained-window schedule
- exact signed folded lookup-contract semantics together with machine-readable contract-field validation
- exact whole-oracle counts for named compiler families in the compiler subproject
- exact qubit tightening from slot allocation and semiclassical phase-shell accounting in that subproject
- exact comparison of those compiler-family counts against Google's published
  2026 secp256k1 baseline lines

## Statements the repository should not make

- “fully verified globally optimal primitive-gate quantum circuit”
- “reconstruction of an unpublished Google circuit”
- “exact final physical machine cost”
- “primitive-gate qRAM already proved for every compiler family”

## Publication-safe wording

Safe:

- “exact ISA-level arithmetic artifact”
- “explicit lookup contract”
- “tested retained-window scaffold”
- “modeled implementation hypothesis note”
- “comparison against Google's published 2026 secp256k1 estimates”

Unsafe:

- “hidden exact Google circuit”
- “primitive-gate complete proof”
- “final physical cost proven exactly”

## Bottom line

The repository has two strengths: a checked arithmetic mainline and a separate
exact compiler-family oracle subproject. It is not a solved end-to-end
globally optimal primitive-gate implementation, but the statement “nothing
below ISA is exact” does not describe the checked-in artifacts accurately.
