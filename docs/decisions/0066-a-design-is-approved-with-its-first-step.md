---
status: accepted
date: 2026-11-15
decision-makers: [wyatt]
informed: [claude]
---
# A design is approved with its first step

:::{decision}
:chooses: OPT_0066_WITH_FIRST_STEP
:resolves: Q_BUILD_START
:::

## Context and Problem Statement

{need}`REQ_APPROVED_IS_BUILDING` has an approved design doc implemented by a plan with a
step done. {need}`DEC_0056` noted that the check cannot see a build start until a step
is done, which leaves no moment at which a design could first be approved.

Measured on 2026-11-15 at commit `1ec2b54`, from the history of each design doc and of
the plan that implements it:

| Reading | Value |
| --- | --- |
| Design docs whose history holds a commit that set them to approved | 7 |
| Of those, approved in the commit that first added their plan | 7 |
| Of those, since built | 5 |
| For those five, the time from approval to the first step done | 40 minutes, 2 hours 39, 2 hours 41, and twice about 26 hours |
| Rules that stop a plan implementing a draft design doc | none found |

How each was read: the approving commit by `git log -S`; the first step done as the
first commit of the plan in which a step is marked done; the rules by a search of the
plan rules and the graph checker.

So every design was approved before any step, and the requirement as written would have
failed each of the seven for the time between. One limit: the times are commit dates,
which a rebase can move.

{need}`REQ_COVERAGE` was not in the ask. It has every requirement of an accepted RFC
satisfied by a component of an approved or implemented design doc, so a design doc that
is in draft, under this record or under {need}`DEC_0056`, leaves the requirements of its
RFC uncovered. That holds for every option below alike.

### The ask as put

What was put to wyatt, copied from the transcript of the session. An option marked
"(Recommended)" was the one recommended. The readings shown beside a question in the
same message were those of the table above, save where the outcome says a figure was
wrong; they are not copied again.

```text
Question: Q_BUILD_START: how does a design get approved if approval needs a step done?
Evidence: all 7 designs were approved in the commit that first added their plan; first
step came 40 minutes to 26 hours later; nothing stops a plan implementing a draft
design.

Options, in the order shown:
- Approve with the first step (Recommended): A design stays draft, names only, while its
  plan is written and reviewed. It becomes approved in the change that marks the first
  step done. Approved then always means being built, with no gap.
- Approved may wait while plan is draft: Approval as now; the step test applies only
  once the plan is active. A plan left in draft lets a design sit approved unbuilt,
  which is the case DEC_0056 ruled against.
- Drop the step test: Approved needs only a plan, as now. Returning an idle design to
  draft is done by hand when someone notices. No check holds DEC_0056.

Answer: Approve with the first step (Recommended)
```

## Decision Drivers

- {need}`DEC_0056`: an approved design is one being built
- {need}`DEC_0051`: before the code a design is names and links, which a draft can hold
- A rule with a gap in it that every design falls into is not one a check can hold

## Considered Options

:::{opt} Approved with the first step
:id: OPT_0066_WITH_FIRST_STEP
A design doc stays draft, names only, while its plan is written and reviewed, and
becomes approved in the change that marks the first step done. Good, because approved
then means being built with no time between. Good, because nothing stops a plan
implementing a draft today. Bad, because a plan is reviewed against a design that is
not yet approved. Bad, because {need}`REQ_COVERAGE` has to be amended.
:::

:::{opt} Approved may wait while the plan is draft
:id: OPT_0066_PLAN_DRAFT
The step test applies only once the plan is active. Good, because approval stays where
it is. Bad, because a plan left in draft keeps a design approved and unbuilt, which is
what {need}`DEC_0056` ruled against.
:::

:::{opt} No step test
:id: OPT_0066_NO_TEST
An approved design needs only a plan, as now. Good, because nothing changes. Bad,
because no check then holds {need}`DEC_0056`.
:::

## Decision Outcome

Chosen option: {need}`OPT_0066_WITH_FIRST_STEP`, because wyatt, 2026-11-15, choosing from
Claude's recommendations with the readings above in the ask: "Approve with the first step
(Recommended)". The ask did not name {need}`REQ_COVERAGE`; it was found afterwards and is
recorded above.

## Consequences

- Good, because {need}`REQ_APPROVED_IS_BUILDING` can be held as written.
- Bad, because {need}`REQ_COVERAGE` has to be amended so that a draft design doc's
  components cover a requirement, or an accepted RFC is reported the day it is accepted.
- Bad, because what review a draft design of names gets before a plan is built on it is
  not settled.
