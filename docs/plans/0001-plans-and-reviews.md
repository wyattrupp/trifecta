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

{need}`RFC_0002` and the MADRs that resolve its questions.

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

:::{task} Fold in the k=2 review
:id: TASK_0001_05
:builds: COMP_PLAN_RULES, COMP_PLAN_TYPES, COMP_NEW_COMMAND, COMP_NEXT_COMMAND
:gate: The fixtures for every finding that a corpus mutation can show are rejected; the corpus passes.
Apply the findings of the review recorded in RFC_0002 that held up.

- [x] **5.1** Bound task blocks by MyST's closing colons, the next task or the next section, and report an unclosed task.
- [x] **5.2** Report checkboxes outside a task, a plan with no task, padded task and step numbers, and placeholders in an active or done plan.
- [x] **5.3** Exempt abandoned plans in the requirement text, and add Out of scope to RFCs and Risks to design docs.
- [x] **5.4** Reject documents outside the typed directories, and point the README away from the superpowers default paths.
- [x] **5.5** Give plan statuses, frontmatter parsing, the lint directories and the derived views one home each.
- [x] **5.6** Record the review in RFC_0002, DES_0002 and this plan, and add the fixtures.
:::

## Review

:::{review} Correctness; single source of truth and fidelity to the superpowers shapes
:id: REV_PLAN_0001_1
:k: 2
:date: 2026-11-08
The review recorded as {need}`REV_RFC_0002_1` covered this document.
:::

## As built

### Task 1 (2026-11-08)

sphinx-needs drops empty fields before it validates, so a `minItems` rule never sees an
empty `reviewed_by`. The schemas use `required`. The same gap was in REQ_DECISION_OPTIONS:
a decision with no `chooses` or no options passed. It now uses `required` too and has the
fixture `decision-options-no-choice`.

### Task 2 (2026-11-08)

The parser lives in its own module with no Sphinx import, so `tools/next.py` loads it
without Sphinx; `tools/new.py` also reads `DOC_TYPES` from the extension.
`doc-identity-gap` created MADR 0009, which now exists; it creates 0012.

### Task 3 (2026-11-08)

As designed.

### Task 4 (2026-11-08)

As designed.

### Task 5 (2026-11-08)

Two findings were not taken: duplicate directive options, which docutils already
rejects, and CRLF line endings, which Sphinx and `splitlines` normalize before the
parser sees them.

Found while verifying the skeletons: a frontmatter value holding `#` or a quote broke the
directive it is injected into, since MyST reads those as option syntax. The extension
now quotes such values; `tools/new.py` quotes the author it writes into the frontmatter.
