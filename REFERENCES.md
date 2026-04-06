# References and external pointers

This file lists the main external works and repositories that shaped the current
artifact and the later research passes.

## Papers

- Google / Babbush et al. 2026, *Securing Elliptic Curve Cryptocurrencies against Quantum Vulnerabilities: Resource Estimates and Mitigations*
- Cain et al. 2026, *Shor's algorithm is possible with as few as 10,000 reconfigurable atomic qubits*
- Luo et al. 2026, *Space-Efficient Quantum Algorithm for Elliptic Curve Discrete Logarithms with Resource Estimation*
- Papa 2025, *Validation of Quantum Elliptic Curve Point Addition Circuits*
- Luongo, Narasimhachar, Sireesh 2025, *Optimized circuits for windowed modular arithmetic with applications to quantum attacks against RSA*
- Khattar, Gidney et al. 2025, *The rise of conditionally clean ancillae for optimizing quantum circuits*
- Dallaire-Demers et al. 2025, *Brace for impact: ECDLP challenges for quantum cryptanalysis*
- Polimeni, Seidel 2025, *End-to-end compilable implementation of quantum elliptic curve logarithm in Qrisp*
- Harrigan et al. 2024, *Expressing and Analyzing Quantum Algorithms with Qualtran*
- Litinski 2024, *Quantum schoolbook multiplication with fewer Toffoli gates*
- Low, Zhu, Sundaram et al. 2024/2025, *A Unified Architecture for Quantum Lookup Tables*
- Roetteler et al. 2017, *Quantum resource estimates for computing elliptic curve discrete logarithms*
- Gidney 2019, *Windowed quantum arithmetic*
- Häner et al. 2022, *Space-time optimized table lookup for quantum circuits*
- Gouzien et al. 2023, *Performance Analysis of a Repetition Cat Code Architecture: Computing 256-bit Elliptic Curve Logarithm in 9 Hours with 126133 Cat Qubits*
- Gu et al. 2025, *Resource analysis of Shor's elliptic curve algorithm with an improved quantum adder on a two-dimensional lattice*

## Repositories / tooling

- MQT QCEC — quantum circuit equivalence checking with ancilla / garbage aware partial-equivalence flows
- Qualtran — open-source IR and resource-analysis tooling for quantum algorithms
- Microsoft QuantumEllipticCurves — Q# implementation and resource-estimation repo for elliptic-curve primitives

## Important boundary note

These references are used in several different ways:

1. as direct public baselines,
2. as motivation for new benchmark / validation layers,
3. as future-work targets for flattening, tooling, arithmetic backends, or
   alternate branches,
4. as conceptual guidance for the new lookup-focused research pass.

They are **not** all imported into the main exact verifier path.
That separation is deliberate.
