---
status: accepted
date: 2026-11-11
decision-makers: [wyatt]
informed: [claude]
---
# The recorder follows a child that records itself

:::{decision}
:chooses: OPT_0035_STACKED
:resolves: Q_NESTED
:driven_by: REQ_NESTED_RECORDING
:::

## Context and Problem Statement

`test_build_reuse`, `test_store_reuse` and `test_record` start Python children that
run a recorder of their own, which today refuses the parent. That is the only reason in
two of them, 6141 Linux seconds, and 7963 with `test_record`. Code in such a child can
step around a wrapper without replacing it.

## Decision Drivers

- The child's own manifest, chosen by the test, never stands for it
- The largest saving in scope
- Every way around a wrapper is stated

## Considered Options

:::{opt} Stack the parent's recorder, with the gap stated
:id: OPT_0035_STACKED
The parent's recorder loads first under a name and variable of its own and records
the child as it records any child; the ways code can step around a wrapper are listed.
Good, because, with {need}`DEC_0038`'s moves of `test_record`'s other refusing
tests, it stores the three modules. Bad, because the listed ways stay open for the
repository's own test code.
:::

:::{opt} Merge the child's own manifest
:id: OPT_0035_MERGE
Bad, because the test chose that manifest's configuration, which
{need}`REQ_NESTED_RECORDING` rules out.
:::

:::{opt} Keep refusing
:id: OPT_0035_REFUSE
Good, because no gap. Bad, because the three modules stay fresh.
:::

## Decision Outcome

Chosen option: {need}`OPT_0035_STACKED`, because wyatt, 2026-11-11: "just make recommendations, and ask using ask user tool"; he chose "Accept the stated gap", for code the repository's own tests
run.

## Consequences

- Good, because modules 1, 3 and 4 of {need}`DEC_0032`'s order can be stored.
- Bad, because a way around a wrapper the design does not list, found later, reopens this decision.
