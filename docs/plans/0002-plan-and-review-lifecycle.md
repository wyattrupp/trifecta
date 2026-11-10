---
status: done
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

- [x] **2.1** List every plan under `docs/plans/` at the base ref, and collect each resolved task with its raw lines, step marks and As built entry.
- [x] **2.2** Report a resolved task whose raw text, marks or entry differ now, or that is gone from its plan, including when the plan file is gone.
- [x] **2.3** Compare each typed document's status with the base ref, and report a backward move.
- [x] **2.4** Make CI fail a push whose base it cannot resolve, in place of falling back to `HEAD^` or to no base.
- [x] **2.5** Add the five fixtures, and set the component's `spec` path.
:::

:::{task} Dropped-step citations and build state
:id: TASK_0002_03
:builds: COMP_DROP_REASONS, COMP_BUILD_STATE
:gate: The fixtures for a dropped step cited nowhere, cited only inside a longer number, an approved design with no live plan, and an implemented design element with no spec, are rejected.
The last task of the plan, so it also closes the design.

- [x] **3.1** Report a dropped step of a resolved task whose `N.k` does not occur, as a whole number pair, in its task's As built entry.
- [x] **3.2** Report an approved design doc that no draft, active or done plan implements, and an element of an implemented design doc with no `spec`.
- [x] **3.3** Add the four fixtures, and set the two components' `spec` paths.
- [x] **3.4** Update the docstring of `ext/plans.py`, which calls drop reasons a convention.
- [x] **3.5** Mark DES_0003 implemented, check that every requirement of RFC_0003 has its fixture, review this plan's As built k=2, and set this plan's status to done.
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

:::{review} Fidelity to evidence; documentation standard
:id: REV_PLAN_0002_3
:k: 2
:date: 2026-11-09
:digest: e5c17a61d8fbc043fa5a3ae7a184342535e55a8da8d989edb99a102a922a7b3b
The As built entries of tasks 1 to 3, read against the code, the fixtures and the
merged pull requests; what held up is in the Task 3 entry.
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

The code review of the task, k=2 and then twice more on its fixes, found that reading
Markdown with patterns let a pull request hide a heading or a block from the digest while
the build still rendered it: a lone CR, a backtick in a fence's info string, a blockquoted
or list-indented directive, a heading in an HTML comment, a no-break space after a fence
closer, and a `status:` line inside another frontmatter value. The digest now reads
headings, fences, directives and HTML blocks with MyST's own parser, set up with the
extensions `docs/conf.py` takes from `ext/digest.py`, on the file with its frontmatter
blanked as the build reads it; it leaves out only the line YAML reads as the `status` key;
it fails closed when it finds no Review section; and a review record is a closed top-level
directive whose body holds options and plain paragraphs with no raw HTML. DES_0003's
component and interface say so. Its last edits follow the fixes the two reviewers stated
and were checked by a probe that runs each exploit, with no further pass. Each exploit has
a fixture.

### Task 2 (2026-11-09)

The lifecycle checker reads every status with the frontmatter's YAML loader, which now
refuses a key given twice and an unhashable key, so the build and the checker read one
status; the MADR freeze leaves out only the line YAML reads as the status key, which
closes a duplicate `status` that read as proposed to the old checker and accepted to the
build. A document is its number: a renamed document is still compared, so a rename cannot
revive one that left by an exit or hide a backward move, and a task in a renamed plan is
not moved. A status that can be read at the base and not now counts as a backward move.
A base directory that is absent lists nothing; any other git failure is reported, not
read as empty. Beyond the five fixtures the step names: an edited As built entry, a
status-looking line inside another frontmatter value, a duplicate frontmatter key, a
renamed plan set back to draft, and an unreadable status. The CRLF step-gap fixture
allows REQ_FROZEN_TASKS, since its renumbered step is in a resolved task. Not taken from
the code review: a second `## As built` or a second task with a resolved task's ID, since
REQ_SECTION_SKELETON and REQ_TASK_ORDER fail the build on each; the pull request's own
checker running in CI, which awaits a ruling.

### Task 3 (2026-11-09)

The plan parser keeps each As built entry's text, from its heading to the next H3 or the
end of the section, without its code, HTML comments or link targets, and `cited` reads
`N.k` as a whole pair: `13.1`, `1.20` and `1.2.3` do not cite `1.2`, and a sentence's
closing period does not stop a citation. A line that looks like a step, with more than one
space after its bullet or more than one character in its box, is reported as a malformed
step. The build-state rules run in the graph checker over `needs.json`, and a `spec` of
spaces alone names nothing. The fixture audit confirms that every requirement of RFC_0003
has its fixture now that DES_0003 is implemented. Step 3.4 also named the README, which
never called drop reasons a convention, so only the docstring of `ext/plans.py` says
otherwise now. The review of this As built is recorded as REV_PLAN_0002_3.

The entries for tasks 1 and 2 were frozen when they merged, so their corrections are here.
Task 1 cites {need}`DEC_0011` for reviewer identity: that MADR makes approval of the pull
request the proof of review, and k is the reviewer's statement, which the check does not
test. Its claim that each exploit has a fixture held for all but two, a list-indented
directive and a status-looking line inside another frontmatter value; both now have one.
Task 2's fixture for that line indents it, so the checker before task 2 would have caught
it too; the new digest fixture puts it at the start of a line. A failed test of whether a
base directory exists reads as absent, after the base itself resolves; only a failed
listing is reported. Not taken from this task's code review, for a ruling: a design doc
set straight to implemented needs no live plan, a `spec` may name a whole file, and a
citation shows a reason is given, not what it says.
