---
status: accepted
date: 2026-11-15
decision-makers: [wyatt]
informed: [claude]
---
# The source is held to the declared terms

:::{decision}
:chooses: OPT_0055_HOLD_SOURCE
:resolves: Q_TERM_SOURCE
:::

## Context and Problem Statement

{need}`RFC_0010` records that the book it reads draws its glossary from the names in the
source, which it treats as the one home of the vocabulary, and that this holds here only
in part: a session takes each word as written, so terms declared ahead of the code are
of use to it. What is left of the fault is that {need}`REQ_CANONICAL_TERMS` holds the
prose of the corpus to the declared terms and nothing compares those terms with the
source.

Measured on 2026-11-15 at commit `50ff955`, over the term needs of the RFCs and the
names, comments and string literals of the 27 Python files under `src`:

| Reading | Value |
| --- | --- |
| Declared terms | 29 |
| Terms found in a name in the source | 14 |
| Terms found in a comment or a string in the source | 18 |
| Terms found nowhere in the source | 11 |
| Of those, terms of an RFC that is not built | 5 |
| Of those, terms of {need}`RFC_0010`, which are about documentation | 4 |
| Of those, terms of a built RFC that the source words another way | 2 |
| Declared synonyms | 15 |
| Synonyms found in a name, a comment or a string in the source | 0 |
| Distinct names in the source | 2,059 |

How each was read: names, comments and strings by Python's `tokenize` module; each split
into words at case changes and at anything that is not a letter or a digit, lowered, and
with a final `s` dropped; a term or synonym is found where its words occur in that order.

Three things the comparison showed. One term is used in the source with another meaning:
{need}`TERM_TRACE` is the requirements of one RFC with what satisfies them, and all 21
names in the source that hold the word are in `record.py` and are about tracing a
process with strace. Two terms of built RFCs are worded another way in the source:
{need}`TERM_NESTED_RECORDING` is `nested_recorder` there, ten times, and
{need}`TERM_DECISION_RECORD` is `madr`, eight times. And no declared synonym occurs in
the source at all, though no check reads the source for one.

Two limits. The match is of words, so it found where the word of {need}`TERM_TRACE`
occurs and not that it means something else there; a person read that. And the source
is the Python files only, not the workflow files or the README.

## Decision Drivers

- What is left of the book's fault in {need}`RFC_0010`: no term is compared with the
  source
- {need}`DEC_0052`: the source is now where a component is described, so more prose
  that the terms should bind will be there
- Most terms are words of the corpus, such as plan, review and gate, with no one home in
  the code
- The size of the tool, which {need}`Q_TOOL_SIZE` leaves open

## Considered Options

:::{opt} Hold the source to the terms
:id: OPT_0055_HOLD_SOURCE
Terms stay declared by hand in RFCs. The rule against a declared synonym reaches the
source: a synonym in a name, a comment or a string there is a finding. No glossary is
drawn from the code. Good, because one vocabulary then binds the corpus and the source,
which matters more once descriptions move to the source. Good, because it is the rule
that exists, read over more files, and it passes today. Bad, because it does not catch a
term used with another meaning, as with {need}`TERM_TRACE`.
:::

:::{opt} Also report terms the source does not use
:id: OPT_0055_UNMATCHED
As above, and the check lists each term of a built RFC that no name or comment in the
source uses. Good, because it would have reported the two terms worded another way. Bad,
because a term that rightly has no code needs a rule to excuse it, and nine of the
eleven unmatched terms are of that kind.
:::

:::{opt} Draw the glossary from the code
:id: OPT_0055_FROM_CODE
The book's way: terms are the names in the source with what their docstrings say, and
the term needs are retired. Good, because nothing is declared twice. Bad, because there
are 2,059 names and 29 terms, and most of the terms name things of the corpus that no
one name in the code stands for.
:::

:::{opt} No comparison
:id: OPT_0055_NONE
As now: the terms bind the prose of the corpus only. Good, because nothing is built. Bad,
because the source has kept to the vocabulary so far with nothing holding it there.
:::

## Decision Outcome

Chosen option: {need}`OPT_0055_HOLD_SOURCE`, because wyatt, 2026-11-15, choosing from
Claude's recommendations with the readings above in the ask: "Hold source to the terms
(Recommended)".

## Consequences

- Good, because the descriptions that {need}`DEC_0052` moves to the source come under
  the same terms as the corpus they leave.
- Bad, because the check does not yet hold this; {need}`REQ_CANONICAL_TERMS` stands as
  written, and {need}`RFC_0010` has to gain a requirement before this binds anything.
- Bad, because the one word with two meanings is left as it is: {need}`TERM_TRACE` and
  the names in `record.py` both stand, and no rule here tells them apart.
- Bad, because the two terms the source words another way are not reported, and stay
  so unless someone changes the term or the names.
- Bad, because whether the rule reads workflow files, the README and the tests is not
  settled here.
