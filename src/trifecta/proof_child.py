"""The child that runs the proof modules (COMP_TEST_PROOFS) and reports on its own channel.

Started by ``trifecta.proofs`` as ``python -E -X utf8``, with the channel's path, the
modules to run and the tests to leave out. It writes one JSON record per line: its
``os.name`` before any import and after the run, every import error, every collected
test, every result, every class or module set-up and tear-down that did not succeed, and
an end record once it has reported all of them.
"""

from __future__ import annotations

import importlib
import inspect
import json
import os
import sys
import traceback
import unittest
from unittest.case import _SubTest

#: Set-up and tear-down names unittest gives an _ErrorHolder's description.
FIXTURES = {"setUpClass": "class", "tearDownClass": "class",
            "setUpModule": "module", "tearDownModule": "module"}


class Channel:
    def __init__(self, path: str):
        self.out = open(path, "w", encoding="utf-8", newline="\n")

    def write(self, kind: str, **fields) -> None:
        self.out.write(json.dumps({"kind": kind, **fields}, ensure_ascii=False) + "\n")
        self.out.flush()


def _where(test) -> tuple[str, str, str]:
    cls = type(test)
    return cls.__module__, cls.__qualname__, getattr(test, "_testMethodName", "")


def _defined_in(test) -> tuple[str, str]:
    """The module and class that define the method a test runs."""
    func = inspect.unwrap(getattr(type(test), test._testMethodName))
    module = getattr(func, "__module__", "")
    qual = getattr(func, "__qualname__", "")
    return module, qual.rpartition(".")[0]


def _detail(err) -> str:
    if isinstance(err, str):
        return err[:300]
    if err is None:
        return ""
    return "".join(traceback.format_exception_only(err[0], err[1])).strip()[:300]


class Recorder(unittest.TestResult):
    """Records each outcome against the test it belongs to; a subtest's against its test."""

    def __init__(self, channel: Channel, returned: dict[int, str | None], modules: list[str]):
        super().__init__()
        self.channel, self.returned = channel, returned
        self.modules = sorted(modules, key=len, reverse=True)

    def _split(self, dotted: str) -> str:
        """``module:qualified.class`` for a dotted class path, split at the longest module."""
        for module in self.modules:
            if dotted.startswith(module + "."):
                return f"{module}:{dotted[len(module) + 1:]}"
        return dotted

    def _record(self, test, outcome: str, err=None) -> None:
        if isinstance(test, _SubTest):
            test = test.test_case
        if isinstance(test, unittest.suite._ErrorHolder):
            name, _, target = test.description.partition(" (")
            scope = FIXTURES.get(name, "module")
            target = target.rstrip(")")
            if scope == "class":
                target = self._split(target)
            self.channel.write("fixture", scope=scope, target=target, outcome=outcome,
                               detail=_detail(err))
            return
        module, cls, name = _where(test)
        self.channel.write("result", module=module, cls=cls, name=name, outcome=outcome,
                           detail=_detail(err), returned=self.returned.get(id(test)))

    def addSuccess(self, test):
        self._record(test, "success")

    def addFailure(self, test, err):
        self._record(test, "failure", err)

    def addError(self, test, err):
        self._record(test, "error", err)

    def addSkip(self, test, reason):
        self._record(test, "skip", reason)

    def addExpectedFailure(self, test, err):
        self._record(test, "expected_failure", err)

    def addUnexpectedSuccess(self, test):
        self._record(test, "unexpected_success")

    def addSubTest(self, test, subtest, err):
        if err is not None:
            failure = issubclass(err[0], test.failureException)
            self._record(test, "failure" if failure else "error", err)


def _watch_returns(returned: dict[int, str | None]) -> None:
    """Record what each test method call returned, as the test case makes the call."""

    def call(self, method):
        value = method()
        returned[id(self)] = None if value is None else type(value).__name__

    unittest.TestCase._callTestMethod = call

    def call_async(self, method):
        value = self._callMaybeAsync(method)
        returned[id(self)] = None if value is None else type(value).__name__

    unittest.IsolatedAsyncioTestCase._callTestMethod = call_async


def _flatten(suite) -> list:
    out = []
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            out += _flatten(item)
        else:
            out.append(item)
    return out


def main(argv: list[str]) -> int:
    channel_path, modules, leave_out = argv[0], json.loads(argv[1]), set(json.loads(argv[2]))
    channel = Channel(channel_path)
    channel.write("os", when="before", os_name=os.name)
    returned: dict[int, str | None] = {}
    _watch_returns(returned)
    loader = unittest.TestLoader()
    tests = []
    for name in modules:
        try:
            module = importlib.import_module(name)
            loaded = loader.loadTestsFromModule(module)
        except BaseException as exc:  # an import that raises anything is a result
            channel.write("module_error", module=name,
                          detail=_detail((type(exc), exc, None)))
            continue
        for test in _flatten(loaded):
            if hasattr(test, "_testMethodName") and not isinstance(test, unittest.loader._FailedTest):
                defined_module, defined_cls = _defined_in(test)
                key = f"{defined_module}:{defined_cls}.{test._testMethodName}"
                if key in leave_out:
                    continue
                module_name, cls, method = _where(test)
                channel.write("collected", module=module_name, cls=cls, name=method,
                              defined_module=defined_module, defined_cls=defined_cls)
            tests.append(test)
    suite = unittest.TestSuite(tests)
    result = Recorder(channel, returned, modules)
    try:
        suite.run(result)
    except BaseException as exc:  # a test that exits the interpreter ends the run here
        channel.write("module_error", module="(run)", detail=_detail((type(exc), exc, None)))
    channel.write("os", when="after", os_name=os.name)
    channel.write("end")
    channel.out.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
