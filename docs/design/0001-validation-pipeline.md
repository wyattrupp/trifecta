---
status: implemented
authors: [wyatt]
---
# Validation pipeline

:::{design}
:::

## Overview

`tools/check.py` runs one deterministic pipeline over the corpus. Sphinx builds the HTML
with warnings as errors; the trifecta extension checks each document's shape while it is
read; sphinx-needs schemas check the graph; a post-build checker reads `needs.json` for
the rules schemas cannot express; Vale lints the rendered prose; a git-aware checker
guards MADR history when the check is given a base ref with `--base`; and the fixture
audit confirms every invariant has a negative fixture. Each stage reports findings in one
format, and the pipeline fails on any finding. The toolchain-table, line-ending and
location stages are described in {need}`DES_0006`.

## Requirements

:::{needtable}
:filter: type == 'req' and len(satisfies_back) > 0
:columns: id, title, satisfies_back as "Satisfied by"
:style: table
:::

## Constraints

:::{needtable}
:filter: type == 'decision' and len(constrained_by_back) > 0
:columns: id, title, status
:style: table
:::

## Components

:::{component} Native graph schemas
:id: COMP_NEEDS_SCHEMA
:spec: src/trifecta/ext/ontology.py#needs_schema_definitions
:satisfies: REQ_UNIQUE_IDS, REQ_LINK_TARGETS, REQ_DECISION_OPTIONS, REQ_RFC_ACCEPTANCE, REQ_COVERAGE, REQ_SUPERSESSION
:constrained_by: DEC_0001, DEC_0006
:provides: IF_NEEDS_JSON
The ontology: need types, link types with their target types, a derived `considers` link
per decision, a derived `doc_status` field per child need, and the schemas whose IDs are
the requirements they enforce.
:::

:::{component} Document extension
:id: COMP_DOC_EXTENSION
:spec: src/trifecta/ext/__init__.py#DOC_TYPES
:satisfies: REQ_DOC_IDENTITY, REQ_FRONTMATTER_SCHEMA, REQ_SECTION_SKELETON, REQ_GENERATED_VIEWS, REQ_STATUS_SINGLE_SOURCE, REQ_CHOSEN_SENTENCE
:constrained_by: DEC_0002, DEC_0003
A Sphinx extension that validates frontmatter, injects each document's title, ID, status
and metadata into its document-level need, and checks the section skeleton while the
document is read. Injection keeps the line number of every line after the directive.
:::

:::{component} Graph checker
:id: COMP_GRAPH_CHECKER
:spec: src/trifecta/check_graph.py#def check
:satisfies: REQ_CHOICE_CONSIDERED, REQ_NO_ORPHANS, REQ_SPEC_RESOLVES
:constrained_by: DEC_0006
:consumes: IF_NEEDS_JSON
Reads `needs.json` after the build and checks the rules that schemas cannot express:
value comparisons across needs, disjunctions across link types, and filesystem paths.
:::

:::{component} Prose styles
:id: COMP_VALE_STYLES
:spec: src/trifecta/styles/Trifecta/REQ_NORMATIVE_SCOPE.yml
:satisfies: REQ_NORMATIVE_SCOPE, REQ_NO_DECISION_LANGUAGE
:constrained_by: DEC_0005
Vale rules named by the requirement they enforce, applied to the rendered HTML through
two configurations: one ignoring requirement and interface needs, one ignoring nothing
but page chrome and generated tables. Before both runs, the pipeline removes the need
metadata rows from a copy of the built pages, so option text such as a task's gate is
not linted.
:::

:::{component} Term rule generator
:id: COMP_VALE_GENERATOR
:spec: src/trifecta/gen_vale.py#def generate
:satisfies: REQ_CANONICAL_TERMS
:constrained_by: DEC_0005
:consumes: IF_NEEDS_JSON
Writes a Vale substitution rule from the `synonyms` of every term need, so the glossary
is the only list of terms.
:::

:::{component} Lifecycle checker
:id: COMP_LIFECYCLE
:spec: src/trifecta/check_lifecycle.py#def check
:satisfies: REQ_IMMUTABLE_DECISIONS
:constrained_by: DEC_0002
Compares each MADR with its version at a base git ref and reports any change other than
an allowed status transition.
:::

:::{component} Pipeline
:id: COMP_PIPELINE
:spec: src/trifecta/check.py#def main
:satisfies: REQ_WARNINGS_FATAL, REQ_PINNED_TOOLCHAIN
:constrained_by: DEC_0006
:provides: IF_FINDING
Runs every stage in a fixed order, maps each Sphinx warning to the requirement it
violates, verifies the pinned toolchain, and prints sorted findings.
:::

:::{component} Fixture runner
:id: COMP_FIXTURE_RUNNER
:spec: src/trifecta/run_fixtures.py#def main
:satisfies: REQ_FIXTURE_PER_INVARIANT
:constrained_by: DEC_0007
:consumes: IF_NEEDS_JSON, IF_FINDING
Copies the repository, proves the unmutated copy passes, then applies each fixture's
mutations to a fresh copy and asserts the expected finding appears. The control keeps
what its test modules reported; a copy runs its test modules only when its fixture
expects `REQ_PROVEN_BY_TEST` or a mutation touches `tests/` or `src/`, and otherwise its
check judges the control's reports, taken only for the same modules and the same tests
left out (wyatt, 2026-11-11: "Yes, do those first").
:::

## Interfaces

:::{interface} needs.json
:id: IF_NEEDS_JSON
:spec: src/trifecta/ext/ontology.py#needs_build_json
:constrained_by: DEC_0001
The sphinx-needs export of every need and its resolved links. Consumers MUST read only
the current version's `needs` table and MUST NOT depend on field order.
:::

:::{interface} Finding
:id: IF_FINDING
:spec: src/trifecta/findings.py#class Finding
:constrained_by: DEC_0006
One violation per line: `REQ_ID`, a tab, a location, a tab, a message. Every finding
MUST begin with the ID of the requirement it violates, and output MUST be sorted so two
runs over the same input are byte-identical.
:::

## Risks

A sphinx-needs upgrade can change warning codes or schema output; the fixture runner
catches it, because each fixture names the finding it expects. Vale runs on Windows as
`bin/vale.exe`, and the `check-windows` job runs every stage ({need}`DES_0006`).

CI runs the pull request's own checker, extension, `docs/conf.py`, fixtures and
workflow, so a pull request can change what checks it; the maintainer's review of the
pull request is the safeguard, and no ruleset requires an approval. Vale skips content by class name, so raw HTML that carries an ignored class
escapes the lint. The Vale table in `tools/setup.py` is checked for form, not against
Vale's published checksums. A `spec` fragment is matched as text in the file. A fixture
passes on any finding of its requirement, unless it sets `only`.

## Review

:::{review} Correctness; security
:id: REV_DES_0001_1
:k: 2
:date: 2026-11-08
The review recorded as {need}`REV_RFC_0001_1` covered this design doc and the code it
describes.
:::

:::{review} Correctness; security
:id: REV_DES_0001_2
:k: 2
:date: 2026-11-09
:digest: 54531476db4f20338fd29c9b05a4b368202d62d5bbe0d7a16f868d95f4506826
:::
