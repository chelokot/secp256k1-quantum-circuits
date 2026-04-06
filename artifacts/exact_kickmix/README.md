# Archived exact kickmix artifact

This directory preserves an exact kickmix-ISA point-add release that the
repository keeps as a reference artifact.

The verification path here is replay-oriented:

- recompute archived secp256k1 points from archived scalars
- re-execute the exact ISA netlist
- verify scaffold and oracle hash linkage
- verify the archived proof-manifest hashes

Verifier command from the repository root:

```bash
python src/verify_exact_archive.py --repo-root .
```
