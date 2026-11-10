"""REQ_ONE_PACKAGE: the wheel holds every part of the toolchain, and the check accepts the
package's own release URL. Task 3 of PLAN_0003 adds the declaration the check reads."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from trifecta.check import package_url_problem

ROOT = Path(__file__).resolve().parent.parent

#: Every part REQ_ONE_PACKAGE lists, as a path in the wheel.
PARTS = {
    "the extension": "trifecta/ext/__init__.py",
    "the ontology and native graph rules": "trifecta/ext/ontology.py",
    "the plan rules": "trifecta/ext/plans.py",
    "the review digest": "trifecta/ext/digest.py",
    "the RFC schema": "trifecta/ext/schemas/rfc.json",
    "the decision schema": "trifecta/ext/schemas/decision.json",
    "the design schema": "trifecta/ext/schemas/design.json",
    "the plan schema": "trifecta/ext/schemas/plan.json",
    "the normative Vale style": "trifecta/styles/Trifecta/REQ_NORMATIVE_SCOPE.yml",
    "the decision-language Vale style": "trifecta/styles/Trifecta/REQ_NO_DECISION_LANGUAGE.yml",
    "the normative Vale configuration": "trifecta/vale/normative.ini",
    "the prose Vale configuration": "trifecta/vale/prose.ini",
    "the command": "trifecta/cli.py",
    "the pipeline": "trifecta/check.py",
    "the fixture runner": "trifecta/run_fixtures.py",
    "the setup command and its Vale table": "trifecta/setup.py",
    "the new command": "trifecta/new.py",
    "the next command": "trifecta/next.py",
    "the review command": "trifecta/review.py",
}


class WheelHoldsTheToolchain(unittest.TestCase):
    def test_every_part_is_in_the_wheel(self):
        with tempfile.TemporaryDirectory() as out:
            subprocess.run([sys.executable, "-m", "pip", "wheel", "--no-deps",
                            "--no-build-isolation", "-q", "-w", out, str(ROOT)], check=True)
            (wheel,) = Path(out).glob("trifecta-*.whl")
            with zipfile.ZipFile(wheel) as archive:
                names = set(archive.namelist())
                entry_points = next(n for n in names if n.endswith(".dist-info/entry_points.txt"))
                scripts = archive.read(entry_points).decode("utf-8")
        for part, path in PARTS.items():
            with self.subTest(part=part):
                self.assertIn(path, names)
        self.assertIn("trifecta=trifecta.cli:main", scripts.replace(" ", ""))


class LockLineAcceptsTheOwnRelease(unittest.TestCase):
    def test_own_release_wheel_is_accepted(self):
        url = ("https://github.com/wyattrupp/trifecta/releases/download/v0.1.0/"
               "trifecta-0.1.0-py3-none-any.whl")
        self.assertIsNone(package_url_problem(url))


if __name__ == "__main__":
    unittest.main()
