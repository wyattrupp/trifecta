---
status: accepted
date: 2026-11-15
decision-makers: [wyatt]
informed: [claude]
---
# Outside Python a definition is a key or a heading

:::{decision}
:chooses: OPT_0065_KEY_OR_HEADING
:resolves: Q_NON_PYTHON_DEFINITION
:::

## Context and Problem Statement

{need}`REQ_SPEC_EXACT` has a `spec` path resolve to one definition and
{need}`REQ_SPEC_NAMED_BACK` has that definition name its need. {need}`DEC_0053` left open
what a definition is, and where a comment on it goes, in a file that is not Python.

Measured on 2026-11-15 at commit `1ec2b54`, over the 49 `spec` paths:

| Reading | Value |
| --- | --- |
| Paths into files that are not Python | 7 |
| By format | YAML 4, TOML 1, JSON 1, Markdown 1 |
| Paths with no fragment | 3 |
| Fragments that are the key of a job in a workflow, found once as a key | 2 |
| Fragments that are the name of a workflow step, found twice | 1 |
| Fragments that are a Markdown heading | 1 |
| Formats among them that cannot hold a comment | 1, JSON |

How each was read: the lines of each file that hold the fragment, by eye for which is a
key, a heading or a comment.

## Decision Drivers

- {need}`DEC_0053`: the address is exact and held both ways
- Seven components are built from files that are not Python, and they are components
  like the rest
- A format with no comments cannot name anything back

## Considered Options

:::{opt} A key or a heading, with a comment where the format allows
:id: OPT_0065_KEY_OR_HEADING
In YAML and TOML a definition is a key that occurs once as a key; in Markdown it is a
heading. The id of the need goes in a comment directly above it. A file whose format
holds no comment is named whole, with no fragment, and owes no name back. Good, because
six of the seven are held as exactly as Python is. Bad, because the step name found
twice has to be pointed at another way. Bad, because each format is one more thing for
the check to read.
:::

:::{opt} Exact rules for Python only
:id: OPT_0065_PYTHON_ONLY
Outside Python a `spec` path is held as now. Good, because nothing is built. Bad,
because the fault {need}`DEC_0053` answers stays for seven components.
:::

:::{opt} A whole file only
:id: OPT_0065_WHOLE_FILE
Outside Python a `spec` path takes no fragment. Good, because it is simplest. Bad,
because one job of a workflow can no longer be pointed at.
:::

## Decision Outcome

Chosen option: {need}`OPT_0065_KEY_OR_HEADING`, because wyatt, 2026-11-15, choosing from
Claude's recommendations with the readings above in the ask: "Key or heading; comment if
possible (Recommended)".

## Consequences

- Good, because the two requirements now say what they ask of every format in use.
- Bad, because a format not among the four has no rule, and the first one used will
  need it.
- Bad, because the component built from the ruleset in JSON is tied to its file from
  one side only.
