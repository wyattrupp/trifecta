---
status: accepted
date: 2026-11-10
decision-makers: [claude]
informed: [wyatt]
---
# A stage result is keyed by the inputs it recorded

:::{decision}
:chooses: OPT_0028_RECORDED
:resolves: Q_REUSE_KEY
:driven_by: REQ_REUSE_SOUND
:::

## Context and Problem Statement

The fixture runner's cache keys the test results on every file but `docs/`, on the claim
that no test reads `docs/`; nothing checks that claim, and the key changes whenever any
other file does, so the 50 fixtures that add a test or change a lock run every test
again. A key has to cover everything a result depends on, or a changed input passes
unchecked, and should cover nothing more, or nothing is reused.

## Decision Drivers

- No changed input passes unchecked
- A machine, not an author, says what a stage read
- A fixture that changes one file reruns only what reads that file

## Considered Options

:::{opt} Record what each run reads, and key on that
:id: OPT_0028_RECORDED
While a stage or a test module runs, a recorder in its process notes every file it opens,
path it probes, directory it lists and environment variable it reads, through Python's
audit hooks and wrappers on the probing functions and `os.environ`, and marks the run
unstorable on any event it does not know; a Python child the run
starts records itself the same way and hands its manifest back. Good, because the key is
what the run read, so it is neither too wide nor a claim. Bad, because the recorder sees
only Python; a run that starts any other program, or a child that hands back no manifest,
is not stored, and the recorder has its own overhead.
:::

:::{opt} Declare each stage's inputs by hand
:id: OPT_0028_DECLARED
A manifest file names the paths each stage and test module depends on. Good, because it
is simple and costs nothing at run time. Bad, because it is a claim like today's, which a
new read can make false without any check failing.
:::

:::{opt} Key on every file in the repository
:id: OPT_0028_WHOLE_TREE
Good, because it cannot miss an input in the repository. Bad, because every fixture
changes a file, so nothing is ever reused across fixtures, which is slower than today.
:::

## Decision Outcome

Chosen option: {need}`OPT_0028_RECORDED`, because it is the only option whose key is
both checked and narrow. A run whose reads are not all recorded is simply run every
time, so the recorder's blind spots cost speed, not soundness.

## Consequences

- Good, because today's unchecked claim about `docs/` goes: a test that starts reading
  `docs/` puts those files in its own manifest.
- Good, because a manifest is a record a person can read to see why a result was or was
  not reused, which the profile reports.
- Bad, because a test that runs Vale, git or another program, inside or outside the
  repository, is run every time; the profile shows what that costs.
- Bad, because a read by native code that bypasses the audited calls, which several of
  the lock's dependencies hold, would be missed; a test traces the system calls of each
  recorded stage on Linux and reports a read the manifest lacks, and the design's risks
  state what that leaves.
