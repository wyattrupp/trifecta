"""Take a document's digest when a review starts, and stamp the review with it
(COMP_REVIEW_COMMAND, DEC_0011).

    python tools/review.py digest docs/plans/0002-plan-and-review-lifecycle.md
    python tools/review.py stamp docs/plans/0002-plan-and-review-lifecycle.md \\
        --digest D --lenses "Correctness; security" --k 2

``stamp`` appends a review record to the document's Review section with today's date. It
refuses a path that is not a typed document, and a digest that no longer matches the file,
since then the text the review read is not the text it would be recorded against.
"""

from __future__ import annotations

import argparse
import datetime
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ext"))

import digest as reviewed  # noqa: E402
from trifecta import doc_need_id, doc_type  # noqa: E402

REVIEW_ID_RE = re.compile(r"^:id: REV_[A-Z]+_\d{4}_(?P<n>\d+)\s*$")


class Refused(Exception):
    pass


def typed(path: Path) -> tuple[str, str]:
    """The document's directive and need ID, or Refused."""
    try:
        rel = path.resolve().relative_to((ROOT / "docs").resolve())
    except ValueError:
        raise Refused(f"{path} is not under docs/") from None
    docname = rel.with_suffix("").as_posix()
    kind, need_id = doc_type(docname), doc_need_id(docname)
    if path.suffix != ".md" or not path.is_file() or not kind or not need_id:
        raise Refused(f"{path} is not a typed document")
    directive = kind[1]["directive"]
    if directive not in reviewed.RELIED_ON:
        raise Refused(f"a {directive} carries no review")
    return directive, need_id


def stamp(path: Path, given: str, lenses: str, k: int, today: str) -> str:
    """Append a review record carrying ``given``; return its ID."""
    directive, need_id = typed(path)
    text = reviewed.read(path)
    current = reviewed.digest(text, directive)
    if given != current:
        raise Refused(f"{path} changed since the review started: its digest is now "
                      f"{current}, not {given}; review the current text")
    if k < 1 or not lenses.strip() or "\n" in lenses:
        raise Refused("--k is a positive number and --lenses one line of text")
    lines = text.replace("\r\n", "\n").split("\n")
    section = reviewed.review_section(lines)
    if section is None:
        raise Refused(f"{path} has no Review section")
    numbers = [int(m.group("n")) for line in lines if (m := REVIEW_ID_RE.match(line))]
    review_id = f"REV_{need_id}_{max(numbers, default=0) + 1}"
    record = ["", f":::{{review}} {lenses.strip()}", f":id: {review_id}", f":k: {k}",
              f":date: {today}", f":digest: {current}", ":::"]
    end = section.end
    while end > 0 and not lines[end - 1].strip():
        end -= 1  # write after the last record, not after trailing blank lines
    tail = lines[section.end:]
    out = lines[:end] + record + ([""] + tail if tail and tail != [""] else [""])
    path.write_bytes("\n".join(out).encode("utf-8"))
    return review_id


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    d = sub.add_parser("digest", help="print the digest of a document's reviewed content")
    d.add_argument("doc", type=Path)
    s = sub.add_parser("stamp", help="append a review record carrying the digest")
    s.add_argument("doc", type=Path)
    s.add_argument("--digest", required=True)
    s.add_argument("--lenses", required=True)
    s.add_argument("--k", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "digest":
            directive, _ = typed(args.doc)
            print(reviewed.digest(reviewed.read(args.doc), directive))
        else:
            print(stamp(args.doc, args.digest, args.lenses, args.k,
                        datetime.date.today().isoformat()))
    except Refused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
