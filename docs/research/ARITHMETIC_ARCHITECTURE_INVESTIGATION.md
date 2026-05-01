# Arithmetic architecture investigation

This file is the checked-in research log for arithmetic-architecture work that
goes beyond the current exact frontier.

It records only two kinds of information:

- primary-source observations from the literature,
- local experiments run against the checked-in repository semantics.

It does not promote modeled numbers to headline results. A direction is treated
as promising here only if it survives the repository's actual accumulator,
lookup, and scaffold semantics.

## Current exact baseline

As of the current exact compiler frontier, the repository's central exact point is:

- `23,912,611` non-Clifford
- `1,587` logical qubits

This is the family
`folded_bitwise_banked_unary_qrom_measured_uncompute_v1__streamed_lookup_tail_leaf_v1__semiclassical_qft_v1`
in `compiler_verification_project/artifacts/family_frontier.json`.

The current arithmetic leaf is a complete mixed-add formula over the
homogeneous short-Weierstrass embedding used in `src/common.py`, where affine
recovery is `x = X / Z`, `y = Y / Z`.

## Repository constraints that dominate arithmetic changes

The following repository facts constrain any replacement leaf:

- The retained-window scaffold starts from a direct seed and then reuses one
  running accumulator through all retained window additions.
- The current coordinate model is homogeneous projective, not Jacobian.
- A candidate leaf is not useful unless it survives the actual retained-window
  schedule, not only isolated single-step tests.

The relevant files are:

- `artifacts/circuits/ecdlp_scaffold_optimized.json`
- `src/common.py`
- `src/extended_verifier.py`
- `compiler_verification_project/src/project.py`

## Local experiments

### 2026-04-08: current leaf versus Renes-Costello-Batina complete formulas

Primary source:

- Renes, Costello, Batina, "Complete addition formulas for prime order elliptic
  curves", ePrint 2015/1060, <https://eprint.iacr.org/2015/1060>

What was checked locally:

- encoded the paper's complete `a = 0` formulas as candidate ISA bodies,
- ran the repository slot search with `src/leaf_schedule_optimizer.py`.

Result:

- Algorithm 8, the complete mixed-add formula for `j = 0`, fits in `8`
  arithmetic slots but not `7`,
- Algorithm 7, the full complete projective addition, fits only in `9` or more
  arithmetic slots.

Interpretation:

- the checked-in leaf is already very close to the best known complete mixed-add
  formula class for secp256k1,
- there is no evidence inside this formula family for a real drop from `8`
  arithmetic slots to `7`.

Status:

- promising for understanding the ceiling,
- not promising as a path to an immediate qubit reduction.

### 2026-04-08: incomplete Jacobian mixed-add candidate

Primary sources:

- old EFD Jacobian mixed-add formulas,
  <https://www.hyperelliptic.org/EFD/oldefd/jacobian.html>
- Sedlacek, Chi-Dominguez, Jancar, Brumley, ePrint 2021/1595,
  <https://eprint.iacr.org/2021/1595>

What was checked locally:

- encoded an incomplete mixed Jacobian add candidate,
- verified that it fits in `7` arithmetic slots,
- encoded a Jacobian doubling candidate that fits in `6` arithmetic slots,
- tested both under the repository's current semantics and under correct
  Jacobian semantics.

Positive result:

- under correct Jacobian interpretation, the mixed-add candidate passes broad
  random single-step tests and chained nontrivial-`Z` tests.

Negative result:

- the candidate is not compatible with the repository's current homogeneous
  accumulator semantics,
- even after that coordinate mismatch is corrected conceptually, the
  retained-window schedule still produces real exceptional pairs.

Concrete blockers found locally:

- `accumulator = INF` is not the main blocker because the scaffold already
  replaces the first retained addition with a direct seed,
- `phase_b` has direct doubling and inverse witnesses because the retained
  schedule mixes a running `aG` accumulator with windows of `bH`, where
  `H = [h]G`,
- `phase_a` is also not globally safe: the last retained window has an exact
  inverse witness coming from the decomposition of `n`.

Exact structural witness for `phase_a`:

- let `window = 15`,
- let `weight = 2^(16 * 15)`,
- then `n = lower + 0xffff * weight`,
- `lower < weight`, so the lower windows can realize `lower G`,
- the last retained window can realize `0xffff * weight * G`,
- together they sum to `nG = INF`.

Interpretation:

- a `7`-slot incomplete Jacobian mixed-add leaf exists as an isolated formula,
- it cannot simply replace the current complete leaf in the current
  one-accumulator retained-window oracle.

Status:

- promising only for a deeper whole-oracle rewrite that globally removes
  exceptional pairs,
- not promising as a drop-in replacement for the current architecture.

### 2026-04-08: naive Jacobian fallback composition

What was checked locally:

- priced a naive arithmetic leaf that always computes incomplete mixed-add,
  doubling, and the extra zero/equality handling needed to choose the right
  branch coherently.

Result:

- the naive combined leaf blows the whole-oracle total up to roughly
  `41.18M` non-Clifford under the repository's current arithmetic cost model.

Interpretation:

- "just add a doubling fallback" is not good enough under the current
  `<40M` and preferred `<30M` targets.

Status:

- not promising.

### 2026-04-08: ladder rewrite gate screen

Primary sources:

- Hamburg, "Faster Montgomery and double-add ladders for short Weierstrass
  curves", ePrint 2020/437, <https://eprint.iacr.org/2020/437>
- Häner, Jaques, Naehrig, Roetteler, Soeken, "Improved Quantum Circuits for
  Elliptic Curve Discrete Logarithms", ePrint 2020/077,
  <https://eprint.iacr.org/2020/077>

What was checked locally:

- compared the current exact raw-32 oracle's arithmetic shape against a
  ladder-style per-bit rewrite.

Current exact arithmetic shape:

- `28` retained additions plus one direct lookup seed,
- `11` field multiplications per leaf,
- `308` field-multiplication instances across the repeated-add arithmetic path.

Hamburg's ladder headline:

- Montgomery ladder on short Weierstrass curves using `8M + 3S + 7A` per bit
  with `6` registers,
- Joye ladder using `9M + 3S + 7A` per bit with `5` registers.

Rough screening result:

- even before pricing squarings, one `256`-bit Montgomery ladder already
  implies `2048` multiplication-equivalent steps,
- that is about `6.6x` the current repeated-add arithmetic path's `308`
  multiplications,
- a naive rewrite that computes the two-scalar relation through separate ladder
  paths would therefore be badly misaligned with the current `<30M` and
  `<40M` targets.

Interpretation:

- the ladder papers are important because they show genuinely lower-register
  complete arithmetic,
- but they belong to a different algorithmic regime than the repository's
  retained-window oracle,
- they should be treated as whole-algorithm rewrite candidates, not as a
  plausible short-term arithmetic-leaf substitution.

Status:

- promising only as a deep rewrite candidate,
- not promising for immediate gate-capped improvement.

### 2026-04-08: torsion-profile filter for alternative complete models

Primary sources:

- Bernstein, Birkner, Joye, Lange, Peters, "Twisted Edwards Curves",
  ePrint 2008/013, <https://eprint.iacr.org/2008/013>
- Bernstein, Lange, "Montgomery curves and the Montgomery ladder",
  ePrint 2017/293, <https://eprint.iacr.org/2017/293.pdf>
- Bernstein, Chuengsatiansup, Kohel, Lange, "Twisted Hessian curves",
  ePrint 2015/781, <https://eprint.iacr.org/2015/781>

What was checked locally:

- screened the curve-model families that are most often associated with cheap
  complete or strongly unified addition laws,
- checked the torsion conditions those models require over the base field,
- compared them to secp256k1's actual base-field group order.

External facts used:

- twisted Edwards over the base field requires a rational point of order `4`,
- the Montgomery chapter states that complete Edwards curves are birationally
  equivalent to Montgomery curves with points of order `4` and a unique point
  of order `2`,
- twisted Hessian curves over a finite field always have a rational point of
  order `3`, and conversely a base-field point of order `3` is the structural
  entry point into that model family.

Local secp256k1 facts:

- the repository uses the standard prime subgroup order
  `n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141`,
- `n` is odd and `n mod 3 = 1`,
- therefore the base-field group has no rational torsion of order `2`, `3`, or
  `4`.

Immediate consequence:

- base-field Edwards, Montgomery, and Hessian rewrites are structurally blocked
  for secp256k1,
- low-degree base-field isogeny does not rescue this either:
  a rational isogeny kernel would have to be a rational subgroup whose order
  divides the base-field group order, and the repository works in a prime-order
  subgroup,
- equivalently, an isogenous curve over the same field has the same group order,
  so the missing `2`-, `3`-, and `4`-torsion does not suddenly appear on the
  prime-order side of the problem.

Interpretation:

- the fast complete-model families that owe their speed to low rational torsion
  are not realistic base-field rewrite candidates for this repository,
- a future Edwards-, Montgomery-, or Hessian-style direction would have to pay
  for an extension-field or other much deeper redesign, which is already far
  outside the near-term exact improvement target.

Status:

- useful as a strong negative filter,
- not promising as a base-field qubit-reduction path for secp256k1.

### 2026-04-08: split-branch oracle screen

What was checked locally:

- screened a whole-oracle rewrite that computes `aG` and `bH` in separate
  scalar-multiplication branches and only combines the two accumulators at the
  end,
- encoded a valid complete projective `a = 0` full-add body using both input
  projective points and ran the repository slot search on that body.

Result:

- the valid complete projective full-add body fits in `9` arithmetic slots, not
  in `8`,
- this already exceeds the current central exact frontier's `6` arithmetic
  slots before counting any lookup workspace or phase-shell bits.

Interpretation:

- split-branch scalar multiplication does not look like a qubit-reduction path
  unless the final branch combine is done in some other representation,
- the most obvious alternative is to normalize one branch and use a mixed add,
  but that pushes the design back toward inversion-heavy arithmetic.

Status:

- not promising as a near-term qubit reduction path,
- still worth remembering as a structural alternative if an inversion-friendly
  branch combine ever becomes attractive.

### 2026-04-08: abstract Bos-2014 masking-shell slot screen

Primary source:

- Bos, Costello, Longa, Naehrig, "Selecting Elliptic Curves for Cryptography:
  An Efficiency and Security Analysis", ePrint 2014/130,
  <https://eprint.iacr.org/2014/130>

What was checked locally:

- transcribed the mixed Jacobian-affine masking shell from Bos Algorithm 18 into
  an abstract ISA-style dataflow,
- treated the conditionals as constant-time field selects,
- ran the repository slot search on that abstract body.

Important limitation:

- this was a slot-screen only,
- it was not a semantic replay and did not yet adapt the arithmetic core from
  `a = -3` to secp256k1's `a = 0`,
- the halving step was represented only abstractly at the arithmetic level.

Result:

- the abstract mixed masking shell fits in `7` arithmetic slots,
- its rough arithmetic shape is about `11` field-multiplication-like operations,
  `8` field subtractions, `2` field additions, and `1` constant multiplication.

Interpretation:

- this is the first positive signal that an exception-handling shell does not
  automatically destroy the live-range budget,
- unlike the naive "compute both add and double" fallback, the Bos-style shell
  appears compatible with a sub-`8` arithmetic-slot target at the dataflow
  level,
- this materially strengthens the case for trying to rebuild the shell around an
  `a = 0` arithmetic core.

Status:

- promising,
- still unproven until an `a = 0` semantic version exists and passes real
  retained-window checks.

### 2026-04-08: abstract Rondepierre-2015 `a = 0` core slot screen

Primary source:

- Rondepierre, "Revisiting Atomic Patterns for Scalar Multiplications on
  Elliptic Curves", ePrint 2015/408, <https://eprint.iacr.org/2015/408>

What was checked locally:

- transcribed Formula (9), the paper's `a = 0` mixed Jacobian-affine addition
  core, into an abstract ISA-style dataflow,
- modeled the precomputed affine point as already carrying the negated
  coordinates used by the paper,
- ran the repository slot search on that arithmetic core.

Important limitation:

- this was again a slot-screen only,
- it was not yet embedded in a complete masking shell,
- it was not a semantic replay against the repository's retained-window oracle.

Result:

- the abstract `a = 0` mixed Jacobian-affine core fits in `7` arithmetic slots,
- the rough arithmetic shape stays in the same range as the current leaf on
  multiplication-dominant cost, while shifting work away from the current
  complete homogeneous pattern.

Interpretation:

- this is the first positive signal that the specific `a = 0` arithmetic core
  needed for a Bos-style masking adaptation is compatible with a `7`-slot live
  target,
- together with the Bos-shell screen, it gives a coherent path where both the
  exception-management shell and the underlying `a = 0` arithmetic core survive
  the slot budget independently.

Status:

- promising,
- still below the bar for a real circuit result until the shell and core are
  combined into one semantic candidate.

### 2026-04-09: cached-`Z^2/Z^3` requirement in the Rondepierre core

What was checked locally:

- revisited Formula (9) at the level of exact field-product counting rather than
  multiplication-equivalent pricing,
- separated the two cases:
  - the paper's intended input state, where the Jacobian point already carries
    `Z^2` and `Z^3`,
  - the repository's current accumulator style, where those powers would have
    to be recomputed inside the leaf.

Result:

- with cached `Z^2` and `Z^3`, the paper's core matches the advertised
  `7M + 2S` profile, i.e. `9` field products,
- without cached `Z^2` and `Z^3`, the same core becomes
  `8M + 3S`, i.e. `11` field products in the repository's current exact opcode
  vocabulary,
- that means the earlier optimistic gate proxy depends on a genuine
  representation change, not merely on swapping one arithmetic body for
  another.

Whole-oracle implication:

- if the current exact arithmetic vocabulary treats all field products as
  `field_mul`, the uncached version has no gross arithmetic advantage over the
  current `11`-product leaf,
- under the same zero-test and staged-select proxies used elsewhere in this
  log, the uncached whole-oracle proxy is about `22,867,159`,
- the cached version remains the optimistic branch at about `19,168,527`.

Interpretation:

- the Jacobian-shell candidate is still alive, but only as a whole-oracle
  coordinate-state pivot where the running accumulator explicitly carries
  `Z^2` and `Z^3`,
- it is not a drop-in replacement for the current `3`-register homogeneous
  accumulator.

### 2026-04-09: current leaf interface blocks a `7`-slot cached-`Z^2/Z^3` core

What was checked locally:

- encoded an executable abstract skeleton where the accumulator already carries
  `X, Y, Z, Z^2, Z^3`,
- kept the current leaf-interface discipline in which both lookup coordinates
  are loaded before arithmetic begins,
- ran the checked slot search on that strengthened prefix-loaded skeleton.

Result:

- a `7`-slot search fails on the strengthened skeleton,
- the same skeleton immediately fits at `8` slots,
- this is not yet the full Rondepierre body, but it is already enough to show
  that the current eager-load leaf boundary is hostile to a cached-`Z^2/Z^3`
  design.

Interpretation:

- the optimistic cached-`Z^2/Z^3` branch now has a concrete interface blocker:
  it wants a different leaf contract, not just a different arithmetic body,
- in practice that means at least one of the following must change before a
  `7`-slot exact candidate is realistic:
  - staged lookup loading instead of eager `x/y` materialization,
  - a richer lookup payload that avoids holding both affine coordinates at once,
  - or a different accumulator/lookup split entirely.

### 2026-04-09: delayed lookup loading restores the strengthened skeleton to `7` slots

What was checked locally:

- built a second executable abstract skeleton with the same strengthened
  accumulator state `X, Y, Z, Z^2, Z^3`,
- changed only the lookup discipline:
  - load affine `x`,
  - consume it,
  - then load affine `y` later into the reused lookup slot,
- measured the fixed-order live peak with an explicit output boundary at
  `qx, qy, qz`.

Result:

- the eager-load strengthened skeleton peaks at `8` live field slots,
- the delayed-load strengthened skeleton peaks at `7`,
- this is the first executable positive signal in the current pass that a
  concrete leaf-interface change can recover the `7`-slot class even with
  cached `Z^2/Z^3` state present.

Interpretation:

- the current blocker is not "cached `Z^2/Z^3` is inherently incompatible with
  `7` slots",
- the blocker is specifically the current eager interface that materializes both
  affine lookup coordinates before arithmetic consumes either of them,
- this makes staged lookup loading the strongest concrete next interface
  candidate for a real exact branch.

### 2026-04-08: naive fused Bos-plus-Rondepierre screen

What was checked locally:

- built a naive fused candidate that computes an `a = 0` mixed-add core, an
  explicit doubling core, and then uses field selects to choose between them.

Result:

- the naive fused candidate fits in `8` arithmetic slots, not `7`,
- its rough arithmetic shape is about `16` field multiplications,
  `12` field additions, `7` field subtractions, and `1` constant multiplication,
- under the current arithmetic cost model this kind of naive fusion would be
  materially more expensive than the current leaf.

Interpretation:

- the encouraging `7`-slot signals from the Bos-shell screen and the
  Rondepierre-core screen do not survive a trivial "compute both and select"
  composition,
- if this research direction is going to work, it will have to work for the
  same reason Bos 2014 is interesting in the first place: the exception-handling
  shell must share intermediates with the dedicated add path rather than merely
  wrapping it with a parallel doubling path.

Status:

- negative result for the naive composition,
- positive result for the higher-level direction because it isolates the real
  requirement: a shared-intermediate masking construction, not a branchy
  add-versus-double wrapper.

### 2026-04-08: shared-intermediate compatibility screen

What was checked locally:

- compared the early arithmetic dataflow in the Bos 2014 masking shell with the
  early arithmetic dataflow in the Rondepierre 2015 `a = 0` mixed
  Jacobian-affine core,
- priced both abstract arithmetic shapes under the repository's current
  arithmetic cost model.

Result:

- both constructions start by building the same projective normalizers
  `Z^2` and `Z^3`,
- the Bos shell uses deltas of the form
  `x2 * Z^2 - X` and `y2 * Z^3 - Y`,
- the Rondepierre `a = 0` core uses the same quantities up to sign via
  `Ebar = X - Xq * Z^2` and `Fbar = Y - Yq * Z^3`,
- under the repository's current abstract arithmetic pricing, the Bos shell and
  the Rondepierre core are both in the same multiplication-dominant cost band
  as the current leaf,
- in fact, under this simplified abstract pricing they both land slightly below
  the current leaf, which is encouraging even though it is not yet a valid
  whole-candidate cost claim.

Interpretation:

- this is the strongest positive signal found so far for the current top
  research candidate,
- the shell and the core are not merely philosophically compatible; they appear
  to share the same expensive early intermediates, which is exactly what is
  needed to avoid the naive-fusion failure,
- the remaining challenge is not to discover whether the two ideas have any
  overlap, but to construct a correct shared-intermediate masking schedule for
  the `a = 0` case.

Status:

- promising,
- still below the bar for a real circuit result because no secp256k1-width
  semantic combined candidate exists yet.

### 2026-04-08: semantic toy-curve screen for the Rondepierre-2015 `a = 0` core

What was checked locally:

- instantiated the paper's mixed Jacobian-affine `a = 0` core on the checked-in
  `toy61_b2` curve from `src/verifier.py` and `src/extended_verifier.py`,
- replayed the core exhaustively over all `61 x 61 = 3721` input pairs under
  Jacobian semantics `x = X / Z^2`, `y = Y / Z^3`,
- screened the reasonable sign conventions for the paper's delta terms.

Result:

- the semantically correct sign convention for the toy replay is
  `Ebar = Xq * Z^2 - X` and `Fbar = Yq * Z^3 - Y`,
- under that convention the core passes every ordinary mixed-add case,
  every inverse case, and every `Q = O` case,
- the exact category totals are:
  - `random`: `3480 / 3480`
  - `inv`: `60 / 60`
  - `q_inf`: `60 / 60`
  - `dbl`: `0 / 60`
  - `p_inf`: `1 / 61`

Interpretation:

- the core's semantic failure surface is much smaller than the earlier
  repository screens for incomplete Jacobian drop-in formulas,
- on the toy curve, the `a = 0` core already handles inverse pairs correctly,
- the remaining missing cases are concentrated in `P = O` and `P = Q`.

Status:

- promising,
- strong evidence that the masking shell does not need to repair inverse cases
  explicitly.

### 2026-04-08: minimal semantic shell around the `a = 0` core

What was checked locally:

- wrapped the toy-width `a = 0` core in the smallest semantic shell suggested
  by the previous result,
- used the branch structure:
  - if `P = O`, return `Q`,
  - else if `Q = O`, return `P`,
  - else if `Ebar = 0` and `Fbar = 0`, return `2P`,
  - else return the core output,
- replayed that shell exhaustively over all `3721` toy-curve input pairs.

Result:

- the minimal shell passes the full toy replay exactly,
- the exact category totals are:
  - `random`: `3480 / 3480`
  - `dbl`: `60 / 60`
  - `inv`: `60 / 60`
  - `p_inf`: `61 / 61`
  - `q_inf`: `60 / 60`

Interpretation:

- this is the first semantic combined candidate in the current arithmetic pass
  that survives exhaustive replay,
- the shell can be driven by values the `a = 0` core already computes,
  especially `Ebar` and `Fbar`,
- no explicit inverse-specific branch is needed in the toy-width candidate.

Status:

- promising,
- still below the bar for a real qubit result because the candidate is only a
  toy-width semantic replay.

### 2026-04-08: abstract live-range screen for a minimal core-plus-double shell

What was checked locally:

- built an abstract ISA-style candidate that carries both the `a = 0` core
  outputs and a dedicated doubling output triple to the final output selects,
- forced the doubling outputs to remain live until the end of the leaf rather
  than letting the slot search discard them early.

Result:

- even with the doubling outputs required to survive to the final selects,
  the abstract candidate still fits in `7` arithmetic slots,
- a more conservative nested-select variant that also keeps an explicit
  `Z = 1` passthrough source alive for the `P = O` path still fits in `7`
  arithmetic slots,
- the rough arithmetic shape of that screen is about `18` field
  multiplications, `11` field subtractions, and `4` constant multiplications.

Important limitation:

- this is only a live-range screen,
- it does not yet price the zero-test and equality-test machinery,
- it still does not price how the explicit `Z = 1` value is materialized inside
  a real leaf,
- it is not yet the Bos-style shared-intermediate construction.

Interpretation:

- the simple coexistence of the add output and the doubling output does not by
  itself force an `8`-slot leaf,
- the main remaining question is therefore semantic and arithmetic integration,
  not an obvious live-range impossibility.

Status:

- promising,
- still too abstract to treat as a candidate leaf.

### 2026-04-08: worst-case tmpand zero-test workspace screen

What was checked locally:

- priced the doubling predicate `Ebar = 0 and Fbar = 0` under the same
  temporary logical-AND equality-ladder style already used by the checked
  low-qubit lookup family,
- reused the repository's lookup-family workspace rule as the conservative
  proxy for a field-width zero test:
  `n - 1` non-Clifford and `n - 2` local workspace qubits for an `n`-bit word.

Result for `n = 256`:

- one field-width zero test costs `255` non-Clifford and `254` local workspace
  qubits under this conservative model,
- two zero tests plus one final one-bit conjunction cost `511` non-Clifford,
- if the two ladders can reuse the same scratch region sequentially, the
  temporary workspace is still about `255` qubits,
- if they must coexist, the temporary workspace rises to about `509` qubits.

Whole-oracle implication:

- the current central exact point is `1587` logical qubits, which decomposes as
  `6 * 256 + 49 + 1 + 1`,
- a hypothetical `7`-slot arithmetic leaf with sequential tmpand-style zero
  tests lands at about `7 * 256 + 255 + 49 + 1 + 1 = 2098` logical qubits
  before any extra branch-control bookkeeping,
- the same candidate with parallel zero-test scratch rises to about `2352`
  logical qubits,
- the gate total barely moves, reaching only about `22,754,342`
  non-Clifford.

Interpretation:

- under the repository's current temporary logical-AND workspace assumptions,
  a naive zero-test shell almost completely spends the `256`-qubit win gained
  by moving from `8` arithmetic slots to `7`,
- this is the first hard quantitative reason that the Bos-style shared shell is
  not just elegant but probably necessary,
- a `7`-slot Jacobian-style leaf only becomes a meaningful qubit win if its
  branch predicates use much less than a full-width tmpand scratch region or
  can reuse qubits already paid for elsewhere in the leaf.

Status:

- negative for the naive tmpand-predicate route,
- positive because it sharpens the design target for any viable shell.

### 2026-04-08: low-ancilla comparator literature screen for shell predicates

Primary sources:

- Khattar, Gidney, "Rise of conditionally clean ancillae for optimizing quantum
  circuits", arXiv 2407.17966, <https://arxiv.org/abs/2407.17966>
- Vandaele, "Asymptotically Optimal Quantum Circuits for Comparators and
  Incrementers", arXiv 2603.12917, <https://arxiv.org/abs/2603.12917>

What was checked locally:

- compared the shell-predicate bottleneck above against recent primary-source
  comparator results rather than the repository's older tmpand proxy,
- treated the needed `Ebar = 0` and `Fbar = 0` checks as a pair of
  quantum-classical or compare-to-zero subroutines.

Primary-source observations:

- Khattar and Gidney explicitly report an `n`-qubit quantum-classical
  comparator using about `3n` Toffolis with `log*(n)` clean ancillae,
- Vandaele explicitly reports comparator constructions with `Theta(n)` gate
  count and a provably minimal qubit count, including the classical-quantum
  setting.

Repository implication at `n = 256`:

- in the current oracle, `Q = O` already arrives as a checked lookup metadata
  bit, so the nontrivial shell predicates are `P = O` and the doubling test,
- the checked scaffold and toy-width shell suggest that `P = O` can be carried
  as an explicit one-bit accumulator-infinity flag rather than recomputed from a
  field-width zero test at every leaf,
- a single retained addition then needs only:
  - one compare-to-zero on `Ebar`,
  - one compare-to-zero on `Fbar`,
  - and one one-bit conjunction for the doubling branch,
- under the same `3n` comparator proxy at `n = 256`, that is about `1537`
  non-Clifford per retained addition,
- across the current `28` retained additions this is about `43,036`
  non-Clifford total,
- that is still tiny relative to the current central exact point,
- if the ancilla demand really stays in the `O(log*(n))` or minimal-qubit
  regime, a `7`-slot candidate could plausibly remain in roughly the
  mid-`1800`s logical-qubit range instead of collapsing back to `~2100`.

Important limitation:

- this is still only a literature-driven screen,
- no checked repository lowering exists yet for either comparator family,
- adapting those constructions to the exact shell predicates here is an
  inference from the primary-source abstracts, not a validated circuit result.

Interpretation:

- the shell direction is probably dead if it needs tmpand-style field-zero
  ladders,
- the same shell direction becomes interesting again if the predicate layer can
  be lowered through newer low-ancilla comparator techniques,
- this shifts the main open question from the add-versus-double arithmetic core
  to the exact reversible implementation of the predicate layer.

Status:

- promising as the most credible escape route from the tmpand-workspace wall,
- still unproven until a concrete comparator-based predicate lowering is
  transcribed and screened locally.

### 2026-04-08: comparator-based threshold screen for `7/6/5` arithmetic slots

What was checked locally:

- translated the comparator-based predicate screen into whole-oracle headline
  numbers using the current central exact decomposition
  `slots * 256 + 49 + 1 + 1`,
- modeled the doubling predicate as two `3n`-style comparators plus one final
  one-bit conjunction at `n = 256`,
- swept a small ancilla range `1..8` for the predicate layer.

Result:

- the gate total remains essentially unchanged at about `22,796,867`
  non-Clifford across the whole sweep,
- the qubit totals are approximately:
  - `7` arithmetic slots: `1844..1851` logical qubits,
  - `6` arithmetic slots: `1588..1595` logical qubits,
  - `5` arithmetic slots: `1332..1339` logical qubits,
  - `4` arithmetic slots: `1076..1083` logical qubits.

Interpretation:

- even an excellent low-ancilla predicate layer does not make a `7`-slot
  candidate competitive with Google's public qubit line,
- `6` slots would still remain above `1450`,
- the first `256`-bit slot-count target that plausibly beats `1450` while
  preserving the current gate advantage is `5` arithmetic slots,
- beating `1200` at full field width still requires `4` arithmetic slots.

Status:

- negative for the idea that `7` slots alone would be enough,
- positive because it isolates the real finish line: predicate work only keeps
  the Jacobian-shell direction alive if it can eventually pair with a
  `5`-slot-style arithmetic architecture or with field-width compression.

### 2026-04-08: observed slot floor for the current Jacobian-shell line

What was checked locally:

- reran the repository slot search against the two strongest abstract candidates
  in the current Jacobian-shell line:
  - the standalone Rondepierre `a = 0` mixed Jacobian-affine core,
  - the abstract minimal shell that keeps a dedicated doubling output triple
    alive to the final selects.

Result:

- the standalone `a = 0` core does not fit in `6` arithmetic slots,
- the abstract minimal shell also does not fit in `6` arithmetic slots,
- both candidates bottom out at `7` arithmetic slots.

Interpretation:

- this is the clearest local evidence so far that the present Jacobian-shell
  line is a `7`-slot class, not a plausible `5`-slot class,
- comparator work can still decide whether the line is viable at all,
  but it no longer looks like a path to beating Google on qubits at full
  `256`-bit slot width by itself,
- any full-width path to the `1450` line now appears to require either a new
  arithmetic architecture that changes the slot floor, or a separate field-width
  compression mechanism.

Status:

- negative for the idea that incremental refinement of the current
  Jacobian-shell candidate will reach the needed slot count,
- positive because it sharply narrows the remaining research space.

### 2026-04-08: width thresholds implied by the `7`-slot floor

What was checked locally:

- converted the `7`-slot floor into required effective field widths under the
  current central exact whole-oracle overhead model
  `slots * width + 49 + 1 + 1 + predicate_ancilla`,
- swept a small predicate-ancilla range `1..8`.

Result:

- for a `7`-slot design to beat `1450` logical qubits, the effective field-slot
  width must fall to about `198..199` bits,
- for a `7`-slot design to beat `1200`, the effective field-slot width must
  fall to about `163..164` bits,
- for a hypothetical `6`-slot design, the corresponding widths would be about
  `231..233` bits for `1450` and about `190..191` bits for `1200`.

Interpretation:

- once the current Jacobian-shell line is recognized as a `7`-slot class,
  beating Google by qubits no longer looks like a pure predicate problem,
- the line only remains interesting if it can be paired with a serious
  field-width compression mechanism,
- the width target is not mild: `7` slots still needs something like a
  `256 -> 199` compression just to reach `1450`.

Status:

- negative for any plan that treats the current shell as a complete answer on
  its own,
- positive because it gives an exact quantitative target for any future
  compressed-representation work.

### 2026-04-08: information-theoretic barrier for slot-local width compression

What was checked locally:

- compared the width targets above against the exact meaning of a live
  arithmetic slot in the current repository methodology,
- treated each arithmetic slot as an independently addressable reversible
  register that may need to hold an arbitrary secp256k1 field element.

Result:

- an exact reversible register that can hold an arbitrary element of
  `F_p` for secp256k1 must distinguish `p` states,
- since `p` is a 256-bit prime, this already requires `ceil(log2 p) = 256`
  logical qubits in any standalone slot-local encoding,
- therefore a target such as a `199`-qubit field slot cannot be realized by
  merely changing the basis or digit system of one independent field register.

Interpretation:

- the phrase "field-width compression" is dangerous unless it is stated more
  precisely,
- the repository cannot beat the `256`-qubit slot width by a simple exact
  re-encoding of an arbitrary field element,
- any real path below that line must instead do one of the following:
  - reduce the number of simultaneously independent field elements,
  - exploit semantic correlations across registers,
  - move to a distributed encoding where one "slot" no longer means one
    standalone field element,
  - or change the whole arithmetic architecture so the live objects are not
    generic full-field values.

Status:

- negative for naive interpretations of the earlier width targets,
- positive because it clarifies that the remaining search space is structural,
  not cosmetic.

### 2026-04-08: current exact leaf offers no easy correlated-register hook

What was checked locally:

- inspected the checked exact leaf and its slot-allocation artifact in the
  actual peak-live region,
- compared the live set at the peak against the hope that several registers
  might already be algebraically redundant enough to justify a shared encoding.

Result:

- the checked exact peak occurs very early at `pc = 8` in
  `artifacts/circuits/optimized_pointadd_secp256k1.json`,
- the slot-allocation artifact records `6` arithmetic slots live before the
  write and `7` during the write at that point,
- the live objects around that peak are essentially:
  - the running accumulator registers `qx, qy, qz`,
  - the looked-up affine registers `lx, ly`,
  - the first cross-term product `t0 = qx * lx`,
  - and the newly materialized sum `t1 = lx + ly`.

Interpretation:

- this is not a peak created by duplicated branch outputs or by obviously
  correlated shell metadata,
- it is the arithmetic core itself expanding two independently varying points
  into cross terms,
- therefore the current homogeneous mixed-add family does not seem to contain
  an easy local path where two or three live field registers can simply be
  "merged" into one shared reversible encoding without changing the arithmetic
  architecture.

Status:

- negative for the idea of an easy distributed-encoding retrofit inside the
  current exact leaf,
- positive because it points back to the right scale of change: new live
  objects, not just better packing of the old ones.

### 2026-04-08: `direct_lookup_seed` does not eliminate `P = O`, but makes a carried flag plausible

What was checked locally:

- inspected the checked scaffold structure and the semantic replay used by the
  compiler-verification project,
- compared the intended role of `direct_lookup_seed` against the actual seed
  cases observed in machine-checked replay.

Result:

- the scaffold does use a `direct_lookup_seed` for raw window `0` and then runs
  `28` retained additions,
- however, the checked semantic replay still records `seed_zero_cases = 9`
  out of `30` audited cases in
  `compiler_verification_project/artifacts/verification_summary.json`,
- in those cases the accumulator entering the first retained addition is still
  infinity.

Interpretation:

- `direct_lookup_seed` removes one leaf invocation, but it does not make the
  accumulator-nonzero condition structural,
- therefore the `P = O` path cannot simply be deleted from a Jacobian-shell
  design for the current oracle,
- however, because `P = O` is already a one-bit semantic condition on the
  running accumulator rather than a fresh lookup property, the natural shell
  implementation is to carry that condition explicitly between leaf calls,
- any shell simplification that assumes a nonzero retained-add accumulator is
  inconsistent with the checked repository semantics.

Status:

- negative for one previously tempting simplification,
- positive because it points to a cheaper shell design than a repeated
  full-width `Z = 0` comparator.

### 2026-04-08: toy shell is compatible with a carried accumulator-infinity flag

What was checked locally:

- revisited the successful toy-width shell through the lens of predicate state,
- separated the cases that require arithmetic comparison from the cases already
  determined by one-bit control information.

Result:

- in the toy shell, `Q = O` is already determined externally by lookup
  metadata,
- `P = O` can be treated as a carried one-bit property of the running
  accumulator,
- the only field-width arithmetic predicates needed inside the shell are then
  `Ebar = 0` and `Fbar = 0`,
- this reproduces the same exhaustive toy replay success while removing the
  need for a fresh `Z = 0` field comparator on every leaf.

Interpretation:

- the shell budget should be thought of as:
  - one persistent accumulator-infinity control bit,
  - lookup-infinity metadata already present in the checked oracle,
  - and the arithmetic comparators for `Ebar` and `Fbar`,
- this is a materially better fit to the repository methodology than repeatedly
  detecting infinity from the full field register state,
- the remaining exact-design question is how to materialize and update that
  carried bit coherently across leaf calls.

Important limitation:

- the carried-flag update rule has not yet been transcribed into a checked ISA
  lowering,
- it may require one additional persistent control qubit relative to the
  current central exact family, although that qubit impact is negligible
  compared to arithmetic-slot changes.

Status:

- promising,
- strong evidence that the predicate bottleneck is smaller than the earlier
  worst-case shell model suggested.

### 2026-04-08: explicit toy update rule for the accumulator-infinity flag

What was checked locally:

- derived and exhaustively tested a one-step update rule for the carried
  accumulator-infinity flag on the toy shell,
- used the same successful toy-width branch structure and the same
  `Ebar, Fbar` convention as the working shell replay.

Result:

- the exhaustive toy replay supports the exact next-flag rule
  `next_inf = if p_inf then q_inf else if q_inf then 0 else (Ebar = 0 and Fbar != 0)`,
- this rule matches the true affine result on all `3721` toy-curve input pairs,
- no additional field-width predicate beyond the already needed `Ebar` and
  `Fbar` tests appears in that update rule.

Interpretation:

- this is stronger than merely saying a carried flag is plausible,
- it means the shell can treat accumulator infinity as a true one-bit state
  variable whose update reuses the same arithmetic predicates already needed for
  the doubling-versus-core branch,
- the remaining cost question is therefore not whether a separate `P = O`
  detector exists, but how to encode this branch logic cleanly in the exact ISA
  boundary.

Status:

- promising,
- strong evidence that the shell-control layer is structurally simpler than the
  older field-zero-test model suggested.

### 2026-04-08: explicit toy branch partition for the shell

What was checked locally:

- enumerated the actual branch classes induced by the toy shell over all
  `3721` input pairs,
- expressed the shell as a five-way partition:
  - use `Q`,
  - use `P`,
  - use `2P`,
  - use `O`,
  - use core output.

Result:

- the exhaustive branch counts are:
  - `use_q`: `61`
  - `use_p`: `60`
  - `use_double`: `60`
  - `use_inf`: `60`
  - `use_core`: `3480`
- in this partition, `f0` is only relevant inside the already rare `e0 = 1`
  branch:
  - `e0 and f0` selects doubling,
  - `e0 and not f0` selects infinity,
  - `not e0` selects the ordinary core output.

Interpretation:

- this reinforces the idea that the shell should be designed as a staged
  control problem rather than as a flat bundle of independent comparators,
- the natural branch structure is:
  - first resolve the cheap carried one-bit cases `p_inf` and `q_inf`,
  - then resolve `e0`,
  - only then, if needed, resolve `f0`.

Status:

- promising,
- useful as a concrete guide for any future comparator-based lowering.

### 2026-04-08: immediate literature scan for a width-compression middle path

Primary sources checked:

- Luo et al. 2026, <https://arxiv.org/abs/2604.02311>
- Kahanamoku-Meyer, Yao 2024, <https://arxiv.org/abs/2403.18006>
- Gidney 2025, <https://arxiv.org/abs/2507.23079>
- Remaud, Vandaele 2025, <https://arxiv.org/abs/2501.16802>
- Gaur, Thapliyal 2025, <https://arxiv.org/abs/2506.17588>

What was checked locally:

- looked for primary-source arithmetic results that could plausibly reduce the
  effective field-slot width without immediately jumping to the known
  high-gate ECDLP pivots such as affine inversion or full RNS-style rewrites.

Result:

- Luo 2026 remains a true low-qubit ECDLP path, but it does so through the
  affine-plus-inversion pivot already identified earlier, not through a mild
  width compression of the current retained-add arithmetic,
- Kahanamoku-Meyer and Yao 2024 show that extremely low-ancilla multiplication
  is possible asymptotically, but in a generic integer-multiplication setting,
  not as a checked secp256k1 field-arithmetic lowering compatible with the
  current repository methodology,
- Gidney 2025 and Remaud-Vandaele 2025 materially strengthen the story for
  low-ancilla add/compare/control layers, but they do not by themselves shrink
  the `256`-bit field width,
- Gaur-Thapliyal 2025 shows RNS-related quantum multiplication ideas, but again
  in a direction much closer to the heavy arithmetic pivot than to a mild
  compression of the current oracle.

Interpretation:

- in the immediately visible literature, the landscape still splits into two
  camps:
  - predicate/control improvements that help ancilla pressure,
  - major arithmetic rewrites that change the whole representation,
- no convincing primary-source "middle path" has yet appeared that would turn
  the current `7`-slot Jacobian-shell line into a `~199`-bit effective-width
  design with the repository's current gate advantage intact.

Status:

- negative for the idea that a near-term paper transplant will solve the width
  problem,
- positive because it confirms that the next step really is original repository
  design work, not just literature collection.

### 2026-04-08: x-only Project-pseudomultiply-Recover screen

Primary source:

- Smith, "Efficient and secure algorithms for GLV-based scalar multiplication
  and their implementation on GLV-GLS curves", ePrint 2015/983,
  <https://eprint.iacr.org/2015/983.pdf>

What was checked locally:

- screened the short-Weierstrass x-only / pseudomultiply-recover line as a
  structural alternative where the live state is no longer a full affine or
  projective point,
- compared the paper's two-dimensional scalar-multiplication arithmetic count
  against the repository's current retained-add arithmetic path.

Result:

- the paper's two-dimensional short-Weierstrass path has leading arithmetic cost
  about `(14β + 12)M + (9β + 3)S` before lower-order additions and recovery,
- at `β = 256` and with the conservative screen `S/M = 1`, that is about
  `5903` multiplication-equivalent steps,
- the current checked retained-add path uses only `28 * 11 = 308`
  field-multiplication instances across the arithmetic leaf calls,
- the x-only structural path is therefore roughly `19.2x` heavier at the
  multiplication-dominant level even before pricing recovery overhead.

Interpretation:

- x-only state reduction is a real structural idea, unlike the earlier naive
  width-compression language,
- but in the immediately relevant short-Weierstrass form it looks badly
  misaligned with the repository's gate priorities,
- this makes it a useful negative reference point: not every structural escape
  from full `(X,Y,Z)` state is automatically compatible with the
  sub-`30M` / sub-`40M` goal.

Status:

- useful as a structural comparison class,
- not promising as a near-term gate-capped replacement for the checked oracle.

### 2026-04-08: carry-save arithmetic as a negative reference point

Primary source:

- Gossett, "Quantum Carry-Save Arithmetic", arXiv quant-ph/9808061,
  <https://arxiv.org/abs/quant-ph/9808061>

What was checked locally:

- screened carry-save arithmetic only as a structural comparison class for the
  current search,
- compared its advertised qubit/depth tradeoff against the repository's
  explicit objective, which is to reduce logical qubits without surrendering
  the current gate advantage.

Primary-source observation:

- the paper explicitly states that carry-save techniques reduce gate delay from
  `O(N^3)` to `O(N log N)` at the cost of increasing the number of qubits from
  `O(N)` to `O(N^2)`.

Interpretation:

- even before any secp256k1-specific adaptation, this is the opposite direction
  from the current repository objective,
- carry-save style redundant arithmetic may still matter for depth-focused
  architectures, but it is a bad fit for the present low-qubit search.

Status:

- useful only as a negative reference point,
- not promising for the current qubit frontier.

### 2026-04-08: gate headroom for a comparator-plus-compression branch

What was checked locally:

- started from the then-current central exact point `22,753,831`,
- added the corrected comparator-predicate estimate for the current
  `28` retained additions, about `43,036` non-Clifford total,
- measured the remaining slack against the repository's practical gate caps.

Result:

- after comparator predicates, the oracle still sits at about `22,796,867`
  non-Clifford,
- the remaining headroom is about:
  - `7,203,133` to stay below `30M`,
  - `17,203,133` to stay below `40M`,
  - `47,203,133` to stay below Google's public `70M` line,
- per retained addition, that is roughly:
  - `257,255` non-Clifford of slack under `30M`,
  - `614,398` under `40M`,
  - `1,685,826` under `70M`.

Interpretation:

- the repository still has a large gate budget for experimental
  width-compression arithmetic,
- the main issue is not a lack of gate headroom,
- the main issue is whether a compressed representation can deliver the
  required `~199`-bit effective width for the `7`-slot class, or whether a new
  arithmetic architecture is needed to change the slot floor itself.

Status:

- positive for further compression experiments under the current gate caps,
- negative for the idea that gates are the main blocker at this stage.

## Immediate next experiment

The next concrete research step should no longer be another literature scan.

The best next move is now narrower and more concrete:

- build a semantically honest abstract leaf that keeps the successful toy shell
  shape,
- make the branch structure depend only on:
  - lookup-infinity metadata already present in the checked oracle,
  - a carried accumulator-infinity flag,
  - and the arithmetic values already produced in the core,
- organize the predicate layer as a staged branch partition:
  - `p_inf` / `q_inf` first,
  - then `e0`,
  - then `f0` only inside the `e0 = 1` branch,
- stop using the repository's tmpand equality family as the default predicate
  proxy for `Ebar = 0` and `Fbar = 0`,
- instead, transcribe one concrete low-ancilla comparator-based predicate layer
  and rerun both the slot screen and the whole-oracle qubit arithmetic,
- price the missing `P = O` passthrough machinery, especially the need to
  surface an explicit Jacobian `Z = 1` when the carried flag says the
  accumulator is infinity,
- treat any future "compression" work as structural or distributed encoding
  work, not as a simple sub-`256` standalone field-slot re-encoding.

That experiment would be the first one capable of upgrading the current
toy-width semantic success into a repository-relevant arithmetic candidate.

## Literature scan

### Renes-Costello-Batina 2015

Source:

- <https://eprint.iacr.org/2015/1060>

Relevant observation:

- for `a = 0`, the complete mixed-add formula is already cheaper than full
  complete projective addition,
- the paper explicitly argues that complete Jacobian formulas would require
  higher bidegree and are therefore unlikely to beat the homogeneous complete
  formulas cleanly,
- the paper also warns that ruling out exceptional pairs is much harder in
  fixed-base, multiscalar, and endomorphism-heavy settings than in the simpler
  variable-base paths where incomplete formulas are often used safely.

Repository verdict:

- this paper supports treating the current leaf family as near-ceiling inside
  the "complete homogeneous mixed-add" design space,
- it also supports treating "just prove incomplete additions are unreachable"
  as a hard whole-algorithm problem rather than a small local cleanup.

### Massolino-Renes-Batina 2016

Source:

- <https://eprint.iacr.org/2016/1133.pdf>

Relevant observation:

- this work parallelizes the complete Weierstrass formulas in hardware,
  confirming that the formulas remain attractive when additions are cheap and
  multiple multipliers are available,
- it does not introduce a new complete arithmetic law that changes the formula
  class.

Repository verdict:

- useful as evidence that the current complete arithmetic path is not an
  obviously bad engineering choice,
- not a source of a new low-qubit formula class.

### Sedlacek-Chi-Dominguez-Jancar-Brumley 2021

Source:

- <https://eprint.iacr.org/2021/1595>

Relevant observation:

- the paper studies exceptional points for short-Weierstrass formulas across
  projective, Jacobian, modified Jacobian, w12, and xyzz coordinates,
- it explicitly treats the Renes formulas as complete and the other common
  coordinate families as having exceptional pairs.

Repository verdict:

- this is strong negative evidence against trying to salvage incomplete
  Jacobian-style formulas inside the current retained-window schedule.

### Hamburg 2020

Source:

- <https://eprint.iacr.org/2020/437>

Relevant observation:

- complete short-Weierstrass ladders with `6` or even `5` registers exist,
- the formulas target regular scalar-multiplication ladders with per-bit
  structure, not a retained-window two-scalar addition oracle.

Repository verdict:

- interesting long-horizon direction for a full oracle rewrite,
- not a near-term replacement for the current retained-window architecture.

The main reason is structural: the current oracle realizes one direct seed plus
retained window additions, whereas a ladder rewrite would move back toward a
per-bit schedule. Without a much deeper redesign, that is likely to lose badly
on gate count even if the live register count is attractive.

### Häner-Jaques-Naehrig-Roetteler-Soeken 2020

Source:

- <https://eprint.iacr.org/2020/077>

Relevant observation:

- this paper improves quantum affine Weierstrass point-add circuits and studies
  explicit qubit/depth/T-count tradeoffs,
- the work is a useful reminder that lower-register arithmetic can come from
  moving to affine formulas and better inversion handling rather than from
  squeezing the current complete homogeneous leaf.

Repository verdict:

- relevant as a whole-arithmetic-redesign reference,
- not yet a credible near-term replacement for the current exact frontier under
  the repository's preferred gate caps, because it points toward inversion-heavy
  arithmetic rather than a drop-in improvement of the existing leaf.

### Bos-Costello-Longa-Naehrig 2014

Source:

- <https://eprint.iacr.org/2014/130>

Relevant observation:

- for fixed-base Weierstrass scalar multiplication, the paper explicitly states
  that one generally cannot prove that the running point will never equal, or be
  the inverse of, one of the many precomputed table values,
- instead of paying for the much more expensive mathematically complete
  formulas, the paper proposes "complete masked" Jacobian-plus-affine and
  Jacobian-plus-Jacobian additions that preserve the multiplication/squaring
  counts of the incomplete formulas,
- the masking route handles addition, doubling, inverse pairs, and the point at
  infinity inside one constant-time routine.

Repository verdict:

- this is the first external direction that meaningfully aligns with the local
  repository findings,
- it supports the negative result that fixed-base or multiscalar retained-window
  paths should expect exceptional pairs,
- it also suggests a more interesting follow-up than RCB-versus-Jacobian:
  instead of searching for a mathematically complete formula, search for a
  quantum-friendly masking construction that keeps the incomplete arithmetic
  footprint close to the cheaper Jacobian mixed-add path.

Open caveats:

- the paper studies `a = -3`, not secp256k1's `a = 0`,
- the online fixed-base path still assumes a conventional fixed-base scalar
  multiplication algorithm rather than the repository's exact two-scalar oracle,
- its "complete masked" construction is promising as a design pattern, not yet
  as a directly reusable formula set.

### GLV endomorphism directions

Sources:

- implementation literature on secp256k1 endomorphism-based scalar
  decomposition,
- regular w-NAF / Straus-Shamir multiscalar methods used with GLV-style splits.

Relevant observation:

- secp256k1 has a natural `j = 0` endomorphism, so one scalar multiplication can
  be rewritten as a shorter multiscalar multiplication,
- this is attractive in conventional implementations because it replaces one
  long scalar multiplication by two shorter components and can reduce lookup
  table sizes at a fixed security level.

Local repository screen:

- the current exact oracle already pushes most doublings into classical
  precomputation and pays mainly for retained additions,
- a GLV rewrite with regular online interleaving would reintroduce an online
  doubling schedule,
- for a single scalar split into two `128`-bit components, an interleaving
  schedule with width `w` still pays `128` doublings online, whereas the current
  fixed-window path pays only `15` retained additions after the seed,
- even at `w = 16`, a favorable Straus-style estimate gives `8` combined
  additions plus `128` doublings; this is not obviously better under the
  repository's gate model.

Repository verdict:

- GLV is worth keeping in the long-horizon idea set because it changes the
  whole scalar-multiplication architecture,
- it is not a clear near-term win under the repository's exact gate-capped
  retained-window model.

### Rondepierre 2015

Source:

- Rondepierre, "Revisiting Atomic Patterns for Scalar Multiplications on
  Elliptic Curves", ePrint 2015/408, <https://eprint.iacr.org/2015/408>

Relevant observation:

- the paper targets secure scalar multiplication and double scalar multiplication
  on short-Weierstrass curves,
- it gives an `a = 0` mixed Jacobian-affine addition pattern with
  `9` multiplication-equivalent field products (`2S + 7M`) and `8` additions,
- it explicitly claims good performance for double scalar multiplication with
  the Straus-Shamir trick.

Local repository screen:

- this is one of the closest architectural matches in the literature because the
  repository oracle also computes a two-scalar relation `[a]G + [b]H`,
- however, the online schedule is still bit-level and doubling-heavy,
- using the paper's own `12M + 15A + 3S` style per-bit cost for double scalar
  multiplication with `S/M = 1`, the arithmetic path is roughly
  `256 * (12 + 3) = 3840` multiplication-equivalent steps,
- the current checked retained-add path uses `28 * 11 = 308`
  field-multiplication instances across the arithmetic leaf calls.

Interpretation:

- despite the attractive `a = 0` mixed-add formula, a Straus-Shamir style
  rewrite looks roughly `12.5x` heavier than the current repeated-add path when
  screened through the repository's multiplication-dominant cost model,
- this makes it a poor near-term direction for preserving the current
  sub-`30M` and sub-`40M` gate ambitions.

Status:

- useful as a source of `a = 0` mixed Jacobian-affine arithmetic ideas,
- not promising as a full oracle rewrite under the repository's current gate
  priorities.

### Co-Z ladder literature

Source:

- Goundar, Joye, Miyaji 2010, <https://eprint.iacr.org/2010/309>

Relevant observation:

- co-Z arithmetic and conjugate addition help regular binary ladders and can
  reduce register pressure in ladder-style scalar multiplication.

Repository verdict:

- same long-horizon status as the Hamburg ladder path,
- not a drop-in path for the checked-in retained-window oracle.

### 2026-04-08: GLV endomorphism regime check

Primary source:

- Longa, Sica, "Four-Dimensional Gallant-Lambert-Vanstone Scalar
  Multiplication", discussed operationally in Faz-Hernandez et al.,
  "Faster software for fast endomorphisms", ePrint 2015/036,
  <https://eprint.iacr.org/2015/036>

What was checked locally:

- compared the repository's current retained-window oracle against the exact
  shape of a GLV-style rewrite for secp256k1,
- used the checked scaffold facts:
  - two `256`-bit scalars,
  - `16`-bit windows,
  - one direct seed,
  - `28` retained optimized leaf calls and `3` classical tail elisions.

Relevant external observation:

- the source explicitly notes that, when precomputation is already available at
  runtime, the main software advantage of GLV becomes much smaller because the
  baseline implementation is already using interleaving and lookup-based scalar
  multiplication rather than paying raw online doublings.

Local screen:

- a secp256k1 GLV rewrite would split each `256`-bit scalar into two
  approximately `128`-bit scalars,
- for the repository's current two-scalar relation `[a]G + [b]H`, that means
  moving from `2 x 256` bits of scalar volume to `4 x 128`, which is still
  `512` total scalar bits,
- under the current `16`-bit windowing discipline, this preserves the raw
  window volume exactly: `32` scalar windows before and `32` after,
- the obvious combined-lookup interpretation becomes strictly harder because the
  current exact scaffold uses `2` lookup channels per leaf, whereas a direct GLV
  generalization wants `4` coefficient streams attached to
  `G`, `psi(G)`, `H`, and `psi(H)`.

Interpretation:

- GLV is a strong software idea when the baseline spends a lot of work on
  online doublings or long scalar ladders,
- the checked repository oracle already moved most of that cost into fixed-base
  lookup structure,
- so the near-term effect of GLV here is not "half-length scalars" but "same
  total window volume plus a harder lookup/multiscalar contract".

Status:

- useful as a structural reference,
- not promising as a near-term qubit-reduction path under the current retained
  window oracle.

### Khattar-Gidney 2024

Source:

- <https://arxiv.org/abs/2407.17966>

Relevant observation:

- the paper explicitly studies how to trade ancilla demand against controls,
- its reported comparator headline is directly relevant to shell predicates:
  about `3n` Toffolis for an `n`-bit quantum-classical comparator with
  `log*(n)` clean ancillae.

Repository verdict:

- this is currently the most relevant external lead for implementing
  `Ebar = 0` and `Fbar = 0` without paying a tmpand-style `254`-qubit scratch
  region per field-width zero test,
- it does not solve the arithmetic-shell problem by itself, but it may remove
  the main workspace blocker.

### Vandaele 2026

Source:

- <https://arxiv.org/abs/2603.12917>

Relevant observation:

- the paper explicitly claims `Theta(n)`-gate comparator circuits with a
  provably minimal qubit count,
- it also covers the classical-quantum comparator setting that is closest to
  compare-to-zero shell predicates.

Repository verdict:

- this strengthens the case that the shell bottleneck may be in the repository's
  current predicate proxy rather than in the arithmetic architecture itself,
- it is now a direct candidate source for the next concrete lowering
  experiment.

### 2026-04-08: zero-test versus comparator distinction

What was checked locally:

- revisited the shell predicates `Ebar = 0` and `Fbar = 0` under the actual
  repository representation boundary,
- asked whether these are really full comparators or only exact zero-tests on
  canonical field-element registers.

Local representation fact:

- the repository stores field elements in exact fixed-width canonical `Fp`
  registers,
- under that representation, deciding `value = 0` is not a modular
  compare-to-constant problem; it is a zero-test on a `256`-bit register.

Consequence:

- the relevant primitive can be treated as an open-control multi-controlled
  `X` or `AND/NOR` reduction, not necessarily as a general-purpose comparator,
- this is structurally easier than the generic comparator proxy used in earlier
  rough screens.

Simple gate screen:

- using the standard `2n`-Toffoli style proxy for an `n`-controlled `X` with a
  constant number of clean ancillae, one zero-test compute-plus-uncompute costs
  about `4n`,
- at `n = 256`, that is `1024` non-Clifford per zero-test,
- two such predicates per retained leaf give an upper proxy of `2048`
  non-Clifford,
- across `28` retained additions this contributes about `57,344`
  non-Clifford total,
- adding that to the current central exact point gives about
  `22,811,175` non-Clifford before any further shell simplifications.

Qubit implication:

- the same proxy is compatible with a constant-size shell workspace rather than
  a `254`-qubit tmpand ladder,
- under the current `7`-slot shell accounting, this keeps the whole-oracle
  qubit picture in the same `1843..1846` band already identified for low-ancilla
  shell controls.

Interpretation:

- the shell predicates are more naturally a zero-test problem than a comparator
  problem,
- this makes the Jacobian-shell line look stronger on qubits than the earlier
  tmpand proxy suggested,
- it still does not turn the `7`-slot class into a Google-level qubit path, but
  it materially strengthens the case that a real exact sub-`2100` improvement
  could come from shell engineering.

### 2019/1166 as a regime check

Primary source:

- Schwabe, Sprenkels, "The complete cost of cofactor h=1", ePrint 2019/1166,
  <https://eprint.iacr.org/2019/1166>

Relevant observation:

- the paper explicitly studies constant-time variable-base scalar multiplication
  on prime-order Weierstrass curves using the Renes-Costello-Batina complete
  formulas,
- its stated comparison target is the cost of cofactor-one complete formulas
  against widely used Montgomery and twisted-Edwards systems that come with a
  nontrivial cofactor.

Repository verdict:

- this is consistent with the repository's current reading that complete
  short-Weierstrass arithmetic is not a temporary stopgap for prime-order
  curves; it is the realistic base-field regime once the low-torsion model
  families are unavailable,
- this makes the search space narrower but clearer: the next win is more likely
  to come from structural live-object changes or shell engineering than from a
  magical base-field model swap.

### 2026-04-08: staged shell-control budget

What was checked locally:

- priced the qubit effect of carrying explicit shell-state controls on top of a
  hypothetical `7`-slot retained-add leaf,
- kept the current central exact family's fixed non-arithmetic budget:
  `49` lookup workspace qubits and `1` live phase bit.

Result:

- with `7` arithmetic slots, total qubits are `1841 + control_slots`,
- this gives:
  - `1843` qubits for `2` control slots,
  - `1844` qubits for `3` control slots,
  - `1845` qubits for `4` control slots,
  - `1846` qubits for `5` control slots.

Interpretation:

- once the arithmetic leaf drops from `8` slots to `7`, the exact number of
  shell-state control bits matters very little for headline qubits,
- the real question is still whether the shell can buy a genuine arithmetic-slot
  drop without reintroducing a large tmpand-style workspace.

### 2026-04-08: extension-field rescue screen

What was checked locally:

- priced the qubit effect of rescuing torsion-based alternative models by moving
  from `Fp` arithmetic to `Fp^d` arithmetic,
- kept the same optimistic `7` arithmetic-slot target and the current central
  exact family's fixed non-arithmetic budget.

Result:

- a single generic `Fp^d` register costs at least `256d` logical qubits when
  expanded back to exact `Fp` storage,
- under that optimistic proxy, a `7`-slot arithmetic leaf costs:
  - `3635` logical qubits at `d = 2`,
  - `5427` logical qubits at `d = 3`.

Interpretation:

- even before pricing any extension-field gate overhead, the qubit budget is
  already far worse than the current exact frontier,
- this effectively kills the obvious "use an extension field to unlock a better
  curve model" escape hatch for the repository's low-qubit objective.

### 2026-04-08: first-nonzero seed screen

What was checked locally:

- compared a hypothetical scaffold rewrite that seeds from the first nonzero
  window against the already studied carried-`accumulator_infinity` shell,
- cross-checked the repository artifacts that observe seed-zero behavior.

Artifact facts:

- the compiler-side semantic replay explicitly records `seed_zero_cases = 9` in
  `compiler_verification_project/artifacts/verification_summary.json`,
- the repository's lighter `256`-case scaffold audit records
  `seed_zero_cases = 0` in
  `artifacts/verification/extended/scaffold_schedule_summary.json`,
- these are different audits with different deterministic sample sets, so they
  should not be read as contradictory.

Structural observation:

- the shell branch
  `if p_inf then use_q else if q_inf then use_p else ...`
  already implements a lazy first-nonzero seed,
- after the first nonzero lookup point arrives, the carried `p_inf` flag flips
  to `0` and the schedule reduces to ordinary retained additions,
- replacing the fixed seed with an explicit "first nonzero window" search does
  not remove the need for the same `q_inf` metadata and the same carried
  accumulator-infinity state,
- on fully quantum window registers, any explicit first-nonzero search would
  merely rebuild equivalent prefix-control logic at the scaffold level.

Interpretation:

- "first nonzero seed" is not a new architecture frontier here,
- it is best understood as a different description of the carried-flag shell
  that is already under study,
- the real open problem therefore remains the low-ancilla predicate layer and
  the `7`-slot arithmetic body, not the seed discipline by itself.

### 2026-04-08: `phase_a` exceptional-profile screen

What was checked locally:

- analyzed the exact retained `phase_a` schedule window by window using the
  repository's actual `16`-bit windowing and secp256k1 subgroup order,
- for each retained `phase_a` window `j = 1..15`, tested whether any reachable
  lower-window accumulator can satisfy either:
  - doubling: `lower = digit * 2^(16j) mod n`,
  - inverse: `lower + digit * 2^(16j) = n`,
- used the fact that every `lower` in `[0, 2^(16j))` is realizable by the
  lower `j` windows.

Result:

- no doubling witnesses exist for any retained `phase_a` window,
- no inverse witnesses exist for retained `phase_a` windows `1..14`,
- exactly one inverse witness class exists at retained `phase_a` window `15`,
  namely the already identified top-window decomposition of `n`.

Concrete sample:

- for `window = 15`, the exceptional digit is `0xffff`,
- the corresponding lower contribution is
  `1766847064778384329583297500742918083407097331215962105700739806324474177`.

Interpretation:

- the retained `phase_a` path is much less hostile than the generic shell view
  suggested,
- windows `1..14` in `phase_a` do not need doubling or inverse handling at all,
- retained `phase_a` window `15` needs only the inverse branch, not a doubling
  branch,
- the full shell is still needed for `phase_b`, but a phase-specialized hybrid
  policy now looks materially more realistic.

Simple gate consequence under the zero-test proxy:

- a full shell on all `28` retained leaves would use `56` zero-tests,
- a phase-specialized shell uses only `27`:
  - `0` on retained `phase_a` windows `1..14`,
  - `1` on retained `phase_a` window `15`,
  - `2` on each of the `13` retained `phase_b` windows,
- under the earlier `1024`-non-Clifford compute-plus-uncompute proxy per
  zero-test, this changes the shell overhead from `57,344` down to `27,648`.

Why this matters:

- the Rondepierre `a = 0` core advertises `9` multiplication-equivalent field
  products versus the current complete leaf's `11`,
- even before pricing additions, that is a gross arithmetic saving of
  `56` multiplication-equivalents over `28` retained calls,
- under the repository's exact `256`-bit schoolbook multiplier pricing, this is
  about `3,698,632` non-Clifford of gross arithmetic headroom,
- this is much larger than the phase-specialized shell's rough zero-test budget.

Status:

- this is the strongest positive signal so far for a gate-competitive Jacobian
  shell path,
- it still does not change the conclusion that the `7`-slot class is not a
  Google-level qubit path by itself.

### 2026-04-08: `phase_b` exceptional-profile screen

What was checked locally:

- revisited the retained `phase_b` schedule under the repository's actual
  scaffold semantics,
- asked whether the same kind of per-window pruning found for `phase_a` is
  available once the second scalar is attached to a variable base
  `H = [h]G`.

Structural observation:

- a retained `phase_b` lookup has the form
  `lookup = [digit * 2^(16j)] H`,
- over the prime-order subgroup, every nonzero scalar
  `digit * 2^(16j)` is invertible modulo `n`,
- as `h` ranges over the subgroup, the corresponding lookup point ranges over
  the full subgroup as well.

Immediate consequence:

- for every retained `phase_b` window and every nonzero digit, there exist
  choices of `a` and `h` that make the pre-window accumulator equal to the
  lookup point, producing a doubling witness,
- likewise there exist choices that make the accumulator the inverse of the
  lookup point, producing an inverse witness,
- unlike retained `phase_a`, retained `phase_b` does not admit a useful
  per-window pruning of the exceptional branches.

Interpretation:

- the current hybrid opportunity is one-sided:
  - retained `phase_a` is mostly safe,
  - retained `phase_b` still needs the full exceptional-handling shell.

### 2026-04-08: hybrid-shell gate proxy

What was checked locally:

- combined the current central exact point with:
  - the `phase_a` pruning screen,
  - the earlier zero-test proxy,
  - the arithmetic headline of the Rondepierre `a = 0` core.

Arithmetic-only proxy:

- then-current central exact point:
  `22,753,831` non-Clifford,
- current complete leaf: `11` multiplication-equivalent field products,
- Rondepierre `a = 0` core: `9`,
- over `28` retained calls this is a gross saving of `56`
  multiplication-equivalents,
- under the repository's exact `256`-bit schoolbook multiplier pricing
  (`66,047` non-Clifford), that is `3,698,632` gross arithmetic headroom.

Hybrid shell proxy:

- retained `phase_a` windows `1..14` pay no shell predicates,
- retained `phase_a` window `15` pays one zero-test,
- retained `phase_b` windows `0..12` pay two zero-tests each,
- under the `1024` non-Clifford compute-plus-uncompute proxy per zero-test, the
  total shell overhead is `27,648`.

Optimistic gate proxy:

- combining only those two effects gives
  `22,753,831 - 3,698,632 + 27,648 = 19,082,847`.

What this does and does not mean:

- this is not a modeled headline result and not a checked circuit,
- it ignores the detailed cost of shell selects, passthrough routing, and the
  exact add/sub profile of the replacement core,
- but it is the first rough screen in this pass that points to a potentially
  gate-improving Jacobian-shell branch rather than merely a gate-neutral one.

### 2026-04-08: shell select-overhead bound

What was checked locally:

- bounded the remaining uncertainty from shell routing and output selection
  under the repository's exact arithmetic cost model,
- used the checked current-leaf histogram and the exact select-kernel cost from
  the generated arithmetic lowerings.

Repository facts:

- the current exact leaf already contains `3` `select_field_if_flag`
  operations,
- the arithmetic lowering prices each field-width select at `255`
  non-Clifford.

Conservative shell bound:

- even a fairly pessimistic staged shell with `12` extra field selects per
  retained leaf contributes only
  `12 * 255 * 28 = 85,680` non-Clifford,
- for comparison, more pessimistic envelopes are still small:
  - `6` extra selects per leaf: `42,840`,
  - `9` extra selects per leaf: `64,260`,
  - `15` extra selects per leaf: `107,100`,
  - `18` extra selects per leaf: `128,520`.

Interpretation:

- output routing and branch selection are not the dominant uncertainty in the
  current Jacobian-shell gate screen,
- the gross arithmetic headroom from the `11 -> 9`
  multiplication-equivalent shift remains larger by more than an order of
  magnitude than any reasonable select-overhead estimate,
- this further strengthens the claim that the next serious blocker is semantic
  materialization of the shell, not arithmetic cost plausibility.

### 2026-04-08: explicit staged-select schedule

What was checked locally:

- wrote down the concrete branch partition already supported by the toy shell:
  - `use_q` if `p_inf`,
  - `use_p` if `!p_inf && q_inf`,
  - `use_double` if `!p_inf && !q_inf && e0 && f0`,
  - `use_inf` if `!p_inf && !q_inf && e0 && !f0`,
  - `use_core` if `!p_inf && !q_inf && !e0`,
- counted how many exact field-width selects are needed to realize that
  partition as a staged output-selection network over `(X, Y, Z)`.

Concrete staged schedule:

- stage 1: choose `double` versus `inf` inside the exceptional branch using
  `f0`:
  - `3` field selects,
- stage 2: choose `core` versus exceptional output using `e0`:
  - `3` field selects,
- stage 3: choose `previous` versus passthrough `P` using `q_inf`:
  - `3` field selects,
- stage 4: choose `previous` versus passthrough `Q` using `p_inf`:
  - `3` field selects.

Result:

- the shell can be written with an explicit `12` field-select schedule per
  retained leaf,
- under the repository's exact `255`-non-Clifford select kernel, that is
  `12 * 255 = 3,060` per retained leaf and `85,680` over all `28` retained
  additions.

Refined optimistic proxy:

- starting from the arithmetic-only hybrid proxy `19,082,847`,
- adding the explicit staged-select schedule gives
  `19,168,527`.

Interpretation:

- even a concrete staged-shell selection network keeps the Jacobian-shell line
  far below the current central exact point in this rough proxy,
- this makes the remaining uncertainty overwhelmingly semantic rather than
  arithmetic-cost-driven.

## Current verdicts

### Promising

- adapting the Bos 2014 complete-masking skeleton to an `a = 0` mixed
  Jacobian-affine addition law, most plausibly using the Rondepierre 2015
  `a = 0` arithmetic core as the dedicated add path,
- phase-specialized shell policies that exploit the much narrower exceptional
  profile of retained `phase_a`,
- the smaller semantic shell suggested by the toy replay:
  `P = O`, `Q = O`, and `Ebar = Fbar = 0` for doubling,
- comparator-based predicate layers with sublinear or minimal ancilla, if they
  can be adapted to exact field-zero detection in this shell,
- whole-oracle rewrites that globally remove exceptional pairs rather than
  trying to patch them locally,
- new complete coordinate systems or addition laws that genuinely beat the
  current homogeneous mixed-add peak,
- ladder-like rewrites only if they are evaluated as a full oracle replacement,
  not as a local leaf substitution.

### Not promising

- searching for a `7`-slot result inside the existing complete homogeneous
  mixed-add family,
- incomplete Jacobian or xyzz leaf substitutions inside the current scaffold,
- naive coherent fallback that always prices both mixed-add and doubling,
- expecting the current Jacobian-shell candidate family to slide from `7`
  arithmetic slots down to `5` through local schedule cleanup,
- tmpand-style full-width zero-test ladders as the default implementation of
  the shell predicates,
- base-field Edwards, Montgomery, or Hessian rewrites for secp256k1,
- treating "first nonzero seed" as a separate arithmetic breakthrough rather
  than as a restatement of the carried-`accumulator_infinity` shell.

## Next questions

1. Is there any complete arithmetic law for prime-order short Weierstrass
   curves that is genuinely outside the Renes/Bosma-Lenstra homogeneous family
   and still compatible with a fixed-window retained-add oracle?
2. Is a ladder-based full rewrite even remotely competitive against the current
   `28` retained additions plus direct-seed scaffold under the repository's exact arithmetic
   cost model?
3. Can a whole-oracle redesign prove that exceptional pairs are unreachable,
   rather than paying for completeness inside every retained addition?
4. Can the Bos 2014 masking construction be rederived for secp256k1's `a = 0`
   case by replacing the `a = -3` mixed-add core with the `a = 0` mixed
   Jacobian-affine core from Rondepierre 2015, while keeping the multiplication
   footprint near the dedicated add path?
5. Can the shell predicates `P = O` and `Ebar = Fbar = 0` be implemented with a
   comparator family whose ancilla demand is closer to the 2024-2026
   low-ancilla literature than to the repository's tmpand lookup ladders?
6. Is there any structural live-object redesign that does not rely on the
   low-torsion model families already ruled out by secp256k1's base-field group
   order?

## Current best research candidate

The most interesting arithmetic-architecture direction currently visible from
the literature is not a new coordinate system and not a ladder rewrite.

It is the following synthesis:

- use the Bos 2014 "complete masked" idea as the exception-management shell,
- but swap in an `a = 0` mixed Jacobian-affine arithmetic core rather than the
  paper's `a = -3` formulas,
- use Rondepierre 2015 as the best currently identified source of a compact
  `a = 0` mixed Jacobian-affine core.

Why this is the current top candidate:

- Bos 2014 is the only source found so far that explicitly targets
  fixed-base and multi-scalar Weierstrass settings where exceptional pairs
  really matter, and does so without paying the full cost of mathematically
  complete formulas,
- Rondepierre 2015 is the only source found so far in this pass that gives an
  explicit `a = 0` mixed Jacobian-affine arithmetic pattern that is cheaper than
  the current complete leaf's arithmetic footprint,
- both sources point toward keeping mixed Jacobian-affine arithmetic and moving
  the exception handling into a masking shell, which is much closer to the
  repository's priorities than a per-bit ladder rewrite,
- the toy-width semantic shell built around the `a = 0` core already passes
  exhaustive replay with only `P = O`, `Q = O`, and `Ebar = Fbar = 0` doubling
  handling,
- the abstract live-range screens show that neither carrying a doubling output
  triple to the end of the leaf nor keeping an explicit `Z = 1` passthrough
  source alive automatically breaks the `7`-slot target.

What this no longer claims:

- it no longer looks like a complete route to Google's public qubit line at
  full `256`-bit slot width,
- the current evidence instead says it is the best near-term candidate for a
  real exact arithmetic improvement, while a true headline qubit breakthrough
  would still require a different slot floor or a deeper structural change in
  the live objects.

Why this is still unproven:

- Bos 2014 is written for `a = -3`,
- Rondepierre 2015 is not itself a complete masking construction,
- no secp256k1-width checked-in circuit exists for the combined idea,
- the remaining shell details, especially the predicate layer and the `P = O`
  passthrough path, are still unresolved,
- the conservative tmpand-style predicate model is too expensive in qubits to
  deliver a meaningful win even if the arithmetic leaf reaches `7` slots.

What has now been ruled out around it:

- the nearby low-torsion complete-model families that would normally be the
  next place to look, namely base-field Edwards, Montgomery, and Hessian
  rewrites, are structurally blocked by secp256k1's lack of rational `2`-, `3`-,
  and `4`-torsion.
