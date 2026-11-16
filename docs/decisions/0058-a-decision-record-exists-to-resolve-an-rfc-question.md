---
status: accepted
date: 2026-11-15
decision-makers: [wyatt]
informed: [claude]
---
# A decision record exists to resolve an RFC question

:::{decision}
:chooses: OPT_0058_PER_QUESTION
:resolves: Q_DECISION_BAR
:::

## Context and Problem Statement

{need}`RFC_0010` records that the book it reads keeps a log of its most important
decisions, three to five to begin with, and that this holds here in part: the book's
count rests on a team that recalls its routine choices, which does not carry over, and
what is left is how much a person has to read. {need}`RFC_0010` also records one bar
that wyatt set aside as too narrow: a record only where a person ruled.

Measured on 2026-11-15 at commit `50ff955`, over the fifty decision records that stood
before this RFC and the nine RFCs they belong to:

| Reading | Value |
| --- | --- |
| Records that resolve a question raised in an RFC | 50 of 50 |
| Questions in the nine RFCs | 39, all resolved |
| Questions with more than one record | 4, with 2, 3, 4 and 6 records |
| Records per RFC | 2 to 7 for eight RFCs, and 19 for {need}`RFC_0009` |
| Records cited by another file | 50 of 50 |
| Of those, cited by one file only | 13 |
| Records that constrain a component | 49 |
| Records cited from the source or the tests | 21 |
| Records whose decision-makers are wyatt, and claude alone | 36 and 14 |
| Records superseded | 1 |
| Words in the fifty, and the median | 17,487 and 360 |

How each was read: a record's `resolves` link against the question needs of the RFCs; a
citation as the record's id found in another file under `docs`, `src` or `tests`, or in
the README; `constrained_by` links on components; the front matter of each record.

So a bar already stands, and a tool holds one side of it: {need}`REQ_RFC_ACCEPTANCE` has
every question of an accepted RFC resolved by an accepted decision, and no record exists
that does not resolve one. The count of fifty comes from nine RFCs in eight days and
from four questions that took more than one record, not from records written for choices
nobody asked about. Of the four, one holds a record and the record that superseded it;
the other three, all in {need}`RFC_0009`, hold several choices under one question, and
{need}`Q_PROGRAMS` holds six.

Two limits. A citation shows a link, not that the record was needed; how many of the
fifty a person would not miss was not measured. And the first ask that was put gave the
records as 5.6 to an RFC and did not give the 39 questions or the four that hold more
than one record.

### The ask as put

What was put to wyatt, copied from the transcript of the session. An option marked
"(Recommended)" was the one recommended. The readings shown beside a question in the
same message were those of the table above, save where the outcome says a figure was
wrong; they are not copied again.

First:

```text
Question: Q_DECISION_BAR: which choices get a decision record? Evidence: all 50 earlier
records resolve a question an RFC raised, none exists otherwise; 5.6 per RFC; all 50
cited, 49 constrain a component; median 360 words; 14 decided by a session alone.

Options, in the order shown:
- A record per RFC question, no other (Recommended): State the bar that is already
  measured: a choice gets a record when, and only when, an RFC raised it as a question.
  No count cap. How much there is to read falls to Q_CORPUS_SIZE.
- Raise the bar on questions: A choice is raised as a question only if it binds more
  than one component or is costly to undo; lesser choices are settled in the RFC's own
  prose. Fewer records; the line is judgement no check makes.
- Cap questions per RFC: An RFC may raise at most N questions, N yours to set.
  Mechanical; forces splitting or folding. RFC_0005 has 6 and RFC_0009 more today.
- Hold it open: Record nothing; evidence does not show the fault, so leave
  Q_DECISION_BAR open until it bites.

Answer: A record per RFC question, no other (Recommended)
```

Then:

```text
Question: Your Q_DECISION_BAR choice lacked this: 39 questions have 50 records. Four
questions carry 2 to 6 records each (11 extra, 10 in RFC_0009; Q_PROGRAMS has 6). Does
"a record per RFC question, no other" stand, and what of several records on one
question?

Options, in the order shown:
- Stands; several allowed: Bar is: a record exists only to resolve an RFC question. A
  question may take more than one record when it holds more than one choice. Matches the
  corpus as it is; 11 extra records stand.
- Stands; one per question: Bar is exactly one accepted record per question. A question
  needing a second choice is split into two questions first. Existing 11 extras are
  immutable and stay; rule binds from now.
- Hold it open: Record nothing; Q_DECISION_BAR stays open.

Answer: Stands; several allowed
```

## Decision Drivers

- What is left of the book's fault in {need}`RFC_0010`: a person's reading time, not
  the count
- A record is where a session finds a choice it cannot recall and a person finds what
  was ruled
- A bar a tool can hold is worth more than one that rests on judgement
- wyatt, 2026-11-15, of a record only where a person ruled: "that feels way too narrow"

## Considered Options

:::{opt} A record for an RFC question, and for nothing else
:id: OPT_0058_PER_QUESTION
A choice gets a decision record when, and only when, an RFC raised it as a question. A
question may take more than one record where it holds more than one choice. No count is
capped. Good, because it is the bar the corpus already keeps, and one side of it is
held by a check. Good, because the place to ask whether a choice deserves a record is
where the question is raised. Bad, because it bounds nothing: an RFC may raise any
number of questions and a question may take any number of records. Bad, because no check
holds the other side, that a record resolves a question.
:::

:::{opt} One record to a question
:id: OPT_0058_ONE_EACH
As above, with exactly one accepted record to a question; a question that needs a
second choice is split first. Good, because a question and its answer are one to one.
Bad, because eleven records already stand beyond the first on their questions and
cannot change.
:::

:::{opt} A higher bar for a question
:id: OPT_0058_HIGHER
A choice is raised as a question only if it binds more than one component or is costly
to undo, and a lesser choice is settled in the prose of the RFC. Good, because there are
fewer records. Bad, because where the line falls is a judgement no check makes, and a
choice settled in prose is one a session may not find.
:::

:::{opt} A cap on the questions of an RFC
:id: OPT_0058_CAP
An RFC raises no more than a set number of questions. Good, because a tool can hold it.
Bad, because the number is arbitrary, and a cap is met by folding choices together,
which is what {need}`Q_PROGRAMS` shows.
:::

## Decision Outcome

Chosen option: {need}`OPT_0058_PER_QUESTION`, because wyatt, 2026-11-15, choosing from
Claude's recommendations: "A record per RFC question, no other (Recommended)". The ask
that was put did not say that 39 questions hold the fifty records and that four of them
hold more than one. Asked the same day with those readings whether the choice stands
and what of several records on one question, wyatt: "Stands; several allowed".

## Consequences

- Good, because nothing in the corpus has to change: the fifty records, and those of
  this RFC, all meet the bar.
- Bad, because the fault is answered by finding it mostly absent, and the part that is
  left, how much there is to read, is passed whole to {need}`Q_CORPUS_SIZE`.
- Bad, because no check yet reports a decision record that resolves no question;
  {need}`RFC_0010` has to gain a requirement before that side binds.
- Bad, because seventeen of the thirty-six records that name wyatt as decision-maker do
  not quote him, and fourteen were decided by a session alone. This bar says nothing of
  who may decide.
