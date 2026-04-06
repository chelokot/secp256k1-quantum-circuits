# Proof sketch for the exact secp256k1 kickmix netlist

1. `pointadd_exact_kickmix.json` is an exact micro-instruction netlist for the map `Q <- Q + P[k]`.
2. The verifier interprets each opcode with deterministic arithmetic semantics over the secp256k1 prime field.
3. The 9,024 audit inputs are derived from `SHAKE256(SHA256(netlist_bytes))`, mirroring the Fiat-Shamir structure described in the whitepaper appendix.
4. `pointadd_audit_9024.csv` records every derived case and all cases pass.
5. `toy_curve_exhaustive.json` exhaustively checks the same compiler shape on a tiny `a=0` curve over `p=23` for every enumerated accumulator point, every nonzero base point in the chosen subgroup, and every 4-bit signed window key.
6. `ecdlp_scaffold_exact_sample.json` is the exact 28-call hierarchical Shor scaffold around the audited point-add leaf, using the archived 28-call retained-window scaffold.
