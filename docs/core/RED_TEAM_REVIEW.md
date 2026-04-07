# Internal red-team review

This file lists the strongest objections a skeptical reader can raise and the
repository-supported answer to each one.

## Severity-ranked objections

| Objection | Severity if hidden | Repository-supported answer | Still open? |
|---|---:|---|---|
| “This is not a primitive-gate circuit because lookup is abstracted.” | High | Still true at the primitive-gate layer, but the lookup objection is narrower than before: the folded contract is now machine-readable and audited exhaustively for a canonical secp256k1 base plus deterministic multibase samples. | Yes |
| “`mbuc_*` cleanup is not a primitive-gate verified coherent subcircuit.” | High | True. The repository checks basis-state semantics at the ISA boundary. | Yes |
| “The scaffold is metadata, not a full Shor gate list.” | High | True. The scaffold is replayed and checked for coherence, but it is not a single flattened gate list. | Yes |
| “The 880q / 22.38M headline depends on a backend model.” | High | True. Those totals are explicit modeled projections derived from structural artifacts plus a backend-model bundle. They no longer inherit a hidden legacy leaf calibration constant, but they are still not a primitive-gate lowering. | Yes |
| “Toy-curve proofs are not universal proofs over all prime fields.” | Medium | True. They are finite-model support for the family story. | Yes |
| “No primitive-gate qRAM or QROM is shipped.” | Medium | True. The repository keeps lookup as an explicit contract boundary. | Yes |
| “No end-to-end physical machine proof is shipped.” | Medium | True. Physical studies are separate transfer analyses. | Yes |

## Statements the repository can defend directly

- the optimized leaf's basis-state arithmetic semantics
- deterministic secp256k1 replay for that leaf
- exhaustive finite-model family checks on the toy-curve set
- deterministic scaffold replay for the retained-window schedule
- exact signed folded lookup-contract semantics together with machine-readable contract-field validation
- modeled improvement over Google's published 2026 secp256k1 estimates from
  Babbush et al. 2026 using a derived structural pipeline rather than a standalone headline table

## Statements the repository should not make

- “fully verified primitive-gate quantum circuit”
- “reconstruction of an unpublished Google circuit”
- “exact final physical machine cost”
- “primitive-gate qRAM already proved”

## Publication-safe wording

Safe:

- “exact ISA-level arithmetic artifact”
- “explicit lookup contract”
- “tested retained-window scaffold”
- “modeled backend projection”
- “comparison against Google's published 2026 secp256k1 estimates”

Unsafe:

- “hidden exact Google circuit”
- “primitive-gate complete proof”
- “final physical cost proven exactly”

## Bottom line

The repository is strongest when it is described exactly as a checked arithmetic
artifact plus explicit modeled layers, not as a solved end-to-end quantum
implementation.
