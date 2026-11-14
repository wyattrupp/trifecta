"""REQ_REUSE_SOUND: native code reads nothing in the repository that the recorder misses.

On Linux, ``strace -f`` follows every system call of a recorded run, its children and
whatever native code they load. Each path inside the repository that the calls open,
probe or list must be one the run's manifest holds, and no call may connect anywhere. The
runs traced are the Sphinx build of this repository's documents and the test child on a
small proof module that reads, lists, probes, imports and starts a Python child.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from importlib.machinery import all_suffixes
from pathlib import Path

from trifecta import record
from trifecta.testing import only_on, proves

REPO = Path(__file__).resolve().parent.parent
SUFFIXES = tuple(all_suffixes())
#: A traced call: ``pid name(args`` with its first path, absolute, relative to the working
#: directory, or relative to a descriptor strace names with ``-y``.
CALL = re.compile(r'^(?:\[pid\s+)?\d+\]?\s+(?P<name>\w+)\((?P<args>.*)$')
PATH_ARG = re.compile(r'^(?:(?:AT_FDCWD|-100)(?:<(?P<cwd>[^>]*)>)?|\d+<(?P<dir>[^>]*)>)?,?\s*'
                      r'"(?P<path>(?:[^"\\]|\\.)*)"')
#: The calls that read, probe or list a path, by what they learn; a write is no input.
READS = {"open", "openat", "openat2"}
PROBES = {"stat", "lstat", "newfstatat", "fstatat64", "statx", "access", "faccessat",
          "faccessat2", "readlink", "readlinkat", "execve", "chdir", "listxattr", "getxattr",
          "lgetxattr", "llistxattr"}
LISTS = {"getdents64", "getdents"}
WRITE_FLAGS = ("O_WRONLY", "O_CREAT", "O_TRUNC")


def traced_paths(log: str, cwd: Path) -> tuple[set[tuple[Path, str]], list[str]]:
    """Every ``(path, access)`` the traced calls made, ``read``, ``probe`` or ``list``, and
    every connect call."""
    paths, connects = set(), []
    for line in log.splitlines():
        m = CALL.match(line)
        if not m:
            continue
        name, args = m.group("name"), m.group("args")
        if name == "connect":
            if "AF_UNIX" not in args or "/var/run/nscd" in args:
                connects.append(line)
            continue
        if name in LISTS:
            d = re.match(r"\d+<(?P<dir>[^>]*)>", args)
            if d:
                paths.add((Path(d.group("dir")), "list"))
            continue
        if name not in READS | PROBES:
            continue
        flags = args.split(", ")[2] if name in READS and args.count(", ") >= 2 else ""
        if name in READS and any(f in flags for f in WRITE_FLAGS) and "O_RDWR" not in flags:
            continue
        p = PATH_ARG.match(args)
        if not p:
            continue
        raw = p.group("path").encode().decode("unicode_escape")
        base = Path(p.group("dir") or p.group("cwd") or cwd)
        # Opening a directory learns only that it is one; its entries come by getdents.
        # A failed open learns only that nothing openable is there.
        failed = re.search(r"\)\s*=\s*-1\s", line) is not None
        access = ("read" if name in READS and "O_DIRECTORY" not in flags and not failed
                  else "probe")
        paths.add((Path(os.path.normpath(base / raw)), access))
    return paths, connects


def unheld(paths: set[tuple[Path, str]], root: Path, manifest: dict,
           allowed: list[Path]) -> list[str]:
    """``access path`` for each path inside ``root`` the manifest does not hold as that
    access: a read is a file the manifest hashed, a listing a directory it listed, a
    probe anything it holds."""
    files, listings = set(manifest["files"]), set(manifest["listings"])
    held = files | set(manifest["probes"]) | listings
    # A lookup is keyed "<directory>/<name>": the import system lists the directory and
    # probes the name's candidates, a module file, a package directory or its __init__.
    lookups = [k.removeprefix("./") for k in manifest["lookups"]]
    lookup_dirs = {k.rpartition("/")[0] or "." for k in lookups}
    candidates = set()
    for k in lookups:
        candidates.add(k)
        candidates.update(k + s for s in SUFFIXES)
        candidates.update(f"{k}/__init__{s}" for s in SUFFIXES)
    out = []
    for path, access in sorted(paths):
        if not path.is_relative_to(root) or any(path.is_relative_to(a) for a in allowed):
            continue
        rel = path.relative_to(root).as_posix()
        rel = "." if rel in ("", ".") else rel
        if access == "read":
            ok = rel in files
        elif access == "list":
            ok = rel in listings or rel in lookup_dirs
        else:
            ok = rel in held or rel in lookup_dirs or rel in candidates or rel == "."
        if not ok:
            out.append(f"{access} {rel}")
    return out


def trace(command: list[str], cwd: Path, directory: Path, root: Path) -> tuple[dict, str]:
    record.prepare(str(directory), str(root))
    env = {k: v for k, v in os.environ.items() if k not in record.OWN}
    # The search path this process has, as the fixture runner gives it, only when it lies
    # in the root given here: a recorded child refuses an entry outside it (DEC_0042).
    entries = [e for e in env.get(record.PATH_ENV, "").split(os.pathsep) if e]
    if entries and not all(Path(e).resolve().is_relative_to(root.resolve())
                           for e in entries):
        del env[record.PATH_ENV]
    env[record.ENV] = str(directory)
    log = directory.parent / f"{directory.name}.strace"
    proc = subprocess.run(["strace", "-f", "-y", "-s", "4096", "-qq", "-o", str(log),
                           "-e", "trace=%file,%network,getdents64,getdents", *command],
                          cwd=cwd, env=env, capture_output=True, encoding="utf-8",
                          errors="replace")
    if proc.returncode != 0:
        raise AssertionError(f"the traced run exited {proc.returncode}: {proc.stderr[-500:]}")
    manifest = json.loads((directory / record.MANIFEST).read_text(encoding="utf-8"))
    return manifest, log.read_text(encoding="utf-8", errors="replace")


TEST_MODULE = '''
import os, subprocess, sys, unittest
import helper


class T(unittest.TestCase):
    def test_reads(self):
        open("data/a.txt").read()
        os.listdir("data")
        os.path.exists("data/gone")
        subprocess.run([sys.executable, "-c", "open('data/b.txt').read()"], check=True)
        self.assertEqual(helper.VALUE, 1)
'''


SAMPLE = r'''101 openat(AT_FDCWD, "docs/a.md", O_RDONLY|O_CLOEXEC) = 3</repo/docs/a.md>
101 openat(AT_FDCWD</repo>, "docs/b.md", O_RDONLY) = 3
101 newfstatat(3</repo/docs>, "c.md", {st_mode=S_IFREG|0644, ...}, 0) = 0
101 openat(AT_FDCWD, "/repo/out.txt", O_WRONLY|O_CREAT|O_TRUNC, 0666) = 4
101 getdents64(5</repo/sub>, 0x55 /* 3 entries */, 32768) = 80
102 stat("/repo/pkg/mod.py", {st_mode=S_IFREG|0644, ...}) = 0
102 access("/elsewhere/x", R_OK) = -1 ENOENT (No such file or directory)
102 connect(7, {sa_family=AF_INET, sin_port=htons(443)}, 16) = 0
102 openat(AT_FDCWD, "/repo/docs/none.conf", O_RDONLY) = -1 ENOENT (No such file or directory)
'''


class Parsing(unittest.TestCase):
    @proves("REQ_REUSE_SOUND")
    def test_strace_lines_give_the_paths_read_probed_and_listed(self):
        paths, connects = traced_paths(SAMPLE, Path("/repo"))
        self.assertEqual({(p.as_posix(), a) for p, a in paths
                          if p.as_posix().startswith("/repo")},
                         {("/repo/docs/a.md", "read"), ("/repo/docs/b.md", "read"),
                          ("/repo/docs/c.md", "probe"), ("/repo/sub", "list"),
                          ("/repo/pkg/mod.py", "probe"), ("/repo/docs/none.conf", "probe")})
        self.assertEqual(len(connects), 1)
        manifest = {"files": {"docs/a.md": "x"},
                    "probes": {"docs/c.md": "file", "docs/none.conf": "absent"},
                    "listings": {"sub": []}, "lookups": {"./pkg/mod": "pkg/mod.py"}}
        self.assertEqual(unheld(paths, Path("/repo"), manifest, []), ["read docs/b.md"])
        # A file the native code opened is held only by its hash, not by a probe.
        probed = {**manifest, "files": {}, "probes": {"docs/a.md": "file", "docs/c.md": "file"}}
        self.assertIn("read docs/a.md", unheld(paths, Path("/repo"), probed, []))
        # A lookup excuses its candidates, not the rest of the package's tree.
        deeper = {(Path("/repo/pkg/mod/data.txt"), "probe")}
        self.assertEqual(unheld(deeper, Path("/repo"), manifest, []), ["probe pkg/mod/data.txt"])


class Traced(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def check(self, manifest: dict, log: str, cwd: Path, root: Path, allowed: list[Path]):
        self.assertTrue(manifest["storable"], manifest.get("why"))
        paths, connects = traced_paths(log, cwd)
        self.assertGreater(len(paths), 0, "strace reported no call")
        # The interpreter's own files are the environment's; the recorder's own file is
        # loaded before it starts and belongs to the package's identity.
        own = [Path(p) for p in (sys.prefix, sys.base_prefix, record.__file__)]
        self.assertEqual(unheld(paths, root, manifest, allowed + own), [])
        self.assertEqual(connects, [])

    @proves("REQ_REUSE_SOUND")
    @only_on("posix")
    def test_the_build_reads_nothing_its_manifest_lacks(self):
        directory, out = self.tmp / "record", self.tmp / "html"
        # Sphinx changes into its configuration directory, so it starts there.
        manifest, log = trace([sys.executable, "-m", "sphinx", "-q", "-E", "-b", "html",
                               ".", str(out)], REPO / "docs", directory, REPO)
        self.check(manifest, log, REPO / "docs", REPO, [REPO / "docs" / "_build"])

    @proves("REQ_REUSE_SOUND")
    @only_on("posix")
    def test_the_test_child_reads_nothing_its_manifest_lacks(self):
        root = self.tmp / "repo"
        (root / "tests").mkdir(parents=True)
        (root / "data").mkdir()
        (root / "tests" / "__init__.py").write_text("", encoding="utf-8")
        (root / "tests" / "test_traced.py").write_text(TEST_MODULE, encoding="utf-8")
        (root / "helper.py").write_text("VALUE = 1\n", encoding="utf-8")
        for name in ("a.txt", "b.txt"):
            (root / "data" / name).write_text(name, encoding="utf-8")
        control = self.tmp / "control"
        control.mkdir()
        plan = control / "plan.json"
        plan.write_text(json.dumps({"modules": ["tests.test_traced"], "leave_out": []}),
                        encoding="utf-8")
        package = str(Path(record.__file__).resolve().parent.parent)
        boot = ("import sys; sys.path.insert(0, sys.argv[1]); "
                "from trifecta.proof_child import main; "
                "sys.path.remove(sys.argv[1]); sys.path.insert(0, ''); "
                "sys.exit(main(sys.argv[2:]))")
        manifest, log = trace([sys.executable, "-E", "-X", "utf8", "-c", boot, package,
                               str(control / "records.jsonl"), str(plan)],
                              root, self.tmp / "record", root)
        records = (control / "records.jsonl").read_text(encoding="utf-8")
        self.assertIn('"outcome": "success"', records)
        self.check(manifest, log, root, root, [])
