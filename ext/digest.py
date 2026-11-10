"""The review digest (COMP_REVIEW_DIGEST, IF_REVIEW_DIGEST, DEC_0011).

A document's reviewed content is its raw file less what changes without changing what was
reviewed: the frontmatter ``status`` line, ``:spec:`` option lines, the Review section,
and for a plan the As built section and its step marks. The digest is the SHA-256 of that
content.

Structure (H2 headings, code fences, directives, HTML blocks) is read with MyST's own
Markdown parser, configured as the build configures it, so this module finds exactly the
sections and blocks Sphinx renders: a regex reading of Markdown can be led to see a
heading or a fence that the build does not, or to miss one it does. No Sphinx build runs,
so ``tools/review.py`` uses these functions on their own.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

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
#: The MyST extensions the build enables. docs/conf.py reads this, so the digest parses
#: the file as the build does.
MYST_EXTENSIONS = ("colon_fence",)

STATUS_RE = re.compile(r"^status:")
SPEC_RE = re.compile(r"^:spec:")
DIGEST_RE = re.compile(r"^:digest:[ \t]*(?P<digest>\S*)[ \t]*$")
#: Line breaks as Sphinx and MyST read a source file: CRLF, a lone CR and LF.
BREAK_RE = re.compile(r"\r\n|\r|\n")
#: The directives whose ``spec`` option names the artifact built for them.
SPEC_DIRECTIVES = ("{component}", "{interface}")
#: Block tokens that can define a need or hide text from a reader: a directive is a fence.
BLOCK_TOKENS = ("fence", "colon_fence", "html_block")
#: What a review record's body may hold besides its options: plain paragraphs, with no
#: raw HTML inside them.
PLAIN_TOKENS = ("paragraph_open", "inline", "paragraph_close")

_md = None


def _parse(text: str) -> list:
    global _md
    if _md is None:
        from markdown_it.renderer import RendererHTML
        from myst_parser.config.main import MdParserConfig
        from myst_parser.parsers.mdit import create_md_parser

        _md = create_md_parser(MdParserConfig(enable_extensions=set(MYST_EXTENSIONS)),
                               RendererHTML)
    return _md.parse(text)


def split_lines(text: str) -> list[str]:
    """The file's lines, CRLF and a lone CR read as LF (REQ_ONE_LINE_ENDING)."""
    return BREAK_RE.split(text)


@dataclass
class Structure:
    """What MyST finds in a file, by 0-based line."""

    lines: list[str]
    tokens: list
    h2: list[tuple[int, str]] = field(default_factory=list)  # (line, title), top level
    code: list[bool] = field(default_factory=list)  # inside a backtick or tilde fence

    def spans(self, title: str) -> list[tuple[int, int]]:
        """(heading line, end) of every H2 section with this title."""
        out = []
        for k, (line, name) in enumerate(self.h2):
            if name == title:
                end = self.h2[k + 1][0] if k + 1 < len(self.h2) else len(self.lines)
                out.append((line, end))
        return out


def structure(lines: list[str]) -> Structure:
    """Parse the file as the build sees it: the extension blanks the frontmatter block, up
    to its first ``---`` closer, before MyST reads the rest."""
    end = plans.frontmatter_end(lines)
    seen = [""] * (end + 1) + lines[end + 1:] if end is not None else lines
    tokens = _parse("\n".join(seen))
    found = Structure(lines, tokens, code=[False] * len(lines))
    for k, tok in enumerate(tokens):
        if tok.type == "heading_open" and tok.tag == "h2" and tok.level == 0 and tok.map:
            found.h2.append((tok.map[0], tokens[k + 1].content.strip()))
        if tok.type == "fence" and tok.map:
            for i in range(*tok.map):
                found.code[i] = True
    return found


def _frontmatter_status(lines: list[str]) -> int | None:
    """Index of the line YAML reads as the frontmatter's one ``status`` key and its value,
    when that pair fills one line on its own; otherwise None, and nothing is left out."""
    end = plans.frontmatter_end(lines)
    if not end:
        return None
    try:
        root = yaml.compose("\n".join(lines[1:end]), Loader=plans.NoTimestampLoader)
    except yaml.YAMLError:
        return None
    if not isinstance(root, yaml.MappingNode):
        return None
    pairs = [(k, v) for k, v in root.value if isinstance(k, yaml.ScalarNode) and k.value == "status"]
    if len(pairs) != 1:
        return None
    key, value = pairs[0]
    line = key.start_mark.line
    if (key.start_mark.column != 0 or not isinstance(value, yaml.ScalarNode)
            or value.end_mark.line != line or not STATUS_RE.match(lines[line + 1])):
        return None
    return line + 1


def _spec_lines(found: Structure) -> set[int]:
    """``:spec:`` option lines of component and interface directives, and no other line."""
    out = set()
    for tok in found.tokens:
        if tok.type not in ("colon_fence", "fence") or not tok.map or tok.info.split()[:1] not in (
                [d] for d in SPEC_DIRECTIVES):
            continue
        j = tok.map[0] + 1
        while j < tok.map[1] and plans.OPTION_RE.match(found.lines[j]):
            if SPEC_RE.match(found.lines[j]):
                out.add(j)
            j += 1
    return out


def reviewed_content(text: str, directive: str) -> str:
    """The text a review covers, exactly as IF_REVIEW_DIGEST states."""
    lines = split_lines(text)
    found = structure(lines)
    drop = set()
    if (status := _frontmatter_status(lines)) is not None:
        drop.add(status)
    drop.update(_spec_lines(found))
    for title in LEFT_OUT.get(directive, ("Review",)):
        for span in found.spans(title):
            drop.update(range(*span))
    kept = []
    for i, line in enumerate(lines):
        if i in drop:
            continue
        if directive == "plan" and not found.code[i] and plans.STEP_RE.match(line):
            line = line[:3] + plans.OPEN + line[4:]  # "- [x] " -> "- [ ] "
        kept.append(line.rstrip(" \t"))
    return "\n".join(kept).rstrip("\n")


def digest(text: str, directive: str) -> str:
    return hashlib.sha256(reviewed_content(text, directive).encode("utf-8")).hexdigest()


def read(path: Path) -> str:
    """The raw file as text: bytes decoded as UTF-8 less a byte order mark, as Sphinx reads
    it, with newlines untranslated."""
    return path.read_bytes().decode("utf-8-sig")


@dataclass
class ReviewSection:
    digests: list[str]  # the digest of every well-formed review record that carries one
    stray: list[int]  # 0-based lines that are no part of a well-formed review record
    end: int  # index where a new record goes: the section's end


def _record(tok, lines: list[str]) -> tuple[list[str], bool]:
    """A review record's option-line digests, and whether it is well formed: closed, with
    nothing in its body but option lines and plain paragraphs."""
    start, end = tok.map
    opener = re.match(r"^ {0,3}(:{3,})", lines[start])
    closer = re.match(r"^ {0,3}(:{3,})[ \t]*$", lines[end - 1])
    closed = (end - 1 > start and opener is not None and closer is not None
              and len(closer.group(1)) >= len(opener.group(1)))
    body = tok.content.split("\n")
    digests, k = [], 0
    while k < len(body) and plans.OPTION_RE.match(body[k]):
        if d := DIGEST_RE.match(body[k]):
            digests.append(d.group("digest"))
        k += 1
    rest = _parse("\n".join(body[k:]))
    plain = all(t.type in PLAIN_TOKENS for t in rest) and not any(
        c.type == "html_inline" for t in rest for c in (t.children or []))
    return digests, closed and plain


def review_section(lines: list[str], found: Structure | None = None) -> ReviewSection | None:
    """The review records in the Review section, and every line that is not part of one.

    A record is a top-level ``review`` directive whose body holds its options and plain
    paragraphs; only a ``digest`` among its options counts. A second Review section is
    stray in full."""
    found = found or structure(lines)
    spans = found.spans("Review")
    if not spans:
        return None
    (start, end), extra = spans[0], spans[1:]
    digests, stray = [], [s for s, _ in extra]
    for tok in found.tokens:
        if not tok.map or tok.level != 0 or not start < tok.map[0] < end:
            continue
        if tok.type == "colon_fence" and tok.info.split()[:1] == ["{review}"]:
            got, ok = _record(tok, lines)
            if ok:
                digests += got
                continue
        stray.append(tok.map[0])
    return ReviewSection(digests, sorted(stray), end)


def blocks_in(found: Structure, title: str) -> list[int]:
    """Lines where a block opens, at any depth, in a section left out of the digest."""
    spans = found.spans(title)
    return sorted({tok.map[0] for tok in found.tokens if tok.type in BLOCK_TOKENS and tok.map
                   and any(s < tok.map[0] < e for s, e in spans)})


def problems(text: str, directive: str, status: str | None) -> list[tuple[str, int]]:
    """REQ_REVIEW_CURRENT, as (message, 1-based line)."""
    lines = split_lines(text)
    found = structure(lines)
    relied_on = status in RELIED_ON.get(directive, ())
    section = review_section(lines, found)
    if section is None:
        # Fail closed: a relied-on document whose Review section is not found would
        # otherwise pass with no review at all.
        return [("no Review section is found", 1)] if relied_on else []
    out = [("a Review section holds only review records, each closed, with options and "
            "plain paragraphs", i + 1) for i in section.stray]
    for title in LEFT_OUT.get(directive, ()):
        if title != "Review":
            out += [(f"the {title} section is outside the digest, so it opens no block",
                     i + 1) for i in blocks_in(found, title)]
    if relied_on:
        current = digest(text, directive)
        if current not in section.digests:
            out.append((f"no review carries the current digest {current}; review the "
                        f"document and stamp the review with tools/review.py",
                        found.spans("Review")[0][0] + 1))
    return out
