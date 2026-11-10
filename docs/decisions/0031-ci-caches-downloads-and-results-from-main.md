---
status: accepted
date: 2026-11-10
decision-makers: [claude]
informed: [wyatt]
---
# CI caches downloads, and results from main

:::{decision}
:chooses: OPT_0031_DOWNLOADS_AND_MAIN
:resolves: Q_CI_CACHE
:driven_by: REQ_REUSE_SOUND
:::

## Context and Problem Statement

Each CI job starts from a fresh runner: it downloads the lock's wheels and Vale, runs the
check, and runs the fixtures with an empty store, so the control and every fixture that
misses run everything. GitHub's cache action keeps files between runs. A pull request's
runs share one cache scope, read their own scope before the base branch's, and can save
into it, and each run runs the workflow file as the pull request has it at that commit;
so an earlier commit of a pull request can save a cache entry that a later commit, whose
diff a reviewer reads, restores. The check and fixture steps run code the pull request
controls.

## Decision Drivers

- No result a pull request's code wrote is read by any other run
- Whatever is restored is verified by hash, or is used only on an exact manifest match
- The top-level check stays a fresh run

## Considered Options

:::{opt} Cache downloads by hash, and fetch results from main's last push run
:id: OPT_0031_DOWNLOADS_AND_MAIN
Pip's downloaded archives and setup's Vale archive are cached, keyed on the locks and
the setup script; pip checks every archive against the lock's hashes and setup checks the
Vale archive's SHA-256 before every extraction, so a bad cached file is refused, not run,
and `bin/` is never cached. Push runs on main run the fixtures from an empty store and
upload the store they wrote as an artifact; a pull request's run downloads the artifact of the
latest successful push run of the check workflow on main, found and fetched by its run
ID, so it cannot be a cache entry the pull request saved. The top-level check runs with
`--fresh`. Good, because a pull request that changes only documents reuses main's result
for every test module whose manifest holds no variable that differs between runs, and
every result it reuses was run by merged code in one run. Bad,
because the workflow needs `actions: read` to find and fetch the artifact, and a pull
request that changes code reuses only within its own run.
:::

:::{opt} Cache downloads only
:id: OPT_0031_DOWNLOADS
Good, because no result crosses runs and no permission changes. Bad, because the control
and every missing fixture still run every test on every run, the largest cost after the
builds.
:::

:::{opt} Cache results with the cache action
:id: OPT_0031_CACHE_ACTION
Results saved by the cache action, from main's push runs and from each run of a pull
request. Good, because a pull request's later pushes reuse its earlier results, and no
permission changes. Bad, because a pull request's own scope is read first, so an earlier
commit of it can save a store, forged to match anything, that its final commit restores
while the reviewed diff shows nothing.
:::

## Decision Outcome

Chosen option: {need}`OPT_0031_DOWNLOADS_AND_MAIN`, because it is the only option in
which every result a run reuses was written by merged code, and every download is checked
against a hash.

## Consequences

- Good, because the actions are GitHub's own, pinned by SHA like the others, and the only
  added permission is `actions: read`, which reads runs and artifacts that are public in
  this repository.
- Good, because a stored result is reused only by an exact manifest match, so an honest
  store that no longer fits saves nothing and costs nothing.
- Bad, because the fixture runner's verdicts in a pull request rest on main's stored
  results: a result main stored wrongly, through a gap in the recorder, can hide a
  fixture failure until an input it recorded changes. The top-level fresh check guards
  the check's own findings, not the fixture runner's.
- Bad, because a test module that copies the environment records variables such as
  `GITHUB_RUN_ID`, which differ between runs, so it is reused only within a run; the
  profile names those modules.
- Bad, because a pull request opened before main's first such push run, or after its
  artifact expires, finds no store and runs everything.
