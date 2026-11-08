---
status: done
authors: [claude]
created: 2026-11-08
---
# Plans and reviews

:::{plan}
:implements: DES_0002
:::

## Read before starting

{need}`RFC_0002` for the requirements, {need}`DES_0002` for the components each task
builds, and the three MADRs that resolve the RFC's questions: {need}`DEC_0008`,
{need}`DEC_0009` and {need}`DEC_0010`. The superpowers spec and plan shapes in
gfl2_pmxview (`docs/superpowers/specs/2026-11-07-spec-plan-shapes-design.md` there) are
the shapes this adapts to the graph.

## Rules for every task

Each new requirement gets its negative fixture in the task that adds it. The unmutated
corpus passes at the end of every task.

## Tasks

:::{task} Plan and review ontology
:id: TASK_0001_01
:builds: COMP_PLAN_TYPES
:gate: The REQ_PLAN_IMPLEMENTS and REQ_REVIEWED fixtures are rejected; the corpus passes.
Declare the new types in `docs/conf.py` and adopt reviews across the corpus.

- [x] **1.1** Declare the plan, task and review types, and the `implements` and `builds` links.
- [x] **1.2** Derive `reviewed_by` on RFCs, design docs and plans from the review needs in the same file.
- [x] **1.3** Add the REQ_PLAN_IMPLEMENTS and REQ_REVIEWED schemas.
- [x] **1.4** Add a Review section to the RFC and design doc skeletons, and record the 2026-11-08 review in RFC_0001 and DES_0001.
- [x] **1.5** Add the plan frontmatter schema and the fixtures for both requirements.
:::

:::{task} Plan rules
:id: TASK_0001_02
:builds: COMP_PLAN_RULES, IF_PLAN_SHAPE
:gate: The REQ_TASK_ORDER, REQ_TASK_SHAPE, REQ_LINEAR_EXECUTION and REQ_AS_BUILT fixtures are rejected.
Write `ext/plans.py` and call it from the extension for every plan.

- [x] **2.1** Parse tasks, their options and steps, the H2 sections and the As built entries, skipping code fences.
- [x] **2.2** Report task order, task shape, linear execution and As built problems with their lines.
- [x] **2.3** Add the plans type to `DOC_TYPES` and call the rules from `on_source_read`.
- [x] **2.4** Add a fixture for each of the four requirements, and a second for a ticked step in a draft plan.
:::

:::{task} Plan coverage checker
:id: TASK_0001_03
:builds: COMP_PLAN_COVERAGE
:gate: The REQ_DESIGN_BUILT fixture is rejected.
Compare each planned design with the tasks that build it, after the build.

- [x] **3.1** Write `check_plans` in `tools/check_graph.py`, counting only draft, active and done plans.
- [x] **3.2** Add the fixture that drops one element from a task's `builds`.
:::

:::{task} Skeleton and next-step commands
:id: TASK_0001_04
:builds: COMP_NEW_COMMAND, COMP_NEXT_COMMAND
:gate: A skeleton of each type passes the check; `next` prints the right step for an open plan and refuses a draft.
Write the two commands from the shared constants.

- [x] **4.1** Write `tools/new.py` for RFCs, MADRs, design docs and plans.
- [x] **4.2** Write `tools/next.py`.
- [x] **4.3** Run the check over a skeleton of each type, and `next` over an open copy of this plan.
:::

## Review

## As built

### Task 1 (2026-11-08)

sphinx-needs drops empty fields before it validates, so a `minItems` rule never sees an
empty `reviewed_by`. The schemas use `required`. The same gap was in REQ_DECISION_OPTIONS:
a decision with no `chooses` or no options passed. It now uses `required` too and has the
fixture `decision-options-no-choice`.

### Task 2 (2026-11-08)

The parser lives in its own module with no Sphinx import so the commands can load it.
`doc-identity-gap` created MADR 0009, which now exists; it creates 0012.

### Task 3 (2026-11-08)

As designed.

### Task 4 (2026-11-08)

As designed.
