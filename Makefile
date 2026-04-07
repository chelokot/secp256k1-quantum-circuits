.PHONY: verify verify-quick verify-optimized projection test hashes figures compare-cain

verify:
	python scripts/verify_all.py

verify-quick:
	python scripts/verify_all.py --quick

verify-optimized:
	python src/verifier.py --package-dir artifacts --mode all

projection:
	python scripts/rebuild_resource_projection.py

test:
	python -m unittest discover -s tests -v

hashes:
	python scripts/hash_repo.py

figures:
	python scripts/generate_figures.py

compare-cain:
	python scripts/compare_cain_2026.py
