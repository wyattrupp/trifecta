# Pinned toolchain (REQ_PINNED_TOOLCHAIN, REQ_PLATFORM_TOOLCHAIN): `trifecta setup` installs the
# hashed lock, this repository's package from source, and Vale for this platform from its table
# of release files and hashes. Setup runs the package from src/, since it is what installs it.
PY ?= python3

.PHONY: setup vale check fixtures clean

setup:
	PYTHONPATH=src $(PY) -m trifecta setup

vale:
	$(PY) -m trifecta setup --vale-only

## check: run the pipeline. Set BASE=<git ref> to also check MADR immutability.
check: vale
	$(PY) -m trifecta check $(if $(BASE),--base $(BASE))

## fixtures: prove the corpus passes and every negative fixture fails as expected.
fixtures: vale
	$(PY) -m trifecta fixtures

clean:
	rm -rf docs/_build
