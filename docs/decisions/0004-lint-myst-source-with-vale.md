---
status: superseded
date: 2026-11-07
decision-makers: [wyatt]
---
# Lint MyST source with Vale

:::{decision}
:chooses: OPT_0004_SOURCE
:resolves: Q_PROSE_LINT_TARGET
:driven_by: REQ_NORMATIVE_SCOPE
:::

## Context and Problem Statement

Vale has to read the prose of every need. MyST directives in backtick fences look like
code blocks to Vale, which skips them.

## Decision Drivers

- Need content has to be linted, not skipped
- Findings point at source lines

## Considered Options

:::{opt} Lint the MyST source, written with colon fences
:id: OPT_0004_SOURCE
Good, because findings point at source lines. Bad, because Vale cannot tell which need a
paragraph belongs to.
:::

:::{opt} Lint the rendered HTML
:id: OPT_0004_HTML
Good, because need types render as CSS classes Vale can scope by. Bad, because findings
point at rendered pages.
:::

## Decision Outcome

Chosen option: {need}`OPT_0004_SOURCE`, because colon fences keep need content visible to
Vale and findings land on source lines.

## Consequences

- Good, because authors see findings in the file they edit.
- Bad, because rules cannot be scoped to a need type.
