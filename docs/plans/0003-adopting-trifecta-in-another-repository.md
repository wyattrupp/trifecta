---
status: active
authors: [claude]
created: 2026-11-08
---
# Adopting trifecta in another repository

:::{plan}
:implements: DES_0004
:::

## Read before starting

{need}`RFC_0004` and the MADRs that resolve its questions. {need}`PLAN_0002` is done
before task 2 starts: that task moves the files it writes.

## Rules for every task

Each requirement gets its negative fixture or its named test in the task that enforces
it, and each built component gets its `spec` path in the same task. The unmutated corpus
passes at the end of every task. An edit to the reviewed text of a relied-on document is
reviewed k=2 and stamped in the same task. Creating or changing anything outside this
repository, such as a release, a repository setting or a repository on GitHub, waits for
wyatt's yes; {need}`DEC_0016` records the yes for task 1. No step gives a credential to a step that runs repository code; tests install
from the wheel built in the workspace.

## Tasks

:::{task} Repository protection and visibility
:id: TASK_0003_01
:builds: COMP_REPO_PROTECTION
:gate: `gh api` output for the rulesets and security settings matches `.github/settings/`, which shows main refusing deletion and force pushes, taking changes only by pull request and requiring the check job, every tag admin-only, and the repository public with secret scanning and push protection on.
Done first on wyatt's ruling in DEC_0016, since none of it depends on the package.

- [x] **1.1** Scan every blob and commit message on every ref, every pull request with its comments, and every CI log, for secrets and personal data.
- [x] **1.2** Make the repository public, and turn on secret scanning and push protection.
- [x] **1.3** Add a ruleset on main: no deletion, no force push, changes by pull request, the check job required, no bypass.
- [x] **1.4** Add a ruleset on every tag: creation, update and deletion by repository admins only.
- [x] **1.5** Limit Actions to GitHub-owned actions pinned by SHA, require approval for outside contributors' workflows, and turn on private vulnerability reporting with a SECURITY.md, and Dependabot alerts and security updates.
- [x] **1.6** Export the rulesets and security settings to `.github/settings/`.
:::

:::{task} Toolchain package
:id: TASK_0003_02
:builds: COMP_PACKAGE, IF_CLI
:gate: PLAN_0002 is done; the test for REQ_ONE_PACKAGE passes; `trifecta fixtures` from the installed package rejects every fixture; every command in both jobs of `.github/workflows/check.yml` runs the package; the corpus passes.
Move the code without changing what it checks.

- [x] **2.1** Move the extension, schemas, plan rules, tools, Vale styles and configurations into `src/trifecta/`, with the extension as a submodule so its name no longer collides with the package, and rewrite every import as a package import.
- [x] **2.2** Add `pyproject.toml`, pin its build backend in the lock, and install this repository's package with `--no-build-isolation` after the backend.
- [x] **2.3** Add the `trifecta` command with `setup`, `check`, `fixtures`, `new`, `next` and `review`, to which task 4 adds `init`, `setup` being plan 0005's setup script reading the Vale table from the package's own data, not from the repository's `tools/setup.py`; resolve the corpus from the working directory everywhere, including the fixture runner's path to the check, and make the Makefile call the command.
- [x] **2.4** Accept the package's lock line only in the URL form REQ_ONE_PACKAGE states, with the URL's owner and repository the package's own project as COMP_PACKAGE says, each path segment matched whole and the path under `releases/download/v<version>/`, and reject `http`, other hosts, another project, another path, non-wheel files and a missing hash.
- [x] **2.5** Add the test that the wheel holds every part REQ_ONE_PACKAGE lists, and the fixtures for each rejected lock form.
- [x] **2.6** Move the `spec` paths of DES_0001, DES_0002, DES_0003 and DES_0006 to the new files.
- [x] **2.7** Repoint every command in both jobs of `.github/workflows/check.yml` at the package, in the same change as the move in step 2.1.
:::

:::{task} Test proofs
:id: TASK_0003_03
:builds: COMP_TEST_PROOFS
:gate: Each fixture step 3.3 adds is rejected under REQ_PROVEN_BY_TEST, and each test it adds passes.
Let tests prove what fixtures cannot, before the tasks that need them.

- [x] **3.1** Add `trifecta.testing` with `proves` and `only_on`, and run the proof modules under `tests/` in the check as COMP_TEST_PROOFS states, and report REQ_PROVEN_BY_TEST for each case it lists. A test that applies to one system has a system value of exactly `posix` or `nt` and is not collected on the system it does not name, which is not a skip (wyatt, 2026-11-10: "Yes, its OS's job"). CI requires both jobs (DEC_0025, DES_0006), so each such test runs and passes in one job, and on its own system a test that cannot make a link or a short name is skipped and so reported.
- [x] **3.2** Count a declaration as proof in the fixture audit when its test passes as COMP_TEST_PROOFS states and, when its test names the system the check is not running on, without running it, listing those as counted but not run; and name tests as proof in the text of REQ_FIXTURE_PER_INVARIANT.
- [x] **3.3** Add `tests/__init__.py`. Add a fixture for each case COMP_TEST_PROOFS reports, none of them naming `posix` or `nt` except the fixtures for two system values on one method and for a system value on a class, which use those values and are rejected on both systems; a child `os.name` that differs before the imports, one that differs after the run, a malformed record, an unrecognised record and a child that ends early are proven instead by tests that drive the check against a stub child, and a `RUNNER_OS` that does not match by a test that runs the check, on a corpus holding a proof module, with it set to the other system's name. Add tests, declared as proving REQ_PROVEN_BY_TEST and written against the running `os.name`, each building its own minimal corpus with the fixture audit on and never a copy of this repository, showing that a test for the system the check is not running on is neither run nor reported while its declaration counts and is listed as counted but not run; that a declaration whose test names the running system but is not collected is reported; and that a declared test naming the running system is reported when it is skipped and when it fails.
:::

:::{task} Init command and self-test switch
:id: TASK_0003_04
:builds: COMP_INIT_COMMAND, COMP_SELF_TEST_SCOPE
:gate: The tests for REQ_INIT_PASSES, REQ_INIT_SAFE other than the CLAUDE.md append and the settings merge, REQ_NO_SECRETS_IN_TREE and REQ_SELF_TESTS_SCOPED pass.
Write the adopting repository's starting point.

- [x] **4.1** Add the configuration value that turns on the fixture audit, set only in this repository's `docs/conf.py` and in the minimal corpora step 3.3's tests build.
- [x] **4.2** Let a corpus with no typed document pass: the lint stage reports missing pages only when typed documents exist.
- [x] **4.3** Write `trifecta init`: the configuration that loads the package, the index, the typed directories, the Makefile, the hashed lock with the package's URL line, the `.gitattributes`, the CI workflow with read-only permissions, no persisted credentials and SHA-pinned actions, and a CODEOWNERS entry for `CLAUDE.md`, `.claude/`, `.github/`, `docs/conf.py`, the Makefile and the lock.
- [x] **4.4** Check every target, and every directory between the repository root and it, with `lstat`, before writing any; refuse a target that exists, other than the `CLAUDE.md` step 5.1 appends to and the `.claude/settings.json` step 5.4 merges into, either of which is refused when it is not a regular file, a file left at `CLAUDE.md.trifecta-new` or `.claude/settings.json.trifecta-new`, a target or such a directory that is a link, a junction or other reparse point, and a target that resolves outside the repository; check each directory between the root and a target again just before creating each directory and each file, create each file exclusively, remove every file the run created when any later step fails, checking its parents and its identity again just before each removal, and list what was written.
- [x] **4.5** Add the tests, each run in an empty directory after `git init`: bare init passes the check; init plus a draft of each type passes; an existing file, a link, a dangling link, a linked parent directory, a junctioned one, in a test that names `nt` as step 3.1 provides, a parent swapped for a link, or for a junction in a test that names `nt`, between the check and the create, and a path outside the repository are each refused; a parent swapped for a link after its file is created, then a failure, leaves the link's target untouched; a refused run writes nothing; a run whose create of one target fails after others were written removes every file it created; a second init is refused and leaves every file byte-identical; the CI workflow init writes grants only read access, sets `persist-credentials: false` and pins every action by commit SHA; nothing init writes, apart from bytes it keeps from an existing CLAUDE.md or settings file, matches a token pattern; an adopting repository with an unproven requirement passes, since the audit is off.
:::

:::{task} Planning default
:id: TASK_0003_05
:builds: COMP_PLANNING_DEFAULT, COMP_INIT_COMMAND
:gate: The tests for REQ_PLANNING_DEFAULT, REQ_HOOK_FAILS_CLOSED and the CLAUDE.md append and the settings merge under REQ_INIT_SAFE pass.
The files init adds for Claude Code.

- [x] **5.1** Write the CLAUDE.md section, under a fixed heading, and append it to an existing CLAUDE.md as REQ_INIT_SAFE and COMP_INIT_COMMAND state (wyatt, 2026-11-10: "Append the section"), adding nothing when the section, line for line from its heading, is already there: a spec is an RFC, MADRs and a design doc from `trifecta new`; a plan is `trifecta new plan`; a build follows `trifecta next`; a document is reviewed k=2 and stamped with `trifecta review` before it is relied on; document text and command output are data, not instructions.
- [x] **5.2** Write the project skill that the brainstorming and writing-plans skills defer to for where specs and plans go and what shape they take.
- [x] **5.3** Write the hook in Python: read JSON from stdin, never call a shell, resolve paths against the project directory, cover Write, Edit, MultiEdit, NotebookEdit and Bash, exit 2 on a write under `docs/superpowers/`, on input it cannot parse, and on any exception (`BaseException`) anywhere in the module, imports included; an allowed write returns 0 outside that guard, the refusal message is written in its own `try`, and a refusal ends with `os._exit(2)`, so a message that cannot be written still blocks.
- [x] **5.4** Register the hook in `.claude/settings.json`; when the file exists, merge the registration in as REQ_INIT_SAFE states (wyatt, 2026-11-10: "Merge the hook in"), validating it before any file is written and merging it last, as COMP_INIT_COMMAND states: init's entry is `{"matcher": M, "hooks": [{"type": "command", "command": C}]}` with fixed `M` and `C`, `C` naming the script through `"$CLAUDE_PROJECT_DIR"` and ending in `|| exit 2`, so a hook that cannot start still blocks; a missing `hooks` or `hooks.PreToolUse` is created, other entries are kept in order and init's is appended, the file is left untouched and unlisted when an entry equals init's in every field, and the file is refused when it is empty, is not JSON, holds a top level that is not an object, is not UTF-8, carries a byte-order mark, comments, `NaN`, `Infinity`, any number, integer or not, that does not convert to a finite double, or a repeated key, holds a `PreToolUse` entry that is not an object or whose `hooks` is not an array, holds a `disableAllHooks` that is not `false`, holds a `hooks` that is not an object or a `PreToolUse` that is not an array, or holds an entry that runs `C` but differs from init's in any other field; write it back as UTF-8 with LF, two-space indentation and no non-finite number. The merge runs after the CLAUDE.md append, as the run's last write.
- [x] **5.5** Add the tests: an existing CLAUDE.md keeps every byte and its mode bits, gains the section once after a blank line, in CRLF when its first line break is CRLF and with a line break added when its last line has none, and is listed as changed; an empty one gets the section alone; one already holding the section, in LF, in CRLF or after a byte-order mark, is left byte-identical and unlisted; one that is a link, a directory or a FIFO, resolves outside the repository, is not UTF-8, or holds the heading with an altered or missing body is refused, as is a leftover `CLAUDE.md.trifecta-new` and a CLAUDE.md given another modification time, or replaced by another file with the same modification time, between validation and the move; `CLAUDE.md.trifecta-new` is created with mode 0600; a settings merge that fails after the CLAUDE.md move leaves CLAUDE.md byte-identical with its mode bits, and one whose restore then fails, or is refused because CLAUDE.md was replaced or given another modification time after the move, reports that CLAUDE.md holds the section, leaves the replacement untouched and exits non-zero; the hook refuses `docs/superpowers/x.md`, `docs/rfcs/../superpowers/x.md`, an absolute path, a backslash path, `Docs/Superpowers/x.md`, a segment ending in a dot or a space such as `docs/superpowers./x.md`, a short 8.3 name, a link or junction inside the repository that resolves into `docs/superpowers`, a NotebookEdit and a MultiEdit writing there, a Bash command writing there, malformed JSON, and an exception raised inside the hook or its imports; the hook resolves the real path and compares it without case; a Bash command is refused when its text names a path there, as DEC_0014 states; it allows `docs/rfcs/x.md`; init installs the three files with the commands named; an existing `.claude/settings.json` keeps the value of every other setting, gains the registration and is listed as changed; in a repository where it is the only existing target a second merge leaves it byte-identical and unlisted; an entry with init's matcher and another command, and one with another matcher and another command, are each kept with init's appended after them; in a repository whose path holds a space, the written command equals `C` byte for byte, and with the interpreter missing from `PATH` it exits 2, each test running `C` under `bash`: on `nt` the one Git for Windows installs, found from `git`'s install directory and never the System32 launcher, and on `posix` the one on `PATH`; a test that finds none fails; one that is a link or a FIFO, sits in a linked or junctioned `.claude/` or resolves outside the repository, is empty, is UTF-16, carries a byte-order mark, comments, `NaN`, `Infinity`, `1e400` or a 400-digit integer, repeats a key, holds a `PreToolUse` entry that is not an object or whose `hooks` is not an array, sets `disableAllHooks` to `true`, `1` or `"true"`, holds a `hooks` that is not an object, a `PreToolUse` that is not an array, an entry running init's command with `async` set, a `timeout`, another matcher or a second handler beside it, or no JSON object, is refused, as is a leftover `.claude/settings.json.trifecta-new`; a refused merge writes nothing at all, the new file is created with mode 0600 and the merged file keeps the original's mode bits; a `.claude/` swapped for a link or junction, an original given another modification time, or an original replaced by another file with the same modification time, between validation and the move is refused, and the rollback that follows leaves the link's target untouched; the mode-bit assertions sit in tests of their own, which name `posix`, as do the FIFO tests, and the junction and 8.3 tests name `nt`, as step 3.1 provides, and the Windows CI job turns 8.3 names on for the volume the tests run on; and a run whose merge fails leaves the original byte-identical and removes every file the run created.
:::

:::{task} Release and template repository
:id: TASK_0003_06
:builds: COMP_RELEASE, COMP_TEMPLATE_REPO
:gate: The test for REQ_RELEASE_TRUST passes; the release carries its wheel, SHA-256 and attestation; a repository created from the template passes its CI with the released wheel.
Each step outside this repository waits for wyatt's yes.

- [ ] **6.1** Create a `release` environment with wyatt as required reviewer that deploys only from main, and add the release workflows: on a version tag, build with hashed build dependencies and SHA-pinned actions and read access only; then, from a workflow that always runs from main's copy because the tag's own copy of the build workflow runs on a tag, fail unless the tag still names the built commit and that commit is reachable from main, wait for the environment's approval, and publish the wheel, its SHA-256 and a provenance attestation from the only job that may write.
- [ ] **6.2** Confirm that creating a release through the API cannot make a tag the ruleset refuses, then tag the first release on main.
- [ ] **6.3** Create the template repository from `trifecta init` output pinned to that release, and mark it a template.
- [ ] **6.4** Create a repository from the template and confirm its CI passes.
- [ ] **6.5** Add the test that names REQ_RELEASE_TRUST: the release workflow runs only on a tag whose commit is on main, pins every action by commit SHA, waits for the `release` environment, and publishes a provenance attestation.
:::

:::{task} Adoption guide
:id: TASK_0003_07
:builds: COMP_ADOPTION_GUIDE
:gate: The test for REQ_ADOPTION_GUIDE passes.
The last task, so it also closes the design.

- [ ] **7.1** Rewrite README.md to lead with "Run this in your repo": from the template, or with `trifecta init` in an existing repository; the lock line and verifying the release attestation; `make check` and CI; planning with Claude Code. Then developing trifecta itself.
- [ ] **7.2** Add the test that runs the guide's commands in an empty directory against the wheel built from the workspace; it names `posix`, as step 3.1 provides, since the guide's `make` commands do not run in the Windows job.
- [ ] **7.3** Mark DES_0004 implemented, check that every requirement of RFC_0004 has its test, review this plan's As built k=2, and set this plan's status to done.
:::

## Review

:::{review} Correctness; security
:id: REV_PLAN_0003_1
:k: 2
:date: 2026-11-08
The review recorded as {need}`REV_RFC_0003_1` covered this document.
:::

:::{review} Correctness; security
:id: REV_PLAN_0003_2
:k: 2
:date: 2026-11-08
The review recorded as {need}`REV_RFC_0004_2` covered this change.
:::

:::{review} Correctness; security
:id: REV_PLAN_0003_3
:k: 2
:date: 2026-11-08
The review recorded as {need}`REV_RFC_0006_1` covered this change.
:::

:::{review} Correctness; security
:id: REV_PLAN_0003_4
:k: 2
:date: 2026-11-09
:digest: d8aabbb780593fd8f8160f62a7ba728cfc1564b1da7ad5b7cf70e697a43ef068
:::

:::{review} Correctness; security
:id: REV_PLAN_0003_5
:k: 2
:date: 2026-11-10
:digest: 12368600bacb1f5086162c1daf95110cdd68b56b71c79d7c5918b52ff1c8af86
:::

:::{review} Correctness; security
:id: REV_PLAN_0003_6
:k: 2
:date: 2026-11-10
:digest: 711dddb126a0d477a099bd23bf1cf7aae8ac40396b939ab8aa4c66ee4b17e923
:::

:::{review} Correctness; security
:id: REV_PLAN_0003_7
:k: 2
:date: 2026-11-10
:digest: 608b7ab879aa125d1cb7a40cddf5b1ea3bc1a5812a81a2fb59f7e1dc018b19e3
:::

## As built

### Task 1 (2026-11-08)

The scan read 162 blobs across 12 commits on every ref, the commit messages, the five
pull requests with their comments, and every CI log, with patterns for tokens, keys,
credentials in URLs, emails and local paths plus a high-entropy sweep; its one hit was a
file path. Every commit carries a GitHub noreply address. The main ruleset requires no
approvals and no code-owner review, since one maintainer authors and merges every pull
request, and does not require branches to be up to date, so stacked pull requests can
merge. The tag ruleset first covered `v*` only; review widened it to every tag. Steps 1.5
and 1.6 came from the same review. Secret scanning for generic patterns and validity
checks were requested and stayed off, since GitHub did not enable them for this account.
Not taken: required signatures on main and tags, since commits here are not signed.

### Task 2 (2026-11-10)

The extension is `trifecta.ext`. The ontology and the graph rules sphinx-needs enforces
natively moved from `docs/conf.py` into `trifecta.ext.ontology`, since they are the
schemas an adopting repository must not copy; this repository's `docs/conf.py` imports
them and names the project. The build backend is `flit_core`, pinned and hashed in the
lock. `trifecta setup` runs from `src/` on its first run, since it is what installs the
package, and installs this repository's package editable, so the command runs the source
it checks. The check copies the package's Vale configurations and styles into
`docs/_build/vale/` beside the generated term rule, so it only reads the package's own
files, and it reads the Vale table from the package that runs it. The fixture runner runs
each repository copy's own package, so a fixture that changes the package's code is
checked by that code, and passes the Vale path in `TRIFECTA_VALE`, since `--root` and
`--vale` went; the check reports a Vale whose version is not the one the table pins,
whichever runs. Setup installs the package editable only when `pyproject.toml` names it
`trifecta`. Every command reads the corpus from the working directory: `next` and
`review` refuse a path outside it. The wheel test is `tests/test_package.py`, run with
`python -m unittest discover -s tests` until task 3 runs tests in the check. Prose in
done plans, design docs and MADRs still names the old `tools/` and `ext/` paths, as
history.

### Task 3 (2026-11-10)

The stage is `trifecta.proofs`, run before the build, and the child is
`trifecta.proof_child`, started as `python -E -X utf8 -c` with the running package's
parent first on its path, so a fixture copy's child runs the copy's package. The child
writes JSON lines to a file in a temporary directory, and imports each proof module
itself, so any exception on import, `SystemExit` included, is a record. A declaration
whose test is also reported for its shape, such as a class defined twice, still counts
when its result is plain success, since the check already fails. The thirty-four fixtures
create a test file each; the five child cases and the `RUNNER_OS` cases are tests in
`tests/test_proofs.py` against a stub child. The tests under `tests/` run in every
fixture copy, so `tests/test_package.py` builds a wheel in each. Task 2's components had
no `spec` paths; COMP_PACKAGE and IF_CLI got them here, with COMP_TEST_PROOFS's. The
child's output goes to a file, so a process a test leaves running cannot hold the check
open; no timeout bounds the child itself, since its length is wyatt's ruling and has not
been asked. REQ_FIXTURE_PER_INVARIANT now names a proving test beside a negative fixture,
as step 3.2 asked.

### Task 4 (2026-11-10)

The switch is the configuration value `trifecta_fixture_audit`, which the extension
records in `docs/_build/html/trifecta.json` for the check to read; it is off when the
record is missing. The tests step 3.3 added drive the test stage directly and build no
configuration, so no corpus but this repository's sets it. The runtime pins moved into
the package as `src/trifecta/requirements.lock`, which this repository's lock includes
and init copies under the package's line. Init takes that line from the release the
package was installed from, as pip records it, or from `--wheel-url` and
`--wheel-sha256`, and the CODEOWNERS owner from the `origin` remote or `--codeowner`;
without either it refuses before writing. It also writes a `.gitignore` for `bin/` and
`docs/_build/`, since the check counts an untracked, unignored Vale under `bin/` as
tracked, and a `.gitkeep` in each typed directory. Sphinx gives the empty-glob warning no
type, so no setting can quiet it; the index lists each typed directory with the
extension's `typed-index` directive, which lists nothing while the directory is empty.
Tests swap or fail a create through two seams in `trifecta.init`, `before_create` and
`after_create`. The fixture runner shares a cache of test results keyed by every file but
the corpus under `docs/`, which no test reads, and by the running package, so a copy that
changes only the corpus does not run the tests again; the check outside the fixture
runner never uses it. An existing `.gitignore`, Makefile or workflow is refused like any
other target.

### Task 5 (2026-11-10)

The three files are package data under `src/trifecta/claude/`: the section, the skill,
which init writes as `.claude/skills/trifecta-planning/SKILL.md`, and the hook, written
as `.claude/hooks/trifecta_guard.py`. The registered command tries `python3`, then
`python`, then exits 2, since Windows often has only `python`; a refusal from the first
interpreter leaves the second an empty input, which it refuses too. The hook strips the
`\\?\` prefix Windows' `realpath` can return before it compares paths, since `relpath`
refuses to relate a prefixed path to one without, and an unrelated path counts as outside
the project. A shell command is refused when its text names `docs/superpowers` in any
case and with either separator, or holds a token that resolves there. Init reads an
existing CLAUDE.md or settings file through a handle it checks is the file `lstat` saw,
and the new file, created as `<name>.trifecta-new` with mode 0600 and then given the
original's mode bits, is moved over it only after the original's identity and
modification time are checked again. Tests reach the moments between validation and the
move through two more seams, `before_move` and `after_move`. The Windows CI job turns 8.3
names on for `C:`, where the tests' temporary directories are. Both interpreters run the
hook with `-I`, so nothing beside the script or in the environment changes what it
imports. The hook resolves a relative path against the session's `cwd`, reads a segment
up to any `:` so an NTFS stream name still names its directory, and refuses a path it
cannot relate to the project, such as a share path, when it names `docs/superpowers`
anywhere. Beside identity and modification time, init compares size and, on POSIX, the
change time, since ext4 gives a freed inode number to the next file and `utime` cannot
set a change time; it checks the new file is still the one it wrote before setting its
mode and before the move, and it refuses a read-only original.
