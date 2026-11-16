---
status: accepted
date: 2026-11-15
decision-makers: [wyatt]
informed: [claude]
---
# A spec path is an address, held both ways

:::{decision}
:chooses: OPT_0053_BOTH_WAYS
:resolves: Q_SPEC_STRENGTH
:::

## Context and Problem Statement

{need}`RFC_0010` records that the link from a design doc to the source proves little:
{need}`REQ_SPEC_RESOLVES` holds that a path exists and that a fragment occurs in it, and
the prose beside the path can go stale while the check passes. {need}`DEC_0052` moves
what a built component does into its source, so little prose is left beside the path.
What the path itself has to prove is still open.

Measured on 2026-11-15 at commit `50ff955`, over the 49 component and interface needs
that carry a `spec` path:

| Reading | Value |
| --- | --- |
| Files the 49 paths name | 28 |
| Paths with no fragment | 3 |
| Fragments that name a `def` or a `class` | 34 |
| Fragments that are a bare name, such as a constant | 8 |
| Fragments that are text in a workflow file or the README | 4 |
| Fragments the check's own pattern finds more than once in the file | 7 of 46 |
| Of those, fragments whose other match is a comment or a second workflow step | 2 |
| Top-level functions and classes in the 27 Python files under `src` | 394 |
| Of those, named by a fragment | 34 |
| Lines inside the named functions and classes, of the lines of those files | 1,183 of 10,730 |
| Needs whose `spec` file names the need's id | 28 of 49 |
| Needs with a `satisfies` link to a requirement | 36 of 49 |

How each was read: the fragments by the pattern in `check_graph.py`, the fragment
followed by no word character, counted over each file; functions and classes by Python's
`ast` module; a need's id by a search of the file its path names.

So the check holds that a place exists and no more. The place is found by a search for
text, not for a definition: for seven needs the text is found more than once, and for
two a comment or another step would keep the check passing with the named thing gone.
The path names one entry point of a component, about a ninth of the source by lines, and
says nothing of what it does. What a component does is held another way, by the
requirement it satisfies and the test that proves the requirement. One limit: the 28 is
counted for the whole file, not at the definition the fragment names, so the needs that
lack a name at that definition number 21 or more.

## Decision Drivers

- The book's fault with a check that still passes after what it guards has changed,
  which {need}`RFC_0010` finds to hold here most of all
- {need}`DEC_0052`: the description is in the source, so the source has to say which
  component it describes
- A test, through a requirement, already holds what a component does
- How often the source changes: for 27 of the 49 needs the `spec` file has a commit
  later than the need's own lines

## Considered Options

:::{opt} An exact address, held both ways
:id: OPT_0053_BOTH_WAYS
A `spec` path resolves to exactly one definition: a function, a class, an assignment, or
a named key in a file that is not Python. That place names the need's id back. The link
claims nothing of prose or of what the component does. Good, because a need whose
definition is gone fails the check, and a reader of the source learns which component it
is reading. Good, because it claims only what a tool can hold. Bad, because 21 or more
needs gain a name in their source. Bad, because a file with no place for a comment, such
as a ruleset in JSON, needs a rule of its own.
:::

:::{opt} An exact address only
:id: OPT_0053_EXACT
A `spec` path resolves to exactly one definition, and the source says nothing back.
Good, because the seven loose matches are closed with no change to the source. Bad,
because a description that lives in the source is not tied to the need it describes.
:::

:::{opt} A digest of the definition
:id: OPT_0053_DIGEST
A need records a digest of the text of its definition, and a change to that text fails
the check until the need is looked at again. Good, because no change passes unseen. Bad,
because it fires on every change, most of which change nothing the need says, and a
person learns to pass it without reading.
:::

:::{opt} As now
:id: OPT_0053_AS_NOW
The file exists and the fragment's text occurs in it. Good, because nothing changes.
Bad, because the check goes on passing for a need whose definition is gone.
:::

## Decision Outcome

Chosen option: {need}`OPT_0053_BOTH_WAYS`, because wyatt, 2026-11-15, choosing from
Claude's recommendations with the readings above in the ask: "Address, both ways
(Recommended)".

## Consequences

- Good, because with {need}`DEC_0052` a component has one description, in the source,
  and a link each way between it and its need.
- Good, because the fault is answered by claiming less: the link is an address, and what
  a component does stays with its requirement and that requirement's test.
- Bad, because the check does not yet hold any of this; {need}`REQ_SPEC_RESOLVES` stands
  as written, and {need}`RFC_0010` has to gain a requirement before this binds anything.
- Bad, because the 13 built needs with no `satisfies` link have nothing holding what they
  do, and this does not change that.
- Bad, because what counts as a definition in a workflow file, a JSON file or the README
  is not settled here.
