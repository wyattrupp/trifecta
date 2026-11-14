"""REQ_INIT_PASSES and REQ_INIT_SAFE: the tests of `trifecta init` that do what the
recorder refuses, moved from ``test_init`` unchanged (COMP_LIFTED_REASONS): its bash test,
which runs the workflow's script through bash (DEC_0034), and its Windows junction tests.

Each refuses the run of this module under its own recorder, so this module is never
stored, and ``test_init``, which keeps the rest, is.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from trifecta import init as init_module
from trifecta.testing import only_on, proves
from trifecta.toolchain import program_env

from tests import test_init
from tests.test_init import Repo


class InitSafe(unittest.TestCase):
    refused, swap_parent = test_init.InitSafe.refused, test_init.InitSafe.swap_parent

    @proves("REQ_INIT_SAFE")
    @only_on("nt")
    def test_junctioned_parent_is_refused(self):
        import _winapi
        with Repo() as root, tempfile.TemporaryDirectory() as outside:
            _winapi.CreateJunction(outside, str(root / "docs"))
            self.assertIn("docs/ is a link", self.refused(root))
            self.assertEqual(os.listdir(outside), [])

    @proves("REQ_INIT_SAFE")
    @only_on("nt")
    def test_parent_swapped_for_a_junction_before_the_create_is_refused(self):
        self.swap_parent(junction=True)

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
            subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", "first"], cwd=root, check=True,
                           env=program_env())
            first = run(root, zero)
            self.assertEqual((first.returncode, first.stdout.strip()), (0, "make check"))
            self.assertEqual(run(root, "1" * 40).returncode, 1,
                             "a missing base is refused even at the first commit")
            base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True,
                                  encoding="utf-8", check=True, env=program_env()).stdout.strip()
            subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", "second"], cwd=root, check=True,
                           env=program_env())
            self.assertEqual(run(root, zero).returncode, 1, "a new branch's push is refused")
            later = run(root, base)
            self.assertEqual((later.returncode, later.stdout.strip()), (0, f"make check BASE={base}"))


if __name__ == "__main__":
    unittest.main()
