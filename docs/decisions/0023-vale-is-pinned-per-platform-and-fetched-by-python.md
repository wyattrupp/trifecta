---
status: accepted
date: 2026-11-08
decision-makers: [wyatt]
consulted: [claude]
---
# Vale is pinned per platform and fetched by Python

:::{decision}
:chooses: OPT_0023_PYTHON_SETUP
:resolves: Q_VALE_PLATFORMS
:driven_by: REQ_PLATFORM_TOOLCHAIN, REQ_PORTABLE_FINDINGS
:::

## Context and Problem Statement

wyatt, 2026-11-08, approved the Windows design: "windows design looks good". The Makefile
fetches Vale's Linux binary with `curl`, `sha256sum` and `tar`, and runs only where `make`
does. Vale publishes a binary and a SHA-256 for Linux, macOS and Windows on x86-64 and
ARM, except Windows on ARM.

## Decision Drivers

- One command sets up the toolchain on every platform, with only Python installed
- Every binary is pinned by hash, as REQ_PINNED_TOOLCHAIN already requires on Linux
- The setup moves into the package with the rest of the tools

## Considered Options

:::{opt} A Python setup script with one table of per-platform release files and hashes
:id: OPT_0023_PYTHON_SETUP
Good, because it needs only the Python the check already needs, reads the platform from
the standard library, verifies the hash before it opens the archive, and becomes
`trifecta setup` when plan 0003 builds the package. Bad, because the table carries five
hashes to update on each Vale release.
:::

:::{opt} Run the check in a container image
:id: OPT_0023_CONTAINER
Good, because one Linux image serves every platform. Bad, because every user then needs a
container runtime, and Windows paths reach the check only through a mount.
:::

:::{opt} Support Windows only through WSL
:id: OPT_0023_WSL
Good, because the Makefile stays as it is. Bad, because the check never runs on Windows
itself, so the path and line-ending faults stay hidden.
:::

## Decision Outcome

Chosen option: {need}`OPT_0023_PYTHON_SETUP`, because it was the design wyatt approved,
and it runs the check on Windows itself with nothing installed but Python.

## Consequences

- Good, because the Makefile keeps its targets, now calling the script, and every command
  also runs as `python tools/...` without `make`.
- Good, because the table is one home for Vale's version and hashes: the Makefile's
  Vale variables go, its targets call the script, and the pipeline checks the table.
- Good, because the script, not the check, is where the download happens, so it carries
  its own rules: a fixed release URL, a refused redirect off GitHub's hosts, a refused
  `bin` that is a link or leaves the repository, an archive opened only after its hash
  matches, and one regular-file member read out by name, never extracted by the archive's
  own paths.
- Bad, because a Vale upgrade means copying five hashes from Vale's checksum file into the
  table.
