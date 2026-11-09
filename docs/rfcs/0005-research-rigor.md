---
status: accepted
authors: [claude]
created: 2026-11-08
---
# Research rigor

:::{rfc}
:::

## Summary

A repository chooses how much evidence its decisions need, with one
{need}`rigor level <TERM_RIGOR_LEVEL>`: off, evidence or strict. Two new document types
hold the {need}`evidence <TERM_EVIDENCE>`: a {need}`survey <TERM_SURVEY>` of prior work,
made of sources and the claims taken from them, and an
{need}`experiment <TERM_EXPERIMENT>`, made of a hypothesis with its prediction, results
pinned to their data by hash, and a conclusion. A decision's chosen option links the
evidence that supports it. Evidence that goes bad, a retracted source or a refuted
prediction, fails the decisions resting on it until a new MADR supersedes them.

## Motivation

wyatt, 2026-11-08, asked "how they might run their repository with a research rigor, such
as requiring surveys of literature, or experiments using the scientific method, to prove
out ideas", and, asked whether that meant software decisions or research: "I believe both
is the only way to truly be properly thorough. I do like the configuration piece you
mentioned, though".

Today a MADR records why an option was chosen in its own words, and nothing checks that
the reasons rest on anything. A benchmark run, a user study, a training run and a review
of papers are all evidence of the same kind to the check: a statement, where it came
from, and whether it still holds. The check can hold the structure of that evidence: a
prediction stated before the results, data that still hashes to what was reported, a
source that has not been retracted. It cannot judge whether a method was sound; that stays
with the review.

## Terms

:::{term} Rigor level
:id: TERM_RIGOR_LEVEL
The one setting that decides what evidence a repository's decisions need: off, evidence or
strict.
:::

:::{term} Survey
:id: TERM_SURVEY
A document under `docs/surveys/` that reviews prior work as sources and the claims taken
from them.
:::

:::{term} Experiment
:id: TERM_EXPERIMENT
A document under `docs/experiments/` that tests one hypothesis against a prediction
stated before its results.
:::

:::{term} Evidence
:id: TERM_EVIDENCE
A claim from a survey or a result from an experiment, as a decision links it.
:::

## Requirements

:::{req} The rigor level is one setting
:id: REQ_RIGOR_LEVEL
The rigor level MUST be set once, in the corpus configuration, to `off`, `evidence` or
`strict`, and MUST default to `off`. The check MUST reject any other value.
:::

:::{req} Surveys have a fixed shape
:id: REQ_SURVEY_SHAPE
A survey MUST hold sections for its question, protocol, sources, claims, synthesis and
review. Each source MUST give a citation, a DOI or an `https` URL, and the date it was
retrieved, and MAY carry a `retracted` field with the date and the reason. A source MUST
be defined once in the corpus, and any other survey MUST reference it by its ID. Each
claim MUST link from exactly one source and MUST give a locator in it, such as a page or
section.
:::

:::{req} Experiments have a fixed shape
:id: REQ_EXPERIMENT_SHAPE
An experiment MUST have the status `planned`, `running`, `concluded` or `abandoned`, and
sections for its hypothesis, method, results, conclusion and review. Its hypothesis MUST
state the prediction that would support it. Each result MUST name its data as a path in
the repository or an `https` URL, with the data's SHA-256. A conclusion MUST give the
verdict `supported`, `refuted` or `inconclusive`.
:::

:::{req} Data is pinned by hash
:id: REQ_DATA_PINNED
The check MUST hash the data of every result whose data is in the repository and MUST
report a result whose data is missing, differs from its SHA-256, is a link, or resolves
outside the repository. A result whose data is at a URL MUST declare its size in bytes,
and the check MUST NOT access the network.
:::

:::{req} External data is verified on demand
:id: REQ_EXTERNAL_DATA
A separate command MUST download the data of every result whose data is at a URL and
report each whose SHA-256 or size differs from the declared one. It MUST fetch only
`https` URLs, MUST NOT follow a redirect to any other scheme, MUST stop reading once a
download exceeds its declared size, and MUST NOT write, unpack or run what it downloads.
:::

:::{req} Support comes only from sound evidence
:id: REQ_SUPPORT_SOUND
At every rigor level, a `supported_by` link MUST point only at a claim whose source is
not retracted, or at a result of an experiment concluded with the verdict `supported`.
An `informed_by` link MAY point at any claim or result and MUST NOT count as support. An
accepted decision whose chosen option is supported by a claim of a retracted source MUST
be reported until a decision supersedes it.
:::

:::{req} Evidence relied on is reviewed
:id: REQ_EVIDENCE_REVIEWED
A survey or experiment that holds evidence linked by `supported_by` from an accepted
decision MUST carry a review, as a relied-on document does.
:::

:::{req} Decisions cite evidence
:id: REQ_EVIDENCE_REQUIRED
At the rigor levels `evidence` and `strict`, the chosen option of every accepted decision
MUST have at least one `supported_by` link.
:::

:::{req} Experiments are pre-registered
:id: REQ_PREREGISTERED
At the rigor level `strict`, an experiment that is `running` or `concluded` at the base
ref MUST keep the hypothesis, prediction and method it had there, and one `concluded` at
the base ref MUST NOT change at all. Results and a conclusion MUST appear only in a
`concluded` experiment, and the conclusion MUST link the results it rests on.
:::

:::{req} Surveys declare their protocol
:id: REQ_SURVEY_PROTOCOL
At the rigor level `strict`, every survey MUST declare its protocol: where it searched,
the query, the date range, and what it included and excluded.
:::

:::{req} Planning finds evidence first
:id: REQ_EVIDENCE_PLANNING
At the rigor levels `evidence` and `strict`, the planning instructions that init writes
MUST direct a session to find or produce the evidence for a decision, as a survey for
prior work or an experiment for anything measurable, and to link it before the decision
is accepted.
:::

## Questions

:::{question} Where is the rigor level set?
:id: Q_RIGOR_SCOPE
:::

:::{question} What documents carry the evidence?
:id: Q_EVIDENCE_TYPES
:::

:::{question} What does the evidence level demand of a decision?
:id: Q_EVIDENCE_DUTY
:::

:::{question} What does the strict level add?
:id: Q_STRICT_RIGOR
:::

:::{question} Where does experiment data live?
:id: Q_DATA_HOME
:::

:::{question} What happens when evidence goes bad?
:id: Q_BAD_EVIDENCE
:::

## Out of scope

Judging whether a method, a source or a statistical test is sound, which stays with the
review; replication, meaning two independent pieces of evidence per decision, which
wyatt did not take; evidence for requirements and for options a decision did not choose;
fetching or checking a source's citation against an index; moving this repository past
the rigor level `off`, which would need evidence for every accepted decision here and is
a decision of its own.
