---
status: approved
authors: [claude]
---
# Storable test modules

:::{design}
:::

## Overview

{need}`RFC_0009`'s eight never-stored proof modules become storable without weakening
{need}`REQ_REUSE_SOUND`, in the order {need}`DEC_0032` gives. The recorder names every
reason it refuses a run; git, a hash-pinned Vale and `strace` become known programs on
stated terms; a second recorder follows a child that records itself; a recorded run sees
a fixed host name; and the tests that need what stays refused, bash, make, pip and the
network, move into modules of their own that stay fresh. Each lift comes with tests that
a changed input reruns the module and that a start outside its terms is refused. Nothing
here is built until {need}`PLAN_0007` is done, the host name included, as
{need}`DEC_0039` records.

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

:::{component} Refusal reasons
:id: COMP_REFUSAL_REASONS
:satisfies: REQ_REFUSALS_NAMED
:constrained_by: DEC_0032
The recorder keeps every reason it refuses a run, not only the first, each with the
process that raised it, the module's own or a child named by its executable's base
name, with `-m` and the module name when it was started so and nothing else of its
command, bounded in number and length as `why` is. A refused manifest holds them in a
`reasons` list beside `why`, which stays the first. A reason holds no environment value,
and a path in it holds the root's placeholder; the home directory, the temporary
directory and the interpreter's prefixes are replaced by placeholders of their own, and
any other absolute path outside the root is cut to its base name. The proof child reports each test's wall
time on its channel, and the profile of a module the store did not store lists its
reasons and its tests' times; naming them changes nothing about whether the run is
stored, and nothing reads them but the profile. The naming and the manifest's section
names here and below are this design's, not rulings.
:::

:::{component} Known programs
:id: COMP_KNOWN_PROGRAMS
:satisfies: REQ_KNOWN_PROGRAM
:constrained_by: DEC_0033, DEC_0037, DEC_0038
The recorder's wrapper of `subprocess.Popen._execute_child` lets a start through,
unrefused, only when its executable resolves to one of three programs and its whole
argument list matches one of that program's forms below, and records the program's path
and SHA-256 in a new manifest section, `programs`, with the inputs below in `files`,
`probes`, `listings`, `outside` and `environment`. A start through a shell, a script or a
`.cmd` or `.bat` file, any other argument list, and any variable of the program's family
not on its list keep the refusal. The forms are this design's, from the calls the stored
modules make, and the Linux test below proves them.

git, under {need}`DEC_0033`: not under the repository and not one the run made, started
as `git init -q DIR`, as the tests start it, or as `git -C DIR` and then exactly one of
`remote get-url origin`,
`ls-files -z`, `ls-files -z --cached --others --exclude-standard` or `config user.name`,
where `DIR` is a directory the run created and `init` came before any other start on it.
No `-c` is allowed, and no `add` or `commit` (wyatt, 2026-11-12: "Withdraw the
forms").
Here and below, "the whole environment" is every variable that reaches the program,
inherited through `env=None` or copied into its mapping, each recorded as a hash at the
start, less the recorder's own and those whose values the run itself set, as
{need}`DES_0008`'s recorder treats them, so a path the run made is never part of a key;
a test starts a program with `env=None` and shows an inherited variable is recorded.
The environment must hold `GIT_CEILING_DIRECTORIES` at the made
directory's parent, `GIT_CONFIG_NOSYSTEM=1`, an empty `GIT_CONFIG_GLOBAL`, and `HOME`
and `XDG_CONFIG_HOME` on directories the run made, which the tests set; any other
`GIT_*` variable is refused. A `.git` file, alternates, `commondir`, and any file in
`.git/hooks` other than git's samples are refused, and the made repository's
configuration may hold only the keys `git init` writes and `user.name`; any other key is
refused. It records git's executables, the loader's files, the locale archive and
message catalogs, the template tree in `init`, the parents of the made repository, and
the whole environment, since `TZ`, `LD_*`, `LOCPATH`, `NLSPATH` and `GCONV_PATH` move
what git and its loader read; the files under the made `HOME` and `XDG_CONFIG_HOME`,
such as `git/ignore` and `git/attributes`, are the run's own and need no record. On
Windows the list is stated from Git for Windows' layout, its installation's
`etc/gitconfig` and templates and `USERPROFILE` among them. git on this repository stays
refused.

Vale, under {need}`DEC_0038`: `bin/vale` under the repository, whose SHA-256 the recorder
checks before the start against a pin of the binary itself per platform, a new constant
in the toolchain, read from the recorder's package as loaded when the run began and
trusted as the recorder is; the file holding the pin is a recorded input; a mismatch
refuses, and the stamp file is never trusted for it. It is started as `vale --version`
or as `vale --config=FILE --no-global --output=line --no-exit DIR...`, where `FILE` and
each `DIR` are under the build directory the run made, as `run_vale` starts it with
`--no-global` added, so no configuration outside them is searched. The configuration may
hold only a stated set of keys, and every path in it, `StylesPath` and the vocabularies
it reaches among them, must resolve under that build directory; the styles directory is
recorded, and a configuration that fails this is refused. A configuration with
`Packages`, the `sync` command, a linted file of a format for which Vale starts a
program, and any `VALE_*` variable are refused. It records the whole environment, since
no trace sees which variable Vale reads. On Windows the list is stated from Vale's
layout, as wyatt ruled for git.

`strace`, under {need}`DEC_0037`: named by its path and hash, started by
`test_record_trace` only, as `strace -f -y -s 4096 -qq -o LOG COMMAND...`, with `LOG`
under the run's directory; it has no proof test of its own, since `strace` cannot run
under another, and is trusted with the kernel, as {need}`DEC_0037` accepts. Its log
gives the traced command's inputs: every path read, probed or listed outside the run's
own directories, each failed `open`, `stat`, `access` or `readlink` as an absence, each
program it starts by path and SHA-256, with its `#!` interpreter, followed again, and its
ELF interpreter, which the kernel opens with no call in the log, and the command's whole environment, which no
trace sees read. `/dev/null` and `/dev/urandom` are allowed, and in the traced processes' own `/proc`
entries only listing `fd` and reading the `exe` link; any other read under `/proc` or
`/dev`, and any `connect` or socket of a network family, refuse the run. The
traced command runs under the recorder too, so the host name it sees is the fixed one of
COMP_HOST_NAME.

git and Vale each have a test, on Linux, that runs the program in its forms under
`strace` and fails on a path opened, probed or listed outside its stated inputs, a
further program started, a host-name read, or a connection.
:::

:::{component} Nested recorder
:id: COMP_NESTED_RECORDER
:satisfies: REQ_NESTED_RECORDING
:constrained_by: DEC_0035
A second recorder, the parent's, loaded from a `.pth` file of its own whose name sorts
before the test recorder's, so `site` runs it first, and a start source under a module
name of its own, `_trifecta_record_parent`, when `TRIFECTA_RECORD_PARENT` names
its directory. When a recorded process starts a Python child whose environment holds
`TRIFECTA_RECORD`, the parent's recorder, which starts first, gives the child a fresh
parent directory under `TRIFECTA_RECORD_PARENT` and leaves `TRIFECTA_RECORD` to the
test's recorder, which starts second and writes its own manifest where the test prepared
it. Since the parent's recorder installs its wrappers first, they are innermost: the
parent's wrapper of `_execute_child` runs last, nearest the real call, and checks the
final arguments and environment, whatever the test's wrapper changed; and the test's
recording mapping of `os.environ` wraps the parent's, so each variable read passes
through both. Tests show that the parent's wrapper is innermost, seeing the final
arguments and environment, and that a variable read reaches both. The names here are
this design's. The parent's recorder records the child as it
records any Python child; the child's own manifest never stands for it. A start whose
environment already holds `TRIFECTA_RECORD_PARENT` not set by the parent's recorder, and
any write into a directory the parent's recorder prepared other than its own, keep the
refusal. A test's wrapper above the parent's cannot drop the variable, since the parent's
sets it last; a drop below the parent's wrapper starts a child that leaves no manifest,
which is refused.

A write is judged by where it lands, not by how it is spelled: once its links and `..`
are resolved, and by the device and file number of each directory above it, so a link, a
`/proc` path, a long-path prefix or a share that reaches the prepared directory is
refused, and so is opening for writing another name of a file in it. Moving, copying or
hard-linking anything out of it is refused too. A Python child whose final environment
sets `PYTHONPATH`, `PYTHONHOME`, `PYTHONPLATLIBDIR`, `PYTHONSTARTUP` or
`PYTHON_FROZEN_MODULES` without `-E` or `-I`, or that is started with
`-X frozen_modules=off`, is refused, since it can run code before `site` starts the
recorder; a recorder that starts under prefixes other than its parent's, which its
directory's configuration names, or after a module from outside them was loaded, refuses
its run. A callback that `shutil.rmtree` calls on an error is recorded as the run's own
code. At each child start and at exit the parent's recorder checks that its audit hook
still sees an event and that each wrapper it installed is still reached from its
attribute through `__wrapped__`, each step a wrapper some recorder in the process
installed, so a function that only names a wrapper is a replacement.

The ways code can step around a wrapper without replacing it are listed and accepted by
{need}`DEC_0035` for the repository's own tests: a wrapper's original in `__wrapped__`
and its closure, `os._Environ.__getitem__` past the recording mapping, and
`sys.addaudithook` and `object.__setattr__`, which the recorder lists as harmless. To
these wyatt added, for the same tests, tampering with a recorder's own state from inside
the process, through `sys.modules`, `gc`, frames or a trace function (wyatt,
2026-11-13: "Accept and list it (Recommended)"). A way the list does not hold, found
later, reopens that decision.
:::

:::{component} Host name
:id: COMP_HOST_NAME
:satisfies: REQ_HOST_READS
:constrained_by: DEC_0039
The recorder wraps `os.uname` and `posix.uname` together and fills
`platform`'s cache at its start, so that inside a recorded run each gives a fixed host
name, and records the other `uname` fields, each as a SHA-256 and never the value, in a
new manifest section, `uname`. A test
shows that `platform.node()`, after `platform.system()` and before it, and
`posix.uname().nodename` give the constant, and that a change to another field reruns
the run. Every other way to read the host's identity stays as it was: a read of
`/etc/hostname` or `/proc/sys/kernel/hostname` and the `HOSTNAME` variable are recorded,
`socket.gethostname` is refused, each with a test, and the MAC address that
`uuid.getnode()` reads through native code falls under {need}`DES_0008`'s native-code
risk. Derived, not ruled: `toolchain.bin_vale` tests `os.name` in place of
`platform.system()`, so it reads nothing of the host on Windows.
:::

:::{component} Lifted reasons
:id: COMP_LIFTED_REASONS
:satisfies: REQ_LIFT_PROVEN
:constrained_by: DEC_0032, DEC_0034, DEC_0036, DEC_0038, DEC_0040
The stored unit stays the module. The lifts are built in {need}`DEC_0032`'s order, each
shared lift with the first module that needs it. Tests move into modules that stay fresh
and are never stored: the bash tests of `test_init` and `test_planning`;
`test_adoption`'s guide test; `test_record`'s `-S` test and its tests whose children
do a refused thing on purpose; the two tests of `test_store_reuse` that start a child
reading the host name on purpose (wyatt, 2026-11-13: "Move them, in task 5
(Recommended)"); the nested recorder's own tests, in `test_record_nested`, which run
three recorders deep under the module's; and the Windows junction and ctypes tests of `test_init`,
`test_planning` and `test_record`. `test_package` builds its wheel through
`flit_core.buildapi.build_wheel`, not `pip wheel`. The hook child of `test_planning`
that leaves a malformed manifest keeps the refusal until the task that stores
`test_planning` finds its cause and fixes it. The check starts the
Sphinx build in `docs/`, so the change into the configuration's directory is no change,
and maps Sphinx's warning paths as before. The recorder wraps `os._exit`: in the process
it started in, it takes its lock, writes the manifest with the exit status as the
`atexit` path writes it, and holds the lock through the real exit, so another thread's
audit hook blocks before its operation. It writes the manifest under a temporary name
and renames it into place as its last step before the real exit; an event that reaches
the hook after the snapshot without blocking rewrites it as refused. A fork is already
refused by the recorder.

Each lift has tests, declared for {need}`REQ_REUSE_SOUND`: a change to each input it
records reruns the module; a start outside its terms is refused; and each input it does
not record, a git alternates file, a `.git` file, an `includeIf`, a program planted on
`PATH`, a `bin/vale` with another hash, either reruns the module or is refused.
`trifecta fixtures` and `trifecta fixtures --fresh` give the same result for every fixture
after each lift, on Linux and on Windows.
:::

## Interfaces

{need}`DES_0008`'s IF_MANIFEST gains three sections, amended there when the first of
them is built: `reasons`, the list of every reason a refused run was refused, beside
`why`; `programs`, mapping each known program started to its SHA-256; and `uname`, the
`uname` fields other than the host name, each as a SHA-256. A manifest without them is
malformed, since a lookup requires every section, so it is never reused.

## Risks

A known program's stated list is proven on the git and Vale versions the Linux test runs;
on another version, or on Windows, where no trace runs, it is trusted, as
{need}`DES_0008`'s Risks accept for native code. The pin of `bin/vale` lives in the
repository and is trusted as the recorder is: a change can alter both together, as it
can alter the recorder, which is why only a push run on main publishes a store. The
nested recorder leaves the listed ways around a wrapper open for the repository's own
test code. A recorded run sees a host name that is not the machine's; code that relied
on it would behave otherwise under the recorder than outside it, and no test in scope
does. Until this design's host-name task lands, after {need}`PLAN_0007` (wyatt,
2026-11-11: "Move the host-name fix too"), the recorder as built lets a run read the host
name through `os.uname` unrecorded, so a store published from main can hold such runs,
`test_profile`'s among them. The fresh modules, `test_adoption`'s guide above all, keep
their cost, which the profile shows.

## Review

:::{review} Correctness; security
:id: REV_DES_0009_1
:k: 2
:date: 2026-11-11
:digest: 07c3a4064299238f2ec4d4c109baca09076fe7e7171a69a76d6ef856276df9c0
Three rounds, one reviewer per lens, on this design and decisions {need}`DEC_0032` to
{need}`DEC_0040`, checking claims against the RFC's rulings and the recorder, the
toolchain, the check and the tests. Folded in from correctness: each decision's options
are those put to wyatt, and what the design derives is marked as its own; git's forms
trimmed to the calls the stored modules make, `init -q DIR` among them; Vale's forms
from `run_vale`; `strace`'s full arguments and its trust; the parent recorder's load
order; the host name built in a task of its own while PLAN_0007 runs. Folded in from
security: an allowed list of arguments, `GIT_*` variables and configuration keys for
git, with `HOME` and `XDG_CONFIG_HOME` on directories the run made; `--no-global`, keys
and paths for Vale's configuration; network, `/proc`, `/dev` and interpreters in the
`strace` key; the parent's wrappers innermost; the `uname` fields hashed; the
`os._exit` manifest renamed into place last; reasons that hold no value; what the whole
environment is.
:::

:::{review} Correctness; security
:id: REV_DES_0009_2
:k: 2
:date: 2026-11-12
:digest: b570d1b6b984609cd6c80d011f46c630fc5ef403ea9acbd6e5619c89d3507e9b
Two rounds, one reviewer per lens, on wyatt's rulings of 2026-11-11 and 2026-11-12
that followed acceptance and on {need}`PLAN_0008`. Folded in: `test_record`'s refusal
tests moved to a fresh module; the host-name fix built after PLAN_0007, with the gap it
leaves open stated in {need}`DES_0009`'s Risks; git's forms for `add` and `commit`
withdrawn, since the correctness pass found `test_build_reuse` never starts git, which
Claude had claimed; git's whole environment recorded; the PLAN_0007 session's
measurements noted, with this RFC's plan held.
:::

:::{review} Correctness; security
:id: REV_DES_0009_3
:k: 2
:date: 2026-11-13
:digest: 3262dd28cead768ff6037d8b7f082c61872402a29e787f1bc946abb916d9e09b
Reviewed with {need}`DES_0008`'s amendment in {need}`PLAN_0008`'s task 1. Folded in: a
manifest without the new sections is malformed and never reused, since a lookup requires
every section, not read as before.
:::
