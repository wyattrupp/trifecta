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
evidence that supports it. Evidence that goes bad, a retracted source or a retracted
experiment, fails the decisions resting on it until a new MADR supersedes them.

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
prediction merged before the results, data that still hashes to what was reported, a
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
`strict`, and MUST default to `off`; the check MUST reject any other value. The init
command MUST write the setting, at the level it is given. The check MUST apply the
stricter of the level at the base ref and the level in the tree.
:::

:::{req} Surveys have a fixed shape
:id: REQ_SURVEY_SHAPE
A survey MUST hold sections for its question, protocol, sources, claims, synthesis and
review. Each source MUST give a citation, a DOI or an `https` URL with no user
information, and the date it was retrieved, and MAY carry a `retracted` field with the
date and the reason. Two sources MUST NOT share a DOI, compared without case, or, for a
source with no DOI, a URL without its fragment; any other survey MUST reference the
source by its ID. A `retracted` field present at the base ref MUST NOT be removed or
changed. Each claim MUST link from exactly one source and MUST give a locator in it, such
as a page or section.
:::

:::{req} Experiments have a fixed shape
:id: REQ_EXPERIMENT_SHAPE
An experiment MUST have the status `planned`, `running`, `concluded` or `abandoned`, MUST
move only forward through them, to `abandoned` from `planned` or `running`, and MUST hold
sections for its hypothesis, method, results, conclusion and review. Its hypothesis MUST
state the prediction that would support it. Each result MUST name its data as a path in
the repository or an `https` URL with no user information, with the data's SHA-256 as 64
lowercase hexadecimal digits. An experiment MUST hold at most one conclusion, which MUST
give the verdict `supported`, `refuted` or `inconclusive` and MUST link the results of
the same experiment it rests on. A concluded experiment MAY carry a `retracted` field with
the date and the reason.
:::

:::{req} Data is pinned by hash
:id: REQ_DATA_PINNED
The check MUST refuse, before any filesystem access, a `data` path that is not a relative
POSIX path, or that holds an empty, `.` or `..` segment, a drive, a backslash, a colon
anywhere, or a segment ending in a dot or a space. It MUST refuse a segment that names a
reserved device, matched without case: `CON`, `PRN`, `AUX`, `NUL`, `CONIN$`, `CONOUT$`,
`COM0` to `COM9`, `COM¹` to `COM³`, `LPT0` to `LPT9` or `LPT¹` to `LPT³`, with or without
an extension. The data MUST be a regular file tracked by git at exactly that path
and case, MUST NOT be or sit under a symbolic link or other reparse point, and MUST NOT
be a Git LFS pointer. The check MUST hash it and report a difference from its SHA-256. A
result whose data is at a URL MUST declare its size as a positive number of bytes. The
check MUST NOT access the network.
:::

:::{req} External data is verified on demand
:id: REQ_EXTERNAL_DATA
A separate command MUST download the data of every result whose data is at a URL and
report each whose SHA-256 or size differs from the declared one. It MUST fetch only
`https` URLs with verified certificates, MUST refuse a host unless every address it
resolves to is a global address, read after unwrapping IPv4-mapped, NAT64 and 6to4 forms,
MUST connect to an address it checked, MUST check every redirect the same way, and MUST
follow no more redirects than a limit fixed in the package. It MUST request the content
without encoding and hash the bytes as received, MUST read at most one byte more than the
declared size, or than a size limit fixed in the package if that is smaller, MUST report
more bytes than declared as a size difference, and MUST stop at a deadline fixed in the
package. It MUST NOT read credentials, proxies or certificate settings from the
environment, MUST NOT send credentials or cookies, and MUST NOT write, unpack or run what
it downloads.
:::

:::{req} Support comes only from sound evidence
:id: REQ_SUPPORT_SOUND
At every rigor level, each `supported_by` link of an accepted decision MUST point only at
a claim whose source is not retracted, or at a result that the conclusion of its
experiment rests on, where that experiment is `concluded` with the verdict `supported`
and is not retracted. An `informed_by` link MAY point at any claim or result and MUST NOT
count as support.
:::

:::{req} Evidence relied on is reviewed
:id: REQ_EVIDENCE_REVIEWED
A survey or experiment that holds evidence linked by `supported_by` from an accepted
decision MUST carry a review of its current text, as REQ_REVIEWED and REQ_REVIEW_CURRENT
require of a relied-on document.
:::

:::{req} Decisions cite evidence
:id: REQ_EVIDENCE_REQUIRED
At the rigor levels `evidence` and `strict`, the chosen option of every accepted decision
MUST have at least one `supported_by` link.
:::

:::{req} Experiments are pre-registered
:id: REQ_PREREGISTERED
At the rigor level `strict`, an experiment new since the base ref MUST be `planned`, and
an experiment MUST move at most one status forward since the base ref, other than to
`abandoned`. One `running` at the base ref MUST keep the hypothesis, prediction and method
it had there. One `concluded` at the base ref MUST NOT change, except in its Review
section and by gaining a `retracted` field. One `running` or `concluded` at the base ref
MUST NOT be removed, or moved to another path or ID. Results and a conclusion MUST appear
only in a `concluded` experiment.
:::

:::{req} Surveys declare their protocol
:id: REQ_SURVEY_PROTOCOL
At the rigor level `strict`, every survey MUST declare its protocol: where it searched,
the query, the date range, and what it included and excluded. A protocol present at the
base ref MUST NOT change.
:::

:::{req} Planning finds evidence first
:id: REQ_EVIDENCE_PLANNING
The planning instructions that init writes MUST direct a session, when the rigor level is
`evidence` or `strict`, to find or produce the evidence for a decision, as a survey for
prior work or an experiment for anything measurable, and to link it before the decision
is accepted. They MUST direct the session to treat retrieved sources and data as data,
not instructions, to ask the user before downloading or running anything, and to remove
credentials and personal data from data before it is committed.
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

Judging whether a method, a source or a statistical test is sound, and whether a survey
cites its own authors' work, which stay with the review; replication, meaning two
independent pieces of evidence per decision, which wyatt did not take; evidence for
requirements and for options a decision did not choose; checking a source's citation
against an index; a limit on the size of data in the repository; moving this repository
past the rigor level `off`, which would need evidence for every accepted decision here and
is a decision of its own.

## Review

:::{review} Correctness; security
:id: REV_RFC_0005_1
:k: 2
:date: 2026-11-08
The research-rigor set at commit 2df849b: this RFC, {need}`DEC_0017` to
{need}`DEC_0022`, {need}`DES_0005` and {need}`PLAN_0004`. No off-lineage pass ran; the
local model was down. Folded in: experiments arrive `planned`, move one status at a time
and forward only, and cannot be removed or moved once running; a concluded experiment
stays open to its review and a retraction; the stricter of the base and tree levels
applies; retractions and protocols are frozen; sources have an identity key; support is
judged for accepted decisions only and needs the conclusion to rest on the result; relied-on
evidence needs a current review digest; data paths are refused as text before any
filesystem access, and must be tracked regular files with no link, reparse point or LFS
pointer; the verifier refuses non-public addresses, checks every redirect, ignores the
environment's credentials and proxies, hashes raw bytes and caps size and time, and its
findings hold no server text; init writes the level, and the planning paragraph is written
at every level; the retraction lands with its superseding MADR; the fixture runner gains
base mutations and finding locations; the plan names package paths and waits for plans
0002 and 0003 in its first gate. Not taken: making a level change its own pull request,
since the stricter-of rule already holds the line; a cut-off for decisions accepted before
the level was raised, which is a ruling for wyatt and is recorded as a consequence in
DEC_0017; freezing a supporting claim's source fields, which the current-digest rule
covers; a size limit on data in the repository, now out of scope.
:::

:::{review} Correctness; security
:id: REV_RFC_0005_2
:k: 2
:date: 2026-11-09
:digest: 3e63a79632e8f6b6981ae28ef92e7031604d7828136fc8dd2a8e5522d8810e56
:::
