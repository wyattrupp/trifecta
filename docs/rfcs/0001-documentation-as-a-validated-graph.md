---
status: accepted
authors: [wyatt]
created: 2026-11-07
---
# Documentation as a validated graph

:::{rfc}
:::

## Summary

RFCs, MADRs, design docs and plans form one {need}`corpus <TERM_CORPUS>` whose structure,
graph and prose are checked deterministically on every change. Each fact is defined
once, as a {need}`need <TERM_NEED>` with an ID, and every other mention references it.
This repository is the reference implementation and is checked by its own rules.

## Motivation

Documentation drifts because nothing fails when it does. A requirement gets restated
in a design doc and the copies diverge; a decision is revised in place and the history
disappears; a component is renamed and the prose still describes the old one.

Treating the corpus as a typed graph turns each kind of drift into a build failure with
a precise cause. Every rule below is an {need}`invariant <TERM_INVARIANT>` with exactly
one enforcing component, and every invariant is proven by at least one
{need}`negative fixture <TERM_FIXTURE>`.

## Terms

:::{term} Need
:id: TERM_NEED
:synonyms: trace item
A typed, identified node in the documentation graph, defined by a sphinx-needs directive.
:::

:::{term} Corpus
:id: TERM_CORPUS
:synonyms: doc set, documentation set
Every RFC, MADR, design doc and plan under `docs/`.
:::

:::{term} Decision record
:id: TERM_DECISION_RECORD
:synonyms: ADR, architecture decision record
A MADR file under `docs/decisions/`; the only place a decision is defined.
:::

:::{term} Invariant
:id: TERM_INVARIANT
A falsifiable statement about the corpus, stated here as a requirement.
:::

:::{term} Finding
:id: TERM_FINDING
:synonyms: lint error
One reported violation of one invariant.
:::

:::{term} Negative fixture
:id: TERM_FIXTURE
:synonyms: failing example, bad example
A mutation of the real corpus that the check is required to reject with a named finding.
:::

:::{term} Derived view
:id: TERM_DERIVED_VIEW
:synonyms: summary table
Content generated from the graph, such as a needtable, which no author writes by hand.
:::

## Requirements

:::{req} Need IDs are unique and well-formed
:id: REQ_UNIQUE_IDS
Every need ID MUST be unique across the corpus and MUST match its type's ID pattern.
:::

:::{req} Document identity comes from the filename
:id: REQ_DOC_IDENTITY
Every document other than the index MUST live in a typed directory and MUST be named
`NNNN-kebab-slug.md`. Its document-level need ID MUST be derived from that number. Within each document type, numbers MUST run from 0001 without
gaps.
:::

:::{req} Frontmatter matches its schema
:id: REQ_FRONTMATTER_SCHEMA
Every typed document MUST have YAML frontmatter that validates against the JSON Schema
for its type, with no unknown keys.
:::

:::{req} Sections follow the skeleton
:id: REQ_SECTION_SKELETON
The H2 sections of a typed document MUST be exactly those declared for its type, in the
declared order.
:::

:::{req} Derived views are generated
:id: REQ_GENERATED_VIEWS
A section declared as a derived view MUST contain exactly one needtable and nothing else.
:::

:::{req} Identity and status have one home
:id: REQ_STATUS_SINGLE_SOURCE
A document's title MUST come from its H1, its ID from its filename, and its status and
metadata from its frontmatter. These MUST NOT be written in the document-level
directive, and child needs MUST NOT carry a status.
:::

:::{req} Links resolve to declared types
:id: REQ_LINK_TARGETS
Every link MUST resolve to an existing need of a type the link type declares as a target.
:::

:::{req} Decisions weigh options
:id: REQ_DECISION_OPTIONS
A decision MUST consider at least two options and MUST choose exactly one.
:::

:::{req} The chosen option was considered
:id: REQ_CHOICE_CONSIDERED
The option a decision chooses MUST be one of the options that decision considers.
:::

:::{req} The chosen-option sentence agrees with the graph
:id: REQ_CHOSEN_SENTENCE
A MADR's Decision Outcome MUST contain exactly one chosen-option sentence, and it MUST
cite the option the decision chooses.
:::

:::{req} Accepted RFCs have no open questions
:id: REQ_RFC_ACCEPTANCE
Every question in an accepted RFC MUST be resolved by an accepted decision.
:::

:::{req} Requirements are covered by design
:id: REQ_COVERAGE
Every requirement in an accepted RFC MUST be satisfied by a component of an approved or
implemented design doc.
:::

:::{req} Design elements trace to their reasons
:id: REQ_NO_ORPHANS
Every component MUST satisfy a requirement or be constrained by a decision. Every
interface MUST be provided by exactly one component.
:::

:::{req} Supersession is explicit and propagates
:id: REQ_SUPERSESSION
A superseded decision MUST be superseded by exactly one accepted decision. A decision
MUST supersede only decisions marked superseded. Design elements MUST be constrained only
by accepted decisions.
:::

:::{req} Specs resolve in the repository
:id: REQ_SPEC_RESOLVES
Every `spec` path on a component or interface MUST exist in the repository, and its
fragment, if given, MUST occur in that file.
:::

:::{req} Normative keywords stay in scope
:id: REQ_NORMATIVE_SCOPE
Uppercase BCP 14 keywords MUST appear only inside requirement and interface needs.
:::

:::{req} Design docs record no decisions
:id: REQ_NO_DECISION_LANGUAGE
Design docs MUST NOT contain the language of choosing; each choice MUST be a MADR.
:::

:::{req} Terms are used canonically
:id: REQ_CANONICAL_TERMS
A declared synonym of a defined term MUST NOT appear in prose in place of the term.
:::

:::{req} Decision records are immutable
:id: REQ_IMMUTABLE_DECISIONS
Once a MADR is accepted, a change MUST only move its status to deprecated or superseded.
A MADR in a terminal status MUST NOT change, and an accepted MADR or a MADR in a terminal
status MUST NOT be deleted or renamed.
:::

:::{req} Warnings are fatal
:id: REQ_WARNINGS_FATAL
Any Sphinx warning MUST fail the check, including those no other requirement names.
:::

:::{req} The toolchain is pinned
:id: REQ_PINNED_TOOLCHAIN
Every Python dependency MUST be pinned to an exact version, and the Vale binary MUST be
pinned by version and checksum.
:::

:::{req} Every invariant has a negative fixture
:id: REQ_FIXTURE_PER_INVARIANT
Every requirement satisfied by a component of an implemented design doc MUST be the
expected finding of at least one negative fixture, or be named by a test whose declaration
counts as its proof under REQ_PROVEN_BY_TEST, and the unmutated corpus MUST pass.
:::

## Questions

:::{question} Which tool holds the need graph?
:id: Q_GRAPH_ENGINE
:::

:::{question} Where is a decision defined?
:id: Q_DECISION_OWNER
:::

:::{question} Is the chosen-option sentence generated or validated?
:id: Q_CHOSEN_SENTENCE
:::

:::{question} What does Vale lint, the source or the rendered output?
:id: Q_PROSE_LINT_TARGET
:::

:::{question} Where does each graph rule run?
:id: Q_RULE_PLACEMENT
:::

:::{question} What is a negative fixture made of?
:id: Q_FIXTURE_FORM
:::

## Out of scope

Publishing or hosting the rendered HTML; documents outside `docs/`; the content of a
requirement, which review judges and no check can.

## Review

:::{review} Correctness; security
:id: REV_RFC_0001_1
:k: 2
:date: 2026-11-08
Whole repository at commit 75a489c, lenses as titled; the local cross-check model was
unreachable, so no pass came from another model lineage. Every finding was verified
against the code. Three were rated high: Sphinx colour codes broke finding mapping in
CI, the push check compared only the last commit, and a trailing space skipped the
chosen-option sentence check. The trailing-space fix has a fixture; the colour fix is
proven by CI itself and the push base by the workflow's own run. The medium and low
findings that held up were fixed in the pull requests that followed, with fixtures where
a corpus mutation can show them.
:::

:::{review} Correctness; security
:id: REV_RFC_0001_2
:k: 2
:date: 2026-11-08
The new text of REQ_FIXTURE_PER_INVARIANT, in the review recorded as {need}`REV_RFC_0003_1`.
:::

:::{review} Correctness; security
:id: REV_RFC_0001_3
:k: 2
:date: 2026-11-09
:digest: 28080b0ffc763891dcfa0453c75220a9a086ba9fd5863b2d9e44068bfeab6caf
:::
