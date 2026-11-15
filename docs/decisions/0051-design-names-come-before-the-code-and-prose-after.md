---
status: accepted
date: 2026-11-15
decision-makers: [wyatt]
informed: [claude]
---
# Design names come before the code and prose after

:::{decision}
:chooses: OPT_0051_NAMES
:resolves: Q_BUILD_ORDER
:::

## Context and Problem Statement

{need}`RFC_0010` records that the book it reads faults a description of a solution
written ahead of the solution, and that this fault holds in full here. Under
{need}`DEC_0008` a design doc is part of a spec, and it is approved, components,
interfaces and prose together, before any of it is built. The question is which of that
has to exist before the code.

Measured at commit `f8818bf` on 2026-11-15, over the seven design docs whose history
holds a commit that set them to approved ({need}`DES_0003` to {need}`DES_0009`),
comparing each at that commit with its text now:

| Reading | At approval | Now |
| --- | --- | --- |
| Components and interfaces named | 46 | 48: all 46 kept, 2 added, none dropped |
| Lines, all seven together | 1,102 | 2,178 |
| Of those, lines in the Review sections | 40 | 438 |
| Lines outside the Review sections | 1,062 | 1,740 |

The commands: `git log --reverse -S'status: approved'` for the approving commit of each;
the `:id:` lines that start `COMP_` or `IF_` at that commit and now; `wc -l` of each
text, and of each from its Review heading to its end. The two design docs that are not
built, {need}`DES_0005` and {need}`DES_0007`, are among the seven and changed least.

So the breakdown into components and interfaces, made before the code, held: nothing
named was dropped. The prose about them did not: outside the review records it grew by
678 lines, about two thirds again, while the code was written. The measurement does not
separate prose that changed its meaning from prose that was added, such as the `spec`
paths set when a component is built.

## Decision Drivers

- The book's fault with a solution described before it is built, which {need}`RFC_0010`
  finds to hold here
- A person's time to read and review, which is what is scarce where a session writes
- A plan's tasks name the components they build, so a plan needs them named
- What the measurement shows held, and what it shows did not

## Considered Options

:::{opt} Names first, prose after
:id: OPT_0051_NAMES
Before the code, a spec is its RFC, its decision records, and a design doc that holds
the names of its components and interfaces and their links, and no more. What is said
about each is written once it is built. Good, because the part that held is the part
kept ahead of the code, and the part that changed is written when it is known. Good,
because a plan's tasks still name what they build. Bad, because a design doc is reviewed
twice, once as names and once as prose. Bad, because what a name alone tells a session
to build is less than the prose told it.
:::

:::{opt} Design after the build
:id: OPT_0051_AFTER
Before the code, a spec is its RFC and its decision records. The design doc is written
from the built code and is approved only once its `spec` paths exist. Good, because
nothing describes the solution ahead of it, which answers the book's fault whole. Bad,
because a plan can no longer name the components it builds, so the links from a plan to
a design and from a task to a component have to be made again another way. Bad, because
the measurement does not call for it: the names held.
:::

:::{opt} Keep the full design first
:id: OPT_0051_FULL
A design doc is approved whole before the code, as now. Good, because nothing changes
and a session is told the most. Bad, because the prose approved is not the prose that
stands once the code is written, so what a person reviewed is not what is true.
:::

## Decision Outcome

Chosen option: {need}`OPT_0051_NAMES`, because wyatt, 2026-11-15, choosing from Claude's
recommendations: "Thin design first (Recommended)". The ask that was put gave the share
of the growth that was review records as about half; the table above measures it as 398
of 1,076 lines, a little over a third. Asked the same day whether the choice stands on
the corrected reading, wyatt: "Yes, it stands".

## Consequences

- Good, because what is approved before the code is short, and is the part that has held.
- Good, because {need}`Q_UNBUILT_DESIGN` grows smaller: a design that nothing builds is
  then a list of names, not pages of prose that may never be true.
- Bad, because the check does not yet tell a design doc of names from a whole one;
  {need}`RFC_0010` has no requirement for it, and one has to be written before this
  binds anything.
- Bad, because the design docs already approved or implemented were written whole, and
  this says nothing of them.
- Bad, because how much a session needs said about a component in order to build it is
  not known, and this was not tried.
