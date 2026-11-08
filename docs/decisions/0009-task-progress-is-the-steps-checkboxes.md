---
status: accepted
date: 2026-11-08
decision-makers: [claude]
informed: [wyatt]
---
# Task progress is the steps' checkboxes

:::{decision}
:chooses: OPT_0009_CHECKBOXES
:resolves: Q_TASK_PROGRESS
:driven_by: REQ_STATUS_SINGLE_SOURCE, REQ_LINEAR_EXECUTION, REQ_AS_BUILT
:::

## Context and Problem Statement

A building session ticks off work as it goes and a resuming session has to find the next
piece of work without reading the whole plan. The progress of a task has to live
somewhere, and anything that restates it can disagree with it.

## Decision Drivers

- Progress has one home, and a child need carries no status of its own
- The next piece of work is found mechanically
- Ticking a step is the same edit a superpowers plan already makes

## Considered Options

:::{opt} Numbered checkboxes in the task body, executed in order
:id: OPT_0009_CHECKBOXES
Good, because the checkbox is the only record of progress, a task is resolved exactly
when its steps are, and the next step is the first open checkbox in the file. Bad,
because work that could run in parallel has to be a separate plan.
:::

:::{opt} A state field on each task need
:id: OPT_0009_FIELD
Good, because state is queryable in needtables. Bad, because it restates what the steps
already say and breaks the rule that child needs carry no status.
:::

:::{opt} A progress file beside the plan
:id: OPT_0009_LEDGER
Good, because the plan text never changes during a build. Bad, because the plan and its
ledger can disagree, and a reader needs both to know where the work stands.
:::

## Decision Outcome

Chosen option: {need}`OPT_0009_CHECKBOXES`, because it keeps progress in one place and
makes the next step a lookup.

## Consequences

- Good, because task numbers are build order, so no task declares what it depends on.
- Good, because `tools/next.py` prints the task holding the next open step.
- Bad, because inserting a task before open ones renumbers them; resolved tasks and ticked
  steps keep their numbers.
