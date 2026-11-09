---
status: accepted
date: 2026-11-08
decision-makers: [claude]
informed: [wyatt]
---
# Resolved tasks and statuses are held against the base ref

:::{decision}
:chooses: OPT_0012_LIFECYCLE
:resolves: Q_TASK_FREEZE
:driven_by: REQ_FROZEN_TASKS, REQ_STATUS_FORWARD
:::

## Context and Problem Statement

A resolved task and its As built entry record what was built, and a document's status
records how far it has come. MADRs are already frozen by comparing each one with its
version at a base git ref. Tasks and statuses need the same protection, and the review
digest alone does not give it: a plan edited and reviewed again would pass with its
history rewritten.

## Decision Drivers

- One mechanism freezes history: MADRs, tasks and statuses alike
- Open tasks stay free to change and to be renumbered
- A re-review cannot launder a rewritten task

## Considered Options

:::{opt} Extend the lifecycle checker to resolved tasks and statuses
:id: OPT_0012_LIFECYCLE
Good, because the base-ref comparison already exists and runs in CI with the right base.
Bad, because the rule runs only when a base ref is given, and a force push to the base
branch can rewrite what it compares against.
:::

:::{opt} A digest on each resolved task
:id: OPT_0012_TASK_DIGEST
Good, because it needs no git. Bad, because the author who edits the task can rewrite its
digest in the same edit.
:::

:::{opt} Rely on the review digest
:id: OPT_0012_REVIEW
Good, because nothing new is built. Bad, because a fresh review legitimises any change,
including to history.
:::

## Decision Outcome

Chosen option: {need}`OPT_0012_LIFECYCLE`, because it is the only option an author cannot
satisfy by editing the plan alone.

## Consequences

- Good, because MADRs, tasks and statuses share one checker and one base ref.
- Bad, because a local run without `BASE` freezes nothing, so CI fails a push whose base
  it cannot resolve, and the base branch is protected against force pushes.
