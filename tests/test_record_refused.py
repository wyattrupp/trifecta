"""REQ_REUSE_SOUND, REQ_REFUSALS_NAMED, REQ_HOST_READS: the recorder's tests that are
refused on purpose, moved from ``test_record`` unchanged (COMP_LIFTED_REASONS): its ``-S``
test, its tests whose children do a refused thing on purpose, its Windows ctypes test, and
its test of two copies, whose ``PYTHONPATH`` names a copy outside the repository (wyatt,
2026-11-13: "Move it too (Recommended)").

Each refuses the run of this module under its own recorder, as it exists to, so this
module is never stored, and ``test_record``, which keeps the rest, is.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from trifecta import record, store
from trifecta.testing import only_on, proves

from tests import test_record
from tests.test_record import controlled_env, executable_name, repository, run


class Installed(unittest.TestCase):
    @proves("REQ_REUSE_SOUND")
    def test_the_pth_line_imports_nothing_when_the_variable_is_unset(self):
        env = {k: v for k, v in os.environ.items() if k not in record.OWN}
        # site, which reads .pth files, has imported os by then.
        code = ("import os, sys; before = set(sys.modules); exec(LINE); "
                "print(sorted(set(sys.modules) - before))")
        for _, line in record.PTH_FILES:
            out = subprocess.run([sys.executable, "-S", "-c", f"LINE = {line!r}; {code}"],
                                 env=env, capture_output=True, encoding="utf-8",
                                 check=True).stdout
            self.assertEqual(out.strip(), "[]")


class Inputs(unittest.TestCase):
    setUp, tearDown = test_record.Inputs.setUp, test_record.Inputs.tearDown
    refused_in = test_record.Inputs.refused_in

    @proves("REQ_REUSE_SOUND")
    @only_on("posix")
    def test_a_link_the_run_makes_reaches_only_what_it_made(self):
        m = run(self.root, """
            import os, tempfile
            made = tempfile.mkdtemp()
            with open(os.path.join(made, "a.txt"), "w") as f:
                f.write("a")
            link = os.path.join(made, "link")
            os.symlink("a.txt", link)
            open(link).read()
            """)
        self.assertTrue(m["storable"], m.get("why"))
        # A link to what the run did not make would let a read under a directory it made
        # reach a file no key holds, as through a linked directory: refused.
        for target in ("os.path.abspath('b.txt')", "os.path.abspath('sub')"):
            with self.subTest(target=target):
                why = self.refused_in(self.root, f"""
                    import os, tempfile
                    made = tempfile.mkdtemp()
                    os.symlink({target}, os.path.join(made, "link"))
                    open(os.path.join(made, "link", "x.txt") if 'sub' in {target!r}
                         else os.path.join(made, "link")).read()
                    """)
                self.assertIn("makes a link to outside what the run made", why)

    @proves("REQ_REUSE_SOUND")
    @only_on("posix")
    def test_a_device_is_held_by_its_kind_never_read(self):
        m = run(self.root, "import os; os.stat('/dev/urandom'); os.lstat('/dev/zero'); "
                           "open('/dev/urandom', 'rb').read(8)")
        self.assertTrue(m["storable"], m.get("why"))
        self.assertNotIn("/dev/urandom", m["outside"])
        self.assertEqual(m["probes"]["/dev/urandom"], "device")
        self.assertEqual(m["probes"]["/dev/zero"], "device")
        # Any other device read could be fed what no key holds: refused.
        why = self.refused_in(self.root, "open('/dev/zero', 'rb').read(8)")
        self.assertIn("which is not a regular file", why)


class Unstorable(unittest.TestCase):
    setUp, tearDown = test_record.Unstorable.setUp, test_record.Unstorable.tearDown
    refused = test_record.Unstorable.refused

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
    @only_on("posix")
    def test_a_path_relative_to_a_descriptor(self):
        why = self.refused("""
            import os
            fd = os.open(".", os.O_RDONLY)
            os.close(os.open("a.txt", os.O_RDONLY, dir_fd=fd))
            """)
        self.assertIn("descriptor", why)

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


class HostName(unittest.TestCase):
    setUp, tearDown = test_record.HostName.setUp, test_record.HostName.tearDown

    @proves("REQ_HOST_READS", "REQ_REUSE_SOUND")
    @only_on("posix")
    def test_a_fresh_posix_is_refused(self):
        routes = {
            "import": "import sys; del sys.modules['posix']; import posix",
            "import_module": "import importlib, sys; del sys.modules['posix']; "
                             "posix = importlib.import_module('posix')",
            "module_from_spec": "import importlib.util; spec = importlib.util.find_spec("
                                "'posix'); posix = importlib.util.module_from_spec(spec); "
                                "spec.loader.exec_module(posix)",
            # Made and not run, the module crashes the interpreter when used.
            "create_builtin": "import _imp, posix; "
                              "posix = _imp.create_builtin(posix.__spec__); "
                              "_imp.exec_builtin(posix)",
            "_load": "import importlib._bootstrap as b, posix; "
                     "posix = b._load(posix.__spec__)",
        }
        for route, code in routes.items():
            with self.subTest(route=route):
                m = run(self.root, code + "\n" + "posix.uname()")
                self.assertFalse(m["storable"])
                self.assertIn("imports posix again", m["why"])

    @proves("REQ_HOST_READS", "REQ_REUSE_SOUND")
    @only_on("posix")
    def test_a_name_that_is_not_a_str_is_refused(self):
        m = run(self.root, """
            import _imp, posix
            class Name(str):
                __hash__ = lambda self: 1
                __eq__ = lambda self, other: False
            class Spec:
                name = Name("posix")
                origin = "built-in"
            made = _imp.create_builtin(Spec())
            _imp.exec_builtin(made)
            made.uname()
            """)
        self.assertFalse(m["storable"])
        self.assertIn("a name that is not a str", m["why"])

    @proves("REQ_REUSE_SOUND")
    def test_another_interpreter_is_refused(self):
        m = run(self.root, """
            try:
                import _interpreters as interpreters
            except ImportError:
                try:
                    import _xxsubinterpreters as interpreters
                except ImportError:
                    interpreters = None
            if interpreters is None:
                open("no-interpreters", "w").close()
            else:
                interpreters.destroy(interpreters.create())
            """)
        if (self.root / "no-interpreters").exists():
            self.skipTest("this Python has no module that starts an interpreter")
        self.assertFalse(m["storable"])
        self.assertIn("starts another interpreter", m["why"])

    @proves("REQ_HOST_READS", "REQ_REUSE_SOUND")
    def test_socket_gethostname_is_refused(self):
        m = run(self.root, "import socket; socket.gethostname()")
        self.assertFalse(m["storable"])
        self.assertIn("host name", m["why"])


class Reasons(unittest.TestCase):
    setUp, tearDown = test_record.Reasons.setUp, test_record.Reasons.tearDown

    @proves("REQ_REFUSALS_NAMED")
    def test_a_reason_in_the_process_and_one_in_a_child_are_both_named(self):
        m = run(self.root, """
            import os, subprocess, sys
            os.chdir("sub"); os.chdir("..")
            subprocess.run([sys.executable, "-E", "-m", "kid", "--secret-argument"],
                           check=True)
            """, env=controlled_env())
        self.assertFalse(m["storable"])
        python = executable_name()
        self.assertEqual(m["reasons"], [
            {"process": None, "why": "changes the working directory"},
            {"process": f"{python} -m kid", "why": "reads the host name"},
            {"process": f"{python} -m kid > {python}", "why": "changes the working directory"},
        ])
        self.assertEqual(m["why"], m["reasons"][0]["why"], "why stays the first")
        self.assertNotIn("secret-argument", json.dumps(m["reasons"]))

    @proves("REQ_REFUSALS_NAMED")
    def test_the_childs_reason_comes_after_the_processs_own(self):
        # The child refuses first in time; its manifest is taken in at the parent's exit,
        # as before, so ``why`` is the one the parent raised itself.
        m = run(self.root, """
            import os, subprocess, sys
            subprocess.run([sys.executable, "-m", "kid"], check=True)
            import socket; socket.gethostname()
            os.chdir("sub"); os.chdir("..")
            """, env=controlled_env())
        self.assertEqual(m["why"], "reads the host name")
        self.assertEqual([r["process"] for r in m["reasons"]],
                         [None, None, f"{executable_name()} -m kid",
                          f"{executable_name()} -m kid > {executable_name()}"])

    @proves("REQ_REFUSALS_NAMED")
    def test_reasons_are_bounded_as_why_is(self):
        m = run(self.root, f"""
            import subprocess
            for name in [f"no-such-program-{{i}}" for i in range(80)] + ["p" * 5000]:
                try:
                    subprocess.run([name], capture_output=True)
                except (OSError, ValueError):
                    pass
            """)
        self.assertEqual(len(m["reasons"]), record.MAX_REASONS)
        self.assertEqual(m["reasons"][0], {"process": None, "why": "runs no-such-program-0"})
        self.assertTrue(record.valid(m))
        m = run(self.root, """
            import subprocess
            try:
                subprocess.run(["p" * 5000], capture_output=True)
            except (OSError, ValueError):
                pass
            """)
        self.assertEqual(len(m["why"]), record.MAX_TEXT)
        self.assertTrue(record.valid(m))

    @proves("REQ_REFUSALS_NAMED")
    def test_a_reason_holds_no_environment_value(self):
        m = run(self.root, """
            import os, subprocess
            try:
                subprocess.run([os.environ["TRIFECTA_DEMO_TOOL"]], capture_output=True)
            except OSError:
                pass
            """, env={**os.environ, "TRIFECTA_DEMO_TOOL": "secret-tool-value"})
        self.assertFalse(m["storable"])
        self.assertNotIn("secret-tool-value", json.dumps(m))
        self.assertEqual(m["why"], "runs <env:TRIFECTA_DEMO_TOOL>")

    @proves("REQ_REFUSALS_NAMED")
    def test_naming_reasons_changes_nothing_about_storing(self):
        stored = run(self.root, """
            import subprocess, sys
            open("a.txt").read()
            subprocess.run([sys.executable, "-c", "open('b.txt').read()"], check=True)
            """)
        self.assertTrue(stored["storable"], stored.get("why"))
        self.assertNotIn("reasons", stored)
        self.assertIn("b.txt", stored["files"])
        # Once refused, the run notes reasons only: what it reads after is no input, and
        # the store keeps no refused manifest whatever reasons it holds.
        refused = run(self.root, """
            import os, subprocess, sys
            open("a.txt").read()
            os.chdir("sub"); os.chdir("..")
            open("c.txt").read()
            subprocess.run([sys.executable, "-c", "open('b.txt').read()"], check=True)
            """)
        self.assertFalse(refused["storable"])
        self.assertIn("a.txt", refused["files"])
        self.assertNotIn("c.txt", refused["files"])
        self.assertNotIn("b.txt", refused["files"])
        shelf = store.Store(self.tmp / "store", self.root)
        self.assertFalse(shelf.put("0" * 64, refused, {}))
        self.assertFalse(shelf.put("0" * 64, {**stored, "reasons": refused["reasons"]}, {}))
        self.assertTrue(shelf.put("0" * 64, stored, {}))


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
