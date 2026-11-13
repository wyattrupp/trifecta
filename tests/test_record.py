"""REQ_REUSE_SOUND: the recorder notes every input a run reads, and marks a run it cannot
follow as one that is never stored.

Each test runs a short Python program in a child, as a recorded run, in a small
repository in a temporary directory, and reads the manifest the child leaves. The
children record themselves through the .pth file setup installs, so these tests run in
the virtual environment setup made.
"""

from __future__ import annotations

import hashlib
import inspect
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

from trifecta import record, store
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
        for name, line in record.PTH_FILES:
            pth = Path(sysconfig.get_paths()["purelib"]) / name
            self.assertEqual(pth.read_text(encoding="utf-8"), line)

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
            for name, line in record.PTH_FILES:
                self.assertEqual((Path(tmp) / name).read_bytes(), line.encode("utf-8"))
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
        # PEP 538: with none set, Python sets LC_CTYPE itself in a C locale unless told not to.
        env = {k: v for k, v in os.environ.items() if k not in record.LOCALE_VARIABLES}
        env["PYTHONCOERCECLOCALE"] = "0"
        m = run(self.root, "pass", env=env)
        for name in record.LOCALE_VARIABLES:
            self.assertIn(name, m["environment"])
            self.assertIsNone(m["environment"][name], name)
        m = run(self.root, "pass", env={**env, "LANGUAGE": "fr"})
        self.assertIsNotNone(m["environment"]["LANGUAGE"])

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


class HostName(unittest.TestCase):
    """COMP_HOST_NAME: inside a recorded run the host name is a constant, the other
    ``uname`` fields are recorded as hashes, and every other way to read the host's
    identity is recorded or refused."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.root = repository(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def names(self, code: str) -> tuple[dict, list]:
        """The manifest of a run of ``code``, and the host names it wrote to names.json."""
        m = run(self.root, "import json, os, posix, platform\nnames = []\n"
                + textwrap.dedent(code)
                + "\nwith open('names.json', 'w') as f:\n    json.dump(names, f)\n")
        out = self.root / "names.json"
        names = json.loads(out.read_text(encoding="utf-8"))
        out.unlink()  # the tree as it was, which the run probed
        return m, names

    @proves("REQ_HOST_READS", "REQ_REUSE_SOUND")
    @only_on("posix")
    def test_every_uname_gives_the_fixed_host_name_before_and_after_platform_system(self):
        every = ("names += [os.uname().nodename, posix.uname().nodename, platform.node(), "
                 "platform.uname().node]")
        for order in (f"{every}\nplatform.system()\n{every}",
                      f"platform.system()\n{every}",
                      # platform's cache emptied: filled again through the wrapper.
                      f"platform._uname_cache = None\n{every}\nplatform.system()\n{every}"):
            with self.subTest(order=order):
                m, names = self.names(order)
                self.assertTrue(m["storable"], m.get("why"))
                self.assertTrue(names)
                self.assertEqual(set(names), {record.HOST_NAME})
                self.assertEqual(set(m["uname"]), set(record.UNAME_FIELDS))

    @proves("REQ_HOST_READS", "REQ_REUSE_SOUND")
    @only_on("posix")
    def test_the_other_fields_are_held_only_as_hashes(self):
        m, _ = self.names("platform.system(); platform.release(); platform.version()")
        real = os.uname()
        text = json.dumps(m)
        for field in record.UNAME_FIELDS:
            self.assertEqual(m["uname"][field], hashlib.sha256(getattr(real, field).encode(
                "utf-8", "surrogateescape")).hexdigest(), field)
        # Linux or x86_64 may occur in a path; the kernel's release and build do not.
        for field in ("release", "version"):
            self.assertNotIn(getattr(real, field), text, field)

    @proves("REQ_HOST_READS", "REQ_REUSE_SOUND")
    @only_on("posix")
    def test_a_change_to_another_field_reruns_the_module(self):
        m, _ = self.names("platform.release()")
        self.assertTrue(m["storable"], m.get("why"))
        shelf = store.Store(self.tmp / "store", self.root)
        ident = shelf.identity("tests", {"module": "tests.test_host", "leave_out": []})
        self.assertTrue(shelf.put(ident, m, "result"))
        lookup = lambda: shelf.lookup(ident, dict(os.environ), store.Hashes(),
                                      lambda result: result == "result")
        self.assertEqual(lookup(), ("result", ""))
        real = os.uname()
        for field in record.UNAME_FIELDS:
            double = os.uname_result(tuple(
                getattr(real, f) + ("-changed" if f == field else "")
                for f in ("sysname", "nodename", "release", "version", "machine")))
            with self.subTest(field=field), mock.patch.object(os, "uname",
                                                              return_value=double):
                self.assertEqual(lookup(), (None, f"uname {field}"))
        # The host name is no input: another one matches.
        double = os.uname_result((real.sysname, "another-host", real.release,
                                  real.version, real.machine))
        with mock.patch.object(os, "uname", return_value=double):
            self.assertEqual(lookup(), ("result", ""))

    @proves("REQ_HOST_READS", "REQ_REUSE_SOUND")
    @only_on("posix")
    def test_a_read_of_etc_hostname_is_recorded(self):
        if not os.path.lexists("/etc/hostname"):
            self.skipTest("this system has no /etc/hostname")
        m = run(self.root, "open('/etc/hostname').read()")
        if os.path.islink("/etc/hostname"):
            # A link the run did not make is refused, and named.
            self.assertFalse(m["storable"])
            self.assertIn("/etc/hostname", m["why"])
        else:
            self.assertTrue(m["storable"], m.get("why"))
            self.assertIn("/etc/hostname", m["outside"])

    @proves("REQ_HOST_READS", "REQ_REUSE_SOUND")
    @only_on("posix")
    def test_a_read_of_the_kernels_host_name_is_recorded(self):
        if not os.path.exists("/proc/sys/kernel/hostname"):
            self.skipTest("this system has no /proc/sys/kernel/hostname")
        m = run(self.root, "open('/proc/sys/kernel/hostname').read()")
        self.assertTrue(m["storable"], m.get("why"))
        self.assertIn("/proc/sys/kernel/hostname", m["outside"])

    @proves("REQ_HOST_READS", "REQ_REUSE_SOUND")
    def test_a_read_of_the_host_name_variables_is_recorded(self):
        m = run(self.root, "import os; os.environ.get('HOSTNAME'); "
                           "os.environ.get('COMPUTERNAME')")
        self.assertTrue(m["storable"], m.get("why"))
        self.assertIn("HOSTNAME", m["environment"])
        self.assertIn("COMPUTERNAME", m["environment"])

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
    def test_a_spec_whose_name_changes_gets_no_fresh_posix(self):
        # Each spec names another module at its first read and posix after: the recorder
        # reads the name once, so the module made is the one it checked.
        make = ("import _imp\n"
                "made = _imp.create_builtin(spec)\n"
                "_imp.exec_builtin(made)\n"
                "if hasattr(made, 'uname'):\n"
                "    names.append(made.uname().nodename)\n")
        specs = {
            "property": "class Spec:\n"
                        "    reads = 0\n"
                        "    @property\n"
                        "    def name(self):\n"
                        "        self.reads += 1\n"
                        "        return 'math' if self.reads == 1 else 'posix'\n"
                        "    origin = 'built-in'\n",
            "__getattr__": "class Spec:\n"
                           "    reads = 0\n"
                           "    def __getattr__(self, attribute):\n"
                           "        if attribute != 'name':\n"
                           "            raise AttributeError(attribute)\n"
                           "        self.reads += 1\n"
                           "        return 'math' if self.reads == 1 else 'posix'\n",
        }
        for variant, define in specs.items():
            with self.subTest(variant=variant):
                m, names = self.names(define + "spec = Spec()\n" + make)
                self.assertLessEqual(set(names), {record.HOST_NAME},
                                     "the real host name reached the run")
                self.assertTrue(not m["storable"] or not names, m)

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

    @proves("REQ_HOST_READS", "REQ_REUSE_SOUND")
    @only_on("posix")
    def test_the_wrapper_hands_out_no_original(self):
        m, names = self.names(
            "import inspect\n"
            "names.append(inspect.unwrap(os.uname)().nodename)\n"
            "for cell in os.uname.__closure__ or ():\n"
            "    value = cell.cell_contents\n"
            "    names.append(value().nodename if callable(value) else value.nodename)\n")
        self.assertTrue(m["storable"], m.get("why"))
        self.assertEqual(set(names), {record.HOST_NAME})
        self.assertGreater(len(names), 1, "the closure was looked into")

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

    @proves("REQ_HOST_READS", "REQ_REUSE_SOUND")
    def test_where_vale_lives_reads_nothing_of_the_host(self):
        # Only on Windows does this guard the change: platform.system() there reads the host.
        m = run(self.root, "from pathlib import Path\n"
                           "from trifecta.toolchain import bin_vale\n"
                           "bin_vale(Path('.'))\n")
        self.assertTrue(m["storable"], m.get("why"))


def controlled_env() -> dict:
    """An environment holding only what a child interpreter needs, so a reason compared
    exactly does not depend on this machine's variables."""
    keep = ("SYSTEMROOT", "PATH", "TEMP", "TMP", "TMPDIR", "HOME", "USERPROFILE")
    return {k: v for k, v in os.environ.items() if k.upper() in keep}


def executable_name() -> str:
    """The interpreter's base name as a reason names a child: no ``.exe``."""
    name = os.path.basename(sys.executable)
    return name[:-4] if name.lower().endswith(".exe") else name


class Reasons(unittest.TestCase):
    """COMP_REFUSAL_REASONS: every reason a run is refused, each with its process."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.root = repository(self.tmp)
        # A child that reads the host name, and a child of its own started with -c.
        (self.root / "kid.py").write_text(
            "import socket, subprocess, sys\n"
            "socket.gethostname()\n"
            "subprocess.run([sys.executable, '-c', 'import os; os.chdir(\"..\")'],"
            " check=True)\n", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

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

    def recorder(self) -> record.Recorder:
        return record.Recorder(str(self.tmp / "record"), {"root": str(self.root)})

    @proves("REQ_REFUSALS_NAMED")
    def test_the_backstop_strips_values_and_leaves_bare_words(self):
        env = {"TRIFECTA_DEMO": "a-demo-value\n", "TRIFECTA_FLAG": "true",
               "TRIFECTA_SHORT": "abc"}
        with mock.patch.dict(os.environ, env):
            r = self.recorder()
            r.refuse("a-demo-value is true or abc")
        self.assertEqual(r.why, "<env:TRIFECTA_DEMO> is true or abc")

    @proves("REQ_REFUSALS_NAMED")
    def test_a_key_is_cut_before_the_reason_is_formatted(self):
        r = self.recorder()
        spaced = ("Q:\\else where\\deep\\name x.txt" if os.name == "nt"
                  else "/opt/else where/deep/name x.txt")
        self.assertEqual(r.shown(spaced), "name x.txt")
        self.assertEqual(r.shown("docs/a.md"), "docs/a.md", "a key in the root is kept")
        self.assertEqual(r.shown(str(self.root / "sub" / "x.txt")), "<root>/sub/x.txt")
        self.assertEqual(r.shown(os.path.join(sys.prefix, "lib", "x.py")), "<prefix>/lib/x.py")

    @proves("REQ_REFUSALS_NAMED")
    def test_a_place_is_replaced_only_where_no_other_path_character_follows(self):
        r = self.recorder()
        r.refuse(f"{self.root}less{os.sep}x and {self.root} and '{self.root}' and {self.root}")
        self.assertNotIn(record.ROOT + "less", r.why)
        self.assertTrue(r.why.endswith(
            f"x and {record.ROOT} and '{record.ROOT}' and {record.ROOT}"), r.why)

    @proves("REQ_REFUSALS_NAMED")
    def test_a_places_trailing_separator_is_ignored(self):
        scratch = self.tmp / "scratch-dir"
        env = {n: str(scratch) + os.sep for n in ("TMPDIR", "TEMP", "TMP")}
        with mock.patch.dict(os.environ, env):
            r = self.recorder()
            r.refuse(f"made {scratch} and {scratch}{os.sep}x")
            self.assertEqual(r.shown(str(scratch / "y")), "<tmp>/y")
        self.assertEqual(r.why, f"made <tmp> and <tmp>{os.sep}x")

    @proves("REQ_REFUSALS_NAMED")
    def test_naming_a_reason_never_raises(self):
        r = self.recorder()
        with mock.patch.object(r, "sanitize", side_effect=RuntimeError("boom")), \
                mock.patch.object(r, "_places", side_effect=RuntimeError("boom")):
            r.refuse("runs git", "python -m kid")
            self.assertEqual(r.shown(str(self.tmp / "elsewhere")), "a path")
        self.assertEqual(r.reasons, [{"process": None,
                                      "why": "the recorder could not name a reason"}])
        self.assertEqual(r.why, "the recorder could not name a reason")

    @proves("REQ_REFUSALS_NAMED")
    def test_a_prefix_that_is_also_the_base_prefix_is_the_prefix(self):
        with mock.patch.multiple(sys, base_prefix=sys.prefix, base_exec_prefix=sys.prefix):
            r = self.recorder()
            r.refuse(os.path.join(sys.prefix, "x.py"))
            self.assertEqual(r.shown(os.path.join(sys.prefix, "y.py")), "<prefix>/y.py")
        self.assertTrue(r.why.startswith(record.PREFIX), r.why)

    @proves("REQ_REFUSALS_NAMED")
    def test_a_full_list_cleans_nothing_more_and_a_write_adds_no_duplicate(self):
        r = self.recorder()
        for i in range(record.MAX_REASONS):
            r.refuse(f"reason {i}")
        with mock.patch.object(r, "sanitize", side_effect=AssertionError("cleaned")):
            r.refuse("one more")
        self.assertEqual(len(r.reasons), record.MAX_REASONS)
        r = self.recorder()
        os.makedirs(r.directory)
        r.refuse("two processes recorded into one place")
        (Path(r.directory) / record.MANIFEST).write_text("{}", encoding="utf-8")
        r.finish()
        m = json.loads((Path(r.directory) / record.MANIFEST).read_text(encoding="utf-8"))
        self.assertEqual(m["reasons"], [{"process": None,
                                         "why": "two processes recorded into one place"}])

    @proves("REQ_REFUSALS_NAMED")
    def test_a_child_is_named_by_its_executable_and_module_only(self):
        for argv, name in ((["-Xutf8", "-m", "kid"], "python -m kid"),
                           (["-X", "utf8", "-Bm", "kid", "x"], "python -m kid"),
                           (["-Wd", "-mkid"], "python -m kid"),
                           (["-c", "import kid"], "python"),
                           (["-m", "not a module"], "python"),
                           (["-mSomeModule"], "python -m SomeModule"),
                           (["script.py", "-m", "kid"], "python")):
            with self.subTest(argv=argv):
                self.assertEqual(record._child_name(["python", *argv],
                                                    os.path.join("bin", "python.exe")), name)

    @proves("REQ_REFUSALS_NAMED")
    def test_a_module_named_after_m_is_no_option(self):
        self.assertIsNone(record._python_child(["python", "-mSomeModule"]))
        self.assertIsNone(record._python_child(["python", "-X", "S", "-c", "pass"]))
        self.assertIsNotNone(record._python_child(["python", "-BS", "-m", "kid"]))
        self.assertEqual(record._interpreter_options(["python", "-Bm", "kid"]), ("B", "kid"))

    @proves("REQ_REFUSALS_NAMED")
    def test_a_path_in_a_reason_holds_only_placeholders_or_its_base_name(self):
        home, scratch = self.tmp / "home-dir", self.tmp / "scratch-dir"
        other = "Q:\\elsewhere\\deep\\name.txt" if os.name == "nt" \
            else "/opt/elsewhere/deep/name.txt"
        places = {self.root: record.ROOT, home: record.HOME, scratch: record.TEMP,
                  Path(sys.prefix): record.PREFIX, Path(sys.base_prefix): record.BASE_PREFIX}
        env = {"HOME": str(home), "USERPROFILE": str(home), "TMPDIR": str(scratch),
               "TEMP": str(scratch), "TMP": str(scratch), "TRIFECTA_DEMO": "a-demo-value"}
        text = " ".join([*(f"{p}{os.sep}x.py" for p in places), self.root.as_posix() + "/y",
                         other, "a-demo-value"])
        with mock.patch.dict(os.environ, env):
            r = record.Recorder(str(self.tmp / "record"), {"root": str(self.root)})
            r.refuse(text, f"python -m kid {other}")
        reason = r.reasons[0]
        for path, holder in places.items():
            self.assertNotIn(str(path), reason["why"])
            self.assertIn(holder, reason["why"])
        self.assertIn(f"{record.ROOT}/y", reason["why"])
        self.assertNotIn("elsewhere", reason["why"] + reason["process"])
        self.assertIn(" name.txt ", reason["why"])
        self.assertTrue(reason["process"].endswith(" name.txt"))
        self.assertIn("<env:TRIFECTA_DEMO>", reason["why"])
        self.assertNotIn("a-demo-value", reason["why"])
        self.assertEqual(r.why, reason["why"])

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


GOOD = {"version": 1, "storable": True,
        "files": {"docs/a.md": "0" * 64}, "probes": {"gone": "absent"},
        "listings": {"docs": [["a.md", "file"]]}, "lookups": {"./mod": "mod.py"},
        "environment": {"HOME": None}, "outside": {},
        "uname": {f: "0" * 64 for f in record.UNAME_FIELDS} if hasattr(os, "uname") else {}}


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
            {"uname": {"nodename": "0" * 64}}, {"uname": {"release": "6.8.0"}},
        ]
        for change in bad:
            with self.subTest(change=change):
                self.assertFalse(record.valid({**GOOD, **change}))
        self.assertFalse(record.valid({**GOOD, "storable": False, "why": 3}))
        git = [{"process": None, "why": "runs git"}]
        self.assertTrue(record.valid({**GOOD, "storable": False, "why": "runs git",
                                      "reasons": git}))
        self.assertTrue(record.valid({**GOOD, "storable": False, "why": "runs git",
                                      "reasons": git + [{"process": "python -m x",
                                                         "why": "reads the registry"}]}))
        for reasons in (None, [], [{"process": None, "why": "runs vale"}],
                        [{"process": 1, "why": "runs git"}], [{"why": "runs git"}],
                        git * (record.MAX_REASONS + 1),
                        [{"process": None, "why": "runs git", "value": "x"}]):
            with self.subTest(reasons=reasons):
                bad = {**GOOD, "storable": False, "why": "runs git"}
                if reasons is not None:
                    bad["reasons"] = reasons
                self.assertFalse(record.valid(bad))
        self.assertFalse(record.valid({**GOOD, "reasons": git}), "a stored run has none")
        # The interpreter's own _sysconfigdata module on Linux has dashes in its name.
        self.assertTrue(record.valid(
            {**GOOD, "lookups": {"./_sysconfigdata__linux_x86_64-linux-gnu": None}}))

    @proves("REQ_HOST_READS", "REQ_REUSE_SOUND")
    @only_on("posix")
    def test_where_os_uname_exists_every_field_is_required(self):
        self.assertTrue(record.valid(GOOD))
        for fields in ((), ("release",), record.UNAME_FIELDS[:-1]):
            with self.subTest(fields=fields):
                self.assertFalse(record.valid(
                    {**GOOD, "uname": {f: "0" * 64 for f in fields}}))


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
        # reaches the parent's wrapper, which runs last. One that breaks the chain of
        # __wrapped__ is refused as a replacement.
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
                if refused is None:
                    self.assertTrue(outer["storable"], processes(outer))
                    self.assertIn("a.txt", outer["files"])
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
