---
status: accepted
date: 2026-11-15
decision-makers: [wyatt]
informed: [claude]
---
# The corpus is written for a session and the tool

:::{decision}
:chooses: OPT_0059_SESSION_AND_TOOL
:resolves: Q_CORPUS_READER
:::

## Context and Problem Statement

{need}`RFC_0010` records that the book it reads writes for people, a team with a
{need}`shared memory <TERM_SHARED_MEMORY>`, and that here there are two readers, a session
and a person, for whom several of the book's faults come out differently. It gives a
document three jobs: to instruct a session, to be the memory a session lacks, and to
record what a person ruled. Who the corpus is written for was left open, and
{need}`Q_CORPUS_SIZE` cannot be answered before it.

Measured on 2026-11-15, at commit `50ff955` with the eight decision records of this RFC
that were not yet committed:

| Reading | Value |
| --- | --- |
| Words in RFCs, decision records, design docs and plans | 21,421, 24,783, 20,427 and 22,793 |
| Words in all, in 85 files | 89,424 |
| Words committed by the end of 2026-11-07, 11-10, 11-13 and 11-15 | 3,043, 46,977, 75,037 and 82,854 |
| The three longest documents | {need}`RFC_0009` 8,201, {need}`DES_0009` 6,577, {need}`PLAN_0007` 5,860 |
| Words an RFC and its design doc hold together | 1,556 to 14,778 |
| Documents a plan names under "Read before starting", and their words | 1 to 5, and 795 to 19,132 |
| Decision records whose outcome quotes wyatt | 27 |

How each was read: words by `wc -w`; the words by day from the tree at the last commit
of each day; the documents a plan names by the ids of RFCs, design docs, decision
records and plans under that heading.

So the corpus grew by about ten thousand words a day for eight days. A plan tells a
session what to read before it starts, up to 19,132 words; nothing tells a person what
to read. In the session that wrote this record, wyatt made eight rulings, each from one
question with a table of readings beside it, and the record of each was written
afterwards. Two limits: what a person did read of the corpus was not measured, only what
was written; and how the nineteen earlier rulings that quote wyatt were put to him was
not looked at.

### The ask as put

What was put to wyatt, copied from the transcript of the session. An option marked
"(Recommended)" was the one recommended. The readings shown beside a question in the
same message were those of the table above, save where the outcome says a figure was
wrong; they are not copied again.

```text
Question: Q_CORPUS_READER (decides Q_CORPUS_SIZE): who is the corpus written for?
Evidence: 89,424 words in 85 files, about 10,000 added a day; plans tell a session to
read up to 19,132 words first; nothing tells a person what to read; your 8 rulings today
were made from asks, not documents.

Options, in the order shown:
- Session and tool; person gets asks (Recommended): Corpus is written for a session to
  act on and a tool to check. A person is not expected to read it through: what a person
  must read is put to them as an ask with evidence, or a derived view. Q_CORPUS_SIZE
  then bounds the ask, not the corpus.
- Both, whole corpus: A person must be able to read all of it. Corpus size then needs a
  hard bound, and most of today's rulings about moving prose are also cuts a person
  needs.
- Person first: Corpus is written for a person; sessions make do. The book's stance.
  Would call for far less text than a session has needed so far.
- Split by document type: RFCs and decision records are for a person; design docs and
  plans are for a session. Bound falls on the first two only (46,204 words today).

Answer: Session and tool; person gets asks (Recommended)
```

## Decision Drivers

- The gap in {need}`RFC_0010`: a session does the writing, and a person's time to read
  is what is scarce
- A session takes each word as written and recalls nothing, so it needs the corpus whole
- A person rules, and a ruling made on a reading has to be able to see the reading
- The rulings measured were made from what was put to the person, not from documents

## Considered Options

:::{opt} A session and the tool, with a person asked
:id: OPT_0059_SESSION_AND_TOOL
The corpus is written for a session to act on and for the tool to check. A person is
not expected to read it through. What a person has to read is put to them: a question
with its evidence, or a derived view. Good, because it is how the rulings measured were
made. Good, because the corpus can be as long as a session needs with no cost to a
person. Bad, because a person then rules on what a session chose to show, and what was
left out does not show. Bad, because nothing yet says what a question to a person has
to hold.
:::

:::{opt} Both, the whole corpus
:id: OPT_0059_BOTH
A person has to be able to read all of it. Good, because nothing is hidden behind a
session's choice of what to show. Bad, because at ten thousand words a day it has
already stopped being true.
:::

:::{opt} A person first
:id: OPT_0059_PERSON
The book's stance: the corpus is written for a person and a session makes do. Good,
because it is short. Bad, because a session has no memory to make do with.
:::

:::{opt} Split by type
:id: OPT_0059_SPLIT
RFCs and decision records are for a person, and design docs and plans for a session.
Good, because a person's part is named and can be bounded. Bad, because that part is
46,204 words today, and a session reads those two types as much as the others.
:::

## Decision Outcome

Chosen option: {need}`OPT_0059_SESSION_AND_TOOL`, because wyatt, 2026-11-15, choosing
from Claude's recommendations with the readings above in the ask: "Session and tool;
person gets asks (Recommended)".

## Consequences

- Good, because {need}`Q_CORPUS_SIZE` grows smaller: what it has to bound is what is put
  to a person, not the corpus.
- Good, because the earlier answers of this RFC that move prose to the source stand on
  their own ground, staleness, and not on sparing a person.
- Bad, because the person's guard against a session is now the question put to them. A
  wrong reading in it leads to a wrong ruling; in the session that wrote this record
  three of the questions put carried a wrong or missing reading and were put again.
- Bad, because the check holds none of this, and what a question to a person has to
  hold is written nowhere in the corpus.
- Bad, because a decision record is still what a later person reads to learn what was
  ruled, so its length still costs someone.
