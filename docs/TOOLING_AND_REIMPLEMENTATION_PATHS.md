# External tooling and reimplementation paths

The core verifier stays intentionally small:

- Python standard library for verification logic
- optional matplotlib for figure regeneration

That keeps the trust path short. Stronger future checks can be added as
separate reimplementation or lowering paths.

## Most relevant external directions

### 1. Qualtran or similar IR re-expression

Use:

- represent the optimized leaf and scaffold in a more formal block structure
- attach richer resource accounting

### 2. QCEC or equivalent fragment checking

Use:

- check lowered fragments after conversion to a circuit IR
- add ancilla-aware equivalence checks outside the current core verifier

### 3. Independent language-stack reimplementation

Use:

- reproduce the artifact in another implementation stack such as Qrisp or Q#
- gain implementation diversity against verifier self-confirmation

## Why these are not core dependencies

The repository prioritizes:

- local reruns
- explicit machine-readable artifacts
- transparent verifier code

Heavy external tooling is therefore documented as a next path, not embedded as a
mandatory part of the current trust base.
