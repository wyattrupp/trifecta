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
end of every task. A relied-on document is an accepted RFC, an approved or implemented
design doc, or an active or done plan. An edit to the reviewed text of a relied-on
document is reviewed k=2 and stamped in the same task; once task 1 lands, a stamp takes the digest the review
started from. This plan is built before {need}`PLAN_0003`, which moves the files it
writes into a package.

## Tasks

:::{task} Review digest and review command
:id: TASK_0002_01
:builds: COMP_REVIEW_DIGEST, IF_REVIEW_DIGEST, COMP_REVIEW_COMMAND
:gate: The fixtures that edit a reviewed sentence and that add prose to a Review section are rejected; the corpus passes with every review stamped.
The digest and the command land together, since adding the check makes every existing
review stale until it is stamped.

- [x] **1.1** Compute the digest from the raw file exactly as IF_REVIEW_DIGEST states, in a module with no Sphinx import.
- [x] **1.2** Add a `digest` field to the review type; report REQ_REVIEW_CURRENT from the extension when no review of a relied-on document carries the current digest, and when a Review section holds anything but review records.
- [x] **1.3** Write `tools/review.py` with `digest <doc>` and `stamp <doc> --digest D --lenses L --k N`; `stamp` refuses a path that is not a typed document and a digest that no longer matches the file.
- [x] **1.4** Review every relied-on document again k=2, taking each digest at the start, and stamp each review with it.
- [x] **1.5** Add the two fixtures, and set the three elements' `spec` paths.
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
- [ ] **3.4** Update the docstring of `ext/plans.py`, which calls drop reasons a convention.
- [ ] **3.5** Mark DES_0003 implemented, check that every requirement of RFC_0003 has its fixture, review this plan's As built k=2, and set this plan's status to done.
:::

## Review

:::{review} Correctness; security
:id: REV_PLAN_0002_1
:k: 2
:date: 2026-11-08
The review recorded as {need}`REV_RFC_0003_1` covered this document.
:::

:::{review} Correctness; security
:id: REV_PLAN_0002_2
:k: 2
:date: 2026-11-09
:digest: e5c17a61d8fbc043fa5a3ae7a184342535e55a8da8d989edb99a102a922a7b3b
:::

## As built

### Task 1 (2026-11-09)

The digest module reads the raw file as UTF-8 less a byte order mark, and reads CRLF as LF,
since the working tree on Windows held CRLF until it was checked out again under the
`.gitattributes`. A `:spec:` line leaves the digest only as an option of a component or
interface, so prose that starts the same way is still covered; the frontmatter is now read
through one function in `ext/plans.py`. `tools/new.py` leaves every Review section empty,
since prose there is reported. A third fixture holds requirement prose that starts with
`:spec:`. The fixture runner's new `allow` key names a requirement an `only` fixture's
mutation breaks of necessity: renumbering a step in a done plan changes its digest.

Step 1.4 reviewed all nineteen relied-on documents in three groups, each with a
correctness and a security pass; no pass came from another model lineage, since the local
model was unreachable. The findings that held up were applied, the edits were reviewed
again with both lenses, and that pass's own fixes were applied as it stated them before the
digests were taken. Code fixes taken with them: Vale exiting non-zero with no message is a
finding, a finding with a line break prints on one line, the fixture runner copies links as
links, and setup retries any connection error and finds a tracked `Bin/` without case.
Not taken, with the reason: a review record's body is the review's own notes
({need}`DEC_0010`), not reviewed content; a design states what its plan builds, so present
tense for unbuilt work stays; an active plan is reviewed and ready, and its Read section
orders the build; reviewer identity and k are attested by the stamper ({need}`DEC_0011`).
Left to task 2: reading status with the YAML loader, which closes a duplicate `status` key
that let a MADR read as proposed, and masking only the frontmatter status line. Left for a
ruling: the pull request's own checker, extension and workflow run in CI, so they can
change what checks them; required checks are not strict; a move into an exit status drops
a design's requirements from the fixture audit. Left to the plans that build them, for
their review before they are built: a survey has no status, so it is never relied on and
REQ_EVIDENCE_REVIEWED cannot hold as written; local data is hashed after git normalizes
its line endings; init's step that refuses an existing target contradicts its step that
leaves an existing settings file alone; a test's declaration of what it proves has no
form yet; the template repository's component has no artifact in this repository; the
first install's source is unstated; and a hook whose interpreter is missing exits with a
code that does not block. Found while running the fixtures: the runner copied the
repository by walking it, so a worktree that only `.git/info/exclude` ignores reached the
copy; it now copies the files git lists, as the check reads them. `reviewed-missing`
removes both of the design doc's review records.
