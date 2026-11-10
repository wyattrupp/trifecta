---
status: implemented
authors: [claude]
---
# Running on Windows

:::{design}
:::

## Overview

A Python setup script installs the hashed Python dependencies and fetches Vale for the
platform it runs on, from one table of Vale release files, sizes and hashes. A `.gitattributes`
checks text out with LF, and the check holds it to one content. One helper maps every
location the check reports to a repository-relative path with forward slashes, a last
stage reports any location it could not map, and every program's output is read as
UTF-8. A second CI job runs setup, the check and the fixtures on Windows. Plan 0003 moves
the script into the package as `trifecta setup`, and its init writes the
`.gitattributes`.

Plan 0005 built every component here and set its `spec`.

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
:spec: tools/setup.py#VALE_FILES
:satisfies: REQ_PLATFORM_TOOLCHAIN
:constrained_by: DEC_0023
`tools/setup.py`, holding the table of Vale's version and, per platform key, the release
file name, its size and its SHA-256. It runs the hashed `pip install` from the lock, then maps
`platform.system()` and `platform.machine()` through an explicit table (`x86_64` and
`AMD64` to x86-64, `aarch64` and `arm64` to ARM) and refuses anything unmapped. It
refuses a `bin` that is a link or reparse point or resolves outside the repository,
downloads from Vale's release URL for the pinned version, built in the script, following
redirects only over `https` to GitHub's hosts and reading no more than twice the expected
size, and compares the SHA-256 before opening the archive. It reads the one top-level
regular-file member named `vale` or `vale.exe` by name, refusing a link member or a
duplicate, writes it to a temporary file in `bin/`, sets it executable and moves it into
place, then runs `vale --version`. The stamp it writes records the version and the
archive's hash, so a changed hash fetches again. The Makefile's targets call the script,
and the pipeline's toolchain stage checks the table and reports files tracked under
`bin/`. The check runs exactly `bin/vale.exe` on Windows and `bin/vale` elsewhere, by
absolute path.
:::

:::{component} Line endings
:id: COMP_LINE_ENDINGS
:spec: tools/check.py#def check_line_endings
:satisfies: REQ_ONE_LINE_ENDING
:constrained_by: DEC_0024
A `.gitattributes` holding exactly `* text=auto eol=lf`, and a pipeline stage that
reports it missing or different, and any other tracked `.gitattributes`. Every reader
opens documents in text mode or strips trailing whitespace, and the fixture runner writes
mutated files with no newline translation, so a fixture's content is the same on every
platform.
:::

:::{component} Portable locations
:id: COMP_PORTABLE_PATHS
:spec: tools/findings.py#def relative_location
:satisfies: REQ_PORTABLE_FINDINGS
One helper in `tools/findings.py`, used for Sphinx's and Vale's locations alike, that
makes a location relative to the resolved repository root, comparing without case on
Windows and converting the platform's separator to a forward slash; a last pipeline stage
that reports a location starting at a root, a drive or a UNC prefix, or holding a `..`
segment or a backslash; and `encoding="utf-8"` on every program the check runs.
:::

:::{component} Windows CI job
:id: COMP_WINDOWS_CI
:spec: .github/workflows/check.yml#check-windows
:constrained_by: DEC_0025
A `check-windows` job in the CI workflow, beside the existing `check` job, on a Windows
runner with the same permissions, checkout settings, SHA-pinned actions and base-ref
logic, with `bash` as its shell, so a failing command fails the step and the event
values reach it through `env`. It sets `PYTHONUTF8=1` and runs `python tools/setup.py`,
the check and the fixture runner without `make`.
:::

## Interfaces

## Risks

The main ruleset requires `check-windows` beside `check`, so a pull request cannot merge
while either is red. A Vale release that drops a
platform leaves its row unable to download, which setup reports by name. The table's
hashes are taken from the release they pin: each is recomputed from an independent
download and compared with Vale's checksum file when the table is written, which catches
a corrupted download but not a release compromised before it was pinned. The table lives
in `tools/setup.py`, which a pull request can edit, and the check holds it to its form,
not to Vale's published checksums, so the maintainer's review of the pull request is the
safeguard, and no ruleset requires an approval. The stamp records the version and the
archive's hash, not the hash of the extracted executable, so an executable placed in
`bin/` by hand runs unverified; CI starts from a fresh checkout. A macOS-only fault would
go unseen, since no job runs there.

## Review

:::{review} Correctness; security
:id: REV_DES_0006_1
:k: 2
:date: 2026-11-08
The review recorded as {need}`REV_RFC_0006_1` covered this document.
:::

:::{review} Correctness; documentation standard
:id: REV_DES_0006_2
:k: 2
:date: 2026-11-09
Reviewed the move to implemented and the updated overview and risks, with
{need}`REV_PLAN_0005_2`.
:::

:::{review} Correctness; security
:id: REV_DES_0006_3
:k: 2
:date: 2026-11-09
:digest: 993d18da1dd035ae59a36de79225c05e8df11566b27813b1d6a4dbda265a45c9
:::
