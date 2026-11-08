---
status: accepted
authors: [claude]
created: 2026-11-08
---
# Plan and review lifecycle

:::{rfc}
:::

## Summary

{need}`RFC_0002` left the lifecycle of plans, reviews and statuses to convention. A
resolved {need}`task <TERM_TASK>` can be rewritten after the fact, a document's status
can move backwards, a {need}`review <TERM_REVIEW>` stays valid however much the document
changes after it, a dropped {need}`step <TERM_STEP>` leaves no trace, an approved design
can sit unbuilt forever, and an implemented one can name no artifact. This RFC makes each
of them a requirement.

## Motivation

A plan's resolved tasks and their As built entries are the record of what was built, and
other documents cite them. Editing one after the fact changes history the way editing an
accepted MADR would, and MADRs are already frozen. A status that moves back, such as an
implemented design returning to approved, quietly drops the obligations that came with
it.

A review is only evidence for the text it read. A document approved after review and
edited the next day carries a review of something else, and nothing notices.

A requirement is enforced, and needs its negative fixture, once a component of an
implemented design satisfies it. A design that stays approved with no live plan, or that
is marked implemented with no artifact, leaves requirements accepted and enforced by
nothing.

## Terms

:::{term} Digest
:id: TERM_DIGEST
A SHA-256 of a document's reviewed content, recorded on a review and recomputed by the check.
:::

## Requirements

:::{req} Resolved tasks are frozen
:id: REQ_FROZEN_TASKS
A task that is resolved at the base ref MUST NOT change: its ID, title, options, steps
with their marks, and As built entry MUST match the base ref, and it MUST NOT be removed
or moved to another plan.
:::

:::{req} Status moves only forward
:id: REQ_STATUS_FORWARD
Against the base ref, an accepted RFC MUST NOT return to draft or review, an approved
design doc MUST NOT return to draft, an implemented one MUST NOT return to approved or
draft, and a done plan MUST NOT return to active or draft.
:::

:::{req} Reviews cover the current text
:id: REQ_REVIEW_CURRENT
An accepted RFC, an approved or implemented design doc, and an active or done plan MUST
have a review whose digest equals the digest of the document's current reviewed content:
the raw file without its frontmatter `status` line, without its Review section, and
without `spec` option lines; for a plan, also without its As built section and with every
step mark read as open. A Review section MUST hold only review records.
:::

:::{req} Dropped steps are cited in As built
:id: REQ_DROP_REASONS
In a draft, active or done plan, the As built entry of a resolved task with a dropped step
MUST cite each dropped step by its number `N.k`.
:::

:::{req} Approved designs are planned
:id: REQ_APPROVED_IS_PLANNED
An approved design doc MUST be implemented by a draft, active or done plan.
:::

:::{req} Implemented designs name their artifacts
:id: REQ_IMPLEMENTED_HAS_SPEC
Every component and interface of an implemented design doc MUST have a `spec`.
:::

## Questions

:::{question} How does a review bind to the text it reviewed?
:id: Q_REVIEW_BINDING
:::

:::{question} Where are resolved tasks and statuses held to their past?
:id: Q_TASK_FREEZE
:::

## Out of scope

Who reviewed a document: the digest binds a review record to text, but it does not prove
that a review happened or who made it, and an author can stamp their own edit. Approval of
the pull request is that proof. Also out of scope: what a review or an As built entry says
beyond citing dropped steps, and how many passes a review needs.

## Review

:::{review} Correctness; security
:id: REV_RFC_0003_1
:k: 2
:date: 2026-11-08
The planning sets for {need}`RFC_0003` and {need}`RFC_0004`, with their MADRs, design
docs and plans, and the edits to {need}`RFC_0001` and {need}`RFC_0002` that came with
them, at commit 35760f3. The local cross-check model was unreachable, so no pass came from
another model lineage. Every finding was verified against the documents and the code.
Folded in: re-review and `spec` steps in both plans; the digest defined over the raw file
without status, `spec` lines and the Review section, which holds only review records; a
stamp takes the digest its review started from; drop citations scoped to resolved tasks
and matched as whole numbers; status moves only forward; an approved design needs a live
plan and an implemented one names its artifacts; the package's import, root and lock-line
changes; bare init passes; and in {need}`RFC_0004`, requirements for the pin form,
release trust, credentials, safe writes by init, and a hook that fails closed. Not taken:
rewriting a dated As built entry of {need}`PLAN_0001`, which is history.
:::
