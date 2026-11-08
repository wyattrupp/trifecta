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

Each new requirement gets its negative fixture in the task that adds it, and each built
component gets its `spec` path in the same task. The unmutated corpus passes at the end
of every task. This plan is built before {need}`PLAN_0003`, which moves the files it
writes into a package.

## Tasks

:::{task} Review digest and review command
:id: TASK_0002_01
:builds: COMP_REVIEW_DIGEST, IF_REVIEW_DIGEST, COMP_REVIEW_COMMAND
:gate: The fixture that edits a reviewed sentence is rejected; the corpus passes with every review stamped.
The digest and the command land together, since adding the check makes every existing
review stale until it is stamped.

- [ ] **1.1** Compute a document's reviewed content and digest as IF_REVIEW_DIGEST states, in a module with no Sphinx import.
- [ ] **1.2** Add a `digest` field to the review type, and report REQ_REVIEW_CURRENT from the extension when no review of a relied-on document carries the current digest.
- [ ] **1.3** Write `tools/review.py`: print a document's digest, or append a review record with today's date, the lenses, k and the digest.
- [ ] **1.4** Stamp the digest on every existing review, each on the document it covers.
- [ ] **1.5** Add the fixture that edits a reviewed sentence of an accepted RFC.
:::

:::{task} Frozen resolved tasks
:id: TASK_0002_02
:builds: COMP_TASK_FREEZE
:gate: The fixtures that edit and that remove a task resolved at the base ref are rejected.
Extend the lifecycle checker that freezes MADRs.

- [ ] **2.1** Read each plan at the base ref with the plan parser, and collect its resolved tasks with their As built entries.
- [ ] **2.2** Report a resolved task whose text or entry differs from the base ref, or that is gone.
- [ ] **2.3** Add the two fixtures.
:::

:::{task} Dropped-step reasons
:id: TASK_0002_03
:builds: COMP_DROP_REASONS
:gate: The fixture that drops a step without citing it is rejected.
The last task of the plan, so it also closes the design.

- [ ] **3.1** Report a dropped step whose number does not occur in its task's As built entry.
- [ ] **3.2** Add the fixture.
- [ ] **3.3** Mark DES_0003 implemented, and check that every requirement of RFC_0003 now has its fixture.
:::

## Review

## As built
