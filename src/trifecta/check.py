"""The pipeline (COMP_PIPELINE): every stage, in a fixed order, emitting IF_FINDING lines."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.parse
from pathlib import Path

import yaml

from . import PROJECT
from .build import run_build
from .check_graph import check as check_graph, load_needs
from .check_lifecycle import check as check_lifecycle
from .ext import DOC_TYPES
from .ext.ontology import DOC_LEVEL
from .findings import CHILD_ENV, Finding, from_sphinx, relative_location, unportable
from .gen_vale import generate
from .profiler import DIRECTORY as PROFILE_DIR, Profiler, target as profile_target
from .profiler import write as write_profile
from .proofs import check_proofs
from .store import DEFAULT as STORE_DIR, location as store_location
from .toolchain import PACKAGE_DIR, VALE_SUFFIXES, OutsideRepository, corpus_root, vale_path

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
    if re.search(r"\s", url):
        return "the URL holds white space"
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
        pin = NAME.match(line)
        if pin and re.sub(r"[-_.]+", "-", pin.group(0)).lower() == "trifecta":
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


#: Directories under ``docs/_build`` the clean before the build keeps: no build writes them.
KEPT = {PROFILE_DIR.name, STORE_DIR.name}


def _real_dir(path: Path) -> bool:
    """A directory that is neither a symbolic link nor a Windows junction."""
    return path.is_dir() and not path.is_symlink() and not os.path.isjunction(path)


def clean_build(root: Path) -> None:
    """Empty ``docs/_build`` but the directories in KEPT, and leave it in place: the build
    sees the same tree whether a run before it left one or not (COMP_BUILD_REUSE)."""
    build = root / "docs" / "_build"
    if not _real_dir(build):
        # A link or a junction is removed, never followed; rmtree refuses either.
        shutil.rmtree(build, ignore_errors=True)
        for remove in (os.unlink, os.rmdir):
            try:
                remove(build)
            except OSError:
                pass
        try:
            build.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        return
    for entry in build.iterdir():
        if entry.name in KEPT and _real_dir(entry):
            continue
        if _real_dir(entry):
            shutil.rmtree(entry, ignore_errors=True)
        else:
            try:
                entry.unlink()
            except OSError:
                pass


def run_sphinx(root: Path, fresh: bool = False,
               stage: dict | None = None) -> list[Finding]:
    """The build's findings, from a fresh build or a stored one (COMP_BUILD_REUSE); when
    ``stage`` is given, whether it was reused and why not."""
    # --no-color: Sphinx forces ANSI colour when CI=true or on Windows, even into a pipe,
    # and the escape codes break the line-anchored patterns in findings.py.
    # A clean output directory: stale pages of deleted documents would otherwise be linted.
    # What the build never writes is kept: the profiles and the store beside it (DEC_0029).
    clean_build(root)
    returncode, stderr, reused, why = run_build(root, fresh)
    if stage is not None:
        stage.update(reused=reused, why=why)
    findings = from_sphinx(stderr, root)
    if returncode != 0 and not findings:
        findings.append(Finding("REQ_WARNINGS_FATAL", "(build)", stderr.strip()[-500:]))
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
            # --no-global: no configuration outside the build directory is searched, the
            # form the recorder lets Vale through in (COMP_KNOWN_PROGRAMS).
            [str(vale), f"--config={config_file}", "--no-global", "--output=line",
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


def fixture_audit_on(root: Path) -> bool:
    """Whether the corpus's configuration turned the fixture audit on, as the build
    recorded it (COMP_SELF_TEST_SCOPE); off when the record is missing or unreadable."""
    try:
        record = json.loads((root / "docs" / "_build" / "html" / "trifecta.json")
                            .read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return isinstance(record, dict) and record.get("fixture_audit") is True


def audit_stage(root: Path, needs: dict[str, dict], proven: set[str]) -> list[Finding]:
    """The fixture audit, where the corpus's configuration turns it on and nowhere else."""
    if not fixture_audit_on(root):
        return []
    return audit_fixtures(needs, root / "tests" / "fixtures", proven)


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
    parser.add_argument("--profile", type=Path, help="where to write the profile "
                        f"(default {PROFILE_DIR.as_posix()}/check.json)")
    parser.add_argument("--fresh", action="store_true",
                        help="run every stage and reuse no stored result")
    # The fixture runner's (COMP_FIXTURE_RUNNER): the control keeps what its test modules
    # reported, and a copy whose mutation leaves the tests and the package alone takes it.
    parser.add_argument("--tests-to", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--tests-from", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    root = corpus_root()
    try:
        profile_path = profile_target(args.profile, root, "check.json")
    except OutsideRepository as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    # Each stage is timed in the order it runs (COMP_PROFILER); the profile is a file,
    # written however the run ends, and touches neither standard output nor the exit status.
    profiler = Profiler("check")
    try:
        return _run(root, args.base, profiler, args.fresh, args.tests_from, args.tests_to)
    finally:
        write_profile(profile_path, profiler.data())


def _run(root: Path, base: str | None, profiler: Profiler, fresh: bool = False,
         tests_from: Path | None = None, tests_to: Path | None = None) -> int:
    stage = profiler.stage
    vale = vale_path(root).resolve()
    with stage("files"):
        files, findings = repo_files(root)
    with stage("lock"):
        findings += check_toolchain(root)
    with stage("vale table"):
        findings += check_vale_table(root, files)
    with stage("line endings"):
        findings += check_line_endings(root, files)
    runs: list = []
    # A stored result that git tracks came with the tree, not from a run: run fresh.
    store_dir = store_location(root)
    if store_dir.is_relative_to(root):
        prefix = store_dir.relative_to(root).as_posix().casefold() + "/"
        fresh = fresh or any(f.casefold().startswith(prefix) for f in files)
    with stage("tests"):
        proof_findings, proven, unrun = check_proofs(root, fresh=fresh, runs=runs,
                                                     given=tests_from, keep=tests_to)
        findings += proof_findings
    # Each proof module, within the test stage: whether its stored records were reused.
    for r in runs:
        entry = {"name": f"tests: {r.module}", "seconds": r.seconds, "reused": r.reused,
                 "why": r.why}
        if r.unstored:  # what kept it out of the store, and what each test cost
            entry |= {"reasons": r.reasons, "tests": r.tests}
        profiler.stages.append(entry)
    with stage("sphinx") as built:
        findings += run_sphinx(root, fresh, built)
    needs_json = root / "docs" / "_build" / "html" / "needs.json"
    if needs_json.is_file():
        with stage("graph"):
            needs = load_needs(needs_json)
            findings += check_graph(needs, root)
        with stage("vale rules"):
            stage_dir = stage_vale(root)
            findings += generate(needs, stage_dir / "styles" / "TrifectaGenerated")
        with stage("need locations"):
            findings = [_locate(f, needs) for f in findings]
        if any(n["type"] in DOC_LEVEL for n in needs.values()):
            # A corpus with no typed document has nothing to lint (plan 0003 step 4.2).
            with stage("lint view"):
                build_lint_view(root)
            with stage("vale version"):
                findings += check_vale_version(vale)
            with stage("vale normative"):
                findings += run_vale(root, vale, "normative.ini")
            with stage("vale prose"):
                findings += run_vale(root, vale, "prose.ini")
        with stage("fixture audit"):
            findings += audit_stage(root, needs, proven)
    else:
        findings.append(Finding(
            "REQ_WARNINGS_FATAL", "docs/_build/html/needs.json",
            "the build produced no needs.json, so graph, lint and fixture checks did not run",
        ))
    if base:
        with stage("history"):
            findings += check_lifecycle(root, base)

    with stage("locations"):
        findings += check_portable(findings)
    for line in unrun:
        print(f"counted but not run: {line}", file=sys.stderr)
    for finding in sorted(set(findings)):
        print(finding.line())
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
