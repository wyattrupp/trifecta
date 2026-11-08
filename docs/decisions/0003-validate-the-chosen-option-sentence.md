---
status: accepted
date: 2026-11-07
decision-makers: [wyatt]
---
# Validate the chosen-option sentence

:::{decision}
:chooses: OPT_0003_VALIDATE
:resolves: Q_CHOSEN_SENTENCE
:driven_by: REQ_CHOSEN_SENTENCE
:::

## Context and Problem Statement

The MADR template states the outcome as a sentence naming the chosen option. That
sentence restates the `chooses` link, which is a second source for the same fact.

## Decision Drivers

- A raw MADR still reads correctly on a code host
- The graph is the source of truth for which option was chosen

## Considered Options

:::{opt} Validate the sentence against the link
:id: OPT_0003_VALIDATE
Good, because the raw file stays complete and readable. Bad, because it is duplication
held consistent by a check, which is weaker than a single source.
:::

:::{opt} Generate the sentence from the link
:id: OPT_0003_GENERATE
Good, because the fact is written once. Bad, because the raw file is incomplete until
rendered.
:::

## Decision Outcome

Chosen option: {need}`OPT_0003_VALIDATE`, because readability of the raw file is part of
the MADR format's value. This is the corpus's one accepted exception to single source of
truth.

## Consequences

- Good, because a MADR reads the same raw and rendered.
- Bad, because the exception has to be enforced forever by its own invariant.
