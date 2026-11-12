---
status: accepted
date: 2026-11-11
decision-makers: [wyatt]
informed: [claude]
---
# Git is a known program on repositories a test made

:::{decision}
:chooses: OPT_0033_STATED_TRACED
:resolves: Q_GIT_KNOWN
:driven_by: REQ_KNOWN_PROGRAM
:::

## Context and Problem Statement

git is the program most of the in-scope modules start. wyatt, 2026-11-11: "lift
git". Every git start in the eight modules is on a repository a test made; the strace of
git 2.39.5 in {need}`RFC_0009` lists what git read outside such a repository.

## Decision Drivers

- A start is stored only when every input it reads is recorded
- Each platform where git is lifted has a proof or a ruling
- A pin set by the recorder never changes a finding

## Considered Options

:::{opt} A stated list, proven by a Linux trace
:id: OPT_0033_STATED_TRACED
Fixed subcommands on a repository the run made, with `-C` only on such a
directory, the configuration and path variables refused or pinned by the test, the
inputs on a stated list recorded, and a `strace` test proving the list on each git
version. Good, because a start costs nothing more and the list is proven. Bad, because
it trusts the list on a version the test has not run.
:::

:::{opt} Trace every git start
:id: OPT_0033_TRACE_EACH
Key each git child on what `strace` saw. Good, because nothing is assumed on
Linux. Bad, because each start costs a traced start, and Windows stays refused.
:::

:::{opt} A stated list, with no trace
:id: OPT_0033_STATED_ONLY
Good, because it is cheapest. Bad, because nothing shows the list is whole.
:::

## Decision Outcome

Chosen option: {need}`OPT_0033_STATED_TRACED`, because wyatt, 2026-11-11: "just make recommendations, and ask using ask user tool"; he chose "Stated list + Linux trace"; for Windows, "Yes, under
the stated list", with the Linux trace standing for both, as {need}`DES_0008`'s Risks
accept for native code; and for git on this repository, "Keep it refused".

## Consequences

- Good, because the tests pin `HOME`, `GIT_CONFIG_GLOBAL` and the ceiling, as the
  chosen option says, and, derived by {need}`DES_0009`, `GIT_CONFIG_NOSYSTEM` and
  `XDG_CONFIG_HOME`, so the machine's configuration is no input.
- Bad, because `trifecta new`'s `config user.name` and the check's `ls-files --others --exclude-standard` have to be traced before the list holds them.
- Bad, because on Windows Git for Windows' credential helper is pinned off by the
  test, and the design states a Windows list from its layout, which no trace proves.
