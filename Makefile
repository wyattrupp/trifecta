# Pinned toolchain (REQ_PINNED_TOOLCHAIN, REQ_PLATFORM_TOOLCHAIN): tools/setup.py installs the
# hashed lock and fetches Vale for this platform from its table of release files and hashes.
PY ?= python3

.PHONY: setup vale check fixtures clean

setup:
	$(PY) tools/setup.py

vale:
	$(PY) tools/setup.py --vale-only

## check: run the pipeline. Set BASE=<git ref> to also check MADR immutability.
check: vale
	$(PY) tools/check.py $(if $(BASE),--base $(BASE))

## fixtures: prove the corpus passes and every negative fixture fails as expected.
fixtures: vale
	$(PY) tools/run_fixtures.py

clean:
	rm -rf docs/_build styles/TrifectaGenerated
