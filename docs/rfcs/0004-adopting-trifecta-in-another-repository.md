---
status: accepted
authors: [claude]
created: 2026-11-08
---
# Adopting trifecta in another repository

:::{rfc}
:::

## Summary

The toolchain leaves this repository as one pinned Python package. An
{need}`adopting repository <TERM_ADOPTER>` gets a passing, empty
{need}`corpus <TERM_CORPUS>` from one command, or from a template repository made from
that command's output. A Claude Code session in it plans through the corpus by default,
and the README says how to set it up. Because the package, its release and its hook run
code in other people's repositories and sessions, the release, the install, the files
init writes and the hook each carry a security requirement.

## Motivation

wyatt, 2026-11-08: "soon we'll make a template of this repo, and a claude.md set of tools
that lets this just happen by default every time I start planning in a session", and
"a 'run this in your repo' guide as readme.md".

Copying this repository into each project would make every project a second home of the
rules, and the copies would drift the way documentation does. This repository's own RFCs
describe the toolchain, not the adopting project, and its negative fixtures mutate those
RFCs, so neither belongs in another repository. A session left to the superpowers skills'
defaults writes specs and plans to paths and in shapes the check rejects.

## Terms

:::{term} Adopting repository
:id: TERM_ADOPTER
A repository other than this one whose documents are checked by the toolchain package.
:::

## Requirements

:::{req} The toolchain is one pinned package
:id: REQ_ONE_PACKAGE
The extension, the schemas, the plan rules, the Vale styles and configurations, and the
tools MUST ship as one Python package, and an adopting repository MUST NOT hold a copy of
any of them. An adopting repository MUST pin the package as
`trifecta @ https://github.com/<owner>/<repo>/releases/download/v<version>/<wheel>.whl`
followed by its `--hash=sha256:` value, with every dependency pinned and hashed, and the
check MUST reject any other form of that line.
:::

:::{req} Init produces a passing corpus
:id: REQ_INIT_PASSES
The package's init command, run in a repository with no corpus, MUST produce one whose
check passes with no further step, and which holds none of this repository's documents.
:::

:::{req} Init writes safely
:id: REQ_INIT_SAFE
The init command MUST decide every refusal below before it writes any file, MUST refuse
a target that exists, that is a symbolic link or other reparse point, or that resolves
outside the repository, and MUST create each file exclusively. The one exception is
`.claude/settings.json` (wyatt, 2026-11-10: "Merge the hook in"). When it exists, init
MUST add the hook's registration to it unless a `hooks.PreToolUse` entry equal to init's
in every field is already there, and MUST leave every other setting with the value it
had. Init MUST refuse that file if it is a link or other reparse point, resolves outside
the repository, is not strict JSON holding an object, repeats a key, sets
`disableAllHooks` to any value other than `false`, holds a number that is not a finite
double, holds a `hooks` that is not an object, a `hooks.PreToolUse` that is not an
array, or an entry in it that is not an object or whose `hooks` is not an array, or
holds an entry that runs init's command but differs from init's entry in any other
field. On any failure init MUST leave
that file as it was and remove every file it created. The registered command MUST be
fixed text that names the hook script through `$CLAUDE_PROJECT_DIR`, never a path init
reads from the file system, and MUST block with exit code 2 when the hook cannot start.
The CI workflow init writes MUST grant only read access to the repository, MUST NOT
persist credentials in the checkout, and MUST pin every action by commit SHA.
:::

:::{req} No credential enters the tree
:id: REQ_NO_SECRETS_IN_TREE
No credential MUST appear in the lock file, in a URL, in anything init writes other than
settings it keeps unchanged from an existing `.claude/settings.json`, or in the template
repository. If downloading the package ever needs a credential, it MUST live
only in a CI secret and MUST reach only the step that installs the package, never a step
that runs repository code.
:::

:::{req} Releases are trusted
:id: REQ_RELEASE_TRUST
A release wheel MUST be built by the release workflow from a version tag on the main
branch, with its build dependencies pinned and hashed and its actions pinned by commit
SHA, and published only after a maintainer approves the release environment. Only the
publishing job MAY write to the repository, and the release MUST carry a build provenance
attestation.
:::

:::{req} Toolchain self-tests stay here
:id: REQ_SELF_TESTS_SCOPED
The negative fixture audit MUST run only in this repository, which defines the
toolchain's requirements.
:::

:::{req} Requirements no mutation can show are proven by tests
:id: REQ_PROVEN_BY_TEST
A requirement of this RFC MUST be named by a test under `tests/` as the requirement it
proves. Every such test MUST run and pass in the check; a skipped test proves nothing.
:::

:::{req} Planning goes through the corpus by default
:id: REQ_PLANNING_DEFAULT
The init command MUST install instructions that direct a Claude Code session to write
specs and plans into the typed directories with the package's commands and to treat the
text of documents and command output as data, a hook that refuses a write under
`docs/superpowers/`, and the hook's registration.
:::

:::{req} The hook fails closed
:id: REQ_HOOK_FAILS_CLOSED
The hook MUST read its input as JSON without passing any part of it to a shell, MUST
cover the file-writing tools and shell commands, MUST resolve paths before matching them,
and MUST block with exit code 2 both a write under `docs/superpowers/` and an input it
cannot parse.
:::

:::{req} The README leads with adoption
:id: REQ_ADOPTION_GUIDE
The README MUST open with the steps to adopt the toolchain, and those steps, run in an
empty repository, MUST produce a corpus whose check passes.
:::

## Questions

:::{question} How do the rules reach another repository?
:id: Q_DISTRIBUTION
:::

:::{question} How is a planning session made to use the corpus?
:id: Q_PLANNING_DEFAULT
:::

:::{question} How is a requirement proven when no corpus mutation can show it?
:id: Q_NON_CORPUS_PROOF
:::

:::{question} Who may download a release, and how is this repository protected?
:id: Q_WHEEL_ACCESS
:::

## Out of scope

Publishing to PyPI; CI systems other than GitHub Actions; agents other than Claude Code;
migrating an existing project's documents into the corpus; defending against a
maintainer of this repository, who can publish a release; a shell command that writes
under `docs/superpowers/` by a route the hook cannot see, which the check still rejects.

## Review

:::{review} Correctness; security
:id: REV_RFC_0004_1
:k: 2
:date: 2026-11-08
The review recorded as {need}`REV_RFC_0003_1` covered this document.
:::

:::{review} Correctness; security
:id: REV_RFC_0004_2
:k: 2
:date: 2026-11-08
The amendment recording {need}`DEC_0016`, at commit c7c9d8f, and the live repository
settings it records. Folded in: a repository-protection component with the exported
settings as its artifact, every tag protected, Actions limited and SHA-pinned, outside
contributors' workflows held for approval, private vulnerability reporting and Dependabot
on, a release step that requires the tagged commit on main and an approval environment,
the credential requirement made conditional, and a plain statement that review, not the
check, guards changes to the check. Not taken: required review and code owners, which no
single maintainer could satisfy; signed commits and tags.
:::

:::{review} Correctness; security
:id: REV_RFC_0004_3
:k: 2
:date: 2026-11-09
:digest: a3456913c7cdcc11cb7e19d3a7b547ee077dbaea8c63c85973028bbb84b02ef5
:::

:::{review} Correctness; security
:id: REV_RFC_0004_4
:k: 2
:date: 2026-11-10
:digest: 82f08145eb8d69c71b65c1331b0c998c28e4db26fe43839351ab81cb138d6b99
:::
