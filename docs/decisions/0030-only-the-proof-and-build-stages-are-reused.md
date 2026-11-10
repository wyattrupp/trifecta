---
status: accepted
date: 2026-11-10
decision-makers: [claude]
informed: [wyatt]
---
# Only the proof and build stages are reused

:::{decision}
:chooses: OPT_0030_PROOFS_AND_BUILD
:resolves: Q_REUSE_STAGES
:driven_by: REQ_REUSE_SCOPED, REQ_REUSE_SOUND
:::

## Context and Problem Statement

Every stage of the check could carry a manifest, but each reused stage is one more place a
stale result could hide, and one more thing to store and restore. The profile of
2026-11-10 (RFC 0008) put the tests at 31.6 of 46 seconds and the Sphinx build at 9.2,
and every other stage at 2.9 seconds or less.

## Decision Drivers

- Reuse only where the measured time is
- Anything that reads git history or the base ref runs every time
- Fewer reused stages, fewer places for a stale result

## Considered Options

:::{opt} The test modules and the Sphinx build
:id: OPT_0030_PROOFS_AND_BUILD
Each proof module's results, and the Sphinx build's warnings and output directory, are
reused by manifest. Every other stage runs: listing files, the lock, the Vale table and
line endings, reading the test declarations and judging their results, the graph checker,
the Vale rules, the lint view and Vale, the fixture audit, the history check and the
location stage. Good, because the two stages hold 89 percent of the measured time. Bad,
because the history check, the lint view and Vale, 4.8 seconds together, still run on
every check.
:::

:::{opt} Every stage
:id: OPT_0030_ALL
Good, because the most is reused. Bad, because the cheap stages save little, the history
check reads git, which the recorder cannot see, and each added stage is a new path for a
stale result.
:::

:::{opt} The test modules only
:id: OPT_0030_PROOFS
Good, because it extends the one cache that exists. Bad, because the 50 fixtures that
change nothing under `docs/` would still each build every page.
:::

## Decision Outcome

Chosen option: {need}`OPT_0030_PROOFS_AND_BUILD`, because it covers the measured time and
keeps git, the judging of test results and every rule's own logic running on every check.

## Consequences

- Good, because judging stays live: a reused test result is judged by the running package
  each time, so a change to the judging rules is never hidden by a stored verdict.
- Good, because each proof module then runs in its own child, so a module's result is the
  same whether it ran alone or was reused.
- Bad, because a module per child adds an interpreter start per module, and
  DES_0004's COMP_TEST_PROOFS, which states one child, has to be amended to match.
- Bad, because restoring a build means copying its output directory, 6.3 MB today, into
  each fixture copy that reuses it.
