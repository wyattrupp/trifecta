---
status: accepted
date: 2026-11-07
decision-makers: [wyatt]
---
# Fixtures mutate the real corpus

:::{decision}
:chooses: OPT_0007_MUTATION
:resolves: Q_FIXTURE_FORM
:driven_by: REQ_FIXTURE_PER_INVARIANT
:::

## Context and Problem Statement

Each invariant needs a negative fixture that the check rejects. A fixture can be a small
standalone corpus, or a mutation applied to this repository's own corpus.

## Decision Drivers

- A fixture fails for the stated reason, not an incidental one
- Fixtures stay valid as the corpus evolves

## Considered Options

:::{opt} Mutations of the real corpus
:id: OPT_0007_MUTATION
Good, because every fixture starts from a corpus proven to pass, so the mutation is the
only change. Bad, because a mutation's anchor text breaks when that text is edited.
:::

:::{opt} Standalone fixture corpora
:id: OPT_0007_STANDALONE
Good, because fixtures are independent of the corpus. Bad, because each fixture
duplicates a whole valid corpus that drifts from the real one.
:::

## Decision Outcome

Chosen option: {need}`OPT_0007_MUTATION`, because the passing corpus is the control and
each mutation is the single variable.

## Consequences

- Good, because a broken anchor fails loudly instead of testing nothing.
- Bad, because editing anchored text means updating the fixture that anchors on it.
