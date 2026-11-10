"""The two decorators a test under ``tests/`` declares itself with (COMP_TEST_PROOFS).

The check reads them from the source as literals and never runs them for their meaning;
both return the method unchanged.

    from trifecta.testing import proves, only_on

    class LinkTests(unittest.TestCase):
        @proves("REQ_INIT_SAFE")
        @only_on("posix")
        def test_link_is_refused(self): ...
"""

from __future__ import annotations

from typing import Callable, TypeVar

F = TypeVar("F", bound=Callable)


def proves(*requirements: str) -> Callable[[F], F]:
    """Declare the requirements a test proves."""
    def mark(method: F) -> F:
        return method
    return mark


def only_on(system: str) -> Callable[[F], F]:
    """Declare that a test applies only to the system whose ``os.name`` is ``system``."""
    def mark(method: F) -> F:
        return method
    return mark
