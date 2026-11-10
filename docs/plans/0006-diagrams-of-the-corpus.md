---
status: active
authors: [claude]
created: 2026-11-08
---
# Diagrams of the corpus

:::{plan}
:implements: DES_0007
:::

## Read before starting

{need}`RFC_0007` and the MADRs that resolve its questions. {need}`PLAN_0005`,
{need}`PLAN_0002` and {need}`PLAN_0003` are done first: the directives land in the package
that plan 0003 builds, and its init writes the index that holds them.

## Rules for every task

Each requirement gets its negative fixture in the task that enforces it, and each built
component gets its `spec` path in the same task. The unmutated corpus passes at the end of
every task, on Linux and Windows. Tests compare DOT text, never SVG, and each names the
requirement it proves, as DEC_0015 has the check read it. An edit to the reviewed text of
a relied-on document is reviewed k=2 and stamped in the same task.

## Tasks

:::{task} Renderer and guards
:id: TASK_0006_01
:builds: COMP_DIAGRAM_RENDERER, COMP_PROGRAM_GUARD, COMP_PAGE_GUARD
:gate: The fixtures that add a `needflow` directive to an RFC and add `sphinx.ext.graphviz` to the configuration are rejected under REQ_DIAGRAMS_IN_PROCESS; the fixtures that add an `https` script through `html_js_files`, and raw HTML holding an image at `//`, a `preload` link, a style with `url()`, a style with `@import`, a `meta` refresh, a `base` element, and an `<svg><style>`, an `<svg><script>` and an `<svg><style><img>` each loading from outside, are rejected under REQ_PAGES_SELF_CONTAINED; the tests that render a two-node graph with no warning, a graph whose labels hold quotes, backslashes, angle brackets and `URL=`, to an SVG the allowlist passes, and a graph whose need text holds Graphviz label escapes such as `\N` and `\G`, drawn as that text, pass on Linux and Windows.
The renderer and the rules that keep it the only way to draw.

- [ ] **1.1** Add `pygraphviz==2.0.4` to the lock with the hashes of its five wheels and no source archive, each compared with the hash PyPI lists; check PyPI for attestations of the five files; record in the As built entry what was compared, the bundled Graphviz version and the vendored libraries.
- [ ] **1.2** Pass `--only-binary=:all:` to every install of the lock: the setup script, the Makefile and CI here, and the files init writes; add pygraphviz to the package's dependencies and to the lock init writes.
- [ ] **1.3** Add `timeout-minutes` to this repository's workflow jobs and to the workflow init writes.
- [ ] **1.4** Write the renderer as COMP_DIAGRAM_RENDERER states, and its tests.
- [ ] **1.5** Write the program guard and the page guard as their components state.
- [ ] **1.6** Add the fixtures, `<svg><style>`, `<svg><script>` and `<svg><style><img>` among them, and set the three `spec` paths.
- [ ] **1.7** Add a renderer test that Graphviz label escapes such as `\N` and `\G` in need text render as that text, not as the node's or the graph's name.
:::

:::{task} Meta-model directive
:id: TASK_0006_02
:builds: COMP_METAMODEL_DIAGRAM
:gate: The fixtures that give the `metamodel` directive content, add a second one to the index, add one to an RFC, and remove it from the index, are rejected under REQ_DIAGRAMS_DERIVED; the test that compares its DOT text for the package's configuration passes.
The smaller of the two diagrams first.

- [ ] **2.1** Make `_same_file` in the configuration record its child type on the link it returns.
- [ ] **2.2** Write the directive as COMP_METAMODEL_DIAGRAM states, with its placement rules, and its DOT test.
- [ ] **2.3** Add the directive to this repository's index and to the index init writes.
- [ ] **2.4** Add the fixtures, and set the component's `spec` path.
:::

:::{task} Trace directive
:id: TASK_0006_03
:builds: COMP_TRACE_DIAGRAM
:gate: The fixtures that remove the `trace` directive from the index and add one to a plan are rejected under REQ_DIAGRAMS_DERIVED; the tests that compare its DOT text for a corpus with an unsatisfied requirement, an open question and a done plan pass, and show both labels and no status on the done plan's tasks.
The last task, so it also closes the design.

- [ ] **3.1** Write the directive as COMP_TRACE_DIAGRAM states, with the meta-model's placement rules applied to it, and its DOT tests.
- [ ] **3.2** Add the directive to this repository's index and to the index init writes.
- [ ] **3.3** Add the fixtures, and set the component's `spec` path.
- [ ] **3.4** Mark DES_0007 implemented, check that every requirement of RFC_0007 has its fixture, and review this plan's As built k=2.
:::

## Review

:::{review} Correctness; security
:id: REV_PLAN_0006_1
:k: 2
:date: 2026-11-08
The review recorded as {need}`REV_RFC_0007_1` covered this document.
:::

:::{review} Correctness; security
:id: REV_PLAN_0006_2
:k: 2
:date: 2026-11-09
:digest: dc208ac06f617100aba0177a5cbd1c0cb3e5cdab4dad10f18861c04058f5013c
:::

## As built
