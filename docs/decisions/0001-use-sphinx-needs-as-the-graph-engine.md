---
status: accepted
date: 2026-11-07
decision-makers: [wyatt]
---
# Use sphinx-needs as the graph engine

:::{decision}
:chooses: OPT_0001_SPHINX_NEEDS
:resolves: Q_GRAPH_ENGINE
:driven_by: REQ_UNIQUE_IDS, REQ_LINK_TARGETS, REQ_COVERAGE
:::

## Context and Problem Statement

The corpus is a typed graph of requirements, decisions, options and design elements.
Something has to parse the needs out of MyST, resolve their links, and expose the result
for validation and for derived views.

## Decision Drivers

- Typed needs with per-type link targets, checked at build time
- Derived views generated from the same graph the checks read
- A machine-readable export that downstream tools consume

## Considered Options

:::{opt} sphinx-needs
:id: OPT_0001_SPHINX_NEEDS
Good, because it types needs, resolves links, exports `needs.json`, and validates the
graph with schemas. Bad, because its configuration surface is large and changes between
major versions.
:::

:::{opt} Bespoke YAML records validated with JSON Schema
:id: OPT_0001_BESPOKE
Good, because the format is minimal and fully controlled. Bad, because link resolution,
rendering and derived views would all be rebuilt from scratch.
:::

## Decision Outcome

Chosen option: {need}`OPT_0001_SPHINX_NEEDS`, because it already provides the graph,
the export and the views, and its schemas cover most graph invariants natively.

## Consequences

- Good, because derived views and checks read one graph.
- Bad, because the pinned sphinx-needs version is a real dependency to upgrade carefully.
