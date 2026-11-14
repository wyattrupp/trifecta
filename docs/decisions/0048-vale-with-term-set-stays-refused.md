---
status: accepted
date: 2026-11-14
decision-makers: [wyatt]
informed: [claude]
---
# Vale started with TERM set stays refused

:::{decision}
:chooses: OPT_0048_REFUSE
:resolves: Q_PROGRAMS
:driven_by: REQ_KNOWN_PROGRAM
:::

## Context and Problem Statement

Traced on Linux in {need}`PLAN_0008`'s task 6, Vale started with `TERM` set looks the
user up through the name service, which connects to the name service's socket and may
load modules that reach the network, and reads the terminal's description from the
user's home and the system's terminfo trees. With `TERM` unset it does neither.

## Decision Drivers

- A known program connects nowhere
- No test changes what it exists to check

## Considered Options

:::{opt} Refuse a start with TERM set
:id: OPT_0048_REFUSE
The recorder refuses Vale when `TERM` is set, and the test that runs the check starts it
without `TERM`. Good, because no lookup and no connection happen. Bad, because a test that
runs the check must leave `TERM` out.
:::

:::{opt} Record the terminal's description and allow the lookup
:id: OPT_0048_RECORD
Good, because nothing changes in the tests. Bad, because the name service can reach the
network, which {need}`REQ_KNOWN_PROGRAM` refuses.
:::

## Decision Outcome

Chosen option: {need}`OPT_0048_REFUSE`, because wyatt, 2026-11-14, choosing from Claude's
recommendations: "Keep refusing TERM (Recommended)".

## Consequences

- Good, because Vale is let through only where the trace shows it connects nowhere.
- Bad, because `test_init`'s helper drops `TERM` from the check it starts.
