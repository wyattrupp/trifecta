---
status: accepted
date: 2026-11-08
decision-makers: [claude]
informed: [wyatt]
---
# Diagrams live on the index

:::{decision}
:chooses: OPT_0027_INDEX
:resolves: Q_DIAGRAM_PLACE
:driven_by: REQ_DIAGRAMS_DERIVED
:::

## Context and Problem Statement

wyatt, 2026-11-08, chose Graphviz over the design shown that day and left the rest of it
standing. That design put the meta-model on the index and the traces on one new page.
REQ_DOC_IDENTITY allows no document outside the typed directories but the index, so a
new page would need that rule changed.

## Decision Drivers

- No accepted requirement changes
- A reader finds the diagrams from the first page
- An adopting repository gets the diagrams from init with nothing to keep up

## Considered Options

:::{opt} Both diagrams on the index
:id: OPT_0027_INDEX
Good, because the index is the one document outside the typed directories, has no
section skeleton, and is the page every reader opens. Bad, because the index grows by
one trace per RFC, and an adopting repository on an earlier release has to add the two
directives to its index when it upgrades.
:::

:::{opt} A trace page beside the index
:id: OPT_0027_TRACE_PAGE
Good, because the index stays short. Bad, because REQ_DOC_IDENTITY would need an
exception for it.
:::

:::{opt} A trace section in each RFC
:id: OPT_0027_RFC_SECTION
Good, because each trace sits with its RFC. Bad, because every RFC and the skeleton that
REQ_SECTION_SKELETON holds them to would change.
:::

## Decision Outcome

Chosen option: {need}`OPT_0027_INDEX`, because it keeps the design wyatt let stand, with
the traces moved from a new page to the index so that no accepted requirement changes;
wyatt can overrule this record with a superseding one.

## Consequences

- Good, because plan 0003's init already writes the index, so an adopting repository gets
  the two directives there.
- Bad, because a corpus with many RFCs has a long index; a later decision can move the
  traces if that becomes a problem.
