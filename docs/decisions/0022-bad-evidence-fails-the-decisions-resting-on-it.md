---
status: accepted
date: 2026-11-08
decision-makers: [wyatt]
consulted: [claude]
---
# Bad evidence fails the decisions resting on it

:::{decision}
:chooses: OPT_0022_FAIL
:resolves: Q_BAD_EVIDENCE
:driven_by: REQ_SUPPORT_SOUND, REQ_EVIDENCE_REVIEWED
:::

## Context and Problem Statement

wyatt, 2026-11-08, answered "A" when asked what happens when evidence goes bad: a source
is retracted, or an experiment refutes its prediction. Accepted MADRs are frozen, so a
decision cannot be edited to drop the evidence it rests on.

## Decision Drivers

- A retraction reaches every decision it touches
- A failed experiment can still be cited for what it showed
- The corpus records that the ground moved, and what was decided after

## Considered Options

:::{opt} Bad evidence fails the decisions resting on it
:id: OPT_0022_FAIL
Good, because `supported_by` may point only at claims of sources that are not retracted
and at results of experiments concluded `supported`, `informed_by` cites anything without
counting as support, and a retraction makes every accepted decision supported by it a
finding until a new MADR supersedes it. Bad, because one retraction can fail the check on
a pull request that did not touch the decision.
:::

:::{opt} Leave it to review
:id: OPT_0022_REVIEW
Good, because it is simpler. Bad, because a retraction then changes nothing anyone is made
to look at.
:::

:::{opt} Report without failing
:id: OPT_0022_REPORT
Good, because bad evidence is visible. Bad, because a report that never fails is easy to
ignore.
:::

## Decision Outcome

Chosen option: {need}`OPT_0022_FAIL`, because wyatt chose it, and it is the only option
that makes a retraction reach the decisions it undermines.

## Consequences

- Good, because the fix is a superseding MADR, so the history shows the old decision, the
  retraction and the new decision.
- Good, because evidence that supports an accepted decision is reviewed k=2 like any
  relied-on document, so a claim is read against its source before it carries weight.
- Bad, because the rule holds at every rigor level, so a repository at `off` that uses
  `supported_by` takes on this duty too.
