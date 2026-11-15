---
status: draft
authors: [claude]
created: 2026-11-13
---
# Fast fixture runs

:::{rfc}
:::

## Summary

The fixture step is nearly all of every CI job, and most of it is 34 fixture copies that
run again test modules whose inputs they did not change. {need}`RFC_0009` makes those
modules storable one refusal at a time; the first lift it built made the step slower.
This RFC asks for two changes that do not wait on the recorder: a copy judges the
control's report for each test module its mutation leaves alone, and the fixtures run as
{need}`shards <TERM_SHARD>` in several jobs behind the two required checks. It also
bounds a job that hangs or is superseded. Every number below is measured from CI's own
profiles; each question records what was measured and what was not.

## Motivation

wyatt, 2026-11-13: "what do we need to do to make this faster? Our runs are terrible,
and I'm not convinced our recent rfc covers it well." And, wyatt, 2026-11-13: "Does your
understanding of the performance situation cover the ci? Because that's taking an hour
plus". Asked for the fix after the measurements below, wyatt, 2026-11-13: "OK, write
it."

Measured from the profiles CI keeps ({need}`REQ_PROFILED`), in two runs of the `check`
workflow: run 43502733400, a push to `main` at `bdbfba7`, before {need}`PLAN_0008`'s task
3, and run 43527987859, the pull request that brought task 3, merged as `1a5a29e`. A
copy-second is one second of one fixture copy's wall time; the runner works on four
copies at once, as many as the machine has processors, so the step's wall time is the
copy-seconds over four.

| | Linux, before task 3 | Linux, with task 3 | Windows, before | Windows, with |
|---|---:|---:|---:|---:|
| Job, minutes | 53 | 62 | 59 | 66 |
| Fixture step, seconds | 3085 | 3558 | 3401 | 3779 |
| Control, seconds | 82 | 114 | 96 | 123 |
| Copy-seconds, all 123 copies | 11,946 | 13,710 | 12,849 | 14,295 |
| Copy-seconds, the 39 copies that run test modules | 9,743 | 11,541 | 9,845 | 11,029 |

The fixture step is 96 to 97 percent of each job; setup and the check before it take
under two minutes together.

Of the 123 copies, 84 change only documents and judge the control's reports, as
{need}`DES_0008` states for a copy whose `tests/` and `src/` equal the base's. The other
39 run their test modules: 5 change a file under `src/`, and 34 leave `src/` alone and
only add files under `tests/`, 32 of them the one file `tests/test_fx.py`. In each of the
39, every module the store never stores runs again, about 250 seconds a copy with four
copies and their modules sharing four processors. With task 3 the never-stored modules
on Linux are `test_adoption`, `test_init`, `test_package`, `test_planning`,
`test_record`, `test_record_nested`, `test_record_trace` and `test_store_reuse`.

Task 3 stored `test_build_reuse`, 8,507 copy-seconds before it and 1,303 with it on
Linux, and added `test_record_nested`, which the store refuses and which holds 8,817;
`test_record` rose from 5,233 to 8,156. The step grew by 473 seconds on Linux and 378 on
Windows. A lift's own tests start recorded children, so each lift adds to the cost it
removes while any module stays unstored.

The profile's Sphinx stage holds 1,959 copy-seconds on Linux before task 3 in 79 builds
of the whole corpus, 12 seconds in the control and 25 on average in a copy. It is what is left once
the modules no longer run in the 34 copies.

Two further costs showed in the same day's runs. In run 43486527920 the Linux check step
ran for 2 hours 39 minutes until it was cancelled: no job has a time limit. And runs
43527245211 and 43527987859, six minutes apart on one branch, both ran; the older one
went on for 39 minutes after the newer began.

The figures for a change not yet built come from a script, not kept in the repository,
that reads a profile's per-copy times and lays the copies out four at a time, longest
first. On the two profiles of run 43527987859 it gives 3,428 and 3,579 seconds for the
fixtures stage that CI measured at 3,434 and 3,588. It cannot see how a copy's time
changes when fewer copies beside it run tests, so each figure is the copies' measured
times rearranged, not a forecast of a run.

## Terms

:::{term} Shard
:id: TERM_SHARD
:synonyms: fixture shard, partition
One of the parts the fixtures are split into for a run, each part run by a CI job of its
own, with every fixture in exactly one part.
:::

## Requirements

:::{req} A copy runs only the modules it can reach
:id: REQ_MODULES_GIVEN
A fixture copy MAY judge the control's report for a test module in place of running it
only when nothing under `src/` differs from the base's in any byte, file or name, and
every entry under `tests/` that the base holds is unchanged in the copy, so the copy's
mutation only adds entries under `tests/`. Such a copy MUST run every module the control
did not report. A copy that changes or removes any entry the base holds under `src/` or
`tests/` MUST run every module. The trees MUST be compared directly, as
{need}`DES_0008` compares them for the whole test stage. A run with `--fresh` MUST take
no report it did not make. No manifest is matched on this path, so
{need}`REQ_REUSE_SOUND` holds for the store and not for it, as DES_0008 already states
for the copies that leave `tests/` and `src/` alone.
:::

:::{req} Shards cover every fixture once
:id: REQ_SHARDS_WHOLE
When the fixtures run as {need}`shards <TERM_SHARD>`, every fixture MUST run in exactly
one shard, the split MUST depend only on the sorted fixture names and the number of
shards, and every shard MUST run the control before its fixtures. The checks the `main`
ruleset requires, `check` and `check-windows`, MUST succeed only when every shard of
their platform succeeded; a shard that failed, was cancelled or was skipped MUST fail
them. The store a push to `main` publishes MUST hold only results of the unmutated tree,
as {need}`DES_0008` states for one job. A run of `trifecta fixtures` with no shard named
MUST run every fixture, as today.
:::

:::{req} A job ends
:id: REQ_JOBS_BOUNDED
Every job of the `check` workflow MUST have a time limit, after which it fails. A new
run for a pull request MUST cancel that pull request's older runs still in progress. A
run for a push to `main` MUST NOT be cancelled by a later one, since it publishes the
store later runs take.
:::

:::{req} The verdicts are the same
:id: REQ_FIXTURE_VERDICTS_SAME
`trifecta fixtures`, the same run split into shards, and `trifecta fixtures --fresh`
MUST give the same result for every fixture, on Linux and on Windows, after each change
this RFC makes.
:::

## Questions

Each question gives what was measured, then what is put to wyatt. None is ruled yet.

:::{question} Does the control's report stand for a module a copy only adds beside?
:id: Q_MODULES_GIVEN
A ruling exists for the whole test stage: a copy whose `tests/` and `src/` equal the
base's judges the control's reports, by comparing the trees, with no manifest (wyatt,
2026-11-11: "Yes, do those first"; {need}`DES_0008`). This question extends it to a
single module in a copy that adds a file under `tests/`.

Measured, by the script the Motivation describes, on run 43527987859: the 34 copies drop
to what they spend outside the control's modules, and the copy-seconds fall from 13,710
to 4,469 on Linux and from 14,295 to 6,424 on Windows; laid out four at a time with the
control, 59.0 to 20.5 minutes and 61.7 to 28.9.

What it trusts: that a file added under `tests/` changes no report of a module that was
already there. {need}`RFC_0009` traced the modules under `strace` and found none reads
a path the fixtures create under `tests/`, and by reading the imports none imports the
names they create, `helpers`, `support_fx`, `test_fx` and `sub`. It fails if a module
lists `tests/`, or imports a name a fixture creates, and its result depends on that.

Not yet measured: whether each module's report in those 34 copies equals the control's.
A fixture passing does not show it, since the runner asks only that the expected finding
is among the copy's findings. A probe branch, `probe/module-reports`, has every copy
that runs its modules keep their reports and compares each with the control's, times
aside, on both platforms; its result is recorded here before this question is put.

Options: **extend the tree rule to a module**, as {need}`REQ_MODULES_GIVEN` states;
**wait for the store**, which gives the same saving only once every module is storable;
or **give the reports and check them on `main`**, where a push run with `--fresh` runs
every module in every copy and fails if a report differs, at the cost of today's hour on
each push.
:::

:::{question} Do the fixtures run in several jobs?
:id: Q_SHARDS
{need}`RFC_0008` left this out because it "changes the jobs the main ruleset requires".
Read from `.github/settings/rulesets.json`: the ruleset requires the contexts `check`
and `check-windows`, by name. A job of each name that needs every shard of its platform
and fails unless all succeeded keeps both contexts, so the ruleset does not change. The
repository is public, read from `gh repo view`, so the jobs cost no runner minutes.
Neither has been run: the gate is read from the configuration, not yet tried.

Measured by the script, the slowest shard with its control, in minutes:

| Shards | Linux today | Linux with {need}`REQ_MODULES_GIVEN` | Windows today | Windows with it |
|---:|---:|---:|---:|---:|
| 1 | 59.0 | 20.5 | 61.7 | 28.9 |
| 2 | 31.1 | 11.9 | 32.6 | 16.2 |
| 4 | 16.9 | 8.8 | 17.8 | 9.8 |
| 6 | 12.3 | 8.8 | 12.7 | 9.6 |

Past four shards little is gained with REQ_MODULES_GIVEN: the floor is the control and
the five copies that change `src/`, 365 to 452 seconds each. Every shard runs the setup
and the control again, and the control took 114 seconds on Linux and 123 on Windows.

Put to wyatt: whether RFC_0008's scope cut is lifted, and how many shards.
:::

:::{question} What becomes of PLAN_0008's remaining tasks?
:id: Q_PLAN_0008_REST
Tasks 1 to 3 of {need}`PLAN_0008` are built; 4 to 7 are not. Measured on run
43527987859: with {need}`REQ_MODULES_GIVEN`, the never-stored modules run in the fixture
step only in the control and in the five copies that change `src/`, 1,773 copy-seconds
on Linux and 1,854 on Windows, and {need}`RFC_0009`'s own table counts those five as
copies that cannot reuse them. What tasks 4 to 7 would then save in CI is the control's
test stage in a pull request's run, which could take `main`'s results: about 100 of its
114 seconds on Linux. A local `trifecta check` without `--fresh` gains the same. Without
REQ_MODULES_GIVEN, RFC_0009's bounds stand as its table gives them.

This question follows {need}`Q_MODULES_GIVEN` and is put only after it is ruled.
:::

:::{question} Is the cost of the tests themselves in scope?
:id: Q_TEST_COST
Neither {need}`RFC_0008` nor {need}`RFC_0009` asks that a test cost less; both only
reuse its result. Measured in run 43502733400 on Linux, five tests hold most of the
check's 68-second test stage: one of `test_build_reuse`, 22.6 seconds; two of
`test_init` that run init and a whole check, 30.7 together; `test_record_trace`'s traced
build, 28.9; `test_adoption`'s guide, 27.6; and one of `test_record`, 10.0. The modules
run side by side, so the stage is shorter than their sum. They are paid in the check, in
the control of every shard, and in every copy that changes `src/`; the control rose from
82 to 114 seconds with task 3. Why each takes what it takes has not been read.

Put to wyatt: whether a look at those tests belongs to this RFC or to a later one.
:::

## Out of scope

A time budget or target: none exists (wyatt, 2026-11-10: "No number yet"), and any is
only reported (wyatt, 2026-11-10: "Report only"). Any change to
{need}`REQ_REUSE_SOUND` for the store, which {need}`RFC_0009` rules out;
{need}`REQ_MODULES_GIVEN` is a path beside the store, as {need}`DES_0008` already holds
one. Sphinx's own incremental build and the number of fixtures, as {need}`RFC_0008` and
RFC_0009 leave them. An adopting repository's CI. The release workflows, which were not
measured.

## Review
