"""Write a skeleton document (COMP_NEW_COMMAND).

    python tools/new.py rfc <slug>
    python tools/new.py decision <slug>
    python tools/new.py design <slug>
    python tools/new.py plan <slug> --implements DES_NNNN

The document takes its type's next number and today's date, and has every section its
type declares. The shapes come from ``DOC_TYPES`` in ext/trifecta.py and from
ext/plans.py, the constants the check reads, so there is no template to drift. A
skeleton is a draft and passes the check; review is what makes it accepted, approved
or active.
"""

from __future__ import annotations

import argparse
import datetime
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "ext"))

import plans  # noqa: E402
from trifecta import DOC_TYPES, FILENAME_RE  # noqa: E402

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ELEMENT_RE = re.compile(r"^:id: ((?:COMP|IF)_[A-Z0-9_]+)\s*$", re.M)
TODO = "TODO."

#: The design doc's derived views, as written in docs/design/0001.
NEEDTABLES = {
    "Requirements": ":::{needtable}\n:filter: type == 'req' and len(satisfies_back) > 0\n"
                    ":columns: id, title, satisfies_back as \"Satisfied by\"\n:style: table\n:::",
    "Constraints": ":::{needtable}\n:filter: type == 'decision' and len(constrained_by_back) > 0\n"
                   ":columns: id, title, status\n:style: table\n:::",
}


def _author() -> str:
    try:
        name = subprocess.run(["git", "-C", str(ROOT), "config", "user.name"],
                              capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        name = ""
    return name or "unknown"


def _next_number(directory: Path) -> str:
    numbers = [int(m.group(1)) for p in directory.glob("*.md") if (m := FILENAME_RE.match(p.stem))]
    return f"{max(numbers, default=0) + 1:04d}"


def _design_elements(design_id: str) -> list[str]:
    number = design_id.removeprefix("DES_")
    files = sorted((ROOT / "docs" / "design").glob(f"{number}-*.md"))
    if not re.fullmatch(r"\d{4}", number) or not files:
        sys.exit(f"no design doc {design_id} under docs/design/")
    return ELEMENT_RE.findall(files[0].read_text(encoding="utf-8"))


def render(kind: str, number: str, slug: str, author: str, today: str,
           implements: str | None = None) -> str:
    directory, spec = next((d, s) for d, s in DOC_TYPES.items() if s["directive"] == kind)
    title = slug.replace("-", " ").capitalize()
    front = {
        "rfc": [("status", "draft"), ("authors", f"[{author}]"), ("created", today)],
        "decision": [("status", "proposed"), ("date", today), ("decision-makers", f"[{author}]")],
        "design": [("status", "draft"), ("authors", f"[{author}]")],
        "plan": [("status", "draft"), ("authors", f"[{author}]"), ("created", today)],
    }[kind]
    links, body = [], {s: TODO for s in spec["sections"]}
    body.update({s: NEEDTABLES[s] for s in spec["derived"]})

    if kind == "decision":
        a, b = f"OPT_{number}_A", f"OPT_{number}_B"
        links = [f":chooses: {a}"]
        body["Considered Options"] = "\n\n".join(
            f":::{{opt}} {TODO}\n:id: {o}\n{TODO}\n:::" for o in (a, b))
        body["Decision Outcome"] = f"Chosen option: {{need}}`{a}`, because {TODO}"
    if kind == "plan":
        elements = _design_elements(implements)
        if not elements:
            sys.exit(f"{implements} has no components or interfaces to build yet")
        links = [f":implements: {implements}"]
        body["Tasks"] = "\n".join([
            f":::{{task}} {TODO}",
            f":id: {plans.task_id(number, 1)}",
            f":builds: {', '.join(elements)}",
            f":gate: {TODO}",
            plans.step_line(1, 1, TODO),
            ":::",
        ])
        body["Review"] = body["As built"] = ""

    out = ["---", *(f"{k}: {v}" for k, v in front), "---", f"# {title}", "",
           f":::{{{spec['directive']}}}", *links, ":::"]
    for section in spec["sections"]:
        out += ["", f"## {section}"] + (["", body[section]] if body[section] else [])
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("kind", choices=[s["directive"] for s in DOC_TYPES.values()])
    parser.add_argument("slug", help="lowercase words joined by hyphens")
    parser.add_argument("--implements", help="the design doc a plan implements, DES_NNNN")
    args = parser.parse_args(argv)
    if not SLUG_RE.match(args.slug):
        parser.error(f"slug must be lowercase words joined by hyphens, got {args.slug!r}")
    if (args.kind == "plan") != bool(args.implements):
        parser.error("--implements is required for a plan and only for a plan")

    directory = ROOT / "docs" / next(d for d, s in DOC_TYPES.items() if s["directive"] == args.kind)
    number = _next_number(directory)
    path = directory / f"{number}-{args.slug}.md"
    if path.exists():
        parser.error(f"{path.relative_to(ROOT)} exists")
    today = datetime.date.today().isoformat()
    path.write_text(render(args.kind, number, args.slug, _author(), today, args.implements),
                    encoding="utf-8", newline="\n")
    print(path.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())
