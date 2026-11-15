---
status: draft
authors: [claude]
created: 2026-11-15
---
# A critique from the Living Documentation book

:::{rfc}
:::

## Summary

Cyrille Martraire's book "Living Documentation" was read in full against this repository.
It supports what the check does: rules held by a tool, one home per fact, and a decision
log that is never edited. It faults how the corpus is produced: documents are written
before the code they describe, far more is written down than the book thinks worth
keeping, and the knowledge about a component sits beside the source and not on it. This
RFC records the twelve faults, records what the book supports so that no answer undoes
it, and puts each fault as a question. It proposes no requirement.

## Motivation

This RFC comes from a reading of Cyrille Martraire's book "Living Documentation", made on
2026-11-15 to find what the book would say of this repository. The book's subject is this
repository's subject: how documentation stays true as the software changes. It was read
whole, for what supports the repository as much as for what faults it. What follows gives
the book's positions in this document's own words and cites no passage; the references
are left out for now.

What was measured in this repository, at commit `f8818bf` on 2026-11-15:

| Reading | Value | Command |
| --- | --- | --- |
| Words under `docs/rfcs`, `docs/decisions`, `docs/design`, `docs/plans` | 78,475 | `wc -w` over each directory's `*.md` |
| Lines of `src/trifecta/*.py` and `src/trifecta/ext/*.py` | 10,598 | `wc -l` |
| Lines of `tests/*.py` | 7,789 | `wc -l` |
| Decision records | 50 | `ls docs/decisions` |
| First and last commit dates | 2026-11-07, 2026-11-14 | `git log --format=%ad --date=short` |

What the book supports:

- A decision log of structured text files beside the code, giving each decision's
  reasons and the options weighed, where an entry is never changed and a new entry
  supersedes it. This is {need}`REQ_DECISION_OPTIONS`, {need}`REQ_IMMUTABLE_DECISIONS`
  and {need}`REQ_SUPERSESSION`.
- A record outside the code for the options that were turned down, since the code cannot
  hold them.
- Rules held by a tool that reports a breach when it happens, so the tool is the
  reference for the rule; a rule nothing can enforce is hardly a rule. This is
  {need}`REQ_FIXTURE_PER_INVARIANT` and the one enforcing component per requirement.
- One home for each piece of knowledge, with every other form produced from it. This is
  {need}`REQ_STATUS_SINGLE_SOURCE` and {need}`REQ_GENERATED_VIEWS`.
- A way to detect a link that broke, wherever a document points straight at a file. This
  is {need}`REQ_LINK_TARGETS` and {need}`REQ_SPEC_RESOLVES`.
- Stating what is wanted before building it, and proving it by a test. This covers a
  requirement and its negative fixture; it does not cover a design doc or a plan.
- A written record for knowledge that has to outlast the people who held it. A coding
  session that starts with no memory of the last one is such a reader.
- Writing something down at once when doing so is cheap. A session that drafts a
  decision record in seconds lowers the cost of writing; the cost of reading and
  reviewing stays.

What the book faults:

1. Documents come before the code. The book names writing documentation before building
   as an abuse of its own method and calls detailed design specifications waste. It
   holds that documentation follows what was built and does not drive it, and that
   designing the whole before implementing any of it no longer fits. Here
   {need}`DEC_0008` makes a spec three kinds of document, a plan follows, and
   {need}`DEC_0014` makes that order the default for a session.
2. A feature nobody built is fully specified. The book says to document only what has
   been built, in answer to a need that was met. {need}`RFC_0007` is accepted and
   {need}`DES_0007` approved, and {need}`PLAN_0006` has no step ticked.
3. Writing a document is the default. The book says a written document is never the
   default, and that only the part of what is known that proved useful again and again
   earns a lasting form. Here every change starts as documents.
4. Too many decisions are recorded. The log the book asks for holds the most important
   decisions, three to five to begin with; a choice that follows a principle already
   written down needs no record of its own; and a good architecture is a few decisions
   that guide the rest. This corpus holds fifty records after eight days, one for each
   choice.
5. The amount of text counts against the design. The book reads many pages spent
   explaining a design as a sign that the design is poor, and names documentation
   becoming unnecessary as the aim. The table above shows the proportion here.
6. Plans are kept. The book treats everything about planning and tracking as short-lived
   and says to throw it away once the work is done, and that the record of a temporary
   process goes when the process does. A done plan stays in the corpus and
   {need}`DEC_0012` freezes its resolved tasks.
7. What is known about a component is not on the component. The book prefers
   {need}`internal documentation <TERM_INTERNAL_DOCUMENTATION>` to
   {need}`external documentation <TERM_EXTERNAL_DOCUMENTATION>`, and ranks a separate
   file of facts about the code last among the ways to add knowledge to it. A design doc
   is such a file. The book makes one allowance that fits: a fact about how files
   relate, and not about one file, belongs outside them.
8. The link from a design doc to the source proves little. The book ranks
   {need}`reconciliation <TERM_RECONCILIATION>` fourth of its four ways to keep
   documentation true, warns against naming a file directly, and shows a check that
   still passes after the behaviour changed as the kind that fails its purpose.
   {need}`REQ_SPEC_RESOLVES` holds that a path exists and that a fragment occurs in it;
   the prose beside the path can go stale and the check passes.
9. Terms are written by hand. The book's glossary is drawn from the names in the source,
   which it treats as the one home of the vocabulary, and it says developers need no
   glossary beyond the code. {need}`REQ_CANONICAL_TERMS` holds prose to terms declared
   in RFCs; nothing compares those terms with the names in `src/`.
10. The diagrams as designed cannot surprise. The book values a generated diagram
    because it shows the code as it is and so can show the author something unexpected.
    {need}`RFC_0007` draws from the needs, which are written by hand, so its diagrams
    show the design as declared.
11. The tool is large, and it is shipped as a framework. The book budgets a few hours
    for a first piece of documentation tooling, gives a worked example of under 170
    lines, and says such tooling serves the code that is delivered and not the reverse.
    Its author gave up on a framework to suit every project and recommends small
    solutions made for one, and says the best rules grow from the people who work under
    them. Here the tool is the product, and `trifecta init` hands its types, its rules
    and its hook to another repository whole.
12. The README holds what changes. The book warns against instructions for developing,
    using and testing in a README, because they change often. Most of this repository's
    README is such instructions. Two things answer the warning in part: the README names
    no version, and a test runs one of its install blocks.

## Terms

:::{term} Internal documentation
:id: TERM_INTERNAL_DOCUMENTATION
Knowledge about an artifact that is held in that artifact, in the technology it is built
with, so that it moves, changes and is deleted with it.
:::

:::{term} External documentation
:id: TERM_EXTERNAL_DOCUMENTATION
Knowledge about an artifact that is held in another file, which a change to the artifact
does not touch.
:::

:::{term} Reconciliation
:id: TERM_RECONCILIATION
A check that two statements of the same knowledge still agree, run because either can
change without the other.
:::

## Requirements

## Questions

:::{question} Who is the corpus written for?
:id: Q_CORPUS_READER
:::

:::{question} Does a change start from documents or from code?
:id: Q_BUILD_ORDER
:::

:::{question} What becomes of an accepted RFC and an approved design that nothing builds?
:id: Q_UNBUILT_DESIGN
:::

:::{question} Which choices get a decision record?
:id: Q_DECISION_BAR
:::

:::{question} What bounds the size of the corpus and of the tool?
:id: Q_CORPUS_SIZE
:::

:::{question} How long does a done plan stay in the corpus?
:id: Q_PLAN_LIFETIME
:::

:::{question} Where is a component described, in a design doc or in its source?
:id: Q_COMPONENT_HOME
:::

:::{question} What does a spec path prove about the prose beside it?
:id: Q_SPEC_STRENGTH
:::

:::{question} Are terms compared with the names in the source?
:id: Q_TERM_SOURCE
:::

:::{question} Are diagrams drawn from the needs or from the code?
:id: Q_DIAGRAM_SOURCE
:::

:::{question} Which rules can an adopting repository change or leave out?
:id: Q_ADOPTER_RULES
:::

:::{question} What does the README hold?
:id: Q_README_SCOPE
:::

## Out of scope

Whether the book is right; the parts of the book about business domains, conversations
between roles in a team, and documentation produced by a running system, which have no
counterpart here; any change to what the book supports, listed above; a requirement,
until the questions are answered.

## Review
