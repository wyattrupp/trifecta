"""Document-level invariants for the trifecta corpus.

This extension owns the rules that concern a document as a whole rather than
the need graph: identity from the filename, frontmatter schema, section
skeleton, derived-view sections, the single source of status, and the MADR
chosen-option sentence. Every finding is a Sphinx warning of type
``trifecta`` whose subtype is the violated requirement's ID, so
``-W`` fails the build and the finding names its invariant.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import jsonschema
import yaml
from docutils import nodes
from sphinx.application import Sphinx
from sphinx.util import logging

from . import digest, plans

logger = logging.getLogger(__name__)

SCHEMA_DIR = Path(__file__).parent / "schemas"

#: One entry per document type. The directory is the type's identity; everything
#: else about a document's shape is declared here and nowhere else.
DOC_TYPES: dict[str, dict] = {
    "rfcs": {
        "directive": "rfc",
        "prefix": "RFC",
        "schema": "rfc.json",
        "sections": [
            "Summary", "Motivation", "Terms", "Requirements", "Questions", "Out of scope",
            "Review",
        ],
        "derived": [],
    },
    "decisions": {
        "directive": "decision",
        "prefix": "DEC",
        "schema": "decision.json",
        "sections": [
            "Context and Problem Statement",
            "Decision Drivers",
            "Considered Options",
            "Decision Outcome",
            "Consequences",
        ],
        "derived": [],
    },
    "design": {
        "directive": "design",
        "prefix": "DES",
        "schema": "design.json",
        "sections": [
            "Overview", "Requirements", "Constraints", "Components", "Interfaces", "Risks",
            "Review",
        ],
        "derived": ["Requirements", "Constraints"],
        #: The one needtable each derived section holds. trifecta new writes these.
        "views": {
            "Requirements": [
                ":::{needtable}",
                ":filter: type == 'req' and len(satisfies_back) > 0",
                ':columns: id, title, satisfies_back as "Satisfied by"',
                ":style: table",
                ":::",
            ],
            "Constraints": [
                ":::{needtable}",
                ":filter: type == 'decision' and len(constrained_by_back) > 0",
                ":columns: id, title, status",
                ":style: table",
                ":::",
            ],
        },
    },
    "plans": {
        "directive": "plan",
        "prefix": "PLAN",
        "schema": "plan.json",
        "sections": ["Read before starting", "Rules for every task", "Tasks", "Review", "As built"],
        "derived": [],
    },
}

FILENAME_RE = re.compile(r"^(\d{4})-[a-z0-9]+(?:-[a-z0-9]+)*$")
OPTION_RE = re.compile(r"^:([A-Za-z_][\w-]*):(.*)$")
CHOSEN_RE = re.compile(r"Chosen option: \{need\}`([A-Z0-9_]+)`")
#: ATX H2 lines as CommonMark reads them: up to 3 leading spaces, optional closing #s.
H2_RE = re.compile(r"^ {0,3}##(?:[ \t]+(.*?))?(?:[ \t]+#+)?[ \t]*$")


def _h2_title(line: str) -> str | None:
    m = H2_RE.match(line)
    return (m.group(1) or "") if m else None


_NoTimestampLoader = plans.NoTimestampLoader


def doc_type(docname: str) -> tuple[str, dict] | None:
    head, _, _ = docname.partition("/")
    if "/" in docname and head in DOC_TYPES:
        return head, DOC_TYPES[head]
    return None


def doc_need_id(docname: str) -> str | None:
    """The document-level need ID, derived from the filename alone."""
    typed = doc_type(docname)
    if not typed:
        return None
    match = FILENAME_RE.match(docname.split("/", 1)[1])
    return f"{typed[1]['prefix']}_{match.group(1)}" if match else None


def _warn(req: str, msg: str, docname: str, line: int | None = None) -> None:
    location = (docname, line) if line is not None else docname
    logger.warning(f"{req}: {msg}", type="trifecta", subtype=req, location=location)


_split_frontmatter = plans.frontmatter_end


def _field_name(key: str) -> str:
    return key.replace("-", "_")


#: Characters MyST's option parser reads as syntax: a comment, a quote, an escape.
_OPTION_SYNTAX = re.compile(r"[#\"'\\]|^\s|\s$")


def _field_value(value) -> str:
    text = ", ".join(str(v) for v in value) if isinstance(value, list) else str(value)
    return json.dumps(text) if _OPTION_SYNTAX.search(text) else text


def on_source_read(app: Sphinx, docname: str, source: list[str]) -> None:
    typed = doc_type(docname)
    if not typed:
        return
    _, spec = typed
    lines = source[0].split("\n")

    # REQ_DOC_IDENTITY: the filename is the only place a document's number is written.
    need_id = doc_need_id(docname)
    if need_id is None:
        _warn("REQ_DOC_IDENTITY", f"filename must be NNNN-kebab-slug.md, got {docname}", docname, 1)
        return

    # REQ_FRONTMATTER_SCHEMA
    fm_end = _split_frontmatter(lines)
    if fm_end is None:
        _warn("REQ_FRONTMATTER_SCHEMA", "document has no YAML frontmatter", docname, 1)
        return
    try:
        meta = yaml.load("\n".join(lines[1:fm_end]), Loader=_NoTimestampLoader) or {}
    except yaml.YAMLError as exc:
        _warn("REQ_FRONTMATTER_SCHEMA", f"frontmatter is not valid YAML: {exc}", docname, 1)
        return
    schema = json.loads((SCHEMA_DIR / spec["schema"]).read_text(encoding="utf-8"))
    errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(meta), key=str)
    for err in errors:
        where = "/".join(str(p) for p in err.absolute_path) or "(root)"
        _warn("REQ_FRONTMATTER_SCHEMA", f"{where}: {err.message}", docname, 1)
    if errors:
        return

    # Locate the H1 and the document-level directive, which must follow it directly.
    h1 = next((i for i in range(fm_end + 1, len(lines)) if lines[i].startswith("# ")), None)
    if h1 is None:
        _warn("REQ_SECTION_SKELETON", "document has no H1 title", docname, fm_end + 2)
        return
    title = lines[h1][2:].strip()
    start = next((i for i in range(h1 + 1, len(lines)) if lines[i].strip()), None)
    opener = f":::{{{spec['directive']}}}"
    if start is None or lines[start].rstrip() != opener:
        found = lines[start].strip() if start is not None else "end of file"
        _warn(
            "REQ_STATUS_SINGLE_SOURCE",
            f"the line after the H1 must be exactly '{opener}' (title, ID and status are "
            f"injected), found '{found}'",
            docname,
            (start or h1) + 1,
        )
        return
    opt_end = start + 1
    authored: dict[str, tuple[str, int]] = {}
    while opt_end < len(lines) and (m := OPTION_RE.match(lines[opt_end])):
        authored[m.group(1)] = (m.group(2).strip(), opt_end + 1)
        opt_end += 1

    # REQ_STATUS_SINGLE_SOURCE: identity and lifecycle facts have exactly one home.
    owned = {"id", "status", "title"} | {_field_name(k) for k in schema["properties"]}
    for key in sorted(k for k in authored if _field_name(k) in owned):
        _warn(
            "REQ_STATUS_SINGLE_SOURCE",
            f"':{key}:' is owned by the filename or frontmatter and must not be written "
            f"in the directive",
            docname,
            authored[key][1],
        )
    code = plans.fenced(lines)
    for i, line in enumerate(lines):
        if i >= opt_end and not code[i] and line.startswith(":status:"):
            _warn(
                "REQ_STATUS_SINGLE_SOURCE",
                "child needs carry no status; their status is their document's",
                docname,
                i + 1,
            )

    # REQ_CHOSEN_SENTENCE: the prose restates the chooses link, so it must agree with it.
    if spec["directive"] == "decision":
        chosen = [c.strip() for c in authored.get("chooses", ("", 0))[0].split(",") if c.strip()]
        _check_chosen_sentence(lines, chosen, docname)

    # REQ_TASK_ORDER, REQ_TASK_SHAPE, REQ_LINEAR_EXECUTION, REQ_AS_BUILT (DEC_0009).
    if spec["directive"] == "plan":
        number = need_id.split("_", 1)[1]
        for req, msg, line in plans.problems(plans.parse(lines), number, meta.get("status")):
            _warn(req, msg, docname, line)

    # REQ_REVIEW_CURRENT (DEC_0011): read from the raw file, as the digest is defined on it.
    if spec["directive"] in digest.RELIED_ON:
        raw = digest.read(Path(app.env.doc2path(docname)))
        for msg, line in digest.problems(raw, spec["directive"], meta.get("status")):
            _warn("REQ_REVIEW_CURRENT", msg, docname, line)

    # Inject the owned facts. The frontmatter block is replaced by blank lines, k fewer
    # than it had, and k option lines are inserted into the directive, so every line
    # after the directive keeps its original number.
    injected = [f":id: {need_id}"] + [
        f":{_field_name(k)}: {_field_value(v)}" for k, v in meta.items()
    ]
    pad = fm_end + 1 - len(injected)
    new = (
        [""] * pad
        + lines[fm_end + 1 : start]
        + [f"{opener} {title}"]
        + injected
        + lines[start + 1 :]
    )
    source[0] = "\n".join(new)


def _check_chosen_sentence(lines: list[str], chosen: list[str], docname: str) -> None:
    if len(chosen) != 1:
        return  # cardinality is REQ_DECISION_OPTIONS's to report
    begin = next((i for i, l in enumerate(lines) if _h2_title(l) == "Decision Outcome"), None)
    if begin is None:
        return  # REQ_SECTION_SKELETON reports a missing or renamed section
    end = next((i for i in range(begin + 1, len(lines)) if _h2_title(lines[i]) is not None), len(lines))
    hits = [(i, m.group(1)) for i in range(begin, end) for m in CHOSEN_RE.finditer(lines[i])]
    if len(hits) != 1:
        _warn(
            "REQ_CHOSEN_SENTENCE",
            f"Decision Outcome must contain exactly one 'Chosen option: {{need}}`ID`' "
            f"sentence, found {len(hits)}",
            docname,
            begin + 1,
        )
        return
    line, cited = hits[0]
    if cited != chosen[0]:
        _warn(
            "REQ_CHOSEN_SENTENCE",
            f"sentence cites {cited} but ':chooses:' is {chosen[0]}",
            docname,
            line + 1,
        )


def on_env_before_read_docs(app: Sphinx, env, docnames: list[str]) -> None:
    """REQ_DOC_IDENTITY: every document but the index lives in a typed directory, and per
    type, numbers run 0001..N with no gaps."""
    for docname in sorted(env.found_docs):
        if docname != app.config.root_doc and not doc_type(docname):
            _warn(
                "REQ_DOC_IDENTITY",
                f"{docname} is in no typed directory; documents live in "
                f"{', '.join(d + '/' for d in DOC_TYPES)} (trifecta new writes them there)",
                docname,
                1,
            )
    for directory in DOC_TYPES:
        numbers = sorted(
            int(m.group(1))
            for d in env.found_docs
            if d.startswith(directory + "/") and (m := FILENAME_RE.match(d.split("/", 1)[1]))
        )
        expected = list(range(1, len(numbers) + 1))
        if numbers != expected:
            missing = sorted(set(expected) - set(numbers))
            _warn(
                "REQ_DOC_IDENTITY",
                f"{directory}/ numbers must run 0001..{len(numbers):04d} without gaps or "
                f"duplicates; found {numbers}, missing {missing}",
                f"{directory}/",
                None,
            )


def on_doctree_read(app: Sphinx, doctree: nodes.document) -> None:
    docname = app.env.docname
    typed = doc_type(docname)
    if not typed:
        return
    _, spec = typed
    top = next(iter(doctree.findall(nodes.section)), None)
    if top is None:
        return
    sections = [c for c in top.children if isinstance(c, nodes.section)]
    titles = [s[0].astext() for s in sections]

    # REQ_SECTION_SKELETON
    if titles != spec["sections"]:
        _warn(
            "REQ_SECTION_SKELETON",
            f"H2 sections must be exactly {spec['sections']} in that order; found {titles}",
            docname,
            top.line,
        )

    # REQ_GENERATED_VIEWS: a derived section holds one generated table and nothing else.
    from sphinx_needs.directives.needtable import Needtable

    for section in sections:
        if section[0].astext() not in spec["derived"]:
            continue
        body = [c for c in section.children[1:] if not isinstance(c, nodes.target)]
        if len(body) != 1 or not isinstance(body[0], Needtable):
            kinds = [type(c).__name__ for c in body]
            _warn(
                "REQ_GENERATED_VIEWS",
                f"section '{section[0].astext()}' is a derived view and must contain only "
                f"one needtable; found {kinds}",
                docname,
                section.line,
            )


def setup(app: Sphinx) -> dict:
    app.connect("source-read", on_source_read)
    app.connect("env-before-read-docs", on_env_before_read_docs)
    app.connect("doctree-read", on_doctree_read)
    return {"version": "1.0", "parallel_read_safe": True, "parallel_write_safe": True}
