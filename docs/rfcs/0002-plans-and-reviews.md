---
status: accepted
authors: [claude]
created: 2026-11-08
---
# Plans and reviews

:::{rfc}
:::

## Summary

A planning session produces a spec and a plan, and a building session executes the plan
in order. In this {need}`corpus <TERM_CORPUS>` a spec is not a new kind of document: it
is an RFC for the problem and the requirements, the MADRs for each choice, and a design
doc for the components. What the corpus lacked is added here: a {need}`plan <TERM_PLAN>`
whose {need}`tasks <TERM_TASK>` build the design in order, and a
{need}`review <TERM_REVIEW>` record that an RFC, a design doc and a plan carry before
they are relied on.

## Motivation

A plan written as free prose drifts the way the rest of the documentation did before
this corpus. Tasks get numbered three ways, inserted with letters, and executed out of
order; a session resuming the work reads the whole plan to find where it is. A design
component nobody planned is never built, and nothing notices. Specs get relied on before
anyone reviews them.

Holding plans to the same graph turns each of these into a {need}`finding <TERM_FINDING>`:
the task order is the build order, the next {need}`step <TERM_STEP>` is the first open
checkbox, every component of a planned design is built by a task, and an unreviewed
document cannot be accepted, approved or made active.

## Terms

:::{term} Plan
:id: TERM_PLAN
A document under `docs/plans/` that implements one design doc as an ordered list of tasks.
:::

:::{term} Task
:id: TERM_TASK
A numbered unit of a plan that builds named components or interfaces and states its gate.
:::

:::{term} Step
:id: TERM_STEP
A numbered checkbox inside a task: open, done or dropped.
:::

:::{term} Gate
:id: TERM_GATE
What decides that a task is done: the fixtures, commands or checks that pass.
:::

:::{term} Review
:id: TERM_REVIEW
A dated record in a document's Review section of a review with k distinct-lens passes.
:::

## Requirements

:::{req} A plan implements one design doc
:id: REQ_PLAN_IMPLEMENTS
A plan MUST implement exactly one design doc.
:::

:::{req} Tasks run in build order
:id: REQ_TASK_ORDER
A task ID MUST be `TASK_<plan number>_<NN>`, and task numbers MUST run from 01 in
document order without gaps.
:::

:::{req} Tasks have a fixed shape
:id: REQ_TASK_SHAPE
A task MUST sit under its plan's Tasks section, MUST build at least one component or
interface, MUST state a gate, and MUST contain at least one step. Steps MUST be written
`- [ ] **N.k** text`, where N is the task's number and k runs from 1 without gaps.
:::

:::{req} Execution is linear
:id: REQ_LINEAR_EXECUTION
A step MUST NOT be done or dropped while an earlier step of the same plan is open, and a
draft plan MUST NOT have a done or dropped step.
:::

:::{req} As built records each resolved task
:id: REQ_AS_BUILT
A plan's As built section MUST hold exactly one `### Task N (YYYY-MM-DD)` entry for each
resolved task, in task order, and a done plan MUST have every task resolved.
:::

:::{req} A planned design is built in full
:id: REQ_DESIGN_BUILT
Once a draft, active or done plan implements a design doc, every component and interface
of that design MUST be built by a task of such a plan.
:::

:::{req} Relied-on documents are reviewed
:id: REQ_REVIEWED
An accepted RFC, an approved or implemented design doc, and an active or done plan MUST
each record at least one review, and every review MUST state its k and its date.
:::

## Questions

:::{question} Where does a spec live?
:id: Q_SPEC_HOME
:::

:::{question} Where does a task's progress live?
:id: Q_TASK_PROGRESS
:::

:::{question} Where is a review recorded?
:id: Q_REVIEW_HOME
:::

## Review
