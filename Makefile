.PHONY: verify verify-quick verify-optimized refresh test test-sequential compare-cain materialize-exact-circuits materialize-all-exact-circuits

verify:
	python scripts/verify_all.py

verify-quick:
	python scripts/verify_all.py --quick

verify-optimized:
	python src/verifier.py --package-dir artifacts --mode all

refresh:
	python scripts/refresh_repo.py

test:
	python scripts/run_tests.py --jobs auto

test-sequential:
	python -m pytest -q

compare-cain:
	python scripts/compare_cain_2026.py

materialize-exact-circuits:
	python compiler_verification_project/scripts/materialize_exact_circuits.py

materialize-all-exact-circuits:
	python compiler_verification_project/scripts/materialize_exact_circuits.py --all-families
