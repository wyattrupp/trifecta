"""The pipeline (COMP_PIPELINE): every stage, in a fixed order, emitting IF_FINDING lines."""

from __future__ import annotations

import argparse
import ast
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_graph import check as check_graph, load_needs  # noqa: E402
from check_lifecycle import check as check_lifecycle  # noqa: E402
from findings import CHILD_ENV, Finding, from_sphinx, relative_location, unportable  # noqa: E402
from gen_vale import generate  # noqa: E402
from toolchain import VALE_SUFFIXES, vale_path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ext"))

from trifecta import DOC_TYPES  # noqa: E402

# An exact pin with at least one sha256 hash, all on one line (pip accepts that form).
LOCK_LINE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._\-\[\],]*==[^\s=<>~!;]+(?: --hash=sha256:[0-9a-f]{64})+$"
)
#: The release address and the redirect hosts the setup script's copies are held to
#: (REQ_PLATFORM_TOOLCHAIN); the release file names come from toolchain.VALE_SUFFIXES.
RELEASES = "https://github.com/errata-ai/vale/releases/download/"
HOSTS = {"github.com", "objects.githubusercontent.com", "release-assets.githubusercontent.com"}
#: The names the setup script binds once, at top level, to a literal; nothing else writes them.
TABLE_NAMES = ("VALE_VERSION", "VALE_FILES", "RELEASES", "HOSTS")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
VALE_LINE = re.compile(r"^(?P<loc>.+?:\d+:\d+):(?P<check>[\w.]+):(?P<msg>.*)$")


def _written_names(node: ast.AST) -> set[str]:
    """Names a statement assigns, or changes in place through a subscript, attribute or call."""
    targets: list[ast.AST] = []
    if isinstance(node, (ast.Assign, ast.Delete)):
        targets = list(node.targets)
    elif isinstance(node, (ast.AnnAssign, ast.AugAssign, ast.For, ast.AsyncFor, ast.NamedExpr)):
        targets = [node.target]
    elif isinstance(node, (ast.With, ast.AsyncWith)):
        targets = [i.optional_vars for i in node.items if i.optional_vars]
    elif isinstance(node, (ast.Global, ast.Nonlocal)):
        return set(node.names)
    elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        targets = [node.func.value]
    return {sub.id for t in targets for sub in ast.walk(t) if isinstance(sub, ast.Name)}


def _vale_table(source: str) -> tuple[dict, list[str]]:
    """The setup script's table names, read as literals and never run, and what is wrong."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError) as exc:
        return {}, [f"does not parse: {exc}"]
    values, problems = {}, []
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, value = node.targets[0], node.value
        elif isinstance(node, ast.AnnAssign):
            target, value = node.target, node.value
        else:
            continue
        if value is not None and isinstance(target, ast.Name) and target.id in TABLE_NAMES:
            try:
                values[target.id] = ast.literal_eval(value)
            except Exception:  # literal_eval raises several types on non-literals
                problems.append(f"{target.id} is not a literal")
    writes: dict[str, int] = {}
    for node in ast.walk(tree):
        for name in _written_names(node) & set(TABLE_NAMES):
            writes[name] = writes.get(name, 0) + 1
    for name in TABLE_NAMES:
        if writes.get(name, 0) != 1:
            problems.append(f"{name} must be bound once, at top level, and never changed")
    return values, problems


def check_vale_table(root: Path, files: list[str]) -> list[Finding]:
    where = "tools/setup.py"
    values, problems = _vale_table((root / where).read_text(encoding="utf-8"))
    findings = [Finding("REQ_PLATFORM_TOOLCHAIN", where, p) for p in problems]
    version, table = values.get("VALE_VERSION"), values.get("VALE_FILES")
    if values.get("RELEASES") != RELEASES:
        findings.append(Finding("REQ_PLATFORM_TOOLCHAIN", where, f"RELEASES must be {RELEASES!r}"))
    if values.get("HOSTS") != HOSTS:
        findings.append(Finding("REQ_PLATFORM_TOOLCHAIN", where, f"HOSTS must be {sorted(HOSTS)}"))
    if not (isinstance(version, str) and re.fullmatch(r"\d+\.\d+\.\d+", version)
            and isinstance(table, dict)):
        findings.append(Finding("REQ_PLATFORM_TOOLCHAIN", where,
                                "VALE_VERSION must be a version and VALE_FILES a table"))
        table = {}
    for key, suffix in VALE_SUFFIXES.items() if table else ():
        row = table.get(key)
        if not (isinstance(row, tuple) and len(row) == 3):
            findings.append(Finding("REQ_PLATFORM_TOOLCHAIN", where,
                                    f"no (file, sha256, size) row for {key}"))
            continue
        name, sha256, size = row
        if name != f"vale_{version}_{suffix}":
            findings.append(Finding("REQ_PLATFORM_TOOLCHAIN", where,
                                    f"{key}: file {name!r} is not vale_{version}_{suffix}"))
        if not (isinstance(sha256, str) and SHA256.match(sha256)):
            findings.append(Finding("REQ_PLATFORM_TOOLCHAIN", where,
                                    f"{key}: hash is not 64 lowercase hexadecimal digits"))
        if not (type(size) is int and size > 0):
            findings.append(Finding("REQ_PLATFORM_TOOLCHAIN", where,
                                    f"{key}: size is not a positive number of bytes"))
    for key in sorted(map(str, set(table) - set(VALE_SUFFIXES))):
        findings.append(Finding("REQ_PLATFORM_TOOLCHAIN", where, f"unknown platform {key!r}"))
    for name in files:
        # Case-blind, since Windows and macOS put Bin/ and bin/ in one place.
        if name.lower().startswith("bin/"):
            findings.append(Finding("REQ_PLATFORM_TOOLCHAIN", name,
                                    "bin/ holds only what setup writes; nothing there is tracked"))
    return findings


def check_toolchain(root: Path) -> list[Finding]:
    findings = []
    lock = root / "requirements.lock"
    for n, line in enumerate(lock.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if line and not line.startswith("#") and not LOCK_LINE.match(line):
            findings.append(Finding(
                "REQ_PINNED_TOOLCHAIN", f"requirements.lock:{n}", f"not an exact pin with --hash: {line[:80]}",
            ))
    return findings


#: The one line the root .gitattributes holds, byte for byte (REQ_ONE_LINE_ENDING).
GITATTRIBUTES = b"* text=auto eol=lf\n"


def repo_files(root: Path) -> tuple[list[str], list[Finding]]:
    """Every file git tracks or would track: committed, or untracked and not ignored."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            capture_output=True, encoding="utf-8", errors="replace", check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        return [], [Finding("REQ_WARNINGS_FATAL", "(git)",
                            f"cannot list the repository's files with git: {exc}")]
    return sorted({name for name in proc.stdout.split("\0") if name}), []


def check_line_endings(root: Path, files: list[str]) -> list[Finding]:
    findings = []
    path = root / ".gitattributes"
    if not path.is_file():
        findings.append(Finding(
            "REQ_ONE_LINE_ENDING", ".gitattributes", f"missing; it holds exactly {GITATTRIBUTES!r}",
        ))
    elif path.read_bytes() != GITATTRIBUTES:
        findings.append(Finding(
            "REQ_ONE_LINE_ENDING", ".gitattributes", f"must hold exactly {GITATTRIBUTES!r}",
        ))
    for name in files:
        # Case-blind, since git on Windows and macOS reads .GitAttributes too.
        if name != ".gitattributes" and Path(name).name.lower() == ".gitattributes":
            findings.append(Finding(
                "REQ_ONE_LINE_ENDING", name, "the root .gitattributes is the only one",
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
        capture_output=True, encoding="utf-8", errors="replace", env=CHILD_ENV,
    )
    findings = from_sphinx(proc.stderr, root)
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
            capture_output=True, encoding="utf-8", errors="replace", cwd=root,
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
        loc = relative_location(m.group("loc"), root)
        msg = m.group("msg").split(": ", 1)[-1] if req else m.group("msg")
        findings.append(Finding(req.group(0) if req else "REQ_WARNINGS_FATAL", loc, msg))
    return findings


def check_portable(findings: list[Finding]) -> list[Finding]:
    """The last stage: report every location no stage could map (REQ_PORTABLE_FINDINGS)."""
    return [
        Finding("REQ_PORTABLE_FINDINGS", "(location)",
                f"{f.req} is located at {f.location!r}, not a repository-relative path")
        for f in findings if unportable(f.location)
    ]


def audit_fixtures(needs: dict[str, dict], fixtures: Path) -> list[Finding]:
    expected = set()
    for path in sorted(fixtures.glob("*.yaml")):
        expected.add((yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("expect"))
    # A requirement is enforced once a component of an implemented design satisfies it;
    # before that it is planned, and its fixture arrives with the build.
    def enforced(req: dict) -> bool:
        return any(needs.get(c, {}).get("doc_status") == "implemented"
                   for c in req.get("satisfies_back") or [])

    return [
        Finding("REQ_FIXTURE_PER_INVARIANT", f"{fixtures.name}/",
                f"no negative fixture expects {need['id']}")
        for need in needs.values()
        if need["type"] == "req" and enforced(need) and need["id"] not in expected
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--base", help="git ref to check MADR immutability against")
    parser.add_argument("--vale", type=Path, default=None)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    vale = (args.vale or vale_path(root)).resolve()

    files, findings = repo_files(root)
    findings += check_toolchain(root)
    findings += check_vale_table(root, files)
    findings += check_line_endings(root, files)
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

    findings += check_portable(findings)
    for finding in sorted(set(findings)):
        print(finding.line())
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
