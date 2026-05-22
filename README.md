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
   packages one selected standard-QROM family claim into an SP1 attestation bundle with
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
selected standard-QROM family claim into a machine-checked proof artifact without
claiming a primitive-gate full-Shor witness.

## Main results

### Compiler + verification subproject

The root-level `compiler_verification_project/` is the repository's strongest
exact layer below the ISA boundary. Its checked-in central whole-oracle result
is:

- **public standard-QROAM headline:** `36,957,412 non-Clifford`, `1,199 logical qubits`

Those numbers are exact for the chosen compiler family, not a claim of global
optimality or a Clifford-complete full-Shor netlist. The public headline is the
reusable-chunk four-slot family selected in
`compiler_verification_project/artifacts/public_headline_result.json`. It uses
standard QROAMClean `K = 1` chunk streams over the full 32768-entry folded
coordinate domain, an exact semiclassical-QFT phase shell, and the executable
`complete_a0_reusable_chunk_tail` point-add leaf. The counted lookup workspace
includes folded-control qubits plus one live 155-bit QROAM chunk target and no
free full-coordinate lookup lane. The older `34,925,796 / 1,044` three-slot
family remains checked as a reference boundary, but it is no longer the single
public headline.

Against Google's published 2026 secp256k1 baseline, the public standard-QROAM
result is:

- **2.4352x** lower in non-Clifford cost than the public low-qubit line
- **1.8941x** lower in non-Clifford cost than the public low-gate line
- **1 qubit below** the public low-qubit line
- **251 qubits below** the public low-gate line

### SP1 attestation layer

The repository now also ships a public SP1 attestation at the exact
compiler-family boundary, similar in broad shape to Google's disclosure but
with a public 8-case corpus and explicit proof-freshness checks. The public
headline proof artifacts live under
`compiler_verification_project/artifacts/zkp_attestation_reusable_chunk_candidate/`
and bind:

- a hashed reusable-chunk executable witness leaf
- a hashed selected family summary in
  `compiler_verification_project/artifacts/zkp_attestation_reusable_chunk_candidate/zkp_attestation_family.json`
- a hashed deterministic public point-add case corpus in
  `compiler_verification_project/artifacts/zkp_attestation_reusable_chunk_candidate/zkp_attestation_cases.json`
- a hashed reusable-chunk lowering/resource certificate

The SP1 guest re-checks semantic hashes for those embedded typed documents,
replays the leaf on every public case, checks the affine group law, and
reconstructs the claimed exact non-Clifford and logical-qubit formulas. It also
checks the resource certificate, including executable interval liveness,
qchunk/QROAM-target concurrency, no full-coordinate lookup lane, and numeric
owner capacity. It also validates the committed compiler-parameter document
before committing public values. The candidate directory records core,
compressed, and Groth16 fixtures, compressed/Groth16 proof bundles, the wrap
proof bundle, and the matching Groth16 verifying key. During source churn,
`compiler_verification_project/scripts/proof_status.py` is the authority for
whether those proof layers still bind the current input; after the latest
resource-certificate binding changes, final compressed/Groth16 rebuild remains
the release gate before claiming current proof freshness. Together these
artifacts define the public `36,957,412 / 1,199` candidate claim and `8 / 8`
public cases, while the checked compressed/Groth16 proofs remain explicitly
stale until rebuilt against the current resource digest.
The compiler artifacts also include proof-bound generated QROAM,
independent QROAM reference, and modular-arithmetic certificates. The QROAM
reference keeps the selected 155-bit reusable chunk stream separate from the
256-bit full-field ledger sweep, so reviewers can audit the selected lookup
stream and the field-multiplication pseudo-Mersenne reduction without treating
them as loose spreadsheet constants.
This is similar in shape to Google's disclosure model, but it is still not a
primitive-gate full-Shor proof.

### Primary audited mainline

The primary release artifact in `artifacts/` still matters because it carries
the exact ISA-level leaf, the retained-window scaffold metadata, and the exact
lookup-contract layer that the compiler project builds on top of.

### Public baseline used for comparison

When this repository says **Google's published 2026 secp256k1 estimates**, it
means the rounded public comparison lines cited from Babbush et al. 2026 and
stored in `data/public_google_baseline.json`, then mirrored into the exact
compiler frontier and
`compiler_verification_project/artifacts/public_google_baseline_source.json`:

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
- exact leaf slot allocation for the streamed lookup tail leaf
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

## IBM Quantum roadmap context

IBM is one of the clearest public hardware roadmaps to compare against because
it states named fault-tolerant milestones in logical-qubit and gate-scale
language rather than only in physical-qubit counts. That makes IBM's roadmap
especially useful for reading this repository's logical result as an
engineering-scale signal, not just as an abstract asymptotic risk.

The current public headline here is **36,957,412 non-Clifford operations** and
**1,199 logical qubits**. IBM's public roadmap frames Starling as a 2029
fault-tolerant system with **200 logical qubits** and **100 million gates**,
and Blue Jay as a 2033+ class system with about **2,000 logical qubits** and
**1 billion gates**. Starling is therefore already in the right gate-scale
conversation, but below this repository's current logical-qubit requirement.
Blue Jay is the first named IBM target with natural logical-qubit headroom for
this scale of secp256k1 circuit.

The favorable, bounded interpretation is: if IBM delivers the post-Starling
logical-qubit and gate-scale targets it has publicly described, secp256k1 ECDLP
resource estimates like this one stop being only long-range cryptographic
warnings and become workloads that fit inside a named industrial
fault-tolerant machine class. This is roadmap context, not a claim that Heron,
Nighthawk, Starling, or any current IBM processor can run the full circuit
today. The machine-readable source note is
`data/ibm_quantum_roadmap_context.json`; the prose source map is
`docs/references/IBM_QUANTUM_ROADMAP_CONTEXT.md`.

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
python compiler_verification_project/scripts/build.py --target composition-artifacts
python compiler_verification_project/scripts/build.py --target materialized-circuit-manifest
python compiler_verification_project/scripts/build.py --target proof-environment-contract
python compiler_verification_project/scripts/build.py --target resource-zkp-and-public
python compiler_verification_project/scripts/build.py --target zkp-and-public
python compiler_verification_project/scripts/build.py --target release-candidate-zkp
python compiler_verification_project/scripts/verify.py --cases 16
python compiler_verification_project/scripts/proof_status.py
python compiler_verification_project/scripts/fast_zkp_preflight.py
python compiler_verification_project/scripts/proof_environment_report.py
python compiler_verification_project/scripts/verify_public_headline.py
python compiler_verification_project/scripts/build_zkp_attestation_input.py --cases 8
python compiler_verification_project/scripts/build_zkp_attestation_input.py --profile release --output-dir compiler_verification_project/artifacts/zkp_attestation_release_candidate
python compiler_verification_project/scripts/materialize_exact_circuits.py
python scripts/compare_cain_2026.py
```

`compiler_verification_project/scripts/materialize_exact_circuits.py` writes
ignored exact whole-oracle operation streams under
`compiler_verification_project/generated_circuits/`. With no family arguments
it materializes the central public standard-QROM family and the internal minimum-qubit
comparison family; use `--all-families` to dump every checked exact compiler
family.

Use `build.py --target resource-zkp-and-public` for the normal reusable-chunk
resource edit loop: it refreshes `reusable_chunk_lowering.json`, the candidate
ZKP input bundle, and the public headline JSON without rebuilding every compiler
artifact. Use `build.py --target composition-artifacts` after changing resource
or frontier accounting that feeds the composition layer; it refreshes
`full_attack_inventory.json`, `subcircuit_equivalence.json`, and
`headline_opcode_coverage.json` without touching any prover. Use
`build.py --target materialized-circuit-manifest` to refresh the segmented
operation-stream digest/Merkle manifest without a full rebuild. Use
`build.py --target proof-environment-contract` after changing proof paths,
runbook commands, proof manifest membership, or public-headline verification
commands. Use `build.py --target zkp-and-public` when only attestation wrapping
metadata changed.
Checked artifact tests reuse existing build/verification summaries by default;
set `SECP256K1_OPEN_AUDIT_FORCE_REBUILD=1` only when you intentionally want a
test run to regenerate those summaries.
Use `build.py --target release-candidate-zkp` or
`build_zkp_attestation_input.py --profile release` to prepare the 9024-case
Google-comparable input bundle without invoking SP1 proving.
Use `compiler_verification_project/scripts/fast_zkp_preflight.py` as the normal
ZKP/resource edit-loop gate. It runs `proof_status.py`, targeted integrity
groups including `proof_environment_contract_checks`, focused pytest tests, and
the attestation-library Rust unit tests, and it has an internal guard that
rejects any command plan containing a prover. The fast gate also rebuild-checks
the 9024-case release-corpus preflight as semantic evidence only; it is not a
substitute for compressed/Groth16 proof freshness.
After compressed/Groth16 proof rebuilds, run the same preflight with
`--require-current-proofs` to make stale checked proof fixtures a hard failure
without starting another proof.

See `compiler_verification_project/README.md` for the SP1 execute/prove
commands that reproduce the checked attestation bundle.
`compiler_verification_project/scripts/proof_status.py` is the cheap preflight
for proof freshness: it compares the current candidate input, public values,
fixtures, proof binaries, verifier key, and curated proof manifest without
invoking any prover.
`compiler_verification_project/artifacts/proof_environment_contract.json`
binds the checked runbook layer: required tools, no-prover edit-loop commands,
publication freshness gates, direct compressed/Groth16 verification commands,
public-headline artifact digests, and curated proof-manifest records.
Compressed and Groth16 proving are not part of the edit loop; the guarded
runner requires `--allow-heavy-proof` for those release-gate operations so an
ordinary verification pass cannot accidentally start a multi-hour proof.
`compiler_verification_project/scripts/verify_public_headline.py` is the fast
reviewer entrypoint for the checked public headline: by default it validates
the public result, input, public values, source-document hashes, fixture
records, proof-binary digests, wrap proof, and Groth16 verifier key from the
checked branch state. Add `--verify-compressed` or `--verify-groth16` to run
the corresponding checked proof verifier as well. During source churn this
command is allowed to fail because stale checked proof artifacts no longer bind
the current input; use `proof_status.py` first to see whether the failure is an
expected freshness gate.

`make test` uses the built-in parallel test runner in `scripts/run_tests.py`;
use `make test-sequential` for a single-process pytest run.

## Reading order

1. `docs/core/CLAIMS_AND_BOUNDARIES.md`
2. `docs/references/GOOGLE_BASELINE_COMPARISON.md`
3. `docs/core/EXTENDED_VERIFICATION.md`
4. `docs/research/LOOKUP_FOLDING_RESEARCH_PASS.md`
5. `docs/research/OPTIMIZATION_FRONTIERS.md`
6. `docs/references/STATE_OF_THE_ART_2026.md`
7. `docs/references/IBM_QUANTUM_ROADMAP_CONTEXT.md`
8. `docs/core/RED_TEAM_REVIEW.md`
