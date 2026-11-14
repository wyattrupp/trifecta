---
status: accepted
date: 2026-11-14
decision-makers: [wyatt]
informed: [claude]
---
# git and Vale start without PWD

:::{decision}
:chooses: OPT_0050_STRIP
:resolves: Q_PROGRAMS
:driven_by: REQ_KNOWN_PROGRAM, REQ_REUSE_SOUND
:::

## Context and Problem Statement

git and Vale each stat the directory `PWD` names, to learn the working directory's name: a
trace in WSL shows `newfstatat(AT_FDCWD, "/srv/ws", ...)` with `PWD=/srv/ws`. Nothing in
{need}`DES_0009`'s list records that probe. A fixture copy of the repository inherits
`PWD` naming the original checkout, so on CI the traced Vale test reports a probe of
`/home/runner/work/trifecta/trifecta`, and a stored result would hold no key for a
directory the program read.

## Decision Drivers

- A read no key holds keeps the refusal
- Where the check is run from does not decide what git and Vale read

## Considered Options

:::{opt} Strip PWD for git and Vale
:id: OPT_0050_STRIP
The check and the tests start git and Vale with `PWD` removed from the child's
environment, as {need}`DEC_0049` removes the variables that move their reads; a start that
still holds it, even empty, stays refused. Good, because the programs stat no directory
the key misses and a copy reads what the original reads. Bad, because a program started
without it takes the working directory's name from the system, which may spell a linked
directory differently.
:::

:::{opt} Key the directory PWD names
:id: OPT_0050_KEY
Good, because nothing is removed. Bad, because the key then holds a path outside the
repository that differs between copies, so a copy never reuses the original's result.
:::

:::{opt} Leave the probe unrecorded
:id: OPT_0050_LEAVE
Good, because nothing changes. Bad, because a program reads a place no key holds, and the
traced tests fail in every fixture copy.
:::

## Decision Outcome

Chosen option: {need}`OPT_0050_STRIP`, because wyatt, 2026-11-14, choosing from Claude's
recommendations: "Strip PWD for git/Vale (Recommended)".

## Consequences

- Good, because `toolchain.program_env`, the one function that gives every start of git or
  Vale in the check its environment, removes `PWD` beside {need}`DEC_0049`'s variables, from
  the recorder's own list.
- Bad, because a start of git or Vale outside the check and the tests, one that keeps
  `PWD`, as a shell's child does, stays refused.
