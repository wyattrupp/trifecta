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

{need}`RFC_0004` and the MADRs that resolve its questions. {need}`PLAN_0002` is built
first: this plan moves the files it writes.

## Rules for every task

Each new requirement gets its negative fixture or its named test in the task that
enforces it, and each built component gets its `spec` path in the same task. The
unmutated corpus passes at the end of every task. Creating or changing anything outside
this repository, such as a release or a repository on GitHub, waits for wyatt's yes.

## Tasks

:::{task} Toolchain package
:id: TASK_0003_01
:builds: COMP_PACKAGE, IF_CLI
:gate: `trifecta fixtures` from an installed package rejects every fixture, and the corpus passes.
Move the code without changing what it checks.

- [ ] **1.1** Move the extension, schemas, plan rules, tools, Vale styles and configurations into `src/trifecta/`, with a `pyproject.toml` whose build backend is pinned in the lock.
- [ ] **1.2** Add the `trifecta` command with `check`, `fixtures`, `new`, `next` and `review`, reading the corpus from the working directory, and make the Makefile call it.
- [ ] **1.3** Move the `spec` paths of DES_0001, DES_0002 and DES_0003 to the new files.
:::

:::{task} Self-test switch and test proofs
:id: TASK_0003_02
:builds: COMP_SELF_TEST_SCOPE, COMP_TEST_PROOFS
:gate: The fixtures for REQ_SELF_TESTS_SCOPED and REQ_PROVEN_BY_TEST are rejected.
Make the fixture audit this repository's alone, and let tests prove what fixtures cannot.

- [ ] **2.1** Add the configuration value that turns on the fixture audit, set only in this repository's `docs/conf.py`.
- [ ] **2.2** Count a `unittest` module under `tests/` that declares the requirements it proves as their proof, and run those tests in the check.
- [ ] **2.3** Name tests as proof in the text of REQ_FIXTURE_PER_INVARIANT.
- [ ] **2.4** Add the fixtures for REQ_SELF_TESTS_SCOPED and REQ_PROVEN_BY_TEST.
:::

:::{task} Init command
:id: TASK_0003_03
:builds: COMP_INIT_COMMAND
:gate: The test for REQ_INIT_PASSES passes.
Write the adopting repository's starting point.

- [ ] **3.1** Write `trifecta init`: the configuration that loads the package, the index, the typed directories, the Makefile, the CI workflow and the lock line.
- [ ] **3.2** Refuse to overwrite an existing file, and list what was written.
- [ ] **3.3** Add the test that runs init in an empty repository, writes a draft of each type with `trifecta new`, and passes the check.
:::

:::{task} Planning default
:id: TASK_0003_04
:builds: COMP_PLANNING_DEFAULT
:gate: The test for REQ_PLANNING_DEFAULT passes, and init installs all three files.
The three files init adds for Claude Code.

- [ ] **4.1** Write the CLAUDE.md section: a spec is an RFC, MADRs and a design doc from `trifecta new`; a plan is `trifecta new plan`; a build follows `trifecta next`; each document is reviewed k=2 and stamped with `trifecta review` before it is relied on.
- [ ] **4.2** Write the project skill that the brainstorming and writing-plans skills defer to for where specs and plans go and what shape they take.
- [ ] **4.3** Write the PreToolUse hook that refuses a write under `docs/superpowers/` and names `trifecta new`.
- [ ] **4.4** Add the test that feeds the hook a write under `docs/superpowers/` and one under `docs/rfcs/`, and checks init installs the three files.
:::

:::{task} Release and template repository
:id: TASK_0003_05
:builds: COMP_RELEASE, COMP_TEMPLATE_REPO
:gate: A repository created from the template passes its CI with the released wheel.
The first steps outside this repository; each waits for wyatt's yes.

- [ ] **5.1** Add the workflow that builds the wheel on a version tag and attaches it, with its SHA-256, to the release.
- [ ] **5.2** Ask wyatt whether to make this repository public or to authenticate wheel downloads, then tag the first release.
- [ ] **5.3** Create the template repository from `trifecta init` output pinned to that release, and mark it a template.
- [ ] **5.4** Create a repository from the template and confirm its CI passes.
:::

:::{task} Adoption guide
:id: TASK_0003_06
:builds: COMP_ADOPTION_GUIDE
:gate: The test that runs the README's adoption commands passes.
The last task, so it also closes the design.

- [ ] **6.1** Rewrite README.md to lead with "Run this in your repo": from the template, or with `trifecta init` in an existing repository; the lock line; `make check` and CI; planning with Claude Code. Then developing trifecta itself.
- [ ] **6.2** Add the test that runs the guide's commands in an empty directory against the built wheel.
- [ ] **6.3** Mark DES_0004 implemented, and check that every requirement of RFC_0004 has its fixture or test.
:::

## Review

## As built
