"""REQ_RELEASE_TRUST: a version tag builds the wheel with pinned and hashed build
dependencies and SHA-pinned actions and attests its build provenance; a workflow that
always runs from main publishes it, only for a tag whose commit is on main, after the
`release` environment is approved, from the only job that may write, which verifies the
attestation and publishes the wheel and its SHA-256."""

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
    def test_a_version_tag_builds_with_read_access_and_only_attests(self):
        data = load(BUILD)
        self.assertEqual(data["name"], "release-build", "release-publish waits on this name")
        self.assertEqual(data["on"], {"push": {"tags": ["v*"]}})
        self.assertEqual(data["permissions"], {})
        self.assertEqual(list(data["jobs"]), ["build"])
        job = data["jobs"]["build"]
        # Read only, apart from the wheel's provenance (wyatt, 2026-11-10: "Attest in the
        # build job").
        self.assertEqual(job["permissions"], {"contents": "read", "id-token": "write",
                                              "attestations": "write"})
        steps = job["steps"]
        attest = index(steps, "actions/attest-build-provenance@")
        self.assertEqual(steps[attest]["with"], {"subject-path": "dist/trifecta-*.whl"})
        self.assertLess(index(steps, "pip wheel"), attest)
        self.assertLess(attest, index(steps, "actions/upload-artifact@"))
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
        guard = data["jobs"]["guard"]
        for condition in ("github.event.workflow_run.conclusion == 'success'",
                          "github.event.workflow_run.event == 'push'",
                          "github.event.workflow_run.path == '.github/workflows/release-build.yml'"):
            self.assertIn(condition, guard["if"])
        self.assertEqual(guard["permissions"], {"contents": "read"})
        self.assertNotIn("environment", guard, "a bad tag fails before anyone is asked")
        check = "\n".join(runs(guard["steps"]))
        self.assertIn('case "$TAG" in v[0-9]*)', check)
        self.assertIn('test "$tagged" = "$SHA"', check)
        self.assertIn("git/ref/heads/main", check)
        self.assertIn("compare/$SHA...$main", check)
        self.assertIn("ahead|identical", check)
        self.assertEqual(data["jobs"]["publish"]["needs"], "guard")

    @proves("REQ_RELEASE_TRUST")
    def test_only_the_publishing_job_writes_and_it_waits_for_the_environment(self):
        data = load(PUBLISH)
        self.assertEqual(data["permissions"], {})
        self.assertEqual(list(data["jobs"]), ["guard", "publish"])
        job = data["jobs"]["publish"]
        self.assertNotIn("if", job, "publish runs only when the guard passed")
        self.assertEqual(job["environment"], "release")
        self.assertEqual(job["permissions"], {"contents": "write", "attestations": "read",
                                              "actions": "read"})

    @proves("REQ_RELEASE_TRUST")
    def test_publishes_a_wheel_whose_attestation_names_the_tags_build(self):
        steps = load(PUBLISH)["jobs"]["publish"]["steps"]
        download = steps[index(steps, "actions/download-artifact@")]
        self.assertEqual(download["with"]["name"], "dist")
        self.assertEqual(download["with"]["run-id"], "${{ github.event.workflow_run.id }}")
        self.assertEqual(download["with"]["github-token"], "${{ github.token }}")
        verify = index(steps, "for wheel in dist/trifecta-*.whl")
        check = steps[verify]["run"]
        for part in ('gh attestation verify "$wheel" --repo "$GITHUB_REPOSITORY"',
                     '--cert-identity "https://github.com/$GITHUB_REPOSITORY/.github/workflows/'
                     'release-build.yml@refs/tags/$TAG"',
                     '--source-ref "refs/tags/$TAG"', '--source-digest "$SHA"',
                     "--deny-self-hosted-runners", "sha256sum -c SHA256SUMS"):
            self.assertIn(part, check)
        publish = index(steps, "gh release create")
        command = steps[publish]["run"]
        for part in ("dist/trifecta-*.whl", "dist/SHA256SUMS", "--verify-tag",
                     '--jq .sha)" = "$SHA"', "--notes-file",
                     "--cert-identity https://github.com/$GITHUB_REPOSITORY/.github/workflows/"
                     "release-build.yml@refs/tags/$TAG",
                     "--source-ref refs/tags/$TAG", "--source-digest $SHA",
                     "--deny-self-hosted-runners"):
            self.assertIn(part, command)
        self.assertLess(index(steps, "actions/download-artifact@"), verify)
        self.assertLess(verify, publish)


class Settings(unittest.TestCase):
    """The exported settings the workflows rely on (.github/settings/)."""

    @proves("REQ_RELEASE_TRUST")
    def test_release_environment_needs_a_reviewer_and_deploys_only_from_main(self):
        import json
        settings = WORKFLOWS.parent / "settings"
        env = json.loads((settings / "environments.json").read_text(encoding="utf-8"))["release"]
        self.assertIs(env["can_admins_bypass"], False)
        self.assertEqual(env["deployment_branch_policies"], [{"name": "main", "type": "branch"}])
        self.assertEqual(env["deployment_branch_policy"],
                         {"custom_branch_policies": True, "protected_branches": False})
        reviewers = [r for r in env["protection_rules"] if r["type"] == "required_reviewers"]
        self.assertEqual(len(reviewers), 1)
        self.assertTrue(reviewers[0]["reviewers"])
        security = json.loads((settings / "security.json").read_text(encoding="utf-8"))
        self.assertIs(security["immutable_releases"]["enabled"], True)


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
