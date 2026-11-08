---
status: accepted
date: 2026-11-08
decision-makers: [claude]
informed: [wyatt]
---
# The toolchain ships as a pinned package

:::{decision}
:chooses: OPT_0013_PACKAGE
:resolves: Q_DISTRIBUTION
:driven_by: REQ_ONE_PACKAGE, REQ_INIT_PASSES, REQ_SELF_TESTS_SCOPED, REQ_PINNED_TOOLCHAIN
:::

## Context and Problem Statement

wyatt, 2026-11-08, asked for a template of this repository so that every new project
starts with the corpus and its checks. The rules have to reach other repositories
without becoming a second home of the rules in each of them, and without carrying this
repository's own documents and fixtures along.

## Decision Drivers

- The rules have one home across every repository that uses them
- An adopting repository upgrades by changing one pinned line
- This repository's corpus and fixtures stay here

## Considered Options

:::{opt} A Python package with an init command, and a template repository made from its output
:id: OPT_0013_PACKAGE
Good, because the rules live only in the package, an upgrade is a lock line, and the
template repository holds only what init writes. Bad, because the code moves into a
package layout and every `spec` path changes once.
:::

:::{opt} A GitHub template repository copied from this one
:id: OPT_0013_COPY
Good, because it is one click. Bad, because each project gets its own copy of the rules
and of this repository's corpus, and the copies drift.
:::

:::{opt} A git submodule of this repository
:id: OPT_0013_SUBMODULE
Good, because there is one copy. Bad, because the submodule brings this repository's
corpus and fixtures with it, and submodules are easy to leave at a stale commit.
:::

## Decision Outcome

Chosen option: {need}`OPT_0013_PACKAGE`, because it is the only option that keeps one home
for the rules and leaves this repository's documents behind.

## Consequences

- Good, because the template repository is a convenience, not a source: it can be
  regenerated from init at any time.
- Bad, because the package is pinned by a release wheel's URL and hash, and a private
  repository's release assets need a token to download.
