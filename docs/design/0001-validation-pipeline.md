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
guards MADR history; and the fixture audit confirms every invariant has a negative
fixture. Each stage reports findings in one format, and the pipeline fails on any
finding.

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
:spec: docs/conf.py#needs_schema_definitions
:satisfies: REQ_UNIQUE_IDS, REQ_LINK_TARGETS, REQ_DECISION_OPTIONS, REQ_RFC_ACCEPTANCE, REQ_COVERAGE, REQ_SUPERSESSION
:constrained_by: DEC_0001, DEC_0006
:provides: IF_NEEDS_JSON
The ontology: need types, link types with their target types, a derived `considers` link
per decision, a derived `doc_status` field per child need, and the schemas whose IDs are
the requirements they enforce.
:::

:::{component} Document extension
:id: COMP_DOC_EXTENSION
:spec: ext/trifecta.py#DOC_TYPES
:satisfies: REQ_DOC_IDENTITY, REQ_FRONTMATTER_SCHEMA, REQ_SECTION_SKELETON, REQ_GENERATED_VIEWS, REQ_STATUS_SINGLE_SOURCE, REQ_CHOSEN_SENTENCE
:constrained_by: DEC_0002, DEC_0003
A Sphinx extension that validates frontmatter, injects each document's title, ID, status
and metadata into its document-level need, and checks the section skeleton while the
document is read. Injection preserves source line numbers.
:::

:::{component} Graph checker
:id: COMP_GRAPH_CHECKER
:spec: tools/check_graph.py#def check
:satisfies: REQ_CHOICE_CONSIDERED, REQ_NO_ORPHANS, REQ_SPEC_RESOLVES
:constrained_by: DEC_0006
:consumes: IF_NEEDS_JSON
Reads `needs.json` after the build and checks the rules that schemas cannot express:
value comparisons across needs, disjunctions across link types, and filesystem paths.
:::

:::{component} Prose styles
:id: COMP_VALE_STYLES
:spec: styles/Trifecta/REQ_NORMATIVE_SCOPE.yml
:satisfies: REQ_NORMATIVE_SCOPE, REQ_NO_DECISION_LANGUAGE
:constrained_by: DEC_0005
Vale rules named by the requirement they enforce, applied to the rendered HTML through
two configurations: one ignoring requirement and interface needs, one ignoring nothing
but page chrome and generated tables.
:::

:::{component} Term rule generator
:id: COMP_VALE_GENERATOR
:spec: tools/gen_vale.py#def generate
:satisfies: REQ_CANONICAL_TERMS
:constrained_by: DEC_0005
:consumes: IF_NEEDS_JSON
Writes a Vale substitution rule from the `synonyms` of every term need, so the glossary
is the only list of terms.
:::

:::{component} Lifecycle checker
:id: COMP_LIFECYCLE
:spec: tools/check_lifecycle.py#def check
:satisfies: REQ_IMMUTABLE_DECISIONS
:constrained_by: DEC_0002
Compares each MADR with its version at a base git ref and reports any change other than
an allowed status transition.
:::

:::{component} Pipeline
:id: COMP_PIPELINE
:spec: tools/check.py#def main
:satisfies: REQ_WARNINGS_FATAL, REQ_PINNED_TOOLCHAIN
:constrained_by: DEC_0006
:provides: IF_FINDING
Runs every stage in a fixed order, maps each Sphinx warning to the requirement it
violates, verifies the pinned toolchain, and prints sorted findings.
:::

:::{component} Fixture runner
:id: COMP_FIXTURE_RUNNER
:spec: tools/run_fixtures.py#def main
:satisfies: REQ_FIXTURE_PER_INVARIANT
:constrained_by: DEC_0007
:consumes: IF_NEEDS_JSON, IF_FINDING
Copies the repository, proves the unmutated copy passes, then applies each fixture's
mutations to a fresh copy and asserts the expected finding appears.
:::

## Interfaces

:::{interface} needs.json
:id: IF_NEEDS_JSON
:spec: docs/conf.py#needs_build_json
:constrained_by: DEC_0001
The sphinx-needs export of every need and its resolved links. Consumers MUST read only
the current version's `needs` table and MUST NOT depend on field order.
:::

:::{interface} Finding
:id: IF_FINDING
:spec: tools/findings.py#class Finding
:constrained_by: DEC_0006
One violation per line: `REQ_ID`, a tab, a location, a tab, a message. Every finding
MUST begin with the ID of the requirement it violates, and output MUST be sorted so two
runs over the same input are byte-identical.
:::
