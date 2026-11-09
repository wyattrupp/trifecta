---
status: accepted
date: 2026-11-08
decision-makers: [wyatt]
consulted: [claude]
---
# Diagrams are drawn by Graphviz from the lock

:::{decision}
:chooses: OPT_0026_PYGRAPHVIZ
:resolves: Q_DIAGRAM_ENGINE
:driven_by: REQ_DIAGRAMS_IN_PROCESS, REQ_DIAGRAMS_DERIVED, REQ_PAGES_SELF_CONTAINED
:::

## Context and Problem Statement

The design shown on 2026-11-08 drew the diagrams with Mermaid in the reader's browser,
and named Graphviz as the alternative with better layouts and no script, at the cost of
a second binary to pin on every platform. wyatt, 2026-11-08, ruled: "Use Graphviz".

Graphviz publishes a hashed binary archive only for Windows; Linux and macOS users are
pointed at package managers. pygraphviz 2.0.4 publishes wheels for Linux and macOS on
x86-64 and ARM and for Windows on x86-64 that bundle Graphviz's libraries, and its
`layout` and `draw` call Graphviz's `gvLayout` and `gvRender` in the calling process.

## Decision Drivers

- wyatt's ruling: Graphviz draws the diagrams
- What the build runs is pinned: Python dependencies by hash in the lock, as the toolchain
  stage checks, and Vale by checksum, as REQ_PINNED_TOOLCHAIN requires
- The platforms REQ_PLATFORM_TOOLCHAIN lists all draw diagrams, with nothing new to set up
- A diagram needs no script, and no built page needs the network

## Considered Options

:::{opt} pygraphviz from the hashed lock, drawing in the build's process
:id: OPT_0026_PYGRAPHVIZ
Good, because the lock already pins every Python wheel by hash on every platform, so
Graphviz comes with `pip install` and needs no row in the Vale table, no download and no
program on the path. Bad, because the bundled Graphviz version, and the cairo, pango,
fontconfig and other libraries vendored beside it, are whatever the pygraphviz release
ships, out of sight of tools that read the lock; and the wheels add about 5 MB to the
install.
:::

:::{opt} sphinx-needs' `needflow` with the `dot` program
:id: OPT_0026_NEEDFLOW
Good, because sphinx-needs draws the diagrams with no code of ours. Bad, because it runs
`dot` as a program, which has no hashed release for Linux or macOS, so each platform
would install it from a package manager, unpinned.
:::

:::{opt} Mermaid, drawn in the reader's browser
:id: OPT_0026_MERMAID
Good, because one script file serves every platform. Bad, because wyatt ruled for
Graphviz, and every reader then runs a 3 MB script.
:::

## Decision Outcome

Chosen option: {need}`OPT_0026_PYGRAPHVIZ`, because it is Graphviz, as wyatt ruled, and
it is the one way to get Graphviz pinned by hash on every platform the check supports.

## Consequences

- Good, because the diagrams are SVG in the page, readable with scripts off.
- Good, because the build's process is the only place a diagram is drawn, so the check
  can refuse the directives and the extension that would run a program.
- Good, because every package in the lock has a wheel, so installs can be binary-only:
  a platform with no pygraphviz wheel fails to install instead of compiling against an
  unpinned system Graphviz.
- Bad, because Graphviz now parses text that contributors write, inside the build's
  process, with no timeout of its own; the design passes that text only as escaped labels
  and bounds the layout.
- Bad, because the vendored libraries are not in the lock, so each pygraphviz bump records
  the bundled Graphviz version and the vendored libraries, and whether PyPI holds
  attestations for the wheels, in the plan that makes it.
- Bad, because Graphviz is licensed under the Eclipse Public License 2.0, which a
  repository adopting trifecta installs as a dependency.
