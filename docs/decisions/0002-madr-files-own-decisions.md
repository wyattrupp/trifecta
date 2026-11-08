---
status: accepted
date: 2026-11-07
decision-makers: [wyatt]
---
# MADR files own decisions

:::{decision}
:chooses: OPT_0002_MADR_FILES
:resolves: Q_DECISION_OWNER
:driven_by: REQ_IMMUTABLE_DECISIONS, REQ_SUPERSESSION
:::

## Context and Problem Statement

A decision can be written inside the RFC that raised it or in a file of its own. The
location determines its lifecycle: whether it can be superseded without editing the RFC,
and whether its history survives revision.

## Decision Drivers

- A decision outlives the RFC that raised it
- Revisions must not erase history
- Existing MADR tooling reads one file per decision

## Considered Options

:::{opt} One MADR file per decision
:id: OPT_0002_MADR_FILES
Good, because each decision gets an independent, immutable lifecycle with explicit
supersession. Bad, because readers follow links between files.
:::

:::{opt} Decisions inline in the RFC
:id: OPT_0002_INLINE
Good, because the reasoning sits next to the requirements. Bad, because a revised
decision forces an edit to an accepted RFC and loses the original reasoning.
:::

## Decision Outcome

Chosen option: {need}`OPT_0002_MADR_FILES`, because immutability and supersession need a
unit smaller than an RFC.

## Consequences

- Good, because supersession is a graph edge that tooling can follow.
- Bad, because a MADR's frontmatter and its need data have to be reconciled, which the
  extension does by injecting one from the other.
