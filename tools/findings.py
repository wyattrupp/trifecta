"""The finding format every stage emits (IF_FINDING), and the Sphinx-output mapping."""

from __future__ import annotations

import re
from dataclasses import dataclass


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


def _entries(stderr: str) -> list[str]:
    entries: list[list[str]] = []
    for raw in stderr.splitlines():
        if _ENTRY_START.match(raw):
            entries.append([raw])
        elif entries and raw.strip():
            entries[-1].append(raw)
    return ["\n".join(e) for e in entries]


def from_sphinx(stderr: str, docs_prefix: str) -> list[Finding]:
    """Map every Sphinx warning or error to the requirement it violates.

    Anything no requirement claims is still a failure, under REQ_WARNINGS_FATAL.
    """
    findings = []
    for entry in _entries(stderr):
        head = entry.splitlines()[0]
        m = _ENTRY_START.match(head)
        loc = (m.group("loc") or "") if m else ""
        loc = loc.split(docs_prefix, 1)[-1] if docs_prefix in loc else loc
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
