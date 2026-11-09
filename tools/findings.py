"""The finding format every stage emits (IF_FINDING), and the Sphinx-output mapping."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

#: The environment every Python program the check starts runs with, so its output is UTF-8.
CHILD_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8"}


@dataclass(frozen=True, order=True)
class Finding:
    req: str
    location: str
    message: str

    def line(self) -> str:
        return f"{self.req}\t{self.location}\t{self.message}"

    @classmethod
    def parse(cls, line: str) -> "Finding":
        req, location, message = line.split("\t", 2)
        return cls(req, location, message)


_ENTRY_START = re.compile(r"^(?:(?P<loc>\S.*?): )?(?:WARNING|ERROR|CRITICAL): ")
_OWN = re.compile(r"\[trifecta\.(REQ_[A-Z_]+)\]")
_SCHEMA = re.compile(r"Schema path:\s+(REQ_[A-Z_]+)\[")
_NEED_PATH = re.compile(r"Need '([^']+)' has schema violations")
_MESSAGE = re.compile(r"User message:\s+(.*)")
_SCHEMA_MESSAGE = re.compile(r"Schema message:\s+(.*?)\s*(?:\[[a-z_.]+\])?$", re.M)
#: Both arrive as needs.create_need, a code other failures share, so match the message.
_DUPLICATE = re.compile(r"A need with ID '[^']+' already exists|does not match the id_regex")

#: Native sphinx-needs warning codes, by the requirement they enforce.
_NATIVE = {
    "needs.link_target_type": "REQ_LINK_TARGETS",
    "needs.link_outgoing": "REQ_LINK_TARGETS",
    "needs.invalid_id": "REQ_UNIQUE_IDS",
}
_CODE = re.compile(r"\[([a-z_]+\.[a-z_]+)\]\s*$", re.M)


_LOCATION = re.compile(r"^(?P<path>.*?)(?P<suffix>(?::\d+)*)$", re.S)
_DRIVE = re.compile(r"^[A-Za-z]:")


def relative_location(location: str, root: Path) -> str:
    """Map a program's location to a path relative to ``root``, with forward slashes.

    The comparison ignores case where the platform does. A location this cannot map is
    left as it is, for ``unportable`` to report (REQ_PORTABLE_FINDINGS).
    """
    m = _LOCATION.match(location)
    path, suffix = m.group("path"), m.group("suffix")
    if not path:
        return location
    prefix = os.path.normcase(str(root)).rstrip(os.sep) + os.sep
    if os.path.isabs(path) and os.path.normcase(path).startswith(prefix):
        return path[len(prefix):].replace(os.sep, "/") + suffix
    return location


def unportable(location: str) -> bool:
    """A location that starts at a root, a drive or a UNC prefix, or holds ``..`` or a backslash."""
    path = _LOCATION.match(location).group("path")
    return (path.startswith("/") or "\\" in path or bool(_DRIVE.match(path))
            or ".." in path.split("/"))


def _entries(stderr: str) -> list[str]:
    entries: list[list[str]] = []
    for raw in stderr.splitlines():
        if _ENTRY_START.match(raw):
            entries.append([raw])
        elif entries and raw.strip():
            entries[-1].append(raw)
    return ["\n".join(e) for e in entries]


def from_sphinx(stderr: str, root: Path) -> list[Finding]:
    """Map every Sphinx warning or error to the requirement it violates.

    Anything no requirement claims is still a failure, under REQ_WARNINGS_FATAL.
    """
    findings = []
    for entry in _entries(stderr):
        head = entry.splitlines()[0]
        m = _ENTRY_START.match(head)
        loc = relative_location((m.group("loc") or "") if m else "", root)
        text = _ENTRY_START.sub("", head)
        if (own := _OWN.search(entry)):
            req = own.group(1)
            text = _OWN.sub("", text).strip()
            text = text.split(": ", 1)[1] if text.startswith(req) else text
        elif (schema := _SCHEMA.search(entry)):
            req = schema.group(1)
            need = _NEED_PATH.search(entry)
            msg = _MESSAGE.search(entry) or _SCHEMA_MESSAGE.search(entry)
            loc = loc or (f"need:{need.group(1)}" if need else "")
            detail = msg.group(1).strip() if msg else text
            text = f"{need.group(1)}: {detail}" if need else detail
        elif _DUPLICATE.search(entry):
            req = "REQ_UNIQUE_IDS"
            text = _CODE.sub("", text).strip()
        else:
            code = _CODE.search(entry)
            req = _NATIVE.get(code.group(1), "REQ_WARNINGS_FATAL") if code else "REQ_WARNINGS_FATAL"
            text = _CODE.sub("", text).strip()
        findings.append(Finding(req, loc or "(build)", text))
    return findings
