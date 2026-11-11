---
status: active
authors: [claude]
created: 2026-11-10
---
# Fast checks

:::{plan}
:implements: DES_0008
:::

## Read before starting

{need}`RFC_0008`, with the numbers its Motivation holds, and {need}`DEC_0028` to
{need}`DEC_0031`. {need}`DES_0004`'s COMP_TEST_PROOFS states what the test stage
judges, which reuse leaves unchanged. The As built entries of {need}`PLAN_0003` tasks 3
and 4 explain the test child and today's cache, which task 3 here replaces.

## Rules for every task

Profile first: task 1 lands before any reuse, and each later task records, in its As
built entry, the profile of the check and the fixture runner before and after it, locally
and from both CI jobs. No number is a target or a gate (wyatt, 2026-11-10: "No number
yet", "Report only"). Each requirement gets its proving test in the task that enforces
it, named with `@proves`, since no corpus mutation can show a profile or a reuse, and
each built component gets its `spec` path in the same task. The
unmutated corpus passes at the end of every task, on Linux and Windows, and so does
`trifecta fixtures --fresh` once task 3 adds it. An edit to the reviewed text of a
relied-on document is reviewed k=2 and stamped in the same task.

## Tasks

:::{task} Profile
:id: TASK_0007_01
:builds: COMP_PROFILER, IF_PROFILE
:gate: The tests that run the check with and without `--profile` on the same tree give byte-identical standard output and the same exit status, with a finding and without; the check's profile lists every stage of `check.main` in run order; the fixture runner's profile lists the base copy, the control and every fixture with its stages; a profile that cannot be written leaves the output and exit status unchanged; `trifecta profile` prints both kinds as a table; both CI jobs upload the profile and write the tables to the job summary.
Measure before changing anything.

- [x] **1.1** Time each stage in `check.main` and write `docs/_build/profile/check.json`, or the `--profile` path, keeping the profile directory out of the clean before the build.
- [x] **1.2** Time the fixture runner's base copy, control and each fixture's copy, mutation and check, and merge each copy's own check profile into `fixtures.json`.
- [x] **1.3** Add `trifecta profile PATH` to the command line, and the tests, declared for REQ_PROFILED.
- [x] **1.4** Add to both CI jobs a last step that always runs, uploads `docs/_build/profile/` and appends the tables to the job summary.
- [x] **1.5** Record in the As built entry the profiles of both CI jobs and of a local run, and which stages and fixtures hold the time.
:::

:::{task} Recorder
:id: TASK_0007_02
:builds: COMP_RECORDER, IF_MANIFEST
:gate: The tests show the recorder lists a file read, a file copied with `shutil.copy2`, a file the run wrote and then read as no input, a directory listed with the kinds of its entries, a path probed through each wrapped function, on Windows too, as a file, a directory or absent, an environment variable read and one iterated, the source of every imported module, and a Python child's reads, under `-E` and `-I`; that a child started with `-S`, a child leaving no manifest, a `socket.connect`, a change of working directory, an audit event the recorder does not list, and a run of git or of any other program make the manifest unstorable; that the same run in two copies at different paths gives the same manifest; and, on Linux, that `strace -f` of the test stage and of the build opens, probes and lists no path inside the repository that the manifests do not hold, and makes no connection.
The record every reuse rests on, built and proven before anything reads it.

- [x] **2.1** Write `trifecta.record` as COMP_RECORDER states, with the manifest as IF_MANIFEST states.
- [x] **2.2** Have setup install the `.pth` file, in a virtual environment only, that starts the recorder once in a Python child when `TRIFECTA_RECORD` is set, and test that it imports nothing when the variable is unset and that setup outside a virtual environment writes none; run both CI jobs' setup in a virtual environment.
- [x] **2.3** Add the tests, declared for REQ_REUSE_SOUND, the `strace` one with the system value `posix`.
- [x] **2.4** Record in the As built entry what the recorder costs on the test stage, from the profile.
:::

:::{task} Result store and test reuse
:id: TASK_0007_03
:builds: COMP_RESULT_STORE, COMP_PROOF_REUSE
:gate: The tests show that a test module is run again when a file it read changes, a path it probed changes kind, a directory it listed gains an entry, a name its imports looked up appears, a variable it read changes, or the interpreter, an installed distribution or the running package changes, and is reused otherwise; that adding a test module runs that module and reuses the others; that a test child's environment holds no `TRIFECTA_STORE`; that a malformed entry is refused; that a manifest marked unstorable is never stored; that `--fresh` reuses nothing; that a stage the design does not name is never reused; and that the fixture runner gives the same findings for every fixture with `--fresh` and without.
Replaces today's cache, keyed on every file but `docs/`, with one keyed on what each module read.

- [x] **3.1** Write the result store as COMP_RESULT_STORE states, with `TRIFECTA_STORE` in place of `TRIFECTA_PROOF_CACHE`, and `--fresh` for `trifecta check` and `trifecta fixtures`.
- [x] **3.2** Run each proof module in a child of its own under the recorder, with `-B` and an empty `pycache_prefix`, store its records with its manifest, and judge stored and fresh records alike; remove `_content_key`, and remove `TRIFECTA_STORE` from every test child's environment.
- [x] **3.3** Amend DES_0004's COMP_TEST_PROOFS to one child per proof module, with its `os.name` and end-record rules holding per child, reviewed k=2 and stamped.
- [x] **3.4** Add the tests, declared for REQ_REUSE_SOUND and REQ_REUSE_SCOPED, including the comparison of every fixture's findings with `--fresh` and without.
- [x] **3.5** Record in the As built entry the profiles before and after, and which test modules are never stored and why.
:::

:::{task} Build reuse
:id: TASK_0007_04
:builds: COMP_BUILD_REUSE
:gate: The tests show that a change to a document, to `docs/conf.py`, or to a module the build imported runs the build again, that a change to the root `requirements.lock` or to a test restores the stored build and a change to a package file builds again, that the check's findings and their locations are the same either way, including a failed build's, in a copy at another path, and that an archive member that is absolute, holds `..` or is a link is refused; the fixture runner gives the same findings for every fixture with `--fresh` and without.
The second stage the profile measured.

- [x] **4.1** Run the Sphinx build under the recorder through `python -m trifecta.record sphinx`, and store and restore its warnings and output directory as COMP_BUILD_REUSE states.
- [x] **4.2** Add the tests, declared for REQ_REUSE_SOUND and REQ_REUSE_SCOPED.
- [ ] **4.3** Record in the As built entry the profiles before and after.
:::

:::{task} CI cache
:id: TASK_0007_05
:builds: COMP_CI_CACHE
:gate: In both CI jobs, a second run of the same commit restores setup's downloads and setup still checks every hash; a push run on main runs the fixtures from an empty store and uploads it; a pull request's run fetches that store by the run ID of main's latest successful push run of `.github/workflows/check.yml`, never a pull request run from a branch named main, and saves no cache entry holding results; the check step runs with `--fresh`; the fixture step's profile shows which results were reused.
The last task, so it also closes the design.

- [ ] **5.1** Have setup keep the Vale archive and check its SHA-256 before every extraction, and cache pip's downloaded archives and that archive in both jobs with `actions/cache/restore` and `actions/cache/save`, pinned by SHA, never `bin/`.
- [ ] **5.2** Run the check step with `--fresh`, in the Makefile and the Windows job; in push runs on main, run the fixtures from an empty store and upload it, named for `runner.os`; in pull request runs, add `actions: read` and fetch main's store by run ID.
- [ ] **5.3** Record in the As built entry both jobs' times from the workflow and from the profile, before and after, for a pull request that changes only a document and one that changes a test.
- [ ] **5.4** Mark DES_0008 implemented, check that every requirement of RFC_0008 has its proving test, and review this plan's As built k=2.
:::

## Review

:::{review} Correctness; security
:id: REV_PLAN_0007_1
:k: 2
:date: 2026-11-10
:digest: 7edce46089e72fd33ae7025a47802baaa8b77cbb47edb1bdb66d4ed558d482aa
The review recorded as {need}`REV_RFC_0008_1` covered this document. Build detail it
found, for the tasks that build it: count a directory as created only when `os.mkdir`
succeeds; hash the source of `os.rename` and `os.replace`; list `_winapi.CreateProcess`,
which follows `subprocess.Popen`, as known; check that `strace` is on the Ubuntu runner;
the `.pth` file can run twice in one Windows start, so the recorder installs once; a
`.venv` inside the repository needs a rule for which of the prefix and repository rules
wins; tolerate a failed `os.replace` on Windows while another process holds an entry, and
keep the newest of concurrent entries under one identity; find main's run by workflow
path, event `push`, branch main, success and this repository, and name the store artifact
for `runner.os`; cache archives fetched with `pip download` and installed with
`--no-index --require-hashes`, never pip's own wheel cache; set `actions: read` on the
jobs that fetch, not the workflow; never put a value from a fetched store into a cache
key; print stage names and times in the job summary, never environment values.
:::

## As built

### Task 1 (2026-11-11)

The profiler is `trifecta.profiler`. The check times sixteen stages in run order, writes
the profile in a `finally`, so a stage that raises still leaves one, and keeps
`docs/_build/profile/` out of the clean before the build; the clean removes a link or
junction rather than following it. `--profile`, on the check and the fixture runner, and
`trifecta profile` refuse a path outside the repository, as IF_CLI requires, so the
fixture runner reads each copy's own `docs/_build/profile/check.json` after removing the
one copied from the control, rather than naming a path outside the copy. Each fixture
record also holds `mutate_seconds` and `check_seconds`, which IF_PROFILE does not list.
IF_CLI in {need}`DES_0004` now names both, reviewed k=2 and stamped. Table cells escape
Markdown, since a fixture's name reaches the job summary. Review findings dropped: an
exception other than a fixture error, which ends the fixture runner as it did before,
leaves the fixtures it had run out of the profile; a `--profile` path that git does not
ignore is the caller's choice; a copy's own check writes the stages the fixture runner
merges, at the trust of the pull request that runs it.

Before (main at e1d92cd, push run 42933435772): the Linux job 703 s, its fixture step
657 s; the Windows job 909 s, its fixture step 847 s. After, in this task's last run
(run 42938992814): the Linux job 829 s, its fixture step 788 s; the Windows job 791 s,
its fixture step 734 s; the spread between runs of one commit is wider than the change.
Its profiles, in seconds:

| Run | Check | Tests | Sphinx | History | Fixture step | Control | Fixtures summed |
|---|---:|---:|---:|---:|---:|---:|---:|
| Linux CI | 26.0 | 19.3 | 5.6 | 0.2 | 787.7 | 26.0 | 2998 |
| Windows CI | 18.3 | 12.1 | 4.0 | 1.4 | 733.6 | 17.7 | 2668 |
| Local Windows, 24 workers | 97.8 | 72.0 | 16.9 | 4.8 | 765.5 | 79.9 | 14106 |

Summed over the fixtures, the tests and the Sphinx build hold most of the time: locally
6504 s and 3496 s of 14106, on Linux CI 1476 s and 1156 s of 2998, on Windows CI 969 s
and 966 s of 2668. Next come the history check, 276 s on Windows CI, the lint view and
the two Vale runs. The 50 fixtures that miss today's cache run every test and hold 68
percent of the summed fixture time locally, 9639 s, the slowest the `proven-by-test`
fixtures at 215 to 241 s each under contention; the 73 that change only `docs/` take
their test results from the cache and spend their time in the build and the stages
after it.

### Task 2 (2026-11-10)

The recorder is `trifecta.record`. The `.pth` file, `00-trifecta-record.pth` so that no
other `.pth` file runs first, executes the `start.py` that the parent writes into each
record directory, and that file loads the recorder named in the directory's
`config.json` under a module name no run imports. A copy's run therefore records with
the copy's own recorder, and the copy's package is never imported early. The recorder
removes `TRIFECTA_RECORD` from its own process, so only a child it starts through
`subprocess` gets a directory, and each child writes `made.json` beside its manifest,
listing what it created and wrote. The parent drops anything it first saw after the
child started that falls under those paths. Environment values are recorded as SHA-256
hashes of the value with the root replaced, never the value: DES_0008's COMP_RECORDER and
IF_MANIFEST now say so, reviewed k=2 and stamped. RFC_0008's term still says "with its
value", and a hash keys the same match.

What the recorder takes as input beyond the design's text:
- `os.stat`, `os.lstat` and `DirEntry.stat()` report a file's size, so each counts as a
  read of the file.
- A read, probe or listing that follows a link the run made goes to the target. One that
  follows a link the run did not make is refused.
- The `PYTHON*`, `LANG` and `LC_*` variables are recorded when the recorder starts,
  since the interpreter read them before it.
- A variable the run passes to a child through `env=` is the run's own.

Also refused: a path relative to a directory descriptor outside `shutil.rmtree`, a
directory renamed that the run did not make, a listing of a directory that holds the
repository, and a process started other than through `subprocess`, as `multiprocessing`
does. Known events, from sampling the build and the tests:
- The system's time zone, out of scope as the clock is: its key in the Windows registry,
  and on Linux `/etc/localtime`, `/etc/timezone` and the zone database, which babel
  follows through the `/etc/localtime` link. A refusal for a link names the link.
- The console functions colorama binds from `kernel32`.
- `socket.bind`, which urllib3 uses to test for IPv6.
- A `chdir` to the working directory, which Sphinx makes when it reads `conf.py`. The
  build therefore runs from `docs/`.

A Sphinx build of this repository, recorded, is storable: 65 files, 87 probes, 6 listings
and 166 lookups. Of the test modules, run one per child under the recorder:
- Storable: `test_profile`, `test_proofs` and `test_release`.
- Not storable: `test_init`, `test_planning` and `test_adoption`, which run git;
  `test_package`, whose build reads the host name; `test_record`, which records children
  of its own.

`test_record_trace` traces this repository's build and a small test child. It counts a
file read natively only when the manifest holds its hash, a listing only when the
manifest lists it, and a lookup's candidates only as the import system names them. It
reads `docs/`, which today's cache key leaves out until task 3 replaces it. CI's Ubuntu
runner has `strace`.

Review, two rounds. Applied:
- Correctness: the gaps above, a regression in the first fix that dropped a read made
  before the run rewrote the file, and a strict schema for manifests read from a store.
- Security: `prepare` refuses a linked or non-empty directory, and setup replaces the
  `.pth` file rather than writing through a link.

Dropped:
- A manifest is reported by the code it describes, so a store is trusted only from
  main's push runs, as the Risks state and task 5 builds.
- The `.pth` line runs under `-I`, as the design requires.
- An environment hash of a weak secret can be guessed, and the check's job holds no
  secret; task 5 keeps it that way.

Cost, from the profile, locally on Windows with every Python child of the check recorded:
the test stage 74 to 84 s against 55 to 64 s without, the build 8 to 12 s either way. The
test child records until its first refusal, so this is a floor. Task 3 measures each
module.

Profiles before and after, in seconds:

| Run | Check | Tests | Sphinx | Fixture step | Fixtures summed |
|---|---:|---:|---:|---:|---:|
| Linux CI, before (task 1) | 26.0 | 19.3 | 5.6 | 787.7 | 2998 |
| Linux CI, after | 39.0 | 34.3 | 4.0 | 806.0 | 3199 |
| Windows CI, before (task 1) | 18.3 | 12.1 | 4.0 | 733.6 | 2668 |
| Windows CI, after | 42.1 | 32.6 | 6.3 | 1305.9 | 4984 |
| Local, before (task 1) | 97.8 | 72.0 | 16.9 | 765.5 | 14106 |
| Local, after | 70.3 | 59.1 | 6.9 | 736.6 | 13495 |

The new tests add to every copy that misses today's cache: on Linux,
`test_record_trace` builds the documents again under `strace`.

On Windows the fixture step grew from 734 to 1306 s: each copy runs `test_record`, whose
recorded children cost most where a process is slow to start. CI run 42950770650 gave
the after rows; task 3's reuse of test modules is meant to take this back.

### Task 3 (2026-11-10)

The store is `trifecta.store`, `docs/_build/cache/` or the directory `TRIFECTA_STORE`
names, kept out of the clean. The test stage runs each proof module in a recorded child
of its own, looks it up first by its identity, and judges stored and fresh records alike.
Each child gets the whole list of tests to leave out, since a test one module inherits is
left out by the module that defines it, and that list is part of the identity. A result
is stored only from a child that reported its end, with the root's path replaced in each
of its spellings, and is read back with the running copy's path. Hashes are taken afresh
for each module, since a child before it may have changed the tree. A run inside a
recorded process uses no store unless its caller names one, and a stub child is never
stored. The profile lists each module after the `tests` stage, which holds them, as
`tests: <module>` with `reused` and `why`; no other stage carries `reused`.

The store also refuses:
- an entry over 16 MB;
- more than 16 entries tried or kept under one identity;
- a name `put` does not give;
- a file that is not regular;
- a network or device path in a manifest;
- a store reached through a link or junction, checked at every use.

When git tracks a file in the store, the check runs fresh. DES_0008's COMP_RESULT_STORE
says so, and its environment key holds the entries of the site directories, so a module
or `.pth` file no `RECORD` lists changes it. DES_0004's COMP_TEST_PROOFS and IF_CLI are
amended. Both were reviewed k=2 and stamped.

Never stored, in every copy:

| Module | Why |
|---|---|
| `test_init`, `test_planning` | They run git. |
| `test_adoption` | It runs git, on Linux only. |
| `test_package` | Its build reads the host name, or on Linux probes `/etc/os-release` through a link. |
| `test_record`, `test_store_reuse` | They start Python children that record into directories of their own. |
| `test_record_trace` | It runs strace, on Linux only. |

On Linux CI these modules hold 9,540 of the 10,860 seconds the copies spent on tests;
locally the five that run here hold 21,000 of 21,500. Reuse takes the other modules to a
few hundredths of a second each, but those were already the cheap ones.

`trifecta fixtures` and `trifecta fixtures --fresh` both pass 123/123 locally. Their
standard output is identical line for line, so every fixture gives the same result both
ways. That comparison is a run of both commands, not a test: a test that ran the fixture
runner would run again in every copy. The stored run reused 706 of 1,386 module runs and
the fresh run none.

Review, two rounds. Applied:
- Correctness:
  - the inherited leave-out;
  - stale hashes between children;
  - storing a run cut short;
  - the root's path in stored text;
  - the site directories;
  - stub children;
  - the per-identity link check.
- Security:
  - a tracked store runs fresh;
  - only regular files are hashed;
  - network and device paths are refused;
  - bounds on entries and their names;
  - each entry is read through a single open;
  - links;
  - printable reasons.

Dropped:
- **A test module that writes forged entries for another.** Test code runs with the
  check's full power, as DES_0004's Risks state. CI's check step runs `--fresh` from
  task 5.
- **A forged result for another module.** Placed beside the real one, it gives "has 2
  results".
- **Unsalted environment hashes.** Already settled in task 2.
- **A file edited in place under the site directories.** Setup installs only from the
  hash-checked lock.
- **A root that is a prefix of a sibling's path.** The placeholder may then replace too
  much, which costs a miss or a rewritten sibling path in a message, never a reuse.
- **The order of module records after `tests`.** As stated above.
- **Pruning in a shared fixture store.** A matter of speed, left to task 5.

The first CI run (42976895318) reused 236 of 1,386 module runs on Linux and none on
Windows, against 706 locally. Three causes, each a miss, never a false match, fixed and
reviewed k=2 again (correctness; security):
- `sysconfig` on Linux imports `_sysconfigdata__linux_x86_64-linux-gnu`, whose dashes
  failed the manifest's lookup-name rule, so six modules' manifests were refused. A name
  that is an identifier once its dashes are underscores now passes.
- The Windows runner has 8.3 short names on, so its temporary directory comes back as
  `RUNNER~1`: a directory a test made under the short spelling and read under the long
  one was an input, and a copy's `PYTHONPATH` held a spelling of its root the placeholder
  did not replace. The recorder compares paths by their long names, through
  `GetLongPathNameW` bound before its audit hook, and the fixture runner spells its
  temporary directory in full.
- An entry another copy pruned between the listing and the read was called malformed;
  it is skipped.

Applied from that review: binding `GetLongPathNameW` before the hook, since a first
binding with the hook live refused the run and one under the recorder's lock could
deadlock with a thread importing ctypes, and one buffer per call. Dropped: keeping the
binding out of a module global, since the recorder loads under its own name and no code
under test reaches it.

Profiles before and after, in seconds, after from CI run 42995781425:

| Run | Check | Tests | Sphinx | Fixture step | Fixtures summed |
|---|---:|---:|---:|---:|---:|
| Linux CI, before (task 2) | 39.0 | 34.3 | 4.0 | 806.0 | 3199 |
| Linux CI, after | 66.2 | 60.4 | 4.9 | 2825.6 | 10908 |
| Windows CI, before (task 2) | 42.1 | 32.6 | 6.3 | 1305.9 | 4984 |
| Windows CI, after | 63.4 | 56.0 | 4.7 | 2672.4 | 10229 |
| Local, before (task 2) | 70.3 | 59.1 | 6.9 | 736.6 | 13495 |
| Local, after, nothing stored | 134.1 | 114.1 | | | |
| Local, after, reused | 122.3 | 99.4 | 15.0 | 1161.5 | 25519 |
| Local, after, `--fresh` | | | | 1262.4 | 28003 |

The local fixture times are from before the CI fixes, which change nothing locally (no
short names here; 706 runs reused both times). The run after them took 1996 s with two
reviews and two checks running beside it, so it is not a measure.

The fixture step is slower than before, 3.5 times on Linux and twice on Windows, and the
check itself half again: each copy starts thirteen recorded children instead of one, and
the modules never stored are most of the time. CI reused 470 of 1,386 module runs on
Linux and 706 on Windows. This is the measured baseline the later tasks are compared
with; it was merged on wyatt's ruling (2026-11-11): "we're establishing a measured
baseline here. keep going".
