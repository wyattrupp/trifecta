"""The profile (COMP_PROFILER, IF_PROFILE, DEC_0029): where a run of the check or the
fixture runner spends its time, written as JSON beside the build and never on standard
output, so no finding, no byte of standard output and no exit status depends on it.

    trifecta profile docs/_build/profile/check.json

prints a profile as Markdown tables, slowest first, for a person or a CI job summary.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from contextlib import contextmanager
from pathlib import Path

from .toolchain import OutsideRepository, corpus_root, inside

VERSION = 1
#: Where each command writes its profile when ``--profile`` names no other path; kept out
#: of the clean before the Sphinx build.
DIRECTORY = Path("docs") / "_build" / "profile"


def target(given: Path | None, root: Path, name: str) -> Path:
    """Where a command writes its profile: the path ``--profile`` names, or ``name`` in
    DIRECTORY; OutsideRepository when it resolves outside the repository (IF_CLI)."""
    return inside(given if given is not None else DIRECTORY / name, root)


def seconds(value: float) -> float:
    """Wall-clock seconds rounded to milliseconds (IF_PROFILE)."""
    return round(value, 3)


class Profiler:
    """Times named stages in the order they run."""

    def __init__(self, command: str):
        self.command = command
        self.start = time.perf_counter()
        self.stages: list[dict] = []

    @contextmanager
    def stage(self, name: str):
        """Time one stage; the record is added once the stage ends, raised or not."""
        record: dict = {"name": name}
        begin = time.perf_counter()
        try:
            yield record
        finally:
            record["seconds"] = seconds(time.perf_counter() - begin)
            self.stages.append(record)

    def data(self, **extra) -> dict:
        return {"version": VERSION, "command": self.command,
                "total": seconds(time.perf_counter() - self.start),
                "stages": self.stages, **extra}


def write(path: Path, data: dict) -> None:
    """Write a profile; a failure is one line on standard error and nothing else."""
    tmp = path.with_name(path.name + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
        tmp.replace(path)
    except OSError as exc:
        print(f"trifecta: cannot write the profile {path}: {exc}", file=sys.stderr)
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def read(path: Path) -> dict | None:
    """A profile another run wrote, or None when it is missing or not a profile."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not (isinstance(data, dict) and data.get("version") == VERSION
            and isinstance(data.get("stages"), list)):
        return None
    return data


#: Characters a table cell escapes, so a name prints as text and never as markup.
_MARKUP = {c: "\\" + c for c in "\\`*_[]<>|#!"}


def _cell(value) -> str:
    text = " ".join(str(value).split())
    return "".join(_MARKUP.get(c, c) for c in text)


def _reuse(stage: dict) -> str:
    if "reused" not in stage:
        return ""
    if stage["reused"]:
        return f"yes: {stage['why']}" if stage.get("why") else "yes"
    return f"no: {stage['why']}" if stage.get("why") else "no"


def _stage_table(stages: list[dict]) -> list[str]:
    rows = ["| Stage | Seconds | Reused |", "|---|---:|---|"]
    for s in sorted(stages, key=lambda s: -s.get("seconds", 0)):
        rows.append(f"| {_cell(s.get('name', ''))} | {s.get('seconds', 0):.3f} "
                    f"| {_cell(_reuse(s))} |")
    return rows


def table(data: dict) -> str:
    """A profile as Markdown: the stages by time, and for the fixture runner each fixture
    and each check stage summed over every fixture, by time."""
    out = [f"### trifecta {_cell(data.get('command', ''))}: {data.get('total', 0):.3f} s", ""]
    out += _stage_table(data.get("stages", []))
    if data.get("command") != "fixtures":
        return "\n".join(out) + "\n"
    fixtures = data.get("fixtures", [])
    control = data.get("control") or {}
    if control.get("stages"):
        out += ["", "#### Control", ""] + _stage_table(control["stages"])
    sums: dict[str, list] = {}
    for f in fixtures:
        for s in f.get("stages", []):
            entry = sums.setdefault(s.get("name", ""), [0.0, 0, 0])
            entry[0] += s.get("seconds", 0)
            entry[1] += 1
            entry[2] += bool(s.get("reused"))
    if sums:
        out += ["", "#### Check stages summed over the fixtures", "",
                "| Stage | Seconds | Runs | Reused |", "|---|---:|---:|---:|"]
        for name, (total, runs, reused) in sorted(sums.items(), key=lambda kv: -kv[1][0]):
            out.append(f"| {_cell(name)} | {total:.3f} | {runs} | {reused} |")
    out += ["", "#### Fixtures", "", "| Fixture | Seconds | Copy | Check | Result |",
            "|---|---:|---:|---:|---|"]
    for f in sorted(fixtures, key=lambda f: -f.get("seconds", 0)):
        out.append(f"| {_cell(f.get('name', ''))} | {f.get('seconds', 0):.3f} "
                   f"| {f.get('copy_seconds', 0):.3f} | {f.get('check_seconds', 0):.3f} "
                   f"| {'ok' if f.get('ok') else 'FAIL'} |")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="+", type=Path, help="profiles to print")
    args = parser.parse_args(argv)
    root = corpus_root()
    status = 0
    for path in args.paths:
        try:
            inside(path, root)
        except OutsideRepository as exc:
            print(f"refused: {exc}", file=sys.stderr)
            status = 1
            continue
        data = read(path)
        if data is None:
            print(f"trifecta profile: {path} is not a profile", file=sys.stderr)
            status = 1
            continue
        sys.stdout.write(table(data) + "\n")
    return status
