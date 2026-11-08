# trifecta

RFCs, MADRs and design docs as one deterministically validated graph, built on
sphinx-needs, MyST and Vale. The repository is its own example: its documentation
describes this validation system, and this validation system checks that documentation.

The requirements live in `docs/rfcs/0001-documentation-as-a-validated-graph.md`. This
README does not restate them; every finding the check prints begins with the ID of the
requirement it violates.

## Run it

```sh
make setup             # pip install -r requirements.lock; fetch Vale (Linux x86_64) and verify its checksum
make check             # build, validate, lint; prints findings and exits 1 if there are any
make check BASE=main   # also check MADR immutability against a git ref
make fixtures          # prove the corpus passes and every negative fixture is rejected
```

## Where things are

| Path | What it is |
| --- | --- |
| `docs/rfcs/` | RFCs: requirements, terms, questions |
| `docs/decisions/` | MADRs: one decision per file, immutable once accepted |
| `docs/design/` | Design docs: components and interfaces, with `spec` paths into this repo |
| `docs/conf.py` | The ontology and the graph rules sphinx-needs enforces natively |
| `ext/` | Sphinx extension for document-level rules, and frontmatter schemas |
| `tools/` | Pipeline, post-build graph checker, Vale rule generator, lifecycle checker, fixture runner |
| `styles/Trifecta/`, `vale/` | Vale rules, each named by its requirement ID, and their two scopes |
| `tests/fixtures/` | One or more mutations of the real corpus per requirement |

Which component enforces which requirement is recorded in
`docs/design/0001-validation-pipeline.md`, and the reasons for the split are in the MADRs.

## Writing documents

Start each document from an existing one of the same type. Frontmatter carries status and
metadata; the filename carries the number; the H1 carries the title. The document-level
directive (`:::{rfc}`, `:::{decision}`, `:::{design}`) carries only links, and the
extension injects the rest. Use colon fences for every need directive.

A new requirement needs a negative fixture in `tests/fixtures/` before the check passes.
