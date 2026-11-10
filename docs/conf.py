"""This repository's corpus: the package's ontology, and the switches only this repository sets."""

from trifecta.ext.ontology import *  # noqa: F403

project = "trifecta"

#: The fixture audit runs only here, where the toolchain's requirements are defined
#: (REQ_SELF_TESTS_SCOPED).
trifecta_fixture_audit = True
