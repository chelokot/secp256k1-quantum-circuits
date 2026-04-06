# External tooling and reimplementation paths

This repository intentionally keeps its main verification path minimal:

- Python standard library for the verifier,
- optional matplotlib for figure regeneration.

That keeps the audit surface small, but it also means some stronger future checks
should happen **outside** the current core path.

## Best external next steps

### 1. Qualtran re-expression

Use case:
- represent the optimized leaf and scaffold in a more formal intermediate layer,
- attach richer resource accounting,
- and make block-structured compilation more explicit.

Why it matters:
- good fit for hierarchical algorithm description and resource inspection.

### 2. QCEC fragment checking

Use case:
- after lowering fragments to OpenQASM / primitive-level circuits,
- run equivalence checks with explicit ancilla / garbage handling.

Why it matters:
- this is probably the cleanest route from today's exact ISA-level artifact to a
  stronger flattened-fragment story.

### 3. Qrisp / Q# / external-stack reimplementation

Use case:
- independent re-expression in a separate language / compiler stack.

Why it matters:
- independent implementation diversity is one of the best anti-self-deception
  tools for complicated arithmetic circuits.

## Why these are not already merged here

Because the repository's current main strength is:

- a short trust path,
- transparent code,
- and easy local reruns.

Pulling all of those frameworks directly into the core repo would make the main
artifact less transparent, not more.

So the right move is:

- document the paths now,
- preserve the current minimal core,
- and treat heavyweight framework integration as a separate branch or follow-up
  repository.
