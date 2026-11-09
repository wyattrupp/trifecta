---
status: approved
authors: [claude]
---
# Running on Windows

:::{design}
:::

## Overview

A Python setup script with one table of Vale release files and hashes fetches Vale for the
platform it runs on. A `.gitattributes` checks text out with LF, the check reports it
missing, and every reader of a document converts CRLF to LF. The pipeline strips the
repository root from each location in the form the platform writes it, converts what is
left to forward slashes, and reports any location still absolute. A second CI job runs
setup, the check and the fixtures on Windows with `python` commands. Plan 0003 moves the
script into the package as `trifecta setup`, and its init writes the `.gitattributes`.

Components here have no `spec` until they are built; the plan that builds them adds it.

## Requirements

:::{needtable}
:filter: type == 'req' and len(satisfies_back) > 0
:columns: id, title, satisfies_back as "Satisfied by"
:style: table
:::

## Constraints

:::{needtable}
:filter: type == 'decision' and len(constrained_by_back) > 0
:columns: id, title, status
:style: table
:::

## Components

:::{component} Vale setup
:id: COMP_VALE_SETUP
:satisfies: REQ_PLATFORM_TOOLCHAIN
:constrained_by: DEC_0023
`tools/setup.py`, holding the table of Vale's version and, per platform key such as
`linux-x86_64` or `windows-amd64`, the release file name and its SHA-256. It picks the
key from `platform.system()` and `platform.machine()`, refuses a platform with no row,
downloads the file over `https` from Vale's release page into memory, compares the
SHA-256, and extracts the one member named `vale` or `vale.exe` to `bin/`, writing a
per-version stamp. The Makefile's `setup` target calls it, and the pipeline's toolchain
stage checks every row of the table in place of the Makefile variables, and finds the
executable under either name.
:::

:::{component} Line endings
:id: COMP_LINE_ENDINGS
:satisfies: REQ_ONE_LINE_ENDING
:constrained_by: DEC_0024
A `.gitattributes` holding `* text=auto eol=lf`; a pipeline stage that reports the file
missing or without that line; and CRLF converted to LF wherever a document is read as
text: the plan parser, the frontmatter reader, the fixture runner's anchors, and plan
0002's review digest.
:::

:::{component} Portable locations
:id: COMP_PORTABLE_PATHS
:satisfies: REQ_PORTABLE_FINDINGS
:constrained_by: DEC_0023
Location mapping that strips the repository root in both its native form and its form
with forward slashes, then converts backslashes to forward slashes, followed by a last
pipeline stage that reports each finding whose location still starts at a drive, a root
or a UNC prefix.
:::

:::{component} Windows CI job
:id: COMP_WINDOWS_CI
:constrained_by: DEC_0025
A `check-windows` job in the CI workflow, beside the existing `check` job, on a Windows
runner with the same permissions, checkout settings, SHA-pinned actions and base ref. It
runs `python tools/setup.py`, the check and the fixture runner without `make`.
:::

## Interfaces

## Risks

Renormalizing line endings touches every text file once; that commit changes nothing
else, so a review can confirm it with `git diff --ignore-all-space`. Until the protected
branch requires `check-windows`, a pull request can merge with it failing. A Vale release
that drops a platform leaves its row unable to download, which setup reports by name.
