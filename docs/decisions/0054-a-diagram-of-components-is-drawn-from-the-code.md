---
status: accepted
date: 2026-11-15
decision-makers: [wyatt]
informed: [claude]
---
# A diagram of components is drawn from the code

:::{decision}
:chooses: OPT_0054_CODE_MARKED
:resolves: Q_DIAGRAM_SOURCE
:::

## Context and Problem Statement

{need}`RFC_0010` records that the book it reads values a generated diagram because it
shows the code as it is, and so can show its author something unexpected.
{need}`REQ_DIAGRAMS_DERIVED` has a diagram draw only from the configuration and the built
graph, and the graph is the needs, which are written by hand. Such a diagram shows the
design as declared.

Measured on 2026-11-15 at commit `50ff955`:

| Reading | Value |
| --- | --- |
| Steps of {need}`PLAN_0006` done | 0 of 15 |
| `provides` and `consumes` links on components | 8 and 14 |
| Pairs of components those links join, one consuming an interface the other provides | 15 |
| Of those, pairs whose `spec` paths name two different Python files | 8 |
| Imports of one Python file under `src` by another, of 27 files | 52 |
| Pairs that are both declared and imported | 5 |
| Pairs declared and not imported | 3 |
| Pairs imported and not declared | 47 |
| Of those, pairs where both files are named by a `spec` path | 35 |

How each was read: the links from the options of the `component` directives; an import
by Python's `ast` module over every `import` statement, where a name imported from a
package counts as that module when it is one, and as the package otherwise.

So a diagram drawn from the needs would show eight links between files where the code
has 52, and 47 of the code's are in no need. This is not a fault in the needs: `provides`
and `consumes` say which component offers an interface and which uses it, and were never
a record of imports. It is what a diagram of the needs cannot show. Two limits: an
import is one kind of link in code, and calls, files read and programs run were not
counted; and the three pairs declared and not imported all consume
{need}`IF_NEEDS_JSON`, which is read as a file, so imports miss links that are real.

## Decision Drivers

- The book's reason for a generated diagram, which {need}`RFC_0010` finds to hold here in
  full: a person checking a session's work needs a view of the code as it is
- {need}`DEC_0052` and {need}`DEC_0053`: the source is where a component is described,
  and each `spec` path is an exact address into it
- Nothing of {need}`RFC_0007` is built, so no code is lost by a change
- The size of the tool, which {need}`Q_TOOL_SIZE` leaves open

## Considered Options

:::{opt} From the code, with the needs marked on it
:id: OPT_0054_CODE_MARKED
A diagram of components is drawn from the code, from imports to begin with, and the
links the needs declare are marked against it, so that what is declared and absent, and
what is present and undeclared, both show. Good, because it can show what nobody wrote
down. Good, because one picture holds both and the difference is the finding. Bad,
because {need}`REQ_DIAGRAMS_DERIVED` forbids it as written and has to be superseded. Bad,
because imports are not every link, so the picture is still partial.
:::

:::{opt} Both, kept apart
:id: OPT_0054_BOTH
The two diagrams of {need}`RFC_0007` are built as accepted, and a third is drawn from the
code. Good, because nothing accepted changes. Bad, because it is the most to build, and
nothing sets the declared beside the actual.
:::

:::{opt} From the needs only
:id: OPT_0054_NEEDS
{need}`RFC_0007` stands as accepted. Good, because nothing changes. Bad, because the
diagrams show only what was written down.
:::

:::{opt} No diagrams
:id: OPT_0054_NONE
The diagram work is withdrawn unbuilt. Good, because the tool is smallest. Bad, because a
person has no standing view of the code as it is.
:::

## Decision Outcome

Chosen option: {need}`OPT_0054_CODE_MARKED`, because wyatt, 2026-11-15, choosing from
Claude's recommendations: "Code, needs marked on it (Recommended)". The ask that was put
gave 60 imports, 55 of them undeclared, and two import cycles. A name imported from a
package had been counted twice; the table above measures 52 and 47, and no cycle. Asked
the same day whether the choice stands on the corrected reading, wyatt: "Yes, it stands".

## Consequences

- Good, because the three decisions together give a person one description of a
  component, in its source, an exact address to it, and a picture drawn from it.
- Bad, because {need}`RFC_0007` is accepted and its requirement says otherwise. Nothing
  here changes it; a later RFC has to supersede {need}`REQ_DIAGRAMS_DERIVED` before any
  diagram is built, and {need}`PLAN_0006` cannot be worked as written until then.
- Bad, because what becomes of the meta-model and trace diagrams, which draw the corpus
  and not the components, is not settled here and falls to {need}`Q_UNBUILT_DESIGN`.
- Bad, because a diagram drawn from the code is one more thing for the tool to do, which
  weighs on {need}`Q_TOOL_SIZE`.
- Bad, because which links beyond imports are drawn is left open.
