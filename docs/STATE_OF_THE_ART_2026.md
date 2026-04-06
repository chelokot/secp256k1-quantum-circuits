# State of the art map (through 2026)

This file is a curated map of the external work most relevant to this
repository.

The goal is practical:

1. identify the strongest prior art,
2. decide what can be absorbed honestly,
3. and avoid pretending that all layers of the problem are already solved.

## Executive verdict

The literature pressure now comes from four directions:

1. **prime-field logical ECDLP circuits**
2. **lookup / windowed arithmetic engineering**
3. **formal validation and equivalence tooling**
4. **physical fault-tolerant architecture studies**

The current repository is strongest in direction (1) at the exact kickmix
ISA-level arithmetic layer.

This revision also adds a concrete result in direction (2): an exact signed
lookup-folding contract with exhaustive and sampled audits.

## Selected works and what they mean here

| Work | Main layer | What it contributes | How this repo uses it |
|---|---|---|---|
| Roetteler et al. 2017 | logical prime-field baseline | explicit Toffoli-network EC discrete-log baseline | historical anchor only |
| Gidney 2019 | lookup/window theory | explicit windowed arithmetic and lookup tradeoffs | conceptual basis for lookup-layer reshaping |
| Haner et al. 2022 | lookup backend theory | space-time optimized table lookup | future lowering path |
| Qualtran 2024 | tooling / IR | resource modeling and explicit algorithm representation | future external reimplementation path |
| Litinski 2024 | arithmetic backend | cheaper schoolbook multipliers | scenario translation only for now |
| Low/Zhu 2024 | lookup architecture | unified lookup tradeoff framework | future lookup-lowering path |
| Luongo et al. 2025 | windowed modular arithmetic | modest but real lookup/unlookup wins | sanity check for bounded lookup improvements |
| Papa 2025 | validation | why EC point-add circuits need aggressive checking | methodological pressure integrated into repo docs/tests |
| Google/Babbush 2026 | public secp256k1 baseline | public envelope and public appendix framing | main baseline comparison |
| Cain 2026 | neutral-atom architecture | physical-stack transfer study | integrated as approximate hardware transfer |
| Luo 2026 | low-qubit branch | space-efficient inversion-driven ECDLP branch | future alternate branch |
| QCEC | equivalence tooling | fragment-level equivalence checking after lowering | future flattening target |

The machine-readable version lives in:

- `results/literature_matrix.json`

## What the repo now knows with higher confidence

### 1. The old “lookup is 97% of the budget” story was wrong

The corrected accounting shows that arithmetic dominates the current modeled
total and lookup is a smaller but still important secondary share.

This changes how the literature should be read:

- arithmetic papers remain central,
- lookup papers remain relevant but bounded,
- and combined changes are the most plausible route to another large jump.

### 2. Lookup work can still be integrated honestly

This revision adds a concrete example:

- a signed two's-complement lookup-folding contract,
- exhaustive audit over all 65,536 raw 16-bit words for one secp256k1 base,
- 15,906 additional multibase semantic samples,
- modeled total reduction of about 5.9% to 8.4% depending on channel model.

### 3. Validation pressure is real

The repo now benefits from a stronger story around:

- benchmark ladders,
- explicit boundary files,
- red-team notes,
- and dedicated lookup-contract audits.

### 4. Physical-stack papers and logical-stack papers are still orthogonal

Cain and related architecture papers do not invalidate the exact ISA-level work.
They answer a different question:

- what physical machine assumptions do to runtime and qubit counts.

The right use remains compositional:

- logical artifact first,
- physical transfer second.

## What was added in response to this literature review

This pass extends the repository with:

- `docs/COST_MODEL_CORRECTION.md`
- `docs/LOOKUP_FOLDING_RESEARCH_PASS.md`
- updated `docs/OPTIMIZATION_FRONTIERS.md`
- updated `docs/LITERATURE_INTEGRATION_DECISIONS.md`
- updated `results/literature_matrix.json`
- updated research summaries and figures

## Blunt interpretation

The literature now forces more discipline.

This repo is stronger after this pass not because it found another miracle 2x
headline, but because it:

- corrected a real internal modeling error,
- added one exact, auditable lookup optimization,
- and aligned its frontier story with what the evidence now actually supports.
