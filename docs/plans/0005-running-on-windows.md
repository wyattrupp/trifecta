---
status: active
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

- [ ] **1.1** Add `.gitattributes` holding `* text=auto eol=lf`; the index already holds LF, so no stored content changes.
- [ ] **1.2** Add the stage that reports the file missing or different, and any other tracked `.gitattributes`.
- [ ] **1.3** Make the fixture runner write mutated files with `newline=""`, so a fixture's CRLF stays CRLF and its LF stays LF on every platform.
- [ ] **1.4** Add the fixtures, and set the component's `spec` path.
:::

:::{task} Portable locations
:id: TASK_0005_02
:builds: COMP_PORTABLE_PATHS
:gate: The fixture that makes `docs/conf.py` log a Sphinx warning located at `/outside.md` is rejected under REQ_PORTABLE_FINDINGS; the corpus passes.
Fix the mapping, then catch what it misses.

- [ ] **2.1** Add the location helper to `tools/findings.py`, and route the Sphinx and Vale mappings through it.
- [ ] **2.2** Add the last stage that reports a location it could not map.
- [ ] **2.3** Pass `encoding="utf-8"` to every subprocess the check, the lifecycle checker and the fixture runner start.
- [ ] **2.4** Add the fixture, and set the component's `spec` path.
:::

:::{task} Vale setup
:id: TASK_0005_03
:builds: COMP_VALE_SETUP
:gate: The fixtures that drop a platform's row, name a file of another form, give a hash of the wrong length, and track a file under `bin/`, are rejected under REQ_PLATFORM_TOOLCHAIN; `python tools/setup.py` installs a Vale that runs, on Linux and Windows.
Replace the Makefile download.

- [ ] **3.1** Write the table for the pinned version: download each of the five files, compute its SHA-256, compare it with Vale's checksum file, and record in the As built entry what was compared.
- [ ] **3.2** Write `tools/setup.py` as COMP_VALE_SETUP states.
- [ ] **3.3** Remove the Vale variables from the Makefile, make its `setup`, `check` and `fixtures` targets call the script, and make the toolchain stage check the table, report files tracked under `bin/`, and run the executable by its exact name.
- [ ] **3.4** Add the fixtures beside the existing lock fixture, and set the component's `spec` path.
:::

:::{task} Windows CI job
:id: TASK_0005_04
:builds: COMP_WINDOWS_CI
:gate: The `check-windows` job passes on a pull request, and fails on a commit that breaks the check.
The last task, so it also closes the design.

- [ ] **4.1** Add the `check-windows` job as COMP_WINDOWS_CI states, and set the component's `spec` path.
- [ ] **4.2** Push a commit that breaks the check, confirm the job fails, and drop the commit.
- [ ] **4.3** Add the `python` commands to the README beside the `make` targets.
- [ ] **4.4** Once the job has passed on main, ask wyatt to add `check-windows` to the main ruleset's required checks; with his yes, add it, with the integration of the existing `check` context, and update `.github/settings/rulesets.json`; without it, drop this step.
- [ ] **4.5** Mark DES_0006 implemented, check that every requirement of RFC_0006 has its fixture, and review this plan's As built k=2.
:::

## Review

:::{review} Correctness; security
:id: REV_PLAN_0005_1
:k: 2
:date: 2026-11-08
The review recorded as {need}`REV_RFC_0006_1` covered this document.
:::

## As built
