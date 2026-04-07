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

This repository contains exact ISA-level secp256k1 quantum ECDLP circuits,
verification artifacts, and modeled resource estimates.
In Bitcoin terms, a successful attack of this kind would let an attacker
recover spend keys for exposed public keys and authorize fraudulent spends, and
the repository's current hardware-transfer estimate puts such an attack in the
rough range of 3.2 to 4.3 days on a large fault-tolerant quantum machine under
fixed-architecture assumptions.

The repository is strongest at the arithmetic ISA boundary. It publishes exact,
machine-readable point-add schedules and checks their basis-state semantics. It
also publishes modeled backend totals for logical qubits and non-Clifford
counts.

## Main results

### Primary audited mainline

The primary release artifact is in `artifacts/`.

Its modeled ECDLP projection, as recorded in
`artifacts/out/resource_projection.json`, is:

- **880 logical qubits**
- **29,163,456 non-Clifford** under the 2-channel lookup model
- **30,080,960 non-Clifford** under the conservative 3-channel lookup model

### Public baseline used for comparison

When this repository says **Google's published 2026 secp256k1 estimates**, it
means the rounded public comparison lines cited from Babbush et al. 2026 and
stored in `artifacts/out/resource_projection.json`:

- **low-qubit line:** `1200 logical qubits`, `90,000,000 non-Clifford`
- **low-gate line:** `1450 logical qubits`, `70,000,000 non-Clifford`
- **window size:** `16`
- **retained point additions:** `28`

### Signed lookup contract

The optimized mainline incorporates the signed lookup-folding optimization. The
exact lookup-contract artifacts are in
`artifacts/out/lookup_signed_fold_contract.json` and
`artifacts/out/ecdlp_scaffold_lookup_folded.json`.

That contract is exact at the lookup-contract level and audited by:

- **65,536 / 65,536** exhaustive 16-bit words for the canonical `G` window-0
  base
- **15,906 / 15,906** additional multibase semantic samples

Its backend totals remain modeled. The supporting projection in
`artifacts/out/lookup_folded_projection.json` is:

- **29,163,456 non-Clifford** under the folded 2-channel model
- **30,080,960 non-Clifford** under the folded conservative 3-channel model

## Exact vs modeled layers

### Exact in this repository

- optimized secp256k1 point-add leaf semantics
- deterministic secp256k1 audit transcripts
- exhaustive toy-curve family checks
- explicit lookup-contract semantics, including the signed folded variant
- retained-window scaffold metadata and deterministic scaffold replay

### Modeled in this repository

- primitive-gate lookup memory lowering
- primitive-gate cleanup for `mbuc_*` operations
- fully flattened Shor period-finding gate list
- logical-qubit and non-Clifford totals below the ISA boundary
- physical-machine runtime and physical-qubit transfer studies

## Verification summary

The checked-in summaries report:

- optimized secp256k1 audit: **16,384 / 16,384** pass
- base toy-curve proof: **19,850 / 19,850** pass
- extended lookup-contract audit: **8,192 / 8,192** pass
- extended scaffold replay: **256 / 256** pass
- extended toy-family proof: **110,692 / 110,692** pass
- challenge ladder replay: **763 / 763** pass across **7** benchmark curves

See:

- `results/repo_verification_summary.json`
- `results/research_pass_summary.json`

## Repository map

- `artifacts/` — primary optimized artifact, audits, projections,
  research outputs, and figures
- `benchmarks/challenge_ladder/` — deterministic benchmark-curve replay suite
- `src/` — verifier and research logic implemented in Python
- `scripts/` — reproducibility entrypoints
- `docs/` — scope, claims, baseline definitions, verification notes, and
  research interpretation
- `results/` — generated summary JSON files
- `reports/` — report PDFs

## Quick start

From the repository root:

```bash
python scripts/verify_all.py
python scripts/verify_all.py --quick
python scripts/release_check.py
python scripts/compare_cain_2026.py
```

Or with `make`:

```bash
make verify
make verify-quick
make release-check
```

## Reading order

1. `docs/CLAIMS_AND_BOUNDARIES.md`
2. `docs/GOOGLE_BASELINE_COMPARISON.md`
3. `docs/EXTENDED_VERIFICATION.md`
4. `docs/LOOKUP_FOLDING_RESEARCH_PASS.md`
5. `docs/OPTIMIZATION_FRONTIERS.md`
6. `docs/STATE_OF_THE_ART_2026.md`
7. `docs/RED_TEAM_REVIEW.md`
8. `reports/secp256k1_optimized_report.pdf`
