---
status: implemented
authors: [claude]
---
# Fast checks

:::{design}
:::

## Overview

Two pillars. Profiling: the check times each of its stages and the fixture runner times
each copy, control and fixture, and both write the times as JSON under
`docs/_build/profile/`, which CI uploads and summarizes. Manifests: a recorder inside each
test module's child and inside the Sphinx build notes every input the run reads, failing
closed on anything it cannot follow, and a result store keeps the run's results under
that manifest; a later run whose inputs all match takes the stored results in place of
running. Every other stage runs every time, and so does the judging of test results. In
CI, setup's downloads are cached by hash, push runs on main run the fixtures from an empty
store and publish the store they wrote, and pull requests fetch that store from main's run.

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

:::{component} Profiler
:id: COMP_PROFILER
:spec: src/trifecta/profiler.py#class Profiler
:satisfies: REQ_PROFILED
:constrained_by: DEC_0029
:provides: IF_PROFILE
A timer around each stage of `check.main`, in the order the stages run, using
`time.perf_counter`, and around the fixture runner's base copy, its control, and each
fixture's copy, mutation and check. The check writes `docs/_build/profile/check.json`, or
the path `--profile` names; the fixture runner reads each copy's own `check.json` after
its check and writes `docs/_build/profile/fixtures.json`, or the path its `--profile`
names, with the base copy, the control, every fixture with its stages, and the run's
total. Each record of a reusable stage says whether it was reused and, when not, the kind
of the first input that differed, as a path or a variable name, never a variable's
value, or why the run could not be stored. Nothing is written to standard output, and a
profile that cannot be written is a line on standard error, not a finding and not a
change to the exit status. `docs/_build/profile/` is kept out of the clean before the
Sphinx build. `trifecta profile PATH` prints the stages, or the fixtures, by time as a
Markdown table, which CI appends to the job summary. No budget is compared, since none
exists (wyatt, 2026-11-10: "No number yet"); where one is set it is printed beside the
time it bounds and changes no exit status (wyatt, 2026-11-10: "Report only").
:::

:::{component} Recorder
:id: COMP_RECORDER
:spec: src/trifecta/record.py#def start
:satisfies: REQ_REUSE_SOUND
:constrained_by: DEC_0028
:provides: IF_MANIFEST
A module, `trifecta.record`, started by the boot line of the process it records, before
any module of the run is imported, and installed once per process. It fails closed: any
audit event not on its list of handled or known-harmless events marks the manifest
unstorable, and so does a change of working directory.

Reads: an `open` for reading, and the source of a `shutil.copyfile` or the Windows
`_winapi.CopyFile2` event, is a file input, hashed only when it is a regular file;
`/dev/null` and `/dev/urandom` are held by their kind, `device`, never read, and a read of
any other device, a pipe or a socket, which another process can feed, refuses the run. A
link the run makes
may reach only what it made, a directory it created or a file it wrote, its links
resolved; making one that reaches beyond is refused, since a read under a directory the run
made, which is no input, would reach through it a file no key holds. Probes: it wraps `os.stat`, `os.lstat`,
`os.access`, `os.readlink`, and `os.path.exists`, `isfile`, `isdir` and `islink`, which
on Windows are C functions that call no wrapped `os.stat`, and records every probed path
with its kind: file, directory, link, fifo, device, socket or absent. Listings: `os.listdir` and `os.scandir`
record each entry with its kind. Imports: the import system's own lookups are recorded as
the presence or absence of the names it looked for, not as whole listings. Every recorded process, the
Sphinx build's included, runs with `-B` and with `pycache_prefix` set to an empty
directory, which its recorder makes and sets as it starts, so no `.pyc` in the tree is read or written; at the end the recorder adds the source
of every module in `sys.modules`. Environment: `os.environ` and `os.environb` become
mappings that record each key asked for, and every key when iterated or copied, each with
a hash of its value, never the value, since a store CI publishes is public, and still set
the process environment as before; a variable the run set is its own. Iterating or
copying the mapping also records the digest of the names the process started with, so a
variable that appears or vanishes runs the run again. The locale's
variables, which the C library reads where the mapping cannot see, are recorded whether
set or not. The recorder's own
variables, `TRIFECTA_RECORD`, `TRIFECTA_RECORD_PARENT` and `TRIFECTA_STORE`, are never recorded. A file, listing or probe under a
directory the run or one of its children created is not an input, and neither is that
directory as an entry of a listing; the run's own control
files, such as the test child's channel and plan, are not either.

Children: a Python child the run starts with `sys.executable` records itself. The
recorder gives each child a fresh directory, named in `TRIFECTA_RECORD`, since on Windows
a virtual environment's `python.exe` is a launcher whose process ID is not the child's;
a `.pth` file that setup installs in a virtual environment starts the recorder when the
variable is set and imports nothing when it is not, and holds under `-E`, `-I` and `-s`,
since `site` still runs. Outside a virtual environment, where `sys.prefix` is
`sys.base_prefix`, setup installs no `.pth` file and says so on standard error, and a
Python child there leaves no manifest. A child started with `-S`, a child that leaves no manifest in its
directory, a `socket.connect`, and any `os.system`, exec, spawn, fork or `startfile`, or a
`subprocess.Popen` of any other program, mark the manifest unstorable. Paths inside the
repository are recorded relative to its root, and paths and values holding the root's
absolute path have it replaced by a placeholder, so a fixture copy at another path
matches. Files under the interpreter's prefixes are left to the environment key; any
other file read outside the repository is hashed in `outside`.

Native code: a module of the lock built from C or Rust, such as `jsonschema_rs`,
`minijinja`, `rpds`, PyYAML's `_yaml`, `markupsafe` and `charset_normalizer`, can open a
file without any audited call. A test on Linux runs each recorded stage under
`strace -f`, in the form {need}`DES_0009` lets through, and reports every path inside the
repository the system calls opened, probed or listed that the manifest does not hold, and
any connection.
:::

:::{component} Result store
:id: COMP_RESULT_STORE
:spec: src/trifecta/store.py#class Store
:satisfies: REQ_REUSE_SOUND, REQ_REUSE_SCOPED
:constrained_by: DEC_0028, DEC_0030
A directory of entries, `docs/_build/cache/` by default, kept out of the clean before the
Sphinx build, or the directory `TRIFECTA_STORE` names, which replaces
`TRIFECTA_PROOF_CACHE`. An entry is filed under its identity: the stage; for a test
module, its name and the tests left out of it; the environment key, made of `os.name`,
`sys.version`, `sys.executable` with the root replaced, `RUNNER_OS`, the hashes of the
recorder's two `.pth` files, the test's and the parent's, the entries of the site directories, and the name, version and
`RECORD` hash of every installed distribution; and a hash of every file of the package that runs the stage, which an
editable install's `RECORD` does not cover. Under one identity the store keeps the
manifests stored with their results, newest first, and a lookup takes the first whose
every file hash, probe, listing, import lookup, environment value and file outside the
repository matches the current tree and environment; when the store is written for publishing, entries whose identity no longer
matches the running package are dropped. A miss and an unstorable manifest run the
stage; `--fresh` runs every stage and reuses nothing, and stores what it ran. Entries
are JSON, written to a temporary file and moved into place, so copies running at once
never read half an entry, and are checked against their schema and bounded in size and
number when read, since a fetched store is data from another run; a store reached
through a link, or one holding a file git tracks, is not used. A result is stored with
the root's path replaced, and only from a child that reported its end. The store holds results, never verdicts: what a
stored result means is decided by the running package every time. `TRIFECTA_STORE` is
removed from the environment of every test child, so a test that runs the check itself
runs it fresh, as `TRIFECTA_PROOF_CACHE` is removed today.
:::

:::{component} Proof reuse
:id: COMP_PROOF_REUSE
:spec: src/trifecta/proofs.py#def run_modules
:satisfies: REQ_REUSE_SCOPED
:constrained_by: DEC_0030
The test stage runs each proof module it chose in a child of its own, under the recorder,
the children side by side, as many at once as the machine has processors, and stores the
module's records and its manifest; reading the
declarations, matching results to them and judging them run every time, on the stored
records or the fresh ones alike, against every module's name. A module is looked up by
its own identity, so a fixture that adds a test module runs that module, and reuses every
other whose manifest holds neither the new file nor a lookup the new name answers.
`_content_key` and its claim that no test reads `docs/` go. {need}`DES_0004`'s
COMP_TEST_PROOFS, which states one child for every module, is amended to one child per
module, with its rules on the child's `os.name` and its end record holding per child.
One path skips the store: the fixture runner's control keeps what its modules reported,
and a copy whose fixture neither expects `REQ_PROVEN_BY_TEST` nor leaves its `tests/` or
`src/` different from the base's in any byte, file or name judges those reports in place
of running its modules (wyatt, 2026-11-11: "Yes, do those first"). No manifest is matched
there: a copy whose mutation changes only what a test reads elsewhere, such as `docs/` or
the lock, is judged on the control's reports, so {need}`REQ_REUSE_SOUND` holds for the
store and not for this path. A run with `--fresh` takes nothing from it.
:::

:::{component} Build reuse
:id: COMP_BUILD_REUSE
:spec: src/trifecta/build.py#def run_build
:satisfies: REQ_REUSE_SCOPED
:constrained_by: DEC_0030
The Sphinx stage runs `python -m trifecta.record sphinx` with the same options, which
runs Sphinx in the process the recorder already watches, from `docs/`, since Sphinx
changes into the configuration's directory to read `conf.py`. It runs after the clean,
which empties `docs/_build` of all but the profiles and the store and leaves the
directory in place, so the build sees the same tree whether a run before it left one or
not, and nothing under the build directory is an input. It stores the build's standard
error and exit status, with the root replaced by a placeholder, and the output directory
`docs/_build/html` as one archive, without `.doctrees`, within the store's bound on an
entry. A match restores the directory, refusing the whole archive, before writing any of
it, when any member is absolute, holds `..`, is a link, names a Windows device or
repeats another's name but for case, or it would unpack past a bound, and then builds
instead; it unpacks beside the output directory and moves it into place whole. A build
whose error stream already holds a placeholder is not stored. The build runs with `-P`,
so nothing in `docs/` shadows a module; it puts the root back into the stored error stream before
`from_sphinx` reads it, so the findings and their locations are those a fresh build gives. A fixture that changes no file the build read,
such as one that edits the root `requirements.lock` or a test, restores the control's
build; a change to any file of the package, its setup script and lock included, changes
the identity and builds again.
:::

:::{component} CI cache
:id: COMP_CI_CACHE
:constrained_by: DEC_0031
:spec: .github/workflows/check.yml#name: Store
In both jobs of the check workflow: setup runs in a virtual environment, so the recorder's
`.pth` file has somewhere to go. `actions/cache/restore` and `actions/cache/save`, pinned
by SHA, keep pip's downloaded archives, under `PIP_CACHE_DIR`, and setup's Vale archive,
which setup keeps under `TRIFECTA_DOWNLOADS` when that names a directory, under a key
holding `runner.os` and the hash of both locks and the setup script; `bin/` is never
cached. Setup checks the Vale archive's SHA-256 before every extraction, a kept one as a
downloaded one, and downloads again in place of a kept archive with another hash; pip
checks every archive against the lock's hashes. The check step runs with `--fresh`, in
the Makefile and the Windows job alike. The fixture runner runs the control with the store
`TRIFECTA_STORE` names, when set, and the copies with a copy of it taken after the
control, so the results of mutated trees never prune the unmutated tree's from the store
CI keeps. In push runs on main, the fixture step starts from an empty store named in
`TRIFECTA_STORE`, so every result in it was run by that commit, and uploads the store,
which holds the control's results, as an artifact named for `runner.os`. In pull request
runs, a step finds the latest successful run of `.github/workflows/check.yml` whose event
is `push` and whose branch is main in this repository, takes it only when its commit is on
main's first-parent chain, since a tag named main gives the same branch and a merged
branch's commits are on main without main ever having been at them, and downloads that
run's store artifact by its run ID, which needs `actions: read`; the fixture step runs
with `TRIFECTA_STORE` set to it. Where there is no such run, its commit is not on that
chain or it has no artifact, the store starts empty. No result a pull request run writes
is ever read by another run. A last step that always runs uploads `docs/_build/profile/`
and appends `trifecta profile` tables to the job summary.
:::

## Interfaces

:::{interface} Profile
:id: IF_PROFILE
:spec: src/trifecta/profiler.py#def data
:constrained_by: DEC_0029
A JSON object with `version: 1`, `command` (`check` or `fixtures`), `total` in seconds,
and `stages`, an array in run order of objects with `name`, `seconds`, and for a reusable
stage `reused` and `why`, and for a test module the store did not store for a reason it
names `reasons`, its manifest's or, for a storable run the check did not store, the
check's own, each with `process` and `why`, and `tests`, each test's `name`
(`Class.method`) and `seconds` as its proof child reported them on its channel; a module
with no reason named is not listed; for the fixture runner also `base`,
`control` and `fixtures`, each fixture with `name`, `seconds`, `copy_seconds`, `ok` and
its check's `stages`. Times are wall-clock seconds rounded to milliseconds. `why` and a
reason MUST NOT hold the value of an environment variable (wyatt, 2026-11-13: "Never put
values in (Recommended)"). The profile MUST NOT be read by
any rule: it is a report.
:::

:::{interface} Manifest
:id: IF_MANIFEST
:spec: src/trifecta/record.py#def valid
:constrained_by: DEC_0028, DEC_0039
A JSON object with `version: 1`, `storable` and, when false, `why` and `reasons`; `files`,
mapping each path read to its SHA-256; `probes`, mapping each path probed to its kind,
`file`, `directory`, `link`, `fifo`, `device`, `socket` or `absent`, or, for a link
{need}`DES_0009` holds as the interpreter's ({need}`DEC_0045`), `link:` followed by the
link's target as it reads, which a lookup reads again; `listings`, mapping each directory
listed to its sorted entries, each with its kind; `lookups`, the import system's names found or not found;
`environment`, mapping each variable read to the SHA-256 of its value, with the root's
path replaced, or null when it is unset, and, under the key `=names`, which no
variable's name can be, when the run read the whole environment, the SHA-256 of the
names of the variables the process started with, sorted, joined by NUL and less the
recorder's own, which a lookup takes again from its environment; when a Python child's
manifest holds the key, its parent's recorder records its own digest under it in place of
the child's, since the child's environment is what its parent gave it; `outside`, mapping
each file read outside the repository and the interpreter's prefixes to its SHA-256; and
`uname`, mapping each field of `os.uname` other than the host name (`sysname`,
`release`, `version`, `machine`) to the SHA-256 of its value, taken when the run starts,
which a lookup takes again to match. Where `os.uname` exists all four are required, and
inside a recorded run `os.uname`, `posix.uname` and `platform` give a fixed host name,
`localhost`, the design's value, not ruled ({need}`DEC_0039` rules a fixed name); where it
does not, `uname` is empty and the first fill of `platform`'s cache, which
`platform.system()` and the others also make, reads the name through
`socket.gethostname`, which refuses the run. No manifest holds a host name's value: a read of one through a
file or variable (`HOSTNAME`, `COMPUTERNAME`, `/etc/hostname`,
`/proc/sys/kernel/hostname`) is recorded as its SHA-256, as {need}`REQ_HOST_READS` allows.
Paths inside the repository are relative to its root with forward slashes, as
REQ_PORTABLE_FINDINGS writes locations.

`programs` maps each program a run started other than the interpreter, which only a known
program started on its terms can be ({need}`DES_0009`'s COMP_KNOWN_PROGRAMS), and each
program that the command `strace` traced started, with its `#!` interpreter, followed
again, and its ELF interpreter, to the SHA-256 of the file its path reaches, links
followed, which a lookup takes again to match. A key inside the repository is relative to
its root, as the other sections' are, and any other is absolute. A program under a
directory the run made, a file it wrote, a directory a recorder prepared or one the run's
configuration leaves out is not held, unless its path lands beyond them through a link,
where it is held by where it lands; one under the interpreter's prefixes is held.

`reasons` lists every distinct reason the run was refused: the run's own in the order
raised, then each Python child's in the order the children started; `why` is the first,
and "two processes recorded into one place", when raised, leads the list. It holds 1 to 64
reasons, and `reasons[0].why` equals `why`. Each reason is an object with exactly
`process` and `why`: `why` is non-empty, holds no NUL and has at most 4096 characters;
`process` is null for the run's own process, or, non-empty, with no NUL and at most 4096
characters, names a Python child by its executable's base name less `.exe`, with `-m` and
the module when it was started so and nothing else of its command, a child's own child
joined to it by ` > `, cleaned as a reason is. A refused run notes reasons only, never
inputs, and still records its Python children, so their reasons are named.

A reason is built from names, paths and module names only, never a variable's value
(wyatt, 2026-11-13: "Never put values in (Recommended)"). A path a reason names is cut
before the reason is formatted, and the whole reason is cleaned again: the root, the
interpreter's prefixes, the home directory (from `HOME` or `USERPROFILE`) and the
temporary directory (from `TMPDIR`, `TEMP` or `TMP`, `tempfile.tempdir` when the run has
set it, and on POSIX `/tmp` and `/var/tmp`) are replaced by `<root>`, `<prefix>`,
`<base_prefix>`, `<home>` and `<tmp>` where no other path character follows, each place's
trailing separators ignored, the longest first, a drive's root never, and where the prefix
and the base prefix are one path, by `<prefix>`; any other absolute path is cut to its
base name. As a backstop, applied to a reason's `why` and not to its `process`, a
variable's value of four characters or more, stripped, that is not a bare word such as
`true` or `none`, is replaced where it stands as a whole word by `<env:NAME>`. The
64-reason bound, the placeholders, the names, the ` > ` join, the backstop's four
characters and its whole-word match, and the recording of a refused run's children are the
design's, not ruled.
:::

## Risks

The recorder sees what Python does through the audited calls and the wrapped functions,
and fails closed on the events it does not know. A read by native code that opens a file
itself is missed in a run on Windows or macOS; the `strace` test catches it on Linux,
where a dependency that starts doing so fails the test, and a dependency added to the lock
is covered by the same test. Native code that reads the host's identity without an
audited call or a file open, such as the MAC address `uuid.getnode()` reads through
`_uuid`, is missed on every system. A fresh `posix` module, made by `import` or through
`_imp.create_builtin`, is refused, and so is a new interpreter, which has none of the
recorder's hooks or wrappers; reaching the original `uname` through other means stays out
of scope. A test whose result depends on the clock or on chance can be
reused with a result a fresh run would not give; the check already treats one passing run
as a proof, so reuse adds no new assumption, only a longer life for the same one.

The store in `docs/_build/cache/` is trusted: anyone who can write it can make a local
check pass, as anyone who can edit the package can. In CI, pull requests read only the
store a push run on main wrote from an empty start, by merged code, fetched by run ID rather
than by a cache key a pull request could also write; a result that run stored wrongly,
through a gap in the recorder, can hide a fixture failure in pull requests until an input
it recorded changes, and the top-level check, which runs fresh, does not guard the
fixture runner's own verdicts. Only the push-on-main job of the check workflow publishes
a store; no release workflow reads one. Adding `actions: read` to the check workflow lets
its jobs read the repository's workflow runs and artifacts, which are public here anyway.

A test that starts git, Vale or any program other than the interpreter is never stored,
so it runs every time; the profile shows its cost. The wrapped `os.environ` records every
variable on iteration, so a module that copies the environment is reused only where the
whole environment is the same, which in CI is within a run and not across runs. In an
adopting repository, setup installs the `.pth` file in its virtual environment, and the
check uses `docs/_build/cache/` and a child per test module, but its CI workflow, which
init writes, gets no store or download cache until a later change offers one.

## Review

:::{review} Correctness; security
:id: REV_DES_0008_1
:k: 2
:date: 2026-11-10
:digest: 71ca9dff4ba9be98ffca9d08d9b74a0ba97103bd02bab781619e5e8f54565546
The review recorded as {need}`REV_RFC_0008_1` covered this document.
:::

:::{review} Correctness; security
:id: REV_DES_0008_2
:k: 2
:date: 2026-11-10
:digest: 9c7ef46b3795c904e9c6317c67fdc071081fa9f792fe248f14aa6205a3c3b93a
{need}`PLAN_0007` task 2: the environment a manifest records is a SHA-256 of each value,
with the root's path replaced, never the value, since a store CI publishes is public.
Two rounds, one reviewer per lens, with the recorder that builds it.
:::

:::{review} Correctness; security
:id: REV_DES_0008_3
:k: 2
:date: 2026-11-10
:digest: 28317eef4f52b3be08d821a40b1a3fd1a8260c39924d465df36274a636f9cdec
{need}`PLAN_0007` task 3: a lookup also matches import lookups and files outside the
repository; the environment key holds the site directories' entries; entries are bounded,
a store reached through a link or holding a tracked file is not used, and a result is
stored with the root replaced, only from a child that reported its end. Two rounds, one
reviewer per lens, with the code that builds it.
:::

:::{review} Correctness; security
:id: REV_DES_0008_4
:k: 2
:date: 2026-11-11
:digest: 63f7d7ba6d9f3cd6ebe19260ecbff7a5c83ac9a2a72d801e944d6a4594891ab3
{need}`PLAN_0007` task 4: the build runs from `docs/` with `-P` after a clean that leaves
`docs/_build` in place; a restore refuses device names and names repeated but for case,
unpacks beside the output and moves it into place; a directory the run made is no entry
of a listing, and the locale's variables are recorded set or not. One round, one reviewer
per lens, with the code that builds it.
:::

:::{review} Correctness; security
:id: REV_DES_0008_5
:k: 2
:date: 2026-11-11
:digest: deeb9951fe9160f3cf4d5918eaf5d39918c4ba909d06056c3a1123cc99b974bd
COMP_PROOF_REUSE: the modules run side by side, and the fixture runner's path that
takes the control's reports is named, with what it does not match. Three rounds,
one reviewer per lens, with the code that builds it.
:::

:::{review} Correctness; security
:id: REV_DES_0008_6
:k: 2
:date: 2026-11-12
:digest: 1c0deb94234679f4e2f80d21dc7de135d6b7d8ea0afd21366070ce8e27c059b7
{need}`PLAN_0007` task 5: setup keeps the Vale archive under `TRIFECTA_DOWNLOADS` and
checks it as a download; the fixture copies share a copy of the named store, so CI keeps
the control's results; a pull request takes main's store only from a push run whose
commit is on main's first-parent chain. Three rounds, one reviewer per lens, with the
workflow and the code that builds it, the last after the rebase onto the control's kept
reports.
:::

:::{review} Correctness; security
:id: REV_DES_0008_7
:k: 2
:date: 2026-11-13
:digest: 4e440f99c7f34a3e8a1750ecd74c8da60bf4ae4f6c2b0ee13022dccf4a1052b0
Three rounds and a final check, one reviewer per lens, on IF_MANIFEST's `uname`
section and the Risks that {need}`PLAN_0008`'s task 1 added. Folded in: the fixed host
name scoped to systems with `os.uname`, Windows' `platform` refused through
`socket.gethostname`; `localhost` labelled the design's value, not ruled; every field
required where `os.uname` exists; no manifest holds a host name's value; native reads of
the host's identity, such as `uuid.getnode()`, stated as missed; a fresh `posix`, by
import or through `_imp.create_builtin` with its spec's name read once, and a new
interpreter refused, which the security pass found open; taking a wrapper apart stated
out of scope.
:::

:::{review} Correctness; security
:id: REV_DES_0008_8
:k: 2
:date: 2026-11-13
:digest: 10080dad74d209c2811d25476b4005dd73b26d0fd9cb89477bac0faf8a0d91a6
Three rounds, one reviewer per lens, on IF_MANIFEST's `reasons` and IF_PROFILE's
unstored modules that {need}`PLAN_0008`'s task 2 added. Folded in: wyatt's ruling of
2026-11-13 that a reason never holds a variable's value, with a backstop; the field list
restored; the order, the rules `valid()` checks and the child's name stated as built;
where home and the temporary directory are read; paths cut before a reason is formatted
and a place replaced only where no other path character follows; the bound reached before
any cleaning; the design's choices labelled; a module with no reason not listed.
:::

:::{review} Correctness; security
:id: REV_DES_0008_9
:k: 2
:date: 2026-11-13
:digest: 7ce082357bf9c981b54c53ebcb5277b57035a5dc4b27aaaf214ff1ae587ac769
Reviewed with {need}`DES_0009`'s nested recorder in {need}`PLAN_0008`'s task 3. Folded in:
`TRIFECTA_RECORD_PARENT` among the recorder's own variables; the store key holding both
`.pth` files' hashes; a recorded child started without `-X pycache_prefix`.
:::
