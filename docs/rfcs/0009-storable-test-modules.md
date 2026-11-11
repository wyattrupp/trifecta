---
status: draft
authors: [claude]
created: 2026-11-11
---
# Storable test modules

:::{rfc}
:::

## Summary

{need}`DES_0008`'s result store never stores seven proof modules, so every fixture copy
runs them again, and they hold most of the fixture step's test time. This RFC asks which
of them can become storable without weakening {need}`REQ_REUSE_SOUND`: a changed input is
never reused unchecked, and a run that reads what the recorder cannot see is never
stored. It names what each module does that the recorder refuses, what each way of
lifting a refusal would trust, and how each could fail. The choices are wyatt's and stay
open as questions. Building any of this waits until {need}`PLAN_0007` is done.

## Motivation

wyatt, 2026-11-11, asked whether the never-stored modules should "go into a new RFC once
PLAN_0007 is done, or should they stay as the design's accepted cost": "yes", a new RFC.
On when, wyatt, 2026-11-11: waiting for PLAN_0007 "means the execution of it, not the
planning", so this RFC is written now and built after PLAN_0007.

{need}`DES_0008`'s Risks accept that "a test that starts git, Vale or any program other
than the interpreter is never stored". PLAN_0007 task 3 measured that cost. In CI run
42995781425, the baseline wyatt ruled on 2026-11-11 ("we're establishing a measured
baseline here. keep going"), the Linux fixture step took 2826 seconds and the Windows one
2672, against 806 and 1306 before task 3. On Linux the 123 fixture copies spent 10,860
seconds on tests, and these modules held 9,540 of them, summed over the copies:

| Module | Linux seconds | The refusal the profile gives |
|---|---:|---|
| `test_record_trace` | 2344 | runs strace; its tests run only where `os.name` is `posix` |
| `test_adoption` | 2148 | runs git; its test runs only where `os.name` is `posix` |
| `test_record` | 1822 | starts Python children that record into directories of their own |
| `test_store_reuse` | 1289 | as `test_record` |
| `test_init` | 987 | runs git |
| `test_package` | 490 | its wheel build reads the host name, or on Linux probes `/etc/os-release` through a link |
| `test_planning` | 462 | runs git |

Reuse takes every other module to a few hundredths of a second, but those were already
the cheap ones, so reuse as built saves little of what the fixture step spends. The
Windows job's numbers per module are not yet measured.

The recorder keeps only the first reason it refuses a run, so the table holds one reason
per module and hides any others. That first reason is not the first in time: a child's
refusal is merged only when the parent writes its manifest, so any refusal of the
module's own process wins over its children's. Read from the tests' source:

- `test_init`, `test_planning` and `test_adoption` also run bash. In `test_init` one test
  runs the workflow's script through bash with a stub `make`. In `test_planning` the hook
  tests run the hook command through bash. In `test_adoption` one test runs the whole
  adoption guide through bash, which runs pip, git, init and a nested check with Vale.
  Making git a known program would not on its own make these three modules storable.
- `test_adoption` also builds a wheel with `sys.executable -m pip wheel`, the build
  `test_package` runs, so it would meet the host-name refusal with git and bash solved.
- Most of their git use is `git init -q` of an empty directory the test made, in a
  `Repo` helper most tests of `test_init` and `test_planning` share. The code under test
  also runs git: init reads `git remote get-url origin` when no owner is given, and the
  history check reads the base ref.
- `test_record` has tests that start a Python child with `-S`, or a child that runs
  `git --version` or another program, to see the recorder refuse them. Those tests stay
  unstorable under every direction below, unless they move to a module of their own.

The security review of this RFC found a gap in the recorder as built: on Linux,
`os.uname()` and `platform.node()` read the host name and raise no audit event, so a
run that reads the host name that way can be stored without it, against
{need}`REQ_REUSE_SOUND`. `platform.system()`, `platform.uname()` and
`sysconfig.get_platform()` call `os.uname()` too, so refusing every call could make
modules stored today unstorable. How and when to close it is {need}`Q_UNAME`.

## Terms

:::{term} Known program
:id: TERM_KNOWN_PROGRAM
:synonyms: trusted program, allowlisted program
A program other than the interpreter that the recorder lets a run start without refusing
the run, because the design states every input the program reads under the arguments
and environment it was started with, and the recorder records those inputs.
:::

:::{term} Nested recording
:id: TERM_NESTED_RECORDING
:synonyms: stacked recorder
A Python child that its parent's recorder records while the child also runs a recorder
of its own, as the tests of the recorder and the store start: the child's own recorder
serves the test, and the parent's recorder records the child for the parent's manifest.
:::

## Requirements

:::{req} Every refusal is named
:id: REQ_REFUSALS_NAMED
The profile of a test run MUST name, for each module the store did not store, every
reason the recorder refused it, not only the first, each with the process that raised
it, the module's own or a named child, and SHOULD give each test's wall time, so the
cost of each refusal is measured before any is lifted. Naming a reason MUST NOT change
whether the run is stored. A reason MUST hold no environment value, and a path in it
holds the root's placeholder in place of the root, since CI's job summary is public. As
{need}`REQ_PROFILED` holds for every profile, the numbers are only reported.
:::

:::{req} A known program's inputs are recorded
:id: REQ_KNOWN_PROGRAM
A run that starts a program other than the interpreter MAY be stored only when the
design names that program as a {need}`known program <TERM_KNOWN_PROGRAM>` for the
arguments and environment it was started with, and the manifest records every input the
design states it reads under them, or, where the design names tracing for it, every
input a trace of that start found: its executable, each file and directory it reads
that the run did not make, and its environment, whole or narrowed to a list the design
states, since no trace sees a variable read. The program MUST be named
by its resolved absolute path, which is not under the repository and not one the run
made, with that file's hash recorded; a start through a shell, a script, or on Windows a
`.cmd` or `.bat` file MUST keep the refusal. So MUST a start the design does not name,
and one whose arguments or environment hold an option or variable not on a list the
design states for that program. So MUST a start where the program's effective
configuration, or a file in the place it works on, such as a hook, would make it run a
further program, such as a hook, an alias, a filter, a signing program, a credential
helper, a pager or an editor, move it to read elsewhere, or let it reach the network.
On each platform where a lift is made, a test MUST show that the program opens, probes
and lists nothing outside its stated inputs and connects nowhere, as the `strace` test
does for the interpreter's native code; on a platform without that proof the refusal
stays unless wyatt rules otherwise, which is {need}`Q_GIT_KNOWN`.
:::

:::{req} A nested recording is the parent's own
:id: REQ_NESTED_RECORDING
A Python child that runs a recorder of its own MAY be stored only through
{need}`nested recording <TERM_NESTED_RECORDING>`, in which the parent's recorder records
that child as it records any Python child. The manifest the child's own recorder writes
MUST NOT stand for the child in the parent's manifest, since the test that started the
child chose that recorder's configuration, its ignore list and the refusals it provokes. The
parent's recorder MUST load under a name of its own; a start whose environment already
holds the parent's variable, and any write into a directory the parent's recorder
prepared other than that recorder's own, MUST keep the refusal. A child in which the
parent's recorder cannot tell, at each child start and at exit, that its own audit hook
and wrappers stayed in place, with its handling of each child start not bypassed, MUST
keep the refusal. Code in the same process can step around a wrapper without replacing
it; the design MUST list those ways, and the refusal stays while any is open, unless
wyatt rules the gap acceptable, which is {need}`Q_NESTED`.
:::

:::{req} The host's identity is an input, refused or not read
:id: REQ_HOST_READS
A read of the host's identity, such as its name through `socket.gethostname`,
`os.uname` or `platform`, or its operating system's release file, MUST make the run
unstorable unless it is recorded as an input, as a hash and never the value, as
{need}`IF_MANIFEST` records an environment variable, or is taken out of the run. The
design MUST list the ways a run reads it, and a test MUST show each way it lists is
seen. A host name is recorded only by the recorder taking it itself, since the
calls that read it carry no value to the hook, and a lookup MUST take it again to match
it, so recording it adds an input kind to IF_MANIFEST and to the store's lookup. A read
through a link outside the repository that the run did not make MAY be recorded, with
the link's target and the target's content, only for paths the design names; every
other such read stays refused, the time zone's files among them, which PLAN_0007 left
out as the clock is.
:::

:::{req} Each lifted refusal is proven
:id: REQ_LIFT_PROVEN
Each refusal this RFC lifts MUST come with tests, declared for {need}`REQ_REUSE_SOUND`,
in which a change to each input the lift records makes the module run again, in which
a start outside the lift's terms is still refused, and in which each input the design
states the lift does not record, such as a git alternates file, a `.git` file, an
`includeIf` or a program planted on `PATH`, either makes the module run again or is
refused. `trifecta fixtures` and
`trifecta fixtures --fresh` MUST give the same result for every fixture after each lift,
on Linux and on Windows.
:::

## Questions

:::{question} Which modules are in scope, and in what order?
:id: Q_SCOPE_MODULES
Scope is wyatt's ruling. The seconds above favour `test_record_trace`, `test_adoption`
and `test_record`, but the first two are also the hardest to make sound, and the names
{need}`REQ_REFUSALS_NAMED` asks for may show other blockers. One order is to name every
refusal first, then lift the cheapest sound ones, then measure again.
:::

:::{question} Is git a known program, and on what terms?
:id: Q_GIT_KNOWN
Directions, each with what it trusts and how it fails:

- **git on a repository the run made.** Allow a fixed list of subcommands, such as
  `init`, `rev-parse`, `commit` and `remote get-url`, only in a directory the run
  created, with `init` before any other. Every git call of the code under test uses
  `-C`, and the recorder refuses a change of working directory, so `-C` is allowed only
  when it names a directory the run made. The repository's own files are then the run's
  output, not inputs, but only while git reads nowhere else: a `.git` file naming
  another directory, an `objects/info/alternates` file, a `commondir`, a
  `core.worktree`, git's search upward for an enclosing repository before `init`, any
  global option not on a stated list, such as `--git-dir`, `--work-tree`,
  `--exec-path`, `--template`, `--config-env`, `--attr-source` and `--namespace`, and
  every `GIT_*` variable that names a path, such as `GIT_DIR`, `GIT_COMMON_DIR`,
  `GIT_OBJECT_DIRECTORY`, `GIT_ALTERNATE_OBJECT_DIRECTORIES`, `GIT_WORK_TREE`,
  `GIT_INDEX_FILE`, `GIT_CONFIG_SYSTEM`, `GIT_CONFIG_GLOBAL`, `GIT_TEMPLATE_DIR` and
  `GIT_EXEC_PATH`, all move it, so each is refused, or its target recorded. A start
  without `GIT_CEILING_DIRECTORIES`, set by the test, is refused, since the recorder
  sets no pin; git does not search into the ceiling itself, so the ceiling is the made
  directory's parent. `-c` is allowed only for named keys, such as `user.name` and
  `user.email`, and `GIT_CONFIG_PARAMETERS`, `GIT_CONFIG_COUNT` and its keys are
  refused. A hook is a file, not a setting: any file in the repository's `.git/hooks`
  other than git's samples is refused at each start, whether the test wrote it or
  `init` copied it from a template. The inputs left
  include the git executable, its exec path and the helpers under `libexec/git-core`;
  the system, global and XDG configuration files, `%PROGRAMDATA%\Git\config` on
  Windows, and every file they include, where `includeIf` makes the result depend on the
  repository's path and on other settings; the XDG `git/ignore` and `git/attributes`
  files and those `core.excludesFile` and `core.attributesFile` name; the mailmap; the
  template directory `init` copies, `info/exclude` and hooks among it; and the `GIT_*`,
  `HOME`, `XDG_CONFIG_HOME`, `PATH` and locale variables. On Windows, `cmd\git.exe` is a
  launcher that starts `mingw64\bin\git.exe` and its libraries. These are examples, not
  a whole list: the direction trusts that a list the design states is whole for those
  subcommands on every git version that runs the check, and where no list can be closed
  on a platform the refusal stays. It fails if a setting starts a program, such as
  `core.fsmonitor`, `core.hooksPath`, an alias, a credential helper, or
  `commit.gpgSign` with `gpg.program`; if `commit` runs a hook from the templates; or if
  `commit` starts `gc` or `maintenance` on its own, which can go on writing after the
  manifest is written. So the recorder would have to read the effective configuration
  and refuse any such setting. A commit also reads the clock for its dates; a test whose
  result does not depend on them is outside the clock rule {need}`RFC_0008` leaves out,
  but one that compares commit IDs is not.
- **git on this repository.** The history check, setup's `ls-files`, and `trifecta new`,
  which runs `git config user.name` in the repository and so reads its `.git/config`
  beside the global files, read refs, objects, packs, the index or the configuration,
  which no stated list covers without tracing each call. This likely stays refused.
- **Pinning git's configuration.** The recorder starts git with `GIT_CONFIG_NOSYSTEM`,
  an empty `GIT_CONFIG_GLOBAL` and an empty template directory, so the configuration is
  no input. It trusts nothing new, but it changes what the code under test sees, such as
  the `user.name` `trifecta new` reads. A pin set by the recorder can change a finding,
  so a pin belongs to the test, never to the recorder.
- **Tracing git on Linux.** Run each git child under `strace` and take its manifest from
  the calls. It trusts `strace` and the kernel, costs a traced start for every call, and
  leaves Windows refused. A trace holds no environment reads, since `getenv` is no
  system call, so the child's whole environment would have to be recorded beside it.

Linux can check each direction with `strace`; Windows cannot. {need}`DES_0008`'s Risks
already accept that gap for native code; whether it is acceptable for git is wyatt's
ruling.
:::

:::{question} Where do the tests that run bash live?
:id: Q_BASH
bash runs whatever its script names, so it cannot be a known program on stated inputs,
and {need}`REQ_KNOWN_PROGRAM` keeps it refused. One direction is to move each test that runs bash, the workflow test in `test_init` and
the hook tests in `test_planning`, into a module of its own, so the rest of each module
can be stored. That trusts nothing new; it changes only where a test lives, and its
`@proves` moves with it. `test_adoption` runs the whole adoption guide through bash,
with pip, init and Vale, and would likely stay fresh.
:::

:::{question} How does the recorder follow a child that records itself?
:id: Q_NESTED
Directions, each with what it trusts and how it fails:

- **Merge the child's own manifest.** The parent reads the manifest the child's recorder
  wrote. Both recorders load from the same copy's `record.py`, so the code is no
  different; but the test chose the child's configuration and ignore list, and its
  tests provoke refusals on purpose, so the child's manifest records what the test
  asked, not what the parent needs. {need}`REQ_NESTED_RECORDING` rules this out.
- **Stack two recorders.** The parent's recorder gives the grandchild a directory of its
  own under a second variable, since it already rewrites every Python child's
  environment, and its recorder starts first; the test's recorder starts after it. None
  of this works today: the `.pth` line reads only `TRIFECTA_RECORD`, the start source
  loads nothing when `_trifecta_record` is already loaded, and `start` removes
  `TRIFECTA_RECORD` from the process, so the parent's recorder starting first would
  delete the test's variable. Stacking needs a second `.pth` line, start source and
  module name, each a change to the installed environment and a point to trust. The
  parent's audit hook sees every event, the test recorder's own included, and the test
  recorder's reads of its own directory fall under what the run made. It fails in five
  ways. The test recorder wraps `subprocess.Popen._execute_child` last, so its wrapper
  runs first and sets `TRIFECTA_RECORD`, and the parent's wrapper then refuses the
  grandchild's own Python children as recording into a directory of their own; the
  parent's wrapper has to run first, or tell a stacked variable from a test's, and
  which is a choice for the design.
  Code in the grandchild can step around a wrapper without replacing it: every wrapper
  keeps its original in `__wrapped__` and in its closure, `os._Environ.__getitem__`
  reads past the recording mapping, and the recorder lists `sys.addaudithook` and
  `object.__setattr__` as harmless; a check at child start and at exit that the hook and
  wrappers are in place sees none of that, nor a swap put back before exit; whether a
  gap of this kind, stated, is acceptable is wyatt's ruling, and until then
  {need}`REQ_NESTED_RECORDING` keeps the refusal. A test, or a recorder a fixture
  changed, could set the parent's variable or rewrite a `config.json` the parent's
  recorder wrote to widen its ignore list, since writes into a recorder's own directory
  are not recorded; both have to be refused, while the test's recorder still writes its
  own manifest into the directory the test prepared. And two hooks per event make each
  grandchild slower, by an amount to measure.

The tests in `test_record` that provoke a refusal on purpose stay unstorable either way.
:::

:::{question} How is `test_package`'s host read handled?
:id: Q_HOST
The wheel build reads the host name, and on Linux probes `/etc/os-release`, a link to
`/usr/lib/os-release`. Which code reads them is not yet found. Directions:

- **Record them.** A hash of the host name, and the link with its target and the
  target's hash, as {need}`REQ_HOST_READS` allows. The calls that read the name carry
  no value to the audit hook, so the recorder takes the name itself, and the store
  takes it again at every lookup: a new input kind in IF_MANIFEST and the store. CI
  runners change their host name every run, so this reuses within one run's 123 copies, where the time is, and not
  across runs. A hash of a host name is guessable, and a store CI publishes is public,
  the same as for an environment value today.
- **Take the read out.** Find the reader and give it what it needs through the test's
  own environment, if the reader allows that. It trusts nothing new, but it holds only
  while that reader does not change.
:::

:::{question} Does `test_record_trace` stay fresh?
:id: Q_TRACE_FRESH
Its subject is the recorder's blind spot: it shows that native code reads nothing the
recorder misses. A reuse keyed on a manifest the recorder wrote cannot see a change to
an input the recorder missed, which is what the test exists to catch. Directions:

- **Stay fresh in every copy**, as today: 2344 seconds on Linux.
- **Key it on what `strace` saw**, not on the recorder's manifest. It trusts `strace`,
  which sees the file, network and listing calls it is told to trace, of the command it
  traces, which also records itself; a change to the installed
  distributions changes the identity and runs it again. `strace` traces only the build
  and the test child the module starts, not the module's own process, so that process
  stays keyed on the recorder's manifest; the traced half's key has to say what it does
  with reads under `/proc`, `/dev` and the temporary directory, and holds no environment
  reads, since `getenv` is no system call.
- **Run it once per job rather than in every fixture copy.** This changes what a
  fixture copy proves, so it is a scope ruling.
:::

:::{question} How and when is the recorder's `os.uname` gap closed?
:id: Q_UNAME
On Linux, `os.uname()` raises no audit event, so a stored run may have read the host
name through it, which {need}`REQ_REUSE_SOUND` forbids. Directions: wrap `os.uname` and
refuse on any call, at the cost of every module that calls `platform.system()`,
`platform.uname()` or `sysconfig.get_platform()`, which is not yet counted; wrap it and
record the host name as {need}`Q_HOST` describes; or wrap it and record only the fields
other than the host name, which a caller of `platform.system()` reads. Whether this is
fixed in PLAN_0007, in the plan that builds this RFC, or before either, is wyatt's
ruling.
:::

:::{question} Is the unit stored the module or the test?
:id: Q_UNIT
Today one refusal in a module makes the whole module unstorable. Storing each test on
its own would keep a refusal to its test, but costs a recorded child for each test, and
a process start is the dearest step on Windows. Moving the refusing tests into modules
of their own, as {need}`Q_BASH` and {need}`Q_NESTED` describe, keeps the module as the
unit and gets most of the same effect.
:::

## Out of scope

Proposed, for wyatt's ruling under {need}`Q_SCOPE_MODULES`. A time budget or target: none
exists (wyatt, 2026-11-10: "No number yet"), and any is only reported (wyatt,
2026-11-10: "Report only"). Any change to {need}`REQ_REUSE_SOUND`. Network access, and
Vale, make and pip as known programs. A test whose result depends on the clock or on
chance, as {need}`RFC_0008` leaves out. The Sphinx build's reuse and the CI cache, which
are {need}`PLAN_0007`'s tasks 4 and 5. The number of fixtures, and splitting them across
more CI jobs. An adopting repository's CI, which gets no store until a later change.

## Review

:::{review} Correctness; security
:id: REV_RFC_0009_1
:k: 2
:date: 2026-11-11
:digest: ae2eee6dd5a026b880af7b8660af1bee73a87782502c5093e2e0261f796a87af
Two rounds, one reviewer per lens, each checking claims against the recorder, the store,
the tests and {need}`DES_0008`. Folded in from correctness: stacking two recorders needs
a second `.pth` line, start source and module name, and the wrappers of
`_execute_child` run in the wrong order for it; merging a child's manifest is ruled out
on the test's configuration, not on its code; `-C` is allowed only on a directory the
run made, since every git call of the code under test uses it; `trifecta new` reads the
repository's own configuration; `test_adoption` also builds a wheel; a parent's refusal
always wins over a child's; tracing finds inputs a stated list does not, and sees no
variable read; the requirements no longer decide the Windows proof, the host reads,
bash's place or the wrapper gaps, which stay questions. Folded in from security: the
ways git reads outside a repository the run made, through a `.git` file, alternates,
global options, path variables, the search upward and hook files; `-c` and
`--config-env` limited to named keys; a known program named by its resolved path, never
a shell, a script or a planted file; writes into the parent's recorder directories and
its variable refused; negative tests for the inputs a lift leaves out; reasons in the
public profile hold no value and no root. Found by the security pass and confirmed under
Linux: `os.uname()` and `platform.node()` raise no audit event, a gap in the recorder as
built, now {need}`Q_UNAME`. Dropped: that `test_record_trace` and `test_adoption` have no
platform rule, since `only_on` keeps their tests to `posix`.
:::
