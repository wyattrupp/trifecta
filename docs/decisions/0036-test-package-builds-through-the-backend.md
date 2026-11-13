---
status: accepted
date: 2026-11-11
decision-makers: [wyatt]
informed: [claude]
---
# Test package builds through the build backend

:::{decision}
:chooses: OPT_0036_BACKEND
:resolves: Q_HOST
:driven_by: REQ_HOST_READS
:::

## Context and Problem Statement

`test_package` runs `pip wheel`, and pip reads the host: on Linux `distro` reads
`/etc/os-release` and runs `lsb_release`, on Windows `rich` reads the host name. Calling
`flit_core.buildapi.build_wheel` directly gave the wheel with no refusal on either
platform.

## Decision Drivers

- No new input kind for one test
- The wheel is still built and checked

## Considered Options

:::{opt} Build through the backend
:id: OPT_0036_BACKEND
Good, because it trusts nothing new. Bad, because the test proves the backend's
wheel, not pip's call of it.
:::

:::{opt} Keep pip, and record the host
:id: OPT_0036_PIP
Bad, because the host name becomes an input, and pip's other reads stay.
:::

## Decision Outcome

Chosen option: {need}`OPT_0036_BACKEND`, because wyatt, 2026-11-11: "just make recommendations, and ask using ask user tool"; he chose "Yes, through the backend".

## Consequences

- Good, because `test_package` needs no host read beyond the `uname` that
  {need}`DEC_0039` blanks.
- Bad, because `test_adoption`'s guide still runs pip, in its fresh module.
