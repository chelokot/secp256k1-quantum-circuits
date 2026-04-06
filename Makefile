.PHONY: verify verify-optimized verify-strict research test hashes compare compare-cain compare-literature compare-lookup figures release-check

verify:
	python scripts/verify_all.py

verify-optimized:
	python src/verifier.py --package-dir artifacts --mode all

verify-strict:
	python scripts/verify_strict.py --mode all

research:
	python scripts/run_research_pass.py

test:
	python -m unittest discover -s tests -v

hashes:
	python scripts/hash_repo.py

compare:
	python scripts/compare_google_baseline.py

figures:
	python scripts/generate_figures.py

release-check:
	python scripts/release_check.py

compare-cain:
	python scripts/compare_cain_2026.py

compare-literature:
	python scripts/compare_literature.py

compare-lookup:
	python scripts/compare_lookup_research.py
