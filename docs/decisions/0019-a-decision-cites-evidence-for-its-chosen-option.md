---
status: accepted
date: 2026-11-08
decision-makers: [wyatt]
consulted: [claude]
---
# A decision cites evidence for its chosen option

:::{decision}
:chooses: OPT_0019_CHOSEN
:resolves: Q_EVIDENCE_DUTY
:driven_by: REQ_EVIDENCE_REQUIRED, REQ_EVIDENCE_PLANNING
:::

## Context and Problem Statement

wyatt, 2026-11-08, answered "A" when asked what the middle rigor level demands. At `off`
nothing is demanded and `strict` adds to this level, so this level sets what every
decision at either of them has to show.

## Decision Drivers

- Proof lands where "why this and not that" is answered
- No citation is written only to satisfy the check
- The rule is one test on the graph

## Considered Options

:::{opt} The chosen option of every accepted decision links evidence
:id: OPT_0019_CHOSEN
Good, because decisions are where a choice needs proof, and requirements mostly state a
need that the MADR quoting its owner already records. Bad, because a rejected option can
still be dismissed with no evidence.
:::

:::{opt} The chosen option and every requirement of an accepted RFC link evidence
:id: OPT_0019_REQUIREMENTS
Good, because it is more thorough. Bad, because a requirement such as "the check is
deterministic" is a statement of need that no paper or experiment proves, so it would
gather filler citations.
:::

:::{opt} Every considered option links evidence
:id: OPT_0019_EVERY_OPTION
Good, because a rejected option has to be rejected on evidence too. Bad, because an option
written only to be knocked down would need citations of its own.
:::

## Decision Outcome

Chosen option: {need}`OPT_0019_CHOSEN`, because wyatt chose it, and it asks for proof
exactly where a choice is made.

## Consequences

- Good, because the check is one test: the chosen option of each accepted decision has a
  `supported_by` link.
- Good, because the planning files tell a session to find or produce the evidence before
  it writes the MADR, so the citation is not added after the fact.
- Bad, because a rejected option's dismissal still rests on its author's word.
