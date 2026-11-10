"""`trifecta init`: REQ_INIT_PASSES, REQ_INIT_SAFE, REQ_NO_SECRETS_IN_TREE and
REQ_SELF_TESTS_SCOPED. Each test runs in an empty directory after `git init`."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from trifecta import init as init_module
from trifecta.findings import child_env
from trifecta.testing import only_on, proves
from trifecta.toolchain import VALE_ENV, vale_path

REPO = Path(__file__).resolve().parent.parent
URL = "https://github.com/wyattrupp/trifecta/releases/download/v0.1.0/trifecta-0.1.0-py3-none-any.whl"
SHA = "a" * 64
ARGS = ["--codeowner", "@someone", "--wheel-url", URL, "--wheel-sha256", SHA]


def trifecta(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    env = {**child_env(Path(init_module.__file__).resolve().parent.parent),
           VALE_ENV: str(vale_path(REPO))}
    env.pop("TRIFECTA_PROOF_CACHE", None)
    return subprocess.run([sys.executable, "-m", "trifecta", *args], cwd=cwd, env=env,
                          capture_output=True, encoding="utf-8", errors="replace")


def snapshot(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in root.rglob("*") if p.is_file() and ".git" not in p.relative_to(root).parts}


class Repo:
    """An empty repository after `git init`, in a temporary directory."""

    def __enter__(self) -> Path:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve() / "repo"
        self.root.mkdir()
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        return self.root

    def __exit__(self, *exc) -> None:
        self.tmp.cleanup()


def run_init(root: Path) -> tuple[list[str], list[str]]:
    """Run init in ``root``; return what it wrote and what it changed."""
    return init_module.init(root, "@someone", URL, SHA)


class InitPasses(unittest.TestCase):
    @proves("REQ_INIT_PASSES", "REQ_SELF_TESTS_SCOPED")
    def test_bare_init_passes_with_the_audit_off(self):
        with Repo() as root:
            done = trifecta(root, "init", *ARGS)
            self.assertEqual(done.returncode, 0, done.stderr)
            checked = trifecta(root, "check")
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            switches = (root / "docs/_build/html/trifecta.json").read_text(encoding="utf-8")
            self.assertEqual(switches, '{"fixture_audit": false}')
            self.assertFalse(any(p.suffix == ".md" and p.parent.name in init_module.TYPED_DIRS
                                 for p in (root / "docs").rglob("*")))

    @proves("REQ_INIT_PASSES")
    def test_init_plus_a_draft_of_each_type_passes(self):
        with Repo() as root:
            self.assertEqual(trifecta(root, "init", *ARGS).returncode, 0)
            for kind in ("rfc", "decision", "design"):
                self.assertEqual(trifecta(root, "new", kind, f"first-{kind}").returncode, 0)
            rfc = next((root / "docs/rfcs").glob("0001-*.md"))
            text = rfc.read_text(encoding="utf-8")
            rfc.write_text(text.replace("## Requirements\n\nTODO.\n", "## Requirements\n\n"
                                        ":::{req} A part exists\n:id: REQ_PART\nA part MUST exist.\n"
                                        ":::\n", 1), encoding="utf-8", newline="\n")
            design = next((root / "docs/design").glob("0001-*.md"))
            text = design.read_text(encoding="utf-8")
            design.write_text(text.replace("## Components\n", "## Components\n\n:::{component} Part\n"
                                           ":id: COMP_PART\n:satisfies: REQ_PART\nA part.\n:::\n", 1),
                              encoding="utf-8", newline="\n")
            planned = trifecta(root, "new", "plan", "first-plan", "--implements", "DES_0001")
            self.assertEqual(planned.returncode, 0, planned.stdout + planned.stderr)
            checked = trifecta(root, "check")
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)


class AuditScoped(unittest.TestCase):
    @proves("REQ_SELF_TESTS_SCOPED")
    def test_unproven_requirement_is_reported_only_where_the_audit_is_on(self):
        from trifecta.check import audit_stage
        needs = {
            "REQ_X": {"id": "REQ_X", "type": "req", "satisfies_back": ["COMP_X"]},
            "COMP_X": {"id": "COMP_X", "type": "component", "doc_status": "implemented"},
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            html = root / "docs" / "_build" / "html"
            html.mkdir(parents=True)
            self.assertEqual(audit_stage(root, needs, set()), [], "no record: the audit is off")
            for on in (False, True):
                (html / "trifecta.json").write_text(f'{{"fixture_audit": {str(on).lower()}}}',
                                                    encoding="utf-8")
                found = audit_stage(root, needs, set())
                self.assertEqual(bool(found), on, found)
            self.assertEqual(audit_stage(root, needs, {"REQ_X"}), [])


class InitSafe(unittest.TestCase):
    def refused(self, root: Path) -> str:
        before = snapshot(root)
        with self.assertRaises(init_module.Refused) as caught:
            run_init(root)
        self.assertEqual(snapshot(root), before, "a refused run wrote something")
        return str(caught.exception)

    @proves("REQ_INIT_SAFE")
    def test_existing_file_is_refused(self):
        with Repo() as root:
            (root / "Makefile").write_text("all:\n", encoding="utf-8")
            self.assertIn("Makefile exists", self.refused(root))

    @proves("REQ_INIT_SAFE")
    def test_link_and_dangling_link_are_refused(self):
        for target in ("elsewhere.txt", "missing.txt"):
            with self.subTest(target), Repo() as root:
                if target == "elsewhere.txt":
                    (root / target).write_text("x", encoding="utf-8")
                os.symlink(root / target, root / "Makefile")
                self.assertIn("Makefile is a link", self.refused(root))

    @proves("REQ_INIT_SAFE")
    def test_linked_parent_and_outside_path_are_refused(self):
        with Repo() as root, tempfile.TemporaryDirectory() as outside:
            os.symlink(outside, root / "docs", target_is_directory=True)
            self.assertIn("docs/ is a link", self.refused(root))
            self.assertEqual(os.listdir(outside), [])

    @proves("REQ_INIT_SAFE")
    @only_on("nt")
    def test_junctioned_parent_is_refused(self):
        import _winapi
        with Repo() as root, tempfile.TemporaryDirectory() as outside:
            _winapi.CreateJunction(outside, str(root / "docs"))
            self.assertIn("docs/ is a link", self.refused(root))
            self.assertEqual(os.listdir(outside), [])

    def swap_parent(self, junction: bool) -> None:
        with Repo() as root, tempfile.TemporaryDirectory() as outside:
            def swap(rel: str) -> None:
                if rel == "docs/index.md":
                    shutil.rmtree(root / "docs")
                    if junction:
                        import _winapi
                        _winapi.CreateJunction(outside, str(root / "docs"))
                    else:
                        os.symlink(outside, root / "docs", target_is_directory=True)
            with mock.patch.object(init_module, "before_create", swap):
                with self.assertRaises(init_module.Refused):
                    run_init(root)
            self.assertEqual(os.listdir(outside), [])
            self.assertFalse((root / "Makefile").exists())

    @proves("REQ_INIT_SAFE")
    def test_parent_swapped_for_a_link_before_the_create_is_refused(self):
        self.swap_parent(junction=False)

    @proves("REQ_INIT_SAFE")
    @only_on("nt")
    def test_parent_swapped_for_a_junction_before_the_create_is_refused(self):
        self.swap_parent(junction=True)

    @proves("REQ_INIT_SAFE")
    def test_parent_swapped_after_its_file_then_a_failure_leaves_the_target_untouched(self):
        with Repo() as root, tempfile.TemporaryDirectory() as outside:
            (Path(outside) / "conf.py").write_text("theirs", encoding="utf-8")

            def after(rel: str) -> None:
                if rel == "docs/conf.py":
                    (root / "docs").rename(root / "docs-moved")
                    os.symlink(outside, root / "docs", target_is_directory=True)
                if rel == "Makefile":
                    raise OSError("the disk is full")
            with mock.patch.object(init_module, "after_create", after):
                with self.assertRaises(init_module.Refused) as caught:
                    run_init(root)
            self.assertEqual((Path(outside) / "conf.py").read_text(encoding="utf-8"), "theirs")
            self.assertIn("could not remove", str(caught.exception))

    @proves("REQ_INIT_SAFE")
    def test_a_failed_create_removes_every_file_the_run_created(self):
        with Repo() as root:
            before = snapshot(root)

            def fail(rel: str) -> None:
                if rel == ".github/CODEOWNERS":
                    raise OSError("the disk is full")
            with mock.patch.object(init_module, "before_create", fail):
                with self.assertRaises(init_module.Refused):
                    run_init(root)
            self.assertEqual(snapshot(root), before)
            self.assertEqual(sorted(p.name for p in root.iterdir()), [".git"])

    @proves("REQ_INIT_SAFE")
    def test_second_init_is_refused_and_changes_nothing(self):
        with Repo() as root:
            run_init(root)
            self.assertIn("exists", self.refused(root))

    @proves("REQ_INIT_SAFE")
    def test_workflow_is_read_only_without_credentials_and_pinned(self):
        with Repo() as root:
            run_init(root)
            workflow = (root / ".github/workflows/check.yml").read_text(encoding="utf-8")
        self.assertIn("permissions:\n  contents: read\n", workflow)
        self.assertEqual(workflow.count("permissions:"), 1)
        self.assertNotIn("write", workflow.split("jobs:")[0])
        uses = re.findall(r"uses: (\S+)", workflow)
        self.assertTrue(uses)
        for action in uses:
            self.assertRegex(action, r"^[\w.-]+/[\w.-]+@[0-9a-f]{40}$")
        self.assertEqual(workflow.count("persist-credentials: false"),
                         workflow.count("actions/checkout@"))

    @proves("REQ_INIT_PASSES")
    def test_workflow_checks_a_first_push_and_refuses_a_missing_base(self):
        import yaml
        from tests.test_planning import git_bash
        steps = yaml.safe_load(init_module._workflow())["jobs"]["check"]["steps"]
        script = next(s["run"] for s in steps if "make check" in s.get("run", ""))
        bash = git_bash()
        zero = "0" * 40

        def run(root: Path, before: str) -> subprocess.CompletedProcess:
            stub = root.parent / "bin"
            stub.mkdir(exist_ok=True)
            (stub / "make").write_text('#!/bin/sh\necho "make $*"\n', encoding="utf-8", newline="\n")
            os.chmod(stub / "make", 0o755)
            env = {**os.environ, "EVENT": "push", "BASE_REF": "", "BEFORE": before,
                   "PATH": f"{stub.as_posix()}{os.pathsep}{os.environ['PATH']}"}
            return subprocess.run([bash, "-e", "-c", script], cwd=root, env=env,
                                  capture_output=True, encoding="utf-8")

        with Repo() as root:
            git = ["git", "-c", "user.name=t", "-c", "user.email=t@localhost"]
            subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", "first"], cwd=root, check=True)
            first = run(root, zero)
            self.assertEqual((first.returncode, first.stdout.strip()), (0, "make check"))
            self.assertEqual(run(root, "1" * 40).returncode, 1,
                             "a missing base is refused even at the first commit")
            base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True,
                                  encoding="utf-8", check=True).stdout.strip()
            subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", "second"], cwd=root, check=True)
            self.assertEqual(run(root, zero).returncode, 1, "a new branch's push is refused")
            later = run(root, base)
            self.assertEqual((later.returncode, later.stdout.strip()), (0, f"make check BASE={base}"))

    @proves("REQ_INIT_SAFE")
    def test_workflow_pins_are_this_repositorys_own(self):
        ours = (REPO / ".github/workflows/check.yml").read_text(encoding="utf-8")
        for pin in init_module.ACTIONS.values():
            self.assertIn(f"uses: {pin}", ours)


#: Credential shapes: GitHub tokens, AWS keys, private keys, Slack tokens, and a URL that
#: carries a user and password.
TOKENS = re.compile(rb"gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}"
                    rb"|-----BEGIN [A-Z ]*PRIVATE KEY|xox[abpr]-[A-Za-z0-9-]{10,}"
                    rb"|https?://[^/\s:@]+:[^/\s@]+@")


class NoSecrets(unittest.TestCase):
    @proves("REQ_NO_SECRETS_IN_TREE")
    def test_nothing_init_writes_matches_a_token_pattern(self):
        with Repo() as root:
            run_init(root)
            for rel, data in snapshot(root).items():
                with self.subTest(rel):
                    self.assertIsNone(TOKENS.search(data))

    @proves("REQ_NO_SECRETS_IN_TREE")
    def test_the_token_patterns_catch_a_token(self):
        self.assertIsNotNone(TOKENS.search(b"x ghp_" + b"a" * 36))
        self.assertIsNotNone(TOKENS.search(b"https://user:secret@github.com/x"))


if __name__ == "__main__":
    unittest.main()
