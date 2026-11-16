---
status: accepted
date: 2026-11-15
decision-makers: [wyatt]
informed: [claude]
---
# What a person reads is bounded by its form

:::{decision}
:chooses: OPT_0060_FORM
:resolves: Q_CORPUS_SIZE
:::

## Context and Problem Statement

{need}`RFC_0010` records that the book it reads counts the amount of text against a
design, and that this holds here in part: where a session writes, length no longer
measures how hard a design is to explain, and what is left is a person's time to read.
{need}`DEC_0059` settles that the corpus is written for a session and the tool, and that
what a person has to read is put to them. What bounds that is open.

Measured on 2026-11-15 from the transcript of the session that wrote this record, and
by `wc -w`:

| Reading | Value |
| --- | --- |
| Questions put to wyatt in the session, before this one | 13 |
| Of those, questions that asked for a ruling on this RFC | 11: nine rulings, and two put again |
| Words in a question with its options | 83 to 204, mean 157 |
| Words in the readings put beside a ruling's question | about 100 to 190 |
| Words in the decision record written after each of the nine rulings | 850 to 1,025 |
| Rulings whose question was put again for a wrong or missing reading | 3 of 9 |
| Words in `docs/index.md` | 42, in four tables of contents |

How each was read: the questions and their options from the tool calls in the
transcript; the readings beside each from the text that came before it, which misses
text split around other tool calls, so those figures are rough.

So a ruling was made on about 350 words, and its record ran to about 900. None of the
three questions put again was too long; each gave a figure that was wrong or left one
out. And no derived view says what has been ruled: to learn that, a person opens the
decision records one by one. Two limits: this is one session and one person; and the
question for this record was itself put again, having counted eleven rulings where
there were nine, which makes four of ten.

### The ask as put

What was put to wyatt, copied from the transcript of the session. An option marked
"(Recommended)" was the one recommended. The readings shown beside a question in the
same message were those of the table above, save where the outcome says a figure was
wrong; they are not copied again.

First:

```text
Question: Q_CORPUS_SIZE: what bounds how much a person has to read? Evidence: you ruled
11 times on about 350 words each (question, options, readings); each record ran 850 to
1,025 words; 3 of 11 asks had to be put again for a wrong or missing reading, none for
length; no derived view lists what was ruled.

Options, in the order shown:
- Bound by form: ask stands alone (Recommended): No word cap. An ask is one decision
  with its measured readings, how each was read, its limits, and the options, complete
  enough to rule on without opening the corpus. Plus one derived view listing each
  ruling in a line. Corpus length unbounded.
- Word cap on an ask: As above, and an ask may not exceed N words, N yours to set.
  Mechanical once asks live in a file; nothing measured shows length was the problem.
- Cap asks, not words: Bound how many rulings are put to a person per RFC or per day.
  Limits interruptions; pushes choices into fewer, larger asks.
- No bound: Leave to the session's judgement and your global measure-before-asking
  guide. Nothing written in trifecta.

Answer: Bound by form: ask stands alone (Recommended)
```

Then:

```text
Question: Q_CORPUS_SIZE ask miscounted: 9 rulings not 11, so 3 of 9 rulings (a third)
rested on an ask with a wrong or missing reading, not 3 of 11. Other figures unchanged.
Does "Bound by form: ask stands alone" stand?

Options, in the order shown:
- Yes, it stands: Record the choice with the corrected count and the miscount stated in
  the outcome.
- Hold it open: Record nothing; Q_CORPUS_SIZE stays open.

Answer: Yes, it stands
```

## Decision Drivers

- {need}`DEC_0059`: a person reads what is put to them, so that is where the bound falls
- The failures measured were of content, not of length
- A number of words is a threshold with nothing measured to set it by
- A person who wants to know what was ruled has nowhere short to look

## Considered Options

:::{opt} Bound by form
:id: OPT_0060_FORM
No count of words. What is put to a person for a ruling is one decision, with its
measured readings, how each was read, what the readings do not show, and the options,
whole enough to rule on without opening the corpus. One derived view lists each ruling
in a line. The corpus itself is given no bound. Good, because it answers the failure
that was measured. Good, because a person's reading is then the questions and one page.
Bad, because whether a question is whole is a judgement, and a session is the one
judging its own question. Bad, because a form can be met by a question that is long.
:::

:::{opt} A count of words
:id: OPT_0060_WORDS
As above, with a most a question may run to. Good, because a tool could hold it once
questions are kept in a file. Bad, because no reading shows that length was the trouble.
:::

:::{opt} A count of questions
:id: OPT_0060_COUNT
A person is put no more than a set number of rulings for an RFC, or in a day. Good,
because it limits how often a person is stopped. Bad, because choices are then folded
into fewer and larger questions.
:::

:::{opt} No bound
:id: OPT_0060_NONE
It is left to a session's judgement. Good, because nothing is built. Bad, because the
person's one guard under {need}`DEC_0059` then has no stated form.
:::

## Decision Outcome

Chosen option: {need}`OPT_0060_FORM`, because wyatt, 2026-11-15, choosing from Claude's
recommendations: "Bound by form: ask stands alone (Recommended)". The ask that was put
said he had ruled eleven times and that three of eleven questions were put again; there
were nine rulings, so three of nine. Asked the same day whether the choice stands on the
corrected count, wyatt: "Yes, it stands".

## Consequences

- Good, because with {need}`DEC_0059` a person's part is named: the questions put to
  them and one derived page of rulings.
- Bad, because nothing holds the form. The questions of a session are not in the corpus,
  so the check cannot read them, and {need}`RFC_0010` has no requirement for it.
- Bad, because the derived view of rulings does not exist, and each decision record
  would need a line fit to be listed, which none has.
- Bad, because the corpus is left without any bound, so the cost of its length to a
  session, in what it has to read before it starts, is not weighed here.
- Bad, because four of the ten rulings of this RFC needed their question put again, and
  a stated form does not by itself stop a wrong figure.
