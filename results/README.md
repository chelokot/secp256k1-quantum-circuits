# Generated results

These JSON files summarize verification and research outputs generated from the
checked-in repository layers.

## Quick verification summaries

- `repo_verification_summary.json`

Regenerate with:

```bash
python scripts/verify_all.py
```

## Strict verification summary

- `strict_verification_summary.json`

Regenerate with:

```bash
python scripts/verify_strict.py --mode all
```

## Research summary files

- `research_pass_summary.json`
- `literature_matrix.json`
- `physical_stack_reference_points.json`

Regenerate with:

```bash
python scripts/run_research_pass.py
```

## Physical transfer summary

- `cain_2026_integration_summary.json`

Inspect or regenerate with:

```bash
python scripts/compare_cain_2026.py
```
