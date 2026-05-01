# Internal red-team review

This file lists the strongest objections a skeptical reader can raise and the
repository-supported answer to each one.

## Severity-ranked objections

| Objection | Severity if hidden | Repository-supported answer | Still open? |
|---|---:|---|---|
| “This is not a primitive-gate circuit because lookup is abstracted.” | High | Still true at the Clifford-complete primitive-gate layer, but the lookup stack is explicit: the folded contract is machine-readable and audited exhaustively for a canonical secp256k1 base plus deterministic multibase samples, and the compiler project lowers named lookup families into generated operation inventories below that contract. | Yes |
| “The cleanup path is still only an unchecked abstraction.” | High | False at the ISA boundary. The shipped one-bit flag cleanup pair is machine-checked on deterministic secp256k1 cases: the metadata bit is extracted into `f_lookup_inf`, used by the neutral-entry select path, and then uncomputed by replaying the same flag source. | Partly |
| “The scaffold is metadata, not a full Shor gate list.” | High | This is true for the mainline, and the compiler subproject publishes an exact fully quantum raw-32 oracle family with explicit whole-oracle counts. It is still not a globally optimized complete Shor implementation. | Partly |
| “The exact compiler frontier still does not reconstruct a hidden Google circuit.” | High | True. The repository compares against Google's public rounded lines, not against an unpublished circuit. | Yes |
| “Toy-curve proofs are not universal proofs over all prime fields.” | Medium | True. They are finite-model support for the family story. | Yes |
| “No primitive-gate qRAM or QROM is shipped.” | Medium | Partly. The repository now binds the counted lookup-data path to a standard QROAM coordinate-stream primitive, but it still does not ship a bit-for-bit Clifford-complete full-oracle netlist. | Partly |
| “The previous streamed lookup model only counted bitwise path controls.” | High | Closed for the counted family. `standard_qrom_lookup_assessment.json` records the selected standard-QROAM coordinate-stream primitive and rejects the old bitwise-banked path-select model. | No |
| “No end-to-end physical machine proof is shipped.” | Medium | True. The repository ships exact logicalCounts, explicit Microsoft Resource Estimator target profiles, recorded estimator outputs, and a separate Cain transfer study, but it does not ship a hardware-independent theorem-proved physical realization. | Yes |

## Statements the repository can defend directly

- the optimized leaf's basis-state arithmetic semantics
- the shipped one-bit ISA cleanup pair for the neutral-entry control path
- deterministic secp256k1 replay for that leaf
- exhaustive finite-model family checks on the toy-curve set
- deterministic scaffold replay for the retained-window schedule
- exact signed folded lookup-contract semantics together with machine-readable contract-field validation
- exact standard-QROM whole-oracle counts for named compiler families in the compiler subproject
- exact qubit tightening from slot allocation and exact phase-shell lowering in that subproject
- exact comparison of those compiler-family counts against Google's published
  2026 secp256k1 baseline lines

## Statements the repository should not make

- “fully verified globally optimal primitive-gate quantum circuit”
- “reconstruction of an unpublished Google circuit”
- “exact final physical machine cost”
- “Clifford-complete qRAM/full-Shor netlist already proved for every compiler family”

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
