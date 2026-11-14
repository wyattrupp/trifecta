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
:constrained_by: DEC_0033, DEC_0037, DEC_0038, DEC_0043, DEC_0044, DEC_0045, DEC_0046, DEC_0047, DEC_0048, DEC_0049, DEC_0050
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
{need}`DES_0008`'s recorder treats them, so a path the run made is never part of a key,
with the digest of the names of the variables the process started with, which
IF_MANIFEST states, so a variable that appears or vanishes reruns the module; a test
starts a program with `env=None` and shows an inherited variable is recorded, and that
one appearing reruns.
The environment must hold `GIT_CEILING_DIRECTORIES` at the made
directory's parent, `GIT_CONFIG_NOSYSTEM=1`, an empty `GIT_CONFIG_GLOBAL`, and `HOME`
and `XDG_CONFIG_HOME` on directories the run made, which the tests set; any other
`GIT_*` variable is refused. A `.git` file, alternates, `commondir`, and any file in
`.git/hooks` other than git's samples are refused, and the made repository's
configuration may hold only the keys `git init` writes and `user.name`; any other key is
refused, and so, this design's choice, is an `init` where a repository is already. On
the `-C` forms a `.git`, file or directory, anywhere below the made worktree's own is
refused, as a repository of its own or a file naming one elsewhere. A start through a
shell, with code before it starts or with descriptors it inherits is refused, as
`strace`'s is. As `strace`'s log is, what a git let through reads that the run made, its
made repository and the made `HOME` and `XDG_CONFIG_HOME`, is held from its start until
the run reaps it, by waiting or polling: a write, move, removal, change of mode or link
of a path under them, by any name, refuses the run, and so does a run that ends before
it reaps git. A directory a process made, and one its `init` ran on, count as the run's
for its Python children too. Under {need}`DEC_0049` the check and the tests start git
and Vale with `LD_LIBRARY_PATH`, `LD_PRELOAD`, `LD_AUDIT`, `LOCPATH`, `NLSPATH` and
`GCONV_PATH` removed from the child's environment, and, this design's choice, a start
that still holds one is refused, since each moves a read to where no key holds it. Under
{need}`DEC_0050` they start git and Vale without `PWD` too, which each stats as the working
directory's name and which a copy of the repository inherits naming the original (wyatt,
2026-11-14: "Strip PWD for git/Vale (Recommended)"), and a start that still holds it, even
empty, is refused. It
records git's
executables; on Linux the loader's cache, its preload file, which refuses the start when
present, and each library named as needed, found in the cache and followed again, a
library the cache lacks, one the cache chooses by the processor, or a program or library
with a search path of its own refusing the start; every locale's files under
`/usr/lib/locale`, the locale archive among them, the gconv modules' cache beside the C
library, with `gconv-modules` and the `gconv-modules.d` tree, the locale aliases, and each language's catalog of git's messages under
`/usr/share/locale`, whatever language the environment names, where the walk skips the
one entry `locale.alias` when it is a link, since it is already recorded by its link, its
target and its content as {need}`DEC_0043` names it, and refuses any other link (wyatt,
2026-11-14: "Skip LOCALE_ALIAS (Recommended)"); the template tree in
`init`; the parents of the made repository, and the working directory git starts in and
its parents, which git resolves; and the whole environment, since `TZ` and the other
`LD_*` variables move what git and its loader do. The files under the made `HOME` and
`XDG_CONFIG_HOME`, such as `git/ignore` and `git/attributes`, are the run's own and need
no record. On Windows the list is stated from Git for Windows' layout: git is found as
CreateProcess finds it, in the interpreter's own directory, the working directory, the
system's directories and then along `PATH`, each place before it recorded as probed; its
launcher in `cmd` or `bin`, which starts the build's `bin/git.exe`, the build being
`mingw64` or `ucrt64` (wyatt, 2026-11-14: "State ucrt64 too (Recommended)"), whose
`bin/git.exe` must be a file; every other build the launcher knows, the other of those two,
`clangarm64`, `mingw32` and `mingw`, must have no `bin/git.exe`, neither file nor link,
each recorded as probed absent, so an installation that adds one reruns the module, and an
installation holding more than one build is refused, since the launcher could start what
is never hashed; and that
program, found in the build's `bin` or through a launcher, each by
path and SHA-256, with each DLL either imports from that directory, followed again, and
each other name it imports probed there, a DLL found neither there nor in the system's
`System32`, but for the system's API sets, refusing the start; the installation's `etc/gitconfig`,
the build's `etc/gitconfig`, `ProgramData/Git/config`, the templates under the build's
`share/git-core/templates`, the catalogs under the build's `share/locale`, and the
whole environment, `USERPROFILE` among it. Another layout is refused. git on this
repository stays refused.

Vale, under {need}`DEC_0038`: `bin/vale` under the repository, or, under
{need}`DEC_0047`, the Vale at the path `TRIFECTA_VALE` names, as the fixture runner sets it
for a copy, whose SHA-256 the recorder checks before the start against a pin of the binary
itself per platform, a new constant in the toolchain, read from the recorder's package as
loaded when the run began and trusted as the recorder is; the binary is recorded by its
path with its hash, which is what is trusted; the file holding the pin is a recorded input;
a mismatch refuses, a Vale the run made is refused whatever its hash, and the stamp file is
never trusted for it. The binary is hashed again when the run ends, and one changed while
Vale ran refuses the run. A start through a shell, with code before it starts or with
descriptors it inherits is refused, as git's is, and, as for git, what Vale reads that
the run made, the build directory with its configuration, styles and linted files, and
its binary, is held from its start until the run reaps it: a change to any of them, by
any name, meanwhile, or a run that ends before it reaps Vale, refuses the run. It is started as `vale --version` or as
`vale --config=FILE --no-global --output=line --no-exit DIR...`, where `FILE` and each
`DIR` are under the build directory the run made, the highest directory the run made that
holds `FILE`, as `run_vale` starts it with `--no-global` added, so no configuration outside
them is searched. The configuration's stated keys, this design's from what `run_vale`'s
configurations use, are `StylesPath`, `MinAlertLevel`, `IgnoredClasses` and `Vocab` at its
top and, in a section of files, `BasedOnStyles` and a rule's toggle, `Style.Rule` set to
`YES`, `NO` or a level, each style it names a directory under `StylesPath`; a `[formats]`,
`[asciidoctor]` or `[adoc]` section is refused, the last this design's choice. A value of
`StylesPath` or `Vocab` with a character outside letters, digits, `_`, `.`, `/` and `-` is
refused, since Vale reads a value in quotes or backticks unquoted and cuts one at a
comment; `StylesPath` is judged as joined to the configuration's directory, its links
and `..` resolved, and as Vale cleans it, the two the same directory. Every path in it, `StylesPath` and the vocabularies
it reaches among them, must resolve under that build directory, and the styles directory
may hold only styles of rule files and the vocabularies' `accept.txt` and `reject.txt`;
the rule kinds, this design's too, are `existence` and `substitution`, with only the keys
those rules take; a configuration that fails this is refused. A configuration with
`Packages`, the `sync` command, any other option, a linted file of a format for which Vale
starts a program, and any `VALE_*` variable are refused; the files Vale may lint, this
design's choice, are `.html` only. Under {need}`DEC_0048` so is a start with `TERM` set: a
trace shows Vale then looks the user up, through the name service and its socket, and reads
the terminal's description. Each name Vale looks for a configuration by, `.vale`,
`.vale.ini`, `_vale`, `_vale.ini` and `vale.ini`, is probed in the working directory and
each directory above it, and one present refuses the start, this design's choice. It records the binary, the
pin's file and the whole environment, since no trace sees which variable Vale reads, and
on Linux its ELF interpreter and the loader's files, as for git, and `/proc/version`. Under {need}`DEC_0046`, its
runtime's other reads on Linux, which no key can hold, are allowed unkeyed and no others:
its own `maps`, `mountinfo` and `cgroup` under `/proc`, as `self` or by its own number,
`/sys/kernel/mm/transparent_hugepage/hpage_pmd_size`, `/sys/devices/system/cpu/online` and
its own control group's `cpu.max`; any other read under `/proc` or `/sys` is outside the
list, and the trace test fails on it. On Windows the list is stated from Vale's layout, as
wyatt ruled for git: the binary, each name it imports probed beside it, a DLL found
neither there nor in `System32` refusing the start as for git, and the configuration
names above.

`strace`, under {need}`DEC_0037`: named by its path and hash, started by
`test_record_trace`'s own process only, as `strace -f -y -s 4096 -qq -o LOG COMMAND...`.
The recorder lets the start through only when `LOG` is new, does not start with `|` or `!`,
and lies, its parent's links resolved, under a directory the run made, in no directory a
recorder prepared and not under the interpreter's prefixes; `COMMAND` is named by its
absolute path; the start has no shell, no `preexec_fn` and no `pass_fds`, closes the
run's other descriptors, and its environment holds no `TRIFECTA_RECORD_PARENT`; and
`strace`, found along `PATH` as subprocess finds it, each place searched before it recorded
as probed, is a regular ELF file outside the repository and the run's own directories,
started by the path it was found at. The form and these conditions are this design's, not
rulings. `strace` has no proof test of its own, since it cannot run under another, and is
trusted with the kernel, as {need}`DEC_0037` accepts. The recorder makes `LOG` and holds it
open before `strace` starts, and once the run reaps `strace` reads the log through that
descriptor, so what it reads is what `strace` wrote, whatever then becomes of the name; a
call of the traced command on `LOG`, by any name under what the run made, a change to a
directory that holds it, a write of the run's own to it by any name, and a log that does
not start with its command's start each refuse the run. The recorder knows the log as it
makes it, before `strace` starts, and, once `strace` is reaped, refuses the run when the
run wrote the log by any name.

The log gives the traced command's inputs, recorded as {need}`DES_0008`'s recorder records
the run's own: every path read, probed or listed outside the run's own directories, each
failed `open`, `stat`, `access` or `readlink` as what is there, absence for a path not
found; a read keyed both by the name it was given and by the path the kernel opened, which
`-y` gives, and refused when the name no longer reaches that path; each program it starts
by path and SHA-256, keyed where its path lands, with its `#!` interpreter, followed again,
and its ELF interpreter, which the kernel opens with no call in the log; and the command's
whole environment, which no trace sees read. Under {need}`DEC_0044` only the interpreter's
own trees, sysconfig's `stdlib`, `platstdlib`, `purelib`, `platlib`, `scripts` and
`include` under `sys.prefix` and `sys.base_prefix`, are left to the environment key; every
other path under the prefixes is keyed. The system's time zone is left out with the clock,
which {need}`RFC_0008` puts out of scope, as the recorder leaves it out. A read, probe,
listing or start of a path the run itself first wrote, or one under a directory it first
made, while `strace` ran refuses the run, since the log does not say whether the command
saw it before or after. A read of a pipe, a device or a socket, which another process can
feed, refuses the run, and so does a process started with `CLONE_UNTRACED`, which no
trace follows. `/dev/null` and `/dev/urandom` are allowed,
and in the traced processes' own `/proc` entries, as `self` or by number, only listing
`fd`, reading the `exe` link and, under {need}`DEC_0043`, reading `maps` and `cgroup`, none
of them keyed; any other read under `/proc` or `/dev` refuses the run. A socket of a
network family refuses it, but one of `AF_INET` or `AF_INET6` bound to a loopback address
on which the command never connects, sends, listens or accepts, under {need}`DEC_0043`;
any `connect`, and binding a local socket, refuse it too. A read through a link the run
did not make refuses the run, as the recorder's own does, but two kinds of link. One is a
link met resolving `sys.executable`, `sys.prefix`, `sys.base_prefix`,
`sys.exec_prefix`, `sys.base_exec_prefix` or the `home` a virtual environment's
`pyvenv.cfg` names, all the interpreter's, which {need}`DEC_0045` holds as the
interpreter's: it is recorded as a probe of the link with its target, which a lookup reads
again, and followed. The other is the C library's `/usr/share/locale/locale.alias`, which
{need}`DEC_0043` names: it is recorded by the link, its target's content and the content
the link reaches, which a lookup takes again following it. Making a link that reaches
beyond what the run made refuses the run, as the recorder's own does, and so does a signal,
or a pidfd, to a process `strace` does not trace, but for 0, the command's own process
group, which holds `strace` and the run's own process too: a signal there can only end
or stop what is recorded, which then leaves no result. The traced command runs under the recorder too,
so the host name it sees is the fixed one of COMP_HOST_NAME.

git and Vale each have a test, on Linux, that runs the program in its forms under
`strace` and fails on a path opened, probed or listed outside its stated inputs, a
further program started, a host-name read, or a connection, Vale's past the reads of its
runtime {need}`DEC_0046` allows. The tests are in a module of their own, which
stays fresh on Linux, since only `test_record_trace`'s own process may start `strace`.
:::

:::{component} Nested recorder
:id: COMP_NESTED_RECORDER
:satisfies: REQ_NESTED_RECORDING
:constrained_by: DEC_0035, DEC_0041, DEC_0042
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
refused, and so is opening for writing another name of a file in it. `os.rename`,
`os.replace`, `os.link` and the copies `shutil` makes, from a path in it, are refused
too; a copy the run makes by reading and then writing is a read. A write, a move, a copy
or a link that lands under the interpreter's prefixes, judged the same way, is refused,
since a `.pth` file or a module there runs in every child before the recorder, and so is
moving or linking a file out of them. A path the run reaches through a share or a device
namespace, as a long-path prefix spells it, is refused by that name.

Under {need}`DEC_0042`, a Python child is refused when it can run code of the run's
before `site` starts the recorder: its final environment sets `PYTHONHOME`,
`PYTHONPLATLIBDIR`, `PYTHONSTARTUP`, `PYTHON_FROZEN_MODULES` or `PYTHONPYCACHEPREFIX`
without `-E` or `-I`; it is started with `-X frozen_modules=off` or
`-X pycache_prefix`, with or without them; a `-W` option or a `PYTHONWARNINGS` item names
a category whose module is not the standard library's, with or without them; or its
`PYTHONPATH` has an entry, its links resolved and an empty one read as the child's
working directory, that lies outside the repository root and the interpreter's
prefixes, that is not a directory, as a zip is, or that lies outside the prefixes and
holds a name of the standard library, which would load in place of a module the
interpreter or the recorder imports as it starts. The check and the Sphinx build start
a recorded child without `-X pycache_prefix`, since its recorder sets the prefix itself.
A recorded child that honours the environment gets no `PYTHONPATH` in it: the parent's
recorder, as it judges the start, or the check, for the build it starts, writes the
entries it judged, resolved, and the variable's value into the child's configuration, and
the child's recorder, once it has started, puts the entries into `sys.path` ahead of the
standard library, where the variable would have put them, and the variable back into the
environment for the run's own children; so an entry swapped or written after the judgment
runs nothing before the recorder, and what is imported from it later is recorded as any
import is. The variable is recorded. A recorder refuses its run when it starts under prefixes other
than its parent's, which its directory's configuration names; when a module is loaded
that is not of the standard library, the recorders' own and `__main__` aside, or one of
the standard library's name from outside the prefixes, a check that holds while the
recorders' `.pth` files sort first, so a `.pth` file of another package named to sort
before them that imports a module refuses every run; or when its `PYTHONPATH` fails
the checks above, an entry swapped since its start was judged among them; and it lists
each entry in its repository as an input. The test's recorder in a process the parent's
records too counts the parent's repository as inside as well, since the test chose its
own root and the parent's recorder, which judges against the repository's, lists those
entries. These checks
see what was loaded and what the entries hold as the recorder starts: a module that ran
before it and then removed both its file and its entry in `sys.modules` is not found, a
limit {need}`DEC_0042` records. A callback that `shutil.rmtree` calls on an error is
recorded as the run's own code. At each child start and at exit the parent's recorder
checks that its audit hook still sees an event and that each wrapper it installed is
still reached from its attribute through `__wrapped__`, each step a wrapper some
recorder in the process installed, so a function that only names a wrapper is a
replacement; a check that fails to run refuses the run too.

The ways code can step around a wrapper without replacing it are listed and accepted by
{need}`DEC_0035` for the repository's own tests: a wrapper's original in `__wrapped__`
and its closure, `os._Environ.__getitem__` past the recording mapping, and
`object.__setattr__`, which the recorder lists as harmless; and
{need}`DEC_0041` adds, for the same tests, tampering with a recorder's own state from
inside the process, through `sys.modules`, `gc`, frames or a trace function. A way the
list does not hold, found later, reopens those decisions. A run that adds an audit hook,
which {need}`DEC_0035` listed too, is refused: the hook is called inside the recorder's
own calls, as while it writes the manifest, where what it does is in no manifest (wyatt,
2026-11-14: "Refuse it (Recommended)"); the hook a recorder adds in its own start, as the
test's recorder does under the parent's, is let through.
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
`test_adoption`'s guide test; `test_record`'s `-S` test, its tests whose children
do a refused thing on purpose, and its test of two copies, whose `PYTHONPATH` names a
copy outside the repository (wyatt, 2026-11-13: "Move it too (Recommended)"); the test of
`test_store_reuse` that starts a child reading the host name on purpose (wyatt,
2026-11-13: "Move them, in task 5 (Recommended)", ruled as two tests; as measured, the
module has one, on both platforms); the nested recorder's own tests, in `test_record_nested`, which run
three recorders deep under the module's; the Windows junction and ctypes tests of `test_init`,
`test_planning` and `test_record`; and `test_planning`'s hook tests of a share path and of a
`json` shadowed from a temporary directory (wyatt, 2026-11-14: "Move both (Recommended)").
`test_package` builds its wheel through
`flit_core.buildapi.build_wheel`, not `pip wheel`. The hook child of `test_planning`
that left a malformed manifest was its share-path test's, on Linux, as measured in
{need}`PLAN_0008`'s task 7: the guard turned `\\localhost\c$` into a POSIX path
beginning `//`, which the recorder kept as a probe key that `valid()` rejects. The recorder
has refused such a path by name since {need}`PLAN_0008`'s task 3, so the child leaves a
valid refused manifest, and the test, moved as above, no longer keeps `test_planning`
from being stored. The check starts the
Sphinx build in `docs/`, so the change into the configuration's directory is no change,
and maps Sphinx's warning paths as before. The recorder wraps `os._exit`. It first takes
the status as an `int` the real exit accepts, so code of the run's, as an `__index__`,
runs before any snapshot; a status that is none goes to the real exit with nothing
written. In the process it started in, it then takes its lock, writes the manifest as the
`atexit` path writes it, and holds the lock through the real exit, so another thread's
audit hook blocks before its operation and another thread's `os._exit` waits for the
exit. It writes the manifest under a temporary name and renames it into place as its
last step before the real exit. The recorder is quiet only in its own calls: an event
that reaches the hook after the snapshot without blocking, in any thread, the exiting one
included, rewrites the manifest as refused, and the collector and, where the system
allows, signals are held off from the snapshot through the exit. Should the real exit
return or raise, the manifest is rewritten as refused. At a normal exit the recorder
writes the manifest the same way, and once it is in place the recorder is quiet no
longer: an event after it that is no recorder's own, in any thread, as a finalizer's or
a signal handler's at teardown, rewrites the manifest as refused (wyatt, 2026-11-14: "Fix
in task 7 (Recommended)"). Should that rewrite and the manifest's removal both fail, the
event's operation fails, and the next event tries again; the rewrite is made as the
manifest is written and reaches only what it bound then, since the interpreter's teardown
empties the recorder's module. The recorder wraps each handler the run installs, in
`_signal`, which `signal.signal` calls, telling its own wrappers by identity, and the run
reads back its own handler from `signal.getsignal` and `signal.signal`, since Python runs a handler in the main thread between any two of its
instructions, the recorder's own among them, wherever another thread raised the signal:
a handler that runs inside the recorder's own calls refuses the run (wyatt, 2026-11-14:
"Keep it in task 7 (Recommended)"), after the snapshot marks it late, and once the
manifest is written rewrites it as refused. The exit paths
see events only until the interpreter clears its audit hooks at teardown: what runs
after, as an object the interpreter keeps until it clears its own state, is seen by no
hook. So a codec search function or error handler that is not one of the interpreter's
own, the very objects it held as the recorder started, and any `sys.monitoring` callback
are refused as they are registered; a fork callback, which the standard library registers as it is
imported, the recorder holds in the interpreter's place and lets go once the manifest is
written, while the hooks still see what a finalizer it held does (wyatt, 2026-11-14: "Keep
the stub (Recommended)"). These close the ways a run registers a callable of its own
there; an object a run hangs on what the interpreter already keeps there is not seen, an
open class the Risks name. The other places a run can leave an object at
teardown, measured with a finalizer that reads, end refused or never run it: the
context's variables, the asynchronous generator hooks, a trace or profile function,
`sys` and `builtins` attributes, `threading.local`, `sys.excepthook`,
`sys.unraisablehook`, `copyreg`, `atexit` and a weak reference's callback (wyatt,
2026-11-14: "Fix in task 7 (Recommended)"). Each file the recorder writes in its directory, the temporary
name among them, is made afresh: what the name held, a link or a hard link to another
file, is removed first, and the file is created exclusively, never through a link
(wyatt, 2026-11-14: "Fix in task 7 (Recommended)"). The manifest holds
no exit status: the status is passed on to the real exit as given, and a test reads it as
the child's return code (wyatt, 2026-11-14: "Pass-through is enough (Recommended)"). A
fork is already refused by the recorder.

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
their cost, which the profile shows. Two openings in the recorder's ordinary handling,
which predate this design's last task, are known and deferred to a follow-up plan
(wyatt, 2026-11-14: "Follow-up plan (Recommended)"): run code that fires inside the
recorder's own work, a finalizer the collector runs there, whose events the quiet
recorder does not see; and a run's own method the recorder calls while it is at work, as
`__fspath__` on a path it is given, whose reads go unrecorded and whose audit hook the
refusal of `sys.addaudithook` does not see. A signal handler there is refused, as
COMP_LIFTED_REASONS states. With them the same follow-up plan takes a third open class
(wyatt, 2026-11-14: "Stop; defer the class (Recommended)"): an object a run hangs on
what the interpreter keeps past its audit hooks, whose finalizer runs after them, as on
the codec lookup cache, on a built-in function's `__module__` or a function's
`__defaults__`, on the fork callbacks `threading` and `random` register before the run,
or reached past a wrapper, as the original `_signal.signal` through `__wrapped__`; and a
trace function the run sets, which runs inside the recorder's judging.

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

:::{review} Correctness; security
:id: REV_DES_0009_4
:k: 2
:date: 2026-11-13
:digest: 114d03f084b343c31825ae8f62a40702e94abc0c8b1e809616b5b47e1c097e46
Four rounds, one reviewer per lens, on COMP_NESTED_RECORDER and COMP_LIFTED_REASONS as
{need}`PLAN_0008`'s task 3 built them, the fourth narrowed to one finding past the usual
three. Folded in: wyatt's rulings of 2026-11-13, recorded as {need}`DEC_0041` and
{need}`DEC_0042`, and the move of `test_store_reuse`'s two tests; a write judged by where
it lands, the prepared directory's and the prefixes'; the ways a child runs code before
`site`, by environment, option, search path, warning filter and cache prefix, each
refused; the search path carried in the configuration until the recorder starts, which
the security pass found raceable; a wrapper reached only through recorders' wrappers;
an `rmtree` callback recorded as the run's code.
:::

:::{review} Correctness; security
:id: REV_DES_0009_5
:k: 2
:date: 2026-11-13
:digest: 4a6507318dcaa9cd03495349e820dde0787fd20fc05e5157773ae85f70062e17
Two rounds, a ruling round and a final check, one reviewer per lens, on
COMP_KNOWN_PROGRAMS's `strace` as {need}`PLAN_0008`'s task 4 built it. Folded in: wyatt's
rulings of 2026-11-13, recorded as {need}`DEC_0043`, {need}`DEC_0044` and
{need}`DEC_0045`; the start's terms stated in full; the log made and held by the
recorder, known before `strace` starts; reads keyed where the kernel opened them; links,
signals, late writes, untraced children, pipes and devices refused, which the security
passes found open; the environment's names keyed.
:::

:::{review} Correctness; security
:id: REV_DES_0009_6
:k: 2
:date: 2026-11-13
:digest: ab5de98d262f2b36edf7bccbc49fb5da73ce363378d0d5b8e368ba00f643c7ae
One round, one reviewer per lens, on {need}`PLAN_0008`'s task 5. Folded in: wyatt's ruling of
2026-11-13 moving `test_record`'s test of two copies, "Move it too (Recommended)"; the
host-name tests of `test_store_reuse` counted as measured, one.
:::

:::{review} Correctness; security
:id: REV_DES_0009_7
:k: 2
:date: 2026-11-13
:digest: 6cddbd3b717a2fb7f10e3954ab10e60dd7121c52d848a2cc5d997eb8110bbccf
Three rounds, one reviewer per lens, on COMP_KNOWN_PROGRAMS's git and Vale and
COMP_LIFTED_REASONS as {need}`PLAN_0008`'s task 6 built them. Folded in: wyatt's rulings of
2026-11-13, recorded as {need}`DEC_0046` to {need}`DEC_0049`; git's and Vale's terms and
lists stated in full, the design's own choices labelled; a quoted or commented
`StylesPath`, a nested repository, a start with code before it or inherited descriptors,
a DLL from elsewhere and Vale swapped while it ran refused, which the security passes
found open; what a running git or Vale reads held until the run reaps it.
:::

:::{review} Correctness; security
:id: REV_DES_0009_8
:k: 2
:date: 2026-11-14
:digest: b0cfbf8a5b9fd6f68287e91e9b3bd469403ce876635ccd6aebba7a226fb36df9
Two rounds, one reviewer for both lenses, on the fixes CI's runners called for: wyatt's
rulings of 2026-11-14 on Ubuntu's `locale.alias` link and Git for Windows' `ucrt64`
build. Folded in: every other build the launcher knows is held absent, file or link,
which the security pass found open as a link at the other build's `git.exe`.
:::

:::{review} Correctness; security
:id: REV_DES_0009_9
:k: 2
:date: 2026-11-14
:digest: d4ddb6f439c292b9ffca0fc359e50990dfc05d8c05f104c72e7085cfbf7296a1
On the fix CI's fixtures called for: git and Vale stat `PWD`, which a fixture copy
inherits from the original checkout. Folded in: wyatt's ruling of 2026-11-14, recorded as
{need}`DEC_0050`; the check starts them without it and a recorded start holding it is
refused.
:::

:::{review} Correctness; security
:id: REV_DES_0009_10
:k: 2
:date: 2026-11-14
:digest: 28921d1f7b7bb85d9e6242207a09b54fba18a1353763ef9aa02587e01592067b
Three rounds, one reviewer per lens, on COMP_LIFTED_REASONS as {need}`PLAN_0008`'s task 7
built it: the `os._exit` wrapper, the normal exit's seal and what may run after it.
Folded in: wyatt's rulings of 2026-11-14, quoted where they apply; a status taken before
the snapshot, run code in the seal, a second exit, finalizers and signal handlers at
teardown, a refusal that cannot be written, a link at the temporary name, a run's own
audit hook, codec and monitoring callables kept past the hooks, and signal handlers read
back as given, which the security passes found open. Deferred to a follow-up plan, as
Risks states: run code inside the recorder's ordinary work, and objects a run hangs on
what the interpreter keeps past its audit hooks.
:::
