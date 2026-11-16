---
status: accepted
date: 2026-11-15
decision-makers: [wyatt]
informed: [claude]
---
# A done plan keeps its As built and loses its steps

:::{decision}
:chooses: OPT_0057_KEEP_AS_BUILT
:resolves: Q_PLAN_LIFETIME
:::

## Context and Problem Statement

{need}`RFC_0010` records that the book it reads throws a plan away once the work is done,
and that this holds here in part: the book relies on people remembering what mattered in
the plan, and here the As built entry is that memory. A done plan stays in the corpus
whole, and {need}`DEC_0012` freezes its resolved tasks, steps included.

Measured on 2026-11-15 at commit `50ff955`, over the six plans whose status is done:

| Reading | Value |
| --- | --- |
| Words in the six plans | 20,522 |
| Of those, in the As built sections | 11,184 |
| Of those, in the tasks and their steps | 7,612 |
| Of those, before the tasks | 991 |
| Of those, in the Review sections | 735 |
| Commits to a plan after the commit that set it to done | 3, over the six |
| Done plans that another file cites | 6 of 6, from 2 to 10 files each |
| Accepted decision records that cite a done plan | 7 |
| Citations from outside a plan of one of its tasks or steps | 0 |
| Places an As built section names a step by its number | 6, in 3 plans |
| Dropped steps in the six plans | 0 |

How each was read: words by section, split at the Tasks, Review and As built headings; a
citation as the plan's id or the id of one of its tasks found in another file under
`docs`, `src` or `tests`, or in the README; a step named by number as the word step with
a number of the form `N.k` after it, inside the As built section.

So a done plan holds two things of different worth. Its As built is cited as a record of
what happened, by later plans, by design docs and by decision records that cannot now
change. Its steps are instructions that were carried out, and nothing outside the plan
points at them. Two limits: that the As built is used as memory is read from the
citations, not from watching a session use it; and how much of the As built describes a
component, which {need}`DEC_0052` now sends to the source, was not measured.

## Decision Drivers

- What is left of the book's fault in {need}`RFC_0010`: the list of steps is short-lived
  and the As built is not
- Seven accepted decision records cite a done plan by its id, and they are immutable
- {need}`REQ_FROZEN_TASKS` holds a resolved task's steps to the base ref
- A person's reading time, and the size of the corpus

## Considered Options

:::{opt} The As built stays and the steps go
:id: OPT_0057_KEEP_AS_BUILT
When a plan is done, its id, the titles of its tasks, its review records and its As
built stay for good, and the lists of steps are removed. Good, because every citation of
a done plan still resolves, and what is left is the part that is cited. Good, because
about 7,600 words leave the corpus now. Bad, because {need}`REQ_FROZEN_TASKS` forbids it
as written and has to be superseded for steps. Bad, because the six places an As built
names a step by number then point at nothing.
:::

:::{opt} Keep the plan whole
:id: OPT_0057_WHOLE
{need}`DEC_0012` stands, and a done plan is kept entire and frozen. Good, because nothing
is built. Bad, because instructions that were carried out stay in the corpus for good.
:::

:::{opt} Remove the plan when it is done
:id: OPT_0057_REMOVE
The book's way: the plan is deleted and git holds it. Good, because the corpus is
shortest. Bad, because seven decision records that cannot change cite a done plan, with
later plans and design docs, and every one of those links would break.
:::

:::{opt} Move the plan to an archive
:id: OPT_0057_ARCHIVE
A done plan leaves the checked corpus for a place the build links to and does not
validate. Good, because nothing is lost and links hold. Bad, because the tool gains a
second kind of place, and what is not validated can go stale unseen.
:::

## Decision Outcome

Chosen option: {need}`OPT_0057_KEEP_AS_BUILT`, because wyatt, 2026-11-15, choosing from
Claude's recommendations with the readings above in the ask: "As built stays, steps go
(Recommended)".

## Consequences

- Good, because a done plan becomes a record of what happened and no longer also a list
  of what to do.
- Bad, because nothing here has been applied: the six done plans still hold their steps,
  and removing them now would fail {need}`REQ_FROZEN_TASKS`.
- Bad, because {need}`DEC_0012` is accepted and says otherwise for steps. This does not
  change it; {need}`RFC_0010` has to gain a requirement, and the earlier one has to be
  superseded, before a step is removed.
- Bad, because the review digest of a plan covers its step marks, so a done plan's
  reviews would have to be taken again or the digest changed.
- Bad, because the As built itself is left whole, and the part of it that describes a
  component is now said in two places until someone moves it.
