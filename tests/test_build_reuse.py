"""REQ_REUSE_SOUND, REQ_REUSE_SCOPED: the Sphinx build is restored from the store only
while every input its manifest holds is unchanged, gives the same findings and locations
either way, a failed build's included, in a copy at another path, and refuses an archive
member that is absolute, holds ``..`` or is a link.

Each test builds a small Sphinx project in a temporary directory with a store of its own,
recording the build through the .pth file setup installs. A test here starts a Python
child that records into a directory of its own, so this module is never stored itself.
"""

from __future__ import annotations

import base64
import functools
import io
import shutil
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from trifecta import build, check, record, store
from trifecta.testing import proves

CONF = """\
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import helper
project = helper.NAME
html_title = os.environ.get("TRIFECTA_DEMO_TITLE", "demo")
"""

INDEX = """\
Index
=====

.. toctree::

   other
"""


def project(root: Path) -> None:
    """A small Sphinx project, with a lock file and a test the build never reads."""
    docs = root / "docs"
    (root / "tests").mkdir(parents=True)
    docs.mkdir()
    (docs / "conf.py").write_text(CONF, encoding="utf-8")
    (docs / "helper.py").write_text('NAME = "demo"\n', encoding="utf-8")
    (docs / "index.rst").write_text(INDEX, encoding="utf-8")
    (docs / "other.rst").write_text("Other\n=====\n\nText.\n", encoding="utf-8")
    (root / "requirements.lock").write_text("a==1\n", encoding="utf-8")
    (root / "tests" / "test_x.py").write_text("", encoding="utf-8")


def sphinx(root: Path, at: Path, fresh: bool = False):
    """The check's build stage on ``root`` with the store at ``at``: its findings and the
    stage's record."""
    stage: dict = {}
    run = functools.partial(build.run_build, store_at=at)
    with mock.patch.object(check, "run_build", run):
        findings = check.run_sphinx(root, fresh, stage)
    return findings, stage


class Built(unittest.TestCase):
    """Each test starts from a copy of one project built once, and of the store that
    build filled: an entry restores at another path, so no test builds its start again."""

    @classmethod
    def setUpClass(cls):
        cls._base = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        base = Path(cls._base.name).resolve()
        project(base / "repo")
        cls.first = sphinx(base / "repo", base / "store")
        cls.base = base

    @classmethod
    def tearDownClass(cls):
        cls._base.cleanup()

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self._tmp.cleanup)
        tmp = Path(self._tmp.name).resolve()
        self.root, self.store = tmp / "repo", tmp / "store"
        shutil.copytree(self.base / "repo", self.root, symlinks=True)
        shutil.copytree(self.base / "store", self.store, symlinks=True)

    def sphinx(self, root: Path | None = None, fresh: bool = False):
        """The check's build stage on ``root``: its findings and the stage's record."""
        return sphinx(root or self.root, self.store, fresh)

    def reused(self, root: Path | None = None) -> bool:
        return self.sphinx(root)[1]["reused"]


class Reuse(Built):
    @proves("REQ_REUSE_SOUND")
    def test_an_input_the_build_read_builds_again(self):
        first, stage = self.first
        self.assertEqual((first, stage["reused"]), ([], False), stage["why"])
        self.assertTrue(self.reused(), "a copy of the built project restores its build")
        self.assertTrue((self.root / build.OUTPUT / "index.html").is_file())
        self.assertTrue((self.root / build.OUTPUT / "other.html").is_file(),
                        "the restored output directory holds every page")
        docs = self.root / "docs"
        for name, change in (
                ("a document", lambda: (docs / "other.rst").write_text(
                    "Other\n=====\n\nChanged.\n", encoding="utf-8")),
                ("conf.py", lambda: (docs / "conf.py").write_text(
                    CONF + "html_title = 'x'\n", encoding="utf-8")),
                ("a module the build imported", lambda: (docs / "helper.py").write_text(
                    'NAME = "other"\n', encoding="utf-8")),
                ("a new document", lambda: (docs / "new.rst").write_text(
                    "New\n===\n", encoding="utf-8")),
                ("a document removed", lambda: (docs / "other.rst").unlink())):
            with self.subTest(name):
                change()
                self.assertFalse(self.reused())
                self.assertTrue(self.reused())

    @proves("REQ_REUSE_SOUND")
    def test_a_variable_conf_py_reads_builds_again(self):
        self.sphinx()
        changed = {**build.CHILD_ENV, "TRIFECTA_DEMO_TITLE": "other"}
        with mock.patch.object(build, "CHILD_ENV", changed):
            self.assertFalse(self.reused())
            self.assertTrue(self.reused())
        self.assertTrue(self.reused(), "the first entry matches again once it is unset")

    @proves("REQ_REUSE_SOUND")
    def test_output_holding_the_placeholder_is_never_stored(self):
        (self.root / "docs" / "other.rst").write_text(
            f"Other\n=====\n\nSee :doc:`{record.ROOT}`.\n", encoding="utf-8")
        _, stage = self.sphinx()
        self.assertIn("placeholder", stage["why"])
        self.assertFalse(self.reused())

    @proves("REQ_REUSE_SCOPED")
    def test_a_file_the_build_did_not_read_restores_it(self):
        self.sphinx()
        (self.root / "requirements.lock").write_text("a==2\n", encoding="utf-8")
        (self.root / "tests" / "test_x.py").write_text("# changed\n", encoding="utf-8")
        self.assertTrue(self.reused())

    @proves("REQ_REUSE_SOUND")
    def test_a_change_to_the_package_builds_again(self):
        self.sphinx()
        with mock.patch.object(store, "package_hash", return_value="0" * 64):
            self.assertFalse(self.reused())

    @proves("REQ_REUSE_SCOPED")
    def test_fresh_restores_nothing(self):
        self.sphinx()
        findings, stage = self.sphinx(fresh=True)
        self.assertEqual((findings, stage["reused"], stage["why"]), ([], False, "fresh"))

    @proves("REQ_REUSE_SOUND")
    def test_a_failed_build_gives_the_same_findings_in_a_copy_elsewhere(self):
        (self.root / "docs" / "other.rst").write_text(
            "Other\n=====\n\nSee :doc:`nowhere`.\n", encoding="utf-8")
        fresh, stage = self.sphinx()
        self.assertFalse(stage["reused"])
        self.assertTrue(fresh)
        self.assertTrue(all(f.location.startswith("docs/other.rst") for f in fresh), fresh)
        copy = Path(self._tmp.name).resolve() / "elsewhere" / "copy"
        shutil.copytree(self.root, copy)
        shutil.rmtree(copy / build.OUTPUT)
        stored, stage = self.sphinx(copy)
        self.assertTrue(stage["reused"], stage["why"])
        self.assertEqual(stored, fresh)
        self.assertNotIn(str(self.root), "".join(f.message for f in stored))


def archive_of(*entries: tuple[str, bytes, int]) -> str:
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as z:
        for name, content, mode in entries:
            info = zipfile.ZipInfo(name)
            info.external_attr = mode << 16
            z.writestr(info, content)
    return base64.b64encode(data.getvalue()).decode("ascii")


class Archive(unittest.TestCase):
    @proves("REQ_REUSE_SOUND")
    def test_a_member_absolute_holding_dotdot_or_a_link_is_refused(self):
        regular = stat.S_IFREG | 0o644
        good = ("index.html", b"<p>", regular)
        z, files = build.members(archive_of(good))
        with z:
            self.assertEqual([(i.filename, z.read(i)) for i in files],
                             [("index.html", b"<p>")])
        for bad in (("/etc/x", b"", regular), ("../x", b"", regular),
                    ("a/../../x", b"", regular), ("C:/x", b"", regular),
                    ("a\\..\\x", b"", regular), ("link", b"/etc", stat.S_IFLNK | 0o777),
                    ("sub/CON.html", b"", regular), ("x. ", b"", regular),
                    ("INDEX.html", b"", regular)):
            with self.subTest(bad[0]):
                self.assertIsNone(build.members(archive_of(good, bad)))
        self.assertIsNone(build.members("not base64!"))

    @proves("REQ_REUSE_SOUND")
    def test_a_refused_archive_writes_nothing_and_builds(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            bad = {"returncode": 0, "stderr": "",
                   "archive": archive_of(("ok.html", b"", stat.S_IFREG | 0o644),
                                         ("../escape", b"", stat.S_IFREG | 0o644))}
            self.assertFalse(build._restore(bad, root))
            self.assertFalse((root / "docs").exists())
            self.assertFalse((root / "escape").exists())


class Entry(unittest.TestCase):
    @proves("REQ_REUSE_SCOPED")
    def test_the_recorder_runs_only_the_build(self):
        with mock.patch("sys.stderr", io.StringIO()):
            self.assertEqual(record.main(["python", "-c", "print(1)"]), 2)
