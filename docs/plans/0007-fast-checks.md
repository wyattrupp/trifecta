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
- [ ] **1.5** Record in the As built entry the profiles of both CI jobs and of a local run, and which stages and fixtures hold the time.
:::

:::{task} Recorder
:id: TASK_0007_02
:builds: COMP_RECORDER, IF_MANIFEST
:gate: The tests show the recorder lists a file read, a file copied with `shutil.copy2`, a file the run wrote and then read as no input, a directory listed with the kinds of its entries, a path probed through each wrapped function, on Windows too, as a file, a directory or absent, an environment variable read and one iterated, the source of every imported module, and a Python child's reads, under `-E` and `-I`; that a child started with `-S`, a child leaving no manifest, a `socket.connect`, a change of working directory, an audit event the recorder does not list, and a run of git or of any other program make the manifest unstorable; that the same run in two copies at different paths gives the same manifest; and, on Linux, that `strace -f` of the test stage and of the build opens, probes and lists no path inside the repository that the manifests do not hold, and makes no connection.
The record every reuse rests on, built and proven before anything reads it.

- [ ] **2.1** Write `trifecta.record` as COMP_RECORDER states, with the manifest as IF_MANIFEST states.
- [ ] **2.2** Have setup install the `.pth` file, in a virtual environment only, that starts the recorder once in a Python child when `TRIFECTA_RECORD` is set, and test that it imports nothing when the variable is unset and that setup outside a virtual environment writes none; run both CI jobs' setup in a virtual environment.
- [ ] **2.3** Add the tests, declared for REQ_REUSE_SOUND, the `strace` one with the system value `posix`.
- [ ] **2.4** Record in the As built entry what the recorder costs on the test stage, from the profile.
:::

:::{task} Result store and test reuse
:id: TASK_0007_03
:builds: COMP_RESULT_STORE, COMP_PROOF_REUSE
:gate: The tests show that a test module is run again when a file it read changes, a path it probed changes kind, a directory it listed gains an entry, a name its imports looked up appears, a variable it read changes, or the interpreter, an installed distribution or the running package changes, and is reused otherwise; that adding a test module runs that module and reuses the others; that a test child's environment holds no `TRIFECTA_STORE`; that a malformed entry is refused; that a manifest marked unstorable is never stored; that `--fresh` reuses nothing; that a stage the design does not name is never reused; and that the fixture runner gives the same findings for every fixture with `--fresh` and without.
Replaces today's cache, keyed on every file but `docs/`, with one keyed on what each module read.

- [ ] **3.1** Write the result store as COMP_RESULT_STORE states, with `TRIFECTA_STORE` in place of `TRIFECTA_PROOF_CACHE`, and `--fresh` for `trifecta check` and `trifecta fixtures`.
- [ ] **3.2** Run each proof module in a child of its own under the recorder, with `-B` and an empty `pycache_prefix`, store its records with its manifest, and judge stored and fresh records alike; remove `_content_key`, and remove `TRIFECTA_STORE` from every test child's environment.
- [ ] **3.3** Amend DES_0004's COMP_TEST_PROOFS to one child per proof module, with its `os.name` and end-record rules holding per child, reviewed k=2 and stamped.
- [ ] **3.4** Add the tests, declared for REQ_REUSE_SOUND and REQ_REUSE_SCOPED, including the comparison of every fixture's findings with `--fresh` and without.
- [ ] **3.5** Record in the As built entry the profiles before and after, and which test modules are never stored and why.
:::

:::{task} Build reuse
:id: TASK_0007_04
:builds: COMP_BUILD_REUSE
:gate: The tests show that a change to a document, to `docs/conf.py`, or to a module the build imported runs the build again, that a change to the root `requirements.lock` or to a test restores the stored build and a change to a package file builds again, that the check's findings and their locations are the same either way, including a failed build's, in a copy at another path, and that an archive member that is absolute, holds `..` or is a link is refused; the fixture runner gives the same findings for every fixture with `--fresh` and without.
The second stage the profile measured.

- [ ] **4.1** Run the Sphinx build under the recorder through `python -m trifecta.record sphinx`, and store and restore its warnings and output directory as COMP_BUILD_REUSE states.
- [ ] **4.2** Add the tests, declared for REQ_REUSE_SOUND and REQ_REUSE_SCOPED.
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
