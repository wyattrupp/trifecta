---
status: implemented
authors: [claude]
---
# Plans and reviews

:::{design}
:::

## Overview

Plans and reviews join the graph through the same three layers as everything else. The
ontology declares the plan, task and review types, the derived `reviewed_by` link, and
the schemas for plan cardinality and review records. A sphinx-free module reads a plan's
source: its tasks, their steps, the As built entries; the document extension reports what
it finds while the plan is read, and the two commands use the same module to write a
skeleton and to print the next step. The graph checker compares each planned design with
the tasks that build it.

A planning session writes an RFC, MADRs and this kind of design doc, then a plan with
`python tools/new.py plan <slug> --implements DES_NNNN`. A building session runs
`python tools/next.py <plan>` and ticks the step it finishes.

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

:::{component} Plan and review ontology
:id: COMP_PLAN_TYPES
:spec: docs/conf.py#def _same_file
:satisfies: REQ_PLAN_IMPLEMENTS, REQ_REVIEWED
:constrained_by: DEC_0008, DEC_0010
The plan, task and review need types; the `implements` and `builds` links; the derived
`reviewed_by` link on RFCs, design docs and plans; and the schemas for a plan's single
design and for review records.
:::

:::{component} Plan rules
:id: COMP_PLAN_RULES
:spec: ext/plans.py#def problems
:satisfies: REQ_TASK_ORDER, REQ_TASK_SHAPE, REQ_LINEAR_EXECUTION, REQ_AS_BUILT
:constrained_by: DEC_0009
:provides: IF_PLAN_SHAPE
Parses a plan's tasks, steps and As built entries, skipping code fences, and reports each
violation with its requirement and line. The document extension calls it for every plan.
:::

:::{component} Plan coverage checker
:id: COMP_PLAN_COVERAGE
:spec: tools/check_graph.py#def check_plans
:satisfies: REQ_DESIGN_BUILT
:constrained_by: DEC_0008
:consumes: IF_NEEDS_JSON
For each design doc that a draft, active or done plan implements, reports every component
and interface no task of those plans builds.
:::

:::{component} Skeleton command
:id: COMP_NEW_COMMAND
:spec: tools/new.py#def render
:constrained_by: DEC_0008, DEC_0009
:consumes: IF_PLAN_SHAPE
Writes a draft RFC, MADR, design doc or plan with the next number, today's date and every
section of its type, from the constants the check reads. A plan's first task builds every
element of its design.
:::

:::{component} Next-step command
:id: COMP_NEXT_COMMAND
:spec: tools/next.py#def main
:constrained_by: DEC_0009
:consumes: IF_PLAN_SHAPE
Prints an active plan's rules for every task and the whole task holding the first open
step, with that step marked.
:::

## Interfaces

:::{interface} Plan shape
:id: IF_PLAN_SHAPE
:spec: ext/plans.py#STEP_RE
:constrained_by: DEC_0009
The parsed form of a plan: tasks in document order with their options and steps, the H2
sections, and the As built entries. A step line MUST match `STEP_RE`, and readers MUST
take the first open step in document order as the next one.
:::

## Review
