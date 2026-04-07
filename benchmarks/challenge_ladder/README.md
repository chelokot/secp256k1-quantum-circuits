# Challenge ladder

This directory stores the benchmark-ladder replay suite for small deterministic
curves in the `y^2 = x^3 + 7` family.

Contents:

- `challenge_ladder.json` — benchmark-curve definitions and challenge points
- `challenge_ladder_audit.csv` — replay transcript
- `challenge_ladder_summary.json` — summary and hashes

Regenerate with:

```bash
python scripts/release_check.py
```

For interpretation and scope, read `docs/CHALLENGE_LADDER.md`.
