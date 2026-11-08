---
status: accepted
date: 2026-11-08
decision-makers: [claude]
informed: [wyatt]
---
# A review records a digest of what it read

:::{decision}
:chooses: OPT_0011_DIGEST
:resolves: Q_REVIEW_BINDING
:driven_by: REQ_REVIEW_CURRENT
:::

## Context and Problem Statement

wyatt, 2026-11-08: "take out of scope items and plan them". One of them is that a review
record says nothing about the text it covered, so a document edited after its review
still passes. The record has to name what was reviewed in a form the check can compare
with the document as it is now.

## Decision Drivers

- The check is deterministic and runs without git history, as the fixture copies do
- Ticking a step or writing an As built entry does not invalidate a plan's review
- Any other edit to a reviewed document does

## Considered Options

:::{opt} A digest of the reviewed content on each review
:id: OPT_0011_DIGEST
Good, because the check recomputes it from the file alone and the comparison is exact.
Bad, because every reviewed edit needs a new digest, so a command has to write it.
:::

:::{opt} Compare the review date with the document's last commit
:id: OPT_0011_GIT_DATE
Good, because nothing new is written. Bad, because dates have day resolution, a commit
touching only the Review section moves the date, and shallow clones have no history.
:::

:::{opt} The commit the review read, diffed by the check
:id: OPT_0011_COMMIT
Good, because the reviewed text can be shown. Bad, because the commit can be squashed
away, and the check needs full history to diff against it.
:::

## Decision Outcome

Chosen option: {need}`OPT_0011_DIGEST`, because it is the only option that is exact and
needs nothing but the file.

## Consequences

- Good, because a plan's digest reads every step as open and leaves out As built, so the
  build itself never makes the review stale.
- Bad, because the frontmatter status is left out of the digest too, so that accepting a
  reviewed document is not an edit; a change of status is held by the lifecycle rules.
