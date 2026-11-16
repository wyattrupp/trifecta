---
status: accepted
date: 2026-11-15
decision-makers: [wyatt]
informed: [claude]
---
# A draft design that a plan implements is reviewed

:::{decision}
:chooses: OPT_0068_REVIEWED
:resolves: Q_DRAFT_REVIEW
:::

## Context and Problem Statement

By {need}`DEC_0066` a design doc stays draft while its plan is written and reviewed, and
is approved with the first step done. The review of {need}`RFC_0010`, security lens,
found that a draft design doc carries no review, so a plan would be written on names
nobody had reviewed, and that once {need}`REQ_COVERAGE` is amended an accepted RFC could
be covered by such a document for as long as nothing builds it.

Read on 2026-11-15 at commit `57686d9`: `src/trifecta/ext/digest.py` lists the statuses
of a design doc that are relied on as approved and implemented, and the rule that a
relied-on document records a review selects the same two. A draft design doc is in
neither.

### The ask as put

Question: "A draft design carries no review today (digest.py: only approved and
implemented are relied on), and under DEC_0066 a plan is written on a draft design.
Should a draft design that a plan implements have to carry a current review?"

Options, the first marked as recommended:

- "Yes, once a plan implements it (Recommended)": "Add to the requirements: a draft
  design doc that a draft or active plan implements is relied on and must carry a current
  review. Names and links get reviewed before a plan is built on them."
- "No, state it as a risk": "Leave draft designs unreviewed; the RFC already lists this
  under what the requirements leave at risk."
- "Hold it open": "Add it as an eighteenth question for a later ruling."

## Decision Drivers

- {need}`DEC_0066` moved approval later and took the review with it
- A plan's tasks name the components they build, so the names are what a plan rests on
- {need}`DEC_0051`: a draft design is short, so a review of it is cheap

## Considered Options

:::{opt} Reviewed once a plan implements it
:id: OPT_0068_REVIEWED
A draft design doc that a draft or an active plan implements is relied on and carries a
current review. Good, because nothing a plan is built on goes unread. Bad, because a
design is then reviewed as names and again when it is approved with its prose.
:::

:::{opt} Stated as a risk
:id: OPT_0068_RISK
A draft design doc stays unreviewed and the RFC says so. Good, because nothing is added.
Bad, because the gap {need}`DEC_0066` opened stays open.
:::

:::{opt} Held open
:id: OPT_0068_OPEN
The question waits for a later ruling. Good, because nothing is decided in haste. Bad,
because the RFC cannot be accepted with it open.
:::

## Decision Outcome

Chosen option: {need}`OPT_0068_REVIEWED`, because wyatt, 2026-11-15, choosing from
Claude's recommendations: "Yes, once a plan implements it (Recommended)".

## Consequences

- Good, because the review that approval used to bring still comes before a plan is
  built.
- Bad, because a draft design doc that no plan implements yet is still read by no
  review, and may cover an accepted RFC's requirements once {need}`REQ_COVERAGE` is
  amended.
- Bad, because {need}`REQ_REVIEWED` and {need}`REQ_REVIEW_CURRENT` have to be amended to
  take in such a draft.
