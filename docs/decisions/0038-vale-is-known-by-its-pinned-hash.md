---
status: accepted
date: 2026-11-11
decision-makers: [wyatt]
informed: [claude]
---
# Vale is known by its pinned hash

:::{decision}
:chooses: OPT_0038_PINNED
:resolves: Q_PROGRAMS
:driven_by: REQ_KNOWN_PROGRAM, REQ_LIFT_PROVEN
:::

## Context and Problem Statement

The scope puts in modules that need programs RFC_0009 first left out: Vale in
`test_init`'s two check tests, 9.96 of its 11.2 seconds, and make, pip and the network in
`test_adoption`'s guide. Vale runs from `bin/`, under the repository, which
{need}`REQ_KNOWN_PROGRAM` as first written refused.

## Decision Drivers

- A program under the repository is trusted only by its own hash
- No test changes what it exists to check

## Considered Options

:::{opt} A hash-pinned Vale, traced
:id: OPT_0038_PINNED
The recorder checks `bin/vale`'s own SHA-256 against a pin of the binary, read
from its own package, before the start; Vale's inputs are traced on Linux. Good, because
`test_init` is stored. Bad, because the toolchain pins only the release archive today,
so a pin of the binary is a new constant.
:::

:::{opt} Move the Vale tests into a fresh module
:id: OPT_0038_FRESH
Good, because no new trust. Bad, because it saves about a ninth of `test_init`.
:::

## Decision Outcome

Chosen option: {need}`OPT_0038_PINNED`, because wyatt, 2026-11-11: "just make recommendations, and ask using ask user tool"; he chose "Hash-pinned Vale, traced", and on Windows "Yes, as for git";
make, pip and the network are not lifted, since only the fresh guide test needs them; and
for the other reasons, the "Recommended set".

## Consequences

- Good, because the check starts the Sphinx build in `docs/`, so Sphinx's change of directory is no change.
- Good, because the recorder wraps `os._exit` and writes the manifest first, under its
  lock through the real exit, only in its own process, with the exit status.
- Bad, because `test_record`'s `-S` test and the Windows junction and ctypes tests move into a module that stays fresh.
