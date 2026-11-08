"""The ontology of the corpus, and every graph rule sphinx-needs can enforce natively.

Need-local and graph-traversal rules live here as schemas whose ``id`` is the
requirement they enforce (see DEC_0006). Rules that compare values across needs,
need a disjunction across link types, or touch the filesystem live in
``tools/check_graph.py``.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ext"))

project = "trifecta"
extensions = ["myst_parser", "sphinx_needs", "trifecta"]
exclude_patterns = ["_build"]
nitpicky = True
myst_enable_extensions = ["colon_fence"]

needs_build_json = True
needs_id_required = True
needs_title_optional = True
needs_id_regex = r"^[A-Z]+_[A-Z0-9_]+$"

DOC_LEVEL = ["rfc", "decision", "design"]


def _text(description):
    return {"description": description, "nullable": True, "schema": {"type": "string"}}


def _link(outgoing, incoming, targets):
    return {"outgoing": outgoing, "incoming": incoming, "target_types": targets}


# A child need's document status, joined from the document-level need in the same file.
# Derived, so no author can write it.
needs_fields = {
    "doc_status": {
        "description": "Status of the document this need is defined in.",
        "nullable": True,
        "schema": {"type": "string"},
        "derive": {
            "kind": "copy",
            "field": "status",
            "join": {"field": "docname", "equals": "docname"},
            "where": f"type in {DOC_LEVEL}",
        },
    },
}

needs_types = [
    # --- RFC -------------------------------------------------------------------
    dict(
        directive="rfc", title="RFC", prefix="RFC_", id_regex=r"^RFC_\d{4}$",
        fields={"authors": _text("Authors."), "created": _text("Creation date.")},
    ),
    dict(directive="req", title="Requirement", prefix="REQ_"),
    dict(
        directive="term", title="Term", prefix="TERM_",
        fields={"synonyms": _text("Comma-separated words that must not replace this term.")},
    ),
    dict(directive="question", title="Question", prefix="Q_"),
    # --- MADR ------------------------------------------------------------------
    dict(
        directive="decision", title="Decision", prefix="DEC_", id_regex=r"^DEC_\d{4}$",
        fields={
            "date": _text("Decision date."),
            "decision_makers": _text("Decision makers."),
            "consulted": _text("Consulted."),
            "informed": _text("Informed."),
        },
        links={
            # Derived: every option defined in the decision's own file. Never restated.
            "considers": {
                "outgoing": "considers",
                "incoming": "considered by",
                "derive": {
                    "kind": "links",
                    "join": {"field": "docname", "equals": "docname"},
                    "where": "type == 'opt'",
                },
            },
            "chooses": _link("chooses", "chosen by", ["opt"]),
            "resolves": _link("resolves", "resolved by", ["question"]),
            "driven_by": _link("driven by", "drives", ["req"]),
            "supersedes": _link("supersedes", "superseded by", ["decision"]),
        },
    ),
    dict(directive="opt", title="Option", prefix="OPT_", id_regex=r"^OPT_\d{4}_[A-Z0-9_]+$"),
    # --- Design doc ------------------------------------------------------------
    dict(
        directive="design", title="Design", prefix="DES_", id_regex=r"^DES_\d{4}$",
        fields={"authors": _text("Authors.")},
    ),
    dict(
        directive="component", title="Component", prefix="COMP_",
        fields={"spec": _text("Repo path of the artifact that is this component.")},
        links={
            "satisfies": _link("satisfies", "satisfied by", ["req"]),
            "constrained_by": _link("constrained by", "constrains", ["decision"]),
            "provides": _link("provides", "provided by", ["interface"]),
            "consumes": _link("consumes", "consumed by", ["interface"]),
        },
    ),
    dict(
        directive="interface", title="Interface", prefix="IF_",
        fields={"spec": _text("Repo path (and #fragment) of the interface's shape.")},
        links={"constrained_by": _link("constrained by", "constrains", ["decision"])},
    ),
]


def _select(**props):
    return {"properties": {k: ({"enum": v} if isinstance(v, list) else {"const": v})
                           for k, v in props.items()}}


needs_schema_definitions = {"schemas": [
    {
        "id": "REQ_DECISION_OPTIONS",
        "message": "a decision considers at least two options and chooses exactly one",
        "select": _select(type="decision"),
        "validate": {"local": {"properties": {
            "considers": {"type": "array", "minItems": 2},
            "chooses": {"type": "array", "minItems": 1, "maxItems": 1},
        }}},
    },
    {
        "id": "REQ_RFC_ACCEPTANCE",
        "message": "a question in an accepted RFC is resolved by an accepted decision",
        "select": _select(type="question", doc_status="accepted"),
        "validate": {"network_back": {"resolves": {
            "contains": {"local": _select(type="decision", status="accepted")},
            "minContains": 1,
        }}},
    },
    {
        "id": "REQ_COVERAGE",
        "message": "a requirement of an accepted RFC is satisfied by a component of an "
                   "approved or implemented design",
        "select": _select(type="req", doc_status="accepted"),
        "validate": {"network_back": {"satisfies": {
            "contains": {"local": _select(type="component",
                                          doc_status=["approved", "implemented"])},
            "minContains": 1,
        }}},
    },
    {
        "id": "REQ_SUPERSESSION",
        "message": "design elements are constrained only by accepted decisions",
        "select": _select(type=["component", "interface"]),
        "validate": {"network": {"constrained_by": {
            "items": {"local": _select(status="accepted")},
        }}},
    },
    {
        "id": "REQ_SUPERSESSION",
        "message": "a superseded decision is superseded by exactly one accepted decision",
        "select": _select(type="decision", status="superseded"),
        "validate": {"network_back": {"supersedes": {
            "contains": {"local": _select(status="accepted")},
            "minContains": 1,
            "maxContains": 1,
        }}},
    },
    {
        "id": "REQ_SUPERSESSION",
        "message": "a decision supersedes only decisions marked superseded",
        "select": _select(type="decision"),
        "validate": {"network": {"supersedes": {
            "items": {"local": _select(status="superseded")},
        }}},
    },
]}
