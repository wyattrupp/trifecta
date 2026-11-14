"""REQ_REFUSALS_NAMED: a module the test stage runs and does not store names every reason
and each of its tests' times, moved from ``test_store_reuse`` unchanged
(COMP_LIFTED_REASONS).

Its test starts a child that reads the host name on purpose, which refuses the run of
this module under its own recorder, so this module is never stored, and
``test_store_reuse`` is.
"""

from __future__ import annotations

import unittest
from unittest import mock

from trifecta import store
from trifecta.proofs import run_modules
from trifecta.testing import proves

from tests import test_store_reuse


MODULE_REFUSED = """
import socket
import unittest
from trifecta.testing import proves


class R(unittest.TestCase):
    @proves("REQ_R")
    def test_r(self):
        socket.gethostname()
"""


class Named(unittest.TestCase):
    setUp, tearDown = test_store_reuse.Reuse.setUp, test_store_reuse.Reuse.tearDown

    @proves("REQ_REFUSALS_NAMED")
    def test_a_module_not_stored_names_its_reasons_and_its_tests_times(self):
        (self.root / "tests" / "test_r.py").write_text(MODULE_REFUSED, encoding="utf-8")
        names = ["tests.test_b", "tests.test_r"]
        for fresh in (False, True):
            with self.subTest(fresh=fresh):
                _, runs = run_modules(self.root, names, [], None, fresh, self.store)
                stored, refused = runs
                self.assertEqual((stored.unstored, stored.reasons, stored.tests),
                                 (False, [], []))
                self.assertTrue(refused.unstored)
                self.assertEqual(refused.reasons,
                                 [{"process": None, "why": "reads the host name"}])
                self.assertEqual([t["name"] for t in refused.tests], ["R.test_r"])
                self.assertIsInstance(refused.tests[0]["seconds"], float)
        # The refused module ran again; the stored one was reused, as before.
        _, runs = run_modules(self.root, names, [], None, False, self.store)
        self.assertEqual([r.reused for r in runs], [True, False])
        # A storable run the store did not keep is named so; nothing is named empty.
        with mock.patch.object(store.Store, "put", return_value=False):
            _, runs = run_modules(self.root, ["tests.test_b"], [], None, True, self.store)
        self.assertEqual(runs[0].reasons, [{"process": None,
                                            "why": "the store did not store it"}])
