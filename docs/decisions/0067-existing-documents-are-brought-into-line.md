---
status: accepted
date: 2026-11-15
decision-makers: [wyatt]
informed: [claude]
---
# Existing documents are brought into line

:::{decision}
:chooses: OPT_0067_INTO_LINE
:resolves: Q_EXISTING_DOCUMENTS
:::

## Context and Problem Statement

The requirements of {need}`RFC_0010` were written from rulings made on 2026-11-15, after
most of the corpus. The decision records behind them each say that nothing was applied.
What becomes of the documents already written is open.

Measured on 2026-11-15 at commit `1ec2b54`, what the corpus and the source as they stand
would fail:

| Requirement | What fails it today |
| --- | --- |
| {need}`REQ_NAMES_BEFORE_BUILD` | 15 needs, all in the two design docs not built |
| {need}`REQ_SPEC_EXACT` | 7 fragments found more than once |
| {need}`REQ_SPEC_NAMED_BACK` | 21 needs or more |
| {need}`REQ_DESCRIBED_IN_SOURCE` | 10 of the 34 functions and classes a fragment names have no docstring |
| {need}`REQ_APPROVED_IS_BUILDING` | 2 design docs |
| {need}`REQ_DONE_PLAN_HOLDS_NO_STEPS` | 6 plans, with 135 steps |
| {need}`REQ_SIZE_AND_GAIN` | 9 accepted RFCs and 6 done plans |
| {need}`REQ_README_BLOCKS_RUN` | 5 of 6 blocks of shell commands, and the developing part |
| {need}`REQ_SYNONYMS_IN_SOURCE`, {need}`REQ_DECISION_RESOLVES_QUESTION` | nothing |

How each was read: by the scripts of the decision records that the requirements come
from, run again; steps as checkbox lines in the done plans; blocks as fenced blocks
marked as shell.

Two limits. Comments above a definition and constants were not counted for
{need}`REQ_DESCRIBED_IN_SOURCE`, so its count is rough. And an RFC that is already built
cannot state what it expected to add.

### The ask as put

What was put to wyatt, copied from the transcript of the session. An option marked
"(Recommended)" was the one recommended. The readings shown beside a question in the
same message were those of the table above, save where the outcome says a figure was
wrong; they are not copied again.

First:

```text
Question: Q_EXISTING_DOCUMENTS: what of documents written before these requirements?
Evidence: today's corpus fails 8 of 13: 15 unbuilt needs with prose, 21+ missing back-
references, 7 loose fragments, 2 idle approved designs, 135 steps in 6 done plans, 9
RFCs and 6 plans with no size or gain, 5 unrun README blocks.

Options, in the order shown:
- Bring into line; no past sizes (Recommended): No exemption by date. The plan that
  builds each requirement also changes existing documents to meet it. One exception:
  expected size and gain bind RFCs accepted from now on, since a past expectation cannot
  be stated.
- Bring all into line: As above with no exception: the 9 accepted RFCs and 6 done plans
  get size and gain written in after the fact, as measured values.
- Bind new documents only: Requirements apply to documents created after acceptance;
  older ones stay as written. Check needs a date rule, and the corpus holds two
  standards indefinitely.

Answer: Bring into line; no past sizes (Recommended)
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

- One standard in the corpus, so that a passing check means one thing
- {need}`DEC_0059`: a session writes, so the cost of changing documents is small
- A rule by date is one more rule for the check, and {need}`DEC_0061` asks what it gains
- An expectation cannot be written after the fact

## Considered Options

:::{opt} Brought into line, with no sizes for the past
:id: OPT_0067_INTO_LINE
No document is excused by its date. The plan that builds each requirement also changes
the documents and the source that fail it. One exception: {need}`REQ_SIZE_AND_GAIN`
binds an RFC accepted after this one, and the plans of such an RFC. Good, because the
corpus keeps one standard. Good, because nothing is made up about the past. Bad, because
it is a large change to documents that were reviewed as they are. Bad, because some of
them are frozen, and the requirements that freeze them have to be amended first.
:::

:::{opt} Brought into line, sizes included
:id: OPT_0067_ALL
As above with no exception: the nine RFCs and six plans get a size and a gain written in
as measured. Good, because every RFC then states what it cost. Bad, because a measured
size written in afterwards is not what the requirement asks for.
:::

:::{opt} New documents only
:id: OPT_0067_NEW_ONLY
The requirements bind documents made after this RFC is accepted. Good, because nothing
reviewed is changed. Bad, because the check needs a rule by date and the corpus holds
two standards for good.
:::

## Decision Outcome

Chosen option: {need}`OPT_0067_INTO_LINE`, because wyatt, 2026-11-15, choosing from
Claude's recommendations with the readings above in the ask: "Bring into line; no past
sizes (Recommended)".

## Consequences

- Good, because no requirement of {need}`RFC_0010` carries a date but one.
- Bad, because the plan for this RFC is large before it builds anything: it edits two
  design docs, six plans, the README and at least 21 definitions in the source.
- Bad, because the reviews of every document it changes have to be taken again.
- Bad, because the recorder and the store, the largest part of the tool, are excused
  from stating a size and a gain by the exception, though {need}`DEC_0061` named them
  first. Whether they are kept is still a ruling to come.
