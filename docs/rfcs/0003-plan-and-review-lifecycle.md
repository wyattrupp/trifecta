---
status: accepted
authors: [claude]
created: 2026-11-08
---
# Plan and review lifecycle

:::{rfc}
:::

## Summary

{need}`RFC_0002` left three rules to convention. A resolved
{need}`task <TERM_TASK>` can be rewritten after the fact, a
{need}`review <TERM_REVIEW>` stays valid however much the document changes after it, and
the reason a {need}`step <TERM_STEP>` was dropped is never recorded. This RFC makes each
of them a requirement.

## Motivation

A plan's resolved tasks and their As built entries are the record of what was built, and
other documents cite them. Editing one after the fact changes history the way editing an
accepted MADR would, and MADRs are already frozen.

A review is only evidence for the text it read. A document approved after review and
edited the next day carries a review of something else, and nothing notices.

A dropped step is work the plan promised and did not do. Without its reason, the next
session cannot tell an abandoned idea from a forgotten one.

## Terms

:::{term} Digest
:id: TERM_DIGEST
A SHA-256 of a document's reviewed content, recorded on a review and recomputed by the check.
:::

## Requirements

:::{req} Resolved tasks are frozen
:id: REQ_FROZEN_TASKS
A task that is resolved at the base ref MUST NOT change: its ID, title, options, steps
and As built entry MUST match the base ref, and it MUST NOT be removed.
:::

:::{req} Reviews cover the current text
:id: REQ_REVIEW_CURRENT
An accepted RFC, an approved or implemented design doc, and an active or done plan MUST
have a review whose digest equals the digest of the document's current reviewed content.
:::

:::{req} Dropped steps give a reason
:id: REQ_DROP_REASONS
The As built entry of a task with a dropped step MUST cite each dropped step by its
number `N.k`.
:::

## Questions

:::{question} How does a review bind to the text it reviewed?
:id: Q_REVIEW_BINDING
:::

:::{question} Where are resolved tasks held to their past?
:id: Q_TASK_FREEZE
:::

## Out of scope

What a review or an As built entry says beyond the reasons for dropped steps; who may
review; how many passes a review needs. Each stays with the reviewer.

## Review
