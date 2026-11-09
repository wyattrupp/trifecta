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

{need}`RFC_0006` and the MADRs that resolve its questions. Build this plan before task 1
of {need}`PLAN_0002`, whose review digest reads documents as text; the files this plan
writes stay in `tools/` until plan 0003 moves them into the package.

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
:gate: The fixtures that delete `.gitattributes`, that remove its LF line, and that save a plan with CRLF line endings, are rejected or pass as REQ_ONE_LINE_ENDING states; the corpus passes.
First, so every later diff is LF.

- [ ] **1.1** Add `.gitattributes` with `* text=auto eol=lf`, and renormalize the index in a commit that changes only line endings.
- [ ] **1.2** Add the stage that reports the file missing or without that line.
- [ ] **1.3** Convert CRLF to LF in the plan parser, the frontmatter reader and the fixture runner's anchors, and let a fixture write CRLF content.
- [ ] **1.4** Add the fixtures, and set the component's `spec` path.
:::

:::{task} Portable locations
:id: TASK_0005_02
:builds: COMP_PORTABLE_PATHS
:gate: The fixture that includes a file from outside `docs/` with a broken reference in it is rejected under REQ_PORTABLE_FINDINGS on Linux; the corpus passes.
Fix the mapping, then catch what it misses.

- [ ] **2.1** Strip the repository root in its native form and with forward slashes, and convert backslashes to forward slashes.
- [ ] **2.2** Add the last stage that reports a location starting at a drive, a root or a UNC prefix.
- [ ] **2.3** Add the fixture, and set the component's `spec` path.
:::

:::{task} Vale setup
:id: TASK_0005_03
:builds: COMP_VALE_SETUP
:gate: The fixtures that drop a platform's hash, give a hash of the wrong length, and give the version as a range, are rejected; `python tools/setup.py` installs a Vale that runs, on Linux and Windows.
Replace the Makefile download.

- [ ] **3.1** Write `tools/setup.py` with the table, copied from Vale's checksum file for the pinned version, for Linux, macOS and Windows on x86-64 and Linux and macOS on ARM.
- [ ] **3.2** Download into memory, compare the SHA-256, and extract only the executable member to `bin/` with the per-version stamp.
- [ ] **3.3** Make the Makefile's `setup` target call the script, and the toolchain stage check the table and find `vale` or `vale.exe`.
- [ ] **3.4** Move the Makefile fixtures for REQ_PINNED_TOOLCHAIN to the table, add the new ones, and set the component's `spec` path.
:::

:::{task} Windows CI job
:id: TASK_0005_04
:builds: COMP_WINDOWS_CI
:gate: The `check-windows` job passes on a pull request; with wyatt's yes, the main ruleset requires it.
The last task, so it also closes the design.

- [ ] **4.1** Add the `check-windows` job, with the permissions, checkout settings, pinned actions and base ref of the `check` job, running setup, the check and the fixtures as `python` commands.
- [ ] **4.2** Add the `python` commands to the README beside the `make` targets.
- [ ] **4.3** After the job has passed on main, and with wyatt's yes, add it to the main ruleset's required checks and to `.github/settings/rulesets.json`.
- [ ] **4.4** Mark DES_0006 implemented, check that every requirement of RFC_0006 has its fixture, and review this plan's As built k=2.
:::

## Review

## As built
