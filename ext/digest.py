"""The review digest (COMP_REVIEW_DIGEST, IF_REVIEW_DIGEST, DEC_0011).

A document's reviewed content is its raw file less what changes without changing what was
reviewed: the frontmatter ``status`` line, ``:spec:`` option lines, the Review section,
and for a plan the As built section and its step marks. The digest is the SHA-256 of that
content. Pure functions with no Sphinx import, so ``tools/review.py`` uses them without a
build.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

import plans

#: Per directive, the statuses in which a document is relied on, so it must be reviewed and
#: its review must be current. docs/conf.py reads this for REQ_REVIEWED.
RELIED_ON = {
    "rfc": ("accepted",),
    "design": ("approved", "implemented"),
    "plan": plans.RELIED_ON,
}
#: Sections left out of the reviewed content: the review records themselves, and a plan's
#: account of how it was built.
LEFT_OUT = {"rfc": ("Review",), "design": ("Review",), "plan": ("Review", "As built")}

STATUS_RE = re.compile(r"^status:")
SPEC_RE = re.compile(r"^:spec:")
#: The directives whose ``spec`` option names the artifact built for them.
SPEC_OPEN_RE = re.compile(r"^:{3,}\{(?:component|interface)\}")
REVIEW_OPEN_RE = re.compile(r"^(?P<colons>:{3,})\{review\}")
DIGEST_RE = re.compile(r"^:digest:[ \t]*(?P<digest>\S*)[ \t]*$")


def _frontmatter_status(lines: list[str]) -> int | None:
    """Index of the ``status:`` line inside the first ``---`` block, if there is one."""
    end = plans.frontmatter_end(lines)
    return next((i for i in range(1, end) if STATUS_RE.match(lines[i])), None) if end else None


def _spec_lines(lines: list[str], code: list[bool]) -> set[int]:
    """``:spec:`` option lines of component and interface directives, and no other line."""
    out = set()
    for i, line in enumerate(lines):
        if code[i] or not SPEC_OPEN_RE.match(line):
            continue
        j = i + 1
        while j < len(lines) and plans.OPTION_RE.match(lines[j]):
            if SPEC_RE.match(lines[j]):
                out.add(j)
            j += 1
    return out


def sections(lines: list[str]) -> dict[str, tuple[int, int]]:
    """H2 title -> (heading index, end index), reading only H2 lines outside code fences."""
    return plans.parse(lines).sections


def reviewed_content(text: str, directive: str) -> str:
    """The text a review covers, exactly as IF_REVIEW_DIGEST states. CRLF reads as LF
    (REQ_ONE_LINE_ENDING)."""
    lines = text.replace("\r\n", "\n").split("\n")
    code = plans.fenced(lines)
    drop = set()
    if (status := _frontmatter_status(lines)) is not None:
        drop.add(status)
    drop.update(_spec_lines(lines, code))
    spans = sections(lines)
    for title in LEFT_OUT.get(directive, ("Review",)):
        if title in spans:
            drop.update(range(*spans[title]))
    kept = []
    for i, line in enumerate(lines):
        if i in drop:
            continue
        if directive == "plan" and not code[i] and plans.STEP_RE.match(line):
            line = line[:3] + plans.OPEN + line[4:]  # "- [x] " -> "- [ ] "
        kept.append(line.rstrip())
    return "\n".join(kept).rstrip("\n")


def digest(text: str, directive: str) -> str:
    return hashlib.sha256(reviewed_content(text, directive).encode("utf-8")).hexdigest()


def read(path: Path) -> str:
    """The raw file as text: bytes decoded as UTF-8 less a byte order mark, as Sphinx reads
    it, with newlines untranslated."""
    return path.read_bytes().decode("utf-8-sig")


@dataclass
class ReviewSection:
    digests: list[str]  # the digest of every review record that carries one
    stray: list[int]  # 0-based lines in the section that belong to no review record
    end: int  # index where a new record goes: the section's end


def review_section(lines: list[str]) -> ReviewSection | None:
    """The review records in the Review section, and any line outside them."""
    spans = sections(lines)
    if "Review" not in spans:
        return None
    start, end = spans["Review"]
    code = plans.fenced(lines)
    digests, stray = [], []
    i = start + 1
    while i < end:
        m = None if code[i] else REVIEW_OPEN_RE.match(lines[i])
        if not m:
            if lines[i].strip():
                stray.append(i)
            i += 1
            continue
        closer = m.group("colons")
        j = i + 1
        while j < end and lines[j].rstrip() != closer:
            if d := DIGEST_RE.match(lines[j]):
                digests.append(d.group("digest"))
            j += 1
        if j == end:
            stray.append(i)  # never closed inside the section
        i = j + 1
    return ReviewSection(digests, stray, end)


def problems(text: str, directive: str, status: str | None) -> list[tuple[str, int]]:
    """REQ_REVIEW_CURRENT, as (message, 1-based line)."""
    lines = text.replace("\r\n", "\n").split("\n")
    section = review_section(lines)
    if section is None:
        return []  # REQ_SECTION_SKELETON reports a missing Review section
    out = [("a Review section holds only review records", i + 1) for i in section.stray]
    if status in RELIED_ON.get(directive, ()):
        current = digest(text, directive)
        if current not in section.digests:
            out.append((f"no review carries the current digest {current}; review the "
                        f"document and stamp the review with tools/review.py",
                        sections(lines)["Review"][0] + 1))
    return out
