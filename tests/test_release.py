"""REQ_RELEASE_TRUST: a version tag builds the wheel with pinned and hashed build
dependencies and SHA-pinned actions; a workflow that always runs from main publishes it,
only for a tag whose commit is on main, after the `release` environment is approved, from
the only job that may write, with its SHA-256 and a provenance attestation."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

import yaml

from trifecta.testing import proves

WORKFLOWS = Path(__file__).resolve().parent.parent / ".github" / "workflows"
BUILD, PUBLISH = WORKFLOWS / "release-build.yml", WORKFLOWS / "release-publish.yml"


def load(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["on"] = data.pop(True, data.get("on"))  # PyYAML reads the bare key `on` as True
    return data


def runs(steps: list[dict]) -> list[str]:
    return [s.get("run", "") for s in steps]


def index(steps: list[dict], text: str) -> int:
    found = [i for i, s in enumerate(steps) if text in s.get("run", "") or text in s.get("uses", "")]
    assert len(found) == 1, (text, found)
    return found[0]


class ReleaseBuild(unittest.TestCase):
    @proves("REQ_RELEASE_TRUST")
    def test_a_version_tag_builds_with_read_access_only(self):
        data = load(BUILD)
        self.assertEqual(data["on"], {"push": {"tags": ["v*"]}})
        self.assertEqual(data["permissions"], {})
        self.assertEqual(list(data["jobs"]), ["build"])
        job = data["jobs"]["build"]
        self.assertEqual(job["permissions"], {"contents": "read"})
        self.assertNotIn("environment", job)
        checkout = job["steps"][index(job["steps"], "actions/checkout@")]
        self.assertIs(checkout["with"]["persist-credentials"], False)

    @proves("REQ_RELEASE_TRUST")
    def test_only_the_hashed_build_backend_is_installed_and_nothing_fetched(self):
        steps = load(BUILD)["jobs"]["build"]["steps"]
        install = steps[index(steps, "--require-hashes")]["run"]
        self.assertIn("grep '^flit_core==' requirements.lock", install)
        self.assertIn("--no-deps", install)
        wheel = index(steps, "pip wheel")
        for flag in ("--no-deps", "--no-build-isolation", "--no-index"):
            self.assertIn(flag, steps[wheel]["run"])
        self.assertLess(index(steps, 'test "$TAG" = "v$version"'), wheel)
        self.assertLess(index(steps, "--require-hashes"), wheel)
        sums = index(steps, "sha256sum trifecta-*.whl > SHA256SUMS")
        self.assertLess(wheel, sums)
        self.assertLess(sums, index(steps, "actions/upload-artifact@"))


class ReleasePublish(unittest.TestCase):
    @proves("REQ_RELEASE_TRUST")
    def test_publishes_only_a_successful_tag_build_from_main(self):
        data = load(PUBLISH)
        self.assertEqual(data["on"], {"workflow_run": {"workflows": ["release-build"],
                                                       "types": ["completed"]}})
        job = data["jobs"]["publish"]
        for condition in ("github.event.workflow_run.conclusion == 'success'",
                          "github.event.workflow_run.event == 'push'",
                          "github.event.workflow_run.path == '.github/workflows/release-build.yml'"):
            self.assertIn(condition, job["if"])
        steps = job["steps"]
        guard = steps[index(steps, "compare/$SHA...main")]["run"]
        self.assertIn('case "$TAG" in v[0-9]*)', guard)
        self.assertIn('test "$tagged" = "$SHA"', guard)
        self.assertIn("ahead|identical", guard)
        self.assertEqual(index(steps, "compare/$SHA...main"), 0, "the guard comes first")

    @proves("REQ_RELEASE_TRUST")
    def test_only_the_publishing_job_writes_and_it_waits_for_the_environment(self):
        data = load(PUBLISH)
        self.assertEqual(data["permissions"], {})
        self.assertEqual(list(data["jobs"]), ["publish"])
        job = data["jobs"]["publish"]
        self.assertEqual(job["environment"], "release")
        self.assertEqual(job["permissions"]["contents"], "write")

    @proves("REQ_RELEASE_TRUST")
    def test_publishes_the_wheel_its_sha256_and_an_attestation_to_the_existing_tag(self):
        steps = load(PUBLISH)["jobs"]["publish"]["steps"]
        download = steps[index(steps, "actions/download-artifact@")]
        self.assertEqual(download["with"]["run-id"], "${{ github.event.workflow_run.id }}")
        attest = index(steps, "actions/attest-build-provenance@")
        self.assertEqual(steps[attest]["with"]["subject-path"], "dist/trifecta-*.whl")
        publish = index(steps, "gh release create")
        command = steps[publish]["run"]
        for part in ("dist/trifecta-*.whl", "dist/SHA256SUMS", "--verify-tag",
                     '--jq .sha)" = "$SHA"', "--signer-workflow"):
            self.assertIn(part, command)
        self.assertLess(attest, publish)


class Pins(unittest.TestCase):
    @proves("REQ_RELEASE_TRUST")
    def test_every_action_is_pinned_by_commit_sha(self):
        for path in (BUILD, PUBLISH):
            uses = re.findall(r"uses: (\S+)", path.read_text(encoding="utf-8"))
            self.assertTrue(uses, path)
            for action in uses:
                self.assertRegex(action, r"^actions/[\w.-]+@[0-9a-f]{40}$")


if __name__ == "__main__":
    unittest.main()
