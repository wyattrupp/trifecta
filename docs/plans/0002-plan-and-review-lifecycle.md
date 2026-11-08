---
status: active
authors: [claude]
created: 2026-11-08
---
# Plan and review lifecycle

:::{plan}
:implements: DES_0003
:::

## Read before starting

{need}`RFC_0003` and the MADRs that resolve its questions.

## Rules for every task

Each new requirement gets its negative fixture in the task that enforces it, and each
built component gets its `spec` path in the same task. The unmutated corpus passes at the
end of every task. An edit to the reviewed text of a relied-on document is reviewed k=2
and stamped in the same task; once task 1 lands, a stamp takes the digest the review
started from. This plan is built before {need}`PLAN_0003`, which moves the files it
writes into a package.

## Tasks

:::{task} Review digest and review command
:id: TASK_0002_01
:builds: COMP_REVIEW_DIGEST, IF_REVIEW_DIGEST, COMP_REVIEW_COMMAND
:gate: The fixtures that edit a reviewed sentence and that add prose to a Review section are rejected; the corpus passes with every review stamped.
The digest and the command land together, since adding the check makes every existing
review stale until it is stamped.

- [ ] **1.1** Compute the digest from the raw file exactly as IF_REVIEW_DIGEST states, in a module with no Sphinx import.
- [ ] **1.2** Add a `digest` field to the review type; report REQ_REVIEW_CURRENT from the extension when no review of a relied-on document carries the current digest, and when a Review section holds anything but review records.
- [ ] **1.3** Write `tools/review.py` with `digest <doc>` and `stamp <doc> --digest D --lenses L --k N`; `stamp` refuses a path that is not a typed document and a digest that no longer matches the file.
- [ ] **1.4** Review every relied-on document again k=2, taking each digest at the start, and stamp each review with it.
- [ ] **1.5** Add the two fixtures, and set the three elements' `spec` paths.
:::

:::{task} Frozen tasks and forward statuses
:id: TASK_0002_02
:builds: COMP_TASK_FREEZE
:gate: The fixtures that edit, remove, and move a task resolved at the base ref, that delete a plan holding one, and that move an implemented design back to approved, are rejected.
Extend the lifecycle checker that freezes MADRs.

- [ ] **2.1** List every plan under `docs/plans/` at the base ref, and collect each resolved task with its raw lines, step marks and As built entry.
- [ ] **2.2** Report a resolved task whose raw text, marks or entry differ now, or that is gone from its plan, including when the plan file is gone.
- [ ] **2.3** Compare each typed document's status with the base ref, and report a backward move.
- [ ] **2.4** Make CI fail a push whose base it cannot resolve, in place of falling back to `HEAD^` or to no base.
- [ ] **2.5** Add the five fixtures, and set the component's `spec` path.
:::

:::{task} Dropped-step citations and build state
:id: TASK_0002_03
:builds: COMP_DROP_REASONS, COMP_BUILD_STATE
:gate: The fixtures for a dropped step cited nowhere, cited only inside a longer number, an approved design with no live plan, and an implemented design element with no spec, are rejected.
The last task of the plan, so it also closes the design.

- [ ] **3.1** Report a dropped step of a resolved task whose `N.k` does not occur, as a whole number pair, in its task's As built entry.
- [ ] **3.2** Report an approved design doc that no draft, active or done plan implements, and an element of an implemented design doc with no `spec`.
- [ ] **3.3** Add the four fixtures, and set the two components' `spec` paths.
- [ ] **3.4** Update the docstring of `ext/plans.py` and the README, which call drop reasons a convention.
- [ ] **3.5** Mark DES_0003 implemented, check that every requirement of RFC_0003 has its fixture, and review this plan's As built k=2.
:::

## Review

:::{review} Correctness; security
:id: REV_PLAN_0002_1
:k: 2
:date: 2026-11-08
The review recorded as {need}`REV_RFC_0003_1` covered this document.
:::

## As built
