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
endings, though the index holds LF; today's readers convert line endings, but any tool
that reads raw bytes, and every diff and editor, sees a different file on Windows. The
pipeline strips the repository prefix from Sphinx's and Vale's locations with a forward
slash, so on Windows some findings carry an absolute path with backslashes, and
subprocess output is decoded with the Windows code page in place of UTF-8. And CI runs
only on Linux, so none of this is caught.

## Terms

## Requirements

:::{req} Findings are the same on every platform
:id: REQ_PORTABLE_FINDINGS
The check MUST report the same requirements at the same locations on Linux, macOS and
Windows, and MUST locate each finding by a path relative to the repository root, written
with forward slashes. After mapping, a location that starts at a root, a drive or a UNC
prefix, or that holds a `..` segment or a backslash, MUST itself be reported. The check
MUST read the output of every program it runs as UTF-8.
:::

:::{req} Vale is pinned for each platform
:id: REQ_PLATFORM_TOOLCHAIN
One table MUST pin Vale's version and, for each of Linux and macOS on x86-64 and ARM and
Windows on x86-64, the release file, named as Vale names it for that version, and its
SHA-256. The check MUST report a table missing a platform, a file name of another form,
or a hash that is not 64 lowercase hexadecimal digits, and MUST report any file tracked
under `bin/`.
:::

:::{req} Documents have one line ending
:id: REQ_ONE_LINE_ENDING
The repository MUST hold, as its only `.gitattributes`, one at its root that checks text
files out with LF line endings and sets no filter, diff, merge, encoding, `ident` or
`linguist` attribute. Every reader of a document MUST treat a CRLF line ending as LF, so
a document an editor saved with CRLF gives the same result as the same document with LF.
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
longer than Windows' default limit, tracked symbolic links and paths that differ only in
case, which check out differently on Windows; Windows on ARM, until Vale releases a binary
for it; a container or WSL setup, which needs nothing from this repository.

## Review

:::{review} Correctness; security
:id: REV_RFC_0006_1
:k: 2
:date: 2026-11-08
The Windows set at commit 2a9f8c2: this RFC, {need}`DEC_0023` to {need}`DEC_0025`,
{need}`DES_0006` and {need}`PLAN_0005`, with the amendments to {need}`DES_0004` and
{need}`PLAN_0003` that add `trifecta setup` and the `.gitattributes` to init. No
off-lineage pass ran; the local model was down. Folded in: the index already holds LF, so
no renormalization commit, and the line-ending rationale now rests on raw-byte readers,
diffs and editors; the `.gitattributes` is held to one content with no second file and no
filter, diff or `linguist` attribute; one location helper for Sphinx and Vale, a last
stage for locations it could not map, proven by a fixture that logs a warning from
`docs/conf.py`, and UTF-8 for every subprocess; the toolchain requirement checks the
table, not the download, and reports files tracked under `bin/`; setup installs the lock,
maps platforms explicitly, refuses a linked `bin`, fixes the release URL and its hosts,
reads one regular-file member by name, keys its stamp on the archive hash, and runs the
executable it wrote; the Windows job runs under `bash` with `PYTHONUTF8=1`; the ruleset
change is a step that is dropped without wyatt's yes; DEC_0025 states that wyatt's ruling
permits a free macOS job and why it is left out. Not taken: a positive-fixture mode,
since a CRLF fixture with a step gap proves the parser reads CRLF; checking symbolic
links and case collisions, now out of scope.
:::

:::{review} Correctness; security
:id: REV_RFC_0006_2
:k: 2
:date: 2026-11-09
:digest: b7a923a6e18c7645de2f2e72fa5a0a03f9aae1b48daa0b0f163b680cf06fb14a
:::
