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
import textwrap
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
        # The interpreter's own exit, past the recorder's wrapper of os._exit.
        why = self.refused("import subprocess, sys; subprocess.run([sys.executable, '-c', "
                           "'import os, sys; sys.modules[os.name]._exit(0)'])")
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


class OsExit(unittest.TestCase):
    """COMP_LIFTED_REASONS: what ``os._exit``'s manifest cannot vouch for is refused."""

    setUp, tearDown = test_record.Inputs.setUp, test_record.Inputs.tearDown

    @proves("REQ_LIFT_PROVEN", "REQ_REUSE_SOUND")
    @only_on("posix")
    def test_a_signal_handler_reads_nothing_the_manifest_lacks(self):
        # Moved from test_record: the timer fires every tenth of a millisecond, inside the
        # recorder's own work too, where the handler refuses the run, as it should.
        done, directory = test_record.run_exit(self.root, ["-c", textwrap.dedent("""
            import os, signal
            seen = []

            def handler(*_):
                if not seen:
                    seen.append(1)
                    os.write(1, ("read " + open("a.txt").read()).encode())
            signal.signal(signal.SIGALRM, handler)
            signal.setitimer(signal.ITIMER_REAL, 0.0001, 0.0001)
            os._exit(0)
            """)])
        self.assertEqual(done.returncode, 0, done.stderr)
        m = test_record.manifest_at(directory)
        if "read a" in done.stdout:
            self.assertTrue(not m["storable"] or "a.txt" in m["files"],
                            "the handler's read is in the manifest or refuses the run")

    @proves("REQ_LIFT_PROVEN", "REQ_REUSE_SOUND")
    def test_an_event_past_the_lock_after_the_snapshot_rewrites_the_manifest_as_refused(self):
        done, directory = test_record.run_exit(self.root, ["-c", textwrap.dedent("""
            import os, sys, threading, time
            rec = sys.modules["_trifecta_record"]
            go = threading.Event()

            def late():
                # Past the lock, as a recorder's own work is in this thread.
                for name in ("_trifecta_record", "_trifecta_record_parent"):
                    if name in sys.modules:
                        sys.modules[name]._recorder.local.busy = True
                go.wait()
                open("late.txt", "w").close()
            threading.Thread(target=late, daemon=True).start()
            write = rec._write

            def seam(path, text):
                if path.endswith(".tmp") and not rec._recorder.late:
                    go.set()
                    for _ in range(1000):  # until the event has reached the hook
                        if rec._recorder.late:
                            break
                        time.sleep(0.01)
                write(path, text)
            rec._write = seam
            os._exit(0)
            """)])
        self.assertEqual(done.returncode, 0, done.stderr)
        m = test_record.manifest_at(directory)
        self.assertTrue(record.valid(m))
        self.assertFalse(m["storable"])
        self.assertIn(record.LATE, [r["why"] for r in m["reasons"]])
        self.assertFalse((self.root / "late.txt").exists(), "the open waited for the exit")

    @proves("REQ_LIFT_PROVEN", "REQ_REUSE_SOUND")
    def test_a_process_that_dies_between_the_write_and_the_rename_is_refused(self):
        inner = textwrap.dedent("""
            import os, sys
            rec = sys.modules["_trifecta_record"]
            write = rec._write

            def seam(path, text):
                write(path, text)
                if path.endswith(".tmp"):
                    sys.modules[os.name]._exit(0)  # the interpreter's own: no rename
            rec._write = seam
            os._exit(0)
            """)
        m = run(self.root, f"import subprocess, sys; subprocess.run([sys.executable, '-c', {inner!r}])")
        self.assertFalse(m["storable"])
        self.assertIn("a Python child left no manifest", [r["why"] for r in m["reasons"]])
        (directory,) = sorted(self.root.parent.glob("record-*"))
        (child,) = (directory / "children").iterdir()
        self.assertTrue((child / (record.MANIFEST + ".tmp")).is_file())
        self.assertFalse((child / record.MANIFEST).exists())


class AfterTheManifest(unittest.TestCase):
    """COMP_LIFTED_REASONS: what runs after the manifest is written at a normal exit, and a
    link planted at its temporary name."""

    setUp, tearDown = test_record.Inputs.setUp, test_record.Inputs.tearDown

    def exits(self, code: str, missing: bool = False) -> tuple[subprocess.CompletedProcess,
                                                                dict | None]:
        """The run's output and manifest; with ``missing``, None when it left none, which
        refuses it as much as a refused manifest does."""
        done, directory = test_record.run_exit(self.root, ["-c", textwrap.dedent(code)])
        self.assertEqual(done.returncode, 0, done.stderr)
        if missing and not (directory / record.MANIFEST).exists():
            return done, None
        m = test_record.manifest_at(directory)
        self.assertTrue(record.valid(m))
        return done, m

    @proves("REQ_LIFT_PROVEN", "REQ_REUSE_SOUND")
    def test_a_finalizer_at_teardown_refuses_the_run(self):
        done, m = self.exits("""
            import os

            class Kept:
                def __del__(self, open=open, write=os.write):
                    write(1, ("read " + open("a.txt").read()).encode())
            kept = Kept()
            """)
        self.assertIn("read a", done.stdout, "the finalizer ran at teardown")
        self.assertFalse(m["storable"])
        self.assertIn(record.LATE, [r["why"] for r in m["reasons"]])

    @proves("REQ_LIFT_PROVEN", "REQ_REUSE_SOUND")
    def test_a_cycle_collected_at_teardown_refuses_the_run(self):
        done, m = self.exits("""
            import gc, os

            class Finalized:
                def __del__(self, open=open, write=os.write):
                    write(1, ("read " + open("a.txt").read()).encode())

            def cycle():
                a = Finalized()
                a.self = a
            gc.disable()  # collected only once the interpreter tears down
            cycle()
            """)
        if "read a" in done.stdout:
            self.assertFalse(m["storable"], "the finalizer read after the manifest")
            self.assertIn(record.LATE, [r["why"] for r in m["reasons"]])

    @proves("REQ_LIFT_PROVEN", "REQ_REUSE_SOUND")
    @only_on("posix")
    def test_a_signal_handler_at_exit_reads_nothing_the_manifest_lacks(self):
        done, m = self.exits("""
            import atexit, os, signal
            exiting, seen = [], []

            def handler(*_):
                if exiting and not seen:
                    seen.append(1)
                    signal.setitimer(signal.ITIMER_REAL, 0)  # no alarm left for teardown
                    os.write(1, ("read " + open("a.txt").read()).encode())
            signal.signal(signal.SIGALRM, handler)
            signal.setitimer(signal.ITIMER_REAL, 0.0001, 0.0001)
            atexit.register(exiting.append, 1)  # runs just before the recorder writes
            """)
        if "read a" in done.stdout:
            self.assertTrue(not m["storable"] or "a.txt" in m["files"],
                            "the handler's read is in the manifest or refuses the run")

    @proves("REQ_LIFT_PROVEN", "REQ_REUSE_SOUND")
    def test_a_hook_that_reads_during_the_recorders_write_refuses_the_run(self):
        done, m = self.exits("""
            import os, sys
            seen = []

            def hook(event, args):
                if event == "open" and str(args[0]).endswith(".tmp") and not seen:
                    seen.append(1)  # the recorder writing its manifest
                    os.write(1, ("read " + open("a.txt").read()).encode())
            sys.addaudithook(hook)
            """)
        self.assertIn("read a", done.stdout, "the hook read during the write")
        self.assertFalse(m["storable"])
        self.assertIn("adds an audit hook", [r["why"] for r in m["reasons"]])

    @proves("REQ_LIFT_PROVEN", "REQ_REUSE_SOUND")
    def test_a_signal_another_thread_raises_during_the_write_refuses_the_run(self):
        # SIGINT where the system has no SIGUSR1, as Windows has not.
        for exit_by in ("pass", "os._exit(0)"):
            with self.subTest(exit_by=exit_by):
                done, m = self.exits(missing=True, code=f"""
                    import os, signal, sys, threading
                    number = getattr(signal, "SIGUSR1", signal.SIGINT)
                    go, seen = [], []

                    def handler(*_):
                        f, names = sys._getframe(1), []
                        while f is not None:
                            names.append(f.f_code.co_name)
                            f = f.f_back
                        if "_seal" in names and not seen:  # inside the recorder's write
                            seen.append(1)
                            os.write(1, ("read " + open("a.txt").read()).encode())
                    signal.signal(number, handler)

                    def raising():
                        while not go:
                            pass
                        while not seen:
                            signal.raise_signal(number)
                    threading.Thread(target=raising, daemon=True).start()
                    go.append(1)
                    {exit_by}
                    """)
                if "read a" in done.stdout and m is not None:
                    self.assertFalse(m["storable"], "the handler read inside the write")
                    self.assertIn(record.LATE, [r["why"] for r in m["reasons"]])

    @proves("REQ_LIFT_PROVEN", "REQ_REUSE_SOUND")
    def test_a_handler_given_past_signal_signal_is_still_wrapped(self):
        # Through _signal, which signal.signal calls, and marked as a recorder's own wrapper
        # was once marked: either way the run's handler inside the write refuses the run.
        for install in ("import _signal; _signal.signal(number, handler)",
                        "handler.recorded_handler = True; signal.signal(number, handler)"):
            with self.subTest(install=install):
                done, m = self.exits(missing=True, code=f"""
                    import os, signal, sys, threading
                    number = getattr(signal, "SIGUSR1", signal.SIGINT)
                    go, seen = [], []

                    def handler(*_):
                        f, names = sys._getframe(1), []
                        while f is not None:
                            names.append(f.f_code.co_name)
                            f = f.f_back
                        if "_seal" in names and not seen:
                            seen.append(1)
                            os.write(1, ("read " + open("a.txt").read()).encode())
                    {install}

                    def raising():
                        while not go:
                            pass
                        while not seen:
                            signal.raise_signal(number)
                    threading.Thread(target=raising, daemon=True).start()
                    go.append(1)
                    os._exit(0)
                    """)
                if "read a" in done.stdout and m is not None:
                    self.assertFalse(m["storable"], "the handler read inside the write")

    @proves("REQ_LIFT_PROVEN", "REQ_REUSE_SOUND")
    def test_a_codec_function_dressed_as_the_standard_librarys_is_refused(self):
        for register in ("codecs.register(f)", "codecs.register_error('x-dressed', f)"):
            with self.subTest(register=register):
                done, m = self.exits(f"""
                    import codecs, json, os

                    class Kept:
                        def __del__(self, open=open, write=os.write):
                            write(1, ("read " + open("a.txt").read()).encode())

                    def f(*args, _keep=Kept()):
                        return None
                    f.__module__, f.__qualname__ = "json", "f"  # as json names it
                    json.f = f
                    {register}
                    del json.f, f
                    """)
                self.assertFalse(m["storable"])
                self.assertTrue(any(r["why"].startswith("registers a codec")
                                    for r in m["reasons"]))

    @proves("REQ_LIFT_PROVEN", "REQ_REUSE_SOUND")
    def test_a_refusal_that_cannot_be_written_fails_the_event_and_is_tried_again(self):
        done, m = self.exits("""
            import os, sys
            recorder = sys.modules["_trifecta_record"]._recorder

            class Kept:
                def __del__(self, open=open, write=os.write, recorder=recorder):
                    real = recorder.manifest_path
                    # Neither the rewrite nor the removal can be done at this name.
                    recorder.manifest_path = real + ".missing/manifest.json"
                    try:
                        open("a.txt").read()
                        write(1, b"unblocked ")
                    except BaseException:
                        write(1, b"blocked ")
                    recorder.manifest_path = real
                    write(1, ("read " + open("a.txt").read()).encode())
            kept = Kept()
            """)
        self.assertIn("blocked read a", done.stdout, "the read failed while it could not refuse")
        self.assertNotIn("unblocked", done.stdout)
        self.assertFalse(m["storable"], "the next event refused the run")
        self.assertIn(record.LATE, [r["why"] for r in m["reasons"]])

    @proves("REQ_LIFT_PROVEN", "REQ_REUSE_SOUND")
    def test_a_callable_kept_past_the_audit_hooks_refuses_the_run(self):
        kept = "registers {}, which the interpreter keeps past its audit hooks".format
        cases = [("import codecs; codecs.register(Kept())", kept("a codec search function")),
                 ("import codecs; codecs.register_error('x-kept', Kept())",
                  kept("a codec error handler")),
                 ("import sys; sys.monitoring.use_tool_id(3, 'kept'); "
                  "sys.monitoring.register_callback(3, sys.monitoring.events.PY_START, Kept())",
                  kept("a monitoring callback"))]
        if hasattr(os, "register_at_fork"):
            # The recorder holds a fork callback itself and lets it go once the manifest is
            # written, the hooks still listening: its finalizer refuses the run then.
            cases.append(("os.register_at_fork(before=Kept())", record.LATE))
        for line, why in cases:
            with self.subTest(why=why):
                done, m = self.exits(f"""
                    import os

                    class Kept:
                        def __call__(self, *args, **kwargs):
                            return None

                        def __del__(self, open=open, write=os.write):
                            # Run as the interpreter clears its state, its hooks gone.
                            write(1, ("read " + open("a.txt").read()).encode())
                    {line}
                    """)
                self.assertFalse(m["storable"])
                self.assertIn(why, [r["why"] for r in m["reasons"]])

    @proves("REQ_LIFT_PROVEN", "REQ_REUSE_SOUND")
    def test_a_link_at_the_temporary_name_writes_nothing_through_it(self):
        for kind in ("symlink", "link"):
            with self.subTest(kind=kind):
                victim = self.root / "b.txt"
                directory = self.root.parent / f"record-{len(list(self.root.parent.glob('record-*')))}"
                planted = directory / (record.MANIFEST + ".tmp")
                for exit_by in ("pass", "import os; os._exit(0)"):
                    done, m = self.exits(f"""
                        import os
                        os.{kind}({str(victim)!r}, {str(planted)!r})
                        {exit_by}
                        """)
                    self.assertEqual(victim.read_text(encoding="utf-8"), "b",
                                     "the file the link names is untouched")
                    self.assertFalse(m["storable"])
                    directory = self.root.parent / f"record-{len(list(self.root.parent.glob('record-*')))}"
                    planted = directory / (record.MANIFEST + ".tmp")


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
