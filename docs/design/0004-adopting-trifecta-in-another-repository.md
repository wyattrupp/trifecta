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
URL and hash and runs only the corpus checks and the adopter's proof modules. `trifecta init`
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
:spec: pyproject.toml
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
A configuration value, set only in this repository's `docs/conf.py` and in the minimal
corpora this repository's own tests build as their inputs, under which the check runs the
fixture audit.
:::

:::{component} Test proofs
:id: COMP_TEST_PROOFS
:spec: src/trifecta/proofs.py#def check_proofs
:satisfies: REQ_PROVEN_BY_TEST
:constrained_by: DEC_0015
`unittest` modules under `tests/` whose tests declare the requirements they prove. A
declaration is a decorator call `@proves("REQ_…", …)` and a system value a decorator call
`@only_on("posix")` or `@only_on("nt")`, each naming the bare name bound by `from
trifecta.testing import proves, only_on` without `as`, with string literals as its only
arguments; both return the method unchanged. Any other decorator call that ends in
`proves` or `only_on` or refers to `trifecta.testing`, and any other binding of those two
names in a module that imports them, is reported under REQ_PROVEN_BY_TEST.

The check reads every declaration and system value from every `.py` file under `tests/`
as a literal in the source, without importing it. A proof module is a file that holds a
declaration or a system value, and every class statement in it is a class the check
reads. The check itself decides which proof modules run: those whose file name matches
`test*.py` by case-sensitive comparison and whose path is a valid dotted module name. A
declaration or system value in any other file is read, never imported, and reported as
having no result, unless its test names a system the check is not running on. Each
declaration and each system value sits on one method definition in a class body and is
bound to it by the module, named from the file's path relative to the repository root,
the class's qualified name and the method name.

A declaration or system value on anything else, or that cannot be read as a literal, a
directory from `tests/` down to a proof module that is not a package, a class name that
more than one class statement or binding in a module resolves to, a method name that more
than one definition or declaration in a class resolves to or that is rebound later in its
class, a method with more than one system value, a system value on a class, a declared or
system-valued method collected under a class other than the one whose body defines it,
and a declared or system-valued method defined with `async def` in a class whose bases in
the source do not name `IsolatedAsyncioTestCase`, or whose own body holds `yield`, are
reported under REQ_PROVEN_BY_TEST. A system value other than exactly `posix` or `nt`, the
strings of `os.name`, including another case, a list or an empty string, is reported.
With no proof module, including with no `tests/`, the check runs no test and makes none
of the checks below.

When a proof module exists, the check reads `os.name` once, before it starts the tests,
and that value alone decides which tests run and which declarations count without
running; where `RUNNER_OS` is `Linux` or `Windows`, a value other than `posix` or `nt`
respectively is reported under REQ_PROVEN_BY_TEST. It imports no test module itself: it
runs the proof modules it chose in a child process started as `sys.executable -E -X
utf8`, so no `PYTHON` variable such as `PYTHONOPTIMIZE` applies and the child runs in
UTF-8 mode, and passes the child that list by module name and the exact tests to leave
out, which the child removes from the suite before the run, so they are not collected.
The child loads tests from those modules and no other, so an import that only one system
has belongs inside the test. Any exception raised while it imports a proof module becomes
a result for that module, which is reported whatever system its tests name. The child
reports its `os.name` before it imports any test module and again after the run, and its
results, on a channel the tests do not write to, written and read as UTF-8. A child
`os.name` that differs from the check's at either point, a malformed or unrecognised
record, a result for a class the check did not read, and a child that ends without a
result for every test it collected, whatever its exit status, are reported under
REQ_PROVEN_BY_TEST. A result of a class or module set-up or tear-down belongs to the
class or module it names. A result for an undeclared method with no system value, and one
of a set-up or tear-down whose class or module holds no declared or system-valued test,
is otherwise not judged.

Except as the next paragraph states, the check counts a declaration as a proof in the
fixture audit only when the results for its method, matched by the test's class module
and qualified name and its `_testMethodName`, not by its `id()`, are exactly one, and
that one is plain success. A subtest is not a result of its own: a failing, erroring or
skipped subtest is a failure, error or skip of its test. For a test that is declared or
has a system value, except one that names a system the check is not running on, a
failure, an error, a skip, an expected failure, an unexpected success, a skip or error in
a class or module set-up or tear-down, more than one result, a method call, as the test
case makes it and after an `IsolatedAsyncioTestCase` awaits it, that returns anything but
`None`, and no result at all, including for a declaration or system value on a method the
child does not collect as a test, are each reported under REQ_PROVEN_BY_TEST; the child
reports what each such call returned. These rules hold in an adopting repository too,
where only the fixture audit is off.

Where a test names a system and the check is not running on it, the audit counts that
test's declaration as a proof without running it, and lists it as counted but not run, on
standard error, in output that is not a finding and does not change the exit status,
because CI's job for the named system (DEC_0025) runs it and the main ruleset requires
both jobs to pass (DES_0006). That holds while the workflow and the ruleset stay as they
are (see Risks), and it is how DEC_0015's proof, a test that runs and passes, holds for a
test one system cannot run.
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
target with `lstat`, and reads and validates an existing `CLAUDE.md` and
`.claude/settings.json`, so every refusal comes before the first write. It creates each
file exclusively and lists what it wrote. Those two are the targets it changes: it
appends its section to `CLAUDE.md`, then merges the hook's registration into the
settings file as the last write, so the registration never points at a script that was
not written. A file that already holds init's part is not written or listed; one that
is changed is listed as changed.

Each change reads the file through a handle that does not follow links, builds the new
content, and writes it to a new file under a fixed name, the original's name followed by
`.trifecta-new`, created exclusively with mode 0600 and then given the original's mode
bits; a file left at that name by an earlier run is refused and named. Just before the
move it checks with `lstat` that every directory between the repository root and the file
is still not a link or other reparse point, and that the original's identity and
modification time are unchanged; then it moves the new file over the original. The append
keeps every byte already in `CLAUDE.md`, adds the file's line break if its last line has
none, then a blank line and the section, all with the file's own line break: CRLF when
its first line break is CRLF, LF otherwise; an empty file gets the section alone, in LF.
The merge reads the settings file as UTF-8 and merges as REQ_INIT_SAFE states.

On any failure init removes every new file and every file it created in the run, and if
`CLAUDE.md` was already moved, writes its original bytes and mode bits back the same
way, checking the identity and modification time of the file init moved there, so each
original is left as it was. If that restore is refused or fails, init reports that
`CLAUDE.md` holds the section and exits non-zero.
:::

:::{component} Planning default
:id: COMP_PLANNING_DEFAULT
:satisfies: REQ_PLANNING_DEFAULT, REQ_HOOK_FAILS_CLOSED
:constrained_by: DEC_0014
:consumes: IF_CLI
The CLAUDE.md section, the project skill, the PreToolUse hook script and its registration
in `.claude/settings.json`, written by init, or appended to an existing CLAUDE.md and
merged into an existing settings file. The hook covers the file-writing tools
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
:spec: src/trifecta/cli.py#COMMANDS
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

Each of these leaves the declarations of tests for a system counted with nothing running
them: a pull request that drops or retargets a CI job, skips one with a condition, lets a
job or step fail without failing the job, or removes the check step or puts it behind a
condition; a job in another workflow that shares a required job's name; and a ruleset
that stops requiring a job. GitHub treats a skipped required job as passing. Required
checks are not strict (DES_0003), so a job may have passed against an older base, and the
push check on main reports what that missed. In an adopting repository, a test that
applies only to a system its CI has no job for is never run, and nothing reports it. A
Python whose `os.name` is `posix` on Windows, such as Cygwin's or MSYS2's, runs the
`posix` tests there; CI's Windows job uses one whose `os.name` is `nt`.

The template repository is not protected, and nothing compares it with init's output for
the release it pins. The settings exported to `.github/settings/` are a snapshot, and the
live settings can drift from it. A test's declaration of the requirements it proves is
taken as given. `trifecta check` runs the checked repository's own `docs/conf.py` and the
Vale in its `bin/`. The session instructions init writes are guidance to the model, not a
boundary. Instructions already in `CLAUDE.md`, in files it imports, or in local, nested
or user memory files can contradict the appended section; init does not read them, and
only the hook enforces. A CODEOWNERS entry gates nothing unless the ruleset requires
code-owner review.
The hook can be switched off where init cannot see it: `.claude/settings.local.json`,
user settings and managed settings can each disable hooks, so the hook stops a mistake
only in a session that runs it. On Windows a changed `CLAUDE.md` or settings file takes
its access rules from its directory, not from the original, so a file locked down more
tightly than its directory loses that. An `env` in the settings file that sets `PATH` or
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

:::{review} Correctness; security
:id: REV_DES_0004_6
:k: 2
:date: 2026-11-10
:digest: ad1d8bf752102b859920f029bbb5b92a3e430b0368bbc4064f551e0ec24918c6
:::

:::{review} Correctness; security
:id: REV_DES_0004_7
:k: 2
:date: 2026-11-10
:digest: a0f6c31c98c90ff54ab9a74fbdac5a42907df0111d3a1935bef626e62a804bc6
Stopped after fourteen rounds with findings still open on COMP_TEST_PROOFS, left for task
3 of PLAN_0003 to settle when it builds the component: a child that exits during import
before reporting its `os.name`; whether the `async` and `yield` rule follows inherited
bases and nested functions; matching an inherited test to the function that defines it; a
test for an import failure in a module whose tests name the other system; reading `.py`
names case-sensitively; and importing only one of the two decorators.
COMP_SELF_TEST_SCOPE reads the minimal corpora this repository's own tests build as part
of this repository, so REQ_SELF_TESTS_SCOPED is unchanged.
:::
