---
status: accepted
date: 2026-11-11
decision-makers: [wyatt]
informed: [claude]
---
# Test record trace is keyed on its trace

:::{decision}
:chooses: OPT_0037_STRACE_KEY
:resolves: Q_TRACE_FRESH
:driven_by: REQ_KNOWN_PROGRAM, REQ_LIFT_PROVEN
:::

## Context and Problem Statement

`test_record_trace` traces a Sphinx build with `strace`, which the module's
recorder never follows, so its own manifest holds nothing under `docs/`, which the build
reads. A key on that manifest would reuse it after a document changed.

## Decision Drivers

- A changed input is never reused unchecked
- Each fixture copy still proves the module against that copy

## Considered Options

:::{opt} Key it on what strace saw
:id: OPT_0037_STRACE_KEY
With `-y`, every failed probe recorded as absence and the whole environment
recorded. Good, because sound, at most 50 copies and about 953 Linux seconds. Bad,
because it trusts `strace` and the kernel.
:::

:::{opt} Run it once per job
:id: OPT_0037_ONCE
Bad, because a fixture copy no longer proves it.
:::

:::{opt} Stay fresh in every copy
:id: OPT_0037_FRESH
Bad, because it saves nothing.
:::

## Decision Outcome

Chosen option: {need}`OPT_0037_STRACE_KEY`, because wyatt, 2026-11-11: "just make recommendations, and ask using ask user tool"; he chose "Key on what strace saw".

## Consequences

- Good, because {need}`REQ_REUSE_SOUND` is unchanged: the key holds every file read, probed or listed and the whole environment.
- Bad, because `strace` becomes a known program under {need}`REQ_KNOWN_PROGRAM`, named by path and hash.
