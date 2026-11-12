"""REQ_REUSE_SOUND, REQ_REUSE_SCOPED for COMP_CI_CACHE: setup checks the SHA-256 of the
Vale archive it kept before using it; the check workflow caches downloads only, runs the
check with --fresh, runs the fixtures on main's push runs from an empty store it uploads,
and has a pull request's run take only that store, found by run ID.
"""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

from trifecta import setup
from trifecta.testing import proves

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "check.yml"
PINNED = re.compile(r"[\w-]+/[\w/-]+@[0-9a-f]{40}")


def load() -> dict:
    data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    data["on"] = data.pop(True, data.get("on"))  # PyYAML reads the bare key `on` as True
    return data


class KeptArchive(unittest.TestCase):
    DATA = b"the archive"
    NAME, SHA, SIZE = "vale.zip", hashlib.sha256(DATA).hexdigest(), len(DATA)

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.kept = Path(self._tmp.name) / "downloads"
        patch = mock.patch.dict(os.environ, {setup.DOWNLOADS_ENV: str(self.kept)})
        patch.start()
        self.addCleanup(patch.stop)

    def archive(self, served: bytes = DATA):
        with mock.patch.object(setup, "_fetch", return_value=served) as fetch:
            data = setup.archive(self.NAME, self.SHA, self.SIZE)
        return data, fetch.call_count

    @proves("REQ_REUSE_SOUND")
    def test_a_download_is_kept_and_used_once_its_hash_is_checked(self):
        self.assertEqual(self.archive(), (self.DATA, 1))
        self.assertEqual((self.kept / self.NAME).read_bytes(), self.DATA)
        self.assertEqual(self.archive(), (self.DATA, 0))

    @proves("REQ_REUSE_SOUND")
    def test_a_kept_archive_with_another_hash_is_downloaded_again(self):
        self.kept.mkdir()
        (self.kept / self.NAME).write_bytes(b"something else")
        self.assertEqual(self.archive(), (self.DATA, 1))
        self.assertEqual((self.kept / self.NAME).read_bytes(), self.DATA)

    @proves("REQ_REUSE_SOUND")
    def test_a_download_with_another_hash_is_refused_and_not_kept(self):
        with self.assertRaises(setup.SetupError):
            self.archive(b"something else")
        self.assertFalse((self.kept / self.NAME).exists())

    @proves("REQ_REUSE_SOUND")
    def test_nothing_is_kept_unless_a_directory_is_named(self):
        with mock.patch.dict(os.environ):
            del os.environ[setup.DOWNLOADS_ENV]
            self.assertEqual(self.archive(), (self.DATA, 1))
        self.assertFalse(self.kept.exists())


class Workflow(unittest.TestCase):
    def setUp(self):
        self.data = load()
        self.jobs = self.data["jobs"]

    def steps(self, job: str, text: str) -> list[dict]:
        return [s for s in self.jobs[job]["steps"]
                if text in s.get("uses", "") or text in s.get("run", "")
                or text == s.get("name")]

    @proves("REQ_REUSE_SOUND")
    def test_only_downloads_are_cached_by_pinned_actions(self):
        self.assertEqual(self.data["permissions"], {"contents": "read", "actions": "read"})
        for job in self.jobs:
            with self.subTest(job):
                caches = self.steps(job, "actions/cache")
                self.assertEqual(sorted(s["uses"].split("@")[0] for s in caches),
                                 ["actions/cache/restore", "actions/cache/save"])
                for step in caches:
                    self.assertRegex(step["uses"], PINNED)
                    self.assertEqual(step["with"]["path"], "${{ runner.temp }}/downloads")
                key = caches[0]["with"]["key"]
                for part in ("runner.os", "'requirements.lock'",
                             "'src/trifecta/requirements.lock'", "'src/trifecta/setup.py'"):
                    self.assertIn(part, key)
                self.assertNotIn("actions/cache@", str(self.jobs[job]["steps"]))

    @proves("REQ_REUSE_SCOPED")
    def test_the_check_step_reuses_nothing(self):
        make = (ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertIn("-m trifecta check --fresh", make)
        windows = self.steps("check-windows", "Check (with MADR immutability against the base)")
        commands = re.findall(r"trifecta check[^\n]*", windows[0]["run"])
        self.assertTrue(commands)
        self.assertTrue(all("--fresh" in c for c in commands), commands)

    @proves("REQ_REUSE_SOUND")
    def test_a_pull_request_takes_only_the_store_of_mains_push_run(self):
        for job in self.jobs:
            with self.subTest(job):
                store = self.steps(job, "Store")[0]["run"]
                self.assertIn("actions/workflows/check.yml/runs?branch=main&event=push"
                              "&status=success", store)
                self.assertIn('"push main $REPO .github/workflows/check.yml"', store)
                self.assertIn('git rev-list --first-parent origin/main | grep -x "$sha" >/dev/null', store)
                self.assertIn('gh run download "$id"', store)
                self.assertIn('rm -rf "$STORE" && mkdir "$STORE"', store.splitlines()[0])
                steps = self.jobs[job]["steps"]
                fixtures = [s for s in steps
                            if s.get("run") in ("make fixtures", "trifecta fixtures")]
                self.assertEqual(len(fixtures), 1)
                uploads = [s for s in self.steps(job, "upload-artifact")
                           if "store" in s["with"]["name"]]
                self.assertEqual(len(uploads), 1)
                self.assertEqual(uploads[0]["if"], "github.event_name == 'push' && "
                                                   "github.ref == 'refs/heads/main'")
                where = "${{ runner.temp }}/store"
                self.assertEqual(self.steps(job, "Store")[0]["env"]["STORE"], where)
                self.assertEqual(fixtures[0]["env"], {"TRIFECTA_STORE": where})
                self.assertEqual(uploads[0]["with"]["path"], where + "/")
                order = [steps.index(s) for s in (self.steps(job, "Store")[0], fixtures[0],
                                                  uploads[0])]
                self.assertEqual(order, sorted(order))


class NamedStore(unittest.TestCase):
    @proves("REQ_REUSE_SOUND")
    def test_the_copies_never_write_the_named_store(self):
        """The control fills the store STORE_ENV names; the copies share a copy of it, so
        their results never prune the control's from the store CI keeps."""
        from trifecta import profiler, run_fixtures

        with tempfile.TemporaryDirectory() as raw:
            named = Path(raw).resolve() / "named"
            used = []

            def check(base, vale, cache, fresh, tests=()):
                used.append(cache)
                kept = Path(tests[1]).resolve()
                self.assertFalse(kept.is_relative_to(named), "the control's reports stay "
                                 "out of the store CI keeps")
                (cache / f"entry-{len(used)}").write_text("", encoding="utf-8")
                return 0, [], []

            def fixture(f, base, tmp, vale, cache, fresh):
                used.append(cache)
                (cache / f"copy-{f}").write_text("", encoding="utf-8")
                return f, True, "", {}

            with mock.patch.dict(os.environ, {run_fixtures.STORE_ENV: str(named)}), \
                    mock.patch.object(run_fixtures, "make_base", return_value=Path(raw)), \
                    mock.patch.object(run_fixtures, "run_check", check), \
                    mock.patch.object(run_fixtures, "run_fixture", fixture), \
                    mock.patch("sys.stdout"):
                code = run_fixtures._run(ROOT, Path("vale"), ["a", "b"],
                                         profiler.Profiler("fixtures"), {})
            self.assertEqual(code, 0)
            self.assertEqual(used[0], named)
            self.assertTrue(all(c != named for c in used[1:]), used)
            self.assertEqual(sorted(p.name for p in named.iterdir()), ["entry-1"])
