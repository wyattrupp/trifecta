"""The pipeline (COMP_PIPELINE): every stage, in a fixed order, emitting IF_FINDING lines."""

from __future__ import annotations

import argparse
import ast
import json
import re
import shutil
import subprocess
import sys
import urllib.parse
from pathlib import Path

import yaml

from . import PROJECT
from .check_graph import check as check_graph, load_needs
from .check_lifecycle import check as check_lifecycle
from .ext import DOC_TYPES
from .findings import CHILD_ENV, Finding, from_sphinx, relative_location, unportable
from .gen_vale import generate
from .proofs import check_proofs
from .toolchain import PACKAGE_DIR, VALE_SUFFIXES, corpus_root, vale_path

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


def _package_location(path: Path, root: Path) -> str:
    """A package file's location: repository-relative when the package is this source tree."""
    if path.is_relative_to(root):
        return path.relative_to(root).as_posix()
    return f"trifecta/{path.relative_to(PACKAGE_DIR).as_posix()}"


def check_vale_table(root: Path, files: list[str]) -> list[Finding]:
    # The table the running package's setup reads (plan 0003 step 2.3).
    table_file = PACKAGE_DIR / "setup.py"
    where = _package_location(table_file, root)
    values, problems = _vale_table(table_file.read_text(encoding="utf-8"))
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


#: The package's own lock line (REQ_ONE_PACKAGE): a release URL, then its hashes.
PACKAGE_LINE = re.compile(r"^trifecta @ (?P<url>\S+)(?: --hash=sha256:[0-9a-f]{64})+$")
#: A release version, as the tag and the wheel's file name both carry it.
VERSION = r"[0-9]+(?:\.[0-9]+)*(?:(?:a|b|rc)[0-9]+)?(?:\.post[0-9]+)?(?:\.dev[0-9]+)?"
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*")


def package_url_problem(url: str) -> str | None:
    """Why ``url`` is not one of the package's own release wheels, or None."""
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https":
        return "the URL is not https"
    if parts.netloc != "github.com":
        return "the URL's host is not github.com"
    if parts.query or parts.fragment:
        return "the URL carries a query or a fragment"
    segments = parts.path.split("/")
    owner, repo = PROJECT
    if len(segments) != 7 or segments[:5] != ["", owner, repo, "releases", "download"]:
        return f"the URL is not under /{owner}/{repo}/releases/download/"
    tag, wheel = segments[5], segments[6]
    if not (m := re.fullmatch(f"v({VERSION})", tag)):
        return f"the release tag {tag!r} is not v<version>"
    if not re.fullmatch(rf"trifecta-{re.escape(m.group(1))}-[A-Za-z0-9_.]+-[A-Za-z0-9_.]+-[A-Za-z0-9_.]+\.whl", wheel):
        return f"{wheel!r} is not the release's trifecta wheel"
    return None


#: A lock may include one other lock in the repository, as this one includes the package's.
INCLUDE = re.compile(r"^-r (?P<path>[A-Za-z0-9_./-]+\.lock)$")


def check_toolchain(root: Path, name: str = "requirements.lock",
                    seen: frozenset[str] = frozenset()) -> list[Finding]:
    findings = []
    lock = root / name
    for n, line in enumerate(lock.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        where = f"{name}:{n}"
        if include := INCLUDE.match(line):
            target = (lock.parent / include.group("path")).resolve()
            rel = target.relative_to(root).as_posix() if target.is_relative_to(root) else None
            if rel is None or not target.is_file() or rel in seen | {name}:
                findings.append(Finding("REQ_PINNED_TOOLCHAIN", where,
                                        f"includes a lock that is not another file here: {line}"))
            else:
                findings += check_toolchain(root, rel, seen | {name})
            continue
        name = NAME.match(line)
        if name and re.sub(r"[-_.]+", "-", name.group(0)).lower() == "trifecta":
            m = PACKAGE_LINE.match(line)
            problem = (package_url_problem(m.group("url")) if m else
                       "not the form trifecta @ <release wheel URL> --hash=sha256:<hash>")
            if problem:
                findings.append(Finding("REQ_ONE_PACKAGE", where, f"{problem}: {line[:80]}"))
        elif not LOCK_LINE.match(line):
            findings.append(Finding(
                "REQ_PINNED_TOOLCHAIN", where, f"not an exact pin with --hash: {line[:80]}",
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


def stage_vale(root: Path) -> Path:
    """The Vale configurations and the package's styles, copied beside the generated ones
    under the build directory, so the package's own files are only read."""
    stage = root / "docs" / "_build" / "vale"
    shutil.rmtree(stage, ignore_errors=True)
    shutil.copytree(PACKAGE_DIR / "vale", stage / "vale")
    shutil.copytree(PACKAGE_DIR / "styles", stage / "styles")
    return stage


def check_vale_version(vale: Path) -> list[Finding]:
    """The Vale the check runs is the version the package's table pins."""
    values, _ = _vale_table((PACKAGE_DIR / "setup.py").read_text(encoding="utf-8"))
    version = values.get("VALE_VERSION")
    try:
        out = subprocess.run([str(vale), "--version"], capture_output=True, encoding="utf-8",
                             errors="replace").stdout
    except OSError as exc:
        return [Finding("REQ_PLATFORM_TOOLCHAIN", "bin/", f"cannot run {vale.name}: {exc}")]
    if not (isinstance(version, str)
            and re.search(rf"(?<![\w.]){re.escape(version)}(?![\w.])", out)):
        return [Finding("REQ_PLATFORM_TOOLCHAIN", "bin/",
                        f"{vale.name} reports {out.strip()[:60]!r}, not the pinned {version}")]
    return []


def run_vale(root: Path, vale: Path, config: str) -> list[Finding]:
    html = root / "docs" / "_build" / "lint"
    where = _package_location(PACKAGE_DIR / "vale" / config, root)
    targets = [str(html / d) for d in TYPED_DIRS if (html / d).is_dir()]
    if not targets:
        return [Finding("REQ_WARNINGS_FATAL", where, "no typed pages were built to lint")]
    config_file = root / "docs" / "_build" / "vale" / "vale" / config
    try:
        proc = subprocess.run(
            [str(vale), f"--config={config_file}", "--output=line",
             "--no-exit", *targets],
            capture_output=True, encoding="utf-8", errors="replace", cwd=root,
        )
    except OSError as exc:
        return [Finding("REQ_WARNINGS_FATAL", where, f"cannot run {vale}: {exc}")]
    findings = []
    if proc.stderr.strip():
        findings.append(Finding("REQ_WARNINGS_FATAL", where, proc.stderr.strip()[:500]))
    elif proc.returncode != 0:
        # With --no-exit Vale exits non-zero only when it fails to run, which can be silent.
        findings.append(Finding("REQ_WARNINGS_FATAL", where,
                                f"vale exited {proc.returncode} with no message"))
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


#: The document-level need types: a corpus with none of them has no typed document.
DOC_LEVEL = ("rfc", "decision", "design", "plan")


def fixture_audit_on(root: Path) -> bool:
    """Whether the corpus's configuration turned the fixture audit on, as the build
    recorded it (COMP_SELF_TEST_SCOPE); off when the record is missing or unreadable."""
    try:
        record = json.loads((root / "docs" / "_build" / "html" / "trifecta.json")
                            .read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return isinstance(record, dict) and record.get("fixture_audit") is True


def audit_fixtures(needs: dict[str, dict], fixtures: Path, proven: set[str]) -> list[Finding]:
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
                f"no negative fixture expects {need['id']} and no counted test proves it")
        for need in needs.values()
        if need["type"] == "req" and enforced(need)
        and need["id"] not in expected and need["id"] not in proven
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", help="git ref to check MADR immutability against")
    args = parser.parse_args(argv)
    root = corpus_root()
    vale = vale_path(root).resolve()

    files, findings = repo_files(root)
    findings += check_toolchain(root)
    findings += check_vale_table(root, files)
    findings += check_line_endings(root, files)
    proof_findings, proven, unrun = check_proofs(root)
    findings += proof_findings
    findings += run_sphinx(root)
    needs_json = root / "docs" / "_build" / "html" / "needs.json"
    if needs_json.is_file():
        needs = load_needs(needs_json)
        findings += check_graph(needs, root)
        stage = stage_vale(root)
        findings += generate(needs, stage / "styles" / "TrifectaGenerated")
        findings = [_locate(f, needs) for f in findings]
        if any(n["type"] in DOC_LEVEL for n in needs.values()):
            # A corpus with no typed document has nothing to lint (plan 0003 step 4.2).
            build_lint_view(root)
            findings += check_vale_version(vale)
            findings += run_vale(root, vale, "normative.ini")
            findings += run_vale(root, vale, "prose.ini")
        if fixture_audit_on(root):
            findings += audit_fixtures(needs, root / "tests" / "fixtures", proven)
    else:
        findings.append(Finding(
            "REQ_WARNINGS_FATAL", "docs/_build/html/needs.json",
            "the build produced no needs.json, so graph, lint and fixture checks did not run",
        ))
    if args.base:
        findings += check_lifecycle(root, args.base)

    findings += check_portable(findings)
    for line in unrun:
        print(f"counted but not run: {line}", file=sys.stderr)
    for finding in sorted(set(findings)):
        print(finding.line())
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
