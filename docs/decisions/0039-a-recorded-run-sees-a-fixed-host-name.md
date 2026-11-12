---
status: accepted
date: 2026-11-11
decision-makers: [wyatt]
informed: [claude]
---
# A recorded run sees a fixed host name

:::{decision}
:chooses: OPT_0039_BLANK
:resolves: Q_UNAME
:driven_by: REQ_HOST_READS
:::

## Context and Problem Statement

On Linux, `os.uname` raises no audit event, so a run can read the host name
unseen. Under Python 3.12, which CI runs, `jsonschema` imports `uuid`, whose import calls
`platform.system()` and so `os.uname`, in every module that imports `trifecta.check`.

## Decision Drivers

- A host read is never stored unseen
- No module loses its reuse to a read it does not use

## Considered Options

:::{opt} Blank the host name
:id: OPT_0039_BLANK
`os.uname`, `posix.uname` and `platform`'s cache give a fixed host name inside a
recorded run, and the other fields are recorded. Good, because it keeps every reuse. Bad,
because the code under test sees a host name that is not the machine's.
:::

:::{opt} Record the host name as a hash
:id: OPT_0039_HASH
Bad, because a new input kind, and results cached from main miss on another
runner's host name.
:::

:::{opt} Refuse every call
:id: OPT_0039_REFUSE
Bad, because `test_profile`, `test_init`, `test_package`, `test_planning` and
`test_store_reuse` stay fresh on Linux.
:::

## Decision Outcome

Chosen option: {need}`OPT_0039_BLANK`, because wyatt, 2026-11-11: "just make recommendations, and ask using ask user tool"; he chose "Blank the host name", after first choosing "Refuse every call,
in PLAN_0007" on a recommendation that put its cost at `test_profile` alone.

## Consequences

- Good, because the gap closes in PLAN_0007, the timing the chosen option named.
- Bad, because every other host read, `socket.gethostname`, `/etc/hostname`, `HOSTNAME`, stays refused or recorded as before, and `uuid.getnode()`'s native read falls under {need}`DES_0008`'s native-code risk.
- Bad, because on Windows `toolchain.bin_vale` reads the host name through WMI; derived by {need}`DES_0009`, not ruled, it tests `os.name` instead.
