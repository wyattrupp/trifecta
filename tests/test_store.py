"""REQ_REUSE_SOUND: a stored result matches only while every input its manifest holds is
as it was, under the same identity, and the store keeps no malformed or unstorable entry.

These tests build manifests in the shape IF_MANIFEST states for a small repository in a
temporary directory and change one input at a time; they start no child, so the store's
own logic is what they prove.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from trifecta import record, store
from trifecta.proofs import child_environment
from trifecta.testing import proves


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class Tree(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve() / "repo"
        (self.root / "sub").mkdir(parents=True)
        (self.root / "a.txt").write_text("a", encoding="utf-8")
        (self.root / "sub" / "x.txt").write_text("x", encoding="utf-8")
        self.environ = {"TRIFECTA_DEMO": "one"}
        self.manifest = {
            "version": record.VERSION, "storable": True,
            "files": {"a.txt": sha("a")},
            "probes": {"gone": "absent", "sub": "directory"},
            "listings": {"sub": [["x.txt", "file"]]},
            "lookups": {"./helper": None},
            "environment": {"TRIFECTA_DEMO": sha("one"), "TRIFECTA_UNSET": None},
            "outside": {},
        }

    def tearDown(self):
        self._tmp.cleanup()

    def differs(self) -> str | None:
        return store.mismatch(self.manifest, self.root, self.environ, store.Hashes())


class Mismatch(Tree):
    @proves("REQ_REUSE_SOUND")
    def test_the_manifest_matches_the_tree_it_was_made_on(self):
        self.assertTrue(record.valid(self.manifest))
        self.assertIsNone(self.differs())

    @proves("REQ_REUSE_SOUND")
    def test_a_file_read_that_changes(self):
        (self.root / "a.txt").write_text("b", encoding="utf-8")
        self.assertEqual(self.differs(), "file a.txt")

    @proves("REQ_REUSE_SOUND")
    def test_a_path_probed_that_changes_kind(self):
        (self.root / "gone").mkdir()
        self.assertEqual(self.differs(), "path gone")

    @proves("REQ_REUSE_SOUND")
    def test_a_directory_listed_that_gains_an_entry(self):
        (self.root / "sub" / "y.txt").write_text("y", encoding="utf-8")
        self.assertEqual(self.differs(), "directory sub")

    @proves("REQ_REUSE_SOUND")
    def test_a_name_looked_up_that_appears(self):
        (self.root / "helper.py").write_text("", encoding="utf-8")
        self.assertEqual(self.differs(), "import ./helper")

    @proves("REQ_REUSE_SOUND")
    def test_a_variable_read_that_changes_or_appears_names_no_value(self):
        self.environ["TRIFECTA_DEMO"] = "two"
        self.assertEqual(self.differs(), "variable TRIFECTA_DEMO")
        self.environ = {"TRIFECTA_DEMO": "one", "TRIFECTA_UNSET": "secret"}
        why = self.differs()
        self.assertEqual(why, "variable TRIFECTA_UNSET")
        self.assertNotIn("secret", why)

    @proves("REQ_REUSE_SOUND")
    def test_a_value_holding_the_root_matches_in_a_copy_elsewhere(self):
        self.manifest["environment"] = {"TRIFECTA_DEMO": sha(f"{record.ROOT}/x")}
        self.environ = {"TRIFECTA_DEMO": f"{self.root}/x"}
        self.assertIsNone(self.differs())


class Entries(Tree):
    def setUp(self):
        super().setUp()
        self.shelf = store.Store(Path(self._tmp.name).resolve() / "store", self.root)
        self.ok = lambda result: result in ("first", "second")

    def lookup(self, ident: str):
        return self.shelf.lookup(ident, self.environ, store.Hashes(), self.ok)

    @proves("REQ_REUSE_SOUND")
    def test_a_match_is_reused_and_the_newest_wins(self):
        ident = self.shelf.identity("tests", {"module": "tests.test_a", "leave_out": []})
        self.assertEqual(self.lookup(ident), (None, "no stored result"))
        self.assertTrue(self.shelf.put(ident, self.manifest, "first"))
        self.assertTrue(self.shelf.put(ident, self.manifest, "second"))
        self.assertEqual(self.lookup(ident), ("second", ""))
        (self.root / "a.txt").write_text("b", encoding="utf-8")
        self.assertEqual(self.lookup(ident), (None, "file a.txt"))

    @proves("REQ_REUSE_SOUND")
    def test_an_unstorable_manifest_is_never_stored(self):
        ident = self.shelf.identity("tests", {"module": "tests.test_a", "leave_out": []})
        unstorable = {**self.manifest, "storable": False, "why": "runs git"}
        self.assertFalse(self.shelf.put(ident, unstorable, "first"))
        self.assertFalse(self.shelf.put(ident, {**self.manifest, "files": {"/abs": "x"}},
                                        "first"))
        self.assertFalse(self.shelf.path.exists())

    @proves("REQ_REUSE_SOUND")
    def test_a_malformed_entry_is_refused(self):
        ident = self.shelf.identity("tests", {"module": "tests.test_a", "leave_out": []})
        directory = self.shelf.path / ident[:2] / ident
        directory.mkdir(parents=True)
        good = {"version": store.VERSION, "identity": ident, "manifest": self.manifest,
                "result": "first"}
        bad = [
            "not json",
            json.dumps([good]),
            json.dumps({**good, "identity": "0" * 64}),
            json.dumps({**good, "version": True}),
            json.dumps({**good, "extra": 1}),
            json.dumps({**good, "result": "other"}),
            json.dumps({**good, "manifest": {**self.manifest, "storable": False,
                                             "why": "x"}}),
            json.dumps({**good, "manifest": {**self.manifest, "files": {"../a": sha("a")}}}),
            json.dumps({**good, "manifest": {**self.manifest,
                                             "lookups": {"./not a name": None}}}),
        ]
        for n, text in enumerate(bad):
            with self.subTest(n=n):
                for p in directory.iterdir():
                    p.unlink()
                (directory / f"{'9' * 20}-0123abcd.json").write_text(text, encoding="utf-8")
                self.assertEqual(self.lookup(ident), (None, "a malformed entry"))
        # A name put never gives is no entry, so it cannot crowd out the newest.
        for p in directory.iterdir():
            p.unlink()
        (directory / "~.json").write_text(json.dumps(good), encoding="utf-8")
        self.assertEqual(self.lookup(ident), (None, "no stored result"))

    @proves("REQ_REUSE_SOUND")
    def test_the_interpreter_a_distribution_or_the_package_changes_the_identity(self):
        what = {"module": "tests.test_a", "leave_out": []}
        ident = self.shelf.identity("tests", what)
        self.assertTrue(self.shelf.put(ident, self.manifest, "first"))
        base = store.environment_key(self.root)
        self.assertEqual(base["os"], os.name)
        changes = {
            "interpreter": {**base, "python": base["python"] + " other"},
            "executable": {**base, "executable": base["executable"] + "x"},
            "distribution": {**base, "distributions": base["distributions"]
                             + [["other", "1.0", "0" * 64]]},
            "recorder": {**base, "pth": None},
        }
        for name, key in changes.items():
            with self.subTest(name), mock.patch.object(store, "environment_key",
                                                       return_value=key):
                other = store.Store(self.shelf.path, self.root).identity("tests", what)
                self.assertNotEqual(other, ident)
                self.assertEqual(self.lookup(other), (None, "no stored result"))
        with mock.patch.object(store, "package_hash", return_value="0" * 64):
            self.assertNotEqual(store.Store(self.shelf.path, self.root).identity("tests", what),
                                ident)
        self.assertNotEqual(self.shelf.identity("tests", {**what, "leave_out": ["x"]}), ident)
        self.assertEqual(self.lookup(ident), ("first", ""))

    @proves("REQ_REUSE_SOUND")
    def test_the_package_hash_covers_every_file_of_the_package(self):
        package = Path(self._tmp.name).resolve() / "pkg"
        package.mkdir()
        (package / "mod.py").write_text("A = 1\n", encoding="utf-8")
        before = store.package_hash(package)
        (package / "data.txt").write_text("", encoding="utf-8")
        self.assertNotEqual(store.package_hash(package), before)


class ChildEnvironment(unittest.TestCase):
    @proves("REQ_REUSE_SOUND")
    def test_a_test_child_gets_no_store_or_record_variable(self):
        with mock.patch.dict(os.environ, {store.ENV: "x", record.ENV: "y", "KEEP": "1"}):
            env = child_environment()
        self.assertNotIn(store.ENV, env)
        self.assertNotIn(record.ENV, env)
        self.assertEqual(env["KEEP"], "1")


class Portable(unittest.TestCase):
    @proves("REQ_REUSE_SOUND")
    def test_a_result_stored_in_one_copy_reads_back_with_another_copys_path(self):
        from trifecta.proofs import _portable, _restored
        here, there = Path("/tmp/copy-one").resolve(), Path("/tmp/elsewhere/two").resolve()
        line = json.dumps({"kind": "result", "detail": f"{here}{os.sep}x.py and "
                           f"{here.as_posix()}/y.py"})
        stored = _portable([line, "raw " + str(here)], f"tail {here}", here)
        self.assertNotIn(str(here), json.dumps(stored))
        lines, output = _restored(stored, there)
        self.assertEqual(json.loads(lines[0])["detail"],
                         f"{there}{os.sep}x.py and {there.as_posix()}/y.py")
        self.assertEqual(lines[1], "raw " + str(there))
        self.assertEqual(output, f"tail {there}")
