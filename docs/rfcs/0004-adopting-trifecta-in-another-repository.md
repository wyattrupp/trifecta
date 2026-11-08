---
status: accepted
authors: [claude]
created: 2026-11-08
---
# Adopting trifecta in another repository

:::{rfc}
:::

## Summary

The toolchain leaves this repository as one pinned Python package. An
{need}`adopting repository <TERM_ADOPTER>` gets a passing, empty
{need}`corpus <TERM_CORPUS>` from one command, or from a template repository made from
that command's output. A Claude Code session in it plans through the corpus by default,
and the README says how to set it up.

## Motivation

wyatt, 2026-11-08: "soon we'll make a template of this repo, and a claude.md set of tools
that lets this just happen by default every time I start planning in a session", and
"a 'run this in your repo' guide as readme.md".

Copying this repository into each project would make every project a second home of the
rules, and the copies would drift the way documentation does. This repository's own RFCs
describe the toolchain, not the adopting project, and its negative fixtures mutate those
RFCs, so neither belongs in another repository. A session left to the superpowers skills'
defaults writes specs and plans to paths and in shapes the check rejects.

## Terms

:::{term} Adopting repository
:id: TERM_ADOPTER
A repository other than this one whose documents are checked by the toolchain package.
:::

## Requirements

:::{req} The toolchain is one pinned package
:id: REQ_ONE_PACKAGE
The extension, the schemas, the plan rules, the Vale styles and configurations, and the
tools MUST ship as one Python package. An adopting repository MUST NOT hold a copy of any
of them, and MUST pin the package by version and hash.
:::

:::{req} Init produces a passing corpus
:id: REQ_INIT_PASSES
The package's init command, run in a repository with no corpus, MUST produce one whose
check passes and which holds none of this repository's documents.
:::

:::{req} Toolchain self-tests stay here
:id: REQ_SELF_TESTS_SCOPED
The negative fixture audit MUST run only in this repository, which defines the
toolchain's requirements.
:::

:::{req} Requirements no mutation can show are proven by tests
:id: REQ_PROVEN_BY_TEST
A requirement that no mutation of the corpus can show MUST be named by a test under
`tests/` as the requirement it proves, and every such test MUST pass in the check.
:::

:::{req} Planning goes through the corpus by default
:id: REQ_PLANNING_DEFAULT
The init command MUST install instructions that direct a Claude Code session to write
specs and plans into the typed directories with the package's commands, and a hook that
refuses a write under `docs/superpowers/`.
:::

## Questions

:::{question} How do the rules reach another repository?
:id: Q_DISTRIBUTION
:::

:::{question} How is a planning session made to use the corpus?
:id: Q_PLANNING_DEFAULT
:::

:::{question} How is a requirement proven when no corpus mutation can show it?
:id: Q_NON_CORPUS_PROOF
:::

## Out of scope

Publishing to PyPI; CI systems other than GitHub Actions; agents other than Claude Code;
migrating an existing project's documents into the corpus.

## Review
