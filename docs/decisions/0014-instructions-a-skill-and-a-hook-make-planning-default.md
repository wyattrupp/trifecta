---
status: accepted
date: 2026-11-08
decision-makers: [claude]
informed: [wyatt]
---
# Instructions, a skill and a hook make planning default

:::{decision}
:chooses: OPT_0014_LAYERED
:resolves: Q_PLANNING_DEFAULT
:driven_by: REQ_PLANNING_DEFAULT
:::

## Context and Problem Statement

wyatt, 2026-11-08: "a claude.md set of tools that lets this just happen by default every
time I start planning in a session". The superpowers brainstorming skill writes a spec to
`docs/superpowers/specs/` unless the user's preferences say otherwise, and the
writing-plans skill writes a plan with its own task template. A session has to learn the
corpus's paths and shapes before it writes, and be stopped if it writes to the default
path anyway.

## Decision Drivers

- The session knows the flow without being told each time
- The instruction reaches the skills at the moment they choose a path
- A mistake is stopped when it is made, not at the next check

## Considered Options

:::{opt} CLAUDE.md, a project skill and a PreToolUse hook, all written by init
:id: OPT_0014_LAYERED
Good, because CLAUDE.md is always loaded, the skill carries the steps when planning
starts and states the path preference the brainstorming skill defers to, and the hook
refuses a write to the default path deterministically. Bad, because three files carry the
flow; each names the package's commands and restates no rule.
:::

:::{opt} CLAUDE.md alone
:id: OPT_0014_CLAUDE_MD
Good, because it is one file. Bad, because nothing stops a session that follows a skill's
default over the instructions.
:::

:::{opt} A hook alone
:id: OPT_0014_HOOK
Good, because it cannot be ignored. Bad, because it only says no; the session still has
to discover the right shape from the check's findings.
:::

## Decision Outcome

Chosen option: {need}`OPT_0014_LAYERED`, because it is the only option that both tells the
session what to do and stops it when it does otherwise.

## Consequences

- Good, because the rules stay in the package: the three files point at `trifecta new`,
  `trifecta next` and `trifecta review`, and the check's findings carry the detail.
- Bad, because a change to how the superpowers skills choose paths can bypass the skill;
  the hook and the check still hold.
