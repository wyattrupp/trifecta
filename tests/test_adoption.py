"""REQ_ADOPTION_GUIDE: the README opens with the steps to adopt the toolchain, and those
steps, run in an empty repository, produce a corpus whose check passes.

The test runs the README's own block, with the wheel built from the workspace in place of
the release download and its attestation check, which need a published release."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

from trifecta.testing import only_on, proves
from trifecta.toolchain import vale_path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
MARKER = "<!-- adoption-steps:"


def guide() -> str:
    """The adoption block: the first sh block after the marker."""
    text = README.read_text(encoding="utf-8")
    start = text.index("```sh\n", text.index(MARKER)) + len("```sh\n")
    return text[start:text.index("```", start)]


def commands(block: str) -> list[str]:
    """The block's commands, each with its continuation lines joined."""
    out, current = [], ""
    for line in block.splitlines():
        current += line.rstrip("\\") + (" " if line.endswith("\\") else "")
        if not line.endswith("\\"):
            if current.strip() and not current.lstrip().startswith("#"):
                out.append(current.strip())
            current = ""
    return out


class AdoptionGuide(unittest.TestCase):
    @proves("REQ_ADOPTION_GUIDE")
    def test_the_readme_opens_with_the_adoption_steps(self):
        text = README.read_text(encoding="utf-8")
        headings = re.findall(r"^## (.+)$", text, re.M)
        self.assertEqual(headings[0], "Run this in your repo")
        steps = commands(guide())
        # One subshell that stops at the first failure, so a wheel that does not verify
        # is never installed.
        self.assertEqual((steps[0], steps[1], steps[-1]), ("(", "set -euo pipefail", ")"))
        verify = next(i for i, c in enumerate(steps) if c.startswith("gh attestation verify"))
        self.assertIn("--source-digest", steps[verify])
        install = next(i for i, c in enumerate(steps) if "pip install --no-deps" in c)
        self.assertLess(verify, install)
        self.assertIn("--only-binary :all:", next(c for c in steps if "--require-hashes" in c))
        self.assertTrue(any(c.startswith("trifecta init --codeowner @<you>") for c in steps))
        self.assertEqual(steps[-2], "make check")

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
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            shutil.copy2(wheel, repo / wheel.name)
            # This repository's Vale, so the check does not download it again.
            (repo / "bin").mkdir()
            vale = vale_path(ROOT)
            for path in [vale, *vale.parent.glob(".vale-stamp-*")]:
                shutil.copy2(path, repo / "bin" / path.name)
            # init refuses the placeholder a reader replaces with their own name.
            steps = [c.replace("@<you>", "@someone") for c in steps]
            script = "\n".join([steps[0], steps[1], f'version="{version}"', *steps[2:]])
            env = {k: v for k, v in os.environ.items()
                   if not k.startswith(("PYTHON", "VIRTUAL_ENV", "TRIFECTA_"))}
            # The test's own pip cache, so copies that run it again do not download again.
            env["PIP_CACHE_DIR"] = os.environ.get("PIP_CACHE_DIR") or str(Path.home() / ".cache" / "pip")
            env["HOME"] = str(home)
            done = subprocess.run(["bash", "-e", "-c", script], cwd=repo, env=env,
                                  capture_output=True, encoding="utf-8", errors="replace")
            self.assertEqual(done.returncode, 0, (done.stdout + done.stderr)[-3000:])
            self.assertFalse((repo / wheel.name).exists())
            lock = (repo / "requirements.lock").read_text(encoding="utf-8").splitlines()[0]
            self.assertIn(f"/releases/download/v{version}/{wheel.name}", lock)


if __name__ == "__main__":
    unittest.main()
