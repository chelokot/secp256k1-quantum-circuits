# Internal red-team review

This file lists the strongest objections a skeptical reader can raise and the
repository-supported answer to each one.

## Severity-ranked objections

| Objection | Severity if hidden | Repository-supported answer | Still open? |
|---|---:|---|---|
| “This is not a primitive-gate circuit because lookup is abstracted.” | High | True. The repository proves lookup contracts, not a primitive-gate lookup implementation. | Yes |
| “`mbuc_*` cleanup is not a primitive-gate verified coherent subcircuit.” | High | True. The repository checks basis-state semantics at the ISA boundary. | Yes |
| “The scaffold is metadata, not a full Shor gate list.” | High | True. The scaffold is replayed and checked for coherence, but it is not a single flattened gate list. | Yes |
| “The 880q / 31.0M headline depends on a backend model.” | High | True. Those totals are explicit modeled projections. | Yes |
| “Toy-curve proofs are not universal proofs over all prime fields.” | Medium | True. They are finite-model support for the family story. | Yes |
| “No primitive-gate qRAM or QROM is shipped.” | Medium | True. The repository keeps lookup as an explicit contract boundary. | Yes |
| “No end-to-end physical machine proof is shipped.” | Medium | True. Physical studies are separate transfer analyses. | Yes |

## Statements the repository can defend directly

- the optimized leaf's basis-state arithmetic semantics
- deterministic secp256k1 replay for that leaf
- exhaustive finite-model family checks on the toy-curve set
- deterministic scaffold replay for the retained-window schedule
- exact signed folded lookup-contract semantics
- modeled improvement over the public appendix baseline of Babbush et al. 2026

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
- “comparison against the public appendix baseline”

Unsafe:

- “hidden exact Google circuit”
- “primitive-gate complete proof”
- “final physical cost proven exactly”

## Bottom line

The repository is strongest when it is described exactly as a checked arithmetic
artifact plus explicit modeled layers, not as a solved end-to-end quantum
implementation.
