---
status: accepted
date: 2026-11-08
decision-makers: [wyatt]
consulted: [claude]
---
# Documents are checked out with LF

:::{decision}
:chooses: OPT_0024_ATTRIBUTES_AND_READERS
:resolves: Q_LINE_ENDINGS
:driven_by: REQ_ONE_LINE_ENDING
:::

## Context and Problem Statement

wyatt, 2026-11-08, approved the Windows design: "windows design looks good". Git on
Windows commonly sets `core.autocrlf`, which checks text out with CRLF line endings
though the index holds LF, and editors can save CRLF on their own. Today's readers open
files in text mode and the planned review digest strips trailing whitespace, so they
already agree; any tool that reads raw bytes does not, and diffs and editors show a
different file per platform.

## Decision Drivers

- A document hashes the same on every platform
- A file an editor saved with CRLF does not fail the check
- The rule needs no setting on the user's machine

## Considered Options

:::{opt} A `.gitattributes` that checks text out with LF, and readers that treat CRLF as LF
:id: OPT_0024_ATTRIBUTES_AND_READERS
Good, because the attributes file overrides `core.autocrlf` for every clone, and readers
that convert line endings make a stray CRLF harmless. Bad, because two mechanisms carry
one rule, and the attributes file is itself something a pull request can change, so the
check holds it to one content.
:::

:::{opt} A `.gitattributes` alone
:id: OPT_0024_ATTRIBUTES
Good, because it is one file. Bad, because a file an editor saved with CRLF still hashes
differently until it is committed.
:::

:::{opt} Readers that treat CRLF as LF alone
:id: OPT_0024_READERS
Good, because nothing in the repository changes. Bad, because every future reader of
raw bytes has to remember the rule, and Windows checkouts, diffs and editors still differ
from Linux ones.
:::

## Decision Outcome

Chosen option: {need}`OPT_0024_ATTRIBUTES_AND_READERS`, because it was the design wyatt
approved, and it makes every checkout LF while keeping a stray CRLF from changing a
result.

## Consequences

- Good, because the check reports a missing or wrong `.gitattributes`, and plan 0003's
  init writes the same file into an adopting repository.
- Good, because the index already holds LF, so adding the file changes no stored content;
  a Windows checkout only needs refreshing.
- Bad, because the rule mostly guards future readers and tools, since today's readers
  already agree.
