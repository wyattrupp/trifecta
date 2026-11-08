---
status: accepted
date: 2026-11-08
decision-makers: [claude]
informed: [wyatt]
---
# A spec is an RFC, its MADRs and a design doc

:::{decision}
:chooses: OPT_0008_COMPOSE
:resolves: Q_SPEC_HOME
:driven_by: REQ_STATUS_SINGLE_SOURCE, REQ_PLAN_IMPLEMENTS, REQ_DESIGN_BUILT
:::

## Context and Problem Statement

wyatt, 2026-11-08: "make it work with the same validation and single source of truth
discipline that we've established here", for the superpowers spec and plan shapes of
gfl2_pmxview. The superpowers flow writes a spec, then a plan, then builds. A
superpowers spec holds the problem, the user's rulings, numbered design decisions,
gates, risks, out-of-scope items and amendments in one file; its plan adds the files
each task touches. A second home for any of these breaks the rule that each fact is
defined once, so each needs exactly one home in this corpus.

## Decision Drivers

- Each fact has exactly one home, and a decision is defined only in a MADR
- A planning session produces documents the existing checks already hold
- The plan can trace every designed element to the task that builds it

## Considered Options

:::{opt} Compose the spec from an RFC, its MADRs and a design doc, and add a plan type
:id: OPT_0008_COMPOSE
Good, because every part of a spec lands where a check already holds it, and the only new
type is the plan, which nothing here covered. Bad, because a planning session writes
several files where a superpowers spec is one.
:::

:::{opt} A spec document type with its own numbered decisions
:id: OPT_0008_SPEC_TYPE
Good, because one file per spec matches the superpowers default. Bad, because its
decisions duplicate the MADRs' job, escape their immutability rule, and give a choice
two possible homes.
:::

:::{opt} Superpowers-shaped markdown checked outside the graph
:id: OPT_0008_SHAPES
Good, because it is the smallest change to how specs are written today. Bad, because
headings and numbering are checked but nothing links a decision, a requirement or a task
to anything, so traceability is a convention again.
:::

## Decision Outcome

Chosen option: {need}`OPT_0008_COMPOSE`, because it is the only option that keeps one home
per fact while adding the one thing the corpus lacked, the plan.

## Consequences

- Good, because each part of a superpowers spec has one home: the problem and the
  out-of-scope items in the RFC; a ruling in a MADR whose context quotes the user with a
  date and whose decision makers name the user; a design decision in a MADR or a
  component; a gate in a requirement with its negative fixture, and per task in its
  `gate`; risks in the design doc and in each MADR's consequences.
- Good, because a plan needs no Files section (the files are the `spec` paths of the
  components its tasks build) and no Amendments section (an accepted MADR changes only
  by supersession; an RFC, design doc or plan changes in git and is reviewed again).
- Good, because a plan links to one design doc, so a design element no task builds is a
  finding.
- Bad, because the superpowers skills write their own one-file template; `tools/new.py`
  writes these skeletons, and the check rejects what a skill's template gets wrong.
