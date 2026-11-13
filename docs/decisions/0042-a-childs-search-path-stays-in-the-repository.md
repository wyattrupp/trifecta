---
status: accepted
date: 2026-11-13
decision-makers: [wyatt]
informed: [claude]
---
# A child's search path stays in the repository

:::{decision}
:chooses: OPT_0042_INSIDE
:resolves: Q_NESTED
:driven_by: REQ_NESTED_RECORDING, REQ_REUSE_SOUND
:::

## Context and Problem Statement

A Python child imports from `PYTHONPATH` before `site` runs the recorder's `.pth` file:
the `encodings` package, then what the recorder's start source imports. The security
review of {need}`PLAN_0008`'s task 3 showed a child whose `PYTHONPATH` names a directory
holding such a module runs it unrecorded, and so do `PYTHONHOME`, `PYTHONPLATLIBDIR`,
`PYTHONSTARTUP` and `-X frozen_modules=off`. Refusing every `PYTHONPATH` refuses tests
that set it on purpose: `test_record`'s copy test, `test_planning`'s hook test with a
shadowed `json`, and the children `test_init` and the fixture runner start with the
package on the path.

## Decision Drivers

- No code runs before the recorder unseen
- A test that sets the search path to the repository's own code keeps its reuse

## Considered Options

:::{opt} Allow repository and prefix paths
:id: OPT_0042_INSIDE
A `PYTHONPATH` entry, its links resolved and an empty one read as the working
directory, is allowed when it lies under the repository root or the interpreter's
prefixes; the variable is recorded, and the check that nothing from outside them loaded
before the recorder started stays. Any other entry is refused, and so are
`PYTHONHOME`, `PYTHONPLATLIBDIR`, `PYTHONSTARTUP`, `PYTHON_FROZEN_MODULES` and
`-X frozen_modules=off`. Good, because the package's own path keeps its reuse. Bad,
because a shadow in a temporary directory, as `test_planning`'s, stays refused.
:::

:::{opt} Refuse all and fix the tests
:id: OPT_0042_FIX
Good, because the rule is the simplest. Bad, because each test that sets the path has to
change how it starts its child.
:::

:::{opt} Refuse all and leave them unstored
:id: OPT_0042_LEAVE
Good, because nothing changes in the tests. Bad, because `test_record`, `test_init` and
`test_planning` stay fresh for it.
:::

## Decision Outcome

Chosen option: {need}`OPT_0042_INSIDE`, because wyatt, 2026-11-13, choosing from
Claude's recommendations: "Allow repo/prefix paths (Recommended)"; as the option states,
a shadow in a temporary directory, as `test_planning`'s `json`, stays refused.

## Consequences

- Good, because a child started with the package's directory on its path is recorded as any other.
- Bad, because a test's path in a temporary directory, as `test_record`'s copy test names, keeps its module fresh.
- Bad, because a module that runs before the recorder and leaves no trace, its file and its entry in `sys.modules` both gone, is not found; {need}`DES_0009` states the limit.
