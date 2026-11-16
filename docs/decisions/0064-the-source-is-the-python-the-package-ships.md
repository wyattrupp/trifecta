---
status: accepted
date: 2026-11-15
decision-makers: [wyatt]
informed: [claude]
---
# The source is the Python the package ships

:::{decision}
:chooses: OPT_0064_PACKAGE_PYTHON
:resolves: Q_SOURCE_FILES
:::

## Context and Problem Statement

{need}`REQ_SYNONYMS_IN_SOURCE` and {need}`REQ_DIAGRAM_FROM_SOURCE` both read "the source",
and {need}`DEC_0055` left open which files that is.

Measured on 2026-11-15 at commit `1ec2b54`, over the files git tracks:

| Reading | Value |
| --- | --- |
| Python files under `src`, and under `tests` | 27 and 23 |
| Files under `.github`, and files under `src` that are not Python | 8 and 11 |
| Files that `spec` paths name | 28: 23 under `src`, 3 under `.github`, the README and `pyproject.toml` |
| Declared synonyms found in the Python under `src`, and under `tests` | 0 and 0 |
| Declared synonyms found in the README, the Makefile and `pyproject.toml` | 0 |
| Declared synonyms found under `.github` | 3 |

How each was read: files by `git ls-files`; a synonym as its words in order, in the
names, comments and strings of a Python file and in the lines of any other.

The three under `.github` are `cache-hit`, twice, which is the name GitHub gives an
output of its cache action, and `adr`, once, a topic the repository is listed under. Both
are names another party fixes. An import, which the diagram is drawn from, exists only in
Python. One limit: the documents under `docs` and the fixtures under `tests` were not
read, the first because {need}`REQ_CANONICAL_TERMS` already holds them.

### The ask as put

What was put to wyatt, copied from the transcript of the session. An option marked
"(Recommended)" was the one recommended. The readings shown beside a question in the
same message were those of the table above, save where the outcome says a figure was
wrong; they are not copied again.

```text
Question: Q_SOURCE_FILES: which files are the source that terms and the diagram read?
Evidence: 27 Python files under src, 23 under tests; no declared synonym in either; the
only 3 hits anywhere are GitHub-fixed names in .github (cache-hit, adr); imports exist
only in Python.

Options, in the order shown:
- Package Python only (Recommended): Source means the Python files the package ships
  (here, under src). Terms and diagram read those and nothing else. Clean today; tests,
  workflows and README stay outside.
- Package and tests Python: As above plus the 23 test files. Also clean today; doubles
  what the rule reads and test names start to be bound by the terms.
- Every file a spec path names: The 28 files components point into, any format. Follows
  the design; needs an exception for names a third party fixes, as cache-hit shows.

Answer: Package Python only (Recommended)
```

## Decision Drivers

- {need}`DEC_0052`: descriptions move into the source, so the terms have to bind there
- A rule that needs exceptions for names a third party fixes is a weaker rule
- {need}`DEC_0061`: what the rule reads is part of its size

## Considered Options

:::{opt} The Python the package ships
:id: OPT_0064_PACKAGE_PYTHON
The source is the Python files the package ships, here those under `src`, and the terms
and the diagram read those and nothing else. Good, because it is where the descriptions
go and it passes today. Bad, because the tests, the workflows and the README are bound
by no term.
:::

:::{opt} The package and the tests
:id: OPT_0064_WITH_TESTS
As above, with the Python under `tests`. Good, because it also passes today. Bad,
because it doubles what is read and binds the names of tests.
:::

:::{opt} Every file a spec path names
:id: OPT_0064_SPEC_FILES
The 28 files that components point into, whatever their format. Good, because it
follows the design. Bad, because it needs an exception for a name such as `cache-hit`.
:::

## Decision Outcome

Chosen option: {need}`OPT_0064_PACKAGE_PYTHON`, because wyatt, 2026-11-15, choosing from
Claude's recommendations with the readings above in the ask: "Package Python only
(Recommended)".

## Consequences

- Good, because both requirements now read a set of files a tool can list.
- Bad, because how an adopting repository says where its package is has no setting yet.
- Bad, because a component whose `spec` path names a workflow or the README is on no
  diagram drawn from imports.
