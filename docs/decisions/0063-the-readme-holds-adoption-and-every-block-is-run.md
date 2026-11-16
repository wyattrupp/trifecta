---
status: accepted
date: 2026-11-15
decision-makers: [wyatt]
informed: [claude]
---
# The README holds adoption, and every block in it is run

:::{decision}
:chooses: OPT_0063_ADOPTION_ONLY
:resolves: Q_README_SCOPE
:::

## Context and Problem Statement

{need}`RFC_0010` records that the book it reads warns against instructions for
developing, using and testing in a README, because they change often, and that the
fault holds here in full and least: the README names no version, and a test runs one of
its install blocks. What the README is to hold is open.

Measured on 2026-11-15 at commit `50ff955`:

| Reading | Value |
| --- | --- |
| Lines and words in the README | 202 and 1,408 |
| Words before the first section | 46 |
| Words in "Run this in your repo" and its four parts | 834 |
| Words in "Developing trifecta" and its three parts | 528 |
| Code blocks | 7: six of shell commands and one of text |
| Code blocks a test runs | 1, on POSIX only, less three commands that need a published release |
| References in the prose that have the form of a path | 22 |
| Of those, paths not in this repository | 7 |
| Subcommands the README names, of those the command has | 7 of 8 |
| Strings with the form of a version | 0 |
| Commits to the README | 10, on 4 of 9 days, the last on 2026-11-13 |

How each was read: words by section, split at headings outside code blocks, and their
sum compared with the whole; a path as text in backquotes made only of name characters
with a slash or a file ending, looked for in the working tree; subcommands by the word
after the command's name, against the table in `cli.py`; commits by `git log`.

So the README did change, ten times in nine days, and nothing in it was found stale by
these readings: the seven paths not in this repository are all paths of an
{need}`adopting repository <TERM_ADOPTER>` or a bare file name, and the one subcommand
it does not name is `profile`. Its adoption steps are held by {need}`REQ_ADOPTION_GUIDE`
and a test that runs them. The other six blocks and the whole of the developing part
are held by nothing. Three limits: only paths, subcommands and versions were compared,
and no sentence was read against the code; which half each block is in was not
counted; and how much of the developing part is also said in `CLAUDE.md` or the skill
was not measured.

### The ask as put

What was put to wyatt, copied from the transcript of the session. An option marked
"(Recommended)" was the one recommended. The readings shown beside a question in the
same message were those of the table above, save where the outcome says a figure was
wrong; they are not copied again.

```text
Question: Q_README_SCOPE: what does the README hold? Evidence: 1,408 words, 59% adoption
steps, 38% developing-this-repo; 7 code blocks, 1 run by a test; 10 commits in 9 days;
nothing stale found in paths, subcommands or versions; one subcommand (profile) missing.

Options, in the order shown:
- Adoption only, every block run (Recommended): README is what the tool is and how to
  adopt it, and each command block in it is run by a test. The developing half (528
  words) leaves: to where a session reads its instructions, or to source per DEC_0052.
- As now, every block run: Both halves stay. Requirement widens so all 7 blocks are run
  by a test. Prose around them still unguarded.
- Purpose and a link: The book's way: README says what and why in a few lines and points
  to the template repository for steps. Shortest; REQ_ADOPTION_GUIDE would need
  superseding.
- As now: No change. One block tested, the rest held by whoever edits it. Nothing stale
  was found today.

Answer: Adoption only, every block run (Recommended)
```

## Decision Drivers

- The book's warning, which {need}`RFC_0010` finds to hold: instructions change and a
  README is not checked
- {need}`DEC_0059`: instructions for working in this repository are read by a session,
  which takes them from `CLAUDE.md` and the skill
- {need}`DEC_0052`: what a part of the tool does is said in its source
- The one part of the README that a test runs is the part nothing found wrong with

## Considered Options

:::{opt} Adoption only, with every block run
:id: OPT_0063_ADOPTION_ONLY
The README says what the tool is and how to adopt it, and each block of commands in it
is run by a test. The developing part leaves it, for where a session reads its
instructions or for the source. Good, because all that is left is held by a test or is
a few stable lines. Good, because it is the reader an adopter is. Bad, because the
developing part needs a home that is decided nowhere here. Bad, because the prose
between the blocks is still held by nothing.
:::

:::{opt} As now, with every block run
:id: OPT_0063_ALL_BLOCKS
Both parts stay, and the requirement widens to every block. Good, because nothing
moves. Bad, because instructions for developing stay in a file their reader does not
start from.
:::

:::{opt} Purpose and a link
:id: OPT_0063_LINK
The book's way: a few lines of what and why, and a link to the template for the steps.
Good, because it is shortest and changes least. Bad, because {need}`REQ_ADOPTION_GUIDE`
says the README opens with the steps, and the steps are the part a test holds.
:::

:::{opt} As now
:id: OPT_0063_AS_NOW
No change. Good, because nothing stale was found. Bad, because six blocks and half the
words rest on whoever edits them.
:::

## Decision Outcome

Chosen option: {need}`OPT_0063_ADOPTION_ONLY`, because wyatt, 2026-11-15, choosing from
Claude's recommendations with the readings above in the ask: "Adoption only, every block
run (Recommended)".

## Consequences

- Good, because {need}`REQ_ADOPTION_GUIDE` already holds the larger half of this, and
  what is added is the same test over the remaining blocks.
- Bad, because nothing has been moved: the README is as it was, and where its
  developing part goes is not settled.
- Bad, because the check does not hold the wider rule; {need}`RFC_0010` has to gain a
  requirement, and by {need}`DEC_0061` it states its size and its gain first.
- Bad, because a block that needs a published release, or one system only, cannot be
  run whole by a test, as the one tested block already shows.
