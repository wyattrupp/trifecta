---
status: accepted
date: 2026-11-13
decision-makers: [wyatt]
informed: [claude]
---
# Tampering with a recorder's state is accepted

:::{decision}
:chooses: OPT_0041_ACCEPT
:resolves: Q_NESTED
:driven_by: REQ_NESTED_RECORDING
:::

## Context and Problem Statement

{need}`DEC_0035` accepts, for the repository's own tests, the listed ways code can step
around a recorder's wrapper without replacing it. The security review of
{need}`PLAN_0008`'s task 3 found another the list does not hold: code in a recorded
process can reach a recorder's own state, through `sys.modules`, `gc.get_objects` or
`gc.get_referrers`, a frame from `sys._current_frames`, a traceback, or a function
`sys.settrace` or `sys.setprofile` installs, and change it, so a refused run reads as
storable. The single recorder of {need}`DES_0008` is open to the same.

## Decision Drivers

- A way around the recorder that the design does not list reopens {need}`DEC_0035`
- The largest saving in scope, which the nested recorder brings
- Refusing a call the repository's own tests or their tools make costs their reuse

## Considered Options

:::{opt} Accept and list it
:id: OPT_0041_ACCEPT
Tampering with a recorder's own state from inside the process joins the ways
{need}`DEC_0035` accepts for the repository's own tests, and the design lists it. Good,
because nothing the tests do is refused for it. Bad, because code that sets out to
defeat the recorder can, as it already could.
:::

:::{opt} Refuse what can be seen
:id: OPT_0041_REFUSE
The recorder refuses `gc.get_objects`, `gc.get_referrers`, `sys.settrace`,
`sys.setprofile` and `sys._current_frames`; `sys.modules` stays open. Good, because
the routes that raise an event close. Bad, because the open one still reaches every
recorder, and a coverage tool or a debugger under test is refused.
:::

:::{opt} Hold task 3
:id: OPT_0041_HOLD
Good, because no gap is accepted. Bad, because `test_build_reuse` and
`test_store_reuse` stay fresh.
:::

## Decision Outcome

Chosen option: {need}`OPT_0041_ACCEPT`, because wyatt, 2026-11-13, choosing from
Claude's recommendations: "Accept and list it (Recommended)", for the repository's own
tests, extending {need}`DEC_0035`.

## Consequences

- Good, because the nested recorder stores `test_build_reuse` as built.
- Bad, because a test that changes a recorder's state is stored on what it chose to leave, and no check finds it.
- Bad, because a way around a recorder that neither this list nor {need}`DEC_0035`'s holds, found later, reopens both.
