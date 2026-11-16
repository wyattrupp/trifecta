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

### The ask as put

What was put to wyatt, copied from the transcript of the session. An option marked
"(Recommended)" was the one recommended. The readings shown beside a question in the
same message were those of the table above, save where the outcome says a figure was
wrong; they are not copied again.

First:

```text
Question: Q_DIAGRAM_SOURCE: what are diagrams drawn from? Evidence: corpus declares 8
file-level edges between components; code has 60 import edges; 5 overlap; 55 imports
appear nowhere in the corpus, two cycles among them. RFC_0007 (needs-drawn) is accepted,
0 of 15 plan steps built.

Options, in the order shown:
- Code, needs marked on it (Recommended): Diagram of components is drawn from the code
  (imports to start), with declared links marked against it, so the difference shows.
  RFC_0007's needs-only rule would need superseding; its trace and meta-model diagrams
  fall to Q_UNBUILT_DESIGN.
- Both, kept apart: Keep RFC_0007's two corpus diagrams as accepted and add a separate
  code-drawn one. Most to build; nothing puts the two side by side.
- Needs only, as accepted: RFC_0007 stands. Diagrams show the design as declared; the
  fault is accepted as the cost.
- No diagrams: Withdraw the unbuilt diagram work. Smallest tool; a session can draw the
  code on request. Leaves a person with no standing view of the code as it is.

Answer: Code, needs marked on it (Recommended)
```

Then:

```text
Question: Your Q_DIAGRAM_SOURCE choice rested on figures I miscounted: import edges are
52 not 60, undeclared imports 47 not 55, and there are no import cycles (I said two).
Does "Code, needs marked on it" stand on the corrected reading?

Options, in the order shown:
- Yes, it stands: Record the choice with the corrected figures and the miscount stated
  in the outcome.
- Needs only, as accepted: RFC_0007 stands; diagrams show the design as declared.
- No diagrams: Withdraw the unbuilt diagram work.
- Hold it open: Record nothing; Q_DIAGRAM_SOURCE stays open.

Answer: Yes, it stands
```

Then:

```text
Question: DEC_0054 and DEC_0067 rested on readings the review found wrong: no conflict
exists between a code-drawn diagram and RFC_0007's rule (I said one did), and 1 fragment
fails REQ_SPEC_EXACT, not 7. Both corrections make the chosen options cheaper. Do both
rulings stand?

Options, in the order shown:
- Both stand: Records stay as ruled; the RFC carries the corrections, as it now does.
- Put DEC_0054 again: Reopen the diagram source question with the corrected reading.
- Put both again: Reopen both questions with corrected readings.

Answer: Both stand
```

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
