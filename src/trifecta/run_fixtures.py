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
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

from .check import repo_files
from .findings import Finding, child_env
from .profiler import DIRECTORY as PROFILE_DIR, Profiler, seconds, target as profile_target
from .profiler import read as read_profile, write as write_profile
from .store import ENV as STORE_ENV
from .toolchain import VALE_ENV, OutsideRepository, corpus_root, vale_path


class FixtureError(Exception):
    """A fixture that cannot be applied: its anchor text is missing or ambiguous."""


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True,
                   encoding="utf-8", errors="replace")


def make_base(tmp: Path, root: Path) -> Path:
    """Copy what git tracks or would track, so every ignore rule holds, the repository's own
    .git/info/exclude included, which the copy's fresh git would not read."""
    base = tmp / "base"
    files, problems = repo_files(root)
    if problems:
        raise FixtureError(problems[0].message)
    for name in files:
        source, target = root / name, base / name
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


def run_check(copy: Path, vale: Path, cache: Path,
              fresh: bool = False) -> tuple[int, list[Finding], list[dict]]:
    """The copy's check: its exit status, its findings and the stages its profile lists."""
    # The copy's own package runs, so a fixture that changes the package's code or data
    # is checked by that changed code (REQ_SELF_TESTS_SCOPED: this repository only).
    # A profile copied from the control is removed first, so only this run's is read.
    profile = copy / PROFILE_DIR / "check.json"
    profile.unlink(missing_ok=True)
    proc = subprocess.run(
        [sys.executable, "-m", "trifecta", "check", "--base", "HEAD", *(["--fresh"] if fresh else [])],
        capture_output=True, encoding="utf-8", errors="replace", cwd=copy,
        env={**child_env(copy / "src"), VALE_ENV: str(vale), STORE_ENV: str(cache)},
    )
    findings = [Finding.parse(l) for l in proc.stdout.splitlines() if l.count("\t") >= 2]
    data = read_profile(profile)
    return proc.returncode, findings, data["stages"] if data else []


def run_fixture(path: Path, base: Path, tmp: Path, vale: Path,
                cache: Path, fresh: bool = False) -> tuple[str, bool, str, dict]:
    begin = time.perf_counter()
    spec = yaml.safe_load(path.read_text(encoding="utf-8"))
    copy = tmp / path.stem
    shutil.copytree(base, copy, symlinks=True)
    copied = time.perf_counter()
    record = {"name": path.stem, "copy_seconds": seconds(copied - begin)}

    def done(ok: bool, detail: str) -> tuple[str, bool, str, dict]:
        record.update(seconds=seconds(time.perf_counter() - begin), ok=ok)
        record.setdefault("stages", [])
        return path.stem, ok, detail, record

    try:
        apply(copy, spec["mutations"])
    except FixtureError as exc:
        record["mutate_seconds"] = seconds(time.perf_counter() - copied)
        return done(False, f"fixture error: {exc}")
    mutated = time.perf_counter()
    record["mutate_seconds"] = seconds(mutated - copied)
    code, findings, record["stages"] = run_check(copy, vale, cache, fresh)
    record["check_seconds"] = seconds(time.perf_counter() - mutated)
    hits = [f for f in findings if f.req == spec["expect"]]
    # `only: true` also fails the fixture on any other requirement, for a fixture whose
    # point is that a mutation is read correctly, not only that its error is caught.
    # `allow` names the requirements its mutation also breaks of necessity.
    allowed = {spec["expect"], *spec.get("allow", [])}
    others = spec.get("only") and any(f.req not in allowed for f in findings)
    if code != 0 and hits and not others:
        return done(True, f"{spec['expect']}: {hits[0].message}")
    got = sorted({f.req for f in findings}) or ["no findings"]
    return done(False, f"expected {spec['expect']}, got {', '.join(got)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("names", nargs="*", help="run only these fixtures")
    parser.add_argument("--profile", type=Path, help="where to write the profile "
                        f"(default {PROFILE_DIR.as_posix()}/fixtures.json)")
    parser.add_argument("--fresh", action="store_true",
                        help="run every copy's check with --fresh, reusing no stored result")
    root = corpus_root()
    args = parser.parse_args(argv)
    try:
        profile = profile_target(args.profile, root, "fixtures.json")
    except OutsideRepository as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    vale = vale_path(root).resolve()
    fixtures = sorted((root / "tests" / "fixtures").glob("*.yaml"))
    if args.names:
        unknown = sorted(set(args.names) - {f.stem for f in fixtures})
        if unknown:
            parser.error(f"unknown fixture(s): {', '.join(unknown)}")
        fixtures = [f for f in fixtures if f.stem in args.names]
    # The base copy, the control and every fixture are timed (COMP_PROFILER); the profile
    # is written whatever the outcome, and changes neither the output nor the exit status.
    profiler = Profiler("fixtures")
    extra: dict = {"base": None, "control": None, "fixtures": []}
    try:
        return _run(root, vale, fixtures, profiler, extra, args.fresh)
    finally:
        write_profile(profile, profiler.data(**extra))


def _run(root: Path, vale: Path, fixtures: list[Path], profiler: Profiler,
         extra: dict, fresh: bool = False) -> int:
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        with profiler.stage("base copy") as record:
            try:
                base = make_base(tmp, root)
            except (OSError, subprocess.CalledProcessError, FixtureError) as exc:
                base = None
                problem = exc
        extra["base"] = {"seconds": record["seconds"]}
        if base is None:
            print(f"FAIL  control: cannot copy the repository: {problem}")
            return 1
        # The control runs first, into a store every copy shares, so a copy reuses each
        # result whose recorded inputs it left as they were (COMP_RESULT_STORE).
        cache = tmp / "store"
        cache.mkdir()
        with profiler.stage("control") as record:
            code, findings, stages = run_check(base, vale, cache, fresh)
        extra["control"] = {"seconds": record["seconds"], "ok": code == 0, "stages": stages}
        if code != 0:
            print("FAIL  control: the unmutated corpus has findings")
            for f in findings:
                print("      " + f.line())
            return 1
        print("ok    control: the unmutated corpus passes")
        with profiler.stage("fixtures"):
            with ThreadPoolExecutor(max_workers=os.cpu_count() or 2) as pool:
                results = list(pool.map(lambda f: run_fixture(f, base, tmp, vale, cache, fresh),
                                        fixtures))
        extra["fixtures"] = [r[3] for r in results]

    failed = 0
    for name, ok, detail, _ in results:
        failed += not ok
        print(f"{'ok  ' if ok else 'FAIL'}  {name}: {detail}")
    print(f"\n{len(results) - failed}/{len(results)} fixtures rejected as expected")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
