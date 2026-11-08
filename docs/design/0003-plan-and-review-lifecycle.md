---
status: approved
authors: [claude]
---
# Plan and review lifecycle

:::{design}
:::

## Overview

Three additions hold plans and reviews to their past. A digest module reduces a
document to its reviewed content and hashes it; the document extension compares that
hash with the `digest` of the document's reviews, and a command writes a review record
with the current digest. The lifecycle checker, which already freezes MADRs against a
base ref, also compares every task resolved at that ref with its current text. The plan
rules check that each dropped step is cited in its task's As built entry.

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
Computes a document's reviewed content and its SHA-256, and reports an accepted,
approved, implemented, active or done document none of whose reviews carries that digest.
:::

:::{component} Review command
:id: COMP_REVIEW_COMMAND
:constrained_by: DEC_0011
:consumes: IF_REVIEW_DIGEST
Appends a review record to a document's Review section with today's date, the lenses
and k given, and the current digest, and prints the digest on request.
:::

:::{component} Frozen-task checker
:id: COMP_TASK_FREEZE
:satisfies: REQ_FROZEN_TASKS
:constrained_by: DEC_0012
:consumes: IF_PLAN_SHAPE
Compares every task resolved at the base ref, with its As built entry, against the
current plan and reports any change or removal.
:::

:::{component} Drop-reason rule
:id: COMP_DROP_REASONS
:satisfies: REQ_DROP_REASONS
:constrained_by: DEC_0009
:consumes: IF_PLAN_SHAPE
Reports a dropped step whose number does not occur in its task's As built entry.
:::

## Interfaces

:::{interface} Review digest
:id: IF_REVIEW_DIGEST
:constrained_by: DEC_0011
The reviewed content of a document is its lines without the frontmatter `status:` line
and without the Review section; for a plan, also without the As built section and with
every step mark read as open. Lines MUST be stripped of trailing whitespace and joined
with a newline, and the digest MUST be the lowercase hex SHA-256 of that text.
:::

## Risks

A normalisation bug would make every review stale at once; the fixtures cover an edit
that changes the digest and a tick that does not. Adding the digest makes every existing
review stale until it is stamped, so the plan stamps them in the same task.

## Review
