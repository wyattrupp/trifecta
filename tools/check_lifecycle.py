"""History held against a base git ref (COMP_TASK_FREEZE and REQ_IMMUTABLE_DECISIONS).

A MADR past proposed keeps its content; a task resolved at the base keeps its text, step
marks and As built entry, in its plan; a typed document's status moves only forward.
Status is read with the frontmatter's YAML loader, the one the build uses, so a key given
twice or a status-looking line elsewhere in the frontmatter cannot make two readers
disagree.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import yaml

from findings import Finding

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ext"))

import digest  # noqa: E402
import plans  # noqa: E402

DECISIONS = "docs/decisions"
PLANS = "docs/plans"
ALLOWED_FROM_ACCEPTED = {"accepted", "deprecated", "superseded"}
TERMINAL = {"rejected", "deprecated", "superseded"}

#: Per typed directory, its statuses in order; a move to a lower one is backward.
RANKS = {
    "docs/rfcs": ("draft", "review", "accepted"),
    "docs/design": ("draft", "approved", "implemented"),
    "docs/plans": ("draft", "active", "done"),
}
#: Statuses a document leaves the line by. A move into one is outside the forward rule; a
#: move out of one, into any other status, is backward.
EXITS = {"rejected", "withdrawn", "obsolete", "abandoned"}


class GitError(Exception):
    pass


def _git(root: Path, *args: str) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(root), *args], check=True, capture_output=True,
            encoding="utf-8", errors="replace",
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise GitError(str(exc)) from exc


def _listed(root: Path, base: str, directory: str) -> list[str]:
    """Markdown files directly in a directory at the base ref, read NUL-separated. Only a
    directory absent at the base lists nothing; any other git failure is raised."""
    try:
        _git(root, "cat-file", "-e", f"{base}:{directory}")
    except GitError:
        return []
    out = _git(root, "ls-tree", "-z", "--name-only", f"{base}:{directory}")
    return sorted(n for n in out.split("\0") if n.endswith(".md"))


#: A typed document's number, its identity: the slug after it may change.
NUMBER_RE = re.compile(r"^(\d{4})-")


def _current(root: Path, directory: str, name: str) -> Path | None:
    """The file that is this document now: the same path, or else the one file in the same
    directory with the same number, so a renamed document is still compared."""
    same = root / directory / name
    if same.is_file():
        return same
    m = NUMBER_RE.match(name)
    found = sorted((root / directory).glob(f"{m.group(1)}-*.md")) if m else []
    return found[0] if len(found) == 1 else None


def _lines(text: str) -> list[str]:
    return digest.split_lines(text.removeprefix(chr(0xFEFF)))


def status(lines: list[str]) -> str | None:
    """The frontmatter's status as the build reads it, or None if it cannot be read."""
    end = plans.frontmatter_end(lines)
    if end is None:
        return None
    try:
        data = yaml.load("\n".join(lines[1:end]), Loader=plans.NoTimestampLoader)
    except yaml.YAMLError:
        return None  # REQ_FRONTMATTER_SCHEMA reports it
    value = data.get("status") if isinstance(data, dict) else None
    return value if isinstance(value, str) else None


def _without_status(lines: list[str]) -> list[str]:
    i = digest.status_line(lines)
    return lines if i is None else lines[:i] + lines[i + 1:]


def check_decisions(root: Path, base: str) -> list[Finding]:
    findings = []
    for name in _listed(root, base, DECISIONS):
        path = f"{DECISIONS}/{name}"
        before = _lines(_git(root, "show", f"{base}:{path}"))
        status_before = status(before)
        if status_before == "proposed":
            continue
        current = root / path
        if not current.is_file():
            findings.append(Finding(
                "REQ_IMMUTABLE_DECISIONS", path,
                f"a MADR in status '{status_before}' was deleted or renamed",
            ))
            continue
        after = _lines(digest.read(current))
        status_after = status(after)
        # Only the line YAML reads as the status key may change; anything else, a
        # status-looking line elsewhere included, is content.
        if _without_status(before) != _without_status(after):
            findings.append(Finding(
                "REQ_IMMUTABLE_DECISIONS", path,
                f"content of a MADR in status '{status_before}' changed; write a new MADR "
                f"that supersedes it",
            ))
        if status_before in TERMINAL and status_after != status_before:
            findings.append(Finding(
                "REQ_IMMUTABLE_DECISIONS", path,
                f"status '{status_before}' is terminal but changed to '{status_after}'",
            ))
        if status_before == "accepted" and status_after not in ALLOWED_FROM_ACCEPTED:
            findings.append(Finding(
                "REQ_IMMUTABLE_DECISIONS", path,
                f"an accepted MADR may move only to deprecated or superseded, "
                f"not '{status_after}'",
            ))
    return findings


def _backward(directory: str, before: str | None, after: str | None) -> bool:
    """A move out of an exit, or down the order; a status that cannot be read now, where
    one could at the base, counts too, so breaking the frontmatter hides no move."""
    if before is None or before == after:
        return False
    if before in EXITS:
        return True
    order = RANKS[directory]
    if before in order and after not in order and after not in EXITS:
        return True
    return before in order and after in order and order.index(after) < order.index(before)


def check_statuses(root: Path, base: str) -> list[Finding]:
    """REQ_STATUS_FORWARD."""
    findings = []
    relied_on = {s for statuses in digest.RELIED_ON.values() for s in statuses}
    for directory in RANKS:
        for name in _listed(root, base, directory):
            path = f"{directory}/{name}"
            before = status(_lines(_git(root, "show", f"{base}:{path}")))
            current = _current(root, directory, name)
            if current is None:
                if before in relied_on or before in EXITS:
                    findings.append(Finding(
                        "REQ_STATUS_FORWARD", path,
                        f"a document in status '{before}' at the base is gone from the tree",
                    ))
                continue
            after = status(_lines(digest.read(current)))
            if _backward(directory, before, after):
                where = current.relative_to(root).as_posix()
                findings.append(Finding(
                    "REQ_STATUS_FORWARD", where,
                    f"status moved back from '{before}' to "
                    + (f"'{after}'" if after else "a status that cannot be read"),
                ))
    return findings


def _resolved_tasks(lines: list[str]) -> dict[str, tuple[list[str], list[str]]]:
    """Task ID -> (raw task lines, As built entry lines) for every resolved task."""
    plan = plans.parse(lines)
    entries = {}
    if "As built" in plan.sections:
        stop = plan.sections["As built"][1]
        heads = [line for _, line in plan.as_built] + [stop]
        for (n, line), nxt in zip(plan.as_built, heads[1:]):
            entries[n] = [l.rstrip(" \t") for l in lines[line:nxt]]
            while entries[n] and not entries[n][-1]:
                entries[n].pop()
    out = {}
    for task in plan.tasks:
        if task.resolved and task.id:
            out[task.id] = (lines[task.line:task.end + 1], entries.get(task.number, []))
    return out


def check_tasks(root: Path, base: str) -> list[Finding]:
    """REQ_FROZEN_TASKS."""
    now: dict[str, tuple[str, tuple[list[str], list[str]]]] = {}
    for current in sorted((root / PLANS).glob("*.md")):
        path = f"{PLANS}/{current.name}"
        lines = _lines(digest.read(current))
        for task in plans.parse(lines).tasks:
            if task.id:
                now.setdefault(task.id, (path, (lines[task.line:task.end + 1], [])))
        for task_id, frozen in _resolved_tasks(lines).items():
            now[task_id] = (path, frozen)
    findings = []
    for name in _listed(root, base, PLANS):
        path = f"{PLANS}/{name}"
        for task_id, (text, entry) in _resolved_tasks(
                _lines(_git(root, "show", f"{base}:{path}"))).items():
            if task_id not in now:
                findings.append(Finding(
                    "REQ_FROZEN_TASKS", path,
                    f"{task_id}, resolved at the base, is gone"
                    + ("" if (root / path).is_file() else " with its plan"),
                ))
                continue
            where, (text_now, entry_now) = now[task_id]
            same = _current(root, PLANS, name)
            if same is None or where != same.relative_to(root).as_posix():
                findings.append(Finding(
                    "REQ_FROZEN_TASKS", where,
                    f"{task_id}, resolved at the base in {path}, moved to another plan",
                ))
            elif text_now != text:
                findings.append(Finding(
                    "REQ_FROZEN_TASKS", path,
                    f"{task_id} was resolved at the base; its text or step marks changed",
                ))
            elif entry_now != entry:
                findings.append(Finding(
                    "REQ_FROZEN_TASKS", path,
                    f"{task_id} was resolved at the base; its As built entry changed",
                ))
    return findings


def check(root: Path, base: str) -> list[Finding]:
    try:
        _git(root, "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}")
    except GitError:
        return [Finding("REQ_WARNINGS_FATAL", "(git)",
                        f"the base ref '{base}' does not resolve to a commit")]
    try:
        return check_decisions(root, base) + check_statuses(root, base) + check_tasks(root, base)
    except GitError as exc:
        return [Finding("REQ_WARNINGS_FATAL", "(git)", f"cannot read the base ref: {exc}")]
