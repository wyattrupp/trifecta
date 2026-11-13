---
status: accepted
date: 2026-11-13
decision-makers: [wyatt]
informed: [claude]
---
# The traced build's own reads are allowed narrowly

:::{decision}
:chooses: OPT_0043_NARROW
:resolves: Q_TRACE_FRESH
:driven_by: REQ_KNOWN_PROGRAM, REQ_REUSE_SOUND
:::

## Context and Problem Statement

{need}`DEC_0037` keys `test_record_trace` on what `strace` saw, and {need}`DES_0009`
refuses the run on any read under `/proc` but the traced processes' own `fd` listing and
`exe` link, on any socket of a network family, and, as the recorder refuses the run's own,
on a read through a link the run did not make. Built in {need}`PLAN_0008`'s task 4, the
key refuses the module for four reads the Sphinx build makes on Linux: CPython reads its
own `/proc/self/maps` as it starts; `jsonschema_rs` reads its own `/proc/self/cgroup` to
count the processors it may use; an imported library opens an IPv6 socket and binds it to
`::1` to learn whether the host has IPv6, and never connects; and the C library reads
`/usr/share/locale/locale.alias` through a link to `/etc/locale.alias`. So the module
stays fresh.

## Decision Drivers

- A changed input is never reused unchecked
- The traced build reads nothing outside the stated list that reaches the network

## Considered Options

:::{opt} Allow all four narrowly
:id: OPT_0043_NARROW
A traced process may read its own `/proc` entries `maps` and `cgroup`, as `self` or by its
number, unkeyed, as `/dev/urandom` is; it may open a socket of the `AF_INET` or `AF_INET6`
family only when it binds it to a loopback address and never connects, sends to an
address, listens or accepts on it; and its read of `/usr/share/locale/locale.alias`
through its link is recorded by the link, the link's target and the content the link
reaches, which a lookup takes again following the link. That path alone is named, as
{need}`REQ_HOST_READS` lets the design name paths. Good, because the module is stored and
each allowance reaches nothing the key misses. Bad, because the process's own memory map
and control group are read unkeyed.
:::

:::{opt} Leave it unstored
:id: OPT_0043_LEAVE
Good, because nothing is allowed beyond {need}`DES_0009`'s list. Bad, because the module
reruns in every copy, as before {need}`DEC_0037`.
:::

:::{opt} Allow 1, 2, 4; keep sockets refused
:id: OPT_0043_NO_SOCKETS
Good, because no socket of a network family is opened. Bad, because the Sphinx build
opens one and the module stays fresh.
:::

## Decision Outcome

Chosen option: {need}`OPT_0043_NARROW`, because wyatt, 2026-11-13, choosing from Claude's
recommendations: "Allow all four narrowly (Recommended)".

## Consequences

- Good, because `test_record_trace` can be stored, keyed on the documents the build read.
- Bad, because what a process reads of its own memory map and control group is not part of the key, as {need}`DEC_0037` accepts the kernel.
- Bad, because any other read through a link, `/proc` entry or socket stays refused, so a build that reads one more is fresh again.
