---
status: accepted
date: 2026-11-08
decision-makers: [wyatt]
consulted: [claude]
---
# The rigor level is set per repository

:::{decision}
:chooses: OPT_0017_REPOSITORY
:resolves: Q_RIGOR_SCOPE
:driven_by: REQ_RIGOR_LEVEL
:::

## Context and Problem Statement

wyatt, 2026-11-08, on the levels of research rigor: "I do like the configuration piece you
mentioned, though". Asked where the level is set, wyatt answered "A", one setting for the
repository. A product repository and a research repository want different amounts of
evidence, and the level has to live in one place the check reads.

## Decision Drivers

- The level has one home
- Nobody can argue one weak claim down to a lower level
- A repository mixing product and research documents can still hold both to its needs

## Considered Options

:::{opt} One setting in the corpus configuration for the whole repository
:id: OPT_0017_REPOSITORY
Good, because the level lives in one line that the check, `init` and the planning files
all read. Bad, because a repository that mixes product and research documents holds all of
them to the strictest level it needs.
:::

:::{opt} Each RFC declares its level, with a floor for the repository
:id: OPT_0017_PER_RFC
Good, because a research RFC can be strict while a tooling RFC stays light, and the
decisions and designs answering an RFC take its level. Bad, because the level then has a
home in every RFC, and a decision answering two RFCs needs a rule for which level wins.
:::

:::{opt} Each requirement or decision declares its level
:id: OPT_0017_PER_NEED
Good, because it is the finest control. Bad, because the level is restated on every need,
and a weak claim can be moved to a lower level one at a time.
:::

## Decision Outcome

Chosen option: {need}`OPT_0017_REPOSITORY`, because wyatt chose it, and it gives the level
one home with no rule for combining levels.

## Consequences

- Good, because the check reads one value, and a fixture proves each level by changing
  that one line.
- Bad, because a repository that needs strict rigor for one study holds every decision to
  it; a separate repository for the research is the way out.
