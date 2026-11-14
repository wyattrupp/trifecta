---
status: accepted
date: 2026-11-14
decision-makers: [wyatt]
informed: [claude]
---
# The Vale TRIFECTA_VALE names is known by its pin

:::{decision}
:chooses: OPT_0047_PINNED
:resolves: Q_PROGRAMS
:driven_by: REQ_KNOWN_PROGRAM, REQ_REUSE_SOUND
:::

## Context and Problem Statement

{need}`DEC_0038` lets through `bin/vale` under the repository when its SHA-256 is the
toolchain's pin. The fixture runner checks copies of the repository, which hold no
`bin/`, and names the original's Vale in `TRIFECTA_VALE`, so in a copy the check runs a
Vale outside the copy's repository, and `test_init` there was refused.

## Decision Drivers

- A program is trusted by its own hash, never by where it lies
- A fixture copy reuses what the original stored

## Considered Options

:::{opt} Let it through when it matches the pin
:id: OPT_0047_PINNED
The Vale at the path `TRIFECTA_VALE` names, or `bin/vale`, is let through when that
binary's own SHA-256 is the platform's pin; its path is recorded with the hash, which is
what is trusted. Good, because `test_init` is stored in copies too. Bad, because a key now
holds a path outside the repository, so a copy elsewhere reruns.
:::

:::{opt} Only bin/vale under the repository
:id: OPT_0047_OWN
Good, because nothing outside the repository is trusted. Bad, because `test_init` reruns
in every fixture copy.
:::

## Decision Outcome

Chosen option: {need}`OPT_0047_PINNED`, because wyatt, 2026-11-14, choosing from Claude's
recommendations: "Yes, if it matches the pin (Recommended)".

## Consequences

- Good, because the hash trusted is the same pin whichever path names the binary.
- Bad, because a Vale the run itself made stays refused, whatever its hash.
