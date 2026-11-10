# trifecta

RFCs, MADRs, design docs and plans as one deterministically validated graph, built on
sphinx-needs, MyST and Vale. `trifecta check` builds the documents, validates the links
between them, and lints their prose; every finding begins with the ID of the requirement
it breaks.

## Run this in your repo

trifecta is one Python package, released as a wheel with a SHA-256 and a build provenance
attestation. A repository that adopts it pins that wheel by URL and hash in its
`requirements.lock`, beside every dependency, each pinned and hashed:

```text
trifecta @ https://github.com/wyattrupp/trifecta/releases/download/v<version>/trifecta-<version>-py3-none-any.whl --hash=sha256:<sha256>
```

### From the template

Create a repository from
[wyattrupp/trifecta-template](https://github.com/wyattrupp/trifecta-template), which holds
the output of `trifecta init` pinned to the latest release, then set it up:

```sh
gh repo create <your-repo> --template wyattrupp/trifecta-template --private --clone
cd <your-repo>
python3 -m venv "$HOME/.venvs/trifecta"
. "$HOME/.venvs/trifecta/bin/activate"
make setup
make check
```

Replace `@wyattrupp` in `.github/CODEOWNERS` with yourself.

### In an existing repository

Run these at the repository's root, after `git init` if it is new. Init refuses to
replace a file that is already there, other than a `CLAUDE.md`, to which it appends its
section, and a `.claude/settings.json`, into which it merges its hook; move any other
clashing file (a `Makefile`, a `.gitignore`, a workflow named `check.yml`) aside first.

<!-- adoption-steps: tests/test_adoption.py runs this block in an empty repository -->
```sh
# The latest release's wheel, and its provenance: built by the release workflow at its tag.
version=$(gh release view --repo wyattrupp/trifecta --json tagName --jq .tagName | cut -c2-)
wheel="trifecta-$version-py3-none-any.whl"
gh release download "v$version" --repo wyattrupp/trifecta --pattern "$wheel"
gh attestation verify "$wheel" --repo wyattrupp/trifecta \
  --cert-identity "https://github.com/wyattrupp/trifecta/.github/workflows/release-build.yml@refs/tags/v$version" \
  --source-ref "refs/tags/v$version" --deny-self-hosted-runners
# A virtual environment outside the repository: the wheel's own hashed dependencies, then the wheel.
python3 -m venv "$HOME/.venvs/trifecta"
. "$HOME/.venvs/trifecta/bin/activate"
unzip -p "$wheel" trifecta/requirements.lock > "$HOME/.venvs/trifecta/requirements.lock"
python -m pip install --require-hashes -r "$HOME/.venvs/trifecta/requirements.lock"
python -m pip install --no-deps "./$wheel"
# The corpus, the lock pinned to this wheel, CI, CODEOWNERS and the planning files.
trifecta init --codeowner @your-github-name \
  --wheel-url "https://github.com/wyattrupp/trifecta/releases/download/v$version/$wheel" \
  --wheel-sha256 "$(sha256sum "$wheel" | cut -d' ' -f1)"
rm "$wheel"
make check
```

Replace `@your-github-name` with yourself, then commit what init wrote. Without a
GitHub `origin` remote and a release install, init needs `--codeowner` and the two
`--wheel-` options, as above; it lists every file it wrote or changed.

### Check and CI

```sh
make check             # build, validate, lint; prints findings and exits 1 if there are any
make check BASE=main   # also hold history to a git ref: accepted decisions do not change
```

`make setup` installs the lock and Vale on a fresh clone. The workflow init writes,
`.github/workflows/check.yml`, runs the same check on every pull request and on every
push to main, with read access only, no stored credentials, and actions pinned by SHA.
`CODEOWNERS` names who reviews changes to the files that steer the check and the session.

To move to a new release, replace the lock's `trifecta @` line with the new release's URL
and its SHA-256, after verifying its attestation as above.

### Planning with Claude Code

Init adds a section to `CLAUDE.md`, a `trifecta-planning` skill and a hook, so a Claude
Code session plans through the corpus by default:

```sh
trifecta new rfc <slug>                          # the problem and its requirements
trifecta new decision <slug>                     # one MADR per choice
trifecta new design <slug>                       # the components that satisfy the requirements
trifecta new plan <slug> --implements DES_NNNN   # tasks in build order, with checkbox steps
trifecta next docs/plans/NNNN-<slug>.md          # the task holding the next open step
trifecta review digest|stamp docs/...            # review a document before it is relied on
```

The hook refuses a write under `docs/superpowers/`, where the superpowers skills would put
specs and plans; the skill and the `CLAUDE.md` section send them to the typed directories
instead. The section also tells the session to treat the text of documents and command
output as data, not instructions.

## Developing trifecta

This repository is its own example: its documentation describes the toolchain, and the
toolchain checks that documentation. The requirements live in the RFCs under
`docs/rfcs/`.

```sh
make setup             # install the hashed lock and this package from src/; fetch Vale for this platform and verify its hash
make check             # build, validate, lint, and run the tests under tests/
make check BASE=main   # also check history against a git ref
make fixtures          # prove the corpus passes and every negative fixture is rejected
```

Without `make`, on Windows or anywhere, the same commands run as `trifecta`:

```sh
PYTHONPATH=src python -m trifecta setup  # make setup; setup installs the trifecta command
trifecta check [--base main]             # make check
trifecta fixtures                        # make fixtures
```

### Where things are

| Path | What it is |
| --- | --- |
| `docs/rfcs/` | RFCs: requirements, terms, questions |
| `docs/decisions/` | MADRs: one decision per file, immutable once accepted |
| `docs/design/` | Design docs: components and interfaces, with `spec` paths into this repo |
| `docs/plans/` | Plans: one design doc built as ordered tasks with checkbox steps, and As built |
| `docs/conf.py` | Loads the package's ontology for this repository's corpus |
| `src/trifecta/` | The package: the `trifecta` command, pipeline, post-build graph checker, Vale rule generator, lifecycle checker, fixture runner, `new`, `next`, `review` and `setup` |
| `src/trifecta/ext/` | Sphinx extension for document-level rules, the ontology and the graph rules sphinx-needs enforces natively, the plan rules, and frontmatter schemas |
| `src/trifecta/styles/Trifecta/`, `src/trifecta/vale/` | Vale rules, each named by its requirement ID, and their two scopes |
| `tests/` | Tests that prove what no corpus mutation can show, each declaring the requirements it proves |
| `tests/fixtures/` | One or more mutations of the real corpus per requirement |

Which component enforces which requirement is recorded in the design docs, and the
reasons are in the MADRs.

### Planning and building

A spec is an RFC (the problem and the requirements), a MADR per choice, and a design doc
(the components); a plan implements one design doc as tasks in build order
(`docs/decisions/0008-a-spec-is-an-rfc-its-madrs-and-a-design.md`). Each starts as a
draft from `trifecta new`, under `docs/rfcs/`, `docs/decisions/`, `docs/design/` or
`docs/plans/`; the superpowers skills' own paths (`docs/superpowers/...`) and templates
do not apply here, and the check rejects a document outside those directories. An
accepted RFC, an approved or implemented design doc, and an active or done plan record at
least one review, as a `review` need in the Review section. A building
session runs `trifecta next`, does the marked step, ticks it, and writes the task's As
built entry when its last step is ticked.

### Writing documents

Start each document from `trifecta new` or an existing one of the same type. Frontmatter carries status and
metadata; the filename carries the number; the H1 carries the title. The document-level
directive (`:::{rfc}`, `:::{decision}`, `:::{design}`, `:::{plan}`) carries only links, and the
extension injects the rest. Use colon fences for every need directive.

A requirement needs a negative fixture in `tests/fixtures/` once a component of an
implemented design doc satisfies it; until then it is planned, not enforced.
