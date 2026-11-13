"""REQ_REUSE_SOUND, REQ_REUSE_SCOPED: the test stage reuses a proof module's stored
records only while what the module read is unchanged, runs a new module and keeps the
others, reuses nothing with ``--fresh``, and gives the same findings either way.

Each test runs the test stage on a small repository in a temporary directory, with a
store of its own, so its children record themselves through the .pth file setup
installs. Each such child records into a directory of its own, which the module's own
recorder follows as its parent's (COMP_NESTED_RECORDER); a test here whose child reads
the host name on purpose keeps this module from being stored.
"""

from __future__ import annotations

import os
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

from trifecta import profiler, store
from trifecta.proofs import ModuleRun, check_proofs, run_modules
from trifecta.testing import proves

MODULE_A = '''
import os
import unittest
from trifecta.testing import proves


class A(unittest.TestCase):
    @proves("REQ_A")
    def test_a(self):
        self.assertEqual(open("data/a.txt").read(), "a")
        self.assertIsNone(os.environ.get("TRIFECTA_STORE"))
        os.environ.get("TRIFECTA_DEMO")
        os.listdir("data")
        os.path.exists("gone")
        try:
            import extra  # noqa: F401
        except ImportError:
            pass
'''

MODULE_B = '''
import unittest
from trifecta.testing import proves


class B(unittest.TestCase):
    @proves("REQ_B")
    def test_b(self):
        self.assertTrue(True)
'''


def module(name: str) -> str:
    return textwrap.dedent(MODULE_B).replace("B", name.upper()).replace("_b", f"_{name}")


class Reuse(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        tmp = Path(self._tmp.name).resolve()
        self.root, self.store = tmp / "repo", tmp / "store"
        (self.root / "tests").mkdir(parents=True)
        (self.root / "data").mkdir()
        (self.root / "tests" / "__init__.py").write_text("", encoding="utf-8")
        (self.root / "tests" / "test_a.py").write_text(MODULE_A, encoding="utf-8")
        (self.root / "tests" / "test_b.py").write_text(MODULE_B, encoding="utf-8")
        (self.root / "data" / "a.txt").write_text("a", encoding="utf-8")
        patch = mock.patch.dict(os.environ, {store.ENV: str(tmp / "elsewhere")})
        patch.start()
        self.addCleanup(patch.stop)

    def tearDown(self):
        self._tmp.cleanup()

    def stage(self, fresh: bool = False) -> tuple[list, set, dict[str, bool]]:
        runs: list = []
        findings, proven, _ = check_proofs(self.root, fresh=fresh, runs=runs,
                                           store_at=self.store)
        return findings, proven, {r.module: r.reused for r in runs}

    @proves("REQ_REUSE_SOUND")
    def test_a_module_runs_again_only_when_what_it_read_changes(self):
        first = self.stage()
        self.assertEqual(first[:2], ([], {"REQ_A", "REQ_B"}))
        self.assertEqual(first[2], {"tests.test_a": False, "tests.test_b": False})
        again = self.stage()
        self.assertEqual(again[:2], first[:2])
        self.assertEqual(again[2], {"tests.test_a": True, "tests.test_b": True})
        (self.root / "data" / "a.txt").write_text("changed", encoding="utf-8")
        changed = self.stage()
        self.assertEqual(changed[2], {"tests.test_a": False, "tests.test_b": True})
        self.assertEqual(len(changed[0]), 1)
        self.assertTrue(changed[0][0].location.startswith("tests/test_a.py:"))
        # Back as it was, the first entry matches again; a variable it read does not.
        (self.root / "data" / "a.txt").write_text("a", encoding="utf-8")
        self.assertEqual(self.stage()[2], {"tests.test_a": True, "tests.test_b": True})
        with mock.patch.dict(os.environ, {"TRIFECTA_DEMO": "set"}):
            self.assertEqual(self.stage()[2], {"tests.test_a": False, "tests.test_b": True})
        # A directory listed gains an entry, a path probed appears, a name looked up
        # appears: each runs the module again, as the recorder wrote what it saw.
        for change in (lambda: (self.root / "data" / "new.txt").write_text("", "utf-8"),
                       lambda: (self.root / "gone").mkdir(),
                       lambda: (self.root / "extra.py").write_text("", "utf-8")):
            change()
            self.assertEqual(self.stage()[2], {"tests.test_a": False, "tests.test_b": True})
        self.assertEqual(self.stage()[2], {"tests.test_a": True, "tests.test_b": True})

    @proves("REQ_REUSE_SCOPED")
    def test_a_new_module_runs_and_the_others_are_reused(self):
        self.stage()
        (self.root / "tests" / "test_c.py").write_text(module("c"), encoding="utf-8")
        findings, proven, reused = self.stage()
        self.assertEqual((findings, proven), ([], {"REQ_A", "REQ_B", "REQ_C"}))
        self.assertEqual(reused, {"tests.test_a": True, "tests.test_b": True,
                                  "tests.test_c": False})

    @proves("REQ_REUSE_SCOPED")
    def test_fresh_reuses_nothing_and_finds_the_same(self):
        stored = self.stage()
        fresh = self.stage(fresh=True)
        self.assertEqual(fresh[:2], stored[:2])
        self.assertEqual(fresh[2], {"tests.test_a": False, "tests.test_b": False})
        self.assertEqual(self.stage()[2], {"tests.test_a": True, "tests.test_b": True})


MODULE_REFUSED = """
import socket
import unittest
from trifecta.testing import proves


class R(unittest.TestCase):
    @proves("REQ_R")
    def test_r(self):
        socket.gethostname()
"""


class Named(unittest.TestCase):
    setUp, tearDown = Reuse.setUp, Reuse.tearDown

    @proves("REQ_REFUSALS_NAMED")
    def test_a_module_not_stored_names_its_reasons_and_its_tests_times(self):
        (self.root / "tests" / "test_r.py").write_text(MODULE_REFUSED, encoding="utf-8")
        names = ["tests.test_b", "tests.test_r"]
        for fresh in (False, True):
            with self.subTest(fresh=fresh):
                _, runs = run_modules(self.root, names, [], None, fresh, self.store)
                stored, refused = runs
                self.assertEqual((stored.unstored, stored.reasons, stored.tests),
                                 (False, [], []))
                self.assertTrue(refused.unstored)
                self.assertEqual(refused.reasons,
                                 [{"process": None, "why": "reads the host name"}])
                self.assertEqual([t["name"] for t in refused.tests], ["R.test_r"])
                self.assertIsInstance(refused.tests[0]["seconds"], float)
        # The refused module ran again; the stored one was reused, as before.
        _, runs = run_modules(self.root, names, [], None, False, self.store)
        self.assertEqual([r.reused for r in runs], [True, False])
        # A storable run the store did not keep is named so; nothing is named empty.
        with mock.patch.object(store.Store, "put", return_value=False):
            _, runs = run_modules(self.root, ["tests.test_b"], [], None, True, self.store)
        self.assertEqual(runs[0].reasons, [{"process": None,
                                            "why": "the store did not store it"}])


class Scoped(unittest.TestCase):
    @proves("REQ_REUSE_SCOPED")
    def test_only_a_proof_module_is_reported_as_reused(self):
        """The check marks reuse on its proof modules only; every other stage runs."""
        from tests.test_profile import STAGES, corpus, run_main

        def proofs(root, fresh=False, runs=None, **_):
            runs.append(ModuleRun("tests.test_x", 0.1, not fresh, "fresh" if fresh else ""))
            return [], set(), []

        for fresh in (False, True):
            with self.subTest(fresh=fresh), tempfile.TemporaryDirectory() as tmp:
                root = corpus(tmp)
                argv = ["--base", "main"] + (["--fresh"] if fresh else [])
                run_main(root, argv, False, check_proofs=mock.Mock(side_effect=proofs))
                data = profiler.read(root / "docs/_build/profile/check.json")
                names = [s["name"] for s in data["stages"]]
                self.assertEqual([n for n in names if n != "tests: tests.test_x"], STAGES)
                reused = {s["name"]: s["reused"] for s in data["stages"] if "reused" in s}
                self.assertEqual(reused, {"tests: tests.test_x": not fresh})
