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

<!-- BEGIN GENERATED: strict-replayed-tail-headline -->
- **primary strict replayed-tail headline:** `36,973,222 non-Clifford`, `1,968 logical qubits`
- **logical-qubit formula:** `7 * 256 + 173 + 2 + 1 = 1,968`
- **vs Google low-qubit line:** `2.4342x` lower non-Clifford, `+768` logical qubits
- **vs Google low-gate line:** `1.8933x` lower non-Clifford, `+518` logical qubits
<!-- END GENERATED: strict-replayed-tail-headline -->

Those numbers are exact for the chosen compiler family, not a claim of global
optimality or a Clifford-complete full-Shor netlist. The primary public resource
headline is selected in
`compiler_verification_project/artifacts/primary_strict_result.json`, which
points to the replayed-tail source artifact
`compiler_verification_project/artifacts/strict_replayed_tail_headline.json`.
It combines the standard QROAMClean `K = 1` reusable-chunk lookup resource with
the fused-output seven-slot tail schedule replayed by
`compiler_verification_project/artifacts/tail_macro_engine.json`. The counted
lookup workspace includes folded-control qubits plus one live 155-bit QROAM
chunk target and no free full-coordinate lookup lane. The strict count also
includes the one extra guard qubit and 510 non-Clifford operations per tail
needed for the zero-lifted in-place `Y3` register reuse. The old four-slot
macro contract remains a ZKP/publication wrapper reference in
`compiler_verification_project/artifacts/public_headline_result.json`, but it
is no longer the primary strict resource headline. The older
`34,925,796 / 1,044` three-slot family remains checked as a reference boundary,
not as the promoted public claim.

Against Google's published 2026 secp256k1 baseline, the public standard-QROAM
result is:

- **2.4342x** lower in non-Clifford cost than the public low-qubit line
- **1.8933x** lower in non-Clifford cost than the public low-gate line
- **768 qubits above** the public low-qubit line
- **518 qubits above** the public low-gate line

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
replays the leaf on every public case, checks the affine group law, and checks
that the public claim summary matches the resource-engine output embedded in
the reusable-chunk resource document. Formula rows remain as consistency
snapshots, not as the primary public-result source. The no-ZKP engine path also
checks executable interval liveness, qchunk/QROAM-target concurrency, no
full-coordinate lookup lane, numeric owner capacity, and the current
flat-index primitive netlist commitment. The current-headline counted-resource
stream is separately materialized in
`compiler_verification_project/artifacts/headline_resource_manifest.json`, so
the old macro `36,957,412 / 1,199` proof-wrapper result is not backed by the
older three-slot materialized manifest by accident. It also validates the committed compiler-parameter document
before committing public values. `compiler_verification_project/artifacts/constant_provenance.json`
binds the selected phase-shell counts, headline totals, and publication limits
from their source artifacts into the ZKP family document and public headline
JSON, and checks that the old hardcoded ZKP count pattern is absent. The candidate directory records core,
compressed, and Groth16 fixtures, compressed/Groth16 proof bundles, the wrap
proof bundle, and the matching Groth16 verifying key. During source churn,
`compiler_verification_project/scripts/proof_status.py` is the authority for
whether those proof layers still bind the current input; after the latest
resource-certificate binding changes, final compressed/Groth16 rebuild remains
the release gate before claiming current proof freshness. Together these
artifacts still bind the legacy macro/ZKP candidate claim and `8 / 8` public
cases. That claim is kept only as a checked publication-wrapper reference until
rebuilt; the primary strict resource headline is the guarded replayed-tail
`36,973,222 / 1,968` artifact selected by `primary_strict_result.json`.
The compiler artifacts also include `public_candidate_materialized_circuit_manifest.json`,
`public_engine_manifest.json`, and `engine_completion_audit.json`, the no-ZKP
engine gate for the current public candidate. The public-candidate materialized manifest expands the reusable
claim into deterministic run-length primitive rows and then scans the full
materialized primitive stream: every emitted operation has concrete operand
wires, parent-wire bindings, liveness interval, and owner-qubit total. The
checked stream carries a full-stream SHA-256 plus segment Merkle root. It also
records a strict replayed-tail capacity overlay that binds the flat operation
stream's non-Clifford count to the `1,968`-qubit seven-slot capacity result.
The same manifest now emits a strict liveness projection over every run-length
row: arithmetic-tail rows scan to the `1,968` peak, while non-tail rows keep the
materialized engine liveness. It also emits a separate strict materialized
flat-netlist commitment whose segment hashes include the projected liveness and
scan to the same `36,973,222 / 1,968` result. The remaining open step is to make
that strict flat stream the canonical public-engine/ZKP source instead of
keeping the old wrapper stream beside it. Segment
and preview rows bind the contributing run-length rows, operation-index ranges,
liveness rows, derived owner-qubit sums, all 186 QROAM streams over the
generated QROAMClean segment certificate, arithmetic-operation IR rows,
lookup-base rows, and the selected phase-shell rows. The same manifest executes
representative operation indices through the flat-netlist API, checking
concrete operand wires, segment/liveness bindings, QROAM target-domain widths,
and the reduced schoolbook Cartesian operand grid. It also carries a strict
primitive-completeness report, an operand-parent binding report, and an
operand-source binding report. Those reports require QROAM `ccx`, arithmetic
`ccx`, measurement, and phase rows to expand to gate-arity operand references
that point back to counted live parent wires such as `qx`, `qy`, `qz`,
`qchunk`, folded lookup workspace, the active QROAM chunk target, and the
semiclassical phase bit, and require each run-length row to bind to a concrete
arithmetic block, lookup block, QROAM segment, or phase-shell block rather than
only to a family aggregate. The completion audit is intentionally stricter than
the headline: it passes only when those source bindings are current and the
remaining macro boundaries are explicit, while keeping
`clifford_complete_goal_achieved = false` until modular arithmetic expansion,
QROAM emitted table-bit CNOT rows are spliced below the current word-level,
target-bit-site, and range/probe-bound table-CNOT QROAMClean artifacts, the tail
macro in-place schedule, and the final ZKP input contract are internal products
of one canonical executable flat IR.
Modular arithmetic kernels are now generated from the
embedded `executable_modular_circuit_ir`; the modular certificate consumes that
same IR instead of being an independent source of arithmetic resource formulas.
The selected tail macro now has its own executable engine artifact:
`tail_macro_engine.json` expands `complete_a0_all_streamed_tail` into the
23-row counted field-operation stream, then proves a cost-equivalent fused
output stream that computes `X3 = K*N - E*C`, `Y3 = N*M + C*L`, and
`Z3 = M*E + L*K` without materializing the six pair-product lanes as live field
registers. The fused stream preserves the same tail non-Clifford cost, reaches
seven field slots, replays across 110,082 non-infinity toy boundary pairs,
checks 610 lookup-infinity no-op boundary pairs, and derives a seven-slot
owner-capacity ledger. The artifact also rejects the old unguarded `Y3` over
`N` reuse with a concrete secp256k1 `M == 0` witness, then proves the selected
zero-lifted in-place `Y3` over `C` field permutation with an explicit counted
`L == 0` guard. That seven-slot replayed-tail
result is now the primary strict headline in
`strict_replayed_tail_headline.json`; the remaining work is to reduce it below
seven field slots and eventually make the ZKP guest/input consume that exact
strict contract.

`tail_macro_engine.json` now also carries an unpromoted semantic six-slot
candidate. It combines `(I,F) -> (M,N)` as an in-place sum/difference pair and
`(E,K) -> (X3,Z3)` as a pair-output matrix with determinant `-Y3`; the checked
certificate proves the determinant precondition and the toy-boundary replay
passes. The candidate is kept out of the public headline until the variable 2x2
in-place matrix has a finalized primitive resource lowering and cost contract.

The public engine manifest then binds that
strict materialized flat stream, executable instruction rows, wires, schedule events,
owner-capacity rows, resource terms, semantic-boundary evidence, arithmetic
operation IR, the generated QROAMClean `K = 1` primitive certificate, and the
selected semiclassical phase shell into the same public claim layer. Its public
totals are derived from `canonical_materialized_flat_netlist`, while
the legacy wrapper/resource totals are retained as cross-check snapshots, not as
the authoritative source. The materialized flat engine and public engine are
built from compiler/resource artifacts rather than from the ZKP input, so the
proof input can be treated as a downstream publication wrapper instead of an
upstream resource source.
The QROAM reference keeps the selected 155-bit reusable chunk stream separate
from the 256-bit full-field ledger sweep, so reviewers can audit the selected
lookup stream and the field-multiplication pseudo-Mersenne reduction without
treating them as loose spreadsheet constants.
This is similar in shape to Google's disclosure model, but it is still not a
physical-layout or runtime proof for a complete full-Shor machine.

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

The current strict replayed-tail headline here is **36,973,222 non-Clifford
operations** and **1,968 logical qubits**. IBM's public roadmap frames Starling as a 2029
fault-tolerant system with **200 logical qubits** and **100 million gates**,
and Blue Jay as a 2033+ class system with about **2,000 logical qubits** and
**1 billion gates**. Starling is therefore already in the right gate-scale
conversation, but below this repository's current logical-qubit requirement.
Blue Jay is the first named IBM target with natural logical-qubit headroom for
this strict replayed-tail count, with 32 logical qubits above the current
headline.

The favorable, bounded interpretation is: if IBM delivers the post-Starling
logical-qubit and gate-scale targets it has publicly described, secp256k1 ECDLP
resource estimates like this one stop being only long-range cryptographic
warnings and move into the scale of named industrial fault-tolerant machine
classes. This is roadmap context, not a claim that Heron,
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
python compiler_verification_project/scripts/build.py --target public-engine-manifest
python compiler_verification_project/scripts/materialize_exact_circuits.py --public-candidate-flat-netlist --slice-start 0 --slice-count 1000
python compiler_verification_project/scripts/build.py --target proof-environment-contract
python compiler_verification_project/scripts/build.py --target proof-publication-status
python compiler_verification_project/scripts/build.py --target resource-zkp-and-public
python compiler_verification_project/scripts/build.py --target zkp-and-public
python compiler_verification_project/scripts/build.py --target release-candidate-zkp
python compiler_verification_project/scripts/verify.py --cases 16
python compiler_verification_project/scripts/proof_status.py
python compiler_verification_project/scripts/fast_engine_verify.py
python compiler_verification_project/scripts/fast_zkp_preflight.py
python compiler_verification_project/scripts/release_candidate_preproof.py --dry-run-json
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
resource edit loop: it refreshes `reusable_chunk_lowering.json`,
`public_engine_manifest.json`, the candidate ZKP input bundle, and the public
headline JSON without rebuilding every compiler artifact. It also refreshes
`strict_replayed_tail_headline.json`, the primary strict resource presentation
artifact. Use `compiler_verification_project/scripts/update_readme_headline.py`
after that build to rewrite the generated README headline block from the strict
artifact, or pass `--check` in CI/review. Use
`build.py --target public-engine-manifest` after changing only the no-ZKP public
engine manifest layer. Use `build.py --target engine-completion-audit` after
changing only the no-ZKP completion/status layer that classifies covered engine
boundaries and remaining macro boundaries. Use `build.py --target composition-artifacts` after changing resource
or frontier accounting that feeds the composition layer; it refreshes
`full_attack_inventory.json`, `subcircuit_equivalence.json`, and
`headline_opcode_coverage.json` without touching any prover. Use
`build.py --target materialized-circuit-manifest` to refresh the segmented
operation-stream digest/Merkle manifest without a full rebuild. Use
`build.py --target proof-environment-contract` after changing proof paths,
runbook commands, proof manifest membership, or public-headline verification
commands. Use `build.py --target proof-publication-status` after changing
proof-status logic, public-headline pass/freshness semantics, or publication
gate wiring. Use `build.py --target zkp-and-public` when only attestation
wrapping metadata changed.
Checked artifact tests reuse existing build/verification summaries by default;
set `SECP256K1_OPEN_AUDIT_FORCE_REBUILD=1` only when you intentionally want a
test run to regenerate those summaries.
Use `build.py --target release-candidate-zkp` or
`build_zkp_attestation_input.py --profile release` to prepare the 9024-case
Google-comparable input bundle without invoking SP1 proving.
Use `compiler_verification_project/scripts/release_candidate_preproof.py` to
build that 9024-case release input in an isolated output directory, and add
`--execute` when you want the SP1 guest execute path over that input without
invoking a prover.
Use `compiler_verification_project/scripts/fast_zkp_preflight.py` as the normal
ZKP/resource edit-loop gate. It runs `proof_status.py`, targeted integrity
groups including `proof_environment_contract_checks` and
`proof_publication_status_checks`, focused pytest tests, and the
attestation-library Rust unit tests, and it has an internal guard that rejects
any command plan containing a prover. The fast gate also rebuild-checks the
9024-case release-corpus preflight as semantic evidence only; it is not a
substitute for compressed/Groth16 proof freshness.
Use `compiler_verification_project/scripts/fast_engine_verify.py` for the
engine-only no-ZKP loop. It rebuilds the current public resource artifacts,
verifies the reusable engine, public engine manifest, headline resource
manifest, macro public headline, strict replayed-tail headline, and proof
runbook/status metadata, and then runs the
focused Python mutation tests. The public engine manifest also binds semantic
boundary evidence: the streamed-tail edge-case equivalence, reusable-tail toy
semantic/scratch trace, 9024-case release corpus preflight, and checked smoke
case categories. It also binds the public-candidate materialized run-length
stream, the flat-index netlist segment root, and primitive-operation evidence
from the arithmetic operation IR, QROAM primitive certificate, and phase-shell
lowering so drift in those generated streams fails before any prover is
considered. Add
`--include-rust` when you also want the SP1
attestation-library reusable-chunk unit tests, still without proving.
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
`compiler_verification_project/artifacts/proof_publication_status.json` binds
the current publication-readiness verdict. Its `pass` flag means the stale/fresh
status was derived consistently; `publication_ready` remains false until
`proof_status.py --require-all-current` and compressed/Groth16 verification
both agree with the checked artifacts.
Compressed and Groth16 proving are not part of the edit loop; the guarded
runner requires `--allow-heavy-proof` for those release-gate operations so an
ordinary verification pass cannot accidentally start a multi-hour proof.
`compiler_verification_project/scripts/verify_public_headline.py` is the fast
reviewer entrypoint for the checked macro/ZKP public headline: by default it validates
the public result, input, public values, source-document hashes, fixture
records, proof-binary digests, wrap proof, and Groth16 verifier key from the
checked branch state and prints a compact blocker report. Add `--verbose` for
the full per-check JSON, or add `--verify-compressed` / `--verify-groth16` to
run the corresponding checked proof verifier as well. During source churn this
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
