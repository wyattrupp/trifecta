---
status: done
authors: [claude]
created: 2026-11-11
---
# Storable test modules

:::{plan}
:implements: DES_0009
:::

## Read before starting

{need}`RFC_0009`, with the measurements its Motivation and Questions hold, and
{need}`DEC_0032` to {need}`DEC_0040`. {need}`DES_0008`'s COMP_RECORDER, IF_MANIFEST and
COMP_RESULT_STORE, which every task here extends, and the As built entries of
{need}`PLAN_0007` tasks 2 and 3, which say how the recorder and the store were built and
which modules they leave unstored.

## Rules for every task

No task starts until {need}`PLAN_0007` is done (wyatt, 2026-11-11: "Move the host-name
fix too"). Tasks 3 to 7 follow {need}`DEC_0032`'s order as re-ranked on 2026-11-12, and a lift shared by several
modules lands in the task of the first module that needs it. Each task records, in its As
built entry, the fixture runner's profile before and after it, locally and from both CI
jobs, which modules it made storable, and every reason each module in scope still has,
from task 2's profile; a module the gate names as stored that still has a reason is not
stored, and the reason is recorded rather than lifted by a new form the design does not
state. No number is a target or a gate (wyatt, 2026-11-10: "No number yet", "Report
only"). Each lift lands with the tests {need}`REQ_LIFT_PROVEN` asks for, declared for
{need}`REQ_REUSE_SOUND`: a change to each input it records reruns the module, a start
outside its terms is refused, and each input it does not record reruns the module or is
refused. The unmutated corpus passes at the end of every task, on Linux and Windows, and
`trifecta fixtures` and `trifecta fixtures --fresh` give the same result for every
fixture. A test moved into a module that stays fresh keeps its `@proves` and its
assertions unchanged. An edit to the reviewed text of a relied-on document,
{need}`DES_0008`'s IF_MANIFEST and {need}`DES_0009` among them, is reviewed k=2 and
stamped in the same task.

## Tasks

:::{task} A recorded run sees a fixed host name
:id: TASK_0008_01
:builds: COMP_HOST_NAME
:gate: The tests show, on Linux, that inside a recorded run `os.uname().nodename`, `posix.uname().nodename` and `platform.node()`, called before `platform.system()` and after it, all give the fixed host name; that a change to another `uname` field, given through a test double, reruns the module and the manifest holds that field only as a SHA-256; that `socket.gethostname` is refused, and a read of `/etc/hostname`, of `/proc/sys/kernel/hostname` and of the `HOSTNAME` variable is recorded; that `toolchain.bin_vale` reads nothing of the host on Windows; and that the modules stored before the task, `test_profile` among them, are stored after it.
Closes the `os.uname` gap {need}`RFC_0009` found in the recorder as built, before any lift relies on it.

- [x] **1.1** Wrap `os.uname` and `posix.uname` together and fill `platform`'s cache at the recorder's start, so each gives a fixed host name, and record the other fields, hashed, in a `uname` section.
- [x] **1.2** Amend {need}`DES_0008`'s IF_MANIFEST with the `uname` section, reviewed k=2 and stamped.
- [x] **1.3** Have `toolchain.bin_vale` test `os.name` in place of `platform.system()`.
- [x] **1.4** Add the tests, declared for REQ_HOST_READS and REQ_REUSE_SOUND.
- [x] **1.5** Record in the As built entry the profiles before and after.
:::

:::{task} Every refusal is named
:id: TASK_0008_02
:builds: COMP_REFUSAL_REASONS
:gate: The tests show that a run refused for two reasons, one in the module's process and one in a child, holds both in `reasons`, the child named by its executable's base name and `-m` module only, with `why` still the first; that a reason holds no environment value and no absolute path but the root's, home's, temporary directory's and prefixes' placeholders, and cuts any other outside path to its base name; that the same run is stored or refused exactly as without the change; and that the profile lists each unstored module's reasons and its tests' wall times.
Measure before lifting: the profile replaces {need}`RFC_0009`'s one-off probe.

- [x] **2.1** Keep every reason with its process, bounded as `why` is, in a `reasons` list, and amend IF_MANIFEST, reviewed k=2 and stamped.
- [x] **2.2** Report each test's wall time on the proof child's channel, and print each unstored module's reasons and times in the profile.
- [x] **2.3** Add the tests, declared for REQ_REFUSALS_NAMED.
- [x] **2.4** Record in the As built entry every module's reasons from both CI jobs, and compare them with {need}`RFC_0009`'s Motivation table.
:::

:::{task} Nested recording
:id: TASK_0008_03
:builds: COMP_NESTED_RECORDER
:gate: The tests show that a Python child that runs a recorder of its own is recorded by the parent's recorder, whose `.pth` file sorts first and whose wrapper of `_execute_child` is innermost; that a test wrapper that drops `TRIFECTA_RECORD_PARENT` or adds `-S` after the parent's wrapper is installed is refused; that a variable the child reads reaches both recorders; that the child's own manifest never stands for it; that a start whose environment already holds the parent's variable, not set by the parent's recorder, and a write into a directory the parent's recorder prepared are refused; that a wrapper or audit hook replaced in the child is caught at the child's start or exit and refused; that each way around a wrapper the design lists is documented by a test; and that `test_build_reuse` and `test_store_reuse`, whose only reason {need}`RFC_0009`'s probe saw was nested recording, are stored, or every reason task 2's profile still names for them on each platform, inside their nested children included, is recorded, and each is stored in the first later task that lifts its last reason, never by widening a lift beyond the design.
Module 1 of {need}`DEC_0032`'s order, the largest saving, and module 5, which needs nothing more.

- [x] **3.1** Write the parent's recorder, its start source and a `.pth` file that sorts before the test recorder's, as COMP_NESTED_RECORDER states.
- [x] **3.2** Add the tests, declared for REQ_NESTED_RECORDING and REQ_REUSE_SOUND.
- [x] **3.3** Record in the As built entry the profiles before and after, the cost of two recorders per event, and the reasons left in each nested child of modules 1, 3 and 5.
:::

:::{task} The traced build is keyed on its trace
:id: TASK_0008_04
:builds: COMP_KNOWN_PROGRAMS
:gate: The tests show that `strace` is let through only by its path and hash, started by `test_record_trace` with `-f -y -s 4096 -qq -o LOG` and `LOG` under the run's directory, and refused when started by another module, with other arguments, or with `LOG` elsewhere; that the key taken from its log holds every path read, probed or listed, each failed probe as an absence, each program started with its `#!` and ELF interpreters by hash, a change to an interpreter rerunning the module, and the whole environment, an inherited variable under `env=None` included and only the recorder's own and those the run set left out; that a change to a document the build read reruns `test_record_trace` and a change to a test it did not read does not; that a connection, a socket of a network family, a read under `/proc` or `/dev` outside the allowed list, and a content read of a process's own `/proc` other than listing `fd`, reading the `exe` link and reading `maps` and `cgroup` are refused, with {need}`DEC_0043`'s allowances let through and their neighbours refused: a socket of `AF_INET` or `AF_INET6` bound to a loopback address that never connects, sends, listens or accepts, and `/usr/share/locale/locale.alias` read through its link, recorded by the link, its target and what it reaches; that the traced command sees the fixed host name; and that `test_record_trace` is stored.
Module 2.

- [x] **4.1** Let `strace` through on its terms and build the key from its log, as COMP_KNOWN_PROGRAMS states.
- [x] **4.2** Amend IF_MANIFEST with the `programs` section, reviewed k=2 and stamped.
- [x] **4.3** Add the tests, declared for REQ_KNOWN_PROGRAM and REQ_REUSE_SOUND.
- [x] **4.4** Record in the As built entry the profiles before and after, and the copies that reused the module.
:::

:::{task} The recorder's own tests
:id: TASK_0008_05
:builds: COMP_LIFTED_REASONS
:gate: The tests show that `test_record`'s `-S` test, its tests whose children do a refused thing on purpose, its Windows ctypes tests and its test of two copies, whose `PYTHONPATH` names a copy outside the repository (wyatt, 2026-11-13: "Move it too (Recommended)"), run in a module of their own that is never stored, and so does `test_store_reuse`'s test that starts a child reading the host name on purpose (wyatt, 2026-11-13: "Move them, in task 5 (Recommended)", ruled as two tests; as measured, the module has one, on both platforms), each with its `@proves` and assertions unchanged, and that `test_record` and `test_store_reuse` are stored on both platforms.
Module 3, and what is left of module 5.

- [x] **5.1** Move those tests, `test_store_reuse`'s one and `test_record`'s test of two copies among them, into modules of their own, unchanged.
- [x] **5.2** Record in the As built entry the profiles before and after, and `test_record`'s saving against {need}`RFC_0009`'s bound less the moved tests' share.
:::

:::{task} git and Vale are known programs
:id: TASK_0008_06
:builds: COMP_KNOWN_PROGRAMS, COMP_LIFTED_REASONS
:gate: The tests show that git is let through only in the forms COMP_KNOWN_PROGRAMS lists, on a directory the run made, after its `init`, with the ceiling, `GIT_CONFIG_NOSYSTEM`, an empty `GIT_CONFIG_GLOBAL` and `HOME` and `XDG_CONFIG_HOME` on made directories; that a start without each of those settings, a `GIT_CONFIG_GLOBAL` that is not empty, any `-c`, `add`, `commit`, another `GIT_*` variable, `-C` on a directory the run did not make, a start before its `init`, a `.git` file, alternates, `commondir`, a hook, an `include.path` or `includeIf`, a configuration key `git init` does not write, a `filter.*.clean` key among them, a program planted on `PATH`, and git on this repository are refused; that a change to `TZ` or an `LD_*` variable reruns the module; that `bin/vale` is let through only when its own SHA-256 matches the pin for the platform, read from the package as loaded at the run's start, so rewriting the pin's file during the run changes nothing, a changed binary beside an untouched stamp being refused and a matching binary with an absent or wrong stamp let through, and a change to the pin's file rerunning the module; that Vale runs only in its two forms, with `--no-global`, `--config` under the made build directory and a configuration whose keys are on the list and whose `StylesPath` and vocabulary paths stay under it; that `Packages`, `sync`, any `VALE_*` variable, another option and a linted file of a format for which Vale starts a program are refused; that, on Linux, git and Vale in their forms under `strace` read nothing outside their stated inputs, start nothing further, read no host name and connect nowhere; and that `test_init` is stored on both platforms, with its bash test and its Windows junction tests in modules that stay fresh and the check's Sphinx build started in `docs/`.
Module 4, and the git `test_planning` needs.

- [x] **6.1** Let git and Vale through on their terms, with the Windows lists stated from each program's layout, and add the pin of Vale's binary per platform to the toolchain.
- [x] **6.2** Add `--no-global` to `run_vale`, start the Sphinx build in `docs/` and map its warning paths as before, and have the tests pin the git environment.
- [x] **6.3** Move `test_init`'s bash test and its Windows junction tests into modules of their own, unchanged.
- [x] **6.4** Add the tests, declared for REQ_KNOWN_PROGRAM and REQ_REUSE_SOUND.
- [x] **6.5** Record in the As built entry the profiles before and after.
:::

:::{task} The last modules
:id: TASK_0008_07
:builds: COMP_LIFTED_REASONS
:gate: The tests show that a process that exits through `os._exit` writes its manifest under a temporary name, renames it into place last and passes its status to the real exit (wyatt, 2026-11-14: "Pass-through is enough (Recommended)"); that another thread's audited operation begun after `os._exit` was called does not complete before the exit; that an event after the snapshot rewrites the manifest as refused; that a process that dies between the write and the rename leaves no manifest under the final name and is refused; that a recorded hook child that exits through `os._exit(2)` is stored and passes status 2 to the real exit; that the hook child that left a malformed manifest no longer does, its cause recorded; that `test_package` builds its wheel through `flit_core.buildapi.build_wheel` and is stored on both platforms; that `test_planning` is stored on both platforms, with its bash test and its Windows junction and ctypes tests in modules that stay fresh; that `test_adoption`'s guide test runs in a module of its own that is never stored; and that `trifecta fixtures` and `trifecta fixtures --fresh` give the same result for every fixture on Linux and Windows.
Modules 6 and 7, and what is left of `test_adoption`. The last task, so it also closes the design.

- [x] **7.1** Wrap `os._exit` as COMP_LIFTED_REASONS states, and find and fix the cause of the malformed hook manifest.
- [x] **7.2** Build `test_package`'s wheel through the backend.
- [x] **7.3** Move `test_planning`'s bash test and Windows junction and ctypes tests, and `test_adoption`'s guide test, into modules of their own, unchanged.
- [x] **7.4** Add the tests, declared for REQ_LIFT_PROVEN and REQ_REUSE_SOUND.
- [x] **7.5** Record in the As built entry the profiles before and after, against {need}`DEC_0032`'s bounds, and which modules stay fresh and why.
:::

## Review

:::{review} Correctness; security
:id: REV_PLAN_0008_1
:k: 2
:date: 2026-11-12
:digest: 44f983054a914b16bba475e9d2668dace49a4372edbbbb80de09753c283c86b9
The reviews recorded as {need}`REV_RFC_0009_5` and {need}`REV_RFC_0009_6` covered this
document's tasks; this record marks it active, wyatt having asked on 2026-11-12 that it
be run, "run in sdd", after {need}`PLAN_0007` was done.
:::

:::{review} Correctness; security
:id: REV_PLAN_0008_2
:k: 2
:date: 2026-11-13
:digest: 5527093548db7c4c695b7df5afa26d4c25621f7c87cbe7ba16ecc5cce3e8a511
Reviewed with {need}`DES_0009` in this plan's task 3. Folded in: task 5 moves
`test_store_reuse`'s two tests that start a child reading the host name, as wyatt ruled
on 2026-11-13, "Move them, in task 5 (Recommended)", and stores that module.
:::

:::{review} Correctness; security
:id: REV_PLAN_0008_3
:k: 2
:date: 2026-11-13
:digest: fa007d8c77363c98b51d38a0f99842158114677fa940859129fe8d6770625759
Reviewed with {need}`DES_0009` in this plan's task 4. Folded in: task 4's gate lets
through {need}`DEC_0043`'s allowances and refuses their neighbours.
:::

:::{review} Correctness; security
:id: REV_PLAN_0008_4
:k: 2
:date: 2026-11-13
:digest: 655edae7a2843b6517787cd02bf9b082a256d219f41541f7a8b846d094b30d5d
One round, one reviewer per lens, on this plan's task 5. Folded in: wyatt's ruling of
2026-11-13 moving `test_record`'s test of two copies, "Move it too (Recommended)"; the
host-name tests of `test_store_reuse` counted as measured, one.
:::

:::{review} Correctness; security
:id: REV_PLAN_0008_5
:k: 2
:date: 2026-11-14
:digest: 8668772a555f2042851fca6a41e5a6b95c43fb106152b174b5b9dcc7c405e3d4
On task 7's gate, amended to pass the exit status through to the real exit (wyatt,
2026-11-14: "Pass-through is enough (Recommended)").
:::

## As built

### Task 1 (2026-11-13)

Where `os.uname` exists, the recorder calls the real `posix.uname()` once at its start,
builds the result with the host name `localhost`, the design's value and not ruled, and
has `os.uname` and `posix.uname` return it, keeping no reference to the original; it then
empties `platform`'s cache and fills it through the wrapper. The other four fields are
recorded as SHA-256 values in the `uname` section, which `valid()` requires in full where
`os.uname` exists and the store's lookup takes again, a miss naming the field and never
its value. Since the cache is filled at the start, the fields are recorded in every
recorded run on Linux, not only in one that reads them, so a change to the runner's
kernel reruns every stored module there. The recorder now imports `platform` in every
recorded process on Linux. On Windows nothing changes: `platform`'s first fill reads the
name through `socket.gethostname`, which stays refused. `toolchain.bin_vale` tests
`os.name`.

The reviews found more ways to the real host name than the design listed, and each is
now refused, with a test: a fresh `posix` by `import`, `importlib`, `module_from_spec`,
`_imp.create_builtin` or `importlib._bootstrap._load`, the wrapper of
`_imp.create_builtin` reading a spec's name once and refusing a name that is not a `str`;
and a new interpreter, `cpython.PyInterpreterState_New`, which {need}`DES_0008`'s
recorder had let through and which runs with no hooks. {need}`DES_0008`'s IF_MANIFEST
and Risks, and {need}`DES_0009`'s Interfaces, were amended, reviewed k=2 and stamped.
Review findings dropped: taking a wrapper apart, through its closure, stays out of
scope, as {need}`DES_0008`'s Risks now say; the manifest's `version` stays 1, since an
entry without `uname` is malformed and the package's hash already misses it.

Profiles, local Windows, 24 workers, report only; the runs before shared the machine with
a Linux run, so their times are noisy:

| Run | Total | Fixture step | Control | Fixtures summed | Module runs reused |
|---|---:|---:|---:|---:|---:|
| Before, 03b7cdc | 1018.5 | 833.2 | 84.3 | 19649 | 1480 of 1893 |
| After | 980.3 | 828.1 | 77.3 | 19372 | 1471 of 1893 |
| After, `--fresh` | 2341.9 | 2191.2 | 75.5 | 51235 | none |

`trifecta fixtures` and `trifecta fixtures --fresh` gave the same result for all 123
fixtures on Windows. The modules stored before the task are stored after it, on Windows
`test_profile`, `test_proofs`, `test_fast_tests`, `test_ci_cache`, `test_store`,
`test_release`, `test_adoption` and `test_record_trace`, and on Linux, in WSL, the first
six of those; the rest keep the reasons they had. WSL lacks `make` and a venv package,
so `test_adoption` fails there as it did before the task, and the Linux fixture runner
and profiles come from CI.

CI, the fixture runner's profile, before (main at ecb9ce5, push run 43392968986) and
after (this task's run 43393062415), seconds; both runs read main's store, so the same
module runs were reused:

| Job | Total before | Total after | Control before | Control after | Summed before | Summed after | Reused |
|---|---:|---:|---:|---:|---:|---:|---:|
| Linux | 1895.7 | 1562.1 | 51.7 | 41.0 | 7291 | 6052 | 1424 |
| Windows | 2853.6 | 2043.0 | 84.4 | 60.4 | 10803 | 7669 | 1492 |

The control stored the same modules before and after, on Linux `test_ci_cache`,
`test_fast_tests`, `test_profile`, `test_proofs`, `test_release` and `test_store`, and on
Windows those and `test_adoption` and `test_record_trace`; all 123 fixtures passed in
both jobs. The spread between runs is wider than the change.

### Task 2 (2026-11-13)

The recorder keeps every distinct reason in a `reasons` list, the run's own in the order
raised and then each Python child's in the order the children started, at most 64, each
with its process; a child is named by its executable's base name less `.exe`, with `-m`
and the module when it was started so, read by one walker of the interpreter's options
that also decides `-S`. Once refused, a run notes reasons only, never inputs, and still
records its Python children, so their reasons are named; this made the unstored modules
slower, `test_init` from 22.7 to 32.4 s on Windows. A reason is built from names, paths
and module names only, never a variable's value (wyatt, 2026-11-13: "Never put values in
(Recommended)"), with a backstop that replaces a value of four characters or more; a path
is cut before the reason is formatted, and `refuse` falls back to a fixed reason rather
than raise out of the audit hook. The proof child writes each test's wall time on its
channel as a `time` record, and `trifecta profile` prints each unstored module's reasons
and times; a storable run the check did not store now names why. Naming changes nothing
about storing: the same modules are stored before and after, on Windows and in WSL.
{need}`DES_0008`'s IF_MANIFEST and IF_PROFILE were amended, reviewed k=2 in three rounds
and stamped. Review findings dropped: a raw outside path with a space keeps its tail in
the backstop's cleaning, reached only by an unlisted audit event's name; DES_0004's
prose of the channel, which never listed every record, is not amended for `time`.

Reasons, local, Windows and WSL, with the module's summed test seconds; "own" is the
module's own process:

| Module | Windows | Linux, WSL | Windows s | Linux s |
|---|---|---|---:|---:|
| `test_build_reuse` | own: records into a directory of its own | the same | 47.3 | 34.8 |
| `test_record_trace` | stored | own: runs strace | 2.0 | 43.2 |
| `test_adoption` | stored | own: runs git, runs bash; `python -m pip`: reads through a link `os-release`, `mtab`, `rmt`, runs `lsb_release`, runs `uname` | 2.0 | 5.1 |
| `test_record` | own: records into a directory of its own, a child with `-S`, ctypes | own: records into a directory of its own, a child with `-S` | 30.8 | 23.7 |
| `test_store_reuse` | own: records into a directory of its own | the same | 18.7 | 13.8 |
| `test_init` | own: runs git, a junction, runs bash; `python -m trifecta`: runs git, runs vale | own: runs git, runs bash; `python -m trifecta`: runs git, runs vale | 32.4 | 22.4 |
| `test_package` | `python -m pip`: reads the host name, a WMI query, ctypes, `<home>/.cargo/bin/rustc.EXE` through a link, runs rustc | `python -m pip`: as in `test_adoption` | 9.6 | 6.1 |
| `test_planning` | own: runs git, a junction, ctypes, runs bash; `python`: a child left no manifest | own: runs git, runs bash; `python`: a child left no manifest | 22.9 | 14.8 |

Against {need}`RFC_0009`'s Motivation table the reasons agree, with two differences: the
Sphinx build's change of directory in `test_init` did not show, and `test_init` no longer
reads the host name on Windows, which task 1 fixed. The slowest unstored tests are
`test_build_reuse`'s `test_an_input_the_build_read_builds_again`, 17.1 s on Windows and
12.5 s in WSL, and `test_init`'s two `InitPasses` tests, 26.4 s together on Windows.

CI, this task's run 43397321078, the control's reasons, with the module's summed test
seconds; all 123 fixtures passed in both jobs:

| Module | Linux | Windows | Linux s | Windows s |
|---|---|---|---:|---:|
| `test_build_reuse` | own: records into a directory of its own | the same | 50.0 | 63.5 |
| `test_record_trace` | own: runs strace | stored | 27.7 | — |
| `test_adoption` | own: runs git, runs bash; `python3 -m pip`: reads through a link `os-release`, `mtab`, `vtrgb`, `vconsole.conf`, `rmt`, `resolv.conf` and `<home>/.cargo/bin/rustc`, runs `lsb_release`, `uname` and `rustc` | stored | 26.4 | — |
| `test_record` | own: records into a directory of its own, a child with `-S` | the same, and ctypes | 30.6 | 31.7 |
| `test_store_reuse` | own: records into a directory of its own | the same | 17.3 | 23.0 |
| `test_init` | own: runs git, runs bash; `python3 -m trifecta`: runs git, runs vale | the same, and a junction | 31.8 | 50.6 |
| `test_package` | `python3 -m pip`: as in `test_adoption` | `python -m pip`: ctypes, reads the host name, a WMI query, runs rustc | 4.2 | 9.1 |
| `test_planning` | own: runs git, runs bash; `python3`: a child left no manifest | the same, and a junction and ctypes | 10.2 | 20.3 |

The fixture runner took 3004.9 s on Linux and 3380.7 s on Windows, against 1562.1 and
2043.0 s in task 1's run, its summed fixture time 11618 and 12871 s against 6052 and
7669; refused runs now record their Python children, and the spread between runs is
wide. The CI reasons agree with the local ones, and add on Linux the `pip` child's reads
of `vtrgb`, `vconsole.conf`, `resolv.conf` and `rustc`, which the runner's image has.

### Task 3 (2026-11-14)

The entries for tasks 3 to 7 were written after the five tasks merged, from the fixture runner's
profile of each task's last pull request run, Linux and Windows, which all read main's
store; the run before a task is the previous task's last run, task 2's being
43471902430. Local profiles and `trifecta fixtures --fresh` comparisons were taken while
each task was built but not kept, so they are not recorded here; what each task's pull
request reported locally is quoted where it bears on the gate. A copy whose tests and
package equal the base's takes the control's reports, 84 of the 123, so "reused" below
counts the 39 copies that run the test stage. All 123 fixtures passed in every run listed.
The spread between runs is wider than most single changes, as in task 1.

| Run | Task | Linux total | Linux control | Linux summed | Windows total | Windows control | Windows summed | Stored, Linux | Stored, Windows |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 43471902430 | 2 | 2769.3 | 71.2 | 10736 | 3440.3 | 98.8 | 13043 | 6 of 14 | 8 of 14 |
| 43527987859 | 3 | 3558.5 | 113.7 | 13710 | 3778.9 | 122.7 | 14295 | 7 of 15 | 9 of 15 |
| 43536665100 | 4 | 2402.0 | 74.9 | 9279 | 4135.8 | 137.2 | 15599 | 7 of 15 | 9 of 15 |
| 43538789907 | 5 | 2726.8 | 91.0 | 10454 | 2668.1 | 98.9 | 9995 | 9 of 17 | 10 of 17 |
| 43631051212 | 6 | 3580.8 | 134.7 | 13703 | 2783.1 | 119.6 | 10250 | 10 of 20 | 13 of 20 |
| 43638021586 | 7 | 2144.8 | 81.5 | 8221 | 2224.9 | 90.7 | 8312 | 13 of 22 | 16 of 22 |

The parent's recorder, `_trifecta_record_parent`, with a `.pth` file that sorts first,
records each Python child that runs a recorder of its own, and the child's own manifest
never stands for it. The reviews, in four rounds, found more ways for a child to run code
before `site` than the design listed, and each is refused with a test in
`test_record_nested`, which stays unstored: `PYTHONHOME`, `PLATLIBDIR`, `PYTHONSTARTUP`,
frozen modules and `pycache_prefix` settings, a `-W` or `PYTHONWARNINGS` category outside
the standard library, a `PYTHONPATH` entry that is no directory or lies outside the
repository and the prefixes, a standard library shadow, a module outside the standard
library loaded before the start, and writes judged by where they land. A child's
`PYTHONPATH` travels in its configuration until its recorder starts. {need}`DEC_0041` and
{need}`DEC_0042` record wyatt's rulings of 2026-11-13. Two recorders per event cost well
over twice one, `os.stat` from 45 to 420 µs on Linux.

`test_build_reuse` is stored on both platforms; 34 of the 39 copies reused it on each.
The reasons left in the nested children include `test_record`'s `-S` child, its
children whose `PYTHONPATH` names a copy outside the repository, and `python3` children
that replace `os.uname`, import a builtin by a name that is no `str`, start another
interpreter, read the host name, run a program a variable names or change the working
directory; and `test_store_reuse`'s child that reads the host name, on both platforms.
Task 5's moves lifted these. On Windows `test_record`'s own process also loads native
code through ctypes, which no task lifted.

### Task 4 (2026-11-14)

`strace` is let through for `test_record_trace`'s own process only, in the form
`strace -f -y -s 4096 -qq -o LOG`, and the run is keyed on what the log shows, with the
`programs` section retaken at lookup. {need}`DEC_0043`, {need}`DEC_0044` and
{need}`DEC_0045` record wyatt's rulings of 2026-11-13. A `=names` digest now reruns any
module when a variable appears or vanishes. Locally, in WSL, the module took 46 s fresh
and 0.16 s reused, and a changed document it read reran it.

The gate's "stored" holds locally but not on the CI runner: there the trace reaches
`/proc/sys/crypto/fips_enabled` and reads `openssl.cnf`, `libz.so.1`, `libbz2.so.1.0`,
`liblzma.so.5` and `libuuid.so.1` through links, none of which {need}`DEC_0043` allows, so none of the 39
copies reused it on Linux. On Windows it was already stored. The reasons are recorded, not
lifted, as this plan's rules ask.

### Task 5 (2026-11-14)

23 tests of `test_record` moved to `test_record_refused`, and `test_store_reuse`'s one
host-name test to `test_store_reuse_refused`, each unchanged; an AST comparison found the
same 70 tests before and after. On Linux `test_record` and `test_store_reuse` are stored,
each reused in 33 of 39 copies. On Windows `test_store_reuse` is stored, 34 of 39, but
`test_record` is not: its own process loads native code through ctypes on the runner, as
it still does after task 7, so that part of the gate holds on Linux and locally on
Windows only. On Linux `test_record` took 714 s summed over the six copies that ran it,
against 5544 s over the 39 that ran it in task 4's run; the saving bounded from WSL times was
about 1340 of 1490 s.

### Task 6 (2026-11-14)

git is let through in {need}`DEC_0033`'s forms only, with the pinned environment, on a
repository the run made; Vale only when its binary matches the platform's pin, in its two
forms with `--no-global`. {need}`DEC_0046` to {need}`DEC_0049` record wyatt's rulings of
2026-11-13. CI then showed three causes the local runs had not, each fixed in this task:
the runner's `locale.alias` is a link, skipped by name (wyatt, 2026-11-14: "Skip
LOCALE_ALIAS (Recommended)"); Windows' Git has a `ucrt64` build, stated beside `mingw64`
with every other build held absent (wyatt, 2026-11-14: "State ucrt64 too
(Recommended)"); and git and Vale read `$PWD`, so the check starts them without it and
the recorder refuses a start that holds it, {need}`DEC_0050` (wyatt, 2026-11-14: "Strip
PWD for git/Vale (Recommended)").

`test_init` is stored on both platforms, reused in 34 of 39 copies on each. The new
`test_record_programs` and `test_record_programs_traced` stay unstored on the Linux
runner, the first probing `locale.alias` through its link, the second reading the dynamic
loader and libraries through links.

### Task 7 (2026-11-14)

The recorder wraps `os._exit`: it converts the status, writes its manifest under a
temporary name and renames it into place last, holding the shared lock through the real
exit, and passes the status through (wyatt, 2026-11-14: "Pass-through is enough
(Recommended)"). After the snapshot, an event that is no recorder's own refuses the run.
A run that adds an audit hook, registers its own codec function or error handler, or a
`sys.monitoring` callback is refused; fork callbacks are held by a stub and dropped after
the seal (wyatt, 2026-11-14: "Keep the stub (Recommended)"); signal handlers are wrapped
and read back as given, and one that runs inside the recorder's work refuses the run
(wyatt, 2026-11-14: "Keep it in task 7 (Recommended)"). The malformed hook manifest was
the one `test_planning`'s share-path test left on Linux, its `\\localhost\c$` kept as a
probe key that `valid()` rejects, as {need}`DES_0009` records; task 3's refusal of such
paths already made it a valid refused manifest. `test_package` builds its wheel through
`flit_core.buildapi.build_wheel`. Review, in three rounds, left two classes to a later
plan, written into {need}`DES_0009`'s Risks (wyatt, 2026-11-14: "Follow-up plan
(Recommended)" and "Stop; defer the class (Recommended)"): code a run arranges to run
inside the recorder's ordinary work, and objects it hangs on what the interpreter keeps
past its audit hooks.

CI's first run failed the control: `test_record_nested`'s prefixes test wrote its probe
into the site directories, which the store's identity lists, so a module running beside
it was stored under one identity and looked up under another. The probe now lands at
`sys.prefix`, which the recorder refuses alike.

`test_planning` and `test_package` are stored on both platforms, each reused in 34 of 39
copies. Against {need}`DEC_0032`'s Linux bounds, summed over 123 copies, the fixture
runner's summed time went from 10736 s after task 2 to 8221 s; the runs differ by more
than the plan's changes, so no saving is claimed per module. The modules that stay fresh,
and why, from the control of run 43638021586:

| Module | Linux | Windows |
|---|---|---|
| `test_adoption_guide` | runs git with `GIT_LFS_SKIP_SMUDGE` set, runs bash; `python3 -m pip`: reads through links | stored, its one test running on POSIX only |
| `test_init_refused` | runs git outside its forms, runs bash | the same, and a junction |
| `test_planning_refused` | a child's `PYTHONPATH` outside the repository, runs git with `GIT_LFS_SKIP_SMUDGE` set, runs bash | the same, a junction, ctypes and a path through a share or a device namespace |
| `test_record_nested` | a child's `PYTHONPATH` outside the repository, writes under the prefixes, a warnings category outside the standard library, among others | the same, and a path through a share or a device namespace |
| `test_record_refused` | a child with `-S`, a child's `PYTHONPATH` outside the repository, registers a codec search function, among others | the same, and ctypes |
| `test_store_reuse_refused` | `python3`: reads the host name | the same |
| `test_record_trace` | `strace` reaches `fips_enabled` and reads libraries through links | stored |
| `test_record_programs` | probes `locale.alias` through its link | stored |
| `test_record_programs_traced` | runs strace, which only `test_record_trace`'s own process may start; reads the loader and libraries through links | stored |
| `test_record` | stored | loads native code through ctypes |

The first six refuse on purpose on Linux, and `test_record_programs_traced` does by
design; on Windows `test_adoption_guide` is stored, since its one test runs on POSIX
only. The rest are left by the runners: on Linux by links in the image that
{need}`DEC_0043` and {need}`DEC_0045` do not cover, on Windows by `test_record`'s own
ctypes use there.

The gate's `trifecta fixtures` against `trifecta fixtures --fresh` was compared on
Windows only, 123 of 123 alike, before the review's second round of fixes; it was not
compared on Linux, nor again after those fixes.

So four parts of the gates hold locally but not on the CI runners: `test_record_trace`
stored on Linux, `test_record` stored on Windows, `test_adoption_guide` never stored on
Windows, and the `--fresh` comparison on both platforms after the last fixes. The plan
closes with them recorded here and carried into a follow-up plan, beside the two classes
{need}`DES_0009`'s Risks defer (wyatt, 2026-11-14: "Close; follow-up plan
(Recommended)").
