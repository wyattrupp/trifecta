---
status: approved
authors: [claude]
---
# Adopting trifecta in another repository

:::{design}
:::

## Overview

The extension, schemas, plan rules, tools and Vale styles move into one package with a
`trifecta` command. In this repository the package is installed from source and runs the
fixture audit and the self-tests; anywhere else it is installed from a release wheel
pinned by hash and runs only the corpus checks. `trifecta init` writes an adopting
repository's corpus skeleton, build files, CI workflow, and the three files that make a
Claude Code session plan through the corpus. A template repository holds exactly what
init writes. The README leads with the steps to adopt, and a test runs those steps.

Components here have no `spec` until they are built; the plan that builds them adds it.

## Requirements

:::{needtable}
:filter: type == 'req' and len(satisfies_back) > 0
:columns: id, title, satisfies_back as "Satisfied by"
:style: table
:::

## Constraints

:::{needtable}
:filter: type == 'decision' and len(constrained_by_back) > 0
:columns: id, title, status
:style: table
:::

## Components

:::{component} Toolchain package
:id: COMP_PACKAGE
:satisfies: REQ_ONE_PACKAGE
:constrained_by: DEC_0013
:provides: IF_CLI
A `src/trifecta/` package holding the extension, schemas, plan rules, tools, Vale styles
and configurations, with a `pyproject.toml` and a `trifecta` command. It reads the
corpus from the working directory.
:::

:::{component} Self-test switch
:id: COMP_SELF_TEST_SCOPE
:satisfies: REQ_SELF_TESTS_SCOPED
:constrained_by: DEC_0013
A configuration value, set only in this repository's `docs/conf.py`, under which the
check runs the fixture audit.
:::

:::{component} Test proofs
:id: COMP_TEST_PROOFS
:satisfies: REQ_PROVEN_BY_TEST
:constrained_by: DEC_0015
`unittest` modules under `tests/` that declare the requirements they prove; the check
runs them and the fixture audit counts each declaration as a proof.
:::

:::{component} Init command
:id: COMP_INIT_COMMAND
:satisfies: REQ_INIT_PASSES
:constrained_by: DEC_0013
:consumes: IF_CLI
Writes `docs/` with a configuration that loads the package, an index, the typed
directories, a Makefile, the CI workflow, a lock line pinning the package, and the
planning files. It refuses to overwrite a file and lists what it wrote.
:::

:::{component} Planning default
:id: COMP_PLANNING_DEFAULT
:satisfies: REQ_PLANNING_DEFAULT
:constrained_by: DEC_0014
:consumes: IF_CLI
The CLAUDE.md section, the project skill and the PreToolUse hook that init installs. They
name the commands and the typed directories, and the hook refuses a write under
`docs/superpowers/` with a message that names `trifecta new`.
:::

:::{component} Release workflow
:id: COMP_RELEASE
:constrained_by: DEC_0013
Builds the wheel on a version tag and attaches it to the release with its SHA-256, which
is the line an adopting repository pins.
:::

:::{component} Template repository
:id: COMP_TEMPLATE_REPO
:constrained_by: DEC_0013, DEC_0014
A GitHub template repository whose content is the output of `trifecta init` and nothing
else, pinned to the latest release.
:::

:::{component} Adoption guide
:id: COMP_ADOPTION_GUIDE
:constrained_by: DEC_0013, DEC_0014
The README, leading with "Run this in your repo": from the template, or with
`trifecta init` in an existing repository; the lock line; `make check` and CI; planning
with Claude Code. A test runs its commands in an empty directory against the built wheel.
:::

## Interfaces

:::{interface} Command line
:id: IF_CLI
:constrained_by: DEC_0013
`trifecta check [--base REF]`, `trifecta fixtures`, `trifecta new`, `trifecta next`,
`trifecta review` and `trifecta init`. Each command MUST read the corpus from the working
directory, and MUST exit non-zero on any finding or refusal.
:::

## Risks

This repository is private, so an adopting repository on another account cannot download
a release wheel without a token; the release task asks wyatt whether to make the
repository public or to authenticate downloads. Moving the code changes every `spec` path
in the design docs at once; the first task moves them together, and REQ_SPEC_RESOLVES
catches any it misses. A change to how the superpowers skills choose paths can bypass the
skill; the hook and the check still hold.

## Review
