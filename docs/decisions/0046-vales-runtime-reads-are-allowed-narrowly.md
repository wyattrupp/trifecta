---
status: accepted
date: 2026-11-14
decision-makers: [wyatt]
informed: [claude]
---
# Vale's runtime reads on Linux are allowed narrowly

:::{decision}
:chooses: OPT_0046_NARROW
:resolves: Q_PROGRAMS
:driven_by: REQ_KNOWN_PROGRAM, REQ_REUSE_SOUND
:::

## Context and Problem Statement

{need}`DEC_0038` makes a hash-pinned Vale a known program on a stated list, which a trace
on Linux proves. Built in {need}`PLAN_0008`'s task 6, the trace of Vale 3.13.0 in its two
forms shows that it loads the C library, `libstdc++`, `libm`, `libgcc_s`, `libpthread` and
`libresolv`, and that its runtime reads, besides `/proc/version`, its own
`/proc/self/maps`, `mountinfo` and `cgroup`,
`/sys/kernel/mm/transparent_hugepage/hpage_pmd_size`, `/sys/devices/system/cpu/online` and
its control group's `cpu.max`. The libraries and `/proc/version` can be keyed; the rest
cannot, since a process's own entries differ in every process. Unallowed, Vale stays
refused on Linux and `test_init` is never stored there.

## Decision Drivers

- A changed input is never reused unchecked
- Vale reads nothing outside the stated list that reaches the network

## Considered Options

:::{opt} Allow them unkeyed, narrowly
:id: OPT_0046_NARROW
Vale may read its own `maps`, `mountinfo` and `cgroup` under `/proc`, as `self` or by its
own number, `/sys/kernel/mm/transparent_hugepage/hpage_pmd_size`,
`/sys/devices/system/cpu/online` and its own control group's `cpu.max`, none of them
keyed; `/proc/version` and the libraries it loads stay keyed, and any other read under
`/proc` or `/sys` keeps the refusal. Good, because `test_init` is stored on Linux and each
allowance is the process's own state or the machine's, as {need}`DEC_0043` allows the
traced build's. Bad, because those reads are not part of the key.
:::

:::{opt} Keep Vale refused on Linux
:id: OPT_0046_REFUSED
Good, because nothing more is allowed. Bad, because `test_init` reruns in every copy on
Linux.
:::

:::{opt} Move the check's tests into a fresh module on Linux
:id: OPT_0046_MOVE
Good, because the rest of `test_init` is stored. Bad, because the two tests that run Vale
are nearly all its time.
:::

## Decision Outcome

Chosen option: {need}`OPT_0046_NARROW`, because wyatt, 2026-11-14, choosing from Claude's
recommendations: "Allow unkeyed, narrowly (Recommended)".

## Consequences

- Good, because the recorder lets Vale through on Linux on the stated list, and the trace
  test fails on any read under `/proc` or `/sys` beyond these.
- Bad, because a Go runtime that reads one more such file is refused again until the list
  changes.
