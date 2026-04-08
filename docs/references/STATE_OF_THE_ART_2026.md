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
| Bos et al. 2014 | fixed-base complete masking | exception-management reference for fixed-base Weierstrass paths |
| Gossett 1998 | carry-save arithmetic | negative reference for depth-vs-qubits tradeoffs that grow workspace too aggressively |
| Bernstein et al. 2008 / Twisted Edwards | alternative curve models | torsion-profile filter for base-field Edwards-style rewrites |
| Renes, Costello, Batina 2015 | complete short-Weierstrass arithmetic | current complete leaf class and completeness baseline |
| Massolino, Renes, Batina 2016 | hardware scheduling of complete formulas | evidence that the current complete formula class remains competitive in hardware-style settings |
| Gidney 2019 | lookup/windowing | conceptual basis for signed-window and lookup tradeoffs |
| Khattar, Gidney 2024 | comparator / ancilla tradeoffs | predicate-layer reference for low-ancilla zero/equality tests |
| Smith 2015 | x-only / pseudomultiply-recover | structural state-reduction reference for short-Weierstrass scalar multiplication |
| Häner et al. 2020 | quantum affine arithmetic | whole-arithmetic rewrite reference for affine/inversion tradeoffs |
| Goundar, Joye, Miyaji 2010 | co-Z / ladder arithmetic | long-horizon whole-algorithm rewrite reference |
| Hamburg 2020 | complete short-Weierstrass ladders | long-horizon whole-algorithm rewrite reference |
| Bernstein et al. 2015 / Twisted Hessian | alternative curve models | torsion-profile filter for base-field Hessian-style rewrites |
| Sedlacek et al. 2021 | exceptional-point analysis | negative evidence against incomplete Jacobian/xyzz drop-in paths |
| GLV / GLS scalar decomposition literature | endomorphism-based scalar multiplication | potential whole-oracle rewrite direction with different lookup / doubling tradeoffs |
| Häner et al. 2022 | lookup backend | future lowering target |
| Gouzien et al. 2023 | physical architecture | alternate physical reference point |
| Harrigan et al. 2024 / Qualtran | tooling / IR | future external re-expression path |
| Litinski 2024 | arithmetic backend | future arithmetic-backend scenario input |
| Low, Zhu, Sundaram et al. 2024/2025 | lookup architecture | future lookup-lowering path |
| Luongo et al. 2025 | windowed arithmetic | reference for bounded lookup-side gains |
| Papa 2025 | validation | methodological support for strong checking discipline |
| Vandaele 2026 | comparator circuits | predicate-layer reference for minimal-qubit compare-to-constant subroutines |
| Babbush et al. 2026 | published secp256k1 resource estimates | main public baseline comparison |
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

- `docs/research/LOOKUP_FOLDING_RESEARCH_PASS.md`
- `docs/research/ARITHMETIC_ARCHITECTURE_INVESTIGATION.md`
- `docs/research/OPTIMIZATION_FRONTIERS.md`
- `docs/references/TOOLING_AND_REIMPLEMENTATION_PATHS.md`
- `docs/references/PHYSICAL_STACKS_AND_HARDWARE_CONTEXT.md`
- `results/literature_matrix.json`
