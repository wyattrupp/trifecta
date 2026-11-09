---
status: approved
authors: [claude]
---
# Adopting trifecta in another repository

:::{design}
:::

## Overview

The extension, schemas, plan rules, tools and Vale styles move into one package with a
`trifecta` command that reads the corpus from the working directory. In this repository
the package is installed from source with its hashed build backend, and runs the fixture
audit and the self-tests; anywhere else it is installed from a release wheel pinned by
URL and hash and runs only the corpus checks and the adopter's own tests. `trifecta init`
writes an adopting repository's corpus skeleton, build files, hashed lock, hardened CI
workflow, and the files that make a Claude Code session plan through the corpus. A
template repository holds exactly what init writes. The README leads with the steps to
adopt, and a test runs those steps.

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
and configurations, with a `pyproject.toml` and a `trifecta` command. Every path is
resolved from the working directory or from the package's own data, never from a
source-tree location. The pipeline accepts the package's lock line only in the pinned
URL form.
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
`unittest` modules under `tests/` that declare the requirements they prove. The check runs
them, reports a declared test that fails or is skipped, and counts a passing declaration
as a proof in the fixture audit.
:::

:::{component} Init command
:id: COMP_INIT_COMMAND
:satisfies: REQ_INIT_PASSES, REQ_INIT_SAFE, REQ_NO_SECRETS_IN_TREE
:constrained_by: DEC_0013
:consumes: IF_CLI
Writes `docs/` with a configuration that loads the package, an index, the typed
directories, a Makefile, the hardened CI workflow, the hashed lock, a CODEOWNERS entry for
the files that steer the check and the session, and the planning files. It checks every
target with `lstat`, creates each file exclusively, and lists what it wrote.
:::

:::{component} Planning default
:id: COMP_PLANNING_DEFAULT
:satisfies: REQ_PLANNING_DEFAULT, REQ_HOOK_FAILS_CLOSED
:constrained_by: DEC_0014
:consumes: IF_CLI
The CLAUDE.md section, the project skill, the PreToolUse hook script and its registration
in `.claude/settings.json`, all written by init. The hook covers the file-writing tools
and Bash, and refuses a write under `docs/superpowers/` with a message that names
`trifecta new`.
:::

:::{component} Repository protection
:id: COMP_REPO_PROTECTION
:spec: .github/settings/rulesets.json
:satisfies: REQ_RELEASE_TRUST
:constrained_by: DEC_0016
The GitHub settings releases are built under, exported to `.github/settings/`: rulesets
on the default branch and on every tag, secret scanning and push protection, Actions
limited to GitHub-owned actions pinned by SHA, approval for workflows from outside
contributors, private vulnerability reporting, and Dependabot alerts.
:::

:::{component} Release workflow
:id: COMP_RELEASE
:satisfies: REQ_RELEASE_TRUST
:constrained_by: DEC_0013
Builds the wheel on a version tag on main with hashed build dependencies, and after a
maintainer approves the release environment, attaches it to the release with its SHA-256
and a provenance attestation.
:::

:::{component} Template repository
:id: COMP_TEMPLATE_REPO
:constrained_by: DEC_0013, DEC_0014
A GitHub template repository whose content is the output of `trifecta init` and nothing
else, pinned to the latest release.
:::

:::{component} Adoption guide
:id: COMP_ADOPTION_GUIDE
:satisfies: REQ_ADOPTION_GUIDE
:constrained_by: DEC_0013, DEC_0014
The README, leading with "Run this in your repo": from the template, or with
`trifecta init` in an existing repository; the lock line and how to verify the release's
attestation; `make check` and CI; planning with Claude Code. A test runs its commands in
an empty directory against the wheel built from the workspace.
:::

## Interfaces

:::{interface} Command line
:id: IF_CLI
:constrained_by: DEC_0013
`trifecta check [--base REF]`, `trifecta fixtures`, `trifecta new`, `trifecta next`,
`trifecta review` and `trifecta init`. Each command MUST read the corpus from the working
directory, MUST exit non-zero on any finding or refusal, and MUST refuse a path argument
that resolves outside the repository.
:::

## Risks

Moving the code changes every `spec` path
in the design docs at once; task 2 moves them together, and REQ_SPEC_RESOLVES catches any
it misses. A pull request runs its own workflow, Makefile, tools and configuration in CI,
so it can weaken the check it is judged by, and a passing check proves nothing about such
a change. The only safeguard is the maintainer's review before merging: with one
maintainer, GitHub cannot require an approval the author cannot give, so the ruleset
requires none. A second maintainer brings required review and code owners back.

## Review

:::{review} Correctness; security
:id: REV_DES_0004_1
:k: 2
:date: 2026-11-08
The review recorded as {need}`REV_RFC_0003_1` covered this document.
:::

:::{review} Correctness; security
:id: REV_DES_0004_2
:k: 2
:date: 2026-11-08
The review recorded as {need}`REV_RFC_0004_2` covered this change.
:::
