---
status: accepted
date: 2026-11-10
decision-makers: [claude]
informed: [wyatt]
---
# The profile is a file beside the build

:::{decision}
:chooses: OPT_0029_FILE
:resolves: Q_PROFILE_PLACE
:driven_by: REQ_PROFILED
:::

## Context and Problem Statement

A profile has to reach whoever is asking why a run is slow, locally and in CI, without
touching the findings: standard output is the finding stream, sorted and byte-identical
across runs, and the fixture runner parses it from each copy's check.

## Decision Drivers

- Findings and exit status do not change
- The same record locally and in CI
- A person reads it without a tool, and a tool reads it without parsing prose

## Considered Options

:::{opt} A JSON file under the build directory, summarized in CI
:id: OPT_0029_FILE
`--profile PATH` writes the profile as JSON to a file; by default the check writes
`docs/_build/profile/check.json` and the fixture runner `docs/_build/profile/fixtures.json`.
CI uploads the directory as an artifact and writes a table of the slowest stages and
fixtures to the job summary. Good, because it never touches standard output, survives the
run, and is the same file on every platform. Bad, because a person reads a file, or the
CI summary, not the terminal.
:::

:::{opt} A table on standard error
:id: OPT_0029_STDERR
Good, because it is seen at once. Bad, because nothing keeps it, CI logs fold it away, and
the fixture runner would have to collect it from every copy's error stream.
:::

:::{opt} `cProfile` dumps
:id: OPT_0029_CPROFILE
Good, because they show every function. Bad, because they cover one process, while the
time is spent across the check, its test child, Sphinx and every fixture copy, and they
need a tool to read.
:::

## Decision Outcome

Chosen option: {need}`OPT_0029_FILE`, because it keeps the profile off the finding stream
and gives CI and a local run the same record.

## Consequences

- Good, because `docs/_build/` is already ignored and cleaned, so the profile adds no
  tracked file and no ignore rule.
- Good, because the CI summary puts the numbers on the pull request's checks page.
- Bad, because the check's clean of `docs/_build/` before the Sphinx build would remove an
  earlier profile; the profile directory is written after the build and kept out of that
  clean.
