---
status: draft
authors: [claude]
created: 2026-11-15
---
# A critique from the Living Documentation book

:::{rfc}
:::

## Summary

Cyrille Martraire's book "Living Documentation" was read in full against this repository.
It supports what the check does: rules held by a tool, one home per fact, and a decision
log that is never edited. It faults how the corpus is produced: design docs and plans
are written before the code they describe, far more is written down than the book thinks
worth keeping, and the knowledge about a component sits beside the source and not on it.
The book was written for teams of people, so this RFC also sorts its reasons into those
that hold when a coding session does the writing and those that do not, and states the
gap between the book's framing and this repository's: the book passes knowledge among
people who trust what they remember, and this repository keeps control and continuity
where what is remembered cannot be trusted. It records the twelve faults, says how far
each holds across that gap, records what the book supports so that no answer undoes it,
and puts what is left as questions. It proposes no requirement.

## Motivation

This RFC comes from a reading of Cyrille Martraire's book "Living Documentation", made on
2026-11-15 to find what the book would say of this repository. The book's subject is this
repository's subject: how documentation stays true as the software changes. It was read
whole, for what supports the repository as much as for what faults it. What follows gives
the book's positions in this document's own words and cites no passage; the references
are left out for now.

What was measured in this repository, at commit `f8818bf` on 2026-11-15:

| Reading | Value | Command |
| --- | --- | --- |
| Words under `docs/rfcs`, `docs/decisions`, `docs/design`, `docs/plans` | 78,475 | `wc -w` over each directory's `*.md` |
| Lines of `src/trifecta/*.py` and `src/trifecta/ext/*.py` | 10,598 | `wc -l` |
| Lines of `tests/*.py` | 7,789 | `wc -l` |
| Decision records | 50 | `ls docs/decisions` |
| First and last commit dates | 2026-11-07, 2026-11-14 | `git log --format=%ad --date=short` |

What the book supports:

- A decision log of structured text files beside the code, giving each decision's
  reasons and the options weighed, where an entry is never changed and a new entry
  supersedes it. This is {need}`REQ_DECISION_OPTIONS`, {need}`REQ_IMMUTABLE_DECISIONS`
  and {need}`REQ_SUPERSESSION`.
- A record outside the code for the options that were turned down, since the code cannot
  hold them.
- Rules held by a tool that reports a breach when it happens, so the tool is the
  reference for the rule; a rule nothing can enforce is hardly a rule. This is
  {need}`REQ_FIXTURE_PER_INVARIANT` and the one enforcing component per requirement.
- One home for each piece of knowledge, with every other form produced from it. This is
  {need}`REQ_STATUS_SINGLE_SOURCE` and {need}`REQ_GENERATED_VIEWS`.
- A way to detect a link that broke, wherever a document points straight at a file. This
  is {need}`REQ_LINK_TARGETS` and {need}`REQ_SPEC_RESOLVES`.
- Stating what is wanted before building it, and proving it by a test. This covers a
  requirement and its negative fixture; it does not cover a design doc or a plan.
- Writing down the purpose of a piece of work early, so that it can be reviewed before
  anything is built, and writing down a decision and its reasons when it is made. This
  covers an RFC and a decision record written before the code.
- A written record for knowledge that has to outlast the people who held it. A coding
  session that starts with no memory of the last one is such a reader.
- Writing something down at once when doing so is cheap. A session that drafts a
  decision record in seconds lowers the cost of writing; the cost of reading and
  reviewing stays.

What the book faults:

1. Design docs and plans come before the code. The book names writing documentation
   before building as an abuse of its own method and calls detailed design
   specifications waste. It holds that documentation follows what was built and does
   not drive it, and that designing the whole before implementing any of it no longer
   fits. The fault is with a description of the solution written ahead of the solution;
   a statement of what is wanted, and a decision recorded when it is made, are among
   what the book supports, above. Here {need}`DEC_0008` makes a design doc part of a
   spec, a plan follows it, and {need}`DEC_0014` makes that order the default for a
   session.
2. A feature nobody built is fully specified. The book says to document only what has
   been built, in answer to a need that was met. {need}`RFC_0007` is accepted and
   {need}`DES_0007` approved, and {need}`PLAN_0006` has no step ticked.
3. Writing a document is the default. The book says a written document is never the
   default, and that only the part of what is known that proved useful again and again
   earns a lasting form. Here every change starts as documents.
4. Too many decisions are recorded. The log the book asks for holds the most important
   decisions, three to five to begin with; a choice that follows a principle already
   written down needs no record of its own; and a good architecture is a few decisions
   that guide the rest. This corpus holds fifty records after eight days, one for each
   choice.
5. The amount of text counts against the design. The book reads many pages spent
   explaining a design as a sign that the design is poor, and names documentation
   becoming unnecessary as the aim. The table above shows the proportion here.
6. Plans are kept. The book treats everything about planning and tracking as short-lived
   and says to throw it away once the work is done, and that the record of a temporary
   process goes when the process does. A done plan stays in the corpus and
   {need}`DEC_0012` freezes its resolved tasks.
7. What is known about a component is not on the component. The book prefers
   {need}`internal documentation <TERM_INTERNAL_DOCUMENTATION>` to
   {need}`external documentation <TERM_EXTERNAL_DOCUMENTATION>`, and ranks a separate
   file of facts about the code last among the ways to add knowledge to it. A design doc
   is such a file. The book makes one allowance that fits: a fact about how files
   relate, and not about one file, belongs outside them.
8. The link from a design doc to the source proves little. The book ranks
   {need}`reconciliation <TERM_RECONCILIATION>` fourth of its four ways to keep
   documentation true, warns against naming a file directly, and shows a check that
   still passes after the behaviour changed as the kind that fails its purpose.
   {need}`REQ_SPEC_RESOLVES` holds that a path exists and that a fragment occurs in it;
   the prose beside the path can go stale and the check passes.
9. Terms are written by hand. The book's glossary is drawn from the names in the source,
   which it treats as the one home of the vocabulary, and it says developers need no
   glossary beyond the code. {need}`REQ_CANONICAL_TERMS` holds prose to terms declared
   in RFCs; nothing compares those terms with the names in `src/`.
10. The diagrams as designed cannot surprise. The book values a generated diagram
    because it shows the code as it is and so can show the author something unexpected.
    {need}`RFC_0007` draws from the needs, which are written by hand, so its diagrams
    show the design as declared.
11. The tool is large, and it is shipped as a framework. The book budgets a few hours
    for a first piece of documentation tooling, gives a worked example of under 170
    lines, and says such tooling serves the code that is delivered and not the reverse.
    Its author gave up on a framework to suit every project and recommends small
    solutions made for one, and says the best rules grow from the people who work under
    them. Here the tool is the product, and `trifecta init` hands its types, its rules
    and its hook to another repository whole.
12. The README holds what changes. The book warns against instructions for developing,
    using and testing in a README, because they change often. Most of this repository's
    README is such instructions. Two things answer the warning in part: the README names
    no version, and a test runs one of its install blocks.

Where the book's reasons do not carry over. wyatt, 2026-11-15, of the first fault: "we
need to come up with how the 'writing documentation first is wrong' angle for us, because
this isn't necessarily for agentic written software", and, asked what "this" was: "this =
the book". The book gives its reasons for teams of people who write the code themselves.
Sorted by whether each still holds when a coding session writes both the documents and
the code:

- Does not carry over: writing is the cost. The book counts time spent on a document as
  time taken from the code. A session writes either in seconds; the scarce thing is the
  time a person has to read and review.
- Does not carry over: talk takes the place of documents. The book's default is people
  who talk every day and hold the design in their heads. What a session carries over
  from the one before it, and what a person recalls of either, can be wrong without
  anyone noticing, so nothing here rests on it; the gap is stated below.
- Does not carry over: whoever codes knows what is wanted. The book's advice to start
  coding and reflect along the way assumes it. Here a person holds the intent and a
  session writes the code, so the intent has to be written down before the code is.
- Carries over: nobody knows the design before building it. {need}`RFC_0009` and the
  decisions from {need}`DEC_0041` to {need}`DEC_0050` are design found during the build
  and added afterwards.
- Carries over: prose that describes code goes stale, whoever wrote it.
- Not foreseen by the book: prose is free. The effort of writing was what kept a team
  from writing too much. With that gone, only a rule bounds the amount.
- Not foreseen by the book: a required shape is always filled. A session asked for two
  options weighed supplies two, whether or not both were weighed.
- Not foreseen by the book: code is cheap as well. A working trial costs minutes, which
  leaves less reason to settle a design on paper first.

The gap between the book's framing and this repository's. The book is about passing
knowledge among people who share a memory and can trust it. This repository is about
control and continuity where the {need}`shared memory <TERM_SHARED_MEMORY>` cannot be
trusted. wyatt, 2026-11-15, asked whether the gap is control and continuity without
shared memory: "yeah, I would say so. but the lack of shared memory is not really the
point. it's the fallibility of the shared memory that we have to guard against, thus have
to essentially pretend it doesn't exist." A session does carry things over: a summary of
its own past, notes kept between sessions, what the person tells it. A person remembers
too. Any of these can be wrong and read as right, so the repository is built as if none
of them were there: what counts is written in the corpus and held by the check.

| | The book assumes | Here |
| --- | --- | --- |
| Who holds the design | The team, in their heads, and they can be asked | A person holds the intent and did not write the code; the session that wrote it cannot be asked |
| What is remembered | Trusted; a document is a fallback | Fallible, so treated as absent; the corpus is what is known |
| Losing whoever knew | An accident to guard against | The ordinary case, at the end of every session |
| What is scarce | The time and the will to write | A person's time to read and to verify |
| Which way knowledge flows | From the code, through a document, to people | From a person, through a document, to a session and its code, and back to the person to be checked |
| Who reads | People, who skim | A session, which reads all of it and takes it at its word, and a person, who reads as little as will do |
| Trust | The team trusts itself; a call for detail is a sign of trouble | Trust in a session is partial and that is correct; the documents and the check are the control |
| Why writing helps | It makes the writer think | The writer is a session; the gain to the person is something to rule on |

Where the book does treat this situation. It treats it as two cases apart from its main
line, and this repository is both at once and all the time. One is legacy code: nobody
who knows the reasons is left, and what is known has to be rebuilt from what was
written. The other is compliance: a strict procedure, decision-makers who are named, and
a record of what led to what, held by tools and not by diligence. So the book's answers
for those two cases bear on this repository more than its advice to a team that talks:
rules held by a tool, a decision log, and views that are generated.

What a document is for here. The book gives a document one job, to carry knowledge to a
reader later. Here it has three, and the book does not tell them apart:

- Instruction: what a person wants, given to a session that cannot be relied on to ask
  or to recall.
- Memory: what one session leaves for the next, in place of anything it might carry
  over.
- Record of authority: what a person ruled, in their words, kept apart from what a
  session chose. {need}`DEC_0041` already does this, where its outcome quotes the
  ruling and names the recommendations it was chosen from.

Two things follow, and neither is settled here.

- A session makes the book's case against design docs stronger. The book's ground is
  that most of what is known is already in the code and is better drawn out of it than
  written beside it. A session can read the code and describe any component when asked.
  What then has to be written down and kept is what cannot be drawn out of the code
  again: the intent, the rulings, the options turned down, and the evidence.
- The third job suggests one bar for the decision log: a record where a person ruled,
  and none where a session chose alone. wyatt, 2026-11-15, of that bar: "that feels way
  too narrow". The bar is left to {need}`Q_DECISION_BAR`, with that one set aside.

How far each fault holds across the gap. The twelve faults above are stated as the book
makes them. The test applied to each here: does its reason still stand once the shared
memory is treated as absent and a session does the writing? The answers are the
author's judgement, not a measurement, and the numbers are those of the list above.

| Fault | Holds | What is left of it |
| --- | --- | --- |
| 1. Design docs and plans before the code | In full | It rests on the design being unknown before it is built, which carries over. Falls to {need}`Q_BUILD_ORDER`. |
| 7. A component's knowledge is not on it | In full | Prose about code goes stale whoever wrote it, and a session that can describe a component from its source makes the separate description less needed. Falls to {need}`Q_COMPONENT_HOME`. |
| 8. The link to the source proves little | In full, and most of all | A check that passes while the prose is stale is something wrong that reads as right, which is what the gap is a guard against. Falls to {need}`Q_SPEC_STRENGTH`. |
| 10. Diagrams cannot surprise | In full | A person checking a session's work needs a view of the code as it is, not the corpus drawn again. Falls to {need}`Q_DIAGRAM_SOURCE`. |
| 12. The README holds what changes | In full, and least | Stale prose again; a test already runs one install block. Falls to {need}`Q_README_SCOPE`. |
| 2. An unbuilt feature is specified | In part | An accepted RFC is intent kept out of the shared memory, which the gap calls for. Only the design approved ahead of the build is at fault. Falls to {need}`Q_UNBUILT_DESIGN`. |
| 4. Too many decisions are recorded | In part | The book's three to five assumes a team that recalls its routine choices. The count does not carry over; the amount a person has to read does. Falls to {need}`Q_DECISION_BAR`. |
| 5. The amount of text counts against the design | In part | Where prose is free, its length no longer measures how hard the design is to explain. What is left is the person's reading time. Falls to {need}`Q_CORPUS_SIZE`. |
| 6. Plans are kept | In part | The book throws a plan away because people remember what mattered in it. Here the As built entry is that memory and stays; only the list of steps is short-lived. Falls to {need}`Q_PLAN_LIFETIME`. |
| 9. Terms are written by hand | In part | That developers need no glossary beyond the code does not hold for a session, which takes each word as written. What is left: no term is compared with the names in the source. Falls to {need}`Q_TERM_SOURCE`. |
| 11. The tool is large and shipped as a framework | In part | That rules grow from those who work under them does not hold for a session: rules a person sets are the control. It holds for a team that adopts the tool, and the tool's size is a cost either way. Falls to {need}`Q_ADOPTER_RULES` and {need}`Q_TOOL_SIZE`. |
| 3. Writing a document is the default | Not as stated | The book's reason is that talk and memory serve better. The gap rules both out, so writing is the default here by necessity. Only a bound on the amount is left, and fault 5 holds that. |

{need}`Q_CORPUS_READER` belongs to no one fault. The gap answers part of it: there are
two readers, a session and a person, and several of the faults above come out
differently for each.

## Terms

:::{term} Internal documentation
:id: TERM_INTERNAL_DOCUMENTATION
Knowledge about an artifact that is held in that artifact, in the technology it is built
with, so that it moves, changes and is deleted with it.
:::

:::{term} External documentation
:id: TERM_EXTERNAL_DOCUMENTATION
Knowledge about an artifact that is held in another file, which a change to the artifact
does not touch.
:::

:::{term} Reconciliation
:id: TERM_RECONCILIATION
A check that two statements of the same knowledge still agree, run because either can
change without the other.
:::

:::{term} Shared memory
:id: TERM_SHARED_MEMORY
What the people and the sessions working on a repository carry of it outside the
repository: what a person recalls, what a session holds from earlier in its run or was
handed from a past one, a transcript, a note. It can be wrong and read as right.
:::

## Requirements

## Questions

:::{question} Who is the corpus written for?
:id: Q_CORPUS_READER
:::

:::{question} Which documents come before the code they describe?
:id: Q_BUILD_ORDER
:::

:::{question} What becomes of an accepted RFC and an approved design that nothing builds?
:id: Q_UNBUILT_DESIGN
:::

:::{question} Which choices get a decision record?
:id: Q_DECISION_BAR
:::

:::{question} What bounds how much a person has to read?
:id: Q_CORPUS_SIZE
:::

:::{question} What bounds the size of the tool?
:id: Q_TOOL_SIZE
:::

:::{question} How long does a done plan stay in the corpus?
:id: Q_PLAN_LIFETIME
:::

:::{question} Where is a component described, in a design doc or in its source?
:id: Q_COMPONENT_HOME
:::

:::{question} What does a spec path prove about the prose beside it?
:id: Q_SPEC_STRENGTH
:::

:::{question} Are terms compared with the names in the source?
:id: Q_TERM_SOURCE
:::

:::{question} Are diagrams drawn from the needs or from the code?
:id: Q_DIAGRAM_SOURCE
:::

:::{question} Which rules can an adopting repository change or leave out?
:id: Q_ADOPTER_RULES
:::

:::{question} What does the README hold?
:id: Q_README_SCOPE
:::

## Out of scope

Whether the book is right; the parts of the book about business domains, conversations
between roles in a team, and documentation produced by a running system, which have no
counterpart here; any change to what the book supports, listed above; a requirement,
until the questions are answered.

## Review
