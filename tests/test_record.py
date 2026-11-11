"""REQ_REUSE_SOUND: the recorder notes every input a run reads, and marks a run it cannot
follow as one that is never stored.

Each test runs a short Python program in a child, as a recorded run, in a small
repository in a temporary directory, and reads the manifest the child leaves. The
children record themselves through the .pth file setup installs, so these tests run in
the virtual environment setup made.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import textwrap
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

from trifecta import record
from trifecta import setup as setup_module
from trifecta.testing import only_on, proves

REPO = Path(__file__).resolve().parent.parent


def repository(tmp: Path) -> Path:
    root = tmp / "repo"
    (root / "sub" / "deeper").mkdir(parents=True)
    for name, text in (("a.txt", "a"), ("b.txt", "b"), ("c.txt", "c"), ("sub/x.txt", "x"),
                       ("mod_here.py", "VALUE = 1\n")):
        (root / name).write_text(text, encoding="utf-8")
    return root


def run(root: Path, code: str, *flags: str, env: dict | None = None) -> dict:
    """Run ``code`` as a recorded child in ``root``; its manifest."""
    directory = root.parent / f"record-{len(list(root.parent.glob('record-*')))}"
    record.prepare(str(directory), str(root))
    environment = {k: v for k, v in (env if env is not None else os.environ).items()
                   if k not in record.OWN}
    environment[record.ENV] = str(directory)
    subprocess.run([sys.executable, *flags, "-c", textwrap.dedent(code)], cwd=root,
                   env=environment, check=True, capture_output=True)
    return json.loads((directory / record.MANIFEST).read_text(encoding="utf-8"))


class Installed(unittest.TestCase):
    @proves("REQ_REUSE_SOUND")
    def test_the_pth_file_is_installed_in_this_virtual_environment(self):
        self.assertNotEqual(sys.prefix, sys.base_prefix, "the check runs in a virtual environment")
        pth = Path(sysconfig.get_paths()["purelib"]) / record.PTH_NAME
        self.assertEqual(pth.read_text(encoding="utf-8"), record.PTH_LINE)

    @proves("REQ_REUSE_SOUND")
    def test_the_pth_line_imports_nothing_when_the_variable_is_unset(self):
        env = {k: v for k, v in os.environ.items() if k not in record.OWN}
        # site, which reads .pth files, has imported os by then.
        code = ("import os, sys; before = set(sys.modules); exec(LINE); "
                "print(sorted(set(sys.modules) - before))")
        out = subprocess.run([sys.executable, "-S", "-c", f"LINE = {record.PTH_LINE!r}; {code}"],
                             env=env, capture_output=True, encoding="utf-8", check=True).stdout
        self.assertEqual(out.strip(), "[]")


class SetupInstalls(unittest.TestCase):
    def install(self, purelib: Path, in_venv: bool) -> tuple[Path | None, str]:
        err = io.StringIO()
        base = "/elsewhere" if in_venv else sys.prefix
        with mock.patch.object(sys, "base_prefix", base), \
                mock.patch.object(setup_module.sysconfig, "get_paths",
                                  return_value={"purelib": str(purelib)}), \
                redirect_stderr(err):
            target = setup_module.install_recorder()
        return target, err.getvalue()

    @proves("REQ_REUSE_SOUND")
    def test_setup_writes_the_pth_file_in_a_virtual_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            target, err = self.install(Path(tmp), in_venv=True)
            self.assertEqual(target, Path(tmp) / record.PTH_NAME)
            self.assertEqual(target.read_bytes(), record.PTH_LINE.encode("utf-8"))
        self.assertEqual(err, "")

    @proves("REQ_REUSE_SOUND")
    def test_setup_outside_a_virtual_environment_writes_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            target, err = self.install(Path(tmp), in_venv=False)
            self.assertIsNone(target)
            self.assertEqual(list(Path(tmp).iterdir()), [])
        self.assertIn("not in a virtual environment", err)


class Inputs(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.root = repository(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    @proves("REQ_REUSE_SOUND")
    def test_reads_copies_and_own_writes(self):
        m = run(self.root, """
            import shutil
            open("a.txt").read()
            shutil.copy2("b.txt", "b-copy.txt")
            with open("made.txt", "w") as f:
                f.write("mine")
            open("made.txt").read()
            """)
        self.assertTrue(m["storable"], m.get("why"))
        self.assertIn("a.txt", m["files"])
        self.assertIn("b.txt", m["files"], "a copy's source is read")
        self.assertNotIn("made.txt", m["files"], "a file the run wrote is no input")
        self.assertNotIn("b-copy.txt", m["files"])

    @proves("REQ_REUSE_SOUND")
    def test_the_locales_variables_are_recorded_set_or_not(self):
        env = {k: v for k, v in os.environ.items() if k not in record.LOCALE_VARIABLES}
        m = run(self.root, "pass", env=env)
        for name in record.LOCALE_VARIABLES:
            self.assertIn(name, m["environment"])
            self.assertIsNone(m["environment"][name])

    @proves("REQ_REUSE_SOUND")
    def test_a_directory_the_run_made_is_no_entry_of_a_listing(self):
        (self.root / "sub" / "there").mkdir()
        m = run(self.root, """
            import os
            os.mkdir("sub/made")
            os.mkdir("sub/there") if not os.path.isdir("sub/there") else None
            os.listdir("sub")
            """)
        self.assertTrue(m["storable"], m.get("why"))
        names = [e[0] for e in m["listings"]["sub"]]
        self.assertNotIn("made", names)
        self.assertIn("there", names, "a directory there before the run is an entry")

    @proves("REQ_REUSE_SOUND")
    def test_listings_carry_their_kinds(self):
        m = run(self.root, "import os; os.listdir('sub'); list(os.scandir('.'))")
        self.assertEqual(m["listings"]["sub"], [["deeper", "directory"], ["x.txt", "file"]])
        self.assertIn(["a.txt", "file"], m["listings"]["."])

    @proves("REQ_REUSE_SOUND")
    def test_every_wrapped_probe_records_its_kind(self):
        probes = ["os.stat", "os.lstat", "os.access", "os.readlink", "os.path.exists",
                  "os.path.isfile", "os.path.isdir", "os.path.islink", "os.path.lexists",
                  "os.path.isjunction", "os.path.realpath"]
        for probe in probes:
            for path, kind in (("a.txt", "file"), ("sub", "directory"), ("gone", "absent")):
                with self.subTest(probe=probe, path=path):
                    args = f"{path!r}, os.R_OK" if probe == "os.access" else repr(path)
                    m = run(self.root, f"""
                        import os
                        try:
                            {probe}({args})
                        except OSError:
                            pass
                        """)
                    self.assertTrue(m["storable"], m.get("why"))
                    self.assertEqual(m["probes"].get(path), kind)

    @proves("REQ_REUSE_SOUND")
    def test_a_directory_entrys_status_is_a_read(self):
        m = run(self.root, "import os; [e.stat().st_size for e in os.scandir('sub')]")
        self.assertTrue(m["storable"], m.get("why"))
        self.assertIn("sub/x.txt", m["files"])

    @proves("REQ_REUSE_SOUND")
    def test_what_a_child_wrote_is_no_input_to_its_parent(self):
        m = run(self.root, """
            import subprocess, sys
            subprocess.run([sys.executable, "-c", "open('by-child.txt', 'w').write('x')"],
                           check=True)
            open("by-child.txt").read()
            """)
        self.assertTrue(m["storable"], m.get("why"))
        self.assertNotIn("by-child.txt", m["files"])

    @proves("REQ_REUSE_SOUND")
    def test_a_file_read_before_the_run_replaced_it_is_an_input(self):
        m = run(self.root, """
            import os
            open("a.txt").read()
            with open("a.tmp", "w") as f:
                f.write("new")
            os.replace("a.tmp", "a.txt")
            open("b.txt").read()
            os.rename("b.txt", "b-moved.txt")
            """)
        self.assertTrue(m["storable"], m.get("why"))
        self.assertIn("a.txt", m["files"])
        self.assertIn("b.txt", m["files"])

    @proves("REQ_REUSE_SOUND")
    def test_a_variable_the_run_gives_a_child_is_its_own(self):
        m = run(self.root, """
            import os, subprocess, sys
            env = {**os.environ, "TRIFECTA_TEST_GIVEN": "1"}
            subprocess.run([sys.executable, "-c",
                            "import os; os.environ['TRIFECTA_TEST_GIVEN']"], env=env, check=True)
            """)
        self.assertTrue(m["storable"], m.get("why"))
        self.assertNotIn("TRIFECTA_TEST_GIVEN", m["environment"])

    @proves("REQ_REUSE_SOUND")
    @only_on("posix")
    def test_a_listing_through_a_link_it_did_not_make(self):
        os.symlink(self.tmp, self.root / "elsewhere")
        why = self.refused_in(self.root, "import os; os.listdir('elsewhere')")
        self.assertIn("through a link", why)

    @proves("REQ_REUSE_SOUND")
    @only_on("posix")
    def test_rmtree_keeps_its_link_safe_path(self):
        m = run(self.root, "import shutil, sys; "
                           "sys.exit(0 if shutil.rmtree.avoids_symlink_attacks else 3)")
        self.assertTrue(m["storable"], m.get("why"))

    def refused_in(self, root: Path, code: str) -> str:
        m = run(root, code)
        self.assertFalse(m["storable"])
        return m["why"]

    @proves("REQ_REUSE_SOUND")
    @only_on("posix")
    def test_a_read_through_a_link_the_run_made_reads_its_target(self):
        m = run(self.root, """
            import os, tempfile
            link = os.path.join(tempfile.mkdtemp(), "link")
            os.symlink(os.path.abspath("b.txt"), link)
            open(link).read()
            """)
        self.assertTrue(m["storable"], m.get("why"))
        self.assertIn("b.txt", m["files"])

    @proves("REQ_REUSE_SOUND")
    def test_environment_reads_and_iteration(self):
        env = {**os.environ, "TRIFECTA_TEST_READ": "1", "TRIFECTA_TEST_OTHER": "2"}
        m = run(self.root, "import os; os.environ.get('TRIFECTA_TEST_READ'); "
                           "os.environ.get('TRIFECTA_TEST_UNSET')", env=env)
        self.assertIn("TRIFECTA_TEST_READ", m["environment"])
        self.assertIsNone(m["environment"]["TRIFECTA_TEST_UNSET"])
        self.assertNotIn("TRIFECTA_TEST_OTHER", m["environment"])
        m = run(self.root, "import os; dict(os.environ)", env=env)
        self.assertIn("TRIFECTA_TEST_OTHER", m["environment"])
        for own in record.OWN:
            self.assertNotIn(own, m["environment"])
        self.assertNotIn("1", m["environment"].values(), "values are recorded as hashes")

    @proves("REQ_REUSE_SOUND")
    def test_imported_module_sources_and_lookups(self):
        m = run(self.root, "import mod_here\ntry:\n    import not_here\nexcept ImportError:\n    pass")
        self.assertIn("mod_here.py", m["files"])
        self.assertEqual(m["lookups"].get("./mod_here"), "mod_here.py")
        self.assertIn("./not_here", m["lookups"])
        self.assertIsNone(m["lookups"]["./not_here"])
        self.assertNotIn(".", m["listings"], "the import system's listing is recorded by name")

    @proves("REQ_REUSE_SOUND")
    def test_python_child_reads_under_e_and_i(self):
        for flag in ("-E", "-I"):
            with self.subTest(flag=flag):
                m = run(self.root, f"""
                    import subprocess, sys
                    subprocess.run([sys.executable, "{flag}", "-c", "open('c.txt').read()"],
                                   check=True)
                    """)
                self.assertTrue(m["storable"], m.get("why"))
                self.assertIn("c.txt", m["files"])


class Unstorable(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.root = repository(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def refused(self, code: str) -> str:
        m = run(self.root, code)
        self.assertFalse(m["storable"])
        return m["why"]

    @proves("REQ_REUSE_SOUND")
    def test_child_with_dash_s(self):
        why = self.refused("import subprocess, sys; "
                           "subprocess.run([sys.executable, '-S', '-c', 'pass'], check=True)")
        self.assertIn("-S", why)

    @proves("REQ_REUSE_SOUND")
    def test_child_with_dash_s_after_an_option_value(self):
        why = self.refused("import subprocess, sys; subprocess.run([sys.executable, '-X', "
                           "'utf8', '-S', '-c', 'pass'], check=True)")
        self.assertIn("-S", why)

    @proves("REQ_REUSE_SOUND")
    def test_a_process_started_other_than_through_subprocess(self):
        why = self.refused("""
            import multiprocessing, os
            if __name__ == "__main__":
                p = multiprocessing.get_context("spawn").Process(target=os.getpid)
                p.start(); p.join()
            """)
        self.assertIn("other than through subprocess", why)

    @proves("REQ_REUSE_SOUND")
    def test_moving_a_directory_it_did_not_make(self):
        self.assertIn("moves a directory", self.refused("import os; os.rename('sub', 'moved')"))

    @proves("REQ_REUSE_SOUND")
    @only_on("posix")
    def test_a_path_relative_to_a_descriptor(self):
        why = self.refused("""
            import os
            fd = os.open(".", os.O_RDONLY)
            os.close(os.open("a.txt", os.O_RDONLY, dir_fd=fd))
            """)
        self.assertIn("descriptor", why)

    @proves("REQ_REUSE_SOUND")
    def test_listing_a_directory_that_holds_the_repository(self):
        self.assertIn("holds the repository", self.refused("import os; os.listdir('..')"))

    @proves("REQ_REUSE_SOUND")
    def test_child_leaving_no_manifest(self):
        why = self.refused("import subprocess, sys; subprocess.run([sys.executable, '-c', "
                           "'import os; os._exit(0)'])")
        self.assertIn("no manifest", why)

    @proves("REQ_REUSE_SOUND")
    def test_socket_connect(self):
        why = self.refused("""
            import socket
            server = socket.socket(); server.bind(("127.0.0.1", 0)); server.listen()
            client = socket.socket()
            client.connect(server.getsockname())
            """)
        self.assertIn("network", why)

    @proves("REQ_REUSE_SOUND")
    def test_change_of_working_directory(self):
        self.assertIn("working directory", self.refused("import os; os.chdir('sub')"))

    @proves("REQ_REUSE_SOUND")
    def test_unlisted_audit_event(self):
        self.assertIn("trifecta.unlisted", self.refused("import sys; sys.audit('trifecta.unlisted')"))

    @proves("REQ_REUSE_SOUND")
    def test_git_and_other_programs(self):
        self.assertIn("git", self.refused("import subprocess; "
                                          "subprocess.run(['git', '--version'], capture_output=True)"))
        other = [shutil.which("cmd"), "/c", "exit"] if os.name == "nt" else [shutil.which("true")]
        why = self.refused(f"import subprocess; subprocess.run({other!r}, capture_output=True, "
                           "stdin=subprocess.DEVNULL)")
        self.assertIn("runs ", why)


GOOD = {"version": 1, "storable": True,
        "files": {"docs/a.md": "0" * 64}, "probes": {"gone": "absent"},
        "listings": {"docs": [["a.md", "file"]]}, "lookups": {"./mod": "mod.py"},
        "environment": {"HOME": None}, "outside": {}}


class Shape(unittest.TestCase):
    @proves("REQ_REUSE_SOUND")
    def test_a_manifest_from_elsewhere_is_held_to_its_shape(self):
        self.assertTrue(record.valid(GOOD))
        bad = [
            {"version": True}, {"storable": 1}, {"why": "no"}, {"extra": {}},
            {"files": {"../outside": "0" * 64}}, {"files": {"/abs": "0" * 64}},
            {"files": {"C:/x": "0" * 64}}, {"files": {"a\\b": "0" * 64}},
            {"files": {"a": "not a hash"}}, {"outside": {"relative": "0" * 64}},
            {"probes": {"a": "socket"}}, {"listings": {"d": [["a/b", "file"]]}},
            {"lookups": {"./not a name": None}}, {"lookups": {"./m": "/abs/m.py"}},
            {"environment": {"HOME": "the value itself"}}, {"environment": {"A=B": None}},
        ]
        for change in bad:
            with self.subTest(change=change):
                self.assertFalse(record.valid({**GOOD, **change}))
        self.assertFalse(record.valid({**GOOD, "storable": False, "why": 3}))
        self.assertTrue(record.valid({**GOOD, "storable": False, "why": "runs git"}))
        # The interpreter's own _sysconfigdata module on Linux has dashes in its name.
        self.assertTrue(record.valid(
            {**GOOD, "lookups": {"./_sysconfigdata__linux_x86_64-linux-gnu": None}}))


def short_name(path: Path) -> str | None:
    """``path``'s 8.3 short spelling, or None where the volume makes none."""
    import ctypes
    buffer = ctypes.create_unicode_buffer(32768)
    n = ctypes.windll.kernel32.GetShortPathNameW(str(path), buffer, 32768)
    return buffer.value if 0 < n < 32768 and buffer.value != str(path) else None


class ShortNames(unittest.TestCase):
    """Where 8.3 short names are on, as on the Windows runner, one directory has two
    spellings: a run's own output is no input under either."""

    def setUp(self):
        if os.name != "nt":
            self.skipTest("8.3 short names are Windows's")
        self.tmp = Path(tempfile.mkdtemp()).resolve() / "a long directory name"
        self.tmp.mkdir()
        self.addCleanup(shutil.rmtree, self.tmp.parent, True)
        self.root = repository(self.tmp)
        self.short = short_name(self.tmp)
        if self.short is None:
            self.skipTest("this volume makes no short names")

    @proves("REQ_REUSE_SOUND")
    @only_on("nt")
    def test_what_the_run_made_under_a_short_name_is_no_input_under_the_long(self):
        m = run(self.root, f"""
            import os
            made = os.path.join({self.short!r}, "made")
            os.mkdir(made)
            with open(os.path.join(made, "x.json"), "w") as f:
                f.write("mine")
            open(os.path.join({str(self.tmp)!r}, "made", "x.json")).read()
            open("a.txt").read()
            """)
        self.assertTrue(m["storable"], m.get("why"))
        self.assertEqual(m["outside"], {})
        self.assertIn("a.txt", m["files"])


class Portable(unittest.TestCase):
    @proves("REQ_REUSE_SOUND")
    def test_same_run_in_two_copies_gives_the_same_manifest(self):
        code = """
            import os, mod_here
            open("a.txt").read(); os.listdir("sub"); os.path.exists("gone")
            os.environ.get("PYTHONPATH")
            """
        manifests = []
        with tempfile.TemporaryDirectory() as one, tempfile.TemporaryDirectory() as two:
            for tmp in (one, two):
                root = repository(Path(tmp).resolve() / "deeper" / os.path.basename(tmp))
                env = {**os.environ, "PYTHONPATH": str(root)}
                manifests.append(run(root, code, env=env))
        self.assertTrue(manifests[0]["storable"], manifests[0].get("why"))
        self.assertEqual(manifests[0], manifests[1])
        # Read by the interpreter as it started, before any code of the run.
        self.assertIn("PYTHONPATH", manifests[0]["environment"])
