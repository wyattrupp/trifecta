"""REQ_PROFILED: the check and the fixture runner write a profile that changes nothing else.

The stages are stubbed, so these tests time the pipeline's own order and output without a
Sphinx build, Vale or a repository copy; what each stage finds is the stub's.
"""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from trifecta import check, profiler, run_fixtures
from trifecta.ext.ontology import DOC_LEVEL
from trifecta.findings import Finding
from trifecta.testing import proves

#: Every stage of check.main, in the order it runs, when the build gives needs.json, the
#: corpus has a typed document and a base is given.
STAGES = ["files", "lock", "vale table", "line endings", "tests", "sphinx", "graph",
          "vale rules", "need locations", "lint view", "vale version", "vale normative", "vale prose",
          "fixture audit", "history", "locations"]


def run_main(root: Path, argv: list[str], finding: bool,
             profiled: bool = True, **override) -> tuple[str, str, int]:
    """check.main on ``root`` with every stage stubbed, or replaced by ``override``; its
    stdout, stderr and status."""
    found = [Finding("REQ_X", "docs/a.md:1", "a finding")] if finding else []
    stubs = {
        "corpus_root": mock.Mock(return_value=root),
        "vale_path": mock.Mock(return_value=root / "vale"),
        "repo_files": mock.Mock(return_value=(["docs/a.md"], [])),
        "check_toolchain": mock.Mock(return_value=[]),
        "check_vale_table": mock.Mock(return_value=[]),
        "check_line_endings": mock.Mock(return_value=[]),
        "check_proofs": mock.Mock(return_value=([], set(), ["tests/t.py:1 T.t: REQ_Y"])),
        "run_sphinx": mock.Mock(return_value=list(found)),
        "load_needs": mock.Mock(return_value={"A": {"type": next(iter(DOC_LEVEL))}}),
        "check_graph": mock.Mock(return_value=[]),
        "stage_vale": mock.Mock(return_value=root / "stage"),
        "generate": mock.Mock(return_value=[]),
        "build_lint_view": mock.Mock(),
        "check_vale_version": mock.Mock(return_value=[]),
        "run_vale": mock.Mock(return_value=[]),
        "audit_stage": mock.Mock(return_value=[]),
        "check_lifecycle": mock.Mock(return_value=[]),
        **override,
    }
    out, err = io.StringIO(), io.StringIO()
    with ExitStack() as stack:
        for name, stub in stubs.items():
            stack.enter_context(mock.patch.object(check, name, stub))
        if not profiled:
            stack.enter_context(mock.patch.object(check, "write_profile", mock.Mock()))
        stack.enter_context(redirect_stdout(out))
        stack.enter_context(redirect_stderr(err))
        code = check.main(argv)
    return out.getvalue(), err.getvalue(), code


def corpus(tmp: str) -> Path:
    root = Path(tmp)
    html = root / "docs" / "_build" / "html"
    html.mkdir(parents=True)
    (html / "needs.json").write_text("{}", encoding="utf-8")
    return root


class CheckProfile(unittest.TestCase):
    @proves("REQ_PROFILED")
    def test_profile_changes_no_output_or_status(self):
        for finding in (False, True):
            with self.subTest(finding=finding), tempfile.TemporaryDirectory() as tmp:
                root = corpus(tmp)
                plain = run_main(root, ["--base", "main"], finding)
                named = run_main(root, ["--base", "main", "--profile",
                                        str(root / "elsewhere" / "p.json")], finding)
                self.assertEqual(plain[0].encode("utf-8"), named[0].encode("utf-8"))
                self.assertEqual(plain[2], named[2])
                self.assertEqual(plain[2], 1 if finding else 0)
                self.assertTrue((root / "docs/_build/profile/check.json").is_file())
                self.assertTrue((root / "elsewhere" / "p.json").is_file())
                unprofiled = run_main(root, ["--base", "main"], finding, profiled=False)
                self.assertEqual(plain[0].encode("utf-8"), unprofiled[0].encode("utf-8"))
                self.assertEqual(plain[2], unprofiled[2])

    @proves("REQ_PROFILED")
    def test_a_stage_that_raises_still_writes_the_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = corpus(tmp)
            with self.assertRaises(OSError):
                run_main(root, [], False, run_vale=mock.Mock(side_effect=OSError("boom")))
            data = json.loads((root / "docs/_build/profile/check.json")
                              .read_text(encoding="utf-8"))
        self.assertEqual(data["stages"][-1]["name"], "vale normative")

    @proves("REQ_PROFILED")
    def test_profile_lists_every_stage_in_run_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = corpus(tmp)
            run_main(root, ["--base", "main"], True)
            data = json.loads((root / "docs/_build/profile/check.json")
                              .read_text(encoding="utf-8"))
        self.assertEqual(data["version"], 1)
        self.assertEqual(data["command"], "check")
        self.assertEqual([s["name"] for s in data["stages"]], STAGES)
        for s in data["stages"]:
            self.assertIsInstance(s["seconds"], float)
            self.assertEqual(s["seconds"], round(s["seconds"], 3))
        self.assertGreaterEqual(data["total"], 0)

    @proves("REQ_PROFILED")
    def test_unwritable_profile_changes_no_output_or_status(self):
        for finding in (False, True):
            with self.subTest(finding=finding), tempfile.TemporaryDirectory() as tmp:
                root = corpus(tmp)
                blocked = root / "blocked"
                blocked.mkdir()  # a directory where the profile file would go
                plain = run_main(root, [], finding)
                failed = run_main(root, ["--profile", str(blocked)], finding)
                self.assertEqual(plain[0], failed[0])
                self.assertEqual(plain[2], failed[2])
                self.assertIn("cannot write the profile", failed[1])
                self.assertEqual(failed[1].replace(plain[1], "", 1).count("\n"), 1)

    @proves("REQ_PROFILED")
    def test_a_profile_path_outside_the_repository_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as other:
            root = corpus(tmp)
            out, err, code = run_main(root, ["--profile", str(Path(other) / "p.json")], False)
            self.assertFalse((Path(other) / "p.json").exists())
        self.assertEqual((out, code), ("", 1))
        self.assertIn("refused", err)

    @proves("REQ_PROFILED")
    def test_clean_before_the_build_keeps_the_profiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            build = Path(tmp) / "docs" / "_build"
            (build / "profile").mkdir(parents=True)
            (build / "profile" / "fixtures.json").write_text("{}", encoding="utf-8")
            (build / "html").mkdir()
            (build / "html" / "stale.html").write_text("", encoding="utf-8")
            (build / "loose").write_text("", encoding="utf-8")
            check.clean_build(Path(tmp))
            self.assertEqual(sorted(p.name for p in build.iterdir()), ["profile"])
            self.assertTrue((build / "profile" / "fixtures.json").is_file())


FIXTURE = """expect: REQ_X
mutations:
  - file: docs/new.md
    create: "x"
"""


def run_runner(root: Path, argv: list[str], fail: str = "") -> tuple[str, str, int]:
    """run_fixtures.main with the copy and each copy's check stubbed; ``fail`` names the
    step that fails, ``base`` or ``control``."""

    def make_base(tmp: Path, _root: Path) -> Path:
        if fail == "base":
            raise OSError("no copy")
        (tmp / "base").mkdir()
        return tmp / "base"

    def fake_check(copy: Path, vale: Path, cache: Path):
        stages = [{"name": "tests", "seconds": 0.5}, {"name": "sphinx", "seconds": 0.25}]
        if copy.name == "base":
            return (1, [Finding("REQ_Y", "x", "y")], stages) if fail == "control" else (0, [], stages)
        return 1, [Finding("REQ_X", "docs/new.md", "found")], stages

    out, err = io.StringIO(), io.StringIO()
    with mock.patch.object(run_fixtures, "corpus_root", return_value=root), \
            mock.patch.object(run_fixtures, "vale_path", return_value=root / "vale"), \
            mock.patch.object(run_fixtures, "make_base", make_base), \
            mock.patch.object(run_fixtures, "run_check", fake_check), \
            redirect_stdout(out), redirect_stderr(err):
        code = run_fixtures.main(argv)
    return out.getvalue(), err.getvalue(), code


class FixturesProfile(unittest.TestCase):
    def corpus(self, tmp: str) -> Path:
        root = Path(tmp)
        (root / "tests" / "fixtures").mkdir(parents=True)
        for name in ("one", "two"):
            (root / "tests" / "fixtures" / f"{name}.yaml").write_text(FIXTURE, encoding="utf-8")
        return root

    @proves("REQ_PROFILED")
    def test_profile_lists_base_control_and_every_fixture_with_its_stages(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.corpus(tmp)
            _, _, code = run_runner(root, [])
            data = json.loads((root / "docs/_build/profile/fixtures.json")
                              .read_text(encoding="utf-8"))
        self.assertEqual(code, 0)
        self.assertEqual(data["command"], "fixtures")
        self.assertEqual([s["name"] for s in data["stages"]], ["base copy", "control", "fixtures"])
        self.assertIn("seconds", data["base"])
        self.assertEqual([s["name"] for s in data["control"]["stages"]], ["tests", "sphinx"])
        self.assertEqual(sorted(f["name"] for f in data["fixtures"]), ["one", "two"])
        for f in data["fixtures"]:
            self.assertTrue(f["ok"])
            self.assertEqual([s["name"] for s in f["stages"]], ["tests", "sphinx"])
            for key in ("seconds", "copy_seconds", "mutate_seconds", "check_seconds"):
                self.assertIsInstance(f[key], float)

    @proves("REQ_PROFILED")
    def test_unwritable_profile_changes_no_output_or_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.corpus(tmp)
            (root / "blocked").mkdir()
            for fail in ("", "base", "control"):
                plain = run_runner(root, [], fail)
                failed = run_runner(root, ["--profile", str(root / "blocked")], fail)
                self.assertEqual((plain[0], plain[2]), (failed[0], failed[2]))
                self.assertEqual(plain[1], "")
                self.assertEqual(failed[1].count("\n"), 1)
                self.assertIn("cannot write the profile", failed[1])

    @proves("REQ_PROFILED")
    def test_a_failed_base_copy_or_control_still_writes_the_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.corpus(tmp)
            profile = root / "docs/_build/profile/fixtures.json"
            _, _, code = run_runner(root, [], "base")
            data = json.loads(profile.read_text(encoding="utf-8"))
            self.assertEqual(code, 1)
            self.assertIn("seconds", data["base"])
            self.assertIsNone(data["control"])
            _, _, code = run_runner(root, [], "control")
            data = json.loads(profile.read_text(encoding="utf-8"))
        self.assertEqual(code, 1)
        self.assertFalse(data["control"]["ok"])
        self.assertEqual([s["name"] for s in data["control"]["stages"]], ["tests", "sphinx"])
        self.assertEqual(data["fixtures"], [])


class ProfileTable(unittest.TestCase):
    @proves("REQ_PROFILED")
    def test_both_kinds_print_as_tables(self):
        check_profile = {"version": 1, "command": "check", "total": 2.0,
                         "stages": [{"name": "sphinx", "seconds": 0.5},
                                    {"name": "tests", "seconds": 1.5, "reused": False,
                                     "why": "file docs/a.md"}]}
        fixtures_profile = {"version": 1, "command": "fixtures", "total": 9.0,
                            "stages": [{"name": "fixtures", "seconds": 8.0}],
                            "base": {"seconds": 0.1},
                            "control": {"seconds": 1.0, "ok": True,
                                        "stages": check_profile["stages"]},
                            "fixtures": [{"name": "one|pipe", "seconds": 3.0,
                                          "copy_seconds": 0.2, "check_seconds": 2.7,
                                          "ok": False, "stages": check_profile["stages"]}]}
        with tempfile.TemporaryDirectory() as tmp:
            paths = []
            for name, data in (("c.json", check_profile), ("f.json", fixtures_profile)):
                (Path(tmp) / name).write_text(json.dumps(data), encoding="utf-8")
                paths.append(str(Path(tmp) / name))
            out = io.StringIO()
            with redirect_stdout(out), mock.patch.object(profiler, "corpus_root",
                                                         return_value=Path(tmp).resolve()):
                code = profiler.main(paths)
        text = out.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("| tests | 1.500 | no: file docs/a.md |", text)
        self.assertLess(text.index("| tests |"), text.index("| sphinx |"))
        self.assertIn("| one\\|pipe | 3.000 | 0.200 | 2.700 | FAIL |", text)
        self.assertIn("| tests | 1.500 | 1 | 0 |", text)

    @proves("REQ_PROFILED")
    def test_a_file_that_is_not_a_profile_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.json"
            path.write_text("[]", encoding="utf-8")
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()) as err,                     mock.patch.object(profiler, "corpus_root", return_value=Path(tmp).resolve()):
                code = profiler.main([str(path)])
        self.assertEqual(code, 1)
        self.assertIn("not a profile", err.getvalue())

    @proves("REQ_PROFILED")
    def test_a_path_outside_the_repository_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as other:
            path = Path(other) / "c.json"
            path.write_text(json.dumps({"version": 1, "command": "check", "total": 0,
                                        "stages": []}), encoding="utf-8")
            with redirect_stdout(io.StringIO()) as out, redirect_stderr(io.StringIO()) as err,                     mock.patch.object(profiler, "corpus_root", return_value=Path(tmp).resolve()):
                code = profiler.main([str(path)])
        self.assertEqual((code, out.getvalue()), (1, ""))
        self.assertIn("refused", err.getvalue())


if __name__ == "__main__":
    unittest.main()
