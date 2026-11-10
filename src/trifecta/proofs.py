"""Test proofs (COMP_TEST_PROOFS): read every declaration under ``tests/`` from the source,
run the proof modules in a child process, and judge each declaration by its test's result.

``check_proofs`` returns the findings, the requirements a counted declaration proves, and
the declarations counted without running, which the check lists on standard error.
"""

from __future__ import annotations

import ast
import json
import keyword
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from fnmatch import fnmatchcase
from pathlib import Path

from .findings import Finding

REQ = "REQ_PROVEN_BY_TEST"
DECORATORS = ("proves", "only_on")
SYSTEMS = ("posix", "nt")
#: ``RUNNER_OS`` -> the ``os.name`` a CI job on that runner has.
RUNNER_OS = {"Linux": "posix", "Windows": "nt"}
ASYNC_BASE = "IsolatedAsyncioTestCase"

#: Starts the child: the running package first on the path, then the corpus root.
BOOT = ("import sys; sys.path[:0] = [sys.argv[1], '']; "
        "from trifecta.proof_child import main; sys.exit(main(sys.argv[2:]))")


@dataclass
class Method:
    """A declared or system-valued test method, as the source defines it."""
    module: str
    cls: str
    name: str
    where: str
    requirements: list[str] = field(default_factory=list)
    system: str | None = None
    runs: bool = False

    @property
    def key(self) -> str:
        return f"{self.module}:{self.cls}.{self.name}"


@dataclass
class Reading:
    findings: list[Finding] = field(default_factory=list)
    methods: dict[str, Method] = field(default_factory=dict)
    #: (module, class qualified name) of every class statement in a proof module that runs.
    classes: set[tuple[str, str]] = field(default_factory=set)
    #: Proof modules the child runs, by dotted name.
    modules: list[str] = field(default_factory=list)


def _module_name(rel: str) -> str | None:
    """The dotted module name of a file the check runs, or None."""
    parts = rel.removesuffix(".py").split("/")
    if not fnmatchcase(parts[-1] + ".py", "test*.py"):
        return None
    if not all(p.isidentifier() and not keyword.iskeyword(p) for p in parts):
        return None
    return ".".join(parts)


def _refers_to_testing(node: ast.AST) -> bool:
    """Whether an expression names ``trifecta.testing`` as an attribute chain."""
    for sub in ast.walk(node):
        if (isinstance(sub, ast.Attribute) and sub.attr == "testing"
                and isinstance(sub.value, ast.Name) and sub.value.id == "trifecta"):
            return True
    return False


def _own_yield(func: ast.AST) -> bool:
    """Whether a function's own body, outside nested scopes, holds a yield."""
    stack = list(ast.iter_child_nodes(func))
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.Yield, ast.YieldFrom)):
            return True
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            continue
        stack.extend(ast.iter_child_nodes(node))
    return False


def _bound_names(node: ast.AST) -> list[tuple[str, int]]:
    """Every name a statement binds in its own scope, with its line."""
    out = []
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name) and isinstance(sub.ctx, (ast.Store, ast.Del)):
            out.append((sub.id, sub.lineno))
        elif isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.append((sub.name, sub.lineno))
        elif isinstance(sub, (ast.Import, ast.ImportFrom)):
            for alias in sub.names:
                out.append(((alias.asname or alias.name).split(".")[0], sub.lineno))
    return out


class _Reader:
    """Reads one file's declarations and system values."""

    def __init__(self, rel: str, tree: ast.Module, module: str | None):
        self.rel, self.tree, self.module = rel, tree, module
        self.findings: list[Finding] = []
        self.methods: list[Method] = []
        self.classes: list[str] = []
        self.bound: set[str] = set()
        self.marked = False

    def report(self, line: int, message: str) -> None:
        self.findings.append(Finding(REQ, f"{self.rel}:{line}", message))

    def read(self) -> None:
        self._imports()
        self._rebindings()
        self._scope(self.tree.body, owner=None, qual="")
        self._stray_decorators()

    def _imports(self) -> None:
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ImportFrom) and node.level == 0:
                if node.module == "trifecta.testing":
                    self.marked = True
                    for alias in node.names:
                        if alias.name in DECORATORS and alias.asname is None:
                            self.bound.add(alias.name)
                        else:
                            self.report(node.lineno, f"imports {alias.name}"
                                        f"{' as ' + alias.asname if alias.asname else ''} from "
                                        f"trifecta.testing; only the bare names proves and "
                                        f"only_on are read")
                elif node.module == "trifecta" and any(a.name == "testing" for a in node.names):
                    self.marked = True
                    self.report(node.lineno, "imports trifecta.testing as a module; write "
                                "from trifecta.testing import proves, only_on")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "trifecta.testing" or alias.name.startswith("trifecta.testing."):
                        self.marked = True
                        self.report(node.lineno, "imports trifecta.testing as a module; write "
                                    "from trifecta.testing import proves, only_on")

    def _rebindings(self) -> None:
        if not self.bound:
            return
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names = [node.name]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 \
                    and node.module == "trifecta.testing":
                continue
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [(a.asname or a.name).split(".")[0] for a in node.names]
            elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
                names = [node.id]
            elif isinstance(node, ast.arg):
                names = [node.arg]
            else:
                continue
            for name in names:
                if name in self.bound:
                    self.report(getattr(node, "lineno", 1), f"{name} is bound again; it names "
                                "only the decorator imported from trifecta.testing")

    def _decorator_kind(self, dec: ast.expr) -> str | None:
        """'proves' or 'only_on' for a decorator the check reads; None otherwise."""
        if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name) \
                and dec.func.id in self.bound:
            return dec.func.id
        return None

    def _args(self, dec: ast.Call, kind: str) -> list[str] | None:
        if dec.keywords or not dec.args or not all(
                isinstance(a, ast.Constant) and isinstance(a.value, str) for a in dec.args):
            self.report(dec.lineno, f"{kind} takes only string literals as its arguments")
            return None
        return [a.value for a in dec.args]

    def _scope(self, body: list[ast.stmt], owner: ast.ClassDef | None, qual: str) -> None:
        """Read the classes and methods of one scope: the module or a class body."""
        defined: dict[str, int] = {}
        for node in body:
            if isinstance(node, ast.ClassDef):
                name = f"{qual}{node.name}"
                if name in defined:
                    self.report(node.lineno, f"class {name} is defined more than once")
                defined[name] = node.lineno
                self.classes.append(name)
                for dec in node.decorator_list:
                    if (kind := self._decorator_kind(dec)) is not None:
                        self.marked = True
                        self.report(dec.lineno, "a system value on a class; put it on each "
                                    "method" if kind == "only_on" else
                                    "a declaration on a class; put it on each method")
                self._scope(node.body, node, f"{name}.")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if owner is None:
                    self._misplaced(node)
                    continue
                if node.name in defined:
                    self.report(node.lineno, f"{qual}{node.name} is defined more than once")
                defined[node.name] = node.lineno
                self._method(node, owner, qual.rstrip("."))
            else:
                for name, line in _bound_names(node):
                    if name in defined or (owner is None and f"{qual}{name}" in defined):
                        self.report(line, f"{qual}{name} is bound again after its definition")

    def _misplaced(self, func: ast.AST) -> None:
        for sub in ast.walk(func):
            if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                for dec in sub.decorator_list:
                    if self._decorator_kind(dec) is not None:
                        self.marked = True
                        self.report(dec.lineno, "a declaration or system value sits only on a "
                                    "method defined in a class body")

    def _method(self, func: ast.FunctionDef | ast.AsyncFunctionDef, cls: ast.ClassDef,
                qual: str) -> None:
        requirements: list[str] = []
        systems: list[str] = []
        for dec in func.decorator_list:
            kind = self._decorator_kind(dec)
            if kind is None:
                continue
            self.marked = True
            args = self._args(dec, kind)
            if args is None:
                continue
            if kind == "proves":
                if requirements:
                    self.report(dec.lineno, f"{qual}.{func.name} declares more than once")
                requirements += args
            else:
                systems.append(args[0] if len(args) == 1 else repr(args))
                if len(args) != 1 or args[0] not in SYSTEMS:
                    self.report(dec.lineno, f"system value {args!r} is not exactly 'posix' "
                                "or 'nt'")
        if len(systems) > 1:
            self.report(func.lineno, f"{qual}.{func.name} has more than one system value")
        for inner in ast.walk(func):
            if inner is not func and isinstance(
                    inner, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                for dec in inner.decorator_list:
                    if self._decorator_kind(dec) is not None:
                        self.marked = True
                        self.report(dec.lineno, "a declaration or system value sits only on "
                                    "a method defined in a class body")
        if not requirements and not systems:
            return
        if isinstance(func, ast.AsyncFunctionDef) and not self._async_capable(cls):
            self.report(func.lineno, f"{qual}.{func.name} is async in a class that is not an "
                        f"{ASYNC_BASE}, so its body never runs")
        if _own_yield(func):
            self.report(func.lineno, f"{qual}.{func.name} yields, so its body never runs")
        system = systems[0] if len(systems) == 1 and systems[0] in SYSTEMS else None
        self.methods.append(Method(self.module or self.rel, qual, func.name,
                                   f"{self.rel}:{func.lineno}", requirements, system,
                                   runs=self.module is not None))

    def _async_capable(self, cls: ast.ClassDef, seen: frozenset = frozenset()) -> bool:
        local = {n.name: n for n in self.tree.body if isinstance(n, ast.ClassDef)}
        for base in cls.bases:
            name = base.attr if isinstance(base, ast.Attribute) else getattr(base, "id", None)
            if name == ASYNC_BASE:
                return True
            if name in local and name not in seen and \
                    self._async_capable(local[name], seen | {cls.name}):
                return True
        return False

    def _stray_decorators(self) -> None:
        """Decorator calls that look like a declaration but are not one the check reads."""
        for node in ast.walk(self.tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            for dec in node.decorator_list:
                if self._decorator_kind(dec) is not None:
                    continue
                func = dec.func if isinstance(dec, ast.Call) else dec
                tail = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
                if tail in DECORATORS or _refers_to_testing(dec):
                    self.marked = True
                    self.report(dec.lineno, f"decorator {ast.unparse(dec)[:60]} is not one the "
                                "check reads: write @proves(...) or @only_on(...) with the bare "
                                "names imported from trifecta.testing")


def read_tests(root: Path) -> Reading:
    """Read every ``.py`` file under ``tests/`` as source, never importing it."""
    reading = Reading()
    tests = root / "tests"
    if not tests.is_dir():
        return reading
    files = sorted(p for p in tests.rglob("*") if p.name.endswith(".py") and p.is_file())
    for path in files:
        rel = path.relative_to(root).as_posix()
        data = path.read_bytes()
        try:
            tree = ast.parse(data.decode("utf-8"), filename=rel)
        except (SyntaxError, ValueError, UnicodeDecodeError) as exc:
            if b"proves" in data or b"only_on" in data or b"trifecta.testing" in data:
                reading.findings.append(Finding(REQ, rel, f"cannot be read as Python source: {exc}"))
            continue
        module = _module_name(rel)
        reader = _Reader(rel, tree, module)
        reader.read()
        reading.findings += reader.findings
        if not reader.marked:
            continue
        for directory in path.parent.relative_to(root).parents[::-1][1:] + (path.parent.relative_to(root),):
            if not (root / directory / "__init__.py").is_file():
                reading.findings.append(Finding(
                    REQ, directory.as_posix() + "/", "a directory holding a proof module is a "
                    "package: add __init__.py"))
        for method in reader.methods:
            reading.methods[method.key] = method
        if module:
            reading.modules.append(module)
            reading.classes |= {(module, c) for c in reader.classes}
    reading.findings = sorted(set(reading.findings))
    return reading


# --- the run -----------------------------------------------------------------------------

#: Every field a record of each kind holds, and its type.
RECORDS = {
    "os": {"when": str, "os_name": str},
    "module_error": {"module": str, "detail": str},
    "collected": {"module": str, "cls": str, "name": str, "defined_module": str,
                  "defined_cls": str},
    "result": {"module": str, "cls": str, "name": str, "outcome": str, "detail": str,
               "returned": (str, type(None))},
    "fixture": {"scope": str, "target": str, "outcome": str, "detail": str},
    "end": {},
}
OUTCOMES = {"success", "failure", "error", "skip", "expected_failure", "unexpected_success"}


def _parse(lines: list[str]) -> tuple[list[dict], list[str]]:
    records, problems = [], []
    for n, line in enumerate(lines, 1):
        try:
            record = json.loads(line)
        except ValueError:
            problems.append(f"record {n} is not JSON")
            continue
        kind = record.get("kind") if isinstance(record, dict) else None
        shape = RECORDS.get(kind)
        if shape is None or set(record) != {"kind", *shape} or not all(
                isinstance(record[k], t) for k, t in shape.items()):
            problems.append(f"record {n} is not one the check knows: {line[:80]}")
            continue
        if kind in ("result", "fixture") and record["outcome"] not in OUTCOMES:
            problems.append(f"record {n} has an unknown outcome {record['outcome']!r}")
            continue
        records.append(record)
    return records, problems


def run_child(root: Path, modules: list[str], leave_out: list[str],
              child: list[str] | None = None) -> tuple[list[str], str]:
    """Run the proof modules; return the channel's lines and the child's own output."""
    package_parent = str(Path(__file__).resolve().parent.parent)
    with tempfile.TemporaryDirectory() as tmp:
        channel = Path(tmp) / "records.jsonl"
        command = child or [sys.executable, "-E", "-X", "utf8", "-c", BOOT, package_parent]
        proc = subprocess.run(
            [*command, str(channel), json.dumps(modules), json.dumps(leave_out)],
            cwd=root, capture_output=True, encoding="utf-8", errors="replace",
            stdin=subprocess.DEVNULL,
        )
        text = channel.read_text(encoding="utf-8", errors="replace") if channel.is_file() else ""
    return text.splitlines(), (proc.stdout + proc.stderr)[-500:]


def check_proofs(root: Path, child: list[str] | None = None,
                 ) -> tuple[list[Finding], set[str], list[str]]:
    """Findings, the requirements proven, and the declarations counted without running."""
    reading = read_tests(root)
    findings = list(reading.findings)
    if not reading.modules and not reading.methods:
        return findings, set(), []
    os_name = os.name
    runner = os.environ.get("RUNNER_OS")
    if runner in RUNNER_OS and RUNNER_OS[runner] != os_name:
        findings.append(Finding(REQ, "tests/", f"RUNNER_OS is {runner} but os.name is "
                                f"{os_name!r}, not {RUNNER_OS[runner]!r}"))

    def other(m: Method) -> bool:
        return m.system is not None and m.system != os_name

    proven: set[str] = set()
    unrun: list[str] = []
    for m in reading.methods.values():
        if other(m):
            proven.update(m.requirements)
            if m.requirements:
                unrun.append(f"{m.where} {m.cls}.{m.name}: {', '.join(m.requirements)} "
                             f"(runs where os.name is {m.system!r})")
        elif not m.runs:
            findings.append(Finding(REQ, m.where, f"{m.cls}.{m.name} is in a file the check "
                                    "does not run, so it has no result"))
    if not reading.modules:
        return sorted(set(findings)), proven, unrun

    leave_out = sorted(m.key for m in reading.methods.values() if m.runs and other(m))
    lines, output = run_child(root, reading.modules, leave_out, child)
    records, problems = _parse(lines)
    findings += [Finding(REQ, "tests/", p) for p in problems]
    findings += _judge(reading, records, os_name, output, other, proven)
    return sorted(set(findings)), proven, unrun


def _judge(reading: Reading, records: list[dict], os_name: str, output: str,
           other, proven: set[str]) -> list[Finding]:
    findings: list[Finding] = []
    seen_os = {r["when"]: r["os_name"] for r in records if r["kind"] == "os"}
    for when in ("before", "after"):
        if when not in seen_os:
            findings.append(Finding(REQ, "tests/", f"the child reported no os.name {when} the "
                                    "run"))
        elif seen_os[when] != os_name:
            findings.append(Finding(REQ, "tests/", f"the child's os.name {when} the run is "
                                    f"{seen_os[when]!r}, not {os_name!r}"))
    if not any(r["kind"] == "end" for r in records):
        findings.append(Finding(REQ, "tests/", "the child ended before it reported every "
                                f"result: {' '.join(output.split())[-300:]}"))
    for r in records:
        if r["kind"] == "module_error":
            findings.append(Finding(REQ, "tests/", f"{r['module']} raised on import: "
                                    f"{r['detail']}"))
    collected = {(r["module"], r["cls"], r["name"]) for r in records if r["kind"] == "collected"}
    results: dict[tuple[str, str, str], list[dict]] = {}
    for r in records:
        if r["kind"] != "result":
            continue
        target = (r["module"], r["cls"], r["name"])
        if (r["module"], r["cls"]) not in reading.classes:
            findings.append(Finding(REQ, "tests/", f"a result for {r['module']}.{r['cls']}, "
                                    "a class the check did not read"))
            continue
        results.setdefault(target, []).append(r)
    by_key = {(m.module, m.cls, m.name): m for m in reading.methods.values() if m.runs}
    for r in records:
        if r["kind"] != "collected":
            continue
        defined = by_key.get((r["defined_module"], r["defined_cls"], r["name"]))
        if defined and (defined.module, defined.cls) != (r["module"], r["cls"]):
            findings.append(Finding(REQ, defined.where, f"{defined.cls}.{defined.name} is "
                                    f"collected under {r['cls']}, not the class that defines it"))
    holders = {(m.module, m.cls) for m in by_key.values() if not other(m)}
    holder_modules = {m for m, _ in holders}
    for r in records:
        if r["kind"] != "fixture" or r["outcome"] == "success":
            continue
        module, _, cls = r["target"].partition(":")
        judged = (module, cls) in holders if r["scope"] == "class" else module in holder_modules
        if judged:
            findings.append(Finding(REQ, "tests/", f"{r['scope']} set-up or tear-down of "
                                    f"{r['target']}: {r['outcome']}: {r['detail']}"))
    for key, m in by_key.items():
        if other(m):
            continue
        got = results.get(key, [])
        problem = None
        if not got:
            problem = ("has no result" + ("" if key in collected else
                                          ": the child did not collect it as a test"))
        elif len(got) > 1:
            problem = f"has {len(got)} results, not one"
        elif got[0]["outcome"] != "success":
            problem = f"{got[0]['outcome']}: {got[0]['detail']}"
        elif got[0]["returned"] is not None:
            problem = f"returned {got[0]['returned']}, so its body may never have run"
        if problem:
            findings.append(Finding(REQ, m.where, f"{m.cls}.{m.name} {problem}"[:400]))
        else:
            proven.update(m.requirements)
    return findings
