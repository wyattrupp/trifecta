---
status: accepted
date: 2026-11-08
decision-makers: [wyatt]
consulted: [claude]
---
# Surveys and experiments hold the evidence

:::{decision}
:chooses: OPT_0018_TWO_TYPES
:resolves: Q_EVIDENCE_TYPES
:driven_by: REQ_SURVEY_SHAPE, REQ_EXPERIMENT_SHAPE
:::

## Context and Problem Statement

wyatt, 2026-11-08, asked for "surveys of literature, or experiments using the scientific
method", for software decisions and research alike, and answered "A" when asked which
documents carry the evidence. A benchmark, a user study, a training run and a review of
papers have to be the same kind of thing to the check, and a source cited by three
surveys has to have one home.

## Decision Drivers

- Each kind of evidence has its own sections and rules, without rules that branch on a
  field
- A source is defined once
- A decision links the statement it rests on, not a whole document

## Considered Options

:::{opt} Two new document types, surveys and experiments
:id: OPT_0018_TWO_TYPES
Good, because a survey holds `source` and `claim` needs and an experiment holds a
hypothesis, results and a conclusion, each with its own shape; a source is a need with its
own ID that any later survey references; a decision links a claim or a result. Bad,
because the corpus gains two document types and six need types.
:::

:::{opt} One evidence type with a kind field
:id: OPT_0018_ONE_TYPE
Good, because the corpus gains one type. Bad, because a survey and an experiment need
different sections and rules, so most rules would branch on the kind: two types in
disguise.
:::

:::{opt} A bibliography, surveys and experiments
:id: OPT_0018_BIBLIOGRAPHY
Good, because sources live apart from what is claimed of them. Bad, because each new
source means editing a second file, and a bibliography fills with sources nothing cites.
:::

## Decision Outcome

Chosen option: {need}`OPT_0018_TWO_TYPES`, because wyatt chose it, and it gives each kind
of evidence its own shape while keeping one home for each source.

## Consequences

- Good, because a claim, not a paper, is the unit of evidence, so a decision points at
  the statement it rests on and a locator in the source.
- Good, because a benchmark, a user study and a training run are all experiments to the
  check, under one set of rules.
- Bad, because a source defined in one survey and cited by another ties the second to the
  first; removing the first survey breaks the second's links, which the check reports.
