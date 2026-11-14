"""REQ_REUSE_SOUND: native code reads nothing in the repository that the recorder misses.

On Linux, ``strace -f`` follows every system call of a recorded run, its children and
whatever native code they load. Each path inside the repository that the calls open,
probe or list must be one the run's manifest holds, and no call may connect anywhere. The
runs traced are the Sphinx build of this repository's documents and the test child on a
small proof module that reads, lists, probes, imports and starts a Python child.

REQ_KNOWN_PROGRAM: strace is a known program here and only here (COMP_KNOWN_PROGRAMS,
DEC_0037). The recorder lets it through by its path and hash in exactly the form these
traces start it, and keys the module on its log: every path the traced command read,
probed or listed, each absence, each program it started with its interpreters, and the
whole environment; what the log cannot hold refuses the run.
"""

from __future__ import annotations

import hashlib
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
from unittest import mock

from trifecta import record, store
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
    # The form the recorder lets strace through in (COMP_KNOWN_PROGRAMS), its log under a
    # directory the run made.
    proc = subprocess.run(["strace", "-f", "-y", "-s", "4096", "-qq", "-o", str(log), *command],
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


# --- strace as a known program (COMP_KNOWN_PROGRAMS, DEC_0037) ----------------------------

def recorder(root: Path, made: list[Path], module: str | None = record.STRACE_MODULE,
             directory: Path | None = None) -> record.Recorder:
    """A recorder this process makes and never starts: what it judges and records is read
    from it, and it records nothing of this process. ``made`` are the directories it holds
    the run as having made."""
    directory = directory or root.parent / "recorder"
    config = {"root": str(root), "recorder": record.__file__, "ignore": []}
    if module is not None:
        config[record.MODULE_KEY] = module
    r = record.Recorder(str(directory), config)
    r.created.update(record._norm(str(p)) for p in made)
    return r


def manifest_of(r: record.Recorder) -> dict:
    """What ``r`` recorded, as a stored manifest holds it."""
    return {"version": record.VERSION, "storable": not r.refused(),
            **{name: dict(getattr(r, name)) for name in record.SECTIONS}}


def whys(r: record.Recorder) -> list[str]:
    return [reason["why"] for reason in r.reasons]


def elf(path: Path, interpreter: str | None = None) -> Path:
    """Write a 64-bit ELF header at ``path``, naming ``interpreter`` in a PT_INTERP header
    when given: a program to start that is no system file, which this module's own process
    may read without reaching through a system link."""
    import struct
    name = b"" if interpreter is None else os.fsencode(interpreter) + b"\0"
    phnum = 1 if name else 0
    header = (b"\x7fELF" + bytes([2, 1, 1]) + bytes(9)
              + struct.pack("<HHIQQQIHHHHHH", 2, 0x3E, 1, 0, 64, 0, 0, 64, 56, phnum, 0, 0, 0))
    ph = struct.pack("<IIQQQQQQ", 3, 4, 120, 0, 0, len(name), len(name), 1) if name else b""
    path.write_bytes(header + ph + name)
    path.chmod(0o755)
    return path


class TracedTree(unittest.TestCase):
    """A tree to trace in: a repository with documents and a test the trace never reads,
    and a directory the run made, which holds strace's log."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.root = self.tmp / "repo"
        for name, text in (("docs/a.md", "a"), ("docs/b.md", "b"), ("sub/x.txt", "x"),
                           ("tests/test_unread.py", "VALUE = 1\n")):
            (self.root / name).parent.mkdir(parents=True, exist_ok=True)
            (self.root / name).write_text(text, encoding="utf-8")
        self.made = self.tmp / "made"
        self.made.mkdir()
        self.log = self.made / "trace.log"
        # The command a synthetic log starts first, as strace's does: one the run made.
        elf(self.made / "start")
        # A program of the repository's own, with an ELF interpreter of its own.
        (self.root / "bin").mkdir()
        self.loader = elf(self.root / "bin" / "loader")
        self.program = elf(self.root / "bin" / "program", str(self.loader))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def take(self, text: str, r: record.Recorder | None = None) -> record.Recorder:
        """Take ``text``, a log in which ROOT, MADE, LOG and OUTSIDE stand for those paths,
        into ``r``, as the recorder takes strace's log once strace has ended: through the
        descriptor it opened the log with. A log that does not start its command first is
        given the start strace writes first."""
        r = r or recorder(self.root, [self.made])
        text = textwrap.dedent(text).lstrip()
        if not text.startswith("100 execve("):
            text = START + text
        self.write_log(text)
        record._take_trace(r, self.trace(r), 0)
        return r

    def write_log(self, text: str) -> None:
        for holder, path in (("ROOT", self.root), ("MADE", self.made), ("LOG", self.log),
                             ("OUTSIDE", self.tmp / "outside")):
            text = text.replace(holder, str(path))
        self.log.write_text(text, encoding="utf-8")

    def trace(self, r: record.Recorder, fd: int | None = None) -> record._Trace:
        fd = os.open(self.log, os.O_RDONLY) if fd is None else fd
        return record._Trace(str(self.log), str(self.root), fd, r.written, r.created)

    def differs(self, r: record.Recorder, environ: dict | None = None) -> str | None:
        return store.mismatch(manifest_of(r), self.root, environ or {}, store.Hashes())


#: What strace writes first: its command's start, here a program the run made.
START = '100 execve("MADE/start", ["start"], 0x7ffd /* 0 vars */) = 0\n'
LOG = '''\
    100 execve("ROOT/bin/program", ["program"], 0x7ffd5 /* 3 vars */) = 0
    100 openat(AT_FDCWD<ROOT>, "docs/a.md", O_RDONLY|O_CLOEXEC) = 3<ROOT/docs/a.md>
    100 read(3<ROOT/docs/a.md>, "a", 4096) = 1
    100 newfstatat(AT_FDCWD<ROOT>, "docs/gone.md", 0x7ffd, 0) = -1 ENOENT (No such file or directory)
    100 access("ROOT/docs/none", R_OK) = -1 ENOENT (No such file or directory)
    100 readlink("ROOT/docs/unlinked", 0x7ffd, 4096) = -1 ENOENT (No such file or directory)
    100 openat(AT_FDCWD<ROOT>, "sub", O_RDONLY|O_NONBLOCK|O_CLOEXEC|O_DIRECTORY) = 4<ROOT/sub>
    100 getdents64(4<ROOT/sub>, 0x55 /* 3 entries */, 32768) = 80
    100 clone(child_stack=NULL, flags=CLONE_CHILD_CLEARTID|CLONE_CHILD_SETTID|SIGCHLD <unfinished ...>
    101 chdir("docs") = 0
    101 stat("b.md", {st_mode=S_IFREG|0644, st_size=1, ...}) = 0
    100 <... clone resumed>, child_tidptr=0x7f) = 101
    100 stat("sub/x.txt", {st_mode=S_IFREG|0644, st_size=1, ...}) = 0
    100 openat(AT_FDCWD<MADE>, "out.txt", O_WRONLY|O_CREAT|O_TRUNC, 0666) = 5<MADE/out.txt>
    100 openat(AT_FDCWD, "/dev/null", O_RDWR) = 6</dev/null>
    100 openat(AT_FDCWD, "/dev/urandom", O_RDONLY) = 6</dev/urandom>
    100 openat(AT_FDCWD, "/proc/self/fd", O_RDONLY|O_DIRECTORY|O_CLOEXEC) = 7</proc/100/fd>
    100 getdents64(7</proc/100/fd>, 0x55 /* 5 entries */, 32768) = 120
    101 readlink("/proc/self/exe", "/usr/bin/dash", 4096) = 13
    101 readlink("/proc/100/exe", "/usr/bin/dash", 4096) = 13
    100 socket(AF_UNIX, SOCK_STREAM|SOCK_CLOEXEC, 0) = 8<socket:[1]>
    100 --- SIGCHLD {si_signo=SIGCHLD, si_code=CLD_EXITED, si_pid=101} ---
    100 uname({sysname="Linux", nodename="localhost", ...}) = 0
    100 exit_group(0) = ?
    100 +++ exited with 0 +++
'''


INET6 = '100 socket(AF_INET6, SOCK_STREAM|SOCK_CLOEXEC, IPPROTO_IP) = 3<socket:[2]>\n'
BIND6 = ('100 bind(3<socket:[2]>, {{sa_family=AF_INET6, sin6_port=htons(0), '
         'sin6_flowinfo=htonl(0), inet_pton(AF_INET6, "{address}", &sin6_addr), '
         'sin6_scope_id=0}}, 28) = 0\n')


class TraceLog(TracedTree):
    @proves("REQ_KNOWN_PROGRAM", "REQ_REUSE_SOUND")
    @only_on("posix")
    def test_the_log_gives_every_path_read_probed_or_listed_and_each_absence(self):
        r = self.take(LOG)
        self.assertEqual(whys(r), [])
        sha = lambda text: hashlib.sha256(text.encode()).hexdigest()
        self.assertEqual(r.files, {"docs/a.md": sha("a"), "docs/b.md": sha("b"),
                                   "sub/x.txt": sha("x")})
        # Each failed open, stat, access or readlink is held as what is there: absence.
        for key in ("docs/gone.md", "docs/none", "docs/unlinked"):
            self.assertEqual(r.probes[key], "absent")
        # A child that changed its directory read b.md there; its parent kept its own.
        self.assertEqual(r.probes["docs"], "directory")
        self.assertEqual(r.listings, {"sub": [["x.txt", "file"]]})
        self.assertEqual(set(r.programs), {"bin/program", "bin/loader"})
        # What the run made, its own /proc entries' fd and exe, /dev/null and /dev/urandom
        # are no inputs.
        self.assertFalse([k for k in (*r.files, *r.probes, *r.outside)
                          if "out.txt" in k or k.startswith(("/proc", "/dev"))])

    @proves("REQ_REUSE_SOUND")
    @only_on("posix")
    def test_a_change_to_a_document_read_reruns_and_to_a_test_not_read_does_not(self):
        r = self.take(LOG)
        self.assertIsNone(self.differs(r))
        (self.root / "tests" / "test_unread.py").write_text("VALUE = 2\n", encoding="utf-8")
        self.assertIsNone(self.differs(r))
        (self.root / "docs" / "a.md").write_text("changed", encoding="utf-8")
        self.assertEqual(self.differs(r), "file docs/a.md")

    @proves("REQ_REUSE_SOUND")
    @only_on("posix")
    def test_a_path_found_absent_that_appears_reruns(self):
        r = self.take(LOG)
        (self.root / "docs" / "gone.md").write_text("here", encoding="utf-8")
        self.assertEqual(self.differs(r), "path docs/gone.md")

    @proves("REQ_KNOWN_PROGRAM", "REQ_REUSE_SOUND")
    @only_on("posix")
    def test_what_the_trace_cannot_hold_refuses_the_run(self):
        (self.root / "docs" / "link.md").symlink_to(self.root / "docs" / "a.md")
        cases = {
            # Beside what DEC_0043 allows: another entry of its own, another process's
            # maps, and a probe of its own maps.
            '100 openat(AT_FDCWD, "/proc/self/status", O_RDONLY) = 3</proc/100/status>':
                "the proc entry self/status",
            '100 openat(AT_FDCWD, "/proc/1/maps", O_RDONLY) = 3</proc/1/maps>':
                "the proc entry another process/maps",
            '100 stat("/proc/self/maps", {st_mode=S_IFREG|0444, ...}) = 0':
                "the proc entry self/maps",
            '100 openat(AT_FDCWD, "/proc/self/fd/3", O_RDONLY) = 4<ROOT/docs/a.md>':
                "the proc entry self/fd/3",
            '100 readlink("/proc/self/cwd", "/", 4096) = 1': "the proc entry self/cwd",
            '100 readlink("/proc/1/exe", "/sbin/init", 4096) = 10':
                "the proc entry another process/exe",
            '100 openat(AT_FDCWD, "/proc/stat", O_RDONLY) = 3</proc/stat>':
                "the proc entry stat",
            '100 openat(AT_FDCWD, "/proc/filesystems", O_RDONLY) = 3</proc/filesystems>':
                "the proc entry filesystems",
            '100 stat("/proc/self/fd", {st_mode=S_IFDIR|0500, ...}) = 0':
                "the proc entry self/fd",
            '100 openat(AT_FDCWD, "/dev/tty", O_RDWR) = 3</dev/tty>': "the device tty",
            '100 connect(3<socket:[1]>, {sa_family=AF_UNIX, sun_path="/run/x"}, 110) = 0':
                "makes a connection",
            '100 socket(AF_INET6, SOCK_STREAM|SOCK_CLOEXEC, IPPROTO_IP) = 3<socket:[2]>':
                "binds to no loopback address",
            '100 socket(AF_NETLINK, SOCK_RAW, NETLINK_ROUTE) = 3<socket:[3]>':
                "a socket of a network family",
            '100 sendto(3<socket:[1]>, "x", 1, 0, {sa_family=AF_INET, '
            'sin_port=htons(53)}, 16) = 1': "sends to an address",
            '100 openat(AT_FDCWD, "ROOT/docs/a.md", O_WRONLY|O_TRUNC) = 3<ROOT/docs/a.md>':
                "outside the run's own directories",
            '100 unlink("ROOT/docs/b.md") = 0': "outside the run's own directories",
            '100 openat(AT_FDCWD, "LOG", O_RDONLY) = 3<LOG>': "opens the log strace writes",
            '100 openat(AT_FDCWD, "ROOT/docs/link.md", O_RDONLY) = 3<ROOT/docs/a.md>':
                "reads through a link",
            '100 io_uring_setup(8, {}) = 3': "io_uring",
            '100 frobnicate(1) = 0': "a call the recorder does not list: frobnicate",
            'not a line of strace': "a line with no process",
            '100 openat(AT_FDCWD, "ROOT/docs/a.md"..., O_RDONLY) = 3': "cut short",
            '100 openat(7, "a.md", O_RDONLY) = 3': "a descriptor strace did not name",
            '100 read(3, "x", 1 <unfinished ...>': "a call that never ended",
            '100 openat(AT_FDCWD, "ROOT/docs/a.md", O_RDONLY) = 3': "an open strace did not name",
        }
        for line, why in cases.items():
            with self.subTest(line=line):
                r = self.take(line + "\n")
                self.assertTrue(any(why in w for w in whys(r)), whys(r))
                self.assertEqual({reason["process"] for reason in r.reasons}, {"strace"})

    @proves("REQ_KNOWN_PROGRAM", "REQ_REUSE_SOUND")
    @only_on("posix")
    def test_what_dec_0043_allows_is_let_through_and_not_keyed(self):
        allowed = {
            "its own maps":
                '100 openat(AT_FDCWD, "/proc/self/maps", O_RDONLY) = 3</proc/100/maps>\n',
            "its own cgroup, by its number":
                '100 openat(AT_FDCWD, "/proc/100/cgroup", O_RDONLY|O_CLOEXEC) = '
                '3</proc/100/cgroup>\n'
                '100 statx(3</proc/100/cgroup>, "", AT_STATX_SYNC_AS_STAT|AT_EMPTY_PATH, '
                'STATX_ALL, 0x7ffd) = -1 ENOSYS (Function not implemented)\n',
            "a socket bound to IPv6's loopback": INET6 + BIND6.format(address="::1"),
            "a socket bound to IPv4's loopback":
                '100 socket(AF_INET, SOCK_DGRAM, IPPROTO_IP) = 3<socket:[7]>\n'
                '100 bind(3<socket:[7]>, {sa_family=AF_INET, sin_port=htons(0), '
                'sin_addr=inet_addr("127.0.0.1")}, 16) = 0\n'
                '100 close(3<socket:[7]>) = 0\n',
        }
        for name, log in allowed.items():
            with self.subTest(name):
                r = self.take(log)
                self.assertEqual(whys(r), [])
                self.assertEqual(manifest_of(r)["outside"], {})
                self.assertEqual(manifest_of(r)["probes"], {})

    @proves("REQ_KNOWN_PROGRAM", "REQ_REUSE_SOUND")
    @only_on("posix")
    def test_a_loopback_socket_that_reaches_further_is_refused(self):
        bound = INET6 + BIND6.format(address="::1")
        cases = {
            "bound elsewhere": (INET6 + BIND6.format(address="::"), "not loopback"),
            "bound to another host": (INET6 + BIND6.format(address="2001:db8::1"),
                                      "not loopback"),
            "never bound": (INET6, "binds to no loopback address"),
            "connects": (bound + '100 connect(3<socket:[2]>, {sa_family=AF_INET6, '
                         'sin6_port=htons(80)}, 28) = 0\n', "makes a connection"),
            "sends to an address": (bound + '100 sendto(3<socket:[2]>, "x", 1, 0, '
                                    '{sa_family=AF_INET6, sin6_port=htons(53)}, 28) = 1\n',
                                    "sends to an address"),
            "sends": (bound + '100 sendmsg(3<socket:[2]>, {msg_name=NULL}, 0) = 1\n',
                      "sends on a socket of a network family"),
            "listens": (bound + '100 listen(3<socket:[2]>, 5) = 0\n',
                        "listens on a socket of a network family"),
            "accepts": (bound + '100 accept4(3<socket:[2]>, NULL, NULL, 0) = 4<socket:[9]>\n',
                        "accepts on a socket of a network family"),
            "a local socket bound": ('100 socket(AF_UNIX, SOCK_STREAM, 0) = 3<socket:[4]>\n'
                                     '100 bind(3<socket:[4]>, {sa_family=AF_UNIX, '
                                     'sun_path="MADE/s"}, 110) = 0\n', "binds a socket"),
        }
        for name, (log, why) in cases.items():
            with self.subTest(name):
                r = self.take(log)
                self.assertTrue(any(why in w for w in whys(r)), whys(r))

    @proves("REQ_REUSE_SOUND")
    @only_on("posix")
    def test_strace_ended_by_a_signal_is_refused(self):
        r = recorder(self.root, [self.made])
        self.write_log(textwrap.dedent(LOG))
        record._take_trace(r, self.trace(r), -9)
        self.assertEqual(whys(r), ["strace did not finish"])

    @proves("REQ_KNOWN_PROGRAM", "REQ_REUSE_SOUND")
    @only_on("posix")
    def test_a_log_that_does_not_start_its_command_is_refused(self):
        r = recorder(self.root, [self.made])
        self.write_log('100 openat(AT_FDCWD, "ROOT/docs/a.md", O_RDONLY) = 3<ROOT/docs/a.md>\n')
        record._take_trace(r, self.trace(r), 0)
        self.assertEqual(whys(r), ["its log holds no start of the traced command first"])

    @proves("REQ_REUSE_SOUND")
    @only_on("posix")
    def test_a_child_no_trace_follows_is_refused(self):
        for line in ('100 clone(child_stack=NULL, flags=CLONE_UNTRACED|SIGCHLD) = 101',
                     '100 clone3({flags=CLONE_VM|CLONE_UNTRACED, exit_signal=SIGCHLD}, 88) '
                     '= 101'):
            with self.subTest(line=line):
                self.assertEqual(whys(self.take(line + "\n")),
                                 ["starts a process no trace follows"])
        self.assertEqual(whys(self.take('100 clone(child_stack=NULL, flags=SIGCHLD) = 101\n')),
                         [])

    @proves("REQ_REUSE_SOUND")
    @only_on("posix")
    def test_signals_reach_only_what_is_traced(self):
        for line in ('100 kill(0, SIGTERM) = 0', '100 kill(100, SIGTERM) = 0',
                     '100 tgkill(100, 100, SIGABRT) = 0', '100 pidfd_open(100, 0) = 3'):
            with self.subTest(line=line):
                self.assertEqual(whys(self.take(line + "\n")), [])
        for line in ('100 kill(1, SIGTERM) = 0', '100 kill(-1, SIGKILL) = 0',
                     '100 kill(-77, SIGTERM) = 0', '100 tkill(77, SIGTERM) = 0',
                     '100 tgkill(1, 1, SIGTERM) = 0', '100 pidfd_open(1, 0) = 3'):
            with self.subTest(line=line):
                self.assertEqual(whys(self.take(line + "\n")),
                                 ["signals a process it does not trace"])

    @proves("REQ_REUSE_SOUND")
    @only_on("posix")
    def test_a_read_of_what_the_run_wrote_while_strace_ran_is_refused(self):
        r = recorder(self.root, [self.made])
        self.write_log(START + '100 openat(AT_FDCWD, "ROOT/docs/a.md", O_RDONLY) = '
                       '3<ROOT/docs/a.md>\n')
        trace = self.trace(r)
        # The run writes docs/a.md, and makes a directory, after strace started.
        r.written.add(record._norm(str(self.root / "docs" / "a.md")))
        record._take_trace(r, trace, 0)
        self.assertTrue(any("which the run wrote while strace ran" in w for w in whys(r)),
                        whys(r))


class Links(TracedTree):
    """A link the run made reaches only what it made; a read is keyed by the path the
    kernel opened too, and one whose name no longer reaches it is refused."""

    def setUp(self):
        super().setUp()
        self.outside = self.tmp / "outside"
        self.outside.mkdir()
        (self.outside / "secret.txt").write_text("secret", encoding="utf-8")
        elf(self.outside / "prog")
        # A link the run would have made, had it been let: the recorder refuses making it.
        (self.made / "d").symlink_to(self.outside)

    @proves("REQ_REUSE_SOUND")
    @only_on("posix")
    def test_a_read_through_a_link_is_keyed_on_what_was_opened(self):
        r = self.take('100 openat(AT_FDCWD, "MADE/d/secret.txt", O_RDONLY) = '
                      '3<OUTSIDE/secret.txt>\n')
        self.assertEqual(whys(r), [])
        secret = str(self.outside / "secret.txt")
        self.assertEqual(r.outside, {secret: record.file_hash(secret)})
        (self.outside / "secret.txt").write_text("changed", encoding="utf-8")
        self.assertEqual(self.differs(r), f"file {secret}")

    @proves("REQ_REUSE_SOUND")
    @only_on("posix")
    def test_a_program_through_a_link_is_keyed_where_it_lands(self):
        r = self.take('100 execve("MADE/d/prog", ["prog"], 0x7ffd /* 0 vars */) = 0\n')
        self.assertIn(str(self.outside / "prog"), r.programs)

    @proves("REQ_REUSE_SOUND")
    @only_on("posix")
    def test_what_a_link_cannot_carry_is_refused(self):
        cases = {
            '100 stat("MADE/d/secret.txt", {st_mode=S_IFREG|0644, ...}) = 0':
                "through a link the run made",
            # The name now reaches another file than the kernel opened.
            '100 openat(AT_FDCWD, "ROOT/docs/b.md", O_RDONLY) = 3<ROOT/docs/a.md>':
                "whose links changed while strace ran",
            '100 symlink("OUTSIDE", "MADE/l") = 0': "makes a link to outside what the run made",
            '100 symlinkat("OUTSIDE/secret.txt", AT_FDCWD<MADE>, "l") = 0':
                "makes a link to outside what the run made",
        }
        for line, why in cases.items():
            with self.subTest(line=line):
                r = self.take(line + "\n")
                self.assertTrue(any(why in w for w in whys(r)), whys(r))
        self.assertEqual(whys(self.take('100 symlink("start", "MADE/own") = 0\n')), [])


class InterpreterLinks(TracedTree):
    """The interpreter's own links, as a venv's home names one, are held with their targets
    in a trace (DEC_0045); any other read through a link stays refused."""

    def setUp(self):
        super().setUp()
        out = self.tmp / "outside"
        (out / "python-3.12.16" / "lib").mkdir(parents=True)
        (out / "python-3.12.16" / "lib" / "os.py").write_text("x", encoding="utf-8")
        (out / "python-3.12.20" / "lib").mkdir(parents=True)
        (out / "python-3.12.20" / "lib" / "os.py").write_text("x", encoding="utf-8")
        self.home = out / "python-3.12"
        self.home.symlink_to(out / "python-3.12.16")
        (out / "elsewhere").symlink_to(out / "python-3.12.16")
        # The interpreter's links, as a venv whose home is the link names them.
        patcher = mock.patch.object(record, "_interpreter_links",
                                    return_value=[str(self.home)])
        patcher.start()
        self.addCleanup(patcher.stop)

    LOG = ('100 readlink("OUTSIDE/python-3.12", "OUTSIDE/python-3.12.16", 4096) = 30\n'
           '100 stat("OUTSIDE/python-3.12/lib/os.py", {st_mode=S_IFREG|0644, ...}) = 0\n')

    @proves("REQ_KNOWN_PROGRAM", "REQ_REUSE_SOUND")
    @only_on("posix")
    def test_a_venv_home_that_is_a_link_is_held_with_its_target(self):
        r = self.take(self.LOG)
        self.assertEqual(whys(r), [])
        self.assertEqual(r.probes[str(self.home)],
                         record.LINK_TO + str(self.tmp / "outside" / "python-3.12.16"))
        self.assertTrue(record._link_to(r.probes[str(self.home)]))
        self.assertIsNone(self.differs(r))

    @proves("REQ_REUSE_SOUND")
    @only_on("posix")
    def test_a_retargeted_interpreter_link_reruns(self):
        r = self.take(self.LOG)
        self.home.unlink()
        self.home.symlink_to(self.tmp / "outside" / "python-3.12.20")
        self.assertEqual(self.differs(r), f"path {self.home}")

    @proves("REQ_REUSE_SOUND")
    @only_on("posix")
    def test_a_link_seen_first_without_following_is_held_with_its_target(self):
        r = self.take('100 lstat("OUTSIDE/python-3.12", {st_mode=S_IFLNK|0777, ...}) = 0\n'
                      + self.LOG)
        self.assertEqual(whys(r), [])
        self.assertEqual(r.probes[str(self.home)],
                         record.LINK_TO + str(self.tmp / "outside" / "python-3.12.16"))
        self.home.unlink()
        self.home.symlink_to(self.tmp / "outside" / "python-3.12.20")
        self.assertEqual(self.differs(r), f"path {self.home}")

    @proves("REQ_KNOWN_PROGRAM", "REQ_REUSE_SOUND")
    @only_on("posix")
    def test_another_link_under_the_prefix_is_refused(self):
        r = self.take('100 readlink("OUTSIDE/elsewhere", "OUTSIDE/python-3.12.16", 4096) = 30\n')
        self.assertTrue(any("through a link" in w for w in whys(r)), whys(r))

    @proves("REQ_KNOWN_PROGRAM")
    @only_on("posix")
    def test_the_links_met_resolving_a_path_are_the_chain(self):
        out = self.tmp / "outside"
        (out / "bin").symlink_to(self.home)
        # bin -> python-3.12 -> python-3.12.16: both links are met on the way to lib.
        self.assertEqual(record._link_chain(str(out / "bin" / "lib" / "os.py")),
                         [str(out / "bin"), str(self.home)])
        self.assertEqual(record._link_chain(str(out / "python-3.12.16" / "lib")), [])


class HeldLog(TracedTree):
    """The log is read through the descriptor the recorder opened before strace started,
    so no name given to it later stands for it."""

    def strace_wrote(self) -> int:
        fd = record.open_log(str(self.log))
        self.write_log(START + '100 openat(AT_FDCWD, "ROOT/docs/a.md", O_RDONLY) = '
                       '3<ROOT/docs/a.md>\n')
        return fd

    def forged(self) -> str:
        return START.replace("MADE", str(self.made))

    @proves("REQ_KNOWN_PROGRAM", "REQ_REUSE_SOUND")
    @only_on("posix")
    def test_a_log_unlinked_and_made_again_is_not_read(self):
        fd = self.strace_wrote()
        self.log.unlink()
        self.log.write_text(self.forged(), encoding="utf-8")
        r = recorder(self.root, [self.made])
        record._take_trace(r, self.trace(r, fd), 0)
        self.assertIn("docs/a.md", r.files)

    @proves("REQ_KNOWN_PROGRAM", "REQ_REUSE_SOUND")
    @only_on("posix")
    def test_a_log_whose_directory_was_moved_is_not_read_by_its_name(self):
        fd = self.strace_wrote()
        try:
            self.made.rename(self.tmp / "moved")
        except PermissionError:
            os.close(fd)
            self.skipTest("this system moves no directory that holds an open file")
        self.made.mkdir()
        self.log.write_text(self.forged(), encoding="utf-8")
        r = recorder(self.root, [self.made])
        record._take_trace(r, self.trace(r, fd), 0)
        self.assertIn("docs/a.md", r.files)

    @proves("REQ_KNOWN_PROGRAM", "REQ_REUSE_SOUND")
    @only_on("posix")
    def test_what_would_write_the_log_is_refused(self):
        cases = {
            '100 unlink("LOG") = 0': "opens the log strace writes",
            '100 openat(AT_FDCWD, "LOG", O_WRONLY|O_TRUNC) = 3<LOG>':
                "opens the log strace writes",
            '100 rename("MADE", "MADE2") = 0':
                "moves or removes the directory that holds strace's log",
            '100 symlink("MADE", "MADE/alias") = 0\n'
            '100 openat(AT_FDCWD, "MADE/alias/trace.log", O_WRONLY) = 3<LOG>':
                "opens the log strace writes",
        }
        for line, why in cases.items():
            with self.subTest(line=line):
                r = self.take(line + "\n")
                self.assertTrue(any(why in w for w in whys(r)), whys(r))

    @proves("REQ_KNOWN_PROGRAM", "REQ_REUSE_SOUND")
    @only_on("posix")
    def test_the_run_writing_the_log_by_any_name_is_refused(self):
        fd = self.strace_wrote()
        r = recorder(self.root, [self.made])
        r.traces[1] = (object(), self.trace(r, fd))
        other = self.made / "other"
        os.link(self.log, other)
        r.wrote(str(other))
        self.assertIn("writes the log of a strace still running", whys(r))
        os.close(fd)


class FollowedLink(TracedTree):
    """The one path read through a link the run did not make (DEC_0043), here a link
    outside the repository and the run's own directories named in place of locale.alias."""

    def setUp(self):
        super().setUp()
        etc, share = self.tmp / "etc", self.tmp / "share"
        etc.mkdir()
        share.mkdir()
        self.target = etc / "locale.alias"
        self.target.write_text("C.UTF-8 C.UTF-8\n", encoding="utf-8")
        self.alias = share / "locale.alias"
        self.alias.symlink_to(self.target)
        self.other = share / "other.alias"
        self.other.symlink_to(self.target)
        patcher = mock.patch.object(record, "FOLLOWED_LINKS", frozenset({str(self.alias)}))
        patcher.start()
        self.addCleanup(patcher.stop)

    def read(self, path: Path) -> record.Recorder:
        return self.take(f'100 openat(AT_FDCWD, "{path}", O_RDONLY|O_CLOEXEC) = '
                         f'3<{self.target}>\n')

    @proves("REQ_KNOWN_PROGRAM", "REQ_REUSE_SOUND")
    @only_on("posix")
    def test_its_link_and_target_are_held(self):
        r = self.read(self.alias)
        self.assertEqual(whys(r), [])
        digest = record.file_hash(str(self.target))
        self.assertEqual(r.probes[str(self.alias)], "link")
        self.assertEqual(r.outside, {str(self.alias): digest, str(self.target): digest})
        self.assertIsNone(self.differs(r))

    @proves("REQ_REUSE_SOUND")
    @only_on("posix")
    def test_a_change_to_its_content_reruns(self):
        r = self.read(self.alias)
        self.target.write_text("en_US en_US.UTF-8\n", encoding="utf-8")
        self.assertEqual(self.differs(r), f"file {self.alias}")

    @proves("REQ_REUSE_SOUND")
    @only_on("posix")
    def test_a_change_to_its_target_reruns(self):
        r = self.read(self.alias)
        elsewhere = self.tmp / "etc" / "elsewhere.alias"
        elsewhere.write_text("other\n", encoding="utf-8")
        self.alias.unlink()
        self.alias.symlink_to(elsewhere)
        self.assertEqual(self.differs(r), f"file {self.alias}")

    @proves("REQ_KNOWN_PROGRAM", "REQ_REUSE_SOUND")
    @only_on("posix")
    def test_another_file_through_a_link_is_refused(self):
        r = self.read(self.other)
        self.assertTrue(any("reads through a link" in w for w in whys(r)), whys(r))


class TracePrograms(TracedTree):
    def setUp(self):
        super().setUp()
        # An interpreter of the repository's own, with an ELF interpreter, and a script.
        self.interpreter = elf(self.root / "bin" / "interp", str(self.loader))
        self.tool = self.root / "bin" / "tool"
        self.tool.write_text(f"#!{self.interpreter}\necho\n", encoding="utf-8")
        self.tool.chmod(0o755)

    @proves("REQ_KNOWN_PROGRAM", "REQ_REUSE_SOUND")
    @only_on("posix")
    def test_each_program_started_is_held_with_its_interpreters(self):
        self.assertEqual(record._elf_interpreter(str(self.interpreter)), str(self.loader))
        self.assertIsNone(record._elf_interpreter(str(self.loader)))
        r = self.take('100 execve("ROOT/bin/tool", ["tool"], 0x7ffd /* 0 vars */) = 0\n')
        self.assertEqual(whys(r), [])
        self.assertEqual(set(r.programs), {"bin/tool", "bin/interp", "bin/loader"})
        self.assertEqual(r.programs["bin/interp"], record.file_hash(str(self.interpreter)))
        self.assertIsNone(self.differs(r))

    @proves("REQ_REUSE_SOUND")
    @only_on("posix")
    def test_a_change_to_an_elf_interpreter_reruns(self):
        r = self.take('100 execve("ROOT/bin/tool", ["tool"], 0x7ffd /* 0 vars */) = 0\n')
        with open(self.loader, "ab") as f:
            f.write(b"\0")
        self.assertEqual(self.differs(r), "program bin/loader")

    @proves("REQ_REUSE_SOUND")
    @only_on("posix")
    def test_a_change_to_an_interpreter_reruns(self):
        r = self.take('100 execve("ROOT/bin/tool", ["tool"], 0x7ffd /* 0 vars */) = 0\n')
        with open(self.interpreter, "ab") as f:
            f.write(b"\0")
        self.assertEqual(self.differs(r), "program bin/interp")

    @proves("REQ_KNOWN_PROGRAM", "REQ_REUSE_SOUND")
    @only_on("posix")
    def test_a_program_the_kernel_hands_to_a_handler_is_refused(self):
        (self.root / "bin" / "app.exe").write_bytes(b"MZ\x90\x00")
        r = self.take('100 execve("ROOT/bin/app.exe", ["app"], 0x7ffd /* 0 vars */) = 0\n')
        self.assertTrue(any("neither a script nor an ELF program" in w for w in whys(r)),
                        whys(r))

    @proves("REQ_REUSE_SOUND")
    @only_on("posix")
    def test_a_program_searched_for_and_planted_there_reruns(self):
        r = self.take('100 execve("ROOT/bin/cat", ["cat"], 0x7ffd /* 0 vars */) = -1 ENOENT '
                      '(No such file or directory)\n')
        self.assertEqual(r.probes, {"bin/cat": "absent"})
        elf(self.root / "bin" / "cat")
        self.assertEqual(self.differs(r), "path bin/cat")


class StraceTerms(TracedTree):
    """Whether a start of strace is let through, judged as the recorder's wrapper of
    ``_execute_child`` judges it."""

    def setUp(self):
        super().setUp()
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        self.strace = self.bin / "strace"
        shutil.copy(shutil.which("strace"), self.strace)
        # Its ELF interpreter is the system's, reached through a link this module's own
        # recorder would refuse it for reading; programs' interpreters are TracePrograms'.
        patcher = mock.patch.object(record, "_elf_interpreter", return_value=None)
        patcher.start()
        self.addCleanup(patcher.stop)

    def start(self, argv: list[str], r: record.Recorder | None = None, env=None,
              path: str | None = None, **given):
        r = r or recorder(self.root, [self.made])
        final = {"PATH": path or str(self.bin)}
        if env:
            final.update(env)
        # The process started with the environment the start inherits.
        r.start_names = sorted(final)
        terms = {"shell": False, "preexec_fn": None, "close_fds": True, "pass_fds": (),
                 **given}
        why, trace, resolved = record._strace_start(
            r, argv, argv[0], env, final, str(self.root), terms["shell"],
            terms["preexec_fn"], terms["close_fds"], terms["pass_fds"])
        return r, why, trace, resolved

    def form(self, log: Path | str | None = None) -> list[str]:
        return ["strace", *record.STRACE_FORM, str(log or self.log), "/bin/true"]

    @proves("REQ_KNOWN_PROGRAM")
    @only_on("posix")
    def test_strace_is_let_through_by_its_path_and_hash(self):
        r, why, trace, resolved = self.start(self.form())
        self.assertIsNone(why)
        self.assertEqual(resolved, str(self.strace))
        self.assertEqual(r.programs[resolved], record.file_hash(resolved))
        self.assertEqual(trace.log, str(self.log))
        self.assertEqual(whys(r), [])
        # The recorder made the log, new, and holds it open.
        self.assertEqual(trace.identity, (os.stat(self.log).st_dev, os.stat(self.log).st_ino))
        os.close(trace.fd)

    @proves("REQ_KNOWN_PROGRAM", "REQ_REUSE_SOUND")
    @only_on("posix")
    def test_a_start_outside_its_terms_is_refused(self):
        elsewhere = self.tmp / "elsewhere"
        elsewhere.mkdir()
        (self.made / "out").symlink_to(elsewhere)
        (self.made / "there.log").write_text("", encoding="utf-8")
        script = self.tmp / "fake"
        script.mkdir()
        (script / "strace").write_text("#!/bin/sh\n", encoding="utf-8")
        (script / "strace").chmod(0o755)
        inside = self.root / "bin"
        shutil.copy(self.strace, inside / "strace")
        form = self.form()
        module = "runs strace, which only test_record_trace's own process may start"
        args = "runs strace with arguments other than -f -y -s 4096 -qq -o LOG"
        code = "runs strace with code before it starts or descriptors it inherits"
        outside = "runs strace with its log outside a directory the run made"
        cases = {
            "another module": (form, {"module": "tests.test_store"}, module),
            "no module": (form, {"module": None}, module),
            "-e": (["strace", "-e", "trace=%file", *form[1:]], {}, args),
            "no -y": ([form[0], "-f", *form[3:]], {}, args),
            "-s 1024": ([*form[:4], "1024", *form[5:]], {}, args),
            "an option for a command": ([*form[:8], "-p", "1"], {}, args),
            "no command": (form[:8], {}, args),
            "a command along PATH": ([*form[:8], "true"], {},
                                     "runs strace on a command not named by its absolute path"),
            "the log piped into a command": (self.form("|cat"), {},
                                             "runs strace with its log piped into a command"),
            "the log run as a command": (self.form("!cat"), {},
                                         "runs strace with its log piped into a command"),
            "the log elsewhere": (self.form(elsewhere / "x.log"), {}, outside),
            "the log through a link": (self.form(self.made / "out" / "x.log"), {}, outside),
            "the log already there": (self.form(self.made / "there.log"), {},
                                      "runs strace with a log that is already there"),
            "a shell": (form, {"shell": True}, "runs strace through a shell"),
            "code before it starts": (form, {"preexec_fn": print}, code),
            "descriptors": (form, {"pass_fds": (3,)}, code),
            "every descriptor": (form, {"close_fds": False}, code),
            "the parent's variable": (form, {"env": {record.PARENT_ENV: "x"}},
                                      f"runs strace with {record.PARENT_ENV} already set"),
            "a script": (form, {"path": str(script)}, "runs a strace that is not an ELF program"),
            "in the repository": (form, {"path": str(inside)},
                                  "runs a strace under the repository or one the run made"),
            "not found": (form, {"path": str(self.tmp / "nowhere")},
                          "runs strace, which is not found"),
        }
        for name, (argv, given, expected) in cases.items():
            with self.subTest(name):
                module = given.pop("module", record.STRACE_MODULE)
                r = recorder(self.root, [self.made], module=module)
                r, why, trace, _ = self.start(argv, r, **given)
                self.assertEqual(why, expected)
                self.assertIsNone(trace)
                self.assertEqual(r.programs, {})
                self.assertEqual(r.traces, {})

    @proves("REQ_KNOWN_PROGRAM", "REQ_REUSE_SOUND")
    @only_on("posix")
    def test_the_log_is_known_as_it_is_made(self):
        # The start registers the trace before strace starts, under the lock the run's
        # events take: a write of the run's to the log the moment it exists is refused.
        r, why, trace, _ = self.start(self.form())
        self.assertIsNone(why)
        self.assertEqual([t for _, t in r.traces.values()], [trace])
        r.wrote(str(self.log))
        self.assertIn("writes the log of a strace still running", whys(r))
        os.close(trace.fd)

    @proves("REQ_KNOWN_PROGRAM", "REQ_REUSE_SOUND")
    @only_on("posix")
    def test_a_log_the_run_wrote_is_refused_when_taken(self):
        for name in ("the log", "another name of it"):
            with self.subTest(name):
                r, why, trace, _ = self.start(self.form())
                self.assertIsNone(why)
                written = self.log if name == "the log" else self.made / "alias"
                if written != self.log:
                    os.link(self.log, written)
                self.write_log(START)
                # As if a write had been let through: the backstop finds it written.
                r.written.add(record._norm(str(written)))
                record._take_trace(r, trace, 0)
                self.assertIn("the run wrote strace's log", whys(r))
                for path in (self.log, self.made / "alias"):
                    path.unlink(missing_ok=True)

    @proves("REQ_KNOWN_PROGRAM", "REQ_REUSE_SOUND")
    @only_on("posix")
    def test_a_strace_planted_on_path_reruns(self):
        first = self.root / "first"
        first.mkdir()
        real = str(self.bin)
        r, why, _, _ = self.start(self.form(), path=f"{first}:{real}")
        self.assertIsNone(why)
        self.assertEqual(r.probes["first/strace"], "absent")
        environ = {"PATH": f"{first}:{real}"}
        self.assertIsNone(self.differs(r, environ))
        shutil.copy(self.strace, first / "strace")
        self.assertEqual(self.differs(r, environ), "path first/strace")

    @proves("REQ_KNOWN_PROGRAM", "REQ_REUSE_SOUND")
    @only_on("posix")
    def test_a_change_to_strace_reruns(self):
        r, why, _, resolved = self.start(self.form())
        self.assertIsNone(why)
        environ = {"PATH": str(self.bin)}
        self.assertIsNone(self.differs(r, environ))
        with open(resolved, "ab") as f:
            f.write(b"\0")
        self.assertEqual(self.differs(r, environ), f"program {resolved}")

    @proves("REQ_KNOWN_PROGRAM", "REQ_REUSE_SOUND")
    @only_on("posix")
    def test_the_whole_environment_is_recorded_but_the_runs_own(self):
        here = [("HOME", "/home/someone"), ("INHERITED", "one"), ("GIVEN", "two"),
                (record.ENV, "/tmp/record"), ("SET_BY_RUN", "three")]
        sha = lambda v: hashlib.sha256(v.encode()).hexdigest()
        with mock.patch.object(record, "_environment", return_value=here):
            # Started with env=None: every variable it inherits reaches it, and is recorded.
            r = recorder(self.root, [self.made])
            r.env_set.add("SET_BY_RUN")
            record._whole_environment(r, None, dict(here))
            names = record.names_digest(["HOME", "INHERITED", "GIVEN", "SET_BY_RUN"])
            self.assertEqual(r.environment, {"HOME": sha("/home/someone"),
                                             "INHERITED": sha("one"), "GIVEN": sha("two"),
                                             record.NAMES: names})
            # Started with a mapping: a value the run gave is its own, and so is a variable
            # it added.
            given = {**dict(here), "GIVEN": "changed", "ADDED": "four"}
            r = recorder(self.root, [self.made])
            record._whole_environment(r, given, given)
            self.assertEqual(set(r.environment),
                             {"HOME", "INHERITED", "SET_BY_RUN", record.NAMES})
        environ = {k: v for k, v in here if k not in record.OWN}
        self.assertIsNone(self.differs(r, environ))
        self.assertEqual(self.differs(r, {**environ, "INHERITED": "other"}),
                         "variable INHERITED")
        # A variable that appears, or one that vanishes, reruns it too.
        self.assertEqual(self.differs(r, {**environ, "LD_PRELOAD": "/x.so"}),
                         "the environment's names")
        self.assertEqual(self.differs(r, {k: v for k, v in environ.items() if k != "GIVEN"}),
                         "the environment's names")

    @proves("REQ_KNOWN_PROGRAM")
    @only_on("posix")
    def test_a_child_of_the_module_is_not_its_own_process(self):
        directory = self.made / "recorder"
        directory.mkdir()
        r = recorder(self.root, [self.made], directory=directory)
        record._prepare_child(r, None, {}, "python", "token")
        config = json.loads((directory / "children" / "token" / record.CONFIG).read_text(
            encoding="utf-8"))
        self.assertNotIn(record.MODULE_KEY, config)

    @proves("REQ_REUSE_SOUND")
    @only_on("posix")
    def test_the_log_is_the_runs_to_touch_only_once_taken(self):
        r = recorder(self.root, [self.made])
        r.traces[1] = (object(), record._Trace(str(self.log), str(self.root),
                                               record.open_log(str(self.log))))
        r.wrote(str(self.log))
        self.assertIn("writes the log of a strace still running", whys(r))
        r = recorder(self.root, [self.made])
        r.traces[1] = (object(), record._Trace(str(self.log), str(self.root),
                                               os.open(self.log, os.O_RDONLY)))
        r.refuse("an earlier reason")
        self.assertIn({"process": None, "why": "starts strace and does not wait for it"},
                      r.manifest()["reasons"])


class StraceRuns(TracedTree):
    """strace itself, started here in its form, which this module's own process may."""

    def strace(self, command: list[str], env: dict) -> subprocess.CompletedProcess:
        return subprocess.run(["strace", *record.STRACE_FORM, str(self.log), *command],
                              cwd=self.root, env=env, capture_output=True,
                              encoding="utf-8", errors="replace", check=True)

    @proves("REQ_KNOWN_PROGRAM", "REQ_REUSE_SOUND")
    @only_on("posix")
    def test_a_traced_script_is_keyed_on_what_it_read_and_ran(self):
        script = self.root / "run.sh"
        script.write_text("#!/bin/sh\ncat docs/a.md\n[ -e docs/gone ] || echo sub/*\n",
                          encoding="utf-8")
        script.chmod(0o755)
        # The C locale reads no locale's files, which a system may hold through links.
        env = {k: v for k, v in os.environ.items() if k not in record.OWN}
        env["LC_ALL"] = "C"
        out = self.strace([str(script)], env)
        self.assertEqual(out.stdout, "asub/x.txt\n")
        # The system's own files are left out here: what they hold is the module's own
        # recorder's to key, and resolving their links in this process would reach them.
        r = recorder(self.root, [self.made])
        r.ignore += [record._norm(p) for p in ("/usr", "/lib", "/lib32", "/lib64", "/etc",
                                               "/bin", "/sbin")]
        started = []
        # The system's programs are reached through links, which this module's own recorder
        # would refuse it for hashing: here they are only named; TracePrograms hashes them.
        with mock.patch.object(record, "_note_program",
                               lambda r, path, cwd, depth=0: started.append(path)):
            record._take_trace(r, self.trace(r), 0)
        self.assertEqual(whys(r), [])
        self.assertIn("docs/a.md", r.files)
        self.assertEqual(r.probes["docs/gone"], "absent")
        self.assertEqual(r.listings["sub"], [["x.txt", "file"]])
        self.assertIn(str(script), started)
        self.assertIn("cat", {os.path.basename(p) for p in started})
        self.assertIsNone(self.differs(r, env))
        (self.root / "tests" / "test_unread.py").write_text("VALUE = 3\n", encoding="utf-8")
        self.assertIsNone(self.differs(r, env))
        (self.root / "docs" / "a.md").write_text("changed", encoding="utf-8")
        self.assertEqual(self.differs(r, env), "file docs/a.md")

    @proves("REQ_KNOWN_PROGRAM", "REQ_REUSE_SOUND")
    @only_on("posix")
    def test_the_recorder_of_this_module_takes_stracess_log(self):
        # This module's own recorder, which the check starts it under, named by proofs.
        own = getattr(sys.modules.get(record.MODULE), "_recorder", None)
        if own is None:
            self.skipTest("this process is not recorded")
        self.assertEqual(own.config.get(record.MODULE_KEY), record.STRACE_MODULE)
        before = len(own.reasons)
        script = self.root / "read.sh"
        script.write_text("#!/bin/sh\ncat docs/a.md\n", encoding="utf-8")
        script.chmod(0o755)
        env = {k: v for k, v in os.environ.items() if k not in record.OWN}
        env["LC_ALL"] = "C"
        self.strace([str(script)], env)
        # The wrapper let strace through and recorded it; the reap took its log, whose
        # programs the command started are recorded too; no trace is left untaken.
        self.assertEqual(own.reasons[before:], [])
        self.assertTrue(any(os.path.basename(p) == "strace" for p in own.programs))
        self.assertIn("/bin/sh", own.programs)
        self.assertEqual(own.traces, {})

    @proves("REQ_HOST_READS", "REQ_KNOWN_PROGRAM")
    @only_on("posix")
    def test_the_traced_command_sees_the_fixed_host_name(self):
        directory = self.made / "record"
        record.prepare(str(directory), str(self.root))
        env = {k: v for k, v in os.environ.items() if k not in record.OWN}
        env = record.carry_search_path(str(directory), env)
        env[record.ENV] = str(directory)
        out = self.strace([sys.executable, "-c", "import os, platform; "
                           "print(platform.node(), os.uname().nodename)"], env)
        self.assertEqual(out.stdout.split(), [record.HOST_NAME, record.HOST_NAME])
