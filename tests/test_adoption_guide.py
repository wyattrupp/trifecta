"""REQ_ADOPTION_GUIDE: the README's adoption steps, run in an empty repository, produce a
corpus whose check passes. Moved from ``test_adoption`` unchanged (COMP_LIFTED_REASONS,
DEC_0034): it runs the guide through bash, with pip, make, Vale and the network behind
it, so this module is never stored, and ``test_adoption``, which keeps the rest, is.

The test runs the README's own block, with the wheel built from the workspace in place of
the release download and its attestation check, which need a published release."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

from tests.test_adoption import ROOT, commands, guide
from trifecta.testing import only_on, proves
from trifecta.toolchain import program_env, vale_path


class AdoptionGuide(unittest.TestCase):
    @proves("REQ_ADOPTION_GUIDE")
    @only_on("posix")
    def test_the_steps_produce_a_corpus_whose_check_passes(self):
        version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
        # The release download and its attestation need a published release; the wheel
        # built from the workspace stands in for both.
        steps = [c for c in commands(guide()) if not c.startswith(("version=", "gh "))]
        self.assertEqual(len(steps), len(commands(guide())) - 3)
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home, repo, dist = base / "home", base / "repo", base / "dist"
            home.mkdir()
            subprocess.run([sys.executable, "-m", "pip", "wheel", "--no-deps",
                            "--no-build-isolation", "-q", "-w", str(dist), str(ROOT)], check=True)
            (wheel,) = dist.glob(f"trifecta-{version}-*.whl")
            repo.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True, env=program_env())
            shutil.copy2(wheel, repo / wheel.name)
            # This repository's Vale, so the check does not download it again.
            (repo / "bin").mkdir()
            vale = vale_path(ROOT)
            for path in [vale, *vale.parent.glob(".vale-stamp-*")]:
                shutil.copy2(path, repo / "bin" / path.name)
            # init refuses the placeholder a reader replaces with their own name.
            steps = [c.replace("@<you>", "@someone") for c in steps]
            script = "\n".join([steps[0], steps[1], f'version="{version}"', *steps[2:]])
            # Nothing of the run this test is inside: not its Python, its Vale, or the make
            # variables (BASE=...) a `make check` hands down through MAKEFLAGS.
            env = {k: v for k, v in os.environ.items()
                   if not k.startswith(("PYTHON", "VIRTUAL_ENV", "TRIFECTA_"))
                   and k not in ("MAKEFLAGS", "MFLAGS", "MAKELEVEL", "MAKEOVERRIDES", "BASE")}
            # The test's own pip cache, so copies that run it again do not download again.
            env["PIP_CACHE_DIR"] = os.environ.get("PIP_CACHE_DIR") or str(Path.home() / ".cache" / "pip")
            env["HOME"] = str(home)
            done = subprocess.run(["bash", "-e", "-c", script], cwd=repo, env=env,
                                  capture_output=True, encoding="utf-8", errors="replace")
            # The tail: the check reports only the start of a failure's message.
            findings = [l for l in done.stdout.splitlines() if l.count("\t") >= 2]
            self.assertEqual(done.returncode, 0, " | ".join(findings)[-300:]
                             or " ".join(done.stderr.split())[-260:])
            self.assertFalse((repo / wheel.name).exists())
            lock = (repo / "requirements.lock").read_text(encoding="utf-8").splitlines()[0]
            self.assertIn(f"/releases/download/v{version}/{wheel.name}", lock)



if __name__ == "__main__":
    unittest.main()
