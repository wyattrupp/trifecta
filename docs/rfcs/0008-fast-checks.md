---
status: accepted
authors: [claude]
created: 2026-11-10
---
# Fast checks

:::{rfc}
:::

## Summary

`trifecta check` and `trifecta fixtures` measure where their time goes and stop redoing
work whose inputs have not changed. A {need}`profile <TERM_PROFILE>` records the wall time
of every stage of the check, and of every fixture and its stages in the fixture runner,
in a file beside the build, and changes no finding. A stage result is reused only when
its {need}`manifest <TERM_MANIFEST>`, the record of every input the run that made it
read, still matches; a read the recorder cannot see makes the result one that is never
reused.

## Motivation

wyatt, 2026-11-10: "we need to get our hands around manifests and profiling for this.
that CI is ridiculously slow. chip a session to address that as a new design". On the
scope, wyatt, 2026-11-10: "and not just CI... the whole thing", so a local `trifecta
check` and `trifecta fixtures` are in scope beside CI.

Measured on 2026-11-10. In thirteen CI runs that day, run 42744849674 to run
42908460801 of the `check` workflow, the Linux
job took 156 to 586 seconds and the Windows job 370 to 1116; the fixture step was 88 to
95 percent of every job, setup 6 to 31 seconds and the check 4 to 26. The fixture step on
Linux grew from 142 seconds to between 323 and 554 once the check started running the
tests under `tests/`. A local `trifecta check --base main` on Windows took 46 seconds:
the tests 31.6, the Sphinx build 9.2, the history check 2.9, the lint view and Vale 2.0,
every other stage under 0.2. The tests are dominated by two in `tests/test_init.py` that
run init and a nested check, 8.9 and 4.4 seconds, and a wheel build in
`tests/test_package.py`, 2.7. Of the negative fixtures, the 73 that change only files
under `docs/` reuse the control's test results through the fixture runner's cache, which
is keyed on every file but `docs/`; the other 50 add or change a test, change one of the two locks, the setup script,
`.gitattributes` or `.gitignore`, or add a file under `bin/`, miss that cache, and run every test again, though most tests read
none of what they change. Every fixture runs a full Sphinx build, including the 50 whose
change is outside `docs/`. Run alone on the same machine, one fixture that changes a
document took 14 seconds, one that changes a lock 45, and one that adds a test 48; the
whole fixture run, 24 at a time, took 551 seconds, of which the 50 fixtures outside
`docs/` held 68 percent of the summed fixture time. The pull request that brought this
RFC holds the per-fixture numbers.

Neither command says where its time goes: those numbers came from scripts written for
this RFC. And the one cache that exists rests on a claim nothing checks, that no test
reads `docs/`.

## Terms

:::{term} Profile
:id: TERM_PROFILE
:synonyms: timing report
The wall time of each stage of one run of the check or the fixture runner, written as a
file, with whether each reusable stage's result was reused.
:::

:::{term} Manifest
:id: TERM_MANIFEST
:synonyms: dependency record
For one run of one stage, or of one test module, every input it read, as recorded while
it ran: each file with its content hash, each path it probed with what it found there, a
file, a directory, a link or nothing, each directory it listed with its entries, each environment variable it read with its value, and the system,
interpreter and installed distributions it ran with.
:::

:::{term} Reuse
:id: TERM_REUSE
:synonyms: cache hit
Taking a stage's findings and outputs from an earlier run in place of running it.
:::

## Requirements

:::{req} Runs are profiled
:id: REQ_PROFILED
`trifecta check` and `trifecta fixtures` MUST each be able to write a profile: for the
check, the wall time of every stage in the order it ran; for the fixture runner, the wall
time of the copy, of the control, and of each fixture's copy, its check and each stage of
that check, with whether each reusable stage was reused and why not when it was not. The
profile MUST NOT change any finding, the bytes of standard output or the exit status. A
time budget MUST only be reported, never fail a run (wyatt, 2026-11-10: "Report only"),
and none exists until wyatt sets one (wyatt, 2026-11-10, on a target for CI and for local
runs: "No number yet").
:::

:::{req} A reused result had the same inputs
:id: REQ_REUSE_SOUND
A stage result MUST be reused only when its manifest matches the run it would replace:
every file it read has the same content, every path it probed holds the same kind of
thing, every directory it listed has the same entries, every environment variable it read has the same
value or is still unset, and the system, interpreter, installed distributions and the
code of the package that runs the stage are the same. A run that reads anything the
recorder cannot see, such as a child process that delivers no manifest of its own or
a network connection, MUST NOT be stored for reuse, and the recorder MUST start before
any code of the run. A reused result MUST give the same findings, with the same locations, as
running the stage would.
:::

:::{req} The reused stages are named
:id: REQ_REUSE_SCOPED
Only the stages the design names as reusable MAY be reused; every other stage, and every
stage that reads git history or the base ref, MUST run on every check. A run with
`--fresh` MUST reuse nothing; it MAY store what it ran.
:::

## Questions

:::{question} What keys a reused result?
:id: Q_REUSE_KEY
:::

:::{question} Where does the profile go?
:id: Q_PROFILE_PLACE
:::

:::{question} Which stages may be reused?
:id: Q_REUSE_STAGES
:::

:::{question} What does CI keep between runs?
:id: Q_CI_CACHE
:::

## Out of scope

A time budget or target, which is wyatt's ruling and has not been made. Splitting the
fixtures across more CI jobs, which changes the jobs the main ruleset requires, a
repository setting that needs wyatt's yes; the profile is what would show it is needed.
Sphinx's own incremental build, since a change to one document changes the tables and
links of others through the need graph. A test whose result depends on the clock or on
chance: the check takes a passing test as a proof, so it already assumes a test gives the
same result on the same inputs. A faster Sphinx, Vale or interpreter.

## Review

:::{review} Correctness; security
:id: REV_RFC_0008_1
:k: 2
:date: 2026-11-10
:digest: 22f74bc23c98a2b9de17fc8f668d2a4af30e41b5a0bc517060ab701f7fe2a82b
The fast-checks set before its first commit: this RFC, {need}`DEC_0028` to
{need}`DEC_0031`, {need}`DES_0008` and {need}`PLAN_0007`, two rounds, one reviewer per
lens, each checking claims against the code and against Python 3.12 on Windows. Folded
in: the recorder fails closed on any audit event it does not list; it wraps the
`os.path` probes, which on Windows are C functions that skip a wrapped `os.stat`, records
every probe and listing entry with its kind, reads `shutil.copy2` sources through the
`CopyFile2` event, records import lookups by name, runs every recorded process with `-B`
and an empty `pycache_prefix`, names each child's directory by a token, since a virtual
environment's launcher changes the process ID, never records its own variables, and is
checked against `strace` on Linux for reads and connections by native code, which
several locked dependencies hold; the store's identity holds the test module and its
left-out tests, not the command line, plus a hash of the running package, and its
variable is removed from test children; a stored build keeps its error stream and exit
status with the root replaced, and is restored with member checks; DES_0004's single
test child is amended by a plan step; the measured share of the fixture step is 88 to 95
percent. From the security pass: CI restores no results through the cache action, since
a pull request's earlier commit can save into the scope its final commit restores; main's
push runs fill a store from empty and publish it, and pull requests fetch it by run ID;
setup checks the Vale archive's hash before every extraction and `bin/` is never cached;
the `.pth` file goes only into a virtual environment; the risks state that the fixture
runner's verdicts in a pull request rest on main's store.
:::
