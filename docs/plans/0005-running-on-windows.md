---
status: done
authors: [claude]
created: 2026-11-08
---
# Running on Windows

:::{plan}
:implements: DES_0006
:::

## Read before starting

{need}`RFC_0006` and the MADRs that resolve its questions. Build this plan before
{need}`PLAN_0002`; the files it writes stay in `tools/` until plan 0003 moves them into
the package.

## Rules for every task

Each requirement gets its negative fixture in the task that enforces it, and each built
component gets its `spec` path in the same task. The unmutated corpus passes at the end of
every task, on Windows as well as Linux once task 4 lands. An edit to the reviewed text of
a relied-on document is reviewed k=2 and stamped in the same task. Changing a repository
setting waits for wyatt's yes.

## Tasks

:::{task} Line endings
:id: TASK_0005_01
:builds: COMP_LINE_ENDINGS
:gate: The fixtures that delete `.gitattributes`, change its line, add a `diff` attribute, and add a second `.gitattributes` under `docs/` are rejected under REQ_ONE_LINE_ENDING; the fixture that saves a plan with CRLF line endings and a step gap is rejected under REQ_TASK_SHAPE; the corpus passes.
First, so every later checkout is LF.

- [x] **1.1** Add `.gitattributes` holding `* text=auto eol=lf`; the index already holds LF, so no stored content changes.
- [x] **1.2** Add the stage that reports the file missing or different, and any other tracked `.gitattributes`.
- [x] **1.3** Make the fixture runner write mutated files with `newline=""`, so a fixture's CRLF stays CRLF and its LF stays LF on every platform.
- [x] **1.4** Add the fixtures, and set the component's `spec` path.
:::

:::{task} Portable locations
:id: TASK_0005_02
:builds: COMP_PORTABLE_PATHS
:gate: The fixture that makes `docs/conf.py` log a Sphinx warning located at `/outside.md` is rejected under REQ_PORTABLE_FINDINGS; the corpus passes.
Fix the mapping, then catch what it misses.

- [x] **2.1** Add the location helper to `tools/findings.py`, and route the Sphinx and Vale mappings through it.
- [x] **2.2** Add the last stage that reports a location it could not map.
- [x] **2.3** Pass `encoding="utf-8"` to every subprocess the check, the lifecycle checker and the fixture runner start.
- [x] **2.4** Add the fixture, and set the component's `spec` path.
:::

:::{task} Vale setup
:id: TASK_0005_03
:builds: COMP_VALE_SETUP
:gate: The fixtures that drop a platform's row, name a file of another form, give a hash of the wrong length, and track a file under `bin/`, are rejected under REQ_PLATFORM_TOOLCHAIN; `python tools/setup.py` installs a Vale that runs, on Linux and Windows.
Replace the Makefile download.

- [x] **3.1** Write the table for the pinned version: download each of the five files, compute its SHA-256, compare it with Vale's checksum file, and record in the As built entry what was compared.
- [x] **3.2** Write `tools/setup.py` as COMP_VALE_SETUP states.
- [x] **3.3** Remove the Vale variables from the Makefile, make its `setup`, `check` and `fixtures` targets call the script, and make the toolchain stage check the table, report files tracked under `bin/`, and run the executable by its exact name.
- [x] **3.4** Add the fixtures beside the existing lock fixture, and set the component's `spec` path.
:::

:::{task} Windows CI job
:id: TASK_0005_04
:builds: COMP_WINDOWS_CI
:gate: The `check-windows` job passes on a pull request, and fails on a commit that breaks the check.
The last task, so it also closes the design.

- [x] **4.1** Add the `check-windows` job as COMP_WINDOWS_CI states, and set the component's `spec` path.
- [x] **4.2** Push a commit that breaks the check, confirm the job fails, and drop the commit.
- [x] **4.3** Add the `python` commands to the README beside the `make` targets.
- [x] **4.4** Once the job has passed on main, ask wyatt to add `check-windows` to the main ruleset's required checks; with his yes, add it, with the integration of the existing `check` context, and update `.github/settings/rulesets.json`; without it, drop this step.
- [x] **4.5** Mark DES_0006 implemented, check that every requirement of RFC_0006 has its fixture, and review this plan's As built k=2.
:::

## Review

:::{review} Correctness; security
:id: REV_PLAN_0005_1
:k: 2
:date: 2026-11-08
The review recorded as {need}`REV_RFC_0006_1` covered this document.
:::

:::{review} Correctness; documentation standard
:id: REV_PLAN_0005_2
:k: 2
:date: 2026-11-09
Reviewed the task 4 As built entry, the ruleset mirror and the move to done. Not taken: a
`digest` on the design's reviews, since no document carries one yet and plan 0002 builds
that check.
:::

:::{review} Correctness; security
:id: REV_PLAN_0005_3
:k: 2
:date: 2026-11-09
:digest: e3ea1702d286f4984b97c826c676be448d8b9d1ada34959642446c9f3b49a4c5
:::

## As built

### Task 1 (2026-11-08)

"Tracked" in the stage means what git tracks or would track: committed, or untracked and
not ignored, since a fixture's created file is never committed in the copy; names compare
without case, as git on Windows and macOS reads them. The `.gitattributes` is compared
byte for byte. Sphinx turns CRLF into LF before the plan parser sees a line, so a step gap
alone is caught whatever the line ending; the CRLF fixture also ends the task's As built
heading with CRLF, whose pattern stops at the line end, and its new `only: true` key makes
the fixture runner fail it on any requirement but the expected one. A probe with that
heading broken was reported under REQ_AS_BUILT as well, and failed. `venv/` and `.venv/`
are ignored, so a local environment is not listed as files git would track.

### Task 2 (2026-11-08)

Every Python program the check starts also runs with `PYTHONIOENCODING=utf-8`, since a
child Python writes to a pipe in the locale's encoding, and every decode replaces a byte
it cannot read so a stray byte changes one character, not the run. `tools/new.py` reads
`git config` as UTF-8 too. Only a location the helper made relative has its separators
turned to slashes; any other location is left as it was, so a relative path with a
backslash is reported on Windows as on Linux. A location with no path, such as `(build)`
or `need:ID`, is left as it is; the guard reports only paths. Vale's findings stay located
in the built lint page, as before this plan; mapping them to the source document is not
part of it. Messages may still name an absolute path; the requirement covers locations.

### Task 3 (2026-11-08)

The five 3.13.0 files were downloaded on their own and hashed; each SHA-256 matched
`vale_3.13.0_checksums.txt` from the same release, and each archive's listing showed one
top-level regular `vale`, or `vale.exe` in the zip. The table also holds each file's size,
which the twice-the-size read limit needs. `tools/toolchain.py` holds the executable's
path and the file-name suffix per platform, for the script and the check alike, so the
check never imports the script: it reads the script with `ast`, holds `VALE_VERSION`,
`VALE_FILES`, `RELEASES` and `HOSTS` to one top-level binding each that nothing later
changes, and holds the address and hosts to exact values. "Tracked under `bin/`" means
what git tracks or would track, as in task 1, so its fixture removes `bin/` from
`.gitignore`; setup itself refuses to run while git tracks anything there, refuses a
linked executable or stamp, and keys its stamp by platform. The Makefile gains a `vale`
target, which `check` and `fixtures` depend on, running the script with `--vale-only`. CI
sets `GIT_LFS_SKIP_SMUDGE`, since the attribute rule detects a change only after checkout.
Setup ran on Windows here: it fetched, verified and installed `bin/vale.exe`, ran it, and
reused it on a second run; the check and every fixture then passed on Windows with Vale.
On pull request #9, the Linux job's `make setup` ran the script and the Linux and
Windows jobs both passed. GitHub then answered two downloads with `504`, so setup retries
a download that fails on GitHub's side, a server error or a dropped connection, three
times after 5, 15 and 45 seconds; a refused redirect or a bad hash is never retried.

### Task 4 (2026-11-09)

Both jobs passed on pull request #9 and on main. For step 4.2 a commit that broke the
`.gitattributes` was pushed, both jobs failed under REQ_ONE_LINE_ENDING, and a following
commit reverted it, so both commits stay in main's history. wyatt said "Yes, require it"
in the session on 2026-11-09, so the main ruleset requires `check-windows` beside
`check`, both with integration 15368, GitHub Actions, and
`.github/settings/rulesets.json` holds the same rule. Each requirement of RFC_0006 has at
least one fixture. Some clauses have none: REQ_PORTABLE_FINDINGS's fixture covers a
location outside the repository, not a backslash, a `..` segment or UTF-8 output, and no
REQ_ONE_LINE_ENDING fixture shows a reader treating CRLF as LF; the CRLF step-gap fixture
does that under REQ_TASK_SHAPE.
