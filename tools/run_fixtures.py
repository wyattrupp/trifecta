"""The fixture runner (COMP_FIXTURE_RUNNER).

Copies the repository, proves the unmutated copy passes, then applies each fixture's
mutations to a fresh copy and asserts the pipeline reports the expected requirement.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check import repo_files  # noqa: E402
from findings import CHILD_ENV, Finding  # noqa: E402
from toolchain import vale_path  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


class FixtureError(Exception):
    """A fixture that cannot be applied: its anchor text is missing or ambiguous."""


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True,
                   encoding="utf-8", errors="replace")


def make_base(tmp: Path) -> Path:
    """Copy what git tracks or would track, so every ignore rule holds, the repository's own
    .git/info/exclude included, which the copy's fresh git would not read."""
    base = tmp / "base"
    files, problems = repo_files(ROOT)
    if problems:
        raise FixtureError(problems[0].message)
    for name in files:
        source, target = ROOT / name, base / name
        if source.is_file() or source.is_symlink():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target, follow_symlinks=False)
    _git(base, "init", "-q")
    _git(base, "-c", "user.name=fixtures", "-c", "user.email=fixtures@localhost",
         "add", "-A")
    _git(base, "-c", "user.name=fixtures", "-c", "user.email=fixtures@localhost",
         "commit", "-q", "-m", "base")
    return base


def apply(copy: Path, mutations: list[dict]) -> None:
    """Apply mutations. Writes translate no newlines, so a fixture's CRLF stays CRLF and its
    LF stays LF on every platform (REQ_ONE_LINE_ENDING)."""
    for m in mutations:
        target = (copy / m["file"]).resolve()
        if not target.is_relative_to(copy.resolve()):
            raise FixtureError(f"{m['file']}: path leaves the repository copy")
        if "find" in m:
            text = target.read_text(encoding="utf-8")
            count = text.count(m["find"])
            if count != 1:
                raise FixtureError(f"{m['file']}: anchor occurs {count} times, expected 1: "
                                   f"{m['find']!r}")
            target.write_text(text.replace(m["find"], m["replace"]), encoding="utf-8",
                              newline="")
        elif "create" in m:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(m["create"], encoding="utf-8", newline="")
        elif m.get("delete"):
            target.unlink()
        else:
            raise FixtureError(f"unknown mutation {m!r}")


def run_check(copy: Path, vale: Path) -> tuple[int, list[Finding]]:
    proc = subprocess.run(
        [sys.executable, str(copy / "tools" / "check.py"), "--root", str(copy),
         "--base", "HEAD", "--vale", str(vale)],
        capture_output=True, encoding="utf-8", errors="replace", env=CHILD_ENV,
    )
    findings = [Finding.parse(l) for l in proc.stdout.splitlines() if l.count("\t") >= 2]
    return proc.returncode, findings


def run_fixture(path: Path, base: Path, tmp: Path, vale: Path) -> tuple[str, bool, str]:
    spec = yaml.safe_load(path.read_text(encoding="utf-8"))
    copy = tmp / path.stem
    shutil.copytree(base, copy, symlinks=True)
    try:
        apply(copy, spec["mutations"])
    except FixtureError as exc:
        return path.stem, False, f"fixture error: {exc}"
    code, findings = run_check(copy, vale)
    hits = [f for f in findings if f.req == spec["expect"]]
    # `only: true` also fails the fixture on any other requirement, for a fixture whose
    # point is that a mutation is read correctly, not only that its error is caught.
    # `allow` names the requirements its mutation also breaks of necessity.
    allowed = {spec["expect"], *spec.get("allow", [])}
    others = spec.get("only") and any(f.req not in allowed for f in findings)
    if code != 0 and hits and not others:
        return path.stem, True, f"{spec['expect']}: {hits[0].message}"
    got = sorted({f.req for f in findings}) or ["no findings"]
    return path.stem, False, f"expected {spec['expect']}, got {', '.join(got)}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("names", nargs="*", help="run only these fixtures")
    parser.add_argument("--vale", type=Path, default=vale_path(ROOT))
    args = parser.parse_args(argv)
    vale = args.vale.resolve()
    fixtures = sorted((ROOT / "tests" / "fixtures").glob("*.yaml"))
    if args.names:
        unknown = sorted(set(args.names) - {f.stem for f in fixtures})
        if unknown:
            parser.error(f"unknown fixture(s): {', '.join(unknown)}")
        fixtures = [f for f in fixtures if f.stem in args.names]

    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        try:
            base = make_base(tmp)
        except (OSError, subprocess.CalledProcessError, FixtureError) as exc:
            print(f"FAIL  control: cannot copy the repository: {exc}")
            return 1
        code, findings = run_check(base, vale)
        if code != 0:
            print("FAIL  control: the unmutated corpus has findings")
            for f in findings:
                print("      " + f.line())
            return 1
        print("ok    control: the unmutated corpus passes")
        with ThreadPoolExecutor(max_workers=os.cpu_count() or 2) as pool:
            results = list(pool.map(lambda f: run_fixture(f, base, tmp, vale), fixtures))

    failed = 0
    for name, ok, detail in results:
        failed += not ok
        print(f"{'ok  ' if ok else 'FAIL'}  {name}: {detail}")
    print(f"\n{len(results) - failed}/{len(results)} fixtures rejected as expected")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
