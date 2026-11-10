---
status: implemented
authors: [claude]
---
# Plan and review lifecycle

:::{design}
:::

## Overview

These additions hold plans, reviews and statuses to their past. A digest module reduces a
raw document to its reviewed content and hashes it; the document extension compares that
hash with the `digest` of the document's reviews and keeps the Review section to review
records, and a command stamps a review with the digest the reviewer was given. The
lifecycle checker, which already freezes MADRs against a base ref, also compares every
task resolved at that ref and every document's status with the current tree. The plan
rules check that each dropped step is cited in its task's As built entry. The graph
checker requires a live plan for each approved design and a `spec` on each element of an
implemented one.

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

:::{component} Review digest
:id: COMP_REVIEW_DIGEST
:spec: ext/digest.py#def digest
:satisfies: REQ_REVIEW_CURRENT
:constrained_by: DEC_0011
:provides: IF_REVIEW_DIGEST
Computes a document's reviewed content and its SHA-256 from the raw file, reports an
accepted, approved, implemented, active or done document none of whose reviews carries
that digest, or whose Review section it cannot find, and reports anything but a review
record in a Review section. It reads headings, code fences, directives and HTML blocks
with MyST's parser, set up with the build's extensions, so the sections and blocks it finds
are the ones Sphinx renders. A review record is a closed, top-level `review` directive
whose body holds its options and plain paragraphs; only a `digest` among its options
counts, and anything else in the section, a second Review section included, is reported.
A plan's As built section opens no fence, directive or HTML block at any depth, since it is
outside the digest and a block there could define a need.
:::

:::{component} Review command
:id: COMP_REVIEW_COMMAND
:spec: tools/review.py#def stamp
:constrained_by: DEC_0011
:consumes: IF_REVIEW_DIGEST
`review digest <doc>` prints the digest when a review starts; `review stamp <doc>` appends
a review record with today's date, the lenses, k and the digest it is given, and refuses
when the file's digest no longer matches or the path is not a typed document.
:::

:::{component} Lifecycle extension
:id: COMP_TASK_FREEZE
:spec: tools/check_lifecycle.py#def check_tasks
:satisfies: REQ_FROZEN_TASKS, REQ_STATUS_FORWARD
:constrained_by: DEC_0012
:consumes: IF_PLAN_SHAPE
Reads every plan under `docs/plans/` at the base ref, and reports a task resolved there
whose raw text, step marks or As built entry differ now, or that is gone from its plan.
Compares each typed document's status with the base ref and reports a backward move.
It reads each status with the frontmatter's YAML loader, and reports a frontmatter key
given twice. Statuses rank per type: an RFC's draft, review, accepted; a design doc's
draft, approved, implemented; a plan's draft, active, done. A move to a lower rank is
backward, and so is a typed document that is gone from the tree after being accepted,
approved, implemented, active or done at the base ref. A move into rejected, withdrawn,
obsolete or abandoned is outside this rule, and a move out of one of them, into any
other status, is reported as backward.
:::

:::{component} Drop-reason rule
:id: COMP_DROP_REASONS
:spec: ext/plans.py#def cited
:satisfies: REQ_DROP_REASONS
:constrained_by: DEC_0009
:consumes: IF_PLAN_SHAPE
Reports a dropped step of a resolved task whose number `N.k` does not occur in its task's
As built entry as a whole number pair. An occurrence counts when it is not preceded by a
digit or by a digit and a dot, and not followed by a digit or by a dot and a digit, so a
period that ends a sentence after it still counts.
:::

:::{component} Build-state rules
:id: COMP_BUILD_STATE
:spec: tools/check_graph.py#def check_build_state
:satisfies: REQ_APPROVED_IS_PLANNED, REQ_IMPLEMENTED_HAS_SPEC
:constrained_by: DEC_0008
:consumes: IF_NEEDS_JSON
Reports an approved design doc that no draft, active or done plan implements, and a
component or interface of an implemented design doc with no `spec`.
:::

## Interfaces

:::{interface} Review digest
:id: IF_REVIEW_DIGEST
:spec: ext/digest.py#def reviewed_content
:constrained_by: DEC_0011
The digest is computed from the raw file, which MUST be read as UTF-8 with a leading byte
order mark dropped, and each CRLF and each lone CR read as LF. The line YAML reads as the
frontmatter's one `status` key, when the key and its value fill that line alone, every `:spec:` line that is an option line of a `component` or
`interface` directive, in the run of option lines right after its opener, and the Review
section, from its H2 line up to the next H2 or the end of the file, MUST be removed, where
H2 headings, code fences and directives are those MyST's parser finds with the build's
extensions in the file with its frontmatter block blanked, as the build reads it; no other `:spec:` line is removed. For a plan, the As built section MUST
be removed the same way and the mark of every step line read as open. Each remaining line
MUST be stripped of trailing spaces and tabs and the lines MUST be joined with a single
newline; trailing empty lines MUST then be removed, so the text has no final newline. The
digest MUST be the lowercase hex SHA-256 of that text encoded as UTF-8.
:::

## Risks

A normalisation bug would make every review stale at once; the fixtures cover an edit that
changes the digest, and the corpus itself, with ticked steps and `spec` paths added after
review, covers the edits that do not. Adding the digest makes every review stale until it
is stamped, so the plan reviews the corpus again in the same task. CI freezes history only
when it can resolve a base, so a push whose base cannot be resolved fails, and the main
ruleset refuses force pushes.

Whoever stamps a review records it, so the digest proves which text a record names, not
that the text was read ({need}`DEC_0011`). `spec` lines are outside the digest, so a
changed `spec` path is not reviewed again. A move into rejected, withdrawn, obsolete or
abandoned is not held by the forward rule, though a move out of one is, and it drops a
design's requirements from the fixture audit. Required checks are not strict, a setting that awaits wyatt's
ruling, so a pull request is checked against the base it was last run on, and the push
check on main reports what that missed.

## Review

:::{review} Correctness; security
:id: REV_DES_0003_1
:k: 2
:date: 2026-11-08
The review recorded as {need}`REV_RFC_0003_1` covered this document.
:::

:::{review} Correctness; security
:id: REV_DES_0003_2
:k: 2
:date: 2026-11-09
:digest: 7aacfd80b169d170004caabf723a2deb83527ccf0dfe90d7165c476bb9904b03
:::

:::{review} Correctness; security
:id: REV_DES_0003_3
:k: 2
:date: 2026-11-09
:digest: 70afc386c1bd43e43c630f55483b0638a5162484649023c26765dc7b5aca4732
:::

:::{review} Fidelity to evidence; documentation standard
:id: REV_DES_0003_4
:k: 2
:date: 2026-11-09
:digest: 5099ac9b4050f81146f9d72f62402f317fa5f7c051b7bf6ba178c84e0d35dae6
The overview and risks after the design was built, with {need}`REV_PLAN_0002_3`.
:::
