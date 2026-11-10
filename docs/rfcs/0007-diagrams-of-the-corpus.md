---
status: accepted
authors: [claude]
created: 2026-11-08
---
# Diagrams of the corpus

:::{rfc}
:::

## Summary

The built docs draw two kinds of diagram, both from the graph the check already builds:
a {need}`meta-model <TERM_META_MODEL>` of the need types and the link types between
them, and a {need}`trace <TERM_TRACE>` for each RFC. Both are generated, so they cannot
drift from the corpus. Graphviz lays them out inside the build, from the hashed Python
lock, and the page embeds them as SVG, so a diagram needs no script and the build runs no
extra program. The check reports a built page whose attributes or CSS load anything from
outside the build.

## Motivation

wyatt, 2026-11-08, listed "visualizing the ontology" among what users might want, and set
the order "Windows, then visualization, then research rigor". On the design for this
RFC, wyatt, 2026-11-08, ruled: "Use Graphviz".

Today the corpus can be read only one document at a time. The types and link types live
in `docs/conf.py`, and the links between needs show up only as text on each need. Whether
an RFC's requirements are satisfied, built and decided is a question the check answers
with findings, not one a reader can see at a glance.

## Terms

:::{term} Meta-model
:id: TERM_META_MODEL
The need types of the corpus and the link types between them, as `docs/conf.py`
defines them.
:::

:::{term} Trace
:id: TERM_TRACE
For one RFC: its requirements with the components that satisfy them and the tasks that
build those, and its questions with the decisions that resolve them.
:::

## Requirements

:::{req} Diagrams are derived
:id: REQ_DIAGRAMS_DERIVED
One document MUST hold exactly one meta-model directive and exactly one trace directive,
and every other document MUST hold neither. Each directive MUST take no content, argument
or option, and MUST draw only from the configuration and the built graph. The trace
directive MUST draw one trace for every RFC, and MUST mark in words, not only by color,
a requirement that no component of an approved or implemented design satisfies and a
question that no accepted decision resolves.
:::

:::{req} Diagrams are drawn inside the build
:id: REQ_DIAGRAMS_IN_PROCESS
Diagrams MUST be laid out and rendered in the build's own process by the Graphviz that
the hashed lock installs, and embedded in the page as SVG that holds no script, event
handler, foreign object, image, or link to anything but a page of the build. The text of
a need MUST reach a diagram only as a label, never as markup or as an attribute. The check
MUST report the sphinx-needs `needflow`, `needuml` and `needarch` directives, and any
loaded extension among `sphinx.ext.graphviz`, `sphinx.ext.inheritance_diagram` and the
PlantUML and Mermaid extensions.
:::

:::{req} Built pages load nothing from outside the build through attributes or CSS
:id: REQ_PAGES_SELF_CONTAINED
The check MUST report, in every built page, an address in an attribute that loads a
resource, or in a CSS `url()` or `@import`, that resolves outside the built site once
normalized as a browser normalizes it, and any `base` element or `meta` refresh. A link a
reader follows is not a load.
:::

## Questions

:::{question} What draws the diagrams?
:id: Q_DIAGRAM_ENGINE
:::

:::{question} Where do the diagrams live?
:id: Q_DIAGRAM_PLACE
:::

## Out of scope

An interactive explorer page; a command that writes diagrams outside the build; diagrams
of research-rigor evidence, which plan 0004 can add to the trace once its types exist;
pixel-identical SVG across platforms, since fonts differ; a rule against raw HTML, inline
scripts or hand-drawn images in documents, which would be a new authoring rule for wyatt
to make. The page guard reads attributes and CSS only, so an inline script or an
event-handler attribute in raw HTML can still fetch from outside the build; closing that
gap needs the same authoring rule. Also out of scope: `docs/conf.py`, which is trusted
code and can run anything.

## Review

:::{review} Correctness; security
:id: REV_RFC_0007_1
:k: 2
:date: 2026-11-08
The diagram set before its first commit: this RFC, {need}`DEC_0026`, {need}`DEC_0027`,
{need}`DES_0007` and {need}`PLAN_0006`. No off-lineage pass ran; the local model was
down. Folded in: need text reaches Graphviz only through pygraphviz's API as escaped
labels, and the SVG is held to an element and attribute allowlist with the `aria-label`
set through a parser; the guard for programs reads the loaded extensions, so
`sphinx.ext.inheritance_diagram` and the PlantUML and Mermaid extensions count; the
off-build rule is its own requirement, parses every page, normalizes addresses as a
browser does, covers every loading attribute, CSS `url()` and `@import`, `base` and
`meta` refresh, and has a fixture for each kind; placement names one document and leaves
the index to DEC_0027; directives fill placeholders after sphinx-needs resolves links,
merge across parallel reads, and keep the index current on incremental builds; the trace
uses the same predicates as REQ_COVERAGE and REQ_RFC_ACCEPTANCE and treats `done` as
settled; unique graph IDs, `role="img"`, layout bounds, captured Graphviz warnings and a
workflow time limit; binary-only installs, the vendored libraries and attestations
recorded on each bump, and the lock and dependencies init writes; tests name the
requirement they prove; each task's guard rules land with its directive. Not taken: a
rule against raw HTML, inline scripts or hand-drawn images in documents, a new authoring
rule left to wyatt; loading only Graphviz's layout and core plugins, which pygraphviz does
not expose.
:::

:::{review} Correctness; security
:id: REV_RFC_0007_2
:k: 2
:date: 2026-11-09
:digest: 21cef5b682f3921c36fa92a64d0c3d451031664d559956f6eba190776e6243f0
:::
