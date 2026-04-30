> [!WARNING]
> This repository was created entirely with ChatGPT 5.4 Pro. I personally have
> only surface-level knowledge of quantum computing, so I cannot audit it in
> depth myself. I have tried to make it as transparent, tested, and
> reproducible as possible. Anyone with domain expertise is strongly encouraged
> to review this repository and open issues or pull requests.

# secp256k1 quantum attack circuits

secp256k1 is the elliptic curve used by Bitcoin and other cryptocurrency
systems, and a sufficiently powerful fault-tolerant quantum attack on it would
in principle recover private keys from public keys and signatures.

On March 31, 2026, Google Research published a
[whitepaper](https://quantumai.google/static/site-assets/downloads/cryptocurrency-whitepaper.pdf)
and
[blog post](https://research.google/blog/safeguarding-cryptocurrency-by-disclosing-quantum-vulnerabilities-responsibly/)
reporting new secp256k1 quantum ECDLP resource estimates and arguing that the
risk horizon for fault-tolerant attacks may be closer than many earlier
timelines assumed. Google reported rounded estimates of under 1,200 logical
qubits and 90 million non-Clifford gates, or under 1,450 logical qubits and 70
million non-Clifford gates, for secp256k1, but did not publish the full
underlying circuit. Instead, they published a zero-knowledge proof attesting
that such a circuit exists.

This repository began as an attempt to reproduce that result from the public
material alone. ChatGPT 5.4 Pro was used first to construct auditable
secp256k1 circuit artifacts consistent with Google's published resource lines,
and then to search for stronger secp256k1-specific optimizations.

## Content

This repository has **three exact-first layers** and one quarantined
hypothesis note.

1. The primary `artifacts/` mainline publishes exact ISA-level secp256k1
   arithmetic artifacts.
2. The root-level `compiler_verification_project/` subproject completes the
   schedule into a fully quantum raw-32 oracle and publishes exact whole-oracle
   counts for named compiler families.
3. The checked-in `compiler_verification_project/zkp_attestation/` workspace
   packages one selected exact-family claim into an SP1 attestation bundle with
   hashed input documents, a deterministic public point-add corpus, checked
   core/compressed/Groth16 fixtures, and a repo-contained Groth16 verifier
   bundle.
4. Lower-exact implementation ideas are isolated in
   `docs/research/MODELED_IMPLEMENTATION_HYPOTHESES.md` and are not used for
   top-level claims, tests, or headline comparisons.

The repository is strongest at the arithmetic ISA boundary, and the compiler
project tightens one important gap by turning
“leaf + scaffold + contract” into a checked exact compiler-family oracle with
exact schedule completion, exact lookup-family choice, exact slot allocation,
and explicit phase-shell families. The attestation layer then turns one
selected exact-family claim into a machine-checked proof artifact without
claiming a primitive-gate full-Shor witness.

## Main results

### Compiler + verification subproject

The root-level `compiler_verification_project/` is the repository's strongest
exact layer below the ISA boundary. Its checked-in central whole-oracle result
is:

- **central exact family:** `22,753,831 non-Clifford`, `1,586 logical qubits`

Those numbers are exact for the chosen compiler family, not a claim of global
optimality. The family uses a fully bitwise banked unary QROM decode with
measured uncompute, an exact semiclassical-QFT phase shell, and the executable
interface-borrowed point-add leaf. The leaf reuses the `lookup_x` interface lane
as arithmetic scratch only after its coordinate value is consumed; that handoff
is checked by the interface resource-ownership invariant in the compiler
verification summary.

Against Google's published 2026 secp256k1 baseline, the central exact result is:

- **3.9554x** lower in non-Clifford cost than the public low-qubit line
- **3.0764x** lower in non-Clifford cost than the public low-gate line
- **386 qubits above** the public low-qubit line
- **136 qubits above** the public low-gate line

### SP1 attestation layer

The repository now also ships a Google-like attestation at the exact
compiler-family boundary. The checked artifacts bind:

- a hashed `interface_borrowed_leaf.json` witness leaf
- a hashed selected family summary in
  `compiler_verification_project/artifacts/zkp_attestation_family.json`
- a hashed deterministic public point-add case corpus in
  `compiler_verification_project/artifacts/zkp_attestation_cases.json`

The SP1 guest re-checks semantic hashes for those embedded typed documents,
replays the leaf on every public case, checks the affine group law, and
reconstructs the claimed exact non-Clifford and logical-qubit formulas before
committing public values. The checked core fixture is
`compiler_verification_project/artifacts/zkp_attestation_fixture_core.json`,
the checked compressed fixture is
`compiler_verification_project/artifacts/zkp_attestation_fixture_compressed.json`,
and the checked Groth16 fixture is
`compiler_verification_project/artifacts/zkp_attestation_fixture_groth16.json`.
The repo also ships the checked compressed proof bundle at
`compiler_verification_project/artifacts/zkp_attestation_proof_compressed.bin`,
the checked Groth16 proof bundle at
`compiler_verification_project/artifacts/zkp_attestation_proof_groth16.bin`
plus the matching verifying key at
`compiler_verification_project/artifacts/zkp_attestation_groth16_verifier/groth16_vk.bin`,
so the checked proof can be re-verified locally without rebuilding the large
vk-specific dev artifacts. Together these artifacts bind the current central
exact-family claim and `8 / 8` public cases.
This is similar in shape to Google's disclosure model, but it is still not a
primitive-gate full-Shor proof.

### Primary audited mainline

The primary release artifact in `artifacts/` still matters because it carries
the exact ISA-level leaf, the retained-window scaffold metadata, and the exact
lookup-contract layer that the compiler project builds on top of.

### Public baseline used for comparison

When this repository says **Google's published 2026 secp256k1 estimates**, it
means the rounded public comparison lines cited from Babbush et al. 2026 and
copied into the exact compiler frontier:

- **low-qubit line:** `1200 logical qubits`, `90,000,000 non-Clifford`
- **low-gate line:** `1450 logical qubits`, `70,000,000 non-Clifford`
- **window size:** `16`
- **retained point additions:** `28`

### Signed lookup contract

The optimized mainline incorporates the signed lookup-folding optimization. The
exact lookup-contract artifacts are in
`artifacts/lookup/lookup_signed_fold_contract.json` and
`artifacts/circuits/ecdlp_scaffold_lookup_folded.json`.

That contract is exact at the lookup-contract level and audited by:

- **65,536 / 65,536** exhaustive 16-bit words for the canonical `G` window-0
  base
- **15,906 / 15,906** additional multibase semantic samples

## Exact layers

- optimized secp256k1 point-add leaf semantics
- deterministic secp256k1 audit transcripts
- exhaustive toy-curve family checks
- explicit lookup-contract semantics, including the signed folded variant
- retained-window scaffold metadata and deterministic scaffold replay
- exact whole-oracle counts for named compiler families in `compiler_verification_project/`
- exact leaf slot allocation for the checked-in mixed-add leaf
- exact phase-shell family accounting for full-register vs semiclassical-QFT shells
- exact SP1 attestation of one selected compiler-family claim against a public deterministic point-add corpus

Lower-exact implementation hypotheses are documented separately in
`docs/research/MODELED_IMPLEMENTATION_HYPOTHESES.md`.

## Verification summary

The checked-in summaries report:

- optimized secp256k1 audit: **16,384 / 16,384** pass
- base toy-curve proof: **19,850 / 19,850** pass
- extended lookup-contract audit: **81,451 / 81,451** pass across **9** machine-readable contract checks, **65,536** exhaustive canonical-base words, and **15,906** multibase semantic samples
- extended scaffold replay: **256 / 256** pass
- extended toy-family proof: **110,692 / 110,692** pass
- challenge ladder replay: **763 / 763** pass across **7** deterministic benchmark curves

See:

- `results/repo_verification_summary.json`

## Cain et al. 2026

The repository's primary physical-layer file is the checked Microsoft Resource
Estimator integration in
`compiler_verification_project/artifacts/azure_resource_estimator_results.json`,
which records official preset-target outputs for every exact compiler family.

Another paper that strongly shaped this repository's physical-layer thinking is
[Shor's algorithm is possible with as few as 10,000 reconfigurable atomic qubits](https://arxiv.org/abs/2603.28627).
Cain et al. study a fault-tolerant neutral-atom architecture rather than
publishing a new secp256k1 circuit. Their headline reference points are
roughly **10,000 physical qubits** at the minimum-space end, or about
**26,000 physical qubits** for a faster **ECC-256 / P-256** attack with a
runtime around **10 days**; their slower balanced line is around **264 days**.

This repository includes an approximate transfer of the exact compiler-family
frontier into that physical model in
`docs/references/CAIN_2026_NEUTRAL_ATOM_INTEGRATION.md` and
`results/cain_2026_integration_summary.json`. Under fixed cycle-time and
parallelism assumptions, the exact-family runtime range spans roughly **2.65 to
5.35 days** depending on which exact compiler family is chosen. The
same-density physical-qubit range is much broader because the exact frontier
still includes multiple internal family variants. That transfer is intentionally
stated as approximate, because Cain's paper targets **P-256**, while the
primary artifact in this repository is specialized to **secp256k1**.

## Repository map

- `artifacts/` — primary optimized artifact, audits, projections, and research outputs
- `src/` — verifier and research logic implemented in Python
- `scripts/` — reproducibility entrypoints
- `docs/` — scope, claims, baseline definitions, verification notes, and
  research interpretation
- `figures/` — generated report figures
- `results/` — generated summary JSON files
- `compiler_verification_project/` — exact compiler-family oracle build, frontier, verification artifacts, and SP1 attestation workspace

## Quick start

From the repository root:

```bash
python scripts/verify_all.py
python compiler_verification_project/scripts/build.py
python compiler_verification_project/scripts/verify.py --cases 16
python compiler_verification_project/scripts/build_zkp_attestation_input.py --cases 8
python compiler_verification_project/scripts/materialize_exact_circuits.py
python scripts/compare_cain_2026.py
```

`compiler_verification_project/scripts/materialize_exact_circuits.py` writes
ignored exact whole-oracle operation streams under
`compiler_verification_project/generated_circuits/`. With no family arguments
it materializes the central public exact family and the internal minimum-qubit
comparison family; use `--all-families` to dump every checked exact compiler
family.

See `compiler_verification_project/README.md` for the SP1 execute/prove
commands that reproduce the checked attestation bundle.

`make test` uses the built-in parallel test runner in `scripts/run_tests.py`;
use `make test-sequential` for a single-process pytest run.

## Reading order

1. `docs/core/CLAIMS_AND_BOUNDARIES.md`
2. `docs/references/GOOGLE_BASELINE_COMPARISON.md`
3. `docs/core/EXTENDED_VERIFICATION.md`
4. `docs/research/LOOKUP_FOLDING_RESEARCH_PASS.md`
5. `docs/research/OPTIMIZATION_FRONTIERS.md`
6. `docs/references/STATE_OF_THE_ART_2026.md`
7. `docs/core/RED_TEAM_REVIEW.md`
