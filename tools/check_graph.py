"""Post-build rules over needs.json that sphinx-needs schemas cannot express (DEC_0006):
comparing values across needs, disjunctions across link types, and resolving paths in
the repository."""

from __future__ import annotations

import json
from pathlib import Path

from findings import Finding


def load_needs(needs_json: Path) -> dict[str, dict]:
    data = json.loads(needs_json.read_text())
    return data["versions"][data["current_version"]]["needs"]


def _where(need: dict) -> str:
    return f"docs/{need['docname']}{need['doctype']}:{need['lineno']}"


def check(needs: dict[str, dict], root: Path) -> list[Finding]:
    findings = []
    for need in needs.values():
        # REQ_CHOICE_CONSIDERED
        if need["type"] == "decision":
            for chosen in need.get("chooses") or []:
                if chosen not in (need.get("considers") or []):
                    findings.append(Finding(
                        "REQ_CHOICE_CONSIDERED", _where(need),
                        f"{need['id']} chooses {chosen}, which it does not consider "
                        f"(considers {sorted(need.get('considers') or [])})",
                    ))
        # REQ_NO_ORPHANS. A derived union link would make this a local schema, but
        # sphinx-needs 9.2 does not validate union-derived links, so it runs here.
        if need["type"] == "component" and not (need.get("satisfies") or need.get("constrained_by")):
            findings.append(Finding(
                "REQ_NO_ORPHANS", _where(need),
                f"{need['id']} neither satisfies a requirement nor is constrained by a decision",
            ))
        if need["type"] == "interface":
            providers = [p for p in need.get("provides_back") or [] if needs.get(p, {}).get("type") == "component"]
            if len(providers) != 1:
                findings.append(Finding(
                    "REQ_NO_ORPHANS", _where(need),
                    f"{need['id']} must be provided by exactly one component, found {sorted(providers)}",
                ))
        # REQ_SPEC_RESOLVES
        spec = need.get("spec")
        if need["type"] in ("component", "interface") and spec:
            path, _, fragment = spec.partition("#")
            target = root / path
            if not target.is_file():
                findings.append(Finding(
                    "REQ_SPEC_RESOLVES", _where(need),
                    f"{need['id']} spec '{path}' does not exist",
                ))
            elif fragment and fragment not in target.read_text():
                findings.append(Finding(
                    "REQ_SPEC_RESOLVES", _where(need),
                    f"{need['id']} spec fragment '{fragment}' does not occur in {path}",
                ))
    return findings
