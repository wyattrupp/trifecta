"""REQ_FIXTURE_PER_INVARIANT, REQ_REUSE_SOUND: a fixture's copy runs the test modules when
its fixture expects a finding of the test stage or its mutation touches the tests or the
package, and otherwise takes what the control's modules reported, judged afresh in the
copy; what the control kept is taken only for the same modules and the same tests left
out, never by a --fresh run, and gives the same findings at another path. The modules run
side by side and their results keep the order they were given in.
"""

from __future__ import annotations

import io
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from trifecta import proofs
from trifecta.run_fixtures import FixtureError, apply, reaches_tests
from trifecta.testing import proves

SOURCE = """\
import os
import unittest

from trifecta.testing import proves


class T(unittest.TestCase):
    @proves("REQ_X")
    def test_a(self):
        pass

    @proves("REQ_Y")
    def test_b(self):
        self.fail("fails in " + os.getcwd())
"""


def corpus(root: Path, modules: tuple[str, ...] = ("test_x",)) -> Path:
    (root / "tests").mkdir(parents=True)
    (root / "tests" / "__init__.py").write_text("", encoding="utf-8")
    for name in modules:
        (root / "tests" / f"{name}.py").write_text(SOURCE, encoding="utf-8")
    return root


class Scope(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        tmp = Path(self._tmp.name).resolve()
        self.base, self.copy = tmp / "base", tmp / "copy"
        for root in (self.base, self.copy):
            for name in ("tests/test_a.py", "src/pkg/a.py", "docs/a.md", "requirements.lock"):
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                (root / name).write_bytes(b"x\n")

    def reaches(self, expect: str = "REQ_ONE_PACKAGE") -> bool:
        return reaches_tests(expect, self.copy, self.base)

    @proves("REQ_FIXTURE_PER_INVARIANT")
    def test_a_copy_runs_the_tests_only_where_its_fixture_can_reach_them(self):
        self.assertFalse(self.reaches())
        self.assertTrue(self.reaches("REQ_PROVEN_BY_TEST"))
        for mutation in ("docs/a.md", "requirements.lock"):
            with self.subTest(mutation):
                apply(self.copy, [{"file": mutation, "create": "changed\n"}])
                self.assertFalse(self.reaches())
        (self.copy / "tests" / "__pycache__").mkdir()
        (self.copy / "tests" / "__pycache__" / "a.pyc").write_bytes(b"compiled")
        self.assertFalse(self.reaches(), "a cache the run made is no change")

    @proves("REQ_FIXTURE_PER_INVARIANT")
    def test_every_spelling_of_a_change_to_the_tests_or_the_package_is_seen(self):
        for mutation in ({"file": "tests/./sub/../test_a.py", "create": "y\n"},
                         {"file": "tests/test_a.py", "create": "x\r\n"},
                         {"file": "src/pkg/new.py", "create": ""},
                         {"file": "tests/test_a.py", "delete": True},
                         {"file": "src/pkg/a.py", "find": "x", "replace": "y"}):
            with self.subTest(mutation):
                shutil.rmtree(self.copy)
                shutil.copytree(self.base, self.copy)
                apply(self.copy, [mutation])
                self.assertTrue(self.reaches())

    @proves("REQ_FIXTURE_PER_INVARIANT")
    def test_a_fixture_may_not_change_the_copys_git(self):
        for name in (".git/config", ".GIT/x", ".git./config"):
            with self.subTest(name):
                with self.assertRaises(FixtureError):
                    apply(self.copy, [{"file": name, "create": "x"}])


class Kept(unittest.TestCase):
    @proves("REQ_FIXTURE_PER_INVARIANT")
    def test_what_the_control_kept_gives_the_same_findings_at_another_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            control, copy = corpus(base / "control"), corpus(base / "copy")
            kept = base / "kept.json"
            ran = proofs.check_proofs(control, fresh=True, keep=kept)
            runs: list = []
            with mock.patch("sys.stderr", io.StringIO()) as err:
                taken = proofs.check_proofs(copy, runs=runs, given=kept)
            self.assertIn(f"tests: taken from {kept}, not run", err.getvalue())
            self.assertEqual([(r.module, r.reused, r.why) for r in runs],
                             [("tests.test_x", True, "given")])
            self.assertEqual([(f.req, f.location) for f in taken[0]],
                             [(f.req, f.location) for f in ran[0]])
            self.assertEqual(taken[1:], ran[1:])
            message = "".join(f.message for f in taken[0])
            self.assertIn(str(copy), message, "the copy's path put back")
            self.assertNotIn(str(control), message)
            runs = []
            proofs.check_proofs(copy, fresh=True, runs=runs, given=kept)
            self.assertEqual([r.reused for r in runs], [False], "--fresh takes nothing")

    @proves("REQ_FIXTURE_PER_INVARIANT")
    def test_what_was_kept_for_other_modules_is_not_taken(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            control = corpus(base / "control")
            copy = corpus(base / "copy", ("test_x", "test_y"))
            kept = base / "kept.json"
            proofs.check_proofs(control, fresh=True, keep=kept)
            for given in (kept, base / "missing.json"):
                with self.subTest(given.name):
                    runs: list = []
                    proofs.check_proofs(copy, runs=runs, given=given)
                    self.assertEqual([r.module for r in runs],
                                     ["tests.test_x", "tests.test_y"])
                    self.assertNotIn("given", [r.why for r in runs])

    @proves("REQ_FIXTURE_PER_INVARIANT")
    def test_a_malformed_kept_file_is_not_taken(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            root = corpus(base / "root")
            kept = base / "kept.json"
            kept.write_text('{"modules": ["tests.test_x"], "leave_out": [], '
                            '"results": {"tests.test_x": {"lines": [1], "output": ""}}}',
                            encoding="utf-8")
            runs: list = []
            proofs.check_proofs(root, runs=runs, given=kept)
        self.assertNotEqual([r.why for r in runs], ["given"])


class SideBySide(unittest.TestCase):
    @proves("REQ_PROVEN_BY_TEST")
    def test_the_modules_results_keep_the_order_they_were_given(self):
        names = ["tests.test_c", "tests.test_a", "tests.test_b"]
        with tempfile.TemporaryDirectory() as tmp:
            root = corpus(Path(tmp).resolve() / "root", ("test_c", "test_a", "test_b"))
            results, runs = proofs.run_modules(root, names, [], None, True)
        self.assertEqual([r.module for r in runs], names)
        self.assertEqual(list(results), names)
        for name in names:
            self.assertIn(f'"module": "{name}"', "".join(results[name][0]))
