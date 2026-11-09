---
status: accepted
date: 2026-11-08
decision-makers: [claude]
informed: [wyatt]
---
# CI runs the check on Linux and Windows

:::{decision}
:chooses: OPT_0025_LINUX_WINDOWS
:resolves: Q_CI_PLATFORMS
:driven_by: REQ_PORTABLE_FINDINGS
:::

## Context and Problem Statement

wyatt, 2026-11-08, on running the check in CI on three platforms: "I'm not running 3 ci
jobs just to make sure, unless it's absurdly cheap". GitHub's billing documentation lists
standard GitHub-hosted runners, Windows and macOS included, as free for public
repositories, and this repository is public; the cost is the time a pull request waits.

## Decision Drivers

- The platform this work exists for is checked on every pull request
- No job runs only to make sure
- A pull request does not wait on a slow queue for a platform nobody asked for

## Considered Options

:::{opt} A Linux job and a Windows job
:id: OPT_0025_LINUX_WINDOWS
Good, because Windows is the platform with different paths, line endings and executable
names, and it costs nothing on a public repository. Bad, because macOS is supported but
not checked.
:::

:::{opt} Linux, Windows and macOS jobs
:id: OPT_0025_THREE
Good, because every supported platform is checked. Bad, because it is the third job wyatt
did not want run just to make sure, and macOS shares Linux's path separator and line
ending.
:::

:::{opt} A Linux job only
:id: OPT_0025_LINUX
Good, because nothing changes. Bad, because the Windows faults this work fixes would come
back unseen.
:::

## Decision Outcome

Chosen option: {need}`OPT_0025_LINUX_WINDOWS`, because Windows is free here and is the
platform the change is for, while a macOS job would be the third job wyatt ruled out.

## Consequences

- Good, because the Windows job runs setup, the check and the fixtures with `python`
  commands, which proves the commands work without `make`.
- Bad, because the protected branch has to require the Windows job too, a repository
  setting that waits for wyatt's yes after the job exists on main.
- Bad, because if this repository goes private, the Windows job uses paid minutes at
  twice the Linux rate.
