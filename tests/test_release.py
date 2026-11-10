"""REQ_RELEASE_TRUST: the release workflow builds from a version tag on main with pinned and
hashed build dependencies and SHA-pinned actions, waits for the `release` environment, lets
only the publishing job write, and publishes a provenance attestation."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

import yaml

from trifecta.testing import proves

WORKFLOW = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "release.yml"


def load() -> dict:
    data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    # PyYAML reads the bare key `on` as True.
    data["on"] = data.pop(True, data.get("on"))
    return data


class ReleaseWorkflow(unittest.TestCase):
    @proves("REQ_RELEASE_TRUST")
    def test_runs_only_on_a_version_tag_whose_commit_is_on_main(self):
        data = load()
        self.assertEqual(data["on"], {"push": {"tags": ["v*"]}})
        runs = "\n".join(s.get("run", "") for s in data["jobs"]["build"]["steps"])
        self.assertIn('git merge-base --is-ancestor "$GITHUB_SHA" origin/main', runs)
        self.assertIn('test "$TAG" = "v$version"', runs)

    @proves("REQ_RELEASE_TRUST")
    def test_build_dependencies_are_the_hashed_lock_and_nothing_else(self):
        runs = [s.get("run", "") for s in load()["jobs"]["build"]["steps"]]
        self.assertIn("python -m pip install --require-hashes -r requirements.lock", runs)
        build = [r for r in runs if "pip wheel" in r]
        self.assertEqual(len(build), 1)
        for flag in ("--no-deps", "--no-build-isolation", "--no-index"):
            self.assertIn(flag, build[0])

    @proves("REQ_RELEASE_TRUST")
    def test_every_action_is_pinned_by_commit_sha(self):
        uses = re.findall(r"uses: (\S+)", WORKFLOW.read_text(encoding="utf-8"))
        self.assertTrue(uses)
        for action in uses:
            self.assertRegex(action, r"^actions/[\w.-]+@[0-9a-f]{40}$")

    @proves("REQ_RELEASE_TRUST")
    def test_only_the_publishing_job_writes_and_it_waits_for_the_environment(self):
        data = load()
        self.assertEqual(data["permissions"], {})
        jobs = data["jobs"]
        self.assertEqual(set(jobs), {"build", "publish"})
        self.assertEqual(jobs["build"]["permissions"], {"contents": "read"})
        self.assertNotIn("environment", jobs["build"])
        self.assertEqual(jobs["publish"]["environment"], "release")
        self.assertEqual(jobs["publish"]["needs"], "build")
        self.assertIn("write", jobs["publish"]["permissions"].values())
        for step in jobs["build"]["steps"]:
            if "actions/checkout@" in step.get("uses", ""):
                self.assertIs(step["with"]["persist-credentials"], False)

    @proves("REQ_RELEASE_TRUST")
    def test_publishes_a_provenance_attestation_and_never_creates_a_tag(self):
        steps = load()["jobs"]["publish"]["steps"]
        attest = [s for s in steps if "actions/attest-build-provenance@" in s.get("uses", "")]
        self.assertEqual(len(attest), 1)
        self.assertEqual(attest[0]["with"]["subject-path"], "dist/trifecta-*.whl")
        publish = [s["run"] for s in steps if "gh release create" in s.get("run", "")]
        self.assertEqual(len(publish), 1)
        self.assertIn("--verify-tag", publish[0])
        self.assertLess(steps.index(attest[0]), [s.get("run", "") for s in steps].index(publish[0]))


if __name__ == "__main__":
    unittest.main()
