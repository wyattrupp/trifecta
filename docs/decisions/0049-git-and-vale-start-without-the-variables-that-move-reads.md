---
status: accepted
date: 2026-11-13
decision-makers: [wyatt]
informed: [claude]
---
# git and Vale start without the variables that move their reads

:::{decision}
:chooses: OPT_0049_STRIP
:resolves: Q_PROGRAMS
:driven_by: REQ_KNOWN_PROGRAM, REQ_REUSE_SOUND
:::

## Context and Problem Statement

{need}`DES_0009` refuses a start of git or Vale whose environment holds
`LD_LIBRARY_PATH`, `LD_PRELOAD`, `LD_AUDIT`, `LOCPATH`, `NLSPATH` or `GCONV_PATH`, since
each moves what the program or its loader reads to where no key holds it. CI's
`setup-python` sets `LD_LIBRARY_PATH` on Linux, so every check there starts git and Vale
with it, and `test_init` would never be stored on CI's Linux runner.

## Decision Drivers

- A read no key holds keeps the refusal
- What CI's runner sets does not decide whether a module is stored

## Considered Options

:::{opt} Strip them for git and Vale
:id: OPT_0049_STRIP
The check and the tests start git and Vale with the six variables removed from the
child's environment; a start that still holds one stays refused. Good, because the
programs read only the stated places and `test_init` is stored on CI. Bad, because a
setting that needs one of them for git or Vale to run is lost.
:::

:::{opt} Key what each variable names
:id: OPT_0049_KEY
Good, because nothing is removed. Bad, because each names a search path or a module the
recorder would have to follow as the loader and the C library do.
:::

:::{opt} Leave them refused as they come
:id: OPT_0049_REFUSE
Good, because nothing changes. Bad, because `test_init` is never stored on CI's Linux
runner.
:::

## Decision Outcome

Chosen option: {need}`OPT_0049_STRIP`, because wyatt, 2026-11-13, choosing from Claude's
recommendations: "Strip them for git/Vale (Recommended)".

## Consequences

- Good, because one function, `toolchain.program_env`, gives the environment every start
  of git or Vale in the check takes, from the recorder's own list.
- Bad, because a start of git or Vale outside the check and the tests, one that keeps a
  variable, stays refused.
