"""REQ_ADOPTION_GUIDE: the README opens with the steps to adopt the toolchain. The test that
runs those steps in an empty repository is in ``test_adoption_guide``, which is never
stored, so this module is stored."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from trifecta.testing import proves

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


if __name__ == "__main__":
    unittest.main()
