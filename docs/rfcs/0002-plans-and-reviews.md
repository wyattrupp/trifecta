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
A plan MUST have at least one task. A task MUST be a closed `task` directive under its
plan's Tasks section, MUST build at least one component or interface, MUST state a gate,
and MUST contain at least one step; every checkbox in a plan MUST be a step of a task.
A step MUST be written `- [ ] **N.k** text` while open, `- [x] **N.k** text` when done
and `- [-] **N.k** text` when dropped, where N is the task's number and k runs from 1
without gaps. In an active or done plan, a gate or step MUST NOT be the skeleton
placeholder.
:::

:::{req} Execution is linear
:id: REQ_LINEAR_EXECUTION
In a draft, active or done plan, a step MUST NOT be done or dropped while an earlier
step of the same plan is open, and a draft plan MUST NOT have a done or dropped step. An
abandoned plan is exempt.
:::

:::{req} As built records each resolved task
:id: REQ_AS_BUILT
The As built section of a draft, active or done plan MUST hold exactly one
`### Task N (YYYY-MM-DD)` entry for each resolved task, in task order, and a done plan
MUST have every task resolved. An abandoned plan is exempt.
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

## Out of scope

Freezing a resolved task against a base ref, as MADRs are frozen; checking that a review
is newer than the document's last change; the wording of an As built entry, including
why a step was dropped. Each is convention until a requirement says otherwise.

## Review

:::{review} Correctness; single source of truth and fidelity to the superpowers shapes
:id: REV_RFC_0002_1
:k: 2
:date: 2026-11-08
The first draft of this RFC, its three MADRs, design doc 0002, plan 0001 and the code at
commit 6eb3205, lenses as titled (fidelity in place of security: the change parses local
markdown). The local cross-check model was unreachable, so no pass came from another
model lineage. Every finding was verified against the code and the corpus. Folded in, as
task 5 of {need}`PLAN_0001`: unclosed and nested task blocks, checkboxes outside a task
and plans with no task, padded task and step numbers, placeholders left in a relied-on
plan, the abandoned-plan exemption written into the requirements, Out of scope and Risks
sections, the user's ruling quoted in {need}`DEC_0008`, documents outside the typed
directories rejected, and one home each for plan statuses, frontmatter parsing, the lint
directories and the design doc's derived views. Deferred, and listed under Out of scope:
freezing resolved tasks against a base ref, and review staleness.
:::
