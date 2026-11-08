---
status: accepted
date: 2026-11-07
decision-makers: [wyatt]
---
# Lint rendered HTML with Vale

:::{decision}
:chooses: OPT_0005_HTML
:resolves: Q_PROSE_LINT_TARGET
:driven_by: REQ_NORMATIVE_SCOPE, REQ_NO_DECISION_LANGUAGE
:supersedes: DEC_0004
:::

## Context and Problem Statement

Linting the source cannot express the rule that normative keywords appear only inside
requirement and interface needs, because Vale sees no need boundaries in MyST.

## Decision Drivers

- Rules scoped by need type
- Generated content excluded from prose rules

## Considered Options

:::{opt} Lint the rendered HTML
:id: OPT_0005_HTML
Good, because each need renders with a `needs_type_*` class, so a rule can skip exactly
the needs where it does not apply. Bad, because findings point at rendered pages.
:::

:::{opt} Keep linting the MyST source
:id: OPT_0005_SOURCE
Good, because findings point at source lines. Bad, because the scoping invariant stays
unenforceable.
:::

## Decision Outcome

Chosen option: {need}`OPT_0005_HTML`, because an unenforceable invariant is worse than a
less convenient finding location.

## Consequences

- Good, because scoping works by ignoring classes, one Vale configuration per scope.
- Bad, because a finding names an HTML page, which maps one-to-one to its source file.
- Bad, because sphinx-needs renders need metadata as invalid HTML that breaks Vale's
  class scoping, so Vale reads a lint view with metadata rows removed.
