---
status: accepted
date: 2026-11-08
decision-makers: [wyatt]
consulted: [claude]
---
# Strict rigor pre-registers experiments and protocols

:::{decision}
:chooses: OPT_0020_PREREGISTRATION
:resolves: Q_STRICT_RIGOR
:driven_by: REQ_PREREGISTERED, REQ_SURVEY_PROTOCOL
:::

## Context and Problem Statement

wyatt, 2026-11-08, answered "A" when asked what the strict level adds. The weak points of
evidence are a prediction written after the results, results re-run until they agree, and
sources picked because they agree.

## Decision Drivers

- A prediction is fixed before the results exist
- A survey shows how it found its sources
- The rule fits engineering decisions, where one sound benchmark is often all there is

## Considered Options

:::{opt} Pre-registration, pinned data and survey protocols
:id: OPT_0020_PREREGISTRATION
Good, because once an experiment is `running` on the base ref its hypothesis, prediction
and method are frozen by the lifecycle checker that freezes resolved tasks, results appear
only when it is `concluded`, and each survey states where and how it searched before it
lists sources. Bad, because a running experiment whose method turns out wrong has to be
abandoned and started again as a new one.
:::

:::{opt} Pre-registration only
:id: OPT_0020_PREREGISTRATION_ONLY
Good, because it is lighter. Bad, because surveys can stay cherry-picked.
:::

:::{opt} Pre-registration, protocols and replication
:id: OPT_0020_REPLICATION
Good, because two independent pieces of evidence per decision is the strongest rule.
Bad, because many engineering decisions will only ever have one sound benchmark.
:::

## Decision Outcome

Chosen option: {need}`OPT_0020_PREREGISTRATION`, because wyatt chose it, and it closes the
three weak points without asking for evidence an engineering decision cannot have.

## Consequences

- Good, because pre-registration is enforced by the check against the base ref, not by
  trust in the author.
- Good, because a concluded experiment is frozen whole, so a verdict cannot change under a
  decision that rests on it.
- Bad, because the check proves only that the prediction came first; whether the method
  tests the hypothesis stays with the review.
