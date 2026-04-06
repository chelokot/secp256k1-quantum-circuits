# Internal red-team review

This is the attack-your-own-work document.

## Executive summary

I did **not** find a critical arithmetic inconsistency that breaks the
repository's current narrowed claims.

I **did** find one important internal problem during the lookup-focused research
pass:

- an earlier frontier-analysis script misread a per-leaf arithmetic estimate as
  if it were the arithmetic cost of the whole scaffold.

That bug did **not** invalidate the main exact artifact or the main published
headline, but it **did** invalidate the earlier “lookup is ~97% of the current
modeled cost” story.

This repository revision fixes that openly.

## Severity-ranked objections

| Objection | Severity if overclaimed | Current answer | Still open? |
|---|---:|---|---|
| “This is not a primitive-gate circuit because lookup is abstracted.” | High | True. The repo is explicit about this and now distinguishes exact lookup contracts from primitive-lowered lookup machinery. | Yes |
| “MBUC cleanup is not a fully verified coherent quantum subcircuit.” | High | True. The repo only claims basis-state functional semantics at the ISA boundary. | Yes |
| “The scaffold is metadata, not the whole Shor stack.” | High | True. The repo has scaffold replay checks but does not pretend this is a flat full-algorithm gate list. | Yes |
| “The 880q / 31.0M headline depends on a backend model.” | High | True. Those numbers remain projected, not theorem-proved primitive-gate counts. | Yes |
| “Your older frontier analysis overstated lookup dominance.” | High | True. That was a real internal mistake. It is now corrected and documented in `docs/COST_MODEL_CORRECTION.md`. | No, as long as the corrected wording is used |
| “Finite toy proofs are not universal proofs over all prime fields.” | Medium | True. They are finite-model checks supporting the family story, not universal theorems. | Yes |
| “No full ZKP / SNARK proof object is included.” | Medium | True. This repo is an open audit artifact, not a cryptographic proof release. | Yes |

## Most dangerous self-deception risks

### 1. Confusing “exact arithmetic leaf” with “exact whole quantum circuit”

Still the easiest way to get torn apart publicly.

### 2. Treating modeled lookup totals as if the lookup backend were already built

It is not built here. The repo now separates:

- exact lookup contracts,
- lookup audits,
- and backend projections.

### 3. Forgetting the corrected frontier story

The repo can no longer honestly say that the current mainline is already
lookup-dominated.

### 4. Overselling the Google comparison

The comparison remains against the **public appendix envelope**, not against
Google's unpublished internal circuit.

## What the red team failed to break

After the correction and hardening pass, I did not find evidence against the
following narrower statements:

- the optimized leaf's basis-state arithmetic semantics,
- the family netlist on the curated prime-order toy curves,
- the internal coherence of the retained-window scaffold,
- the exact signed lookup-folding contract added in this revision,
- the claim that the current backend projection remains below the public Google
  appendix envelope,
- the claim that the folded lookup branch gives a modest but real modeled win.

## Criticisms that are fair and should be conceded immediately

Concede these immediately instead of fighting them:

- “You have not shipped a primitive-gate qRAM or QROM.”
- “You have not primitive-verified MBUC cleanup.”
- “You have not reconstructed Google's hidden exact circuit.”
- “Your logical-qubit and non-Clifford totals are modeled.”
- “Your earlier lookup-dominance interpretation was wrong.”

The last one matters. Once corrected, it is no longer a fatal flaw; hiding it
would be.

## Criticisms that can be answered directly

### “So does the lookup pass still matter?”

Yes. The new pass is not sold as another giant overall leap. It is sold as a
clean exact contract improvement that composes with future work and yields a
modeled 5.9% to 8.4% total win.

### “Does the correction destroy the repo?”

No. It destroys one earlier interpretation of the frontier, not the exact leaf,
not the secp256k1 audits, and not the current main public-envelope comparison.

### “Should arithmetic papers be taken seriously again?”

Yes. After correction, arithmetic-backend work is likely more important than the
previous frontier note suggested.

## Publication-safe wording

Good:

- “exact ISA-level arithmetic artifact”
- “exact signed lookup-contract improvement”
- “tested retained-window scaffold”
- “modeled backend projection”
- “beats the public appendix envelope”

Bad:

- “fully verified quantum circuit”
- “lookup dominates almost all remaining cost”
- “Google's exact hidden circuit”
- “the final physical machine cost is exactly X”

## Critical error status

**No critical error found that falsifies the repository's current narrowed
claims.**

A real internal modeling bug was found and fixed. The repo is stronger because
that correction is now explicit instead of being buried.
