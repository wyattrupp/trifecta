"""REQ_KNOWN_PROGRAM: on Linux, git and Vale in their forms read nothing outside the
inputs COMP_KNOWN_PROGRAMS states for them, start nothing further, read no host name and
connect nowhere, as ``strace`` shows.

Each form is judged as the recorder judges it, by a recorder this process makes and never
starts, and then run under ``strace``; every path the traced program opened, probed or
listed outside the directory the run made must be one the judged start recorded. Vale's
runtime also reads files of the kernel's no key can hold; until a ruling allows them the
recorder refuses Vale on Linux, and the test shows those reads are all that is left.

strace is a known program only in ``test_record_trace``'s own process (DEC_0037), so this
module's run under its own recorder is refused there, and it stays fresh on Linux.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from trifecta import record
from trifecta.testing import only_on, proves

from tests.test_record_trace import traced_paths

REPO = Path(__file__).resolve().parent.parent
PACKAGE = Path(record.__file__).resolve().parent
#: The files whose reads would read the host's name.
HOST_NAME = ("/etc/hostname", "/proc/sys/kernel/hostname")


def held(r: record.Recorder, root: Path) -> tuple[set[str], dict[str, set[str]]]:
    """Every path ``r`` recorded, as given and resolved, and each listed directory's
    entries."""
    paths, listed = set(), {}
    for name in ("files", "outside", "probes", "listings", "programs"):
        for key, value in getattr(r, name).items():
            path = key if os.path.isabs(key) else os.path.normpath(root / key)
            paths.update({path, os.path.realpath(path)})
            if name == "listings":
                listed[path] = {entry for entry, _ in value}
    return paths, listed


def unstated(paths, r: record.Recorder, root: Path, made: Path) -> list[str]:
    """``access path`` for each path traced outside what the run made that ``r`` did not
    record: a path is held by its key or its resolved key, an absence by a listing of a
    directory above it that lacks the next name on its way, and the root and the
    directories above it, which are directories wherever the root is."""
    keys, listed = held(r, root)
    out = []
    for path, access in sorted(paths):
        p = str(path)
        if path.is_relative_to(made) or p in record.TRACE_DEVICES or p in keys \
                or os.path.realpath(p) in keys or Path(root).is_relative_to(path):
            continue
        covered = False
        for directory, entries in listed.items():
            if Path(p).is_relative_to(directory) and p != directory:
                first = Path(p).relative_to(directory).parts[0]
                covered = first not in entries
                if covered:
                    break
        if not covered:
            out.append(f"{access} {p}")
    return out


@unittest.skipUnless(os.name == "posix" and shutil.which("strace"), "no strace")
class Traced(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.made = self.tmp / "made"
        self.target = self.made / "repo"
        self.home = self.made / "home"
        for path in (self.target, self.home):
            path.mkdir(parents=True)
        self.env = {k: v for k, v in os.environ.items()
                    if not k.startswith(("GIT_", "VALE_")) and k not in ("TERM", *record.OWN)}
        self.env.update(GIT_CEILING_DIRECTORIES=str(self.made), GIT_CONFIG_NOSYSTEM="1",
                        GIT_CONFIG_GLOBAL="", HOME=str(self.home),
                        XDG_CONFIG_HOME=str(self.home / ".config"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def recorder(self) -> record.Recorder:
        r = record.Recorder(str(self.tmp / "recorder"),
                            {"root": str(REPO), "recorder": record.__file__, "ignore": []})
        r.created.add(record._norm(str(self.made)))
        r.git_inits.add(record._norm(str(self.target)))
        record.take_pins(r, record.__file__)
        r.start_names = sorted(self.env)
        return r

    def trace(self, name: str, argv: list[str], judge, cwd: Path, parse_cwd: Path,
              ) -> tuple[record.Recorder, str | None, list[str], str]:
        """Judge ``argv`` and run it under strace: the recorder, why it refused, each path
        traced that it did not record, and the log."""
        r = self.recorder()
        r.local.tracing = True
        try:
            why, resolved = judge(r, argv, argv[0], None, dict(self.env), str(cwd), False)
        finally:
            r.local.tracing = False
        log = self.made / f"{name}.log"
        program = resolved or argv[0]
        done = subprocess.run(["strace", *record.STRACE_FORM, str(log), program, *argv[1:]],
                              cwd=cwd, env=self.env, capture_output=True, encoding="utf-8",
                              errors="replace")
        self.assertEqual(done.returncode in (0, 1, 2), True, done.stderr)
        text = log.read_text(encoding="utf-8", errors="replace")
        paths, connects = traced_paths(text, parse_cwd)
        self.assertEqual(connects, [], name)
        starts = [line for line in text.splitlines() if re.search(r"\bexecve\(", line)]
        self.assertEqual(len(starts), 1, f"{name} starts a further program: {starts}")
        self.assertNotRegex(text, r"\buname\(", f"{name} reads the host's name")
        for path in HOST_NAME:
            self.assertNotIn(f'"{path}"', text, f"{name} reads the host's name")
        return r, why, unstated(paths, r, REPO, self.made), text

    @proves("REQ_KNOWN_PROGRAM")
    @only_on("posix")
    def test_git_in_its_forms_reads_only_its_stated_inputs(self):
        fresh = self.made / "fresh"
        fresh.mkdir()
        r, why, outside, _ = self.trace("init", ["git", "init", "-q", str(fresh)],
                                        record._git_start, REPO, REPO)
        self.assertIsNone(why)
        self.assertEqual(outside, [], "init")
        subprocess.run(["git", "init", "-q", str(self.target)], check=True, env=self.env)
        for form in record.GIT_FORMS:
            with self.subTest(form):
                argv = ["git", "-C", str(self.target), *form]
                r, why, outside, _ = self.trace(form[0], argv, record._git_start, REPO,
                                                self.target)
                self.assertIsNone(why)
                self.assertEqual(outside, [], form)

    @proves("REQ_KNOWN_PROGRAM")
    @only_on("posix")
    def test_vale_in_its_forms_reads_only_its_stated_inputs_and_its_runtimes(self):
        vale = REPO / "bin" / "vale"
        if not vale.is_file():
            self.skipTest("no bin/vale")
        build = self.made / "build"
        shutil.copytree(PACKAGE / "vale", build / "vale" / "vale")
        shutil.copytree(PACKAGE / "styles", build / "vale" / "styles")
        (build / "vale" / "styles" / "TrifectaGenerated").mkdir()
        lint = build / "lint" / "rfcs"
        lint.mkdir(parents=True)
        (lint / "a.html").write_text("<p>The thing must be.</p>", encoding="utf-8")
        forms = {"version": [str(vale), "--version"],
                 "lint": [str(vale), f"--config={build / 'vale' / 'vale' / 'prose.ini'}",
                          *record.VALE_FORM, str(lint)]}
        for name, argv in forms.items():
            with self.subTest(name):
                r, why, outside, _ = self.trace(name, argv, record._vale_start, self.target,
                                                self.target)
                self.assertEqual(why, "runs vale, whose runtime reads of the kernel's files "
                                      "no ruling allows")
                runtime = [line for line in outside if self.runtime(line.split(" ", 1)[1])]
                self.assertEqual([line for line in outside if line not in runtime], [], name)

    @staticmethod
    def runtime(path: str) -> bool:
        """Whether ``path`` is one of the reads of Vale's runtime the recorder names."""
        path = re.sub(r"^/proc/\d+/", "/proc/self/", path)
        return any(path == p or p.endswith("/") and path.startswith(p)
                   for p in record.VALE_RUNTIME_READS)


if __name__ == "__main__":
    unittest.main()
