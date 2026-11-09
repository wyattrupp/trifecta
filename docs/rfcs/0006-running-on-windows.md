---
status: accepted
authors: [claude]
created: 2026-11-08
---
# Running on Windows

:::{rfc}
:::

## Summary

The check gives the same findings, at the same locations, on Linux, macOS and Windows.
Vale is pinned for every platform it is released for and fetched by a Python script that
needs no `make`, `curl`, `sha256sum` or `tar`. Every checkout holds documents with LF
line endings. CI runs the check on Windows as well as Linux.

## Motivation

wyatt, 2026-11-08, listed "running it on windows" among what users might want, and set
the order "Windows, then visualization, then research rigor".

Four things break on Windows today. The Makefile downloads only Vale's Linux binary, with
tools Windows does not ship, and Windows has no `make`. This repository has no
`.gitattributes`, so git with `core.autocrlf` checks documents out with CRLF line
endings: plan 0002's review digest, which hashes the raw file, would differ by platform,
and fixture anchors that span lines would not match. The pipeline strips the repository
prefix from Sphinx's warning locations with a forward slash, so on Windows some findings
carry an absolute path with backslashes. And CI runs only on Linux, so none of this is
caught.

## Terms

## Requirements

:::{req} Findings are the same on every platform
:id: REQ_PORTABLE_FINDINGS
The check MUST report the same findings on Linux, macOS and Windows, and MUST locate each
by a path relative to the repository root, written with forward slashes. A finding whose
location is absolute, holds a backslash or names a drive MUST be reported.
:::

:::{req} Vale is pinned for each platform
:id: REQ_PLATFORM_TOOLCHAIN
One table MUST pin Vale's version and, for each platform Vale is released for that the
check supports, the release file and its SHA-256. The setup command MUST download only a
file named in that table, MUST verify its SHA-256 before opening it, and MUST extract only
the Vale executable, to a fixed name in the repository's `bin/` directory.
:::

:::{req} Documents have one line ending
:id: REQ_ONE_LINE_ENDING
The repository MUST hold a `.gitattributes` that checks text files out with LF line
endings. Every reader of a document MUST treat a CRLF line ending as LF, so a document an
editor saved with CRLF gives the same result as the same document with LF.
:::

## Questions

:::{question} How does the check get Vale on each platform?
:id: Q_VALE_PLATFORMS
:::

:::{question} How do line endings stay the same across platforms?
:id: Q_LINE_ENDINGS
:::

:::{question} On which platforms does CI run the check?
:id: Q_CI_PLATFORMS
:::

## Out of scope

Platforms Vale is not released for; Python versions other than the one CI pins; paths
longer than Windows' default limit; Windows on ARM, until Vale releases a binary for it;
a container or WSL setup, which needs nothing from this repository.
