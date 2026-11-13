---
status: accepted
date: 2026-11-11
decision-makers: [wyatt]
informed: [claude]
---
# All eight modules are in scope, ordered by Linux seconds saved

:::{decision}
:chooses: OPT_0032_LINUX
:resolves: Q_SCOPE_MODULES
:driven_by: REQ_LIFT_PROVEN, REQ_REFUSALS_NAMED
:::

## Context and Problem Statement

Eight proof modules are never stored, and they hold most of the fixture step's test
time. wyatt, 2026-11-11: "they're all in scope, and ordered by highest possible
speedup". {need}`RFC_0009` measured, for each module, the copies of the 123 fixtures that
change none of the paths a trace of the module read, and the Linux seconds that saves.

## Decision Drivers

- Every module in scope
- The order follows the most a module can save
- A measure that exists today

## Considered Options

:::{opt} Linux seconds, summed over the copies
:id: OPT_0032_LINUX
The seconds a module would save on Linux once every reason in it is lifted: its CI
seconds times the copies that can reuse it, over 123. Good, because it is measured, from
a trace of each module. Bad, because Windows, the slower job, has its CI seconds
measured but no trace to bound each module's saving.
:::

:::{opt} Windows seconds, summed over the copies
:id: OPT_0032_WINDOWS
Good, because Windows is the slower job. Bad, because no trace of Windows exists, so
each bound needs new timing runs.
:::

:::{opt} The fixture step's wall time
:id: OPT_0032_WALL
Good, because it is what CI waits for. Bad, because copies run side by side, so a
module's share of it cannot be estimated before the module is built.
:::

## Decision Outcome

Chosen option: {need}`OPT_0032_LINUX`, because wyatt, 2026-11-11: "just make recommendations, and ask using ask user tool"; he chose "Linux summed seconds". The order is `test_build_reuse`,
`test_record`, `test_store_reuse`, `test_record_trace`, `test_init`, `test_package`,
`test_planning`, then what is left of `test_adoption`, whose guide test stays fresh by
{need}`DEC_0034`.

On the numbers after PR #34, which runs the test modules in only 39 copies, he chose,
wyatt, 2026-11-12, choosing from Claude's recommendations: "Re-rank and unhold", so the order is `test_build_reuse`, `test_record_trace`,
`test_record`, `test_init`, `test_store_reuse`, `test_planning`, `test_package`, then
what is left of `test_adoption`, as {need}`Q_SCOPE_MODULES` measures.

## Consequences

- Good, because the order is measured and can be measured again the same way.
- Good, because a lift shared by several modules is built when the first module in
  the order that can be stored needs it, as wyatt accepted ("Accept").
- Bad, because on the 2026-11-11 numbers `test_record_trace` and `test_init` differed by 14 seconds, less than the bounds could settle; on the 2026-11-12 numbers they are 2656 and 1839.
