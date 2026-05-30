# secp256k1 Quantum Circuit Lab

This is a personal educational web subproject for learning the quantum-circuit
and resource-accounting ideas behind this repository.

It is intentionally built as a paged interactive course, not a static report or
one giant lab dump. Each lesson has its own hash route such as `/#qubit` or
`/#ecdlp`, focused explanatory text, and only the labs that belong to that
stage of the learning path:

- concept lessons from qubits to secp256k1 resource contracts
- a zero-to-contributor learning path that groups prerequisites into quantum
  substrate, attack algorithm, circuit engine, and audit/contribution stages
- an end-to-end circuit stack map from phase estimation to proof boundary
- toy gate programming and qubit-state steering
- an executable two-qubit state-vector simulator for amplitudes,
  probabilities, interference, and entanglement
- a stabilizer-vs-magic wheel connecting Clifford moves, T gates, and
  non-Clifford accounting
- a tiny quantum DSL editor for primitive netlist practice
- an opcode-lowering microscope that expands one source operation into primitive
  rows, operands, owners, liveness intervals, and non-Clifford cost
- reversible cleanup and uncompute puzzle
- phase-estimation and inverse-QFT intuition
- a Fourier lens lab that shows inverse QFT as phase-slope alignment and
  destructive interference over candidate output labels
- a phase-kickback hidden-period lab showing how an ECDLP oracle output becomes
  a Fourier slope over `(a,b)` inputs
- a windowed attack scaffold lab connecting 512 phase bits, 32 raw windows,
  retained point-add leaves, classical tail elisions, and Google's public
  16-window-size / 28-retained-additions comparison line
- a whole-oracle resource composer that reconstructs the strict non-Clifford
  and peak-logical-qubit formulas from checked artifacts, including the
  difference between accumulated gate work and reused peak workspace
- finite-field elliptic-curve point addition on a toy curve
- affine/projective coordinate equivalence and field-slot tradeoff lab
- a reversible overwrite lab for seeing when in-place slot reuse is a
  permutation contract rather than destructive assignment
- bit-level partial-product multiplication grid
- real modular-accumulator lowering metrics from checked artifacts
- a scratch lifecycle lab for the current `721,406` abandoned temporary-AND
  blocker, including the `720,896` partial-product cleanup rows and `510`
  zero-lift guard source-control gap
- point-add boundary debugger for random, doubling, inverse, accumulator-infinity,
  and lookup-infinity equivalence cases
- QROAM table-selection accounting
- logical-to-physical qubit bridge for toy error-correction overhead intuition
- a repetition-code toy decoder showing code distance, majority vote, and
  logical failure probability before any hardware-specific layout claim
- non-Clifford magic-budget lab for seeing gate pressure separately from qubits
- no-free-wire owner/liveness invariant checks
- owner-capacity assignment game
- a mini resource-engine exercise that derives peak qubits from live intervals
- a schedule optimizer lab for reducing peak live qubits by moving cleanup
  earlier
- an optimization mission over the checked hybrid bridge candidate landscape
- a contributor mission board that turns course skills into evidence-backed
  repo tasks
- a course coverage audit that maps the original personal education request to
  concrete lessons, labs, boundaries, and tests
- an artifact atlas that maps checked JSON paths to the audit questions they
  answer and the claims they do not prove alone
- a result confidence ladder for practicing when a claim can be called a
  hypothesis, candidate, consequence, proof-wrapper statement, or accepted
  baseline
- field-slot and guard-gap liveness visualizations
- current repo candidate numbers synced from checked artifacts
- a baseline explorer that separates Google public lines, older repo reference
  boundaries, current candidates, and non-promoted consequences
- a baseline tradeoff landscape for comparing `1,200q / 90M`, `1,450q / 70M`,
  historical repo reference rows, the current strict candidate, and the
  guard-corrected hardening target without promoting any unaccepted row
- an accepted-baseline gate that shows why `2,222q` is still blocked until every
  release blocker is closed against the same executable artifact
- a claim-audit drill for classifying result statements before repeating them
- a ZKP boundary lab that separates smoke proof corpus size, stale proof
  fixtures, compressed/Groth16 verification, and physical-baseline readiness
- Playwright end-to-end tests for the learning flow

## Stack

- Vite + React + TypeScript for fast iteration
- D3 for custom visualization scales
- lucide-react for compact interface icons
- Playwright for browser-level checks

## Commands

```bash
npm install
npm run dev
npm run build
npm run test:e2e
npm run audit:screenshots
```

`npm run sync:data` reads the parent repository artifacts and rewrites
`src/generated/project-data.json`. Do not edit that generated file by hand.

`npm run audit:screenshots` captures the first viewport for every lesson into
`education/visual-audit/` with a `manifest.json`. Use it before broad content
changes so the full course can be reviewed as rendered pages, not just source
text.

## Current course boundary

This first version teaches the core mental model and the current repo status:
there is no accepted Clifford-complete physical baseline yet; `1,968q` is the
strict candidate, and `2,222q` is the guard-corrected no-alias consequence. The
next course expansion should add deeper proof public-value tracing, guided
engine implementation exercises, and more step-by-step visual replay of the
real 256-bit modular multiplication stream.
