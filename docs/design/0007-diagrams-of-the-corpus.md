---
status: approved
authors: [claude]
---
# Diagrams of the corpus

:::{design}
:::

## Overview

The extension gains two directives, `metamodel` and `trace`, which the index holds once
each. Each leaves a placeholder where it stands; once sphinx-needs has resolved every
link, the placeholder is replaced with a graph built through pygraphviz's API, with every
need's text as an escaped label, sorted so the same corpus gives the same DOT text. One
renderer lays the graph out and renders it to SVG in the build's process, holds the SVG to
a short list of elements and attributes, and embeds it in the HTML page. pygraphviz joins
the hashed lock with its five wheel hashes, and every install is binary-only. Two check
stages report what would draw with a program, and any built page whose attributes or CSS
load something from outside the build.

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

:::{component} Diagram renderer
:id: COMP_DIAGRAM_RENDERER
:satisfies: REQ_DIAGRAMS_IN_PROCESS
:constrained_by: DEC_0026
One function in the extension that takes a `pygraphviz.AGraph` and the diagram's name.
Graphs are built only through `add_node` and `add_edge`, with attributes from a fixed
list: label, shape, style, color, font and a link to the need's page. A label is a plain
quoted string with its backslashes doubled, never an HTML-like label, so no text a need
holds becomes markup, an escape or an attribute. The graph's `id` is unique per diagram,
so element IDs do not repeat on the index, and fixed `nslimit`, `nslimit1`, `mclimit` and
`searchsize` values bound the layout. The function logs the diagram's name, then calls
`layout("dot")` and `draw(format="svg")` with no arguments, so Graphviz runs in the
build's process, recording Python warnings throughout and logging each as a Sphinx warning
that names the diagram. It parses the SVG, reports any element outside `svg`, `g`,
`title`, `path`, `polygon`, `polyline`, `ellipse`, `text` and `a`, any attribute whose
name starts with `on`, and any link that is not a relative `.html` page with a fragment,
and sets `role="img"` and the `aria-label` through the parser. The `aria-label` is the
diagram's fixed title, never need text. The HTML builder
emits the result as a raw node inside a `figure` captioned with the diagram's title;
every other builder emits the title only. The font is one the render test shows draws
with no warning on Linux and Windows.
:::

:::{component} Meta-model directive
:id: COMP_METAMODEL_DIAGRAM
:satisfies: REQ_DIAGRAMS_DERIVED
:constrained_by: DEC_0026, DEC_0027
The `metamodel` directive. It reads `needs_types` from the configuration: one node per
type, labelled with its title and ID prefix, and one edge per link type from the type
that declares it to each target type, labelled with the link's outgoing name. A derived
link's target is the child type that `docs/conf.py`'s `_same_file` helper records on the
link; it is drawn dashed and its label says "derived". Types and links are sorted by
name. The directive records where it stands, merged across parallel reads, and reports
itself outside the index, twice on the index, missing from the index, or given content,
an argument or an option.
:::

:::{component} Trace directive
:id: COMP_TRACE_DIAGRAM
:satisfies: REQ_DIAGRAMS_DERIVED
:constrained_by: DEC_0026, DEC_0027
The `trace` directive. In `doctree-resolved`, from sphinx-needs' resolved needs, it draws
one diagram per RFC, in ID order, each under a heading that links to the RFC: the RFC's
requirements, each with the components that satisfy it and the tasks that build those
components, and its questions, each with the decisions that resolve it. Every node is
labelled with its ID and title and links to the need. A requirement no component of an
approved or implemented design satisfies is labelled "unsatisfied", and a question no
accepted decision resolves "open", the predicates REQ_COVERAGE and REQ_RFC_ACCEPTANCE
use; a need whose document is not accepted, approved, active, done or implemented carries
its status. Color repeats these labels and never replaces them. Nodes and edges are
sorted by ID. The index is marked outdated on every build, so an incremental build never
shows a stale trace. Its placement rules are the meta-model directive's.
:::

:::{component} Program guard
:id: COMP_PROGRAM_GUARD
:satisfies: REQ_DIAGRAMS_IN_PROCESS
At `builder-inited`, reports any loaded extension among `sphinx.ext.graphviz`,
`sphinx.ext.inheritance_diagram`, `sphinxcontrib.plantuml` and `sphinxcontrib.mermaid`,
read from the extensions Sphinx has loaded, not from the configuration's list; and
reports every `needflow`, `needuml` or `needarch` node in a read document. Every install
of the lock passes `--only-binary=:all:`.
:::

:::{component} Page guard
:id: COMP_PAGE_GUARD
:satisfies: REQ_PAGES_SELF_CONTAINED
A stage of the check that parses every built page with `html.parser` and collects every
address that loads something: `src`, `srcset`, `poster`, `background`, `data` and `ping`
attributes, `href` on `link`, `image`, `use` and SVG `feImage`, `script` and `cursor`,
`codebase` on `object`, `imagesrcset` on `link`, `xlink:href`, and the string addresses of `url()`, `image-set()`, `image()` and `@import`
in `style` elements and attributes, read after CSS escapes are decoded. Each address is
normalized as a browser normalizes it, with leading and trailing spaces and control
characters removed, tabs and line breaks dropped, backslashes turned to slashes and the
scheme lowercased, then resolved against the page. An address with a scheme other than
`data`, one starting with `//`, or one that resolves outside the built site is reported,
as is any `base` element, `meta` refresh or `srcdoc` attribute, any `style` or `script`
element inside `svg`, and any `animate` or `set` whose `attributeName`, compared
lowercased, is one of the attributes above or `style`, or whose `from`, `to`, `by` or
`values` holds `url(`. A `data` address is reported in an
`iframe`, `frame`, `object`, `embed`, `script` or `link`, and anywhere when its media
type, the text of the `data` address before its first `;` or `,`, trimmed and lowercased,
is `text/html` or `image/svg+xml`.
:::

## Interfaces

## Risks

pygraphviz pins a Graphviz release, and the libraries vendored with it, of its own
choosing, so a fault in either waits for a pygraphviz release, and Graphviz parses
contributor text in the build's process; escaped labels, the SVG allowlist and the layout
bounds narrow that, and the workflow's time limit ends a hung build. An adopting repository
on an earlier release fails REQ_DIAGRAMS_DERIVED after upgrading until its index holds the
two directives, which the finding names. SVG differs by platform where fonts differ, so
no test compares it; tests compare the DOT text. A large corpus makes a long index and slow layouts; the trace
is per RFC, so no one layout holds the whole graph. macOS draws with the same wheels but
no CI job runs there. CI runs the pull request's own `docs/conf.py`, checker and page
guard, so a pull request can weaken them, and the maintainer's review of the pull request
is the safeguard for them, since no ruleset requires an approval. The page guard reads
attributes and CSS only, so an inline script, an event-handler attribute, or a form's
`action` or `formaction` in raw HTML can still fetch from outside the build. The guard
parses with Python's HTML parser, which reads `script` and `style` inside `svg`
differently from a browser, so it reports those elements there, and a fixture holds
`<svg><style><img src="https://x/">`.

## Review

:::{review} Correctness; security
:id: REV_DES_0007_1
:k: 2
:date: 2026-11-08
The review recorded as {need}`REV_RFC_0007_1` covered this document.
:::

:::{review} Correctness; security
:id: REV_DES_0007_2
:k: 2
:date: 2026-11-09
:digest: 7e43a1d882bcc5def304064ce3bb83fb5346e359dc28574d104af40747e20055
:::
