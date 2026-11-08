---
status: accepted
date: 2026-11-07
decision-makers: [wyatt]
---
# Split rules between schemas and a checker

:::{decision}
:chooses: OPT_0006_SPLIT
:resolves: Q_RULE_PLACEMENT
:driven_by: REQ_COVERAGE, REQ_SUPERSESSION, REQ_CHOICE_CONSIDERED, REQ_SPEC_RESOLVES
:::

## Context and Problem Statement

sphinx-needs schemas validate need fields and traverse links, and derived fields can join
a child need to its document's status. They cannot compare a value on one need with a
value on another, they cannot require one of two link types (union-derived links are
not validated), and they cannot read the filesystem.

## Decision Drivers

- Each invariant has exactly one enforcing component
- Native checks where possible, so findings appear in the Sphinx build
- No rule is weakened to fit a tool

## Considered Options

:::{opt} Schemas for graph rules, a post-build checker for the rest
:id: OPT_0006_SPLIT
Good, because every rule sphinx-needs can express runs in the build, and the remainder
runs over `needs.json`. Bad, because rules live in two places.
:::

:::{opt} Every rule in sphinx-needs
:id: OPT_0006_ALL_NATIVE
Good, because there is one place. Bad, because value comparison and filesystem checks are
not expressible there.
:::

:::{opt} Every rule in a post-build checker
:id: OPT_0006_ALL_EXTERNAL
Good, because the logic is plain Python. Bad, because it reimplements traversal that
sphinx-needs already does and validates.
:::

## Decision Outcome

Chosen option: {need}`OPT_0006_SPLIT`, because it is the only option that enforces every
invariant without reimplementing the graph engine.

## Consequences

- Good, because schema findings carry the requirement ID as their schema ID.
- Bad, because a reader has to know which of two places owns a rule; the design doc's
  components record it.
