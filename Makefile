# Pinned toolchain (REQ_PINNED_TOOLCHAIN). Vale is fetched by version and verified by checksum.
VALE_VERSION := 3.13.0
VALE_SHA256 := 4378ee4bc7c2493760826270e55d5569cda35d7c89582e9fdc3070e2a1089193
PY ?= python3

.PHONY: setup check fixtures clean

bin/vale:
	mkdir -p bin
	curl -fsSL -o bin/vale.tgz https://github.com/errata-ai/vale/releases/download/v$(VALE_VERSION)/vale_$(VALE_VERSION)_Linux_64-bit.tar.gz
	echo "$(VALE_SHA256)  bin/vale.tgz" | sha256sum -c -
	tar -xzf bin/vale.tgz -C bin vale && rm bin/vale.tgz

setup: bin/vale
	$(PY) -m pip install -r requirements.lock

## check: run the pipeline. Set BASE=<git ref> to also check MADR immutability.
check: bin/vale
	$(PY) tools/check.py $(if $(BASE),--base $(BASE))

## fixtures: prove the corpus passes and every negative fixture fails as expected.
fixtures: bin/vale
	$(PY) tools/run_fixtures.py

clean:
	rm -rf docs/_build styles/TrifectaGenerated
