"""REQ_NESTED_RECORDING, REQ_REUSE_SOUND: a Python child that runs a recorder of its own
is recorded by its parent's recorder (COMP_NESTED_RECORDER), and the ways around a
wrapper DEC_0035 accepts stay as listed.

Each test runs a recorded child that starts a Python child recording into a directory of
its own. Run as a proof module, under the module's own recorder, that is three recorders
deep, which the design refuses, so this module is never stored.
"""

from __future__ import annotations

import inspect
import json
import os
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import textwrap
import unittest
from pathlib import Path

from trifecta import record, store
from trifecta.testing import only_on, proves

from tests.test_record import executable_name, repository, run

def nested(root: Path, inner: str, ignore=(), env: dict | None = None,
           before: str = "") -> tuple[dict, dict]:
    """Run ``inner`` in a Python child that records into a directory of its own, as a test
    of the recorder or the store starts one, from a recorded child that runs ``before``
    first: the recorded child's manifest, which holds the inner child's as its parent's
    recorder saw it, and the manifest the inner child's own recorder wrote."""
    n = len(list(root.parent.glob("outer-*")))
    outer, own = root.parent / f"outer-{n}", root.parent / f"own-{n}"
    record.prepare(str(own), str(root), ignore=[str(p) for p in ignore])
    record.prepare(str(outer), str(root), ignore=[str(own)])
    code = (f"import os, subprocess, sys\n{textwrap.dedent(before)}\n"
            f"os.environ[{record.ENV!r}] = {str(own)!r}\n"
            f"subprocess.run([sys.executable, '-c', {textwrap.dedent(inner)!r}], check=True)\n")
    # Without the search path this process has, as the fixture runner gives it: its entries
    # lie in the repository, which is outside the root this test gives both recorders.
    environment = {k: v for k, v in (env if env is not None else os.environ).items()
                   if k not in record.OWN and k.upper() != record.PATH_ENV}
    environment[record.ENV] = str(outer)
    subprocess.run([sys.executable, "-c", code], cwd=root, env=environment, check=True,
                   capture_output=True)
    load = lambda d: json.loads((d / record.MANIFEST).read_text(encoding="utf-8"))
    return load(outer), load(own)


def processes(m: dict) -> list[tuple[str | None, str]]:
    """Each reason of a manifest as ``(process, why)``."""
    return [(r["process"], r["why"]) for r in m.get("reasons", [])]


def whys(m: dict) -> list[str]:
    """Each reason of a manifest, without its process."""
    return [r["why"] for r in m.get("reasons", [])]


class _TmpRepo(unittest.TestCase):
    """A test with a small repository in a temporary directory of its own."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.root = repository(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class Nested(_TmpRepo):
    """COMP_NESTED_RECORDER: a Python child that runs a recorder of its own is recorded by
    its parent's recorder, which starts first under a name and a variable of its own."""

    @proves("REQ_NESTED_RECORDING")
    def test_the_parents_pth_file_sorts_first_and_loads_under_its_own_name(self):
        names = [name for name, _ in record.PTH_FILES]
        self.assertEqual(names, sorted(names))
        self.assertEqual(names[0], record.PARENT_PTH_NAME)
        purelib = Path(sysconfig.get_paths()["purelib"])
        for name, line in record.PTH_FILES:
            self.assertEqual((purelib / name).read_text(encoding="utf-8"), line)
        self.assertIn(record.PARENT_ENV, record.PARENT_PTH_LINE)
        self.assertIn(f'"{record.PARENT_MODULE}"', record.PARENT_START_SOURCE)
        self.assertNotIn(f'"{record.MODULE}"', record.PARENT_START_SOURCE)
        self.assertIn(record.PARENT_ENV, record.PARENT_START_SOURCE)

    @proves("REQ_NESTED_RECORDING", "REQ_REUSE_SOUND")
    def test_a_child_that_records_itself_is_recorded_by_its_parent(self):
        outer, own = nested(self.root, "open('a.txt').read()")
        self.assertTrue(outer["storable"], processes(outer))
        self.assertIn("a.txt", outer["files"])
        self.assertTrue(own["storable"], processes(own))
        self.assertIn("a.txt", own["files"])

    @proves("REQ_NESTED_RECORDING", "REQ_REUSE_SOUND")
    def test_the_childs_own_manifest_never_stands_for_it(self):
        # The test chose the child's recorder's ignore list; the parent's keeps its own.
        outer, own = nested(self.root, "open('sub/x.txt').read()", ignore=[self.root / "sub"])
        self.assertTrue(outer["storable"], processes(outer))
        self.assertIn("sub/x.txt", outer["files"])
        self.assertNotIn("sub/x.txt", own["files"])

    @proves("REQ_NESTED_RECORDING", "REQ_REUSE_SOUND")
    def test_a_variable_the_child_reads_reaches_both_recorders(self):
        env = {**os.environ, "TRIFECTA_TEST_NESTED": "value"}
        outer, _ = nested(self.root, "pass", env=env)
        self.assertNotIn("TRIFECTA_TEST_NESTED", outer["environment"])
        outer, own = nested(self.root, "import os; os.environ.get('TRIFECTA_TEST_NESTED')",
                            env=env)
        self.assertTrue(outer["storable"], processes(outer))
        self.assertIsNotNone(outer["environment"]["TRIFECTA_TEST_NESTED"])
        self.assertEqual(outer["environment"]["TRIFECTA_TEST_NESTED"],
                         own["environment"]["TRIFECTA_TEST_NESTED"])

    @proves("REQ_REUSE_SOUND")
    def test_a_change_to_an_input_the_child_read_reruns_the_run(self):
        env = {**os.environ, "TRIFECTA_TEST_NESTED": "value"}
        outer, _ = nested(self.root, """
            import os
            open('a.txt').read(); os.environ.get('TRIFECTA_TEST_NESTED')
            """, env=env)
        self.assertTrue(outer["storable"], processes(outer))
        shelf = store.Store(self.tmp / "store", self.root)
        ident = shelf.identity("tests", {"module": "tests.test_nested", "leave_out": []})
        self.assertTrue(shelf.put(ident, outer, "result"))
        lookup = lambda environ: shelf.lookup(ident, environ, store.Hashes(),
                                              lambda result: result == "result")
        self.assertEqual(lookup(env), ("result", ""))
        self.assertIsNone(lookup({**env, "TRIFECTA_TEST_NESTED": "other"})[0])
        (self.root / "a.txt").write_text("changed", encoding="utf-8")
        self.assertIsNone(lookup(env)[0])

    @proves("REQ_NESTED_RECORDING")
    def test_the_parents_wrappers_are_innermost(self):
        nested(self.root, """
            import json, os, subprocess
            def chain(f):
                out = []
                while f is not None:
                    out.append(getattr(f, "__module__", None))
                    f = getattr(f, "__wrapped__", None)
                return out
            with open("chain.json", "w") as f:
                json.dump([chain(subprocess.Popen._execute_child), chain(os.stat)], f)
            """)
        execute_child, stat = json.loads((self.root / "chain.json").read_text("utf-8"))
        self.assertEqual(execute_child, [record.MODULE, record.PARENT_MODULE, "subprocess"])
        self.assertEqual(stat[:2], [record.MODULE, record.PARENT_MODULE])
        self.assertEqual(len(stat), 3)

    @proves("REQ_NESTED_RECORDING", "REQ_REUSE_SOUND")
    def test_the_parents_wrapper_judges_the_final_start(self):
        # A wrapper the child installs after both recorders runs first: what it changes
        # reaches the parent's wrapper, which runs last. A wrapper no recorder installed
        # is refused as a replacement, whatever its ``__wrapped__`` says; the child it
        # starts is still recorded, so no reason says a child left no manifest.
        wrap = """
            import os, subprocess, sys
            original = subprocess.Popen._execute_child
            def execute_child(self, args, executable, *rest):
                rest = list(rest)
                env_at = {at}
                rest[env_at] = {{k: v for k, v in (rest[env_at] or os.environ).items()
                                 if k.upper() != "{parent}"}}
                {change}
                return original(self, args, executable, *rest)
            execute_child.__wrapped__ = original  # a wrapper that keeps the chain
            subprocess.Popen._execute_child = execute_child
            subprocess.run([sys.executable, "-c", "open('a.txt').read()"],
                           env={{**os.environ, "{parent}": "elsewhere"}}, check=True)
            """
        names = list(inspect.signature(subprocess.Popen._execute_child).parameters)
        at = names.index("env") - 3  # less self, args and executable
        python = executable_name()
        for name, change, refused in (
                ("drops the variable", "", None),
                ("adds -S", "args = [args[0], '-S', *args[1:]]",
                 "starts a Python child with -S, which runs no .pth file"),
                ("sets the variable", f"rest[env_at]['{record.PARENT_ENV}'] = 'elsewhere'",
                 f"starts a Python child whose environment already holds "
                 f"{record.PARENT_ENV}")):
            with self.subTest(name):
                outer, _ = nested(self.root, wrap.format(at=at, parent=record.PARENT_ENV,
                                                         change=change))
                replaced = "replaces what the recorder installed: Popen._execute_child"
                if refused is None:
                    self.assertEqual(processes(outer), [(python, replaced)])
                else:
                    self.assertIn((python, refused), processes(outer))

    @proves("REQ_NESTED_RECORDING", "REQ_REUSE_SOUND")
    def test_a_start_that_drops_the_parents_variable_below_its_wrapper_is_refused(self):
        outer, _ = nested(self.root, """
            import os, subprocess, sys
            if os.name == "nt":
                import _winapi
                real = _winapi.CreateProcess
                def create(*a):
                    a = list(a)
                    a[6] = {k: v for k, v in a[6].items()
                            if k.upper() != "TRIFECTA_RECORD_PARENT"}
                    return real(*a)
                _winapi.CreateProcess = create
            else:
                real = subprocess._fork_exec
                def fork_exec(*a):
                    a = list(a)
                    a[5] = [e for e in a[5] if not e.startswith(b"TRIFECTA_RECORD_PARENT=")]
                    return real(*a)
                subprocess._fork_exec = fork_exec
            subprocess.run([sys.executable, "-c", "open('a.txt').read()"], check=True)
            """)
        python = executable_name()
        self.assertFalse(outer["storable"])
        self.assertIn((f"{python} > {python}", "a Python child left no manifest"),
                      processes(outer))

    @proves("REQ_NESTED_RECORDING", "REQ_REUSE_SOUND")
    def test_a_start_whose_environment_already_holds_the_parents_variable_is_refused(self):
        m = run(self.root, f"""
            import os, subprocess, sys
            subprocess.run([sys.executable, "-c", "pass"], check=True,
                           env={{**os.environ, "{record.PARENT_ENV}": "elsewhere"}})
            """)
        self.assertFalse(m["storable"])
        self.assertEqual(m["why"], "starts a Python child whose environment already holds "
                                   f"{record.PARENT_ENV}")

    @proves("REQ_NESTED_RECORDING", "REQ_REUSE_SOUND")
    def test_a_write_into_a_directory_the_parents_recorder_prepared_is_refused(self):
        why = "writes into a directory the recorder prepared"
        python = executable_name()
        for name, code in (
                ("its directory", "open({directory!r}, 'w').close()"),
                ("a child's configuration", """
                    import glob
                    for path in glob.glob({children!r}):
                        open(path, 'a').close()
                    """)):
            with self.subTest(name):
                directory = self.tmp / f"outer-{len(list(self.tmp.glob('outer-*')))}"
                outer, own = nested(self.root, code.format(
                    directory=str(directory / "x.txt"),
                    children=str(directory / "children" / "*" / "config.json")))
                self.assertIn((python, why), processes(outer))
                self.assertTrue(own["storable"], processes(own))
        # In the recorded child itself, as in its children.
        m = run(self.root, f"import os; os.makedirs({str(self.tmp / 'record-0' / 'mine')!r})")
        self.assertEqual(m["why"], why)

    @proves("REQ_NESTED_RECORDING", "REQ_REUSE_SOUND")
    def test_what_the_parents_recorder_installed_is_checked_at_each_start_and_at_exit(self):
        python = executable_name()
        system = "nt" if os.name == "nt" else "posix"
        start = "import subprocess, sys; subprocess.run([sys.executable, '-c', 'pass'])\n"
        for name, code, what in (
                ("a wrapper, at exit", f"import os, {system}; os.stat = {system}.stat",
                 "os.stat"),
                ("a wrapper, at a start", f"import os, {system}; kept = os.stat\n"
                 f"os.stat = {system}.stat\n{start}os.stat = kept", "os.stat"),
                ("the start wrapper, at exit", "import subprocess\n"
                 "subprocess.Popen._execute_child = lambda *a: None",
                 "Popen._execute_child"),
                ("the environment's mapping", "import os; os.environ.__class__ = os._Environ",
                 "os.environ"),
                ("the audit hook", "import sys\n"
                 f"sys.modules[{record.PARENT_MODULE!r}].Recorder.hook.__code__ = "
                 "(lambda self, event, args: None).__code__", "its audit hook")):
            with self.subTest(name):
                outer, _ = nested(self.root, code)
                self.assertIn((python, f"replaces what the recorder installed: {what}"),
                              processes(outer))


class AroundAWrapper(_TmpRepo):
    """The ways code can step around a wrapper without replacing it, which DEC_0035 lists
    and accepts for the repository's own tests: each is shown to stay open, in a child
    that records itself, so a way the list does not hold is one no test here shows."""

    def unseen(self, code: str, env: dict | None = None) -> dict:
        outer, _ = nested(self.root, code, env=env)
        self.assertTrue(outer["storable"], processes(outer))
        return outer

    @proves("REQ_NESTED_RECORDING")
    def test_a_wrappers_original_in_wrapped_and_its_closure(self):
        outer = self.unseen("""
            import os
            f = os.stat
            while hasattr(f, "__wrapped__"):
                f = f.__wrapped__
            f("c.txt")
            f = os.lstat
            while getattr(f, "__closure__", None):
                f = next(c.cell_contents for c in f.__closure__
                         if getattr(c.cell_contents, "__name__", None) == "lstat")
            f("b.txt")
            """)
        for name in ("b.txt", "c.txt"):
            self.assertNotIn(name, outer["files"])
            self.assertNotIn(name, outer["probes"])

    @proves("REQ_NESTED_RECORDING")
    def test_environ_getitem_past_the_recording_mapping(self):
        outer = self.unseen("import os; os._Environ.__getitem__(os.environ, 'TRIFECTA_TEST_PAST')",
                            env={**os.environ, "TRIFECTA_TEST_PAST": "value"})
        self.assertNotIn("TRIFECTA_TEST_PAST", outer["environment"])

    @proves("REQ_NESTED_RECORDING")
    def test_an_audit_hook_the_run_adds(self):
        # The run's hook is called for the events a recorder raises while it is at work,
        # when it notes nothing.
        outer = self.unseen("""
            import sys
            done = []
            def hook(event, args):
                if event == "open" and str(args[0]).endswith("a.txt") and not done:
                    done.append(1)
                    open("b.txt").read()
            sys.addaudithook(hook)
            open("a.txt").read()
            """)
        self.assertIn("a.txt", outer["files"])
        self.assertNotIn("b.txt", outer["files"])

    @proves("REQ_NESTED_RECORDING")
    def test_object_setattr_on_what_the_recorder_made(self):
        outer = self.unseen(f"""
            import os
            for cls in type(os.environ).__mro__:
                if cls.__module__ in {record.MODULES!r}:
                    type.__setattr__(cls, "__getitem__", os._Environ.__getitem__)
            os.environ["TRIFECTA_TEST_SET"]
            """, env={**os.environ, "TRIFECTA_TEST_SET": "value"})
        self.assertNotIn("TRIFECTA_TEST_SET", outer["environment"])


class Checked(_TmpRepo):
    """What the parent's recorder installed, checked for wrappers only a recorder made,
    and a start changed below its wrapper."""

    @proves("REQ_NESTED_RECORDING", "REQ_REUSE_SOUND")
    def test_a_replacement_that_names_the_wrapper_without_calling_it_is_refused(self):
        outer, _ = nested(self.root, """
            import os
            wrapper = os.stat
            real = wrapper
            while hasattr(real, "__wrapped__"):
                real = real.__wrapped__
            def stat(path, *args, **kwargs):
                return real(path, *args, **kwargs)
            stat.__wrapped__ = wrapper
            os.stat = stat
            """)
        self.assertIn((executable_name(), "replaces what the recorder installed: os.stat"),
                      processes(outer))

    @proves("REQ_NESTED_RECORDING", "REQ_REUSE_SOUND")
    @only_on("posix")
    def test_a_replaced_uname_is_refused(self):
        outer, _ = nested(self.root, """
            import os
            real = os.uname()
            os.uname = lambda: os.uname_result((real.sysname, "elsewhere", real.release,
                                                real.version, real.machine))
            """)
        self.assertIn((executable_name(), "replaces what the recorder installed: os.uname"),
                      processes(outer))

    @proves("REQ_NESTED_RECORDING", "REQ_REUSE_SOUND")
    def test_dash_s_added_below_the_parents_wrapper_is_refused(self):
        outer, _ = nested(self.root, """
            import os, subprocess, sys
            if os.name == "nt":
                import _winapi
                real = _winapi.CreateProcess
                def create(*a):
                    a = list(a)
                    program, rest = a[1].split(" ", 1)
                    a[1] = program + " -S " + rest
                    return real(*a)
                _winapi.CreateProcess = create
            else:
                real = subprocess._fork_exec
                def fork_exec(*a):
                    a = list(a)
                    a[0] = [a[0][0], b"-S", *a[0][1:]]
                    return real(*a)
                subprocess._fork_exec = fork_exec
            subprocess.run([sys.executable, "-c", "open('a.txt').read()"], check=True)
            """)
        python = executable_name()
        self.assertFalse(outer["storable"])
        self.assertIn((f"{python} > {python}", "a Python child left no manifest"),
                      processes(outer))


#: How a run rewrites a manifest a recorder wrote, once its child has exited, by a name
#: other than the one the recorder gave it: each must be refused.
REWRITE = """
import glob, json, os, subprocess, sys
DIR = {directory!r}
subprocess.run([sys.executable, "-c", "open('a.txt').read()"], check=True)
[target] = glob.glob(os.path.join(DIR, "children", "*", "manifest.json"))
with open(target) as f:
    data = json.load(f)
data["files"] = {{}}
{alias}
with open(alias, "w") as f:
    json.dump(data, f)
"""
#: Each other name, by the system that has it.
ALIASES = {
    "a link the run made": (os.name == "posix", 'os.symlink(DIR, "link")\n'
                            'alias = os.path.join("link", os.path.relpath(target, DIR))'),
    "/proc/self/root": (sys.platform == "linux", 'alias = "/proc/self/root" + target'),
    "/proc/self/cwd and ..": (sys.platform == "linux", 'alias = "/proc/self/cwd/../" + '
                              'os.path.relpath(target, os.path.dirname(os.getcwd()))'),
    "a long-path prefix": (os.name == "nt", 'alias = "\\\\\\\\?\\\\" + target'),
    "a trailing dot": (os.name == "nt", 'alias = target.replace(DIR, DIR + ".", 1)'),
}
#: The administrative share of the drive the temporary directory is on, on Windows.
SHARE = ('drive, rest = os.path.splitdrive(target)\n'
         'alias = "\\\\\\\\localhost\\\\" + drive[0] + "$" + rest\n')


class Rewritten(_TmpRepo):
    """A write into a directory a recorder prepared is refused by where it lands."""

    def rewrite(self, alias: str) -> dict:
        directory = self.tmp / f"record-{len(list(self.tmp.glob('record-*')))}"
        return run(self.root, REWRITE.format(directory=str(directory), alias=alias))

    @proves("REQ_NESTED_RECORDING", "REQ_REUSE_SOUND")
    def test_a_manifest_rewritten_by_another_name_is_refused(self):
        for name, (here, alias) in ALIASES.items():
            if not here:
                continue
            with self.subTest(name):
                m = self.rewrite(alias)
                self.assertFalse(m["storable"], name)
                self.assertIn("writes into a directory the recorder prepared", whys(m))

    @proves("REQ_NESTED_RECORDING", "REQ_REUSE_SOUND")
    @only_on("nt")
    def test_a_manifest_rewritten_through_an_administrative_share_is_refused(self):
        drive = os.path.splitdrive(str(self.tmp))[0]
        if not os.path.exists(f"\\\\localhost\\{drive[0]}$\\"):
            self.skipTest("no administrative share here")
        m = self.rewrite(SHARE)
        self.assertIn("writes into a directory the recorder prepared", whys(m))

    @proves("REQ_NESTED_RECORDING", "REQ_REUSE_SOUND")
    def test_a_hard_link_to_a_manifest_is_refused(self):
        for name, alias in (
                ("linked, then written", 'os.link(target, "hard")\nalias = "hard"'),
                ("moved out", 'os.replace(target, "moved")\nalias = target'),
                ("copied out", 'import shutil; shutil.copyfile(target, "copy")\n'
                               'alias = target')):
            with self.subTest(name):
                m = self.rewrite(alias)
                self.assertFalse(m["storable"], name)
                self.assertEqual(m["why"], "writes into a directory the recorder prepared")

    @proves("REQ_NESTED_RECORDING", "REQ_REUSE_SOUND")
    def test_a_write_to_another_name_of_a_file_in_the_directory_is_refused(self):
        # However the other name was made, the write finds the file in the recorder's
        # directory by its device and file number.
        top = self.tmp / "top"
        top.mkdir()
        (top / record.MANIFEST).write_text("{}", encoding="utf-8")
        os.link(top / record.MANIFEST, self.tmp / "other")
        r = record.Recorder(str(top), {"root": str(self.root)})
        record.HANDLERS["open"](r, (str(self.tmp / "other"), "w", 0))
        self.assertEqual(r.why, "writes into a directory the recorder prepared")
        r = record.Recorder(str(top), {"root": str(self.root)})
        record.HANDLERS["open"](r, (str(self.root / "a.txt"), "w", 0))
        self.assertIsNone(r.why)


class PreSite(_TmpRepo):
    """A Python child that could run code of the run's before ``site`` starts the
    recorder is refused."""

    @proves("REQ_NESTED_RECORDING", "REQ_REUSE_SOUND")
    def test_a_child_whose_environment_runs_code_before_site_is_refused(self):
        for name in record.PRE_SITE:
            with self.subTest(name):
                m = run(self.root, f"""
                    import os, subprocess, sys
                    subprocess.run([sys.executable, "-c", "pass"],
                                   env={{**os.environ, "{name}": "elsewhere"}})
                    """)
                self.assertEqual(m["why"], f"starts a Python child whose environment sets "
                                           f"{name}, which can run code before the recorder")
        # Under -E or -I the interpreter reads none of them.
        for flag in ("-E", "-I"):
            with self.subTest(flag):
                m = run(self.root, f"""
                    import os, subprocess, sys
                    subprocess.run([sys.executable, "{flag}", "-c", "pass"], check=True,
                                   env={{**os.environ, "PYTHONPATH": "elsewhere"}})
                    """)
                self.assertTrue(m["storable"], m.get("why"))

    @proves("REQ_NESTED_RECORDING", "REQ_REUSE_SOUND")
    def test_frozen_modules_off_is_refused(self):
        for options in ('"-X", "frozen_modules=off"', '"-Xfrozen_modules=off"'):
            with self.subTest(options):
                m = run(self.root, f"""
                    import subprocess, sys
                    subprocess.run([sys.executable, {options}, "-c", "pass"])
                    """)
                self.assertIn("frozen_modules=off", m["why"])

    @proves("REQ_NESTED_RECORDING", "REQ_REUSE_SOUND")
    def test_a_module_run_before_the_recorder_from_outside_the_interpreter_is_refused(self):
        import encodings
        shadow = self.tmp / "shadow"
        shutil.copytree(os.path.dirname(encodings.__file__), shadow / "encodings")
        m = run(self.root, "pass", env={**os.environ, "PYTHONPATH": str(shadow)})
        self.assertFalse(m["storable"])
        self.assertIn("ran encodings from outside the standard library before the recorder "
                      "started", whys(m))

    @proves("REQ_NESTED_RECORDING", "REQ_REUSE_SOUND")
    def test_a_child_under_other_prefixes_is_refused(self):
        directory = self.tmp / "record-prefixes"
        record.prepare(str(directory), str(self.root))
        config = json.loads((directory / record.CONFIG).read_text(encoding="utf-8"))
        config["prefixes"] = [str(self.tmp / "elsewhere")]
        (directory / record.CONFIG).write_text(json.dumps(config), encoding="utf-8")
        env = {k: v for k, v in os.environ.items() if k not in record.OWN}
        env[record.ENV] = str(directory)
        subprocess.run([sys.executable, "-c", "pass"], cwd=self.root, env=env, check=True)
        m = json.loads((directory / record.MANIFEST).read_text(encoding="utf-8"))
        self.assertEqual(m["why"], "runs under prefixes other than its parent's")


OUTSIDE_PATH = ("starts a Python child whose PYTHONPATH names a directory outside the "
                "repository and the interpreter")


class SearchPath(_TmpRepo):
    """DEC_0042: a Python child's PYTHONPATH may name only directories in the repository
    or the interpreter's prefixes, resolved, and is recorded."""

    def started(self, entries: str, cwd: str = ".") -> dict:
        """A recorded run that starts a Python child with PYTHONPATH set to ``entries``
        in ``cwd``."""
        return run(self.root, f"""
            import os, subprocess, sys
            subprocess.run([sys.executable, "-c", "import os; os.environ.get('X')"],
                           check=True, cwd={cwd!r},
                           env={{**os.environ, "PYTHONPATH": {entries!r}}})
            """)

    def recorded(self, entries: str) -> dict:
        """A recorded child started with PYTHONPATH set to ``entries``: its manifest."""
        directory = self.tmp / f"record-path-{len(list(self.tmp.glob('record-path-*')))}"
        record.prepare(str(directory), str(self.root))
        env = {k: v for k, v in os.environ.items() if k not in record.OWN}
        env.update({record.ENV: str(directory), "PYTHONPATH": entries})
        subprocess.run([sys.executable, "-c", "pass"], cwd=self.root, env=env, check=True)
        return json.loads((directory / record.MANIFEST).read_text(encoding="utf-8"))

    @proves("REQ_NESTED_RECORDING", "REQ_REUSE_SOUND")
    def test_an_entry_in_the_repository_is_allowed_and_recorded(self):
        m = self.started(str(self.root / "sub"))
        self.assertTrue(m["storable"], m.get("why"))
        m = self.recorded(str(self.root / "sub"))
        self.assertTrue(m["storable"], m.get("why"))
        self.assertIsNotNone(m["environment"]["PYTHONPATH"])
        self.assertIn("sub", m["listings"], "a new module there runs the child again")

    @proves("REQ_NESTED_RECORDING", "REQ_REUSE_SOUND")
    def test_an_entry_elsewhere_is_refused(self):
        elsewhere = self.tmp / "elsewhere"
        elsewhere.mkdir()
        m = self.started(os.pathsep.join([str(self.root / "sub"), str(elsewhere)]))
        self.assertEqual(m["why"], OUTSIDE_PATH)

    @proves("REQ_NESTED_RECORDING", "REQ_REUSE_SOUND")
    def test_a_link_from_the_repository_to_elsewhere_is_refused(self):
        elsewhere = self.tmp / "elsewhere"
        elsewhere.mkdir()
        try:
            os.symlink(elsewhere, self.root / "link", target_is_directory=True)
        except OSError:
            self.skipTest("no symbolic links here")
        m = self.started(str(self.root / "link"))
        self.assertEqual(m["why"], OUTSIDE_PATH)

    @proves("REQ_NESTED_RECORDING", "REQ_REUSE_SOUND")
    def test_an_empty_entry_is_the_working_directory(self):
        m = self.started(os.pathsep.join(["sub", ""]))
        self.assertTrue(m["storable"], m.get("why"))
        m = self.started(os.pathsep, cwd=str(self.tmp))
        self.assertEqual(m["why"], OUTSIDE_PATH)

    @proves("REQ_NESTED_RECORDING", "REQ_REUSE_SOUND")
    def test_an_entry_holding_a_name_of_the_standard_library_is_refused(self):
        # Refused as the child starts, since a module the recorder imports as it starts,
        # as json, would load from there; and by the child itself, for any other.
        (self.root / "sub" / "json.py").write_text("", encoding="utf-8")
        m = self.started(str(self.root / "sub"))
        self.assertEqual(m["why"], "starts a Python child whose PYTHONPATH holds json, a "
                                   "name of the standard library")
        (self.root / "sub" / "json.py").unlink()
        (self.root / "sub" / "colorsys.py").write_text("", encoding="utf-8")
        m = self.recorded(str(self.root / "sub"))
        self.assertEqual(m["why"], "PYTHONPATH holds colorsys, a name of the standard "
                                   "library")


class RmtreeCallbacks(_TmpRepo):
    """What a callback ``shutil.rmtree`` calls on an error does is the run's own."""

    @proves("REQ_REUSE_SOUND")
    def test_a_read_and_a_start_in_a_callback_are_recorded(self):
        for call in ('shutil.rmtree("missing", onexc=callback)',
                     'shutil.rmtree("missing", False, callback)',
                     'shutil.rmtree("missing", onerror=callback)'):
            with self.subTest(call):
                m = run(self.root, f"""
                    import shutil, warnings
                    warnings.simplefilter("ignore")
                    def callback(*args):
                        open("a.txt").read()
                    {call}
                    """)
                self.assertTrue(m["storable"], m.get("why"))
                self.assertIn("a.txt", m["files"])
        m = run(self.root, """
            import shutil, subprocess
            def callback(*args):
                try:
                    subprocess.run(["no-such-program-rmtree"])
                except OSError:
                    pass
            shutil.rmtree("missing", onexc=callback)
            """)
        self.assertEqual(m["why"], "runs no-such-program-rmtree")


class Prefixes(_TmpRepo):
    """A write that lands under the interpreter's prefixes, where a .pth file or a module
    runs in every child before the recorder, is refused."""

    @proves("REQ_NESTED_RECORDING", "REQ_REUSE_SOUND")
    def test_a_write_under_the_prefixes_is_refused(self):
        purelib = Path(sysconfig.get_paths()["purelib"])
        probe = purelib / f"zz-trifecta-probe-{os.getpid()}.txt"
        routes = {
            "written": f"open({str(probe)!r}, 'w').close()",
            # Across devices the move or link fails; its audit event came first.
            "moved in": f"open('made.txt', 'w').close()\ntry: os.replace('made.txt', "
                        f"{str(probe)!r})\nexcept OSError: pass",
            "linked in": f"open('made.txt', 'w').close()\ntry: os.link('made.txt', "
                         f"{str(probe)!r})\nexcept OSError: pass",
            "copied in": f"open('made.txt', 'w').close(); "
                         f"shutil.copyfile('made.txt', {str(probe)!r})",
        }
        if os.name == "posix":
            routes["through a link"] = (f"os.symlink({str(purelib)!r}, 'site'); "
                                        f"open(os.path.join('site', {probe.name!r}), 'w')"
                                        f".close()")
        try:
            for name, code in routes.items():
                with self.subTest(name):
                    m = run(self.root, f"import os, shutil\n{code}")
                    self.assertIn("writes under the interpreter's prefixes", whys(m))
                    probe.unlink(missing_ok=True)
                    for leftover in ("made.txt", "site"):
                        if os.path.lexists(self.root / leftover):
                            os.unlink(self.root / leftover)
        finally:
            probe.unlink(missing_ok=True)


class Warnings(_TmpRepo):
    """A warnings category the interpreter imports before ``site`` is refused when it is
    not of the standard library, under ``-E`` and ``-I`` too."""

    def setUp(self):
        super().setUp()
        (self.root / "lib").mkdir()
        (self.root / "lib" / "wmod.py").write_text("class W(Warning):\n    pass\n",
                                                   encoding="utf-8")

    @proves("REQ_NESTED_RECORDING", "REQ_REUSE_SOUND")
    def test_a_category_outside_the_standard_library_is_refused(self):
        why = ("starts a Python child whose warnings filter names a category outside the "
               "standard library, which can run code before the recorder")
        for name, options, env in (
                ("-W", '"-W", "error::wmod.W"', ""),
                ("-W attached, under -I", '"-I", "-Werror::wmod.W"', ""),
                ("PYTHONWARNINGS", "", '"PYTHONWARNINGS": "ignore,error::wmod.W"')):
            with self.subTest(name):
                m = run(self.root, f"""
                    import os, subprocess, sys
                    subprocess.run([sys.executable, {options + ', ' if options else ''}"-c",
                                    "pass"], env={{**os.environ, {env}}})
                    """)
                self.assertEqual(m["why"], why)
        with self.subTest("PYTHONWARNINGS set by the run itself"):
            m = run(self.root, """
                import os, subprocess, sys
                os.environ["PYTHONWARNINGS"] = "error::wmod.W"
                subprocess.run([sys.executable, "-c", "pass"])
                """)
            self.assertEqual(m["why"], why)
        m = run(self.root, """
            import subprocess, sys
            subprocess.run([sys.executable, "-W", "error::DeprecationWarning",
                            "-W", "ignore::warnings.Warning", "-c", "pass"], check=True)
            """)
        self.assertTrue(m["storable"], m.get("why"))

    @proves("REQ_NESTED_RECORDING", "REQ_REUSE_SOUND")
    def test_a_module_outside_the_standard_library_loaded_before_the_start_is_refused(self):
        directory = self.tmp / "record-warnings"
        record.prepare(str(directory), str(self.root))
        env = {k: v for k, v in os.environ.items() if k not in record.OWN}
        env.update({record.ENV: str(directory), "PYTHONPATH": str(self.root / "lib"),
                    "PYTHONWARNINGS": "error::wmod.W"})
        subprocess.run([sys.executable, "-c", "pass"], cwd=self.root, env=env, check=True)
        m = json.loads((directory / record.MANIFEST).read_text(encoding="utf-8"))
        self.assertIn("ran wmod, which is not of the standard library, before the recorder "
                      "started", whys(m))


class PycachePrefix(_TmpRepo):
    """Byte code from another directory could stand for the standard library's."""

    @proves("REQ_NESTED_RECORDING", "REQ_REUSE_SOUND")
    def test_a_pycache_prefix_is_refused(self):
        why = ("starts a Python child with -X pycache_prefix, which can run code before the "
               "recorder")
        for name, options in (("separate", '"-X", "pycache_prefix=elsewhere"'),
                              ("attached, under -E", '"-E", "-Xpycache_prefix=elsewhere"')):
            with self.subTest(name):
                m = run(self.root, f"""
                    import subprocess, sys
                    subprocess.run([sys.executable, {options}, "-c", "pass"])
                    """)
                self.assertEqual(m["why"], why)
        m = run(self.root, """
            import os, subprocess, sys
            subprocess.run([sys.executable, "-c", "pass"],
                           env={**os.environ, "PYTHONPYCACHEPREFIX": "elsewhere"})
            """)
        self.assertEqual(m["why"], "starts a Python child whose environment sets "
                                   "PYTHONPYCACHEPREFIX, which can run code before the "
                                   "recorder")


class SearchPathEntries(_TmpRepo):
    """A search-path entry that is not a directory, or one that changed after its child's
    start was judged, is refused."""

    def recorded(self, entries: str) -> dict:
        directory = self.tmp / f"record-path-{len(list(self.tmp.glob('record-path-*')))}"
        record.prepare(str(directory), str(self.root))
        env = {k: v for k, v in os.environ.items() if k not in record.OWN}
        env.update({record.ENV: str(directory), "PYTHONPATH": entries})
        subprocess.run([sys.executable, "-c", "pass"], cwd=self.root, env=env, check=True)
        return json.loads((directory / record.MANIFEST).read_text(encoding="utf-8"))

    @proves("REQ_NESTED_RECORDING", "REQ_REUSE_SOUND")
    def test_an_entry_that_is_not_a_directory_is_refused(self):
        import zipfile
        with zipfile.ZipFile(self.root / "lib.zip", "w") as z:
            z.writestr("helper.py", "")
        m = run(self.root, f"""
            import os, subprocess, sys
            subprocess.run([sys.executable, "-c", "pass"],
                           env={{**os.environ, "PYTHONPATH": {str(self.root / 'lib.zip')!r}}})
            """)
        self.assertEqual(m["why"], "starts a Python child whose PYTHONPATH names something "
                                   "that is not a directory")
        m = self.recorded(str(self.root / "lib.zip"))
        self.assertIn("PYTHONPATH names something that is not a directory", whys(m))

    @proves("REQ_NESTED_RECORDING", "REQ_REUSE_SOUND")
    def test_an_entry_swapped_for_a_link_elsewhere_is_refused_by_the_child(self):
        # As if the link were swapped after the parent judged the start: the child's own
        # recorder judges the entry again.
        elsewhere = self.tmp / "elsewhere"
        elsewhere.mkdir()
        try:
            os.symlink(elsewhere, self.root / "link", target_is_directory=True)
        except OSError:
            self.skipTest("no symbolic links here")
        m = self.recorded(str(self.root / "link"))
        self.assertIn("PYTHONPATH names a directory outside the repository and the "
                      "interpreter", whys(m))


class Namespaces(_TmpRepo):
    """A path read through a share or a device namespace is refused, by name."""

    @proves("REQ_REUSE_SOUND")
    @only_on("nt")
    def test_a_read_through_a_long_path_prefix_is_refused(self):
        other = self.tmp / "other.txt"
        other.write_text("x", encoding="utf-8")
        path = "\\\\?\\" + str(other)
        m = run(self.root, f"open({path!r}).read()")
        self.assertEqual(m["why"], "reaches a path through a share or a device namespace")
        self.assertTrue(record.valid(m))


#: An ``encodings`` that, run before the recorder, reads a file outside and leaves.
SHADOW = """import sys, _io
sys.LEAK = _io.FileIO({secret!r}).read().decode()
del sys.modules['encodings']
sys.path_importer_cache.clear()
{cleanup}
import encodings
"""
#: A child that says what it read before its recorder started.
LEAKED = "import sys; open('out.txt', 'w').write(getattr(sys, 'LEAK', 'none'))"


class CarriedSearchPath(_TmpRepo):
    """A recorded child's PYTHONPATH reaches it in its configuration, not its
    environment, until its recorder has started, so an entry changed after the parent
    judged it runs nothing before the recorder."""

    def setUp(self):
        super().setUp()
        self.secret = self.tmp / "outside" / "secret.txt"
        self.secret.parent.mkdir()
        self.secret.write_text("S5", encoding="utf-8")

    def leaked(self, before: str) -> tuple[dict, str]:
        out = self.root / "out.txt"
        out.unlink(missing_ok=True)
        outer, _ = nested(self.root, LEAKED, before=before)
        return outer, out.read_text(encoding="utf-8")

    @proves("REQ_NESTED_RECORDING", "REQ_REUSE_SOUND")
    def test_a_shadow_written_after_the_check_runs_nothing_first(self):
        real = self.root / "real"
        shadow = SHADOW.format(secret=str(self.secret), cleanup=(
            f"import shutil; shutil.rmtree({str(real / 'encodings')!r})"))
        for delay in (0, 0.001, 0.005, 0.02):
            with self.subTest(delay=delay):
                shutil.rmtree(real, ignore_errors=True)
                outer, out = self.leaked(f"""
                    import threading, time
                    os.makedirs({str(real)!r})
                    os.environ["PYTHONPATH"] = {str(real)!r}
                    def plant():
                        time.sleep({delay})
                        os.makedirs({str(real / 'encodings')!r}, exist_ok=True)
                        with open({str(real / 'encodings' / '__init__.py')!r}, "w") as f:
                            f.write({shadow!r})
                    threading.Thread(target=plant).start()
                    """)
                self.assertFalse(out == "S5" and outer["storable"], processes(outer))

    @proves("REQ_NESTED_RECORDING", "REQ_REUSE_SOUND")
    @only_on("posix")
    def test_a_link_swapped_after_the_check_runs_nothing_first(self):
        real, evil, link = self.root / "real", self.root / "evil", self.root / "lib"
        shadow = SHADOW.format(secret=str(self.secret), cleanup=(
            f"import posix; posix.symlink({str(real)!r}, {str(self.root / 't2')!r}); "
            f"posix.rename({str(self.root / 't2')!r}, {str(link)!r})"))
        for delay in (0, 0.001, 0.005, 0.02):
            with self.subTest(delay=delay):
                for path in (real, evil):
                    shutil.rmtree(path, ignore_errors=True)
                if os.path.lexists(link):
                    os.unlink(link)
                outer, out = self.leaked(f"""
                    import threading, time
                    os.makedirs({str(real)!r}); os.makedirs({str(evil / 'encodings')!r})
                    with open({str(evil / 'encodings' / '__init__.py')!r}, "w") as f:
                        f.write({shadow!r})
                    os.symlink({str(real)!r}, {str(link)!r})
                    os.environ["PYTHONPATH"] = {str(link)!r}
                    def swap():
                        time.sleep({delay})
                        os.symlink({str(evil)!r}, {str(self.root / 't1')!r})
                        os.replace({str(self.root / 't1')!r}, {str(link)!r})
                    threading.Thread(target=swap).start()
                    """)
                self.assertFalse(out == "S5" and outer["storable"], processes(outer))

    @proves("REQ_NESTED_RECORDING", "REQ_REUSE_SOUND")
    def test_the_child_sees_its_search_path_once_its_recorder_has_started(self):
        lib = self.root / "lib"
        lib.mkdir()
        (lib / "helper_here.py").write_text("VALUE = 2\n", encoding="utf-8")
        m = run(self.root, f"""
            import os, subprocess, sys
            subprocess.run([sys.executable, "-c",
                            "import os, helper_here; "
                            "open('seen.txt', 'w').write(os.environ['PYTHONPATH'])"],
                           check=True, env={{**os.environ, "PYTHONPATH": {str(lib)!r}}})
            """)
        self.assertTrue(m["storable"], m.get("why"))
        self.assertEqual((self.root / "seen.txt").read_text(encoding="utf-8"), str(lib))
        self.assertIn("lib/helper_here.py", m["files"])

    @proves("REQ_NESTED_RECORDING")
    def test_a_child_started_without_a_recorder_keeps_its_search_path(self):
        lib = self.root / "lib"
        lib.mkdir()
        env = {k: v for k, v in os.environ.items() if k not in record.OWN}
        env["PYTHONPATH"] = str(lib)
        out = subprocess.run([sys.executable, "-c", "import os, sys; "
                              "print(os.environ['PYTHONPATH'] in sys.path)"],
                             env=env, capture_output=True, encoding="utf-8", check=True)
        self.assertEqual(out.stdout.strip(), "True")
        directory = self.tmp / "record-carried"
        record.prepare(str(directory), str(self.root))
        carried = record.carry_search_path(str(directory), env)
        self.assertNotIn("PYTHONPATH", carried)
        config = json.loads((directory / record.CONFIG).read_text(encoding="utf-8"))
        self.assertEqual(config[record.SEARCH_PATH_ENV], str(lib))


class ParentsRoot(_TmpRepo):
    """A nested test's recorder counts its parent's repository as inside, and nothing
    outside both."""

    def inner(self, entry: Path) -> dict:
        parent = self.tmp / "parent"
        outer = self.tmp / f"outer-{entry.name}"
        own = self.tmp / f"own-{entry.name}"
        record.prepare(str(own), str(self.root))
        record.prepare(str(outer), str(parent), ignore=[str(own)])
        code = (f"import os, subprocess, sys\n"
                f"os.environ[{record.ENV!r}] = {str(own)!r}\n"
                f"subprocess.run([sys.executable, '-c', 'pass'], check=True,\n"
                f"               env={{**os.environ, 'PYTHONPATH': {str(entry)!r}}})\n")
        env = {k: v for k, v in os.environ.items()
               if k not in record.OWN and k.upper() != record.PATH_ENV}
        env[record.ENV] = str(outer)
        subprocess.run([sys.executable, "-c", code], cwd=self.root, env=env, check=True,
                       capture_output=True)
        return json.loads((own / record.MANIFEST).read_text(encoding="utf-8"))

    @proves("REQ_NESTED_RECORDING", "REQ_REUSE_SOUND")
    def test_an_entry_in_the_parents_repository_is_inside(self):
        (self.tmp / "parent" / "lib").mkdir(parents=True)
        (self.tmp / "elsewhere").mkdir()
        outside = ("PYTHONPATH names a directory outside the repository and the "
                   "interpreter")
        m = self.inner(self.tmp / "parent" / "lib")
        self.assertNotIn(outside, whys(m))
        m = self.inner(self.tmp / "elsewhere")
        self.assertIn(outside, whys(m))
