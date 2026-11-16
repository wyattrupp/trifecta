---
status: accepted
date: 2026-11-15
decision-makers: [wyatt]
informed: [claude]
---
# A built component is described in its source

:::{decision}
:chooses: OPT_0052_SOURCE_AND_RELATIONS
:resolves: Q_COMPONENT_HOME
:::

## Context and Problem Statement

{need}`RFC_0010` records that the book it reads prefers knowledge kept on the thing it is
about to knowledge kept in a separate file, and that this fault holds in full here: a
design doc is a separate file of facts about the code. {need}`DEC_0051` settled that
what is said about a component is written once it is built. It did not settle where.

Measured at commit `50ff955` on 2026-11-15, over the nine design docs and the 27 Python
files under `src`:

| Reading | Value |
| --- | --- |
| Component and interface needs | 64: 56 components, 8 interfaces |
| Words of prose inside those needs | 13,177 |
| Words in docstrings in the source | 10,148 |
| Words in comments in the source | 7,056 |
| Needs with a `spec` path | 49 |
| Of those, needs whose id is named in the source | 30 |
| Of those, needs whose `spec` file has a commit later than the last change to the need's own lines | 27, with 154 such commits |
| Of those, needs whose `spec` path is not a Python file | 7 |
| Needs whose id is named in two or more source files | 14 |

How each was read: the needs are the `component` and `interface` directives, and their
prose is the text between the options and the closing fence; docstrings by Python's
`ast` module over modules, classes and functions; comments as lines that start with `#`;
the last change to a need's lines by `git log -L` over them, and the later commits by
`git log` on the file its `spec` path names.

So the source already holds more words about itself than the design docs hold about it,
and nothing compares the two. For 27 of the 49 built needs the code has moved since the
prose beside it last did. Three limits on that reading: the source's words are all of
its docstrings and comments, not only those about a component; the later commits are
counted for the whole file a `spec` path names, not for the one symbol, so the 27 is an
upper bound; and no need's prose was read against its code, so how much of it is now
wrong is not known.

## Decision Drivers

- The book's preference for knowledge on the thing it is about, which {need}`RFC_0010`
  finds to hold here
- The book's one allowance: a fact about how files relate belongs outside them
- A session reads the source it changes, and does not always read the design doc
- Two descriptions of one component, written by hand, with no check between them

## Considered Options

:::{opt} Source, with relations outside
:id: OPT_0052_SOURCE_AND_RELATIONS
Once a component is built, what it does is said in its source, as a docstring or a
comment. Its need in the design doc keeps its name, its links and its `spec` path, and
prose only for what no one file can say: how files relate, and why. Good, because one
component has one description, and it is where a change to the component is made. Good,
because the 14 needs that span files and the 7 whose source has no docstring keep a
home. Bad, because where the line falls between what a component does and how files
relate is a judgement no check makes. Bad, because the built pages no longer show a
component's description unless something draws it from the source.
:::

:::{opt} Source only
:id: OPT_0052_SOURCE_ONLY
A need in a design doc is a name, its links and its `spec` path, with no prose. Good,
because the corpus is shortest and nothing is said twice. Bad, because a fact about
several files then has to be put on one of them, and a ruleset in JSON has nowhere to
put it at all.
:::

:::{opt} Design doc, as now
:id: OPT_0052_DESIGN
The need stays the home of the description, written after the build under
{need}`DEC_0051`. Good, because nothing changes and the built pages hold it all. Bad,
because the source goes on describing itself beside it, and the two drift apart unseen.
:::

## Decision Outcome

Chosen option: {need}`OPT_0052_SOURCE_AND_RELATIONS`, because wyatt, 2026-11-15, choosing
from Claude's recommendations with the readings above in the ask: "Source, relations
outside (Recommended)".

## Consequences

- Good, because with {need}`DEC_0051` a design doc is names and links before the build,
  and names, links and relations after it.
- Good, because {need}`Q_SPEC_STRENGTH` grows smaller: a `spec` path with little prose
  beside it has little to prove.
- Bad, because the check does not yet hold any of this; {need}`RFC_0010` has no
  requirement for it, and one has to be written before this binds anything.
- Bad, because the 13,177 words already in the design docs were written under the old
  rule, and this says nothing of moving them.
- Bad, because whether the built pages draw a component's description from its source is
  left open, and falls to {need}`Q_DIAGRAM_SOURCE` and {need}`Q_TERM_SOURCE` only in part.
