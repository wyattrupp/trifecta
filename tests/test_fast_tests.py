"""REQ_FIXTURE_PER_INVARIANT, REQ_REUSE_SOUND: a fixture's copy runs the test modules when
its fixture expects a finding of the test stage or its mutation touches the tests or the
package, and otherwise takes what the control's modules reported, judged afresh in the
copy; what the control kept is taken only for the same modules and the same tests left
out, and gives the same findings at another path. The modules run side by side and their
results keep their order.
"""

from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

from trifecta import proofs
from trifecta.run_fixtures import reaches_tests
from trifecta.testing import proves

SOURCE = """\
import unittest

from trifecta.testing import proves


class T(unittest.TestCase):
    @proves("REQ_X")
    def test_a(self):
        pass

    @proves("REQ_Y")
    def test_b(self):
        self.fail("fails")
"""


def corpus(root: Path, modules: tuple[str, ...] = ("test_x",)) -> Path:
    (root / "tests").mkdir(parents=True)
    (root / "tests" / "__init__.py").write_text("", encoding="utf-8")
    for name in modules:
        (root / "tests" / f"{name}.py").write_text(SOURCE, encoding="utf-8")
    return root


class Scope(unittest.TestCase):
    @proves("REQ_FIXTURE_PER_INVARIANT")
    def test_a_copy_runs_the_tests_only_where_its_fixture_can_reach_them(self):
        def spec(expect: str, *files: str) -> dict:
            return {"expect": expect, "mutations": [{"file": f} for f in files]}

        for case, reaches in (
                (spec("REQ_PROVEN_BY_TEST", "docs/a.md"), True),
                (spec("REQ_ONE_PACKAGE", "tests/test_a.py"), True),
                (spec("REQ_ONE_PACKAGE", "src/trifecta/a.py"), True),
                (spec("REQ_ONE_PACKAGE", "./Tests/x.py"), True),
                (spec("REQ_ONE_PACKAGE", "docs/a.md", "SRC/x"), True),
                (spec("REQ_REVIEW_CURRENT", "docs/a.md"), False),
                (spec("REQ_ONE_PACKAGE", "requirements.lock"), False),
                (spec("REQ_ONE_LINE_ENDING", ".gitattributes"), False)):
            with self.subTest(case):
                self.assertEqual(reaches_tests(case), reaches)


class Kept(unittest.TestCase):
    @proves("REQ_REUSE_SOUND")
    def test_what_the_control_kept_gives_the_same_findings_at_another_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            control, copy = corpus(base / "control"), corpus(base / "copy")
            kept = base / "kept.json"
            ran = proofs.check_proofs(control, fresh=True, keep=kept)
            runs: list = []
            taken = proofs.check_proofs(copy, fresh=True, runs=runs, given=kept)
        self.assertEqual([(r.module, r.reused, r.why) for r in runs],
                         [("tests.test_x", True, "given")])
        self.assertEqual([(f.req, f.location) for f in taken[0]],
                         [(f.req, f.location) for f in ran[0]])
        self.assertEqual(taken[1:], ran[1:])
        self.assertTrue(any("test_b" in f.message for f in taken[0]))
        self.assertNotIn(str(base / "control"), "".join(f.message for f in taken[0]))

    @proves("REQ_REUSE_SOUND")
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
                    proofs.check_proofs(copy, fresh=True, runs=runs, given=given)
                    self.assertEqual([(r.module, r.reused) for r in runs],
                                     [("tests.test_x", False), ("tests.test_y", False)])

    @proves("REQ_REUSE_SOUND")
    def test_a_malformed_kept_file_is_not_taken(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            root = corpus(base / "root")
            kept = base / "kept.json"
            kept.write_text('{"modules": ["tests.test_x"], "leave_out": [], '
                            '"results": {"tests.test_x": {"lines": [1], "output": ""}}}',
                            encoding="utf-8")
            runs: list = []
            proofs.check_proofs(root, fresh=True, runs=runs, given=kept)
        self.assertEqual([r.reused for r in runs], [False])


class SideBySide(unittest.TestCase):
    @proves("REQ_PROVEN_BY_TEST")
    def test_the_modules_results_keep_their_order(self):
        names = ("test_c", "test_a", "test_b")
        with tempfile.TemporaryDirectory() as tmp:
            root = corpus(Path(tmp).resolve() / "root", names)
            runs: list = []
            findings, proven, _ = proofs.check_proofs(root, fresh=True, runs=runs)
        modules = [r.module for r in runs]
        self.assertEqual(modules, sorted(modules))
        self.assertEqual(len(modules), 3)
        self.assertEqual(proven, {"REQ_X"})
        self.assertEqual(sum("test_b" in f.message for f in findings), 3)
