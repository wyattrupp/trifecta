---
status: accepted
date: 2026-11-08
decision-makers: [claude]
informed: [wyatt]
---
# Reviews are needs in the reviewed document

:::{decision}
:chooses: OPT_0010_NEED
:resolves: Q_REVIEW_HOME
:driven_by: REQ_REVIEWED
:::

## Context and Problem Statement

An RFC, a design doc or a plan is relied on once it is accepted, approved or active, and
the working rule is that it is reviewed first, with k distinct-lens passes. The record of
that review has to be somewhere a check can see, and it has to stay with the document it
reviewed.

## Decision Drivers

- A check can tell whether a relied-on document was reviewed
- The record states k and the date in a form the check validates
- No new place to look: the record travels with the document

## Considered Options

:::{opt} A review need in the document's Review section
:id: OPT_0010_NEED
Good, because each review is a need with validated fields, the document links to it
through a derived link, and reviews are queryable like any other need. Bad, because a
review adds a directive where a heading would do.
:::

:::{opt} A reviews list in the frontmatter
:id: OPT_0010_FRONTMATTER
Good, because the schema validates it with the rest of the metadata. Bad, because what a
review found and what changed is prose, which frontmatter is not for.
:::

:::{opt} A heading convention checked by the extension
:id: OPT_0010_HEADING
Good, because it reads naturally. Bad, because the record is not in the graph, so nothing
else can query or link to it.
:::

## Decision Outcome

Chosen option: {need}`OPT_0010_NEED`, because it puts the review in the graph with fields
the check validates, next to the prose that says what it found.

## Consequences

- Good, because the derived `reviewed_by` link is computed, never written.
- Bad, because MADRs keep the standard MADR sections and carry no Review section; by
  convention, the review of the RFC whose questions they resolve covers them, and no
  check links the two.
