---
status: accepted
date: 2026-11-15
decision-makers: [wyatt]
informed: [claude]
---
# Each part of the tool states its size and its gain

:::{decision}
:chooses: OPT_0061_SIZE_AND_GAIN
:resolves: Q_TOOL_SIZE
:::

## Context and Problem Statement

{need}`RFC_0010` records that the book it reads budgets a few hours for a first piece of
documentation tooling, shows one of under 170 lines, and says such tooling serves the
code that is delivered and not the reverse. Here the tool is the product. The fault
holds in part, and nothing says how large the tool may grow.

Measured on 2026-11-15 at commit `50ff955`, the first two rows counted two ways that
agree:

| Reading | Value |
| --- | --- |
| Lines in the 27 Python files under `src` | 10,730 |
| Lines in the 23 Python files under `tests` | 7,789 |
| Lines in the four files that only {need}`DES_0008` and {need}`DES_0009` point into | 5,681 |
| Of those, lines in `record.py` | 4,930 |
| Lines in the test files named for those parts | 6,230 |
| Lines in the other 23 source files | 5,049 |
| Dependencies the package declares, and distributions the lock pins | 5 and 42 |
| The Linux job in CI, as {need}`PLAN_0007` records it before its first task changed anything | 829 s |
| The fixture step on Linux in CI, as that plan records it after tasks 1, 2, 3 and 4 | 788, 806, 2,826 and 3,593 s |
| A local run of the fixtures with stored results, and with none, as {need}`PLAN_0008` records under task 1 | 980 and 2,342 s |
| The last three runs of CI on the main branch, from start to end | 2,706, 2,777 and 2,793 s |

How each was read: lines by a count of line ends, and again by `wc -l` over the files
git tracks; the four files as those every `spec` path into which belongs to one of the
two design docs; the test files by name, those of the recorder, the store, the profile,
build reuse, the CI cache and fast tests; the times from the As built sections of the
two plans and from the start and end times GitHub gives for each run.

So a little over half the source, and four fifths of the tests, is not the check of a
corpus. It is the means of reusing an earlier run soundly, built to make the check
fast. By the plans' own records the time CI takes rose while it was built, from about
fourteen minutes to about forty-six, and the plan that built the store says of the main
branch's store that it saved almost nothing. A local run with stored results does take
less than half the time of one without.

Four limits. A run's time from start to end holds waiting and two jobs, and is set
beside the time of one job. Other tests and the number of fixtures grew over the same
days, so the rise is not all the recorder's. The test files were sorted by their names,
not by what they import. And no time here was taken by the session that wrote this
record; all are read from the plans or from GitHub.

The answers of this RFC so far add to the tool: {need}`DEC_0053` an exact address held
both ways, {need}`DEC_0054` a diagram drawn from the code, {need}`DEC_0055` the rule
against a declared synonym read over the source, {need}`DEC_0060` a derived view of
rulings. None takes anything out of it.

## Decision Drivers

- What is left of the book's fault in {need}`RFC_0010`: tooling serves what is
  delivered, and its size has to be paid for
- {need}`DEC_0059` and {need}`DEC_0060`: a person rules on measured readings put to them
- A number of lines is a threshold with nothing measured to set it by
- The largest part of the tool was built for a gain its own record does not show in CI

## Considered Options

:::{opt} Each part states its size and its measured gain
:id: OPT_0061_SIZE_AND_GAIN
No count of lines is capped. An RFC that adds code says, when it is put for acceptance,
how many lines it expects and what reading will show the code paid for itself; the As
built of its plan gives both as measured. A part whose gain is not shown is put to a
person, to keep or to cut. Good, because size becomes something a person rules on with a
reading beside it, and not something that happens. Good, because it asks of new code
what the measurement here asks of old. Bad, because it bounds nothing by itself: a part
that states a size and a gain is let in. Bad, because not every gain is a number; what a
rule prevents is hard to measure.
:::

:::{opt} Split reuse out of the tool
:id: OPT_0061_SPLIT
The tool is the check and nothing else, and the recorder, the store and their tests
become a package of their own that it may depend on. Good, because the tool is halved
and each half says what it is. Bad, because no code goes, and there is a second thing to
release and to adopt.
:::

:::{opt} A cap on lines
:id: OPT_0061_CAP
The source holds no more than a set number of lines, and an addition past it takes
something out. Good, because a tool can hold it. Bad, because the number is arbitrary.
:::

:::{opt} No bound
:id: OPT_0061_NONE
The size follows the requirements accepted. Good, because nothing is built. Bad, because
it is how the tool came to its present size.
:::

## Decision Outcome

Chosen option: {need}`OPT_0061_SIZE_AND_GAIN`, because wyatt, 2026-11-15, choosing from
Claude's recommendations with the readings above in the ask: "Each part states size and
measured gain (Recommended)".

## Consequences

- Good, because the four additions this RFC has already answered for each have to state
  a size and a gain before they are built.
- Bad, because nothing has been put to a person yet: whether the recorder and the store
  are kept is not decided here, and they stand as built.
- Bad, because the check does not hold the rule; an RFC has no place for an expected
  size or a gain, and {need}`RFC_0010` has to gain a requirement before this binds.
- Bad, because the gain of the parts that only check, such as a rule that a link
  resolves, was not measured here and may not be measurable.
- Bad, because the times this rests on were read from records and not taken again.
