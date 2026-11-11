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
from pathlib import Path

from trifecta import record
from trifecta.testing import only_on, proves

REPO = Path(__file__).resolve().parent.parent
#: A traced call: ``pid name(args`` with its first path, absolute, relative to the working
#: directory, or relative to a descriptor strace names with ``-y``.
CALL = re.compile(r'^(?:\[pid\s+)?\d+\]?\s+(?P<name>\w+)\((?P<args>.*)$')
PATH_ARG = re.compile(r'^(?:(?:AT_FDCWD|-100)(?:<(?P<cwd>[^>]*)>)?|\d+<(?P<dir>[^>]*)>)?,?\s*'
                      r'"(?P<path>(?:[^"\\]|\\.)*)"')
#: The calls that read, probe or list a path; a write is no input.
READS = {"open", "openat", "openat2", "stat", "lstat", "newfstatat", "fstatat64", "statx",
         "access", "faccessat", "faccessat2", "readlink", "readlinkat", "getdents64",
         "getdents", "execve", "chdir", "listxattr", "getxattr", "lgetxattr", "llistxattr"}
WRITE_FLAGS = ("O_WRONLY", "O_CREAT", "O_TRUNC")


def traced_paths(log: str, cwd: Path) -> tuple[set[Path], list[str]]:
    """Every path the traced calls read, probed or listed, and every connect call."""
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
        if name not in READS:
            continue
        if name.startswith("open") and any(f in args.split(")")[0] for f in WRITE_FLAGS) \
                and "O_RDWR" not in args:
            continue
        if name.startswith("getdents"):
            d = re.match(r"\d+<(?P<dir>[^>]*)>", args)
            if d:
                paths.add(Path(d.group("dir")))
            continue
        p = PATH_ARG.match(args)
        if not p:
            continue
        raw = p.group("path").encode().decode("unicode_escape")
        base = Path(p.group("dir") or p.group("cwd") or cwd)
        paths.add(Path(os.path.normpath(base / raw)))
    return paths, connects


def unheld(paths: set[Path], root: Path, manifest: dict, allowed: list[Path]) -> list[str]:
    """Paths inside ``root`` that the manifest does not hold."""
    held = set(manifest["files"]) | set(manifest["probes"]) | set(manifest["listings"])
    # A lookup is keyed "<directory>/<name>"; the import system lists the directory and
    # probes the name's candidates: name.py, name/, name/__init__.py and the like.
    lookups = [k.removeprefix("./") for k in manifest["lookups"]]
    directories = {k.rpartition("/")[0] or "." for k in lookups}
    out = []
    for path in sorted(paths):
        if not path.is_relative_to(root) or any(path.is_relative_to(a) for a in allowed):
            continue
        rel = path.relative_to(root).as_posix()
        rel = "." if rel in ("", ".") else rel
        if rel in held or rel in directories or rel == ".":
            continue
        if any(rel == k or rel.startswith(k + ".") or rel.startswith(k + "/") for k in lookups):
            continue
        out.append(rel)
    return out


def trace(command: list[str], cwd: Path, directory: Path, root: Path) -> tuple[dict, str]:
    record.prepare(str(directory), str(root))
    env = {k: v for k, v in os.environ.items() if k not in record.OWN}
    env[record.ENV] = str(directory)
    log = directory.parent / f"{directory.name}.strace"
    subprocess.run(["strace", "-f", "-y", "-s", "4096", "-qq", "-o", str(log),
                    "-e", "trace=%file,%network,getdents64,getdents", *command],
                   cwd=cwd, env=env, capture_output=True)
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
'''


class Parsing(unittest.TestCase):
    @proves("REQ_REUSE_SOUND")
    def test_strace_lines_give_the_paths_read_probed_and_listed(self):
        paths, connects = traced_paths(SAMPLE, Path("/repo"))
        self.assertEqual({p.as_posix() for p in paths if p.as_posix().startswith("/repo")},
                         {"/repo/docs/a.md", "/repo/docs/b.md", "/repo/docs/c.md",
                          "/repo/sub", "/repo/pkg/mod.py"})
        self.assertEqual(len(connects), 1)
        manifest = {"files": {"docs/a.md": "x"}, "probes": {"docs/c.md": "file"},
                    "listings": {"sub": []}, "lookups": {"./pkg/mod": "pkg/mod.py"}}
        self.assertEqual(unheld(paths, Path("/repo"), manifest, []), ["docs/b.md"])


class Traced(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def check(self, manifest: dict, log: str, cwd: Path, root: Path, allowed: list[Path]):
        self.assertTrue(manifest["storable"], manifest.get("why"))
        paths, connects = traced_paths(log, cwd)
        self.assertGreater(len(paths), 0, "strace reported no call")
        prefixes = [Path(p) for p in (sys.prefix, sys.base_prefix)]
        self.assertEqual(unheld(paths, root, manifest, allowed + prefixes), [])
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
