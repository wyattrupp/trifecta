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
and puts what is left as thirteen questions. A decision record answers each, and the
requirements below state those answers. Writing them raised four further questions,
which four more decision records answer, and its review two more, answered likewise.

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
- Carries over, in part: nobody knows the design before building it. The decisions from
  {need}`DEC_0041` to {need}`DEC_0050` were found during the build of {need}`RFC_0009`
  and added afterwards. A later measurement, in {need}`DEC_0051`, narrows this: the
  components and interfaces named before the code held, and the prose about them is
  what changed.
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
| 1. Design docs and plans before the code | In full for the prose, not for the names | It rests on the design being unknown before it is built. {need}`DEC_0051` measures that the names of components and interfaces held and the prose about them did not. Fell to {need}`Q_BUILD_ORDER`, which it resolves. |
| 7. A component's knowledge is not on it | In full | Prose about code goes stale whoever wrote it, and a session that can describe a component from its source makes the separate description less needed. Fell to {need}`Q_COMPONENT_HOME`, which {need}`DEC_0052` resolves: a built component is described in its source. |
| 8. The link to the source proves little | In full, and most of all | A check that passes while the prose is stale is something wrong that reads as right, which is what the gap is a guard against. Fell to {need}`Q_SPEC_STRENGTH`, which {need}`DEC_0053` resolves: the path is an exact address, named back from the source, and claims nothing of the prose. |
| 10. Diagrams cannot surprise | In full | A person checking a session's work needs a view of the code as it is, not the corpus drawn again. Fell to {need}`Q_DIAGRAM_SOURCE`, which {need}`DEC_0054` resolves: a diagram of components is drawn from the code, with the declared links marked on it. |
| 12. The README holds what changes | In full, and least | Stale prose again; a test already runs one install block. Fell to {need}`Q_README_SCOPE`, which {need}`DEC_0063` resolves: the README holds adoption only, and every block of commands in it is run by a test. |
| 2. An unbuilt feature is specified | In part | An accepted RFC is intent kept out of the shared memory, which the gap calls for. Only the design approved ahead of the build is at fault. Fell to {need}`Q_UNBUILT_DESIGN`, which {need}`DEC_0056` resolves: the RFC may wait, and a design is approved and a plan written only when the build starts. |
| 4. Too many decisions are recorded | In part | The book's three to five assumes a team that recalls its routine choices. The count does not carry over; the amount a person has to read does. Fell to {need}`Q_DECISION_BAR`, which {need}`DEC_0058` resolves: a record exists to resolve an RFC question and for nothing else, which the fifty records already met. |
| 5. The amount of text counts against the design | In part | Where prose is free, its length no longer measures how hard the design is to explain. What is left is the person's reading time. Fell to {need}`Q_CORPUS_SIZE`, which {need}`DEC_0060` resolves: what is put to a person is bounded by its form, and the corpus is given no bound. |
| 6. Plans are kept | In part | The book throws a plan away because people remember what mattered in it. Here the As built entry is that memory and stays; only the list of steps is short-lived. Fell to {need}`Q_PLAN_LIFETIME`, which {need}`DEC_0057` resolves: a done plan keeps its As built and loses its steps. |
| 9. Terms are written by hand | In part | That developers need no glossary beyond the code does not hold for a session, which takes each word as written. What is left: no term is compared with the names in the source. Fell to {need}`Q_TERM_SOURCE`, which {need}`DEC_0055` resolves: terms stay declared in RFCs, and the rule against a declared synonym reaches the source. |
| 11. The tool is large and shipped as a framework | In part | That rules grow from those who work under them does not hold for a session: rules a person sets are the control. It holds for a team that adopts the tool, and the tool's size is a cost either way. Fell to {need}`Q_ADOPTER_RULES`, which {need}`DEC_0062` resolves: the rules ship whole until an adopting repository asks otherwise; and to {need}`Q_TOOL_SIZE`, which {need}`DEC_0061` resolves: no cap, and each part states its size and its measured gain. |
| 3. Writing a document is the default | Not as stated | The book's reason is that talk and memory serve better. The gap rules both out, so writing is the default here by necessity. Only a bound on the amount is left, and fault 5 holds that. |

{need}`Q_CORPUS_READER` belongs to no one fault. The gap answers part of it: there are
two readers, a session and a person, and several of the faults above come out
differently for each. {need}`DEC_0059` resolves it: the corpus is written for a session and
the tool, and what a person has to read is put to them.

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

Each requirement below states one ruling, and names the decision record that holds it.
None is built, and none binds until this RFC is accepted and a design satisfies it.

:::{req} A design names before it describes
:id: REQ_NAMES_BEFORE_BUILD
A component or an interface that has no `spec` path MUST hold nothing beyond its title
and its options.
:::

From {need}`DEC_0051`. The ruling is wider than this: before the code a design doc holds
names and links "and no more". The requirement bounds only what a component or an
interface says of itself; the other sections of a design doc that is not built are
bounded by nothing here.

:::{req} A built component is described in its source
:id: REQ_DESCRIBED_IN_SOURCE
The definition that the `spec` path of a component or an interface names MUST carry a
description of it: in a Python file, a docstring on that definition or a comment directly
above it; in a YAML, TOML or Markdown file, a comment directly above it. A file whose
format holds no comment owes no description.
:::

From {need}`DEC_0052`. That ruling also keeps prose in the need only for how files relate
and why. No requirement states that half: where the line falls is a judgement, and a
requirement here has to be one a fixture or a test can prove.

:::{req} A spec path resolves to one definition
:id: REQ_SPEC_EXACT
A `spec` path that has a fragment MUST resolve to exactly one definition in the file it
names: a function, a class or an assignment in a Python file; a key that occurs once as a
key in a YAML or TOML file; a heading in a Markdown file. A `spec` path into a file whose
format holds no comment MUST have no fragment. A file that a `spec` path names and that
cannot be read in its format MUST be reported.
:::

:::{req} The source names its need back
:id: REQ_SPEC_NAMED_BACK
The definition that a `spec` path resolves to MUST name the id of the need that points at
it: in a Python file in its docstring or in a comment directly above it, and in a YAML,
TOML or Markdown file in a comment directly above it. A file whose format holds no
comment owes no such name.
:::

Both from {need}`DEC_0053`, with {need}`DEC_0065` for the files that are not Python. They
add to {need}`REQ_SPEC_RESOLVES` and do not undo it: a
fragment that resolves to one definition also occurs in the file.

:::{req} A diagram of components is drawn from the source
:id: REQ_DIAGRAM_FROM_SOURCE
A diagram of components MUST be drawn from the Python files the package ships, from the
imports of one by another at the least, and MUST mark on it each link the needs declare, so that a link
declared and absent from the source, a link in the source that no need declares, and a
link in both can be told apart. The files MUST be read without being imported or run,
MUST lie inside the repository, and one that cannot be read as Python MUST be reported.
Text taken from them MUST reach a diagram only as a label, never as markup or as an
attribute, and the directive that draws the diagram MUST take no content, argument or
option.
:::

From {need}`DEC_0054`, with {need}`DEC_0064` for which files are read. This is a third
diagram, beside the two of {need}`RFC_0007`, and {need}`REQ_DIAGRAMS_IN_PROCESS` holds it
as it holds them. The last sentence carries to the source the guard that requirement
gives the text of a need.

:::{req} Declared synonyms stay out of the source
:id: REQ_SYNONYMS_IN_SOURCE
A declared synonym of a defined term MUST NOT appear in a name, a comment or a string of
a Python file the package ships in place of the term. A file that cannot be read as
Python MUST be reported.
:::

From {need}`DEC_0055`, with {need}`DEC_0064` for which files are read.

:::{req} An approved design is one being built
:id: REQ_APPROVED_IS_BUILDING
An approved design doc MUST be implemented by an active plan in which at least one step
is done, or by a done plan. A design doc that such a plan implements MUST be approved,
implemented or obsolete. Against the base ref, an approved design doc MAY return to
draft only if no plan that implemented it at the base ref was done or had a step done
there, and every plan that implemented it there MUST be abandoned in the same change.
:::

From {need}`DEC_0056`. By {need}`DEC_0066` a design doc stays draft while its plan is
written and becomes approved in the change that marks the first step done; the second
sentence above is what holds that, since without it a design could stay in draft, read
by no review, through its whole build. {need}`DEC_0056` has a plan written only when the
build starts, and {need}`DEC_0066`, the later ruling, has it written and reviewed before
the first step; the requirement follows the later one. The return to draft is
{need}`DEC_0056`'s, and once the first sentence holds on the main branch it has nothing
left to apply to: it is there for the designs approved before this requirement. Two
things it leaves unsettled. A draft design with a draft plan is the ordinary state under
{need}`DEC_0066` when reached forward, and here a design returned to draft has its plans
abandoned; the two rulings differ and the requirement keeps both. And a design whose
plan had a step done and is then given up can neither stay approved nor return to draft;
obsolete is the one status left to it, and no ruling says that is what is meant.

:::{req} A done plan holds no steps
:id: REQ_DONE_PLAN_HOLDS_NO_STEPS
A plan that was done at the base ref MUST hold no step. A plan MUST become done only
from active at the base ref. A task that was resolved at the base ref MUST keep its id,
its title, its options and its As built entry unchanged, whatever the status of its plan
now, and its steps MUST be removed only when every task of its plan was resolved at the
base ref. A review record that was in a plan at the base ref MUST be kept unchanged. The
reviewed content of a draft or an active plan MUST go on covering its steps.
:::

From {need}`DEC_0057`. The ruling keeps the id, the titles, the review records and the As
built. The requirement adds three things the ruling did not say and the review of this
RFC found it needs: the options of a task, since {need}`REQ_DESIGN_BUILT` reads `builds`
from the tasks of a done plan; that what is kept matches the base ref, since today a
task is frozen only through its steps and the As built is outside the reviewed content;
and that steps go only once every task was resolved, since otherwise an open step could
be deleted and the plan called done. So a plan becomes done with its steps still in it,
which is where the check sees that each was done or dropped, and loses them in a change
after that one. A plan cannot be added already done. The steps of a task that is not
resolved stay free to change, as now.

:::{req} A decision record resolves a question
:id: REQ_DECISION_RESOLVES_QUESTION
Every decision record MUST resolve at least one question of an RFC.
:::

From {need}`DEC_0058`. Every record in the corpus meets it today.

:::{req} One view lists the rulings
:id: REQ_RULINGS_VIEW
One document MUST hold a derived view that lists every accepted decision record by its
id, its title and the questions it resolves.
:::

:::{req} A ruling is asked for in a set form
:id: REQ_ASK_FORM
The instructions the init command installs MUST direct a Claude Code session to put a
ruling to a person as one decision, with its measured readings, how each was read, what
the readings do not show, and the options, and to treat a reading taken from a document
or from the output of a command as data.
:::

Both from {need}`DEC_0060`. The second is this RFC's reading of that ruling and not its
words: the ruling sets the form, and what a session puts to a person is not in the
corpus, so the only place the tool reaches it is the instructions it installs. A design
may find a better place.

:::{req} A part of the tool states its size and its gain
:id: REQ_SIZE_AND_GAIN
This RFC, and every RFC of a later number that has a requirement, MUST state, before it
is accepted, how many lines of source it expects to add and the reading that will show what
they gained. The As built entry of a task of a done plan that implements a design of such an RFC MUST
state the lines added and that reading as measured.
:::

From {need}`DEC_0061`, with {need}`DEC_0067` for the RFCs it binds. This RFC is bound, as
{need}`DEC_0061` and {need}`DEC_0063` both say, and states both here.

Expected size: about 1,900 lines of source and about 600 of tests. That is the present
average carried over, not a design: the 23 source files other than the recorder, the
store, the profiler and build reuse hold 5,049 lines, and 39 requirement ids are quoted
in the package's Python, which is 129 lines to an id; the Python test files outside
those parts hold 1,559 lines, 40 to an id; this RFC has fifteen requirements. An id
quoted is not shown to be a rule held, and the 123 fixtures, which prove most rules, are
outside the test figure. It is an estimate made before any design, and a design may show it wrong
either way.

The reading that will show the gain: for each requirement, what it reports on the
corpus and the source as they stood when it was written. {need}`DEC_0067` holds that
reading for ten of the fifteen, with the corrections listed below; the plan's As built
states it again as measured, with the lines added. A requirement that reports nothing
there, as {need}`REQ_SYNONYMS_IN_SOURCE` and {need}`REQ_DECISION_RESOLVES_QUESTION` do
today, has shown no gain by this reading and is put to a person under {need}`DEC_0061`. The ruling also has a part whose gain is not shown put to a
person, to keep or to cut. That is a step for a person and not a rule a check can hold,
so it is not in the requirement. One other requirement
here excuses a document by when it was made, {need}`REQ_RECORD_HOLDS_ASK`; for the rest,
by {need}`DEC_0067` the plan that builds each also changes what fails it.

:::{req} The README's commands are run
:id: REQ_README_BLOCKS_RUN
Every block of commands in the README MUST be run by a test, and the README MUST hold no
instructions for developing this repository. A test MAY leave out a command that needs a
published release or a credential, and MAY run on one system only. Each command left out
MUST be held, whole and in its place among the others, by an assertion on the README's
text. The test MUST run with an environment built from a stated list of names and with
a home directory that is empty.
:::

From {need}`DEC_0063`. It adds to {need}`REQ_ADOPTION_GUIDE`.

:::{req} A draft design that a plan implements is reviewed
:id: REQ_DRAFT_DESIGN_REVIEWED
A draft design doc that a draft or an active plan implements MUST record a review whose
digest matches its reviewed content.
:::

From {need}`DEC_0068`, a ruling made on a finding of the review of this RFC.

:::{req} A decision record holds the ask
:id: REQ_RECORD_HOLDS_ASK
A decision record numbered 0051 or later whose decision-makers include a person MUST
hold the question and the options as they were put to that person, the option that was
recommended if one was, and the readings that were put with them.
:::

From {need}`DEC_0069`, likewise. The number is in the requirement because the fifty
records before it cannot meet it: an accepted record on the main branch does not change,
and what was put for them was not kept. That is a second requirement here that excuses
a document by when it was made; {need}`DEC_0067` rules one, and this one is forced by
{need}`REQ_IMMUTABLE_DECISIONS` and has not been put to a person. The nineteen records of
this RFC hold the question and the options as put. They hold the readings only where
those were in the question itself; the readings that stood beside it in a message are
given by reference to the record's table, which holds the corrected figure where one
was wrong. And a question put again after its record is on the main branch has no place
to be recorded, which is not settled here.

Two rulings give no requirement. {need}`DEC_0059`, that the corpus is written for a
session and the tool, is a stance the requirements above rest on, and nothing a check
can hold. {need}`DEC_0062`, that an adopting repository takes the rules whole, builds
nothing.

Eight requirements of accepted RFCs say otherwise than a requirement above, or reach
less far than it needs, and each has to be amended, under a review of its RFC, before
the one above can be met:

| Requirement above | Earlier requirement | Where they part |
| --- | --- | --- |
| {need}`REQ_APPROVED_IS_BUILDING` | {need}`REQ_STATUS_FORWARD` | The earlier one forbids an approved design doc to return to draft. |
| {need}`REQ_APPROVED_IS_BUILDING` | {need}`REQ_DIAGRAMS_DERIVED` | The earlier one has the trace mark a requirement that no component of an approved or implemented design satisfies, the test {need}`REQ_COVERAGE` uses; once that counts a draft the two differ. |
| {need}`REQ_APPROVED_IS_BUILDING` | {need}`REQ_COVERAGE` | The earlier one has a requirement of an accepted RFC satisfied by a component of an approved or implemented design doc, so a design doc in draft covers nothing. |
| {need}`REQ_DRAFT_DESIGN_REVIEWED` | {need}`REQ_REVIEWED`, {need}`REQ_REVIEW_CURRENT` | Not a contradiction: the earlier ones ask a review, and a current one, only of an approved or implemented design doc, and have to reach a draft that a plan implements. |
| {need}`REQ_DONE_PLAN_HOLDS_NO_STEPS` | {need}`REQ_REVIEW_CURRENT` | The reviewed content of a plan covers its steps, so removing them leaves a done plan with no review of its current text, while its records are to stay unchanged. What a done plan's reviewed content is has to be said. |
| {need}`REQ_DONE_PLAN_HOLDS_NO_STEPS` | {need}`REQ_FROZEN_TASKS` | The earlier one holds the steps of a resolved task to the base ref. |
| {need}`REQ_DONE_PLAN_HOLDS_NO_STEPS` | {need}`REQ_TASK_SHAPE` | The earlier one has every task hold at least one step. |
| {need}`REQ_DONE_PLAN_HOLDS_NO_STEPS` | {need}`REQ_AS_BUILT` | The earlier one calls a task resolved when it has steps and none is open, and a done plan has every task resolved. |

{need}`DEC_0012`, which chose how tasks are frozen, and {need}`DEC_0009`, by which a task
is resolved exactly when its steps are, are accepted and stand; whether the amendments
above need a decision to supersede either is not settled here. The decision records of
this RFC speak of superseding the earlier requirements; what is meant is the amendment
of each in place, under a review of its RFC.

What these requirements leave at risk:

- A draft design doc that no plan implements, whether none was written or the one
  written was abandoned, carries no review. Once
  {need}`REQ_COVERAGE` is amended, the requirements of an accepted RFC can be covered by
  it for as long as nothing builds them. {need}`REQ_DRAFT_DESIGN_REVIEWED` closes this
  only from the point a plan is written.
- A ruling is made on what a session puts to a person. {need}`REQ_RECORD_HOLDS_ASK` has
  the record keep what was put, and the session is still the one that writes it down. In
  the making of this RFC five of nineteen rulings were put a second time for a wrong or
  missing reading, and the review of this RFC found wrong figures behind others, listed
  below.
- {need}`DEC_0062` leaves an adopting repository able to assign over a type or a rule in
  its `docs/conf.py` with no finding. The one guard is the code owner's review of that
  file, where a branch ruleset requires it. Every requirement here that lets a draft do
  more rests on the check meaning one thing in each repository.
- The diagram of components shows imports among the Python the package ships. A link
  made by a subprocess, a workflow or a file read is absent from it and reads as no
  link. It is a view and not a control.

Corrections to the decision records, found in the review of this RFC. The records are
left as the rulings were made on them. Asked on 2026-11-15 whether {need}`DEC_0054` and
{need}`DEC_0067` stand on the first two corrections, wyatt: "Both stand".

- {need}`DEC_0054` says {need}`REQ_DIAGRAMS_DERIVED` forbids a diagram drawn from the
  source. It does not: it holds the meta-model and the trace directives, and says
  nothing of a third diagram. Nothing of {need}`RFC_0007` has to change for
  {need}`REQ_DIAGRAM_FROM_SOURCE`; its trace is touched by the amendment of
  {need}`REQ_COVERAGE`, as the table above says.
- {need}`DEC_0067` gives seven fragments as failing {need}`REQ_SPEC_EXACT`. Seven is the
  count of fragments whose text is found more than once. Read as definitions, one
  fails, the workflow step name found twice, or three if a local variable of the same
  name counts.
- {need}`DEC_0054` gives 14 `consumes` links; there are 15, on 14 lines.
- {need}`DEC_0058` gives the median length of the fifty records as 360 words; it is 353.
- {need}`DEC_0052` gives 7,056 words of comments in the source; a second count gives
  between 7,353 and 7,962 by what is taken as a comment.
- {need}`DEC_0053` gives 28 needs whose `spec` file names their id; a plain search gives
  29, and at the definition itself 10 of the 42 in Python do, so more than the 21 it
  states lack one.
- {need}`DEC_0059` counts eight records not yet committed; seven were.
- {need}`DEC_0062` gives 70 requirements in ten RFCs; they are in nine.
- {need}`DEC_0067`'s table of what fails today leaves out {need}`REQ_DIAGRAM_FROM_SOURCE`,
  {need}`REQ_RULINGS_VIEW` and {need}`REQ_ASK_FORM`, which nothing meets yet.

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

Writing the requirements showed four things the rulings did not settle, and the review of
this RFC two more. Each has since been ruled on, and the requirements above say so where
it changes them.

:::{question} What of the documents written before these requirements?
:id: Q_EXISTING_DOCUMENTS
:::

:::{question} What is a definition, and where is its comment, in a file that is not Python?
:id: Q_NON_PYTHON_DEFINITION
:::

:::{question} Which files are the source that the terms and the diagram read?
:id: Q_SOURCE_FILES
:::

:::{question} How does a design doc come to be approved when approval needs a step done?
:id: Q_BUILD_START
:::

:::{question} Is a draft design doc reviewed before a plan is built on it?
:id: Q_DRAFT_REVIEW
:::

:::{question} Is what was put to a person for a ruling kept?
:id: Q_ASK_KEPT
:::

## Out of scope

Whether the book is right; the parts of the book about business domains, conversations
between roles in a team, and documentation produced by a running system, which have no
counterpart here; any change to what the book supports, listed above; the amendments
to the earlier requirements listed under Requirements, each of which belongs to a review
of its own RFC; whether the recorder and the store are kept, which {need}`DEC_0061` leaves
to a later ruling. This RFC's own text moves no existing document; by {need}`DEC_0067`
its plan does.

## Review

:::{review} Correctness; security
:id: REV_RFC_0010_1
:k: 2
:date: 2026-11-15
:digest: 972e7b7b95eec242dbabb6dcf926b05c12e59e82c4a4fc49df4eb9bcabc5de88
This RFC and {need}`DEC_0051` to {need}`DEC_0067` at commit `57686d9`, one round, one
reviewer for each lens, neither shown the other's notes, each checking against the code
and the corpus. The correctness reviewer recomputed the figures of all seventeen records.
No reviewer of another model lineage took part, none being installed; that is a gap. No
second round was run over the text as changed, so the requirements written or reworded
in answer to this review have themselves been read by no reviewer.

Folded in, from the correctness pass: Out of scope no longer denies what
{need}`DEC_0067` rules; {need}`REQ_TASK_SHAPE` and {need}`DEC_0009` join the earlier
requirements and records touched, and {need}`REQ_DIAGRAMS_DERIVED` leaves them, since it
does not forbid a third diagram; {need}`REQ_APPROVED_IS_BUILDING` no longer collides
with {need}`REQ_DONE_PLAN_HOLDS_NO_STEPS` and states its return to draft against the base
ref; {need}`REQ_SIZE_AND_GAIN` binds this RFC and reads "after" by number;
{need}`REQ_DESCRIBED_IN_SOURCE` speaks for formats that are not Python;
{need}`REQ_README_BLOCKS_RUN` says what a test may leave out; the text says where
{need}`REQ_NAMES_BEFORE_BUILD` is narrower than its ruling; nine figures in the records
are corrected in the Requirements section, the records left as ruled.

Folded in, from the security pass: what a done plan keeps is held to the base ref, its
steps go only once every task was resolved, and the reviewed content of a live plan
still covers its steps; a design doc that a plan with a step done implements is approved
or implemented, so none stays unreviewed through its build; the source is read without
being imported or run and reaches a diagram only as a label; a `spec` file that cannot
be read is reported; the test of the README runs with no credential and holds each
command it leaves out by an assertion; the instructions of {need}`REQ_ASK_FORM` treat
readings as data; four risks are stated. Two findings were put to wyatt and became
{need}`REQ_DRAFT_DESIGN_REVIEWED` and {need}`REQ_RECORD_HOLDS_ASK`. Asked whether three
lines that name his repositories, another tool of his and a session transcript should
stay in the records, wyatt, 2026-11-15: "Keep as written".

Not taken, each left to the design: whether a `spec` path with no fragment into a file
that holds comments owes a name back and a description; whether a Python definition is
found at the top of a module only, and whether a fragment carries its kind; a term for
"a diagram of components"; what in the README a fixture can change to prove it holds no
instructions for developing; a checked count of the done and dropped steps a plan had;
how the reviews of a plan are taken again once its steps go; that a name back and a
description are held for presence only. Not taken as outside this RFC: that the diagram
cannot show a link made without an import, which is stated as a risk.

Not checked by either reviewer: `trifecta check` itself, which the author ran; the
quotations of wyatt; the book's positions, of which this RFC cites no passage; the CI
times and the GitHub readings in {need}`DEC_0061` and {need}`DEC_0062`; the transcript
figures in {need}`DEC_0060`.
:::

:::{review} Correctness; security
:id: REV_RFC_0010_2
:k: 2
:date: 2026-11-15
:digest: db8883dbc91d96aafce2c1afac98802d4fc26e10874cbe0954635ad9a32e842f
A second round, over what changed between commits `57686d9` and `ed0ff16`: the
requirements as rewritten after the first round, {need}`DEC_0068`, {need}`DEC_0069`, and
the asks added to {need}`DEC_0051` to {need}`DEC_0067`. One reviewer for each lens,
neither shown the other's notes; again none of another model lineage. Most of what was
found lay in two requirements the first round's answer had rewritten, and both reviewers
found the two worst. This is the last round: what is changed in answer to it, listed
next, has been read by no reviewer.

Folded in, found by both: a design whose plan is done could return to draft, since a
done plan holds no step to show it was built, so the test now reads a done plan as well
as a step done, at the base ref; and the sentences of
{need}`REQ_DONE_PLAN_HOLDS_NO_STEPS` bound every task of every plan, so they now bind a
task resolved at the base ref, a plan becomes done with its steps still in it and loses
them in a later change, and a plan cannot be added already done.

Folded in, from the correctness pass: {need}`REQ_RECORD_HOLDS_ASK` carries in its own
text the number it binds from, and the RFC says this is a second exemption by date and
was not ruled; what the nineteen records hold of their asks is stated as it is;
{need}`REQ_DIAGRAMS_DERIVED` returns to the earlier requirements touched, for its
trace's test of coverage; the inputs of the expected size are named as they are;
{need}`REQ_DESCRIBED_IN_SOURCE` speaks for a format with no comments; the outcomes of
{need}`DEC_0054` and {need}`DEC_0067` state "Both stand".

Folded in, from the security pass: a review record in a plan at the base ref is kept
unchanged, and {need}`REQ_REVIEW_CURRENT` joins the earlier requirements touched for a
done plan; the measured size and gain go in a task's As built entry, which is held; the
README's test holds each command it leaves out whole and in its place, and runs with a
listed environment and an empty home directory; the diagram's directive takes no
content, argument or option, reads only inside the repository, and reports a file it
cannot read, as the rule on synonyms now does too.

Not taken, each left to the design or to a ruling and stated in the Requirements
section where it bears: what becomes of a design whose started build is given up; that
{need}`DEC_0056` and {need}`DEC_0066` differ on a draft design with a draft plan; where a
question put again after a record is on the main branch is recorded; whether the ask in
a record is a fenced block and whether the prose rules read it; how a renamed plan is
matched to its base; what a citation of a dropped step means once the steps are gone;
whether the README's test also shuts off the network.

Not checked by either reviewer: `trifecta check`, which the author ran; the asks against
the transcript they were copied from; the quotations of wyatt.
:::
