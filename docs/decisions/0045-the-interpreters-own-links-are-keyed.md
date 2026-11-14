---
status: accepted
date: 2026-11-13
decision-makers: [wyatt]
informed: [claude]
---
# The interpreter's own links are keyed

:::{decision}
:chooses: OPT_0045_KEY
:resolves: Q_TRACE_FRESH
:driven_by: REQ_KNOWN_PROGRAM, REQ_REUSE_SOUND
:::

## Context and Problem Statement

Under {need}`DEC_0044` the key {need}`DEC_0037` takes from `strace`'s log leaves out only
the interpreter's own trees, and a read through a link the run did not make refuses the
run, as {need}`DES_0008`'s recorder refuses the run's own. A virtual environment that uv
makes names, in its `pyvenv.cfg`, a `home` reached through a link to the interpreter's
versioned directory, and the interpreter reads that link as it starts. So every traced
Python in such an environment refused `test_record_trace`, though the link only says
where the interpreter lives.

## Decision Drivers

- A changed input is never reused unchecked
- A link that only says where the interpreter lives keeps its environment's reuse

## Considered Options

:::{opt} Key it as the interpreter's
:id: OPT_0045_KEY
The links met resolving `sys.executable`, `sys.prefix`, `sys.base_prefix` and the `home`
a virtual environment's `pyvenv.cfg` names are the interpreter's: a traced read through
one is held as a probe of the link with its target, which a lookup reads again, and
followed. Any other read through a link stays refused. Good, because such an environment
keeps its reuse and a link moved to another interpreter reruns the module. Bad, because
the trace holds one more kind of probe.
:::

:::{opt} Leave such venvs unstored
:id: OPT_0045_LEAVE
Good, because nothing is let through beyond {need}`DEC_0044`. Bad, because the module
reruns in every copy wherever the environment's home is a link, as uv makes it.
:::

## Decision Outcome

Chosen option: {need}`OPT_0045_KEY`, because wyatt, 2026-11-13, choosing from Claude's
recommendations: "Key it as the interpreter's (Recommended)".

## Consequences

- Good, because `test_record_trace` is stored in an environment uv made, keyed on where its interpreter's link points.
- Bad, because a probe in a manifest may hold a link's target, which IF_MANIFEST states.
