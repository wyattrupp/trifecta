"""`trifecta init` (COMP_INIT_COMMAND): write an adopting repository's starting point.

    trifecta init [--codeowner @name] [--wheel-url URL --wheel-sha256 HEX]

It writes the corpus skeleton, the build files, the hashed lock, the CI workflow and the
CODEOWNERS entry into the working directory. Every refusal is decided before the first
write: a target that exists, a target or a directory on its way that is a link or other
reparse point, and a target that resolves outside the repository. Each file is created
exclusively, and a run that fails part way removes every file and directory it created.
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
from .toolchain import PACKAGE_DIR, corpus_root

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
SHA256 = re.compile(r"^[0-9a-f]{64}$")
OWNER = re.compile(r"^@[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})(?:/[A-Za-z0-9._-]+)?$")


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
\t$(PY) -m pip install --require-hashes -r requirements.lock
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
    if not SHA256.match(sha256):
        raise Refused("--wheel-sha256 is not 64 lowercase hexadecimal digits")
    return f"trifecta @ {url} --hash=sha256:{sha256}"


def codeowner(root: Path, given: str | None) -> str:
    """The CODEOWNERS owner: given, or the GitHub owner of the ``origin`` remote."""
    if given is None:
        proc = subprocess.run(["git", "-C", str(root), "remote", "get-url", "origin"],
                              capture_output=True, encoding="utf-8", errors="replace")
        m = re.match(r"^(?:https://github\.com/|git@github\.com:)([A-Za-z0-9-]+)/",
                     proc.stdout.strip())
        if not m:
            raise Refused("no GitHub origin remote to take the CODEOWNERS owner from; "
                          "pass --codeowner @name")
        given = f"@{m.group(1)}"
    if not OWNER.match(given):
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

    def write(self, rel: str, data: bytes) -> None:
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
        fd = os.open(self.root / rel, flags, 0o644)
        st = os.fstat(fd)
        self.created_files.append((rel, st.st_dev, st.st_ino))
        with os.fdopen(fd, "wb") as out:
            out.write(data)
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


def init(root: Path, owner: str | None, url: str | None, sha256: str | None) -> list[str]:
    """Write the starting point into ``root``; return what was written."""
    root = root.resolve()
    targets = files(root.name, codeowner(root, owner), package_line(url, sha256))
    for rel in targets:
        check_target(root, rel)
    run = Run(root)
    try:
        for rel, data in targets.items():
            run.write(rel, data)
    except BaseException as exc:
        left = run.undo()
        detail = exc if isinstance(exc, (Refused, OSError)) else repr(exc)
        message = f"stopped part way, and removed what it wrote: {detail}"
        if left:
            message += f"; could not remove {', '.join(left)}"
        raise Refused(message) from exc
    return list(targets)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--codeowner", help="the owner of the steering files, @user or @org/team")
    parser.add_argument("--wheel-url", help="the release wheel the lock pins")
    parser.add_argument("--wheel-sha256", help="that wheel's SHA-256")
    args = parser.parse_args(argv)
    try:
        written = init(corpus_root(), args.codeowner, args.wheel_url, args.wheel_sha256)
    except Refused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    for rel in written:
        print(f"wrote {rel}")
    return 0
