"""REQ_PROVEN_BY_TEST: how the check runs and judges the tests under ``tests/``.

Each test builds its own minimal corpus, a ``tests/`` package in a temporary directory,
and runs the check's test stage on it; none copies this repository.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

from trifecta.proofs import check_proofs
from trifecta.testing import proves

OTHER = "nt" if os.name == "posix" else "posix"
RUNNER = {"posix": "Linux", "nt": "Windows"}


def corpus(tmp: str, source: str) -> Path:
    root = Path(tmp)
    (root / "tests").mkdir()
    (root / "tests" / "__init__.py").write_text("", encoding="utf-8")
    (root / "tests" / "test_x.py").write_text(
        "import unittest\n\nfrom trifecta.testing import proves, only_on\n\n\n"
        + textwrap.dedent(source), encoding="utf-8")
    return root


PASSING = """
class T(unittest.TestCase):
    @proves("REQ_X")
    def test_a(self):
        pass
"""


class OneSystemTests(unittest.TestCase):
    @proves("REQ_PROVEN_BY_TEST")
    def test_other_system_is_counted_not_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = corpus(tmp, f"""
            class T(unittest.TestCase):
                @proves("REQ_X")
                @only_on("{OTHER}")
                def test_a(self):
                    self.fail("ran on the wrong system")
            """)
            findings, proven, unrun = check_proofs(root)
        self.assertEqual(findings, [])
        self.assertIn("REQ_X", proven)
        self.assertEqual(len(unrun), 1)
        self.assertIn("T.test_a", unrun[0])

    @proves("REQ_PROVEN_BY_TEST")
    def test_running_system_not_collected_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = corpus(tmp, f"""
            class T(unittest.TestCase):
                @proves("REQ_X")
                @only_on("{os.name}")
                def check_a(self):
                    pass
            """)
            findings, proven, _ = check_proofs(root)
        self.assertTrue(any("no result" in f.message for f in findings), findings)
        self.assertNotIn("REQ_X", proven)

    @proves("REQ_PROVEN_BY_TEST")
    def test_running_system_skip_and_failure_are_reported(self):
        for body, word in (("self.skipTest('no')", "skip"), ("self.fail('no')", "failure")):
            with self.subTest(word), tempfile.TemporaryDirectory() as tmp:
                root = corpus(tmp, f"""
                class T(unittest.TestCase):
                    @proves("REQ_X")
                    @only_on("{os.name}")
                    def test_a(self):
                        {body}
                """)
                findings, proven, _ = check_proofs(root)
                self.assertTrue(any(word in f.message for f in findings), findings)
                self.assertNotIn("REQ_X", proven)

    @proves("REQ_PROVEN_BY_TEST")
    def test_runner_os_that_does_not_match_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict(os.environ, {"RUNNER_OS": RUNNER[OTHER]}):
            findings, _, _ = check_proofs(corpus(tmp, PASSING))
        self.assertTrue(any("RUNNER_OS" in f.message for f in findings), findings)

    @proves("REQ_PROVEN_BY_TEST")
    def test_runner_os_that_matches_is_not_reported(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict(os.environ, {"RUNNER_OS": RUNNER[os.name]}):
            findings, proven, _ = check_proofs(corpus(tmp, PASSING))
        self.assertEqual(findings, [])
        self.assertIn("REQ_X", proven)


def stub(tmp: str, records: list) -> list[str]:
    """A child that writes ``records``, each a dict or a raw line, and nothing else."""
    lines = [r if isinstance(r, str) else json.dumps(r) for r in records]
    script = Path(tmp) / "stub_child.py"
    script.write_text(
        "import sys\n"
        f"lines = {lines!r}\n"
        "open(sys.argv[1], 'w', encoding='utf-8').write(''.join(l + '\\n' for l in lines))\n",
        encoding="utf-8")
    return [sys.executable, str(script)]


def os_record(when: str, name: str = os.name) -> dict:
    return {"kind": "os", "when": when, "os_name": name}


RESULT = {"kind": "result", "module": "tests.test_x", "cls": "T", "name": "test_a",
          "outcome": "success", "detail": "", "returned": None}
COLLECTED = {"kind": "collected", "module": "tests.test_x", "cls": "T", "name": "test_a",
             "defined_module": "tests.test_x", "defined_cls": "T"}
GOOD = [os_record("before"), COLLECTED, RESULT, os_record("after"), {"kind": "end"}]


class StubChildTests(unittest.TestCase):
    def judge(self, records: list) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            root = corpus(tmp, PASSING)
            findings, _, _ = check_proofs(root, child=stub(tmp, records))
        return [f.message for f in findings]

    @proves("REQ_PROVEN_BY_TEST")
    def test_good_stub_passes(self):
        self.assertEqual(self.judge(GOOD), [])

    @proves("REQ_PROVEN_BY_TEST")
    def test_os_name_differs_before_imports(self):
        found = self.judge([os_record("before", OTHER), *GOOD[1:]])
        self.assertTrue(any("before" in m for m in found), found)

    @proves("REQ_PROVEN_BY_TEST")
    def test_os_name_differs_after_run(self):
        found = self.judge([*GOOD[:3], os_record("after", OTHER), GOOD[4]])
        self.assertTrue(any("after" in m for m in found), found)

    @proves("REQ_PROVEN_BY_TEST")
    def test_malformed_record(self):
        found = self.judge([*GOOD[:4], "{not json", GOOD[4]])
        self.assertTrue(any("not JSON" in m for m in found), found)

    @proves("REQ_PROVEN_BY_TEST")
    def test_unrecognised_record(self):
        found = self.judge([*GOOD[:4], {"kind": "verdict", "ok": True}, GOOD[4]])
        self.assertTrue(any("not one the check knows" in m for m in found), found)

    @proves("REQ_PROVEN_BY_TEST")
    def test_child_that_ends_early(self):
        found = self.judge(GOOD[:3])
        self.assertTrue(any("ended before" in m for m in found), found)


if __name__ == "__main__":
    unittest.main()
