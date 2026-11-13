---
status: accepted
date: 2026-11-11
decision-makers: [wyatt]
informed: [claude]
---
# Tests that run bash stay fresh in their own module

:::{decision}
:chooses: OPT_0034_FRESH_MODULE
:resolves: Q_BASH
:driven_by: REQ_KNOWN_PROGRAM, REQ_LIFT_PROVEN
:::

## Context and Problem Statement

bash runs whatever its script names, so {need}`REQ_KNOWN_PROGRAM` refuses it.
`test_init` and `test_planning` each have a bash test, about 0.3 seconds, and
`test_adoption` runs the README's adoption guide through bash, with pip, make, Vale and
the network behind it.

## Decision Drivers

- The guide's proof stays the guide as a reader runs it
- A refused program does not hold back the rest of a module

## Considered Options

:::{opt} Move them into modules that stay fresh
:id: OPT_0034_FRESH_MODULE
Good, because no proof changes and the rest of each module can be stored. Bad,
because `test_adoption` saves almost nothing, its guide test being nearly all its time.
:::

:::{opt} Run the guide's commands without bash
:id: OPT_0034_NO_BASH
Good, because more is stored. Bad, because the test would prove its own reading of
the shell, not the guide.
:::

:::{opt} Lift bash
:id: OPT_0034_LIFT_BASH
Bad, because {need}`REQ_KNOWN_PROGRAM` forbids a shell, and everything bash runs
would have to be lifted with it.
:::

## Decision Outcome

Chosen option: {need}`OPT_0034_FRESH_MODULE`, because wyatt, 2026-11-11: "just make recommendations, and ask using ask user tool"; he chose "Own module, stays fresh" for the bash tests of `test_init`
and `test_planning`, and "Keep it fresh in its own module" for `test_adoption`'s guide
test.

## Consequences

- Good, because the adoption guide is still proven as written.
- Bad, because make, pip and the network stay refused; no stored module needs them.
