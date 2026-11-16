---
status: accepted
date: 2026-11-15
decision-makers: [wyatt]
informed: [claude]
---
# An adopting repository takes the rules whole

:::{decision}
:chooses: OPT_0062_WHOLE
:resolves: Q_ADOPTER_RULES
:::

## Context and Problem Statement

{need}`RFC_0010` records that the author of the book it reads gave up on a framework to
suit every project, and holds that the best rules grow from the people who work under
them. It finds this does not hold for a session, for which rules a person sets are the
control, and does hold for a team that adopts the tool. The init command hands an
{need}`adopting repository <TERM_ADOPTER>` the types, the rules and the hook
whole. Which of them it may change or leave out is open.

Measured on 2026-11-15 at commit `50ff955`:

| Reading | Value |
| --- | --- |
| Files the init command writes | 12, and a hook, a skill, a settings entry and a section of `CLAUDE.md` |
| What the `docs/conf.py` it writes holds | an import of every name of the package's types, and the project's name |
| Settings the package offers an adopting repository | 1, the fixture audit, which is off there |
| Switches that leave out or change a rule | none found |
| Requirements in the ten RFCs | 70 |
| Of those, ids found anywhere in the shipped package | 45 |
| Of those, ids found as a string in its Python | 39 |
| Repositories of the owner's account with the tool's name in theirs | 3: the tool, its template, and a repository that checks the template |
| Last push to the template and to the repository that checks it | 2026-11-10 |
| Repositories of that account whose lock file pins the package, by GitHub's code search | none returned |

How each was read: the files from the function that lists them in `init.py`; settings by
a search for where the extension adds one; switches by a search of the check and the
extension for a way to skip a rule; ids by two searches of the package, one of every
file and one of quoted strings in Python; repositories from GitHub by `gh`.

So an adopting repository takes every rule or none. Its one setting is its name. Its
`docs/conf.py` is Python that runs after the import, so it can assign over any name the
package gave it; that is a way round the rules that nothing designed and nothing checks.
And no repository has adopted the tool but the template and the one that checks it, so
nobody has yet asked to leave a rule out.

Three limits. An id found in the package is not shown to be a rule the check holds: the
45 counts mentions in comments, and the ask that was put called the range enforced. Code
search can miss or lag, and a repository outside that account would not show. And the
owner's other standards tool, kept outside this repository, was not looked at.

## Decision Drivers

- What is left of the book's fault in {need}`RFC_0010`: rules handed whole to a team
  that had no part in them
- {need}`DEC_0061`: a part of the tool states its measured gain, and there is no
  adopting repository to measure a way out against
- {need}`REQ_ONE_PACKAGE`: an adopting repository holds no copy of the rules
- A check that means one thing in every repository

## Considered Options

:::{opt} Whole, until an adopting repository asks
:id: OPT_0062_WHOLE
The rules ship whole and no way to leave one out is built. The first adopting repository
that needs a rule left out or changed reopens the question, with its case as the
evidence. Good, because nothing is built for a need nobody has. Good, because the check
means the same thing wherever it passes. Bad, because the book's fault stands for the
first team that adopts: it works under rules it had no part in. Bad, because the way
round through `docs/conf.py` stays open and unseen.
:::

:::{opt} Leave out with a record
:id: OPT_0062_RECORD
An adopting repository may name a rule to leave out, and holds a decision record of its
own for each; the check prints what was left out. Good, because the rules a team works
under are then ones its own person ruled on. Bad, because it is built before anyone
needs it.
:::

:::{opt} A fixed core and an optional rest
:id: OPT_0062_TIERS
Some rules are fixed and the others may be left out. Good, because what the check always
means is named. Bad, because each rule has to be sorted, on no adopting repository's
evidence.
:::

:::{opt} Any, freely
:id: OPT_0062_ANY
The configuration is the adopting repository's to change as it likes. Good, because it
is what is possible today, made plain. Bad, because a passing check then says nothing
that holds across repositories.
:::

## Decision Outcome

Chosen option: {need}`OPT_0062_WHOLE`, because wyatt, 2026-11-15, choosing from Claude's
recommendations with the readings above in the ask: "None, until an adopter asks
(Recommended)".

## Consequences

- Good, because the tool gains nothing from this answer.
- Bad, because the question is put off and not closed: this record says when it is
  asked again, and a later one will have to supersede it.
- Bad, because an assignment in `docs/conf.py` can still change a type or a rule in an
  adopting repository with no finding, and this leaves that as it is.
- Bad, because the part of the book's fault that holds, rules that did not grow from
  those under them, is accepted here and not answered.
