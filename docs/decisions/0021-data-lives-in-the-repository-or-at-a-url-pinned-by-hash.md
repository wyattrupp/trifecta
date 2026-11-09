---
status: accepted
date: 2026-11-08
decision-makers: [wyatt]
consulted: [claude]
---
# Data lives in the repository or at a URL, pinned by hash

:::{decision}
:chooses: OPT_0021_EITHER
:resolves: Q_DATA_HOME
:driven_by: REQ_DATA_PINNED, REQ_EXTERNAL_DATA
:::

## Context and Problem Statement

wyatt, 2026-11-08, answered "A" when asked where experiment data lives. A result pins its
data by SHA-256, and the data has to be somewhere the hash can be checked, while the check
itself stays offline and gives the same answer on every run.

## Decision Drivers

- The check is deterministic and makes no network access
- A small benchmark file needs no hosting
- Training runs and lab datasets outgrow git

## Considered Options

:::{opt} In the repository or at a URL, both pinned by hash
:id: OPT_0021_EITHER
Good, because small data is committed and hashed on every check, and large data is an
`https` URL with its hash and size, which a separate command downloads and checks on
demand, for example in scheduled CI. Bad, because the everyday check cannot tell that
external data has changed or gone.
:::

:::{opt} Always in the repository
:id: OPT_0021_REPOSITORY
Good, because every hash is checked on every run. Bad, because large datasets outgrow git,
even with LFS.
:::

:::{opt} Always at a URL
:id: OPT_0021_URL
Good, because the repository stays small. Bad, because the everyday check can never verify
anything, and a file of a few kilobytes would need hosting.
:::

## Decision Outcome

Chosen option: {need}`OPT_0021_EITHER`, because wyatt chose it, and it checks every hash it
can without letting the check touch the network.

## Consequences

- Good, because in-repository data is checked on every run, and a path that is not a
  plain relative path, a link, an untracked file or a Git LFS pointer is refused before it
  is opened.
- Good, because the download command treats every URL as hostile, since it comes from a
  document anyone can propose in a pull request: it fetches only `https` from public
  addresses, checks every redirect, caps size and time, reads no credentials from the
  environment, and never writes or runs what it reads.
- Bad, because data in Git LFS has to be fetched before the check, and data committed to
  a public repository is public and, once its experiment is concluded, frozen; credentials
  and personal data have to come out before it is committed.
- Bad, because external data is only as current as the last run of the download command.
