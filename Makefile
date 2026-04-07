.PHONY: verify verify-quick verify-optimized refresh test compare-cain

verify:
	python scripts/verify_all.py

verify-quick:
	python scripts/verify_all.py --quick

verify-optimized:
	python src/verifier.py --package-dir artifacts --mode all

refresh:
	python scripts/refresh_repo.py

test:
	python -m unittest discover -s tests -v

compare-cain:
	python scripts/compare_cain_2026.py
