"""REQ_IMMUTABLE_DECISIONS: compare every MADR with its version at a base git ref."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from findings import Finding

DECISIONS = "docs/decisions"
STATUS_LINE = re.compile(r"^status:[^\n]*$", re.M)
ALLOWED_FROM_ACCEPTED = {"accepted", "deprecated", "superseded"}
TERMINAL = {"rejected", "deprecated", "superseded"}


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    ).stdout


def _status(text: str) -> str | None:
    m = STATUS_LINE.search(text)
    return m.group(0).split(":", 1)[1].strip() if m else None


def check(root: Path, base: str) -> list[Finding]:
    findings = []
    listed = _git(root, "ls-tree", "--name-only", f"{base}:{DECISIONS}").split()
    for name in sorted(n for n in listed if n.endswith(".md")):
        path = f"{DECISIONS}/{name}"
        before = _git(root, "show", f"{base}:{path}")
        status_before = _status(before)
        if status_before == "proposed":
            continue
        current = root / path
        if not current.is_file():
            findings.append(Finding(
                "REQ_IMMUTABLE_DECISIONS", path,
                f"a MADR in status '{status_before}' was deleted or renamed",
            ))
            continue
        after = current.read_text(encoding="utf-8")
        status_after = _status(after)
        if STATUS_LINE.sub("status:", before) != STATUS_LINE.sub("status:", after):
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
