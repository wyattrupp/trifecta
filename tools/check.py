"""The pipeline (COMP_PIPELINE): every stage, in a fixed order, emitting IF_FINDING lines."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_graph import check as check_graph, load_needs  # noqa: E402
from check_lifecycle import check as check_lifecycle  # noqa: E402
from findings import Finding, from_sphinx  # noqa: E402
from gen_vale import generate  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ext"))

from trifecta import DOC_TYPES  # noqa: E402

# An exact pin with at least one sha256 hash, all on one line (pip accepts that form).
LOCK_LINE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._\-\[\],]*==[^\s=<>~!;]+(?: --hash=sha256:[0-9a-f]{64})+$"
)
VALE_VERSION = re.compile(r"^VALE_VERSION := \d+\.\d+\.\d+$", re.M)
VALE_SHA = re.compile(r"^VALE_SHA256 := [0-9a-f]{64}$", re.M)
VALE_LINE = re.compile(r"^(?P<loc>.+?:\d+:\d+):(?P<check>[\w.]+):(?P<msg>.*)$")


def check_toolchain(root: Path) -> list[Finding]:
    findings = []
    lock = root / "requirements.lock"
    for n, line in enumerate(lock.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if line and not line.startswith("#") and not LOCK_LINE.match(line):
            findings.append(Finding(
                "REQ_PINNED_TOOLCHAIN", f"requirements.lock:{n}", f"not an exact pin with --hash: {line[:80]}",
            ))
    makefile = (root / "Makefile").read_text(encoding="utf-8")
    if not VALE_VERSION.search(makefile) or not VALE_SHA.search(makefile):
        findings.append(Finding(
            "REQ_PINNED_TOOLCHAIN", "Makefile",
            "Vale must be pinned by VALE_VERSION and VALE_SHA256",
        ))
    return findings


def _locate(finding: Finding, needs: dict[str, dict]) -> Finding:
    """Replace a 'need:<ID>' location with the source file and line of that need."""
    if not finding.location.startswith("need:"):
        return finding
    need = needs.get(finding.location[5:])
    if not need:
        return finding
    where = f"docs/{need['docname']}{need['doctype']}:{need['lineno']}"
    return Finding(finding.req, where, finding.message)


def run_sphinx(root: Path) -> list[Finding]:
    docs = root / "docs"
    # --no-color: Sphinx forces ANSI colour when CI=true or on Windows, even into a pipe,
    # and the escape codes break the line-anchored patterns in findings.py.
    # A clean output directory: stale pages of deleted documents would otherwise be linted.
    shutil.rmtree(docs / "_build", ignore_errors=True)
    proc = subprocess.run(
        [sys.executable, "-m", "sphinx", "-q", "-E", "-n", "-W", "--keep-going", "--no-color",
         "-b", "html", str(docs), str(docs / "_build" / "html")],
        capture_output=True, text=True,
    )
    findings = from_sphinx(proc.stderr, str(root) + "/")
    if proc.returncode != 0 and not findings:
        findings.append(Finding("REQ_WARNINGS_FATAL", "(build)", proc.stderr.strip()[-500:]))
    return findings


META_ROW = re.compile(r'<tr class="need meta.*?</tr>', re.S)
TYPED_DIRS = tuple(DOC_TYPES)


def build_lint_view(root: Path) -> Path:
    """Copy the typed pages with need metadata rows removed.

    sphinx-needs renders metadata as block lines nested inside inline spans. That HTML
    is invalid, and Vale loses its IgnoredClasses scope inside it, so the content after
    it escapes scoping. Metadata holds no authored prose, so removing it is equivalent
    to ignoring it.
    """
    html = root / "docs" / "_build" / "html"
    view = root / "docs" / "_build" / "lint"
    for directory in TYPED_DIRS:
        for page in sorted((html / directory).glob("*.html")):
            out = view / directory / page.name
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(META_ROW.sub("", page.read_text(encoding="utf-8")), encoding="utf-8")
    return view


def run_vale(root: Path, vale: Path, config: str) -> list[Finding]:
    html = root / "docs" / "_build" / "lint"
    targets = [str(html / d) for d in TYPED_DIRS if (html / d).is_dir()]
    if not targets:
        return [Finding("REQ_WARNINGS_FATAL", f"vale/{config}", "no typed pages were built to lint")]
    try:
        proc = subprocess.run(
            [str(vale), f"--config={root / 'vale' / config}", "--output=line",
             "--no-exit", *targets],
            capture_output=True, text=True, cwd=root,
        )
    except OSError as exc:
        return [Finding("REQ_WARNINGS_FATAL", f"vale/{config}", f"cannot run {vale}: {exc}")]
    findings = []
    if proc.stderr.strip():
        findings.append(Finding("REQ_WARNINGS_FATAL", f"vale/{config}", proc.stderr.strip()[:500]))
    for line in proc.stdout.splitlines():
        if not (m := VALE_LINE.match(line)):
            continue
        req = re.search(r"REQ_[A-Z_]+", m.group("check"))
        loc = m.group("loc").split(str(root) + "/", 1)[-1]
        msg = m.group("msg").split(": ", 1)[-1] if req else m.group("msg")
        findings.append(Finding(req.group(0) if req else "REQ_WARNINGS_FATAL", loc, msg))
    return findings


def audit_fixtures(needs: dict[str, dict], fixtures: Path) -> list[Finding]:
    expected = set()
    for path in sorted(fixtures.glob("*.yaml")):
        expected.add((yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("expect"))
    return [
        Finding("REQ_FIXTURE_PER_INVARIANT", f"{fixtures.name}/",
                f"no negative fixture expects {need['id']}")
        for need in needs.values()
        if need["type"] == "req" and need["id"] not in expected
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--base", help="git ref to check MADR immutability against")
    parser.add_argument("--vale", type=Path, default=None)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    vale = (args.vale or root / "bin" / "vale").resolve()

    findings = check_toolchain(root)
    findings += run_sphinx(root)
    needs_json = root / "docs" / "_build" / "html" / "needs.json"
    if needs_json.is_file():
        needs = load_needs(needs_json)
        findings += check_graph(needs, root)
        findings += generate(needs, root / "styles" / "TrifectaGenerated")
        findings = [_locate(f, needs) for f in findings]
        build_lint_view(root)
        findings += run_vale(root, vale, "normative.ini")
        findings += run_vale(root, vale, "prose.ini")
        findings += audit_fixtures(needs, root / "tests" / "fixtures")
    else:
        findings.append(Finding(
            "REQ_WARNINGS_FATAL", "docs/_build/html/needs.json",
            "the build produced no needs.json, so graph, lint and fixture checks did not run",
        ))
    if args.base:
        findings += check_lifecycle(root, args.base)

    for finding in sorted(set(findings)):
        print(finding.line())
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
