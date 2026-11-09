---
status: approved
authors: [claude]
---
# Plan and review lifecycle

:::{design}
:::

## Overview

Four additions hold plans, reviews and statuses to their past. A digest module reduces a
raw document to its reviewed content and hashes it; the document extension compares that
hash with the `digest` of the document's reviews and keeps the Review section to review
records, and a command stamps a review with the digest the reviewer was given. The
lifecycle checker, which already freezes MADRs against a base ref, also compares every
task resolved at that ref and every document's status with the current tree. The plan
rules check that each dropped step is cited in its task's As built entry. The graph
checker requires a live plan for each approved design and a `spec` on each element of an
implemented one.

Components here have no `spec` until they are built; the plan that builds them adds it.

## Requirements

:::{needtable}
:filter: type == 'req' and len(satisfies_back) > 0
:columns: id, title, satisfies_back as "Satisfied by"
:style: table
:::

## Constraints

:::{needtable}
:filter: type == 'decision' and len(constrained_by_back) > 0
:columns: id, title, status
:style: table
:::

## Components

:::{component} Review digest
:id: COMP_REVIEW_DIGEST
:satisfies: REQ_REVIEW_CURRENT
:constrained_by: DEC_0011
:provides: IF_REVIEW_DIGEST
Computes a document's reviewed content and its SHA-256 from the raw file, reports an
accepted, approved, implemented, active or done document none of whose reviews carries
that digest, and reports anything but a review record in a Review section.
:::

:::{component} Review command
:id: COMP_REVIEW_COMMAND
:constrained_by: DEC_0011
:consumes: IF_REVIEW_DIGEST
`review digest <doc>` prints the digest when a review starts; `review stamp <doc>` appends
a review record with today's date, the lenses, k and the digest it is given, and refuses
when the file's digest no longer matches or the path is not a typed document.
:::

:::{component} Lifecycle extension
:id: COMP_TASK_FREEZE
:satisfies: REQ_FROZEN_TASKS, REQ_STATUS_FORWARD
:constrained_by: DEC_0012
:consumes: IF_PLAN_SHAPE
Reads every plan under `docs/plans/` at the base ref, and reports a task resolved there
whose raw text, step marks or As built entry differ now, or that is gone from its plan.
Compares each typed document's status with the base ref and reports a backward move.
:::

:::{component} Drop-reason rule
:id: COMP_DROP_REASONS
:satisfies: REQ_DROP_REASONS
:constrained_by: DEC_0009
:consumes: IF_PLAN_SHAPE
Reports a dropped step of a resolved task whose number `N.k` does not occur in its task's
As built entry as a whole number pair, not inside a longer number.
:::

:::{component} Build-state rules
:id: COMP_BUILD_STATE
:satisfies: REQ_APPROVED_IS_PLANNED, REQ_IMPLEMENTED_HAS_SPEC
:constrained_by: DEC_0008
:consumes: IF_NEEDS_JSON
Reports an approved design doc that no draft, active or done plan implements, and a
component or interface of an implemented design doc with no `spec`.
:::

## Interfaces

:::{interface} Review digest
:id: IF_REVIEW_DIGEST
:constrained_by: DEC_0011
The digest is computed from the raw file. The `status:` line inside the first `---`
frontmatter block, every `:spec:` option line, and the Review section, from its H2 line up
to the next H2 outside a code fence or the end of the file, MUST be removed; for a plan,
the As built section MUST be removed the same way and the mark of every step line read as
open. Each remaining line MUST be stripped of trailing whitespace, the lines MUST be
joined with a single newline and no final newline, and the digest MUST be the lowercase
hex SHA-256 of that text encoded as UTF-8.
:::

## Risks

A normalisation bug would make every review stale at once; the fixtures cover an edit that
changes the digest, and the corpus itself, with ticked steps and `spec` paths added after
review, covers the edits that do not. Adding the digest makes every review stale until it
is stamped, so the plan reviews the corpus again in the same task. CI freezes history only
when it can resolve a base, so a push whose base cannot be resolved fails, and the base
branch needs protection against force pushes.

## Review

:::{review} Correctness; security
:id: REV_DES_0003_1
:k: 2
:date: 2026-11-08
The review recorded as {need}`REV_RFC_0003_1` covered this document.
:::
