---
status: accepted
date: 2026-11-13
decision-makers: [wyatt]
informed: [claude]
---
# The trace leaves out only Python's own trees

:::{decision}
:chooses: OPT_0044_TREES
:resolves: Q_TRACE_FRESH
:driven_by: REQ_KNOWN_PROGRAM, REQ_REUSE_SOUND
:::

## Context and Problem Statement

{need}`DES_0008`'s recorder leaves every file under the interpreter's prefixes to the
environment key, which holds the interpreter's version, the site directories' entries and
every installed distribution's `RECORD`. Built in {need}`PLAN_0008`'s task 4, the key
{need}`DEC_0037` takes from `strace`'s log left out the same prefixes. Where the
interpreter is the system's, its base prefix is `/usr`, so a traced program's reads under
`/usr/lib` and `/usr/share`, which no environment key covers, would go unkeyed; the review
of the task found it.

## Decision Drivers

- A changed input is never reused unchecked
- The interpreter's own files stay with the environment key, as the recorder keeps them

## Considered Options

:::{opt} Only Python's own trees
:id: OPT_0044_TREES
What `strace` saw is left out only under the interpreter's own trees, sysconfig's
`stdlib`, `platstdlib`, `purelib`, `platlib`, `scripts` and `include`, laid out under
`sys.prefix` and under `sys.base_prefix`; every other path under the prefixes, as
`/usr/lib` and `/usr/share`, is keyed. Good, because a system library or data file a traced
program reads is keyed wherever the interpreter lives. Bad, because a read of the
interpreter's own trees stays with the environment key, which holds what is installed and
not each file's content.
:::

:::{opt} Keep whole prefixes out
:id: OPT_0044_PREFIXES
Good, because the trace treats paths as the recorder treats the run's own. Bad, because
under a system interpreter whole system trees go unkeyed.
:::

:::{opt} Key everything
:id: OPT_0044_ALL
Good, because nothing is left to the environment key. Bad, because the interpreter's own
start reads its links, which the recorder refuses, and every module of the standard
library is hashed at each lookup.
:::

## Decision Outcome

Chosen option: {need}`OPT_0044_TREES`, because wyatt, 2026-11-13, choosing from Claude's
recommendations: "Only Python's own trees (Recommended)".

## Consequences

- Good, because a traced program's system libraries and data are part of its key.
- Bad, because the trace's rule and the recorder's own differ: the recorder still leaves the whole prefixes to the environment key for the run's own reads.
