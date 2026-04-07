# References and external pointers

This file lists the external works referenced by the repository and the role
they play.

## Direct public baseline

- Babbush et al. 2026, *Securing Elliptic Curve Cryptocurrencies against Quantum Vulnerabilities: Resource Estimates and Mitigations*

Role:

- source of the published secp256k1 resource estimates used as the repository's
  main comparison baseline

## Physical transfer and architecture context

- Cain et al. 2026, *Shor's algorithm is possible with as few as 10,000 reconfigurable atomic qubits*
- Gouzien et al. 2023, *Performance Analysis of a Repetition Cat Code Architecture: Computing 256-bit Elliptic Curve Logarithm in 9 Hours with 126133 Cat Qubits*
- Gu et al. 2025, *Resource analysis of Shor's elliptic curve algorithm with an improved quantum adder on a two-dimensional lattice*

Role:

- hardware and architecture context
- physical-transfer studies separate from the core logical artifact

## Logical ECDLP, arithmetic, and lookup references

- Roetteler et al. 2017, *Quantum resource estimates for computing elliptic curve discrete logarithms*
- Gidney 2019, *Windowed quantum arithmetic*
- Häner et al. 2022, *Space-time optimized table lookup for quantum circuits*
- Litinski 2024, *Quantum schoolbook multiplication with fewer Toffoli gates*
- Low, Zhu, Sundaram et al. 2024/2025, *A Unified Architecture for Quantum Lookup Tables*
- Luongo, Narasimhachar, Sireesh 2025, *Optimized circuits for windowed modular arithmetic with applications to quantum attacks against RSA*
- Luo et al. 2026, *Space-Efficient Quantum Algorithm for Elliptic Curve Discrete Logarithms with Resource Estimation*

Role:

- conceptual input for arithmetic, lookup, and alternate-branch directions

## Validation and tooling references

- Papa 2025, *Validation of Quantum Elliptic Curve Point Addition Circuits*
- Harrigan et al. 2024, *Expressing and Analyzing Quantum Algorithms with Qualtran*
- Dallaire-Demers et al. 2025, *Brace for impact: ECDLP challenges for quantum cryptanalysis*
- Polimeni, Seidel 2025, *End-to-end compilable implementation of quantum elliptic curve logarithm in Qrisp*
- MQT QCEC
- Microsoft QuantumEllipticCurves

Role:

- validation pressure
- external IR and equivalence-checking paths
- independent reimplementation directions

## Boundary

These references are not all dependencies of the core verifier. Some are direct
baselines, some are external context, and some are future-work directions.
