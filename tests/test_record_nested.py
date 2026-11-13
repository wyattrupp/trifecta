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
    environment = {k: v for k, v in (env if env is not None else os.environ).items()
                   if k not in record.OWN}
    environment[record.ENV] = str(outer)
    subprocess.run([sys.executable, "-c", code], cwd=root, env=environment, check=True,
                   capture_output=True)
    load = lambda d: json.loads((d / record.MANIFEST).read_text(encoding="utf-8"))
    return load(outer), load(own)


def processes(m: dict) -> list[tuple[str | None, str]]:
    """Each reason of a manifest as ``(process, why)``."""
    return [(r["process"], r["why"]) for r in m.get("reasons", [])]


class Nested(unittest.TestCase):
    """COMP_NESTED_RECORDER: a Python child that runs a recorder of its own is recorded by
    its parent's recorder, which starts first under a name and a variable of its own."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.root = repository(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

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


class AroundAWrapper(unittest.TestCase):
    """The ways code can step around a wrapper without replacing it, which DEC_0035 lists
    and accepts for the repository's own tests: each is shown to stay open, in a child
    that records itself, so a way the list does not hold is one no test here shows."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.root = repository(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

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


class Checked(unittest.TestCase):
    """What the parent's recorder installed, checked for wrappers only a recorder made,
    and a start changed below its wrapper."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.root = repository(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

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
ALIASES = {
    "posix": {
        "/proc/self/root": 'alias = "/proc/self/root" + target',
        "a link the run made": ('os.symlink(DIR, "link")\n'
                                'alias = os.path.join("link", os.path.relpath(target, DIR))'),
        "/proc/self/cwd and ..": ('alias = "/proc/self/cwd/../" + os.path.relpath('
                                  'target, os.path.dirname(os.getcwd()))'),
    },
    "nt": {
        "a long-path prefix": 'alias = "\\\\\\\\?\\\\" + target',
        "a trailing dot": 'alias = target.replace(DIR, DIR + ".", 1)',
        "an administrative share": ('drive, rest = os.path.splitdrive(target)\n'
                                    'alias = "\\\\\\\\localhost\\\\" + drive[0] + "$" + rest\n'
                                    'if not os.path.exists(alias):\n'
                                    '    alias = target.replace(DIR, DIR + ".", 1)'),
    },
}


class Rewritten(unittest.TestCase):
    """A write into a directory a recorder prepared is refused by where it lands."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.root = repository(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def rewrite(self, alias: str) -> dict:
        directory = self.tmp / f"record-{len(list(self.tmp.glob('record-*')))}"
        return run(self.root, REWRITE.format(directory=str(directory), alias=alias))

    @proves("REQ_NESTED_RECORDING", "REQ_REUSE_SOUND")
    def test_a_manifest_rewritten_by_another_name_is_refused(self):
        for name, alias in ALIASES[os.name].items():
            with self.subTest(name):
                m = self.rewrite(alias)
                self.assertFalse(m["storable"], name)
                self.assertEqual(m["why"], "writes into a directory the recorder prepared")

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


class PreSite(unittest.TestCase):
    """A Python child that could run code of the run's before ``site`` starts the
    recorder is refused."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.root = repository(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

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
        self.assertIn("ran encodings from outside the interpreter before the recorder "
                      "started", [r["why"] for r in m["reasons"]])

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


class RmtreeCallbacks(unittest.TestCase):
    """What a callback ``shutil.rmtree`` calls on an error does is the run's own."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.root = repository(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

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
