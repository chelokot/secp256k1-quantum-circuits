# Archived exact kickmix artifact

This directory preserves the earlier exact kickmix point-add leaf and 28-call scaffold.

The verification path here is a transcript replay rather than a fresh challenge rebuild:
- the verifier recomputes the archived secp256k1 points from the archived scalars,
- re-executes the exact ISA netlist,
- checks the scaffold/oracle hash linkage,
- checks the archived toy-proof summary,
- checks the archived proof-manifest hashes.

Main verifier command from repository root:

```bash
python src/verify_exact_archive.py --repo-root .
```
