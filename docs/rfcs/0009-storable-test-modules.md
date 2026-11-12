---
status: draft
authors: [claude]
created: 2026-11-11
---
# Storable test modules

:::{rfc}
:::

## Summary

{need}`DES_0008`'s result store never stores seven proof modules on `main`, and an
eighth on PR #32, so every fixture copy
runs them again, and they hold most of the fixture step's test time. This RFC asks which
of them can become storable without weakening {need}`REQ_REUSE_SOUND`: a changed input is
never reused unchecked, and a run that reads what the recorder cannot see is never
stored. It names every reason the recorder raises in the Python code it follows in each module,
measured on Linux and Windows, what each way of lifting a refusal would trust, and how each could fail. Where
a question had a measurable answer, the measurement is recorded with it; what is left is
wyatt's to rule. wyatt has ruled that all eight modules are in scope, "ordered by
highest possible speedup", and that git is lifted. Building any of this waits until
{need}`PLAN_0007` is done.

## Motivation

wyatt, 2026-11-11, asked whether the never-stored modules should "go into a new RFC once
PLAN_0007 is done, or should they stay as the design's accepted cost": "yes", a new RFC.
On when, wyatt, 2026-11-11: waiting for PLAN_0007 "means the execution of it, not the
planning", so this RFC is written now and built after PLAN_0007. On the questions, wyatt,
2026-11-11: "all of those questions seem to be empirically answerable", so each was
measured where it could be. On scope, order and git, wyatt, 2026-11-11: "they're all in
scope, and ordered by highest possible speedup. lift git".

{need}`DES_0008`'s Risks accept that "a test that starts git, Vale or any program other
than the interpreter is never stored". PLAN_0007 task 3 measured that cost. In CI run
42995781425, the baseline wyatt ruled on 2026-11-11 ("we're establishing a measured
baseline here. keep going"), the Linux fixture step took 2826 seconds and the Windows one
2672, against 806 and 1306 before task 3. On Linux the 123 fixture copies spent 10,860
seconds on tests, and seven modules held about 9,540 of them, summed over the copies. Task 4
added an eighth: in CI run 43120488764, on PR #32's head, `test_build_reuse` took 4852
seconds on Linux and 8903 on Windows, and the fixture step 3593 and 5266.

The recorder keeps only the first reason it refuses a run, and stops looking after it.
To find every reason, a copy of the recorder that logs each refusal with its stack and
keeps recording was run on each module, on Windows 11 and on Debian 12 under WSL, on
2026-11-11; the scripts and logs are not kept in the repository. The runner did not
apply `only_on`, so a reason is counted below only from a test on its own platform. The
probe sees what the recorder raises in Python code it follows, nothing inside git, bash,
Vale or another program, and Linux was Debian 12, not CI's Ubuntu 24.04, whose pip and
system paths can differ. Seconds are CI's, summed over the copies; the reasons are the
probe's:

| Module | Linux seconds | Every reason the probe found |
|---|---:|---|
| `test_build_reuse` | 4852 | a Python child that records into a directory of its own, in 7 of its 10 tests; the other 3 raise none; measured on Windows only |
| `test_record_trace` | 2344 | runs strace, in the 2 tests that run where `os.name` is `posix`; the build test is 35.9 of the module's 37.3 seconds |
| `test_adoption` | 2148 | runs git and bash; the wheel build's child, on Linux, reads `/etc/os-release`, `/etc/mtab` and `/etc/rmt` through links and runs `lsb_release` and `uname`, all from pip's `distro` |
| `test_record` | 1822 | a Python child that records into a directory of its own, in 25 of the 30 tests that run on Linux; a child with `-S` in one; none in four; on Windows, ctypes in one test's `setUp` |
| `test_store_reuse` | 1289 | a Python child that records into a directory of its own, in 3 of 4 tests |
| `test_init` | 987 | runs git, through the `Repo` most of its tests share, and bash in one; its `trifecta check` and `trifecta new` children run git, and the check children Vale, and Sphinx changes the working directory while it reads `conf.py`; on Windows, the host name and a WMI query through `toolchain.bin_vale`'s `platform.system()`, and a junction |
| `test_package` | 490 | the wheel build's child: on Linux as in `test_adoption`; on Windows the host name and a WMI query through `platform.system()` in pip's `rich`, ctypes in pip's `platformdirs`, and `rustc`, found on `PATH`, run by pip's user agent |
| `test_planning` | 462 | runs git in most tests and bash in one; about two dozen of the hook's Python children leave no manifest, since the guard refuses through `os._exit(2)`, which runs no `atexit`, and one leaves a malformed one; on Windows, junctions and ctypes |

So a lift of one reason stores little on its own. In `test_init`, the two tests that run
the whole check, 9.96 of 11.2 seconds on Linux and 13.9 of 16.4 on Windows, run Vale
and change the working directory under Sphinx whether or not git and bash are lifted.

The security review of this RFC found a gap in the recorder as built: on Linux,
`os.uname()` and `platform.node()` read the host name and raise no audit event, so a
run that reads the host name that way can be stored without it, against
{need}`REQ_REUSE_SOUND`. `platform.system()`, `platform.uname()` and
`sysconfig.get_platform()` call `os.uname()` too. How and when to close it is
{need}`Q_UNAME`.

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

Each question gives what was measured on 2026-11-11, then what is left to rule.

:::{question} Which modules are in scope, and in what order?
:id: Q_SCOPE_MODULES
Ruled, wyatt, 2026-11-11: "they're all in scope, and ordered by highest possible
speedup". All eight modules are in scope: each reason in the Motivation's table is to
be lifted or taken out of the run, under {need}`REQ_LIFT_PROVEN`, where the other
questions' rulings allow; a reason a ruling keeps refused keeps its module unstored.
The programs the scope brings in that this RFC had left out are {need}`Q_PROGRAMS`.

Proposed reading of "highest possible speedup", for wyatt to confirm: the Linux seconds,
summed over the fixture copies, a module would save once every reason in it is lifted.
Windows seconds, or the fixture step's wall time, where copies run side by side, could
order the list otherwise; `test_build_reuse` alone takes 8903 Windows seconds.

Measured on 2026-11-11 on PR #32's head, `00a998f`, on Debian 12: each module ran as
the proof child runs it, unrecorded, under `strace -f -y`, and every path under the root
that any of its processes read, probed or listed was kept. Listings of the root,
`tests/`, `src/` and `src/trifecta/`, which are on the import path, were dropped, since
the recorder records the import system's listings as the names it looked up, not as the
listing, and by reading the eight modules' own source none lists them itself. A library
or child that lists them would be missed: `flit_core`, in the `pip wheel` child of
`test_adoption` and `test_package`, walks `src/trifecta/`, and no fixture creates or
deletes a file there. `flit_core` may also list the root for its license glob, so rows 2
and 7 count the root's listing, "root" in the table: the fixture that deletes
`.gitattributes`, and for `test_package` the one that creates `bin/`; for any other
module a library's listing of the root would rerun it in at most those two. An import lookup of an absent
name leaves no system call, since the import system answers it from its cached listing,
so the trace does not hold those names. Each path a
fixture creates or deletes counts against a listing of any directory above it. `test_record_trace`'s own `strace`
cannot run under another, so the Sphinx build it traces was traced alone and its paths
added. A fixture copy can reuse a module only if none of its mutations touches one of
those paths. The saving is the module's CI seconds times the copies that can reuse it,
over 123. No module but `test_record_trace` reads the repository's `docs/`, since each
builds its corpus in a directory of its own. The order, from the most saved:

| Order | Module | Copies that can reuse it | Rerun by | Linux seconds saved, at most |
|---:|---|---:|---|---:|
| 1 | `test_build_reuse` | 118 | 5 `src/` | 4655 of 4852 |
| 2 | `test_adoption` | 116 | 5 `src/`, 1 `bin/`, 1 root | 2026 of 2148 |
| 3 | `test_record` | 119 | 4 `src/` | 1763 of 1822 |
| 4 | `test_store_reuse` | 118 | 5 `src/` | 1237 of 1289 |
| 5 | `test_record_trace` | 50 | 73 `docs/` | 953 of 2344 |
| 6 | `test_init` | 117 | 5 `src/`, 1 `bin/` | 939 of 987 |
| 7 | `test_package` | 116 | 5 `src/`, 2 root | 462 of 490 |
| 8 | `test_planning` | 122 | 1 `src/` | 458 of 462 |

Modules 5 and 6 differ by 14 seconds, less than these bounds can settle, so their
order is open. Each figure is an upper bound, counted from one unmutated Linux trace, and is not a
key: it holds only once every reason in that module is lifted; a lift that records more
than the trace saw saves less; a fixture that creates a file under a name a module's
import looked up would rerun it; by reading the imports, no module imports the names
the fixtures create under `tests/`, `helpers`, `support_fx`, `test_fx` and `sub`.
`test_adoption`'s guide failed early under the trace on this machine, so its row counts
only what the test reads before the guide, which works in a directory of its own from
the built wheel; its place in the order holds only until the guide is traced to the
end. What each module waits on, among others:
modules 1 and 4 on {need}`Q_NESTED`; 2 on {need}`Q_GIT_KNOWN`, {need}`Q_BASH`,
{need}`Q_PROGRAMS` and {need}`Q_HOST`; 3 on {need}`Q_NESTED` and {need}`Q_PROGRAMS`; 5 on
{need}`Q_TRACE_FRESH`; 6 and 8 on {need}`Q_GIT_KNOWN`, {need}`Q_BASH` and
{need}`Q_PROGRAMS`; 7 on {need}`Q_HOST`; and 2, 6 and 7 on {need}`Q_UNAME`. Proposed: a lift
shared by several modules is built when the first module in the order that can be
stored needs it.
:::

:::{question} Is git a known program, and on what terms?
:id: Q_GIT_KNOWN
Measured with `strace` on git 2.39.5, Debian 12, for the calls the tests and the code
under test make on a repository the run made, with `GIT_CEILING_DIRECTORIES` at its
parent: `init`, `remote get-url`, `commit` with two `-c` keys, `rev-parse`, `ls-files`
and `cat-file`, as root, with no configuration file present. Outside the made
repository, git read or probed its executables, `/usr/bin/git` and
`/usr/lib/git-core/git`; the dynamic loader's files and its libraries; the locale
archive and git's message catalogs, which `LANG` selects; `/etc/gitconfig`,
`~/.gitconfig` and `~/.config/git/config`, all absent; `~/.config/git/ignore`, in
`ls-files`; the template tree under `/usr/share/git-core/templates`, in `init`;
`/etc/localtime`, in `commit`; and each parent of the made repository and of the
directory git started in. It connected nowhere. `commit` started
`git maintenance run --auto` as a child of its own. The trace kept only absolute paths,
without `strace`'s `-y`, so a read relative to a directory or descriptor outside the
repository would not show; here every such read was under the made `.git`. With no
configuration present, what a configuration can pull in, `include.path`, `includeIf`,
`core.excludesFile`, `core.attributesFile`, `init.templateDir` or `commit.template`, was
not exercised. So the list holds for these calls on this version, with no
configuration; whether it is closed is not shown. CI's Ubuntu 24.04 ships another
version, which is not yet traced, and Windows cannot be traced this way. Paths under
`/proc` and `/dev` were filtered out and are not in this list.

What lifting git would store, measured: nothing on its own, since no module is held by
git alone: `test_init`'s two costly tests also run Vale and change the working
directory under Sphinx, `test_planning`'s hook tests leave no manifest, and
`test_adoption` runs bash and pip.

Directions, each with what it trusts and how it fails:

- **git on a repository the run made.** Allow a fixed list of subcommands only in a
  directory the run created, with `init` before any other, and `-C` only when it names
  such a directory. Refuse every global option not on a stated list, every `GIT_*`
  variable that names a path, a `.git` file, alternates, `commondir`, `core.worktree`,
  `-c` beyond named keys, `GIT_CONFIG_PARAMETERS` and `GIT_CONFIG_COUNT`, a start
  without `GIT_CEILING_DIRECTORIES` set by the test at the made directory's parent, and
  any file in `.git/hooks` other than git's samples. Record the measured inputs above,
  every file the configuration includes, and the `GIT_*`, `HOME`, `XDG_CONFIG_HOME`,
  `PATH` and locale variables. It trusts that the list is whole on every git version
  that runs the check. It fails if a setting starts a program, such as
  `core.fsmonitor`, `core.hooksPath`, an alias, a credential helper or `gpg.program`; so
  the recorder reads the effective configuration and refuses any such setting. The
  measured `git maintenance` child is a further program, which
  {need}`REQ_KNOWN_PROGRAM` refuses, and it can go on writing after the manifest is
  written: a start that may start another git, through maintenance, `gc --auto` or a
  hook, keeps the refusal unless the test passes `-c maintenance.auto=false` and
  `-c gc.auto=0`, both named keys, and a trace on each version shows no program started
  beyond the git the run started. On Windows, where no trace can be taken, a `commit`
  keeps the refusal under any ruling that lifts git without one. A commit reads the
  clock and the time zone for its dates; a test that compares commit IDs is outside the
  clock rule {need}`RFC_0008` leaves out.
- **git on this repository.** The history check, setup's `ls-files` and `trifecta new`
  read refs, objects, packs, the index and the repository's own configuration, which
  no stated list covers without tracing each call. This likely stays refused.
- **Pinning git's configuration.** `GIT_CONFIG_NOSYSTEM`, an empty `GIT_CONFIG_GLOBAL`
  and an empty template directory make the configuration no input. A pin set by the
  recorder can change a finding, such as the `user.name` `trifecta new` reads, so a pin
  belongs to the test, never to the recorder.
- **Tracing git on Linux.** Take each git child's manifest from `strace`. It trusts
  `strace` and the kernel, costs a traced start per call, leaves Windows refused, and
  sees no variable read, so the child's whole environment is recorded beside it.

Ruled, wyatt, 2026-11-11: "lift git". By reading the tests and the code they start,
every git start in the eight modules is on a repository a test made: `Repo` in
`test_init` and `test_planning`, `test_adoption`'s own `git init`, and the code under
test run in them. `test_record` starts `git --version` in a recorded child to prove that
git is refused; it reads no repository the run made and no direction lists
`--version`, so that start stays refused, which is what the test proves. The first
direction would cover the others, and the fourth could;
neither does as things stand:

- the code under test runs subcommands not yet traced: `config user.name` in
  `trifecta new`, and `ls-files --others --exclude-standard` in the check; no test in
  the eight runs the history check, which runs only with `--base`;
- no test sets `GIT_CEILING_DIRECTORIES` or the two maintenance keys, and `test_init`'s
  children keep the real `HOME`, so `user.name` and `core.excludesFile` come from the
  machine's configuration; pinning `HOME`, `GIT_CONFIG_GLOBAL` and
  `GIT_CONFIG_NOSYSTEM` is a change to the tests that must change no finding;
- Git for Windows sets `credential.helper` in its system configuration by default,
  which the first direction refuses;
- some starts are behind bash or make, among them `rev-list` in the CI script
  `test_init` runs and the guide's `make check`, and stay refused with those.

No module in scope runs git on this repository. Left to wyatt: which direction, whether
git on this repository is lifted, and whether
Windows may lift git without a trace, as {need}`DES_0008`'s Risks accept for native
code.
:::

:::{question} Where do the tests that run bash live?
:id: Q_BASH
bash runs whatever its script names, so {need}`REQ_KNOWN_PROGRAM` keeps it refused.
Measured: the bash tests cost little, 0.32 seconds of `test_init` on Linux and 1.06 on
Windows, and 0.17 of `test_planning` on Linux and 0.45 on Windows. Moving them into a module of their own
stores nothing until git, and in `test_init` Vale and the Sphinx working directory, are
lifted too, so it is worth doing only together with those. `test_adoption` runs the whole
adoption guide through bash, so bash keeps that module refused unless one of these
holds. **Run the guide's commands without bash**: the guide is one subshell with
`set -euo pipefail`, `$(...)`, pipes, a redirect, variables and `. activate`, so the
test would carry its own reading of the shell, and would prove that reading rather than
the guide as a reader runs it. **Move the guide's run into a module that stays fresh**:
the proof is unchanged, and the module saves only what its other test costs. **Lift
bash**: {need}`REQ_KNOWN_PROGRAM` forbids it as written. Left to wyatt: whether the bash
tests of `test_init` and `test_planning` move into modules of their own that stay
fresh, and which of these holds for `test_adoption`.
:::

:::{question} How does the recorder follow a child that records itself?
:id: Q_NESTED
Measured: nested recording is the only reason in `test_build_reuse`, raised in 7 of its
10 tests, in 3 of 4 tests of `test_store_reuse`, and in 25 of the 30 tests of
`test_record` that run on Linux: 6141 Linux seconds in CI without `test_record` and
7963 with it, whose `-S` test and Windows ctypes `setUp` also refuse. So moving tests
into modules of their own stores nothing here without following the child; for
`test_record` it takes both.

- **Merge the child's own manifest.** The test chose the child's configuration and
  ignore list, and its tests provoke refusals on purpose, so the child's manifest
  records what the test asked, not what the parent needs. {need}`REQ_NESTED_RECORDING`
  rules this out.
- **Stack two recorders.** The parent's recorder gives the grandchild a directory of its
  own under a second variable, and its recorder starts first. None of this works today:
  the `.pth` line reads only `TRIFECTA_RECORD`, the start source loads nothing when
  `_trifecta_record` is already loaded, and `start` removes `TRIFECTA_RECORD`, so the
  parent's recorder starting first would delete the test's variable. Stacking needs a
  second `.pth` line, start source and module name. The test recorder wraps
  `subprocess.Popen._execute_child` last, so its wrapper runs first; the parent's has to
  run first, or tell a stacked variable from a test's. A test, or a recorder a fixture
  changed, could set the parent's variable or rewrite a `config.json` the parent's
  recorder wrote, so both are refused, while the test's recorder still writes its own
  manifest where the test prepared it. The cost of two hooks per event is measured once
  stacking is built; one recorded start that imports the test stack costs 1.35
  seconds on Linux and 2.07 on Windows today.

Code in the grandchild can step around a wrapper without replacing it: every wrapper
keeps its original in `__wrapped__` and its closure, `os._Environ.__getitem__` reads
past the recording mapping, and the recorder lists `sys.addaudithook` and
`object.__setattr__` as harmless. A check at child start and at exit sees none of that.
Left to wyatt: whether a gap of this kind, stated, is acceptable for code the
repository's own tests run; until then {need}`REQ_NESTED_RECORDING` keeps the refusal,
and modules 1, 3 and 4 of {need}`Q_SCOPE_MODULES`'s order stay unstored.
:::

:::{question} How is `test_package`'s host read handled?
:id: Q_HOST
Measured: the reader is pip, not the package. On Linux pip's `distro` reads
`/etc/os-release`, `/etc/mtab` and `/etc/rmt` through links and runs `lsb_release` and
`uname`; on Windows pip's `rich` calls `platform.system()`, which reads the host name and
runs a WMI query, pip's `platformdirs` loads ctypes, and pip's user agent runs `rustc`
when one is on `PATH`. The test runs `pip wheel --no-build-isolation`, so pip only calls
`flit_core`'s build hook. Calling `flit_core.buildapi.build_wheel` directly, in a
recorded child at the repository's root, gave the wheel with no refusal and no input
outside the repository and the interpreter's prefixes, which the environment key
stands for through the interpreter's version and the installed distributions, as for
every stored module, on Linux and on Windows. It was measured with `-E`, not under the test's own
environment, and the wheel was not compared with pip's.

So taking the read out works for `test_package`, and recording a host name, a new input
kind, is not needed for it. It trusts nothing new; the test then proves the wheel the
backend builds, not pip's call of it. `test_adoption`'s guide runs pip by design and
keeps the reads. trifecta's own `toolchain.bin_vale` calls `platform.system()`, a host
read on Windows, and on Linux through the `os.uname` gap of {need}`Q_UNAME`, which
`os.name` avoids. Left to wyatt: whether the test may build through
the backend.
:::

:::{question} Does `test_record_trace` stay fresh?
:id: Q_TRACE_FRESH
Measured: the module's own manifest holds six files under the root, `tests/__init__.py`
and `tests/test_record_trace.py` among them, and none under `docs/`, while the Sphinx
build it traces reads `docs/`; `strace` starts that build, so the module's recorder
never follows it. A reuse keyed on the module's own manifest would therefore reuse the module after
a document changed, which {need}`REQ_REUSE_SOUND` forbids. The build child does write a
whole manifest of its own, which is what the test checks, but
{need}`REQ_NESTED_RECORDING` rules out standing on it; short of that, only a key taken
from what `strace` saw, beside the module's own manifest, could be sound. The build test is 35.9 of
37.3 seconds on Linux. Traced alone, the build reads 88 paths under `docs/` and 18
under `src/trifecta/`, none of which the 5 `src/` fixtures change, and lists `docs/`
and its document directories, so all 73 fixtures that change, create or delete under
`docs/` rerun it, and a sound key reuses in at most the other 50 copies, about 953 of 2344 Linux seconds, as {need}`Q_SCOPE_MODULES`
measures.

With the module in scope, staying fresh in every copy, as today, keeps it unstored,
though it stays a direction if no other is sound. Directions: **key it on what `strace` saw**,
which trusts `strace` for the file, network and listing calls it traces, resolves
paths through `-y`, records a failed `open`, `stat`, `access` or `readlink` as the file's absence, records the traced
command's whole environment beside it, since a trace holds no variable read, and has to
say what it does with reads under `/proc`, `/dev` and the temporary directory; or **run it once per job**, which changes what a fixture copy
proves. Left to wyatt: which.
:::

:::{question} Which programs besides git does the scope bring in?
:id: Q_PROGRAMS
The Out of scope section left out Vale, make and pip as known programs, and the
network; the scope ruling put in modules that need them, not the programs themselves.
In `test_init`, the two tests that run the whole check, 9.96 of 11.2 seconds on Linux,
run Vale. In `test_adoption`, the guide runs, through bash, `basename`,
`python3 -m venv`, `unzip`, pip installing the lock with `--require-hashes
--only-binary :all:` from the network or the test's pip cache, pip installing the
wheel, `trifecta init`, `sha256sum`, `cut`, `rm`, and `make check`, which runs make,
Vale, Sphinx and git. The `pip wheel` children of `test_adoption` and `test_package`
read the host, as
{need}`Q_HOST` measures. bash is {need}`Q_BASH`, `strace` is {need}`Q_TRACE_FRESH`, and
`os.uname` is {need}`Q_UNAME`.

Directions, each with what it costs:

- **Vale cannot meet {need}`REQ_KNOWN_PROGRAM` as written**: `test_init` runs
  `bin/vale` under the repository, and `test_adoption` copies it into the repository
  the run made, while the requirement names a program outside both. Lifting it means a
  Vale outside the repository, hash-pinned, with a traced list of its inputs, its
  configuration, styles and the files it lints, or a change to the requirement.
- **make cannot meet {need}`REQ_KNOWN_PROGRAM` as written**: it runs every recipe
  through `/bin/sh -c`, and the Makefile, which `trifecta init` writes from the wheel,
  names Vale, Sphinx and git. Lifting it means changing that requirement or running the
  Makefile's targets directly, which no longer proves `make check` as the guide says.
- **pip's downloads** are pinned by the lock's hashes, but which file pip takes depends
  on the host's platform tags, a read under {need}`REQ_HOST_READS`, and on pip's
  version, its configuration file and `PIP_*` variables, and the pip cache, which is
  host state; whether the index answers decides pass or fail while a key stays the same.
  The venv's interpreter is another executable than the one the recorder follows.
  {need}`REQ_REUSE_SOUND` refuses a network read today; installing with `--no-index`
  from a local wheel directory takes the network out, and changes what the guide's test
  proves.
- **Replacing `unzip`, `sha256sum`, `cut`, `basename` and `rm` with Python** in the test
  means it no longer runs the guide as written; changing the guide changes what a reader
  runs to suit the store.
- **Move the tests that need a program into a module that stays fresh**: the proof is
  unchanged, and the module saves only what the rest of it costs; for `test_init`, whose
  Vale tests take 9.96 of 11.2 seconds, about a ninth.

The other reasons in the Motivation's table each have a cost too. Sphinx changes the
working directory to the configuration's while it reads `conf.py`; the recorder
refuses only a change to another directory, so starting the build in `docs/` takes it
out, at the cost that the paths in Sphinx's warnings, which the check parses, may
change; lifting it instead changes how the recorder resolves a relative path. The hook
children that leave no manifest exit through `os._exit`, the product's code; storing a
child with no manifest is unsound, so either the hook exits in a way that runs
`atexit`, a change to the product, or the recorder wraps `os._exit` and writes
the manifest first, a change to the recorder. Removing `test_record`'s `-S` child, or the Windows junctions and
ctypes, may drop what those tests exist to check. Left to wyatt: for Vale, make, pip and
the network each, which direction; and for each other reason, whether its test may
change.
:::

:::{question} How and when is the recorder's `os.uname` gap closed?
:id: Q_UNAME
Measured on Linux: of the modules stored today, `test_profile`, `test_proofs`,
`test_release` and `test_store`, only `test_profile` calls `os.uname`, once, through
`platform.system()` when `uuid` is imported. Refusing every call would cost
`test_profile` its reuse. Recording only the fields other than the host name would keep
it, but closes the gap only if what the caller gets holds no real host name:
`platform.uname()` caches its whole result, host name included, so a later
`platform.node()` reads it from the cache with no call to `os.uname`, and
`posix.uname` is the same function under another name, which a wrapper of `os.uname`
alone leaves open. The probe wrapped `os.uname` alone, so a direct `posix.uname` caller
was not counted. Directions: refuse every call; record the host name as a hash under
{need}`REQ_HOST_READS`, a new input kind; or blank it in what the wrapper returns and in
`platform`'s cache, filled or not, which changes what the code under test sees, as the
pin rule in {need}`Q_GIT_KNOWN` forbids for git. Any of them wraps `posix.uname` and
`os.uname` together, and a test shows that `platform.node()` after `platform.system()`,
and a read through `posix.uname`, are seen. Among the refused modules,
`uuid`'s import, `toolchain.bin_vale` and pip's `packaging`, through
`sysconfig.get_platform()`, call it. Left to wyatt: whether
this is fixed in PLAN_0007, in the plan that builds this RFC, or before either, and
which direction.
:::

:::{question} Is the unit stored the module or the test?
:id: Q_UNIT
Measured: one recorded Python start that imports the test stack costs 1.35 seconds on
Linux and 2.07 on Windows. The 29 tests of `test_planning` that run on Linux take 6.1
seconds together, so a child per test would cost about 39. For that module a test as the
unit costs more than it saves; one whose tests are few and long loses less, such as
`test_store_reuse`, whose 4 tests take 8.4 seconds and would add about 5; and nested recording, the largest reason, holds whole modules
either way. Left to wyatt: whether to close this question with the module as the unit.
:::

## Out of scope

A time budget or target: none exists (wyatt, 2026-11-10: "No number yet"), and any is
only reported (wyatt, 2026-11-10: "Report only"). Proposed, for wyatt's ruling: any
change to {need}`REQ_REUSE_SOUND`; a test whose result depends on the clock or on
chance, as {need}`RFC_0008` leaves out; the Sphinx build's reuse and the CI cache, which
are {need}`PLAN_0007`'s tasks 4 and 5; the number of fixtures, and splitting them across
more CI jobs; an adopting repository's CI, which gets no store until a later change.
Vale, make, pip and the network are no longer left out here, since wyatt's scope ruling
puts in the modules that need them; how each is handled is {need}`Q_PROGRAMS`.

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

:::{review} Correctness; security
:id: REV_RFC_0009_2
:k: 2
:date: 2026-11-11
:digest: 4fcd0541246cff9941efa735e2ef84aea472f8a99d2c35b184b452642f4af9c6
Two rounds on the rewrite that records the measurements of 2026-11-11 and adds
`test_build_reuse`, one reviewer per lens, each checking claims against the probe logs,
the timings, the git traces, the recorder and the store. Folded in from correctness:
nested recording in 7 of `test_build_reuse`'s 10 tests and 25 of `test_record`'s 30 on
Linux; the git trace's loader, locale and parent-directory reads; git lifted stores
nothing on its own; the `os.uname` callers among refused modules; the sums, the bash
seconds on Linux, the test counts behind {need}`Q_UNIT`; 6141 seconds for nested
recording alone, 7963 with `test_record`'s other refusals; the `trifecta new` child's
git. Folded in from security: `platform`'s cache and `posix.uname` leave the host name
open under a partial wrapper, and blanking it changes what the code under test sees; the
git list is not shown closed, with no configuration present and no `-y`; the
maintenance child is a further program, refused unless both auto keys are off and a
trace shows no further start, so a Windows `commit` stays refused; a trace key records
the whole environment and every failed probe; the probe's limits, Python code only and
Debian rather than Ubuntu; what the environment key stands for.
:::

:::{review} Correctness; security
:id: REV_RFC_0009_3
:k: 2
:date: 2026-11-11
:digest: e5d27885607c002fd3a9c9c4ddd39e1a877582decc72af88b5ed7c456f4f9d4c
Three rounds on recording wyatt's rulings of 2026-11-11 on scope, order and git, one
reviewer per lens, each checking claims against the traces, the fixtures, the tests and
the recorder. Folded in from correctness: the reading of "highest possible speedup"
proposed, not ruled; the shared-lift order proposed; the rerun counts per module; the
`.gitattributes` and `docs/superpowers/` fixtures, through the listings above them; the
history check not run by any module; `rev-list` behind bash; `test_adoption`'s own
`git init`; Sphinx's working directory taken out by starting the build in `docs/`; a
recorder wrapper for `os._exit`; what each module waits on. Folded in from security:
the Sphinx build traced alone, not assumed; which listings were dropped and why, and
what that misses; git's untraced subcommands, the tests' configuration, Git for
Windows' credential helper; git on this repository and the git direction left open;
Vale and make cannot meet {need}`REQ_KNOWN_PROGRAM` as written; what pip's downloads
would trust; what replacing the guide's commands or bash would cost its proof;
`test_adoption`'s place in the order provisional.
:::
