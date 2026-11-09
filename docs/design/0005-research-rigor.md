---
status: approved
authors: [claude]
---
# Research rigor

:::{design}
:::

## Overview

The corpus configuration gains `trifecta_rigor`, read by the extension and the checkers.
Two document types join the corpus: surveys under `docs/surveys/` and experiments under
`docs/experiments/`, each with its own need types, schemas and section skeleton. Options
gain two link types to evidence, `supported_by` and `informed_by`. The graph checker tests
those links at every level, and tests that chosen options have support at `evidence` and
above. The check hashes in-repository data; a separate command downloads and hashes
external data. The lifecycle checker, which freezes MADRs and resolved tasks against the
base ref, also freezes experiments at `strict`. The planning files that init writes gain an
evidence step at `evidence` and above.

| Rule | `off` | `evidence` | `strict` |
|---|---|---|---|
| Survey and experiment shapes, link targets, in-repository data hashes | yes | yes | yes |
| Sound support, reviewed evidence, retractions reported | yes | yes | yes |
| Every accepted decision's chosen option has support | | yes | yes |
| Experiments frozen once running; results only when concluded | | | yes |
| Every survey declares its protocol | | | yes |

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

:::{component} Rigor setting
:id: COMP_RIGOR_LEVEL
:satisfies: REQ_RIGOR_LEVEL
:constrained_by: DEC_0017
The `trifecta_rigor` value in `docs/conf.py`, registered by the extension with the default
`off` and checked against the three levels. Every rule below that depends on the level
reads it from here.
:::

:::{component} Survey type
:id: COMP_SURVEY_TYPE
:satisfies: REQ_SURVEY_SHAPE, REQ_SURVEY_PROTOCOL
:constrained_by: DEC_0018, DEC_0020
The `survey` document type with the sections Question, Protocol, Sources, Claims,
Synthesis and Review; the `source` need with `citation`, `doi` or `url`, `retrieved` and
an optional `retracted`; the `claim` need with a `from` link to one source and a
`locator`; and the `protocol` need with `searched`, `query`, `dates`, `includes` and
`excludes`. At `strict` a survey without a protocol need is a finding. `trifecta new
survey` writes the skeleton.
:::

:::{component} Experiment type
:id: COMP_EXPERIMENT_TYPE
:satisfies: REQ_EXPERIMENT_SHAPE
:constrained_by: DEC_0018
The `experiment` document type with the statuses `planned`, `running`, `concluded` and
`abandoned` and the sections Hypothesis, Method, Results, Conclusion and Review; the
`hypothesis` need with a `prediction`; the `result` need with `data`, `sha256` and, for a
URL, `bytes`; and the `conclusion` need with a `verdict` and a `rests_on` link to results.
`trifecta new experiment` writes the skeleton.
:::

:::{component} Data hashes
:id: COMP_DATA_PIN
:satisfies: REQ_DATA_PINNED
:constrained_by: DEC_0021
A check stage that resolves each in-repository `data` path against the repository root,
refuses a link or a path outside it, hashes the file in chunks and compares the digest
with `sha256`. A result with a URL is checked only for its declared hash and size.
:::

:::{component} Data verifier
:id: COMP_VERIFY_DATA
:satisfies: REQ_EXTERNAL_DATA
:constrained_by: DEC_0021
:provides: IF_VERIFY_DATA
The `trifecta verify-data` command. It streams each external result's data into a SHA-256
and a byte count, keeps nothing on disk, and reports each result whose download differs
from what it declares or could not be read.
:::

:::{component} Evidence links
:id: COMP_EVIDENCE_LINKS
:satisfies: REQ_SUPPORT_SOUND, REQ_EVIDENCE_REVIEWED
:constrained_by: DEC_0022
The `supported_by` and `informed_by` link types from an option to a claim or a result, and
a graph check that each `supported_by` target is sound now: its source carries no
`retracted`, or its experiment is `concluded` with the verdict `supported`. A decision that
is superseded is skipped. Each survey or experiment holding a target of `supported_by`
from an accepted decision counts as relied on, so the review rule applies to it.
:::

:::{component} Evidence duty
:id: COMP_EVIDENCE_DUTY
:satisfies: REQ_EVIDENCE_REQUIRED
:constrained_by: DEC_0019
A graph check, run at `evidence` and `strict`, that the option each accepted decision
chooses has at least one `supported_by` link.
:::

:::{component} Pre-registration
:id: COMP_PREREGISTRATION
:satisfies: REQ_PREREGISTERED
:constrained_by: DEC_0020
At `strict`, the lifecycle checker reads each experiment at the base ref. For one that was
`running`, it compares the hypothesis need, its prediction and the Method section with the
current tree; for one that was `concluded`, it compares the whole file. The extension
reports result and conclusion needs in an experiment that is not `concluded`, and a
conclusion with no `rests_on` link.
:::

:::{component} Evidence planning step
:id: COMP_EVIDENCE_PLANNING
:satisfies: REQ_EVIDENCE_PLANNING
:constrained_by: DEC_0019, DEC_0014
The paragraph that init adds to the CLAUDE.md section and the project skill when the rigor
level is `evidence` or `strict`: before a MADR is accepted, find or produce its evidence
with `trifecta new survey` or `trifecta new experiment`, and link it with `supported_by`.
:::

## Interfaces

:::{interface} Data verification command
:id: IF_VERIFY_DATA
:constrained_by: DEC_0021
`trifecta verify-data` MUST read the corpus from the working directory, MUST print one
finding per result that fails in the check's format, and MUST exit non-zero on any finding.
It MUST time out each download and MUST NOT send credentials or cookies.
:::

## Risks

A pull request can add a result whose URL points anywhere, so the verifier runs only on
demand, reads only `https`, sends nothing but the request, caps each download at its
declared size and keeps nothing. A retraction fails the check on every pull request until
a superseding MADR lands, which is the intent but can block unrelated work for a day. The
check holds the shape of evidence, not its quality: a claim can misread its source, and a
method can fail to test its hypothesis, so evidence that supports an accepted decision is
reviewed before it is relied on.
