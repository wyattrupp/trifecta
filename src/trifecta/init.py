"""`trifecta init` (COMP_INIT_COMMAND): write an adopting repository's starting point.

    trifecta init [--codeowner @name] [--wheel-url URL --wheel-sha256 HEX]

It writes the corpus skeleton, the build files, the hashed lock, the CI workflow, the
CODEOWNERS entry and the planning files into the working directory: the CLAUDE.md section,
the project skill, the hook and its registration. Every refusal is decided before the
first write: a target that exists, a target or a directory on its way that is a link or
other reparse point, and a target that resolves outside the repository. An existing
CLAUDE.md gains the section and an existing .claude/settings.json the hook's
registration, each through a new file moved over it. Each file is created exclusively,
and a run that fails part way removes what it created and restores CLAUDE.md.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys
from dataclasses import dataclass, field
from importlib import metadata
from pathlib import Path, PurePosixPath

from .check import GITATTRIBUTES, package_url_problem
from .toolchain import PACKAGE_DIR, corpus_root, program_env

#: The actions the CI workflow init writes runs, pinned by commit SHA; the test for
#: REQ_INIT_SAFE holds them equal to this repository's own workflow.
ACTIONS = {
    "checkout": "actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4.4.0",
    "setup-python": "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065 # v5.6.0",
}
TYPED_DIRS = ("rfcs", "decisions", "design", "plans")
#: The files that steer the check and the session, each owned in CODEOWNERS.
STEERING = ("/CLAUDE.md", "/.claude/", "/.github/", "/docs/conf.py", "/Makefile",
            "/requirements.lock")
SHA256 = re.compile(r"[0-9a-f]{64}")
OWNER = re.compile(r"@[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})(?:/[A-Za-z0-9._-]+)?")


class Refused(Exception):
    pass


# --- what init writes ----------------------------------------------------------------

def _conf(project: str) -> str:
    return (
        '"""This repository\'s corpus, checked by the trifecta package."""\n\n'
        "from trifecta.ext.ontology import *  # noqa: F403\n\n"
        f"project = {json.dumps(project)}\n"
    )


def _index(project: str) -> str:
    sections = [("RFCs", "rfcs"), ("Decisions", "decisions"), ("Design", "design"),
                ("Plans", "plans")]
    out = [f"# {project}", "", "The RFCs, decisions, design docs and plans of this repository.", ""]
    for caption, directory in sections:
        out += [f"```{{typed-index}} {directory}", f":caption: {caption}", "```", ""]
    return "\n".join(out)


MAKEFILE = """\
# The toolchain is the trifecta package, pinned with every dependency in the hashed lock.
PY ?= python3

.PHONY: setup vale check clean

setup:
\t$(PY) -m pip install --require-hashes --only-binary :all: -r requirements.lock
\t$(PY) -m trifecta setup --vale-only

vale:
\t$(PY) -m trifecta setup --vale-only

## check: run the pipeline. Set BASE=<git ref> to also check history against a ref.
check: vale
\t$(PY) -m trifecta check $(if $(BASE),--base $(BASE))

clean:
\trm -rf docs/_build
"""

GITIGNORE = "bin/\ndocs/_build/\n__pycache__/\n"


def _workflow() -> str:
    return f"""\
name: check

on:
  pull_request:
  push:
    branches: [main]

# The job runs pull-request code; it needs only to read the repository.
permissions:
  contents: read

env:
  GIT_LFS_SKIP_SMUDGE: "1"

jobs:
  check:
    runs-on: ubuntu-24.04
    steps:
      - uses: {ACTIONS["checkout"]}
        with:
          fetch-depth: 0
          persist-credentials: false
      - uses: {ACTIONS["setup-python"]}
        with:
          python-version: "3.12"
      - run: make setup
      - name: Check (with history against the base)
        env:
          EVENT: ${{{{ github.event_name }}}}
          BASE_REF: ${{{{ github.base_ref }}}}
          BEFORE: ${{{{ github.event.before }}}}
        run: |
          if [ "$EVENT" = "pull_request" ]; then
            make check BASE="origin/$BASE_REF"
          elif git cat-file -e "$BEFORE^{{commit}}" 2>/dev/null; then
            make check BASE="$BEFORE"
          elif [ "$BEFORE" = 0000000000000000000000000000000000000000 ] \\
              && [ "$(git rev-parse --is-shallow-repository)" = false ] \\
              && [ "$(git rev-list --count HEAD)" = 1 ]; then
            # A repository's first commit: there is no history to hold it against.
            make check
          else
            echo "::error::push base $BEFORE is not in the clone; history cannot be checked"
            exit 1
          fi
"""


def _codeowners(owner: str) -> str:
    lines = ["# Changes to the files that steer the check and the session need this review."]
    lines += [f"{path} {owner}" for path in STEERING]
    return "\n".join(lines) + "\n"


def _lock(package_line: str) -> str:
    pins = (PACKAGE_DIR / "requirements.lock").read_text(encoding="utf-8")
    return package_line + "\n" + pins


def files(project: str, owner: str, package_line: str) -> dict[str, bytes]:
    """Every file init writes, by repository-relative path."""
    out = {
        "docs/conf.py": _conf(project),
        "docs/index.md": _index(project),
        "Makefile": MAKEFILE,
        "requirements.lock": _lock(package_line),
        ".gitignore": GITIGNORE,
        ".github/workflows/check.yml": _workflow(),
        ".github/CODEOWNERS": _codeowners(owner),
    }
    out.update({f"docs/{d}/.gitkeep": "" for d in TYPED_DIRS})
    encoded = {path: text.encode("utf-8") for path, text in out.items()}
    encoded[".gitattributes"] = GITATTRIBUTES
    return encoded


# --- where the package line and the owner come from ----------------------------------

def package_line(url: str | None, sha256: str | None) -> str:
    """The lock's line for the package: from the options, or from the release this
    package was installed from."""
    if url is None and sha256 is None:
        try:
            direct = json.loads(metadata.distribution("trifecta").read_text("direct_url.json") or "")
            url = direct["url"]
            sha256 = direct["archive_info"]["hashes"]["sha256"]
        except (metadata.PackageNotFoundError, ValueError, KeyError, TypeError):
            raise Refused("this trifecta was not installed from a release wheel with its hash; "
                          "pass --wheel-url and --wheel-sha256") from None
    if not url or not sha256:
        raise Refused("--wheel-url and --wheel-sha256 go together")
    if problem := package_url_problem(url):
        raise Refused(f"--wheel-url: {problem}")
    if not SHA256.fullmatch(sha256):
        raise Refused("--wheel-sha256 is not 64 lowercase hexadecimal digits")
    return f"trifecta @ {url} --hash=sha256:{sha256}"


def codeowner(root: Path, given: str | None) -> str:
    """The CODEOWNERS owner: given, or the GitHub owner of the ``origin`` remote."""
    if given is None:
        proc = subprocess.run(["git", "-C", str(root), "remote", "get-url", "origin"],
                              capture_output=True, encoding="utf-8", errors="replace",
                              env=program_env())
        m = re.match(r"^(?:https://github\.com/|git@github\.com:)([A-Za-z0-9-]+)/",
                     proc.stdout.strip())
        if not m:
            raise Refused("no GitHub origin remote to take the CODEOWNERS owner from; "
                          "pass --codeowner @name")
        given = f"@{m.group(1)}"
    if not OWNER.fullmatch(given):
        raise Refused(f"--codeowner {given!r} is not @user or @org/team")
    return given


# --- writing safely ------------------------------------------------------------------

def _is_link(st: os.stat_result) -> bool:
    reparse = getattr(st, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return stat.S_ISLNK(st.st_mode) or bool(reparse)


def _lstat(path: Path) -> os.stat_result | None:
    try:
        return os.lstat(path)
    except FileNotFoundError:
        return None


def _parents(rel: str) -> list[str]:
    """The directories between the repository root and ``rel``, outermost first."""
    parts = PurePosixPath(rel).parts[:-1]
    return ["/".join(parts[:i]) for i in range(1, len(parts) + 1)]


def check_parents(root: Path, rel: str) -> None:
    """Refuse a directory on the way to ``rel`` that is a link or not a directory."""
    for directory in _parents(rel):
        st = _lstat(root / directory)
        if st is None:
            continue
        if _is_link(st):
            raise Refused(f"{directory}/ is a link or other reparse point")
        if not stat.S_ISDIR(st.st_mode):
            raise Refused(f"{directory} is not a directory")


def check_target(root: Path, rel: str) -> None:
    check_parents(root, rel)
    path = root / rel
    if not path.resolve().is_relative_to(root):
        raise Refused(f"{rel} resolves outside the repository")
    st = _lstat(path)
    if st is not None:
        raise Refused(f"{rel} is a link or other reparse point" if _is_link(st)
                      else f"{rel} exists")


#: Test seams: called with the repository-relative path just before each file is created,
#: and just after. A test swaps a directory or makes a create fail through them.
before_create = None
after_create = None


@dataclass
class Run:
    root: Path
    created_files: list[tuple[str, int, int]] = field(default_factory=list)
    created_dirs: list[str] = field(default_factory=list)

    def write(self, rel: str, data: bytes, mode: int = 0o644,
              final_mode: int | None = None) -> None:
        for directory in _parents(rel):
            check_parents(self.root, f"{directory}/x")
            path = self.root / directory
            if _lstat(path) is None:
                os.mkdir(path)
                self.created_dirs.append(directory)
        if before_create:
            before_create(rel)
        check_parents(self.root, rel)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0) \
            | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(self.root / rel, flags, mode)
        with os.fdopen(fd, "wb") as out:
            st = os.fstat(out.fileno())
            self.created_files.append((rel, st.st_dev, st.st_ino))
            # Windows has no O_NOFOLLOW, and a parent can change between the last check and
            # the open: write nothing unless the file opened is the one at the path, in the
            # repository, and not a link.
            check_parents(self.root, rel)
            at_path = _lstat(self.root / rel)
            if at_path is None or _is_link(at_path) \
                    or (at_path.st_dev, at_path.st_ino) != (st.st_dev, st.st_ino) \
                    or not (self.root / rel).resolve().is_relative_to(self.root):
                raise Refused(f"{rel} is not the file just created in the repository")
            out.write(data)
            if final_mode is not None and hasattr(os, "fchmod"):
                os.fchmod(out.fileno(), final_mode)  # through the handle: no link to follow
        if after_create:
            after_create(rel)

    def undo(self) -> list[str]:
        """Remove what the run created, each after checking its parents and its identity
        again; return what could not be removed."""
        left = []
        for rel, dev, ino in reversed(self.created_files):
            try:
                check_parents(self.root, rel)
                st = _lstat(self.root / rel)
                if st is None or _is_link(st) or (st.st_dev, st.st_ino) != (dev, ino):
                    raise Refused(f"{rel} is not the file this run created")
                os.unlink(self.root / rel)
            except (Refused, OSError):
                left.append(rel)
        for directory in reversed(self.created_dirs):
            try:
                check_parents(self.root, f"{directory}/x")
                st = _lstat(self.root / directory)
                if st is not None and not _is_link(st):
                    os.rmdir(self.root / directory)
            except (Refused, OSError):
                left.append(directory + "/")
        return left


# --- the two files init changes: CLAUDE.md and .claude/settings.json -----------------

CLAUDE_MD = "CLAUDE.md"
SETTINGS = ".claude/settings.json"
HOOK = ".claude/hooks/trifecta_guard.py"
SKILL = ".claude/skills/trifecta-planning/SKILL.md"
NEW = ".trifecta-new"
#: The tools the hook covers, and the command that runs it: fixed text naming the script
#: through $CLAUDE_PROJECT_DIR, trying python3 then python, and blocking with exit 2 when
#: neither can start (REQ_INIT_SAFE, REQ_HOOK_FAILS_CLOSED).
MATCHER = "Write|Edit|MultiEdit|NotebookEdit|Bash"
_RUN_HOOK = f'"$CLAUDE_PROJECT_DIR/{HOOK}"'
COMMAND = f"python3 -I {_RUN_HOOK} || python -I {_RUN_HOOK} || exit 2"
ENTRY = {"matcher": MATCHER, "hooks": [{"type": "command", "command": COMMAND}]}


def section() -> str:
    return (PACKAGE_DIR / "claude" / "CLAUDE_SECTION.md").read_text(encoding="utf-8")


def appended(original: bytes) -> bytes | None:
    """CLAUDE.md with init's section appended, or None when it already holds the section."""
    try:
        text = original.decode("utf-8")
    except UnicodeDecodeError:
        raise Refused(f"{CLAUDE_MD} is not UTF-8") from None
    body = text.removeprefix("﻿")
    lines = body.splitlines()
    wanted = section().splitlines()
    starts = [i for i, line in enumerate(lines) if line == wanted[0]]
    if any(lines[i:i + len(wanted)] != wanted for i in starts):
        raise Refused(f"{CLAUDE_MD} holds the heading {wanted[0]!r} without the rest of the "
                      "section; restore or remove it")
    if starts:
        return None
    if not original:
        return section().encode("utf-8")
    first = body.find("\n")
    nl = "\r\n" if first > 0 and body[first - 1] == "\r" else "\n"
    tail = "" if body.endswith(("\n", "\r")) else nl
    return original + (tail + nl + nl.join(wanted) + nl).encode("utf-8")


class _Strict:
    """Hooks for json.loads that refuse what REQ_INIT_SAFE refuses in the settings file."""

    @staticmethod
    def pairs(pairs):
        keys = [k for k, _ in pairs]
        if len(set(keys)) != len(keys):
            raise ValueError("a key is repeated")
        return dict(pairs)

    @staticmethod
    def constant(name):
        raise ValueError(f"{name} is not a finite number")

    @staticmethod
    def number(text):
        value = float(text)
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError(f"{text[:20]} is not a finite double")
        return value

    @staticmethod
    def integer(text):
        value = int(text)
        try:
            float(value)
        except OverflowError:
            raise ValueError(f"{text[:20]}... does not convert to a finite double") from None
        return value


def merged(original: bytes) -> bytes | None:
    """The settings with init's hook entry added, or None when an equal entry is there."""
    where = SETTINGS
    if not original:
        raise Refused(f"{where} is empty")
    if original.startswith(b"\xef\xbb\xbf"):
        raise Refused(f"{where} carries a byte-order mark")
    try:
        text = original.decode("utf-8")
        data = json.loads(text, object_pairs_hook=_Strict.pairs, parse_constant=_Strict.constant,
                          parse_float=_Strict.number, parse_int=_Strict.integer)
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise Refused(f"{where} is not strict JSON: {exc}") from None
    if not isinstance(data, dict):
        raise Refused(f"{where} does not hold a JSON object")
    if "disableAllHooks" in data and data["disableAllHooks"] is not False:
        raise Refused(f"{where} sets disableAllHooks, which would switch the hook off")
    hooks = data.get("hooks", {})
    if not isinstance(hooks, dict):
        raise Refused(f"{where}: hooks is not an object")
    entries = hooks.get("PreToolUse", [])
    if not isinstance(entries, list):
        raise Refused(f"{where}: hooks.PreToolUse is not an array")
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("hooks"), list):
            raise Refused(f"{where}: a hooks.PreToolUse entry is not an object with a hooks array")
    if ENTRY in entries:
        return None
    for entry in entries:
        if any(isinstance(h, dict) and h.get("command") == COMMAND for h in entry["hooks"]):
            raise Refused(f"{where}: an entry runs init's hook but differs from init's entry")
    data.setdefault("hooks", hooks)
    hooks.setdefault("PreToolUse", entries)
    entries.append(ENTRY)
    try:
        return (json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    except UnicodeEncodeError:
        raise Refused(f"{where} holds a string that is not valid Unicode") from None


@dataclass
class Change:
    """An existing file init changes: its bytes and identity as read, and the new bytes."""
    rel: str
    original: bytes
    st: os.stat_result
    new: bytes
    moved: os.stat_result | None = None


def read_existing(root: Path, rel: str) -> tuple[bytes, os.stat_result] | None:
    """An existing CLAUDE.md or settings file, read through a handle that does not follow
    links, or None when there is none; refused unless it is a regular file in the
    repository, reached through no link."""
    check_parents(root, rel)
    path = root / rel
    st = _lstat(path)
    if st is None:
        return None
    if _is_link(st):
        raise Refused(f"{rel} is a link or other reparse point")
    if not stat.S_ISREG(st.st_mode):
        raise Refused(f"{rel} is not a regular file")
    if not path.resolve().is_relative_to(root):
        raise Refused(f"{rel} resolves outside the repository")
    if _lstat(root / (rel + NEW)) is not None:
        raise Refused(f"{rel + NEW} is left from an earlier run; remove it")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0) \
        | getattr(os, "O_NONBLOCK", 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, "rb") as handle:
        opened = os.fstat(handle.fileno())
        if (opened.st_dev, opened.st_ino) != (st.st_dev, st.st_ino) or not stat.S_ISREG(opened.st_mode):
            raise Refused(f"{rel} changed while it was read")
        return handle.read(), opened


#: Test seams: called with the repository-relative path just before an existing file is
#: replaced, and just after.
before_move = None
after_move = None


def _same(a: os.stat_result, b: os.stat_result) -> bool:
    """The same file, unchanged: identity, size and modification time, and on POSIX the
    change time too, since ext4 hands a freed inode number straight to the next file and
    utime cannot set a change time. Windows' st_ctime is the creation time, which file
    tunnelling keeps across a delete and re-create, so it says nothing there."""
    fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns") + (("st_ctime_ns",) if os.name == "posix" else ())
    return all(getattr(a, f) == getattr(b, f) for f in fields)


def _replace(run: "Run", rel: str, data: bytes, mode: int, expected: os.stat_result) -> os.stat_result:
    """Write ``data`` to ``rel`` + .trifecta-new, created exclusively with mode 0600 and then
    given ``mode``, and move it over ``rel`` once ``rel`` is still the file ``expected``
    describes, reached through no link. Return the moved file's identity."""
    run.write(rel + NEW, data, mode=0o600, final_mode=stat.S_IMODE(mode))
    ours = run.created_files[-1]

    def still_ours() -> None:
        check_parents(run.root, rel)
        st = _lstat(run.root / (rel + NEW))
        if st is None or _is_link(st) or (st.st_dev, st.st_ino) != ours[1:]:
            raise Refused(f"{rel + NEW} is not the file this run wrote")
    if not hasattr(os, "fchmod"):  # Windows: chmod only sets the read-only bit
        still_ours()
        os.chmod(run.root / (rel + NEW), stat.S_IMODE(mode))
    if before_move:
        before_move(rel)
    still_ours()
    now = _lstat(run.root / rel)
    if now is None or _is_link(now) or not _same(now, expected):
        raise Refused(f"{rel} changed after init read it")
    os.replace(run.root / (rel + NEW), run.root / rel)
    run.created_files = [f for f in run.created_files if f[0] != rel + NEW]
    moved = os.lstat(run.root / rel)
    if after_move:
        after_move(rel)
    return moved


def init(root: Path, owner: str | None, url: str | None, sha256: str | None
         ) -> tuple[list[str], list[str]]:
    """Write the starting point into ``root``; return what was written and what changed."""
    root = root.resolve()
    targets = files(root.name, codeowner(root, owner), package_line(url, sha256))
    targets[HOOK] = (PACKAGE_DIR / "claude" / "trifecta_guard.py").read_bytes()
    targets[SKILL] = (PACKAGE_DIR / "claude" / "SKILL.md").read_bytes()
    # Every refusal before the first write: the new files, then the two init may change.
    for rel in targets:
        check_target(root, rel)
    changes: dict[str, Change] = {}
    absent: set[str] = set()
    for rel, build in ((CLAUDE_MD, appended), (SETTINGS, merged)):
        existing = read_existing(root, rel)
        if existing is None:
            check_target(root, rel)
            absent.add(rel)  # created exclusively, so one that appears meanwhile is refused
            continue
        original, st = existing
        new = build(original)
        if new is not None:
            readonly = getattr(st, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_READONLY", 0)
            if readonly or not st.st_mode & stat.S_IWUSR:
                raise Refused(f"{rel} is read-only; make it writable to let init change it")
            changes[rel] = Change(rel, original, st, new)
    created = dict(targets)
    if CLAUDE_MD in absent:
        created[CLAUDE_MD] = section().encode("utf-8")
    settings_new = SETTINGS in absent
    run = Run(root)
    try:
        for rel, data in created.items():
            run.write(rel, data)
        if CLAUDE_MD in changes:
            c = changes[CLAUDE_MD]
            c.moved = _replace(run, CLAUDE_MD, c.new, c.st.st_mode, c.st)
        # The settings are the last write, so the hook is registered only once its script
        # and instructions are in place.
        if settings_new:
            run.write(SETTINGS, merged(b'{}'))
        elif SETTINGS in changes:
            c = changes[SETTINGS]
            c.moved = _replace(run, SETTINGS, c.new, c.st.st_mode, c.st)
    except BaseException as exc:
        left = run.undo()
        detail = exc if isinstance(exc, (Refused, OSError)) else repr(exc)
        message = f"stopped part way: {detail}; removed the files it created"
        if left:
            message += f", but could not remove {', '.join(left)}"
        claude = changes.get(CLAUDE_MD)
        if claude and claude.moved is not None:
            try:
                restore = Run(root)
                _replace(restore, CLAUDE_MD, claude.original, claude.st.st_mode, claude.moved)
                message += f"; restored {CLAUDE_MD}"
            except BaseException as again:
                restore.undo()
                message += (f"; {CLAUDE_MD} still holds the section, since restoring it failed: "
                            f"{again}")
        raise Refused(message) from exc
    written = [rel for rel in created] + ([SETTINGS] if settings_new else [])
    return written, [rel for rel in changes]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--codeowner", help="the owner of the steering files, @user or @org/team")
    parser.add_argument("--wheel-url", help="the release wheel the lock pins")
    parser.add_argument("--wheel-sha256", help="that wheel's SHA-256")
    args = parser.parse_args(argv)
    try:
        written, changed = init(corpus_root(), args.codeowner, args.wheel_url, args.wheel_sha256)
    except Refused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    for rel in written:
        print(f"wrote {rel}")
    for rel in changed:
        print(f"changed {rel}")
    return 0
