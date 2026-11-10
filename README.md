# trifecta

RFCs, MADRs, design docs and plans as one deterministically validated graph, built on
sphinx-needs, MyST and Vale. The repository is its own example: its documentation
describes this validation system, and this validation system checks that documentation.

The requirements live in the RFCs under `docs/rfcs/`. This README does not restate them; every finding the check prints begins with the ID of the
requirement it violates.

## Run it

```sh
make setup             # install the hashed lock and this package from src/; fetch Vale for this platform and verify its hash
make check             # build, validate, lint; prints findings and exits 1 if there are any
make check BASE=main   # also check MADR immutability against a git ref
make fixtures          # prove the corpus passes and every negative fixture is rejected
```

Without `make`, on Windows or anywhere, the same commands run as `trifecta`:

```sh
PYTHONPATH=src python -m trifecta setup  # make setup; setup installs the trifecta command
trifecta check [--base main]             # make check
trifecta fixtures                        # make fixtures
```

```sh
trifecta new rfc <slug>                          # a draft of a type: rfc, decision, design
trifecta new plan <slug> --implements DES_NNNN   # a draft plan, its first task building the whole design
trifecta next docs/plans/NNNN-slug.md            # the task holding an active plan's next open step
trifecta review digest|stamp docs/...            # take a document's digest; stamp its review
```

## Where things are

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
| `tests/fixtures/` | One or more mutations of the real corpus per requirement |

Which component enforces which requirement is recorded in the design docs, and the
reasons are in the MADRs.

## Planning and building

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

## Writing documents

Start each document from `trifecta new` or an existing one of the same type. Frontmatter carries status and
metadata; the filename carries the number; the H1 carries the title. The document-level
directive (`:::{rfc}`, `:::{decision}`, `:::{design}`, `:::{plan}`) carries only links, and the
extension injects the rest. Use colon fences for every need directive.

A requirement needs a negative fixture in `tests/fixtures/` once a component of an
implemented design doc satisfies it; until then it is planned, not enforced.
