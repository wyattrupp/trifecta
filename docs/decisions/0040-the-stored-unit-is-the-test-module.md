---
status: accepted
date: 2026-11-11
decision-makers: [wyatt]
informed: [claude]
---
# The stored unit is the test module

:::{decision}
:chooses: OPT_0040_MODULE
:resolves: Q_UNIT
:driven_by: REQ_LIFT_PROVEN
:::

## Context and Problem Statement

A recorded Python start that imports the test stack costs 1.35 seconds on Linux and
2.07 on Windows. `test_planning`'s 29 Linux tests take 6.1 seconds together, about 39 as
one child each.

## Decision Drivers

- A store that saves time
- Nested recording holds whole modules either way

## Considered Options

:::{opt} The module
:id: OPT_0040_MODULE
Good, because one start per module. Bad, because a
module reruns whole when one test's input changes.
:::

:::{opt} The test
:id: OPT_0040_TEST
Bad, because a start per test costs more than it saves.
:::

## Decision Outcome

Chosen option: {need}`OPT_0040_MODULE`, because wyatt, 2026-11-11: "just make recommendations, and ask using ask user tool"; he chose "The module".

## Consequences

- Good, because {need}`DES_0008`'s proof reuse stays as built.
