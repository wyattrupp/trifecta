---
status: accepted
date: 2026-11-15
decision-makers: [wyatt]
informed: [claude]
---
# A decision record holds the ask as put

:::{decision}
:chooses: OPT_0069_HOLDS_ASK
:resolves: Q_ASK_KEPT
:::

## Context and Problem Statement

By {need}`DEC_0059` a person rules on what a session puts to them, and by
{need}`DEC_0060` what is put has a set form. The review of {need}`RFC_0010`, security
lens, found that what was put is kept nowhere: a record quotes the label of the option
chosen, which the session also wrote, so a ruling cannot be read against what the person
was shown.

Read on 2026-11-15 at commit `57686d9`: each of the seventeen decision records of
{need}`RFC_0010` quotes an option label in its outcome, and none holds the question, the
readings or the options as they were put. The correctness lens of the same review
recomputed the records' figures and found nine that did not hold; {need}`RFC_0010` lists
them.

### The ask as put

Question: "No decision record holds the question, readings and options as they were put
to you; all 17 quote only an option label, and the review found 9 wrong figures in the
records. Should a record that quotes a ruling have to hold the ask as put?"

Options, the first marked as recommended:

- "Yes, record holds the ask (Recommended)": "Add a requirement: a decision record that
  quotes a person's ruling holds the question, the readings and the options as put, and
  which was recommended. Lets a ruling be read against what was shown. Records get
  longer."
- "No, state it as a risk": "Leave as is; the RFC already lists it under what the
  requirements leave at risk."
- "Hold it open": "Add it as a question for a later ruling."

## Decision Drivers

- {need}`DEC_0059`: the question put to a person is their guard against a session
- A guard that leaves no trace cannot be checked afterwards
- Five of the rulings of {need}`RFC_0010` were put a second time for a wrong or missing
  reading

## Considered Options

:::{opt} The record holds the ask
:id: OPT_0069_HOLDS_ASK
A decision record that quotes a person's ruling holds the question, the readings and
the options as they were put, and which option was recommended. Good, because a ruling
can be read against what was shown. Bad, because records grow, and the session still
writes down its own question.
:::

:::{opt} Stated as a risk
:id: OPT_0069_RISK
Records stay as they are and the RFC says so. Good, because nothing is added. Bad,
because the person's one guard leaves no trace.
:::

:::{opt} Held open
:id: OPT_0069_OPEN
The question waits. Good, because nothing is decided in haste. Bad, because the RFC
cannot be accepted with it open.
:::

## Decision Outcome

Chosen option: {need}`OPT_0069_HOLDS_ASK`, because wyatt, 2026-11-15, choosing from
Claude's recommendations: "Yes, record holds the ask (Recommended)".

## Consequences

- Good, because this record and {need}`DEC_0068` hold their asks, as the first two to.
- Good, because the seventeen records before them were brought into line, as
  {need}`DEC_0067` has it, before any reached the main branch: each now holds its ask,
  copied from the transcript of the session.
- Bad, because the fifty records before those hold none, cannot now be changed, and
  nothing kept what was put for them.
- Bad, because the readings that stood beside a question in a session, and not in the
  question itself, are part of what was put, and what counts as the ask is not drawn
  finely here.
- Bad, because a session copying out its own question can copy it wrongly, and nothing
  compares the two.
