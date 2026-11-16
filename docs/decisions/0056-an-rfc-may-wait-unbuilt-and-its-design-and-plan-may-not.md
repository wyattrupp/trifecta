---
status: accepted
date: 2026-11-15
decision-makers: [wyatt]
informed: [claude]
---
# An RFC may wait unbuilt, and its design and plan may not

:::{decision}
:chooses: OPT_0056_RFC_WAITS
:resolves: Q_UNBUILT_DESIGN
:::

## Context and Problem Statement

{need}`RFC_0010` records that the book it reads documents only what has been built, and
that this holds here in part: an accepted RFC is intent kept where a session can read
it, which the gap calls for, and only the design approved ahead of the build is at
fault. {need}`DEC_0051` already cuts what a design holds before the code to names and
links. What is open is a spec that is accepted and approved and then not built.

Measured on 2026-11-15 at commit `50ff955`, there are two:

| Reading | Research rigor | Diagrams |
| --- | --- | --- |
| RFC, design doc and plan | {need}`RFC_0005`, {need}`DES_0005`, {need}`PLAN_0004` | {need}`RFC_0007`, {need}`DES_0007`, {need}`PLAN_0006` |
| Their statuses | accepted, approved, draft | accepted, approved, active |
| Steps of the plan ticked | 0 of 28 | 0 of 15 |
| Words in the RFC, the design doc and the plan | 1,850, 1,555 and 1,494 | 896, 1,243 and 777 |
| Requirements in the RFC | 11 | 3 |
| Questions in the RFC, and those a decision record resolves | 6 and 6 | 2 and 2 |
| First and last commit to the three files | 2026-11-08 and 2026-11-09 | 2026-11-08 and 2026-11-09 |

Both were written on 2026-11-08 and none of their six files has changed since the day
after. {need}`RFC_0008` was first committed on 2026-11-10 and {need}`RFC_0009` on
2026-11-11, and the plans of both were done by 2026-11-14. The six files hold 7,815
words, 5,069 of them in the two design docs and the two plans. The statuses that exist
already cover every option below: an RFC can be withdrawn, a design doc can be draft or
obsolete, and a plan can be abandoned. {need}`REQ_APPROVED_IS_PLANNED` asks only that an
approved design doc has a plan, and a plan with no step ticked meets it for as long as
it stands.

How each was read: statuses from each file's front matter; steps by their checkboxes;
words by `wc -w`; commits by `git log` on each file.

One limit. The repository is eight days old, so "not built" here is six days without a
change while two later specs were built. It is not a record that either was given up.

### The ask as put

What was put to wyatt, copied from the transcript of the session. An option marked
"(Recommended)" was the one recommended. The readings shown beside a question in the
same message were those of the table above, save where the outcome says a figure was
wrong; they are not copied again.

```text
Question: Q_UNBUILT_DESIGN: what becomes of an accepted RFC and approved design that
nothing builds? Evidence: 2 such specs (research rigor, diagrams), 0 of 43 plan steps
ticked, untouched since 2026-11-09 while 2 later RFCs were built; 7,815 words, 5,069 of
them design and plan.

Options, in the order shown:
- RFC waits, design and plan do not (Recommended): Accepted RFC and its decision records
  stay as record of intent. A design is approved and a plan written only when the build
  starts; an approved design with no step ticked goes back to draft and its plan to
  abandoned. Applies to both specs now.
- Withdraw the whole spec: RFC withdrawn, design obsolete, plan abandoned, until someone
  takes it up again. Shortest corpus; the intent leaves the accepted set though its
  decision records stay.
- Leave as is: An accepted and approved spec may wait unbuilt with no limit. Nothing
  changes; 5,069 words of how-to stay approved for code that does not exist.
- Rule each case apart: No general rule. Diagrams gets settled with DEC_0054's
  supersession; research rigor is asked separately.

Answer: RFC waits, design and plan do not (Recommended)
```

## Decision Drivers

- What is left of the book's fault in {need}`RFC_0010`: the description of a solution
  approved ahead of a build that has not started
- {need}`DEC_0051`: before the code a design is names and links
- An accepted RFC and its decision records are intent a session cannot recall and has to
  be able to read
- {need}`DEC_0054` already contradicts a requirement of {need}`RFC_0007`

## Considered Options

:::{opt} The RFC waits, the design and the plan do not
:id: OPT_0056_RFC_WAITS
An accepted RFC and its decision records stand for as long as nothing builds them. A
design doc is approved and a plan is written only when the build starts; an approved
design doc whose plan has no step ticked goes back to draft, and that plan is abandoned.
Good, because the intent stays where a session reads it, and what is approved is only
what is being built. Good, because it uses statuses that exist. Bad, because the work of
approving a design is done again when the build starts. Bad, because "when the build
starts" is not a thing the check can see until a step is ticked.
:::

:::{opt} Withdraw the whole spec
:id: OPT_0056_WITHDRAW
The RFC is withdrawn, the design doc made obsolete and the plan abandoned, until someone
takes the work up again. Good, because the corpus is shortest. Bad, because the
requirements leave the accepted set while the decision records that answer their
questions stay, with nothing accepted for them to answer.
:::

:::{opt} Leave as is
:id: OPT_0056_AS_IS
A spec may wait unbuilt, accepted and approved, with no limit. Good, because nothing
changes. Bad, because 5,069 words stay approved that describe code nobody has written.
:::

:::{opt} Rule each case apart
:id: OPT_0056_EACH
No general rule; each unbuilt spec is put to a person. Good, because the two differ.
Bad, because the next one is asked again from nothing.
:::

## Decision Outcome

Chosen option: {need}`OPT_0056_RFC_WAITS`, because wyatt, 2026-11-15, choosing from
Claude's recommendations with the readings above in the ask: "RFC waits, design and plan
do not (Recommended)".

## Consequences

- Good, because with {need}`DEC_0051` an approved design is always one whose build has
  begun.
- Bad, because nothing here has yet been applied: {need}`DES_0005` and {need}`DES_0007`
  are still approved, {need}`PLAN_0004` still draft and {need}`PLAN_0006` still active.
  Whether the check lets an approved design doc go back to draft was not tried.
- Bad, because the check does not yet hold the rule; {need}`REQ_APPROVED_IS_PLANNED`
  stands as written, and {need}`RFC_0010` has to gain a requirement before this binds
  anything.
- Bad, because {need}`RFC_0007` stays accepted with a requirement that {need}`DEC_0054`
  contradicts, and waiting does not mend that; it still has to be superseded.
- Bad, because how long an accepted RFC may wait is given no bound.
