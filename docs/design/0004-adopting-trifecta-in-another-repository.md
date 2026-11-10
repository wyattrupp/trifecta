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
URL form, and only when the URL's owner and repository are the package's own project, so
the line cannot name another project's release.
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
directories, a Makefile, the hardened CI workflow, the hashed lock, the `.gitattributes`
that DES_0006 holds the repository to, a CODEOWNERS entry for the files that steer the
check and the session, and the planning files. Before it writes any file it checks every
target with `lstat`, and reads, parses and validates an existing `.claude/settings.json`,
so every refusal comes before the first write. It creates each file exclusively and
lists what it wrote. The settings file is the one target it changes, and its merge is
the last write; on any failure it removes every file it created in the run, so the
registration never points at a script that was not written. When the
registration is already there it writes nothing to the file and does not list it;
otherwise it lists it as changed. It reads the file as UTF-8 through a handle that does
not follow links, merges the hook's registration in as REQ_INIT_SAFE states, and writes
the result to a new file under the fixed name `.claude/settings.json.trifecta-new`,
created exclusively with mode 0600 and then given the original's mode bits; a file left
at that name by an earlier run is refused and named. Just before the move it checks with
`lstat` that `.claude/` is still not a link or other reparse point, and that the
original's identity and modification time are unchanged; then it moves the new file over
the original. On any failure it removes the new file and leaves the original as it was.
:::

:::{component} Planning default
:id: COMP_PLANNING_DEFAULT
:satisfies: REQ_PLANNING_DEFAULT, REQ_HOOK_FAILS_CLOSED
:constrained_by: DEC_0014
:consumes: IF_CLI
The CLAUDE.md section, the project skill, the PreToolUse hook script and its registration
in `.claude/settings.json`, written by init or, for an existing settings file, merged
into it. The hook covers the file-writing tools
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
`trifecta setup`, `trifecta check [--base REF]`, `trifecta fixtures`, `trifecta new`,
`trifecta next`, `trifecta review` and `trifecta init`. Each command MUST read the corpus from the working
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

The template repository is not protected, and nothing compares it with init's output for
the release it pins. The settings exported to `.github/settings/` are a snapshot, and the
live settings can drift from it. A test's declaration of the requirements it proves is
taken as given. `trifecta check` runs the checked repository's own `docs/conf.py` and the
Vale in its `bin/`. The session instructions init writes are guidance to the model, not a
boundary. A CODEOWNERS entry gates nothing unless the ruleset requires code-owner review.
The hook can be switched off where init cannot see it: `.claude/settings.local.json`,
user settings and managed settings can each disable hooks, so the hook stops a mistake
only in a session that runs it. On Windows the merged settings file takes its access
rules from `.claude/`, not from the original, so a file locked down more tightly than its
directory loses that. An `env` in the settings file that sets `PATH` or
`CLAUDE_PROJECT_DIR` may send the registered command to another interpreter or script;
init does not look for one.

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

:::{review} Correctness; security
:id: REV_DES_0004_3
:k: 2
:date: 2026-11-08
The review recorded as {need}`REV_RFC_0006_1` covered this change.
:::

:::{review} Correctness; security
:id: REV_DES_0004_4
:k: 2
:date: 2026-11-09
:digest: 2d6fd9d99b590d2fa958c2521a220c7cf4db7e6a8994a6c76f4d599d6825573d
:::

:::{review} Correctness; security
:id: REV_DES_0004_5
:k: 2
:date: 2026-11-10
:digest: e3a02b82028be8c615e7ac2b493a37a0704ec94bf4334d05edf8f8dc9b873878
:::
