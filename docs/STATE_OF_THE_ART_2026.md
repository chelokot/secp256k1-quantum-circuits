# State of the art map (through 2026)

This file is a practical map of the external work most relevant to the current
repository.

## Four relevant directions

The external landscape splits into four directions:

1. prime-field logical ECDLP circuits
2. lookup and windowing techniques
3. verification and equivalence tooling
4. physical fault-tolerant architecture studies

The repository's strongest checked contribution is in direction 1, with an
exact arithmetic point-add layer. It also contains an exact lookup-contract
contribution in direction 2.

## Selected works and their role here

| Work | Main layer | Role in this repository |
|---|---|---|
| Roetteler et al. 2017 | logical ECDLP baseline | historical logical reference point |
| Gidney 2019 | lookup/windowing | conceptual basis for signed-window and lookup tradeoffs |
| Häner et al. 2022 | lookup backend | future lowering target |
| Gouzien et al. 2023 | physical architecture | alternate physical reference point |
| Harrigan et al. 2024 / Qualtran | tooling / IR | future external re-expression path |
| Litinski 2024 | arithmetic backend | future arithmetic-backend scenario input |
| Low, Zhu, Sundaram et al. 2024/2025 | lookup architecture | future lookup-lowering path |
| Luongo et al. 2025 | windowed arithmetic | reference for bounded lookup-side gains |
| Papa 2025 | validation | methodological support for strong checking discipline |
| Babbush et al. 2026 | public secp256k1 appendix baseline | main public baseline comparison |
| Cain et al. 2026 | neutral-atom architecture | approximate physical transfer study |
| Luo et al. 2026 | low-qubit ECDLP branch | alternate branch candidate |
| QCEC | equivalence tooling | future flattening target |

The machine-readable companion file is `results/literature_matrix.json`.

## Main repository takeaway from that map

The literature supports the following present-tense reading of the repository:

- the arithmetic layer is the strongest exact contribution,
- lookup work is meaningful when expressed as an exact contract,
- physical papers answer a different question than logical-artifact papers,
- heavy external tooling is best treated as a reimplementation path, not as a
  hidden dependency of the core verifier.

## Files that operationalize this map

- `docs/LOOKUP_FOLDING_RESEARCH_PASS.md`
- `docs/OPTIMIZATION_FRONTIERS.md`
- `docs/TOOLING_AND_REIMPLEMENTATION_PATHS.md`
- `docs/PHYSICAL_STACKS_AND_HARDWARE_CONTEXT.md`
- `results/literature_matrix.json`
