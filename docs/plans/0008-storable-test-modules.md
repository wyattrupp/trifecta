---
status: active
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

- [ ] **2.1** Keep every reason with its process, bounded as `why` is, in a `reasons` list, and amend IF_MANIFEST, reviewed k=2 and stamped.
- [ ] **2.2** Report each test's wall time on the proof child's channel, and print each unstored module's reasons and times in the profile.
- [ ] **2.3** Add the tests, declared for REQ_REFUSALS_NAMED.
- [ ] **2.4** Record in the As built entry every module's reasons from both CI jobs, and compare them with {need}`RFC_0009`'s Motivation table.
:::

:::{task} Nested recording
:id: TASK_0008_03
:builds: COMP_NESTED_RECORDER
:gate: The tests show that a Python child that runs a recorder of its own is recorded by the parent's recorder, whose `.pth` file sorts first and whose wrapper of `_execute_child` is innermost; that a test wrapper that drops `TRIFECTA_RECORD_PARENT` or adds `-S` after the parent's wrapper is installed is refused; that a variable the child reads reaches both recorders; that the child's own manifest never stands for it; that a start whose environment already holds the parent's variable, not set by the parent's recorder, and a write into a directory the parent's recorder prepared are refused; that a wrapper or audit hook replaced in the child is caught at the child's start or exit and refused; that each way around a wrapper the design lists is documented by a test; and that `test_build_reuse` and `test_store_reuse`, whose only reason {need}`RFC_0009`'s probe saw was nested recording, are stored, or every reason task 2's profile still names for them on each platform, inside their nested children included, is recorded, and each is stored in the first later task that lifts its last reason, never by widening a lift beyond the design.
Module 1 of {need}`DEC_0032`'s order, the largest saving, and module 5, which needs nothing more.

- [ ] **3.1** Write the parent's recorder, its start source and a `.pth` file that sorts before the test recorder's, as COMP_NESTED_RECORDER states.
- [ ] **3.2** Add the tests, declared for REQ_NESTED_RECORDING and REQ_REUSE_SOUND.
- [ ] **3.3** Record in the As built entry the profiles before and after, the cost of two recorders per event, and the reasons left in each nested child of modules 1, 3 and 5.
:::

:::{task} The traced build is keyed on its trace
:id: TASK_0008_04
:builds: COMP_KNOWN_PROGRAMS
:gate: The tests show that `strace` is let through only by its path and hash, started by `test_record_trace` with `-f -y -s 4096 -qq -o LOG` and `LOG` under the run's directory, and refused when started by another module, with other arguments, or with `LOG` elsewhere; that the key taken from its log holds every path read, probed or listed, each failed probe as an absence, each program started with its `#!` and ELF interpreters by hash, a change to an interpreter rerunning the module, and the whole environment, an inherited variable under `env=None` included and only the recorder's own and those the run set left out; that a change to a document the build read reruns `test_record_trace` and a change to a test it did not read does not; that a connection, a socket of a network family, a read under `/proc` or `/dev` outside the allowed list, and a content read of a process's own `/proc` other than listing `fd` and reading the `exe` link are refused; that the traced command sees the fixed host name; and that `test_record_trace` is stored.
Module 2.

- [ ] **4.1** Let `strace` through on its terms and build the key from its log, as COMP_KNOWN_PROGRAMS states.
- [ ] **4.2** Amend IF_MANIFEST with the `programs` section, reviewed k=2 and stamped.
- [ ] **4.3** Add the tests, declared for REQ_KNOWN_PROGRAM and REQ_REUSE_SOUND.
- [ ] **4.4** Record in the As built entry the profiles before and after, and the copies that reused the module.
:::

:::{task} The recorder's own tests
:id: TASK_0008_05
:builds: COMP_LIFTED_REASONS
:gate: The tests show that `test_record`'s `-S` test, its tests whose children do a refused thing on purpose, and its Windows ctypes tests run in a module of their own that is never stored, and so do `test_store_reuse`'s two tests that start a child reading the host name on purpose (wyatt, 2026-11-13: "Move them, in task 5 (Recommended)"), each with its `@proves` and assertions unchanged, and that `test_record` and `test_store_reuse` are stored on both platforms.
Module 3, and what is left of module 5.

- [ ] **5.1** Move those tests, `test_store_reuse`'s two among them, into modules of their own, unchanged.
- [ ] **5.2** Record in the As built entry the profiles before and after, and `test_record`'s saving against {need}`RFC_0009`'s bound less the moved tests' share.
:::

:::{task} git and Vale are known programs
:id: TASK_0008_06
:builds: COMP_KNOWN_PROGRAMS, COMP_LIFTED_REASONS
:gate: The tests show that git is let through only in the forms COMP_KNOWN_PROGRAMS lists, on a directory the run made, after its `init`, with the ceiling, `GIT_CONFIG_NOSYSTEM`, an empty `GIT_CONFIG_GLOBAL` and `HOME` and `XDG_CONFIG_HOME` on made directories; that a start without each of those settings, a `GIT_CONFIG_GLOBAL` that is not empty, any `-c`, `add`, `commit`, another `GIT_*` variable, `-C` on a directory the run did not make, a start before its `init`, a `.git` file, alternates, `commondir`, a hook, an `include.path` or `includeIf`, a configuration key `git init` does not write, a `filter.*.clean` key among them, a program planted on `PATH`, and git on this repository are refused; that a change to `TZ` or an `LD_*` variable reruns the module; that `bin/vale` is let through only when its own SHA-256 matches the pin for the platform, read from the package as loaded at the run's start, so rewriting the pin's file during the run changes nothing, a changed binary beside an untouched stamp being refused and a matching binary with an absent or wrong stamp let through, and a change to the pin's file rerunning the module; that Vale runs only in its two forms, with `--no-global`, `--config` under the made build directory and a configuration whose keys are on the list and whose `StylesPath` and vocabulary paths stay under it; that `Packages`, `sync`, any `VALE_*` variable, another option and a linted file of a format for which Vale starts a program are refused; that, on Linux, git and Vale in their forms under `strace` read nothing outside their stated inputs, start nothing further, read no host name and connect nowhere; and that `test_init` is stored on both platforms, with its bash test and its Windows junction tests in modules that stay fresh and the check's Sphinx build started in `docs/`.
Module 4, and the git `test_planning` needs.

- [ ] **6.1** Let git and Vale through on their terms, with the Windows lists stated from each program's layout, and add the pin of Vale's binary per platform to the toolchain.
- [ ] **6.2** Add `--no-global` to `run_vale`, start the Sphinx build in `docs/` and map its warning paths as before, and have the tests pin the git environment.
- [ ] **6.3** Move `test_init`'s bash test and its Windows junction tests into modules of their own, unchanged.
- [ ] **6.4** Add the tests, declared for REQ_KNOWN_PROGRAM and REQ_REUSE_SOUND.
- [ ] **6.5** Record in the As built entry the profiles before and after.
:::

:::{task} The last modules
:id: TASK_0008_07
:builds: COMP_LIFTED_REASONS
:gate: The tests show that a process that exits through `os._exit` writes its manifest with its exit status under a temporary name and renames it into place last; that another thread's audited operation begun after `os._exit` was called does not complete before the exit; that an event after the snapshot rewrites the manifest as refused; that a process that dies between the write and the rename leaves no manifest under the final name and is refused; that a recorded hook child that exits through `os._exit(2)` is stored with exit status 2; that the hook child that left a malformed manifest no longer does, its cause recorded; that `test_package` builds its wheel through `flit_core.buildapi.build_wheel` and is stored on both platforms; that `test_planning` is stored on both platforms, with its bash test and its Windows junction and ctypes tests in modules that stay fresh; that `test_adoption`'s guide test runs in a module of its own that is never stored; and that `trifecta fixtures` and `trifecta fixtures --fresh` give the same result for every fixture on Linux and Windows.
Modules 6 and 7, and what is left of `test_adoption`. The last task, so it also closes the design.

- [ ] **7.1** Wrap `os._exit` as COMP_LIFTED_REASONS states, and find and fix the cause of the malformed hook manifest.
- [ ] **7.2** Build `test_package`'s wheel through the backend.
- [ ] **7.3** Move `test_planning`'s bash test and Windows junction and ctypes tests, and `test_adoption`'s guide test, into modules of their own, unchanged.
- [ ] **7.4** Add the tests, declared for REQ_LIFT_PROVEN and REQ_REUSE_SOUND.
- [ ] **7.5** Record in the As built entry the profiles before and after, against {need}`DEC_0032`'s bounds, and which modules stay fresh and why.
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
