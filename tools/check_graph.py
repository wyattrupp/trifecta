"""Post-build rules over needs.json that sphinx-needs schemas cannot express (DEC_0006):
comparing values across needs, disjunctions across link types, and resolving paths in
the repository."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from findings import Finding


def load_needs(needs_json: Path) -> dict[str, dict]:
    data = json.loads(needs_json.read_text(encoding="utf-8"))
    return data["versions"][data["current_version"]]["needs"]


def _where(need: dict) -> str:
    return f"docs/{need['docname']}{need['doctype']}:{need['lineno']}"


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ext"))

from plans import HELD as LIVE_PLANS  # noqa: E402  (an abandoned plan builds nothing)


def check_plans(needs: dict[str, dict]) -> list[Finding]:
    """REQ_DESIGN_BUILT: once a live plan implements a design doc, every component and
    interface of that design is built by a task of such a plan."""
    findings = []
    built: dict[str, set[str]] = {}  # design ID -> element IDs built by its live plans
    for plan in needs.values():
        if plan["type"] != "plan" or plan.get("status") not in LIVE_PLANS:
            continue
        builds = {b for task in needs.values()
                  if task["type"] == "task" and task["docname"] == plan["docname"]
                  for b in task.get("builds") or []}
        for design in plan.get("implements") or []:
            built.setdefault(design, set()).update(builds)
    for design_id, ids in sorted(built.items()):
        design = needs.get(design_id)
        if not design:
            continue  # REQ_LINK_TARGETS reports the broken link
        for element in sorted(needs.values(), key=lambda n: n["id"]):
            if (element["docname"] == design["docname"]
                    and element["type"] in ("component", "interface")
                    and element["id"] not in ids):
                findings.append(Finding(
                    "REQ_DESIGN_BUILT", _where(element),
                    f"{element['id']} of {design_id} is built by no task of a plan "
                    f"implementing {design_id}",
                ))
    return findings


def check(needs: dict[str, dict], root: Path) -> list[Finding]:
    findings = check_plans(needs)
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
            target = (root / path).resolve()
            if not target.is_relative_to(root.resolve()) or ".git" in target.parts:
                findings.append(Finding(
                    "REQ_SPEC_RESOLVES", _where(need),
                    f"{need['id']} spec '{path}' must be a path inside the repository",
                ))
            elif not target.is_file():
                findings.append(Finding(
                    "REQ_SPEC_RESOLVES", _where(need),
                    f"{need['id']} spec '{path}' does not exist",
                ))
            elif fragment and not re.search(
                re.escape(fragment) + r"(?!\w)",
                target.read_text(encoding="utf-8", errors="replace"),
            ):
                findings.append(Finding(
                    "REQ_SPEC_RESOLVES", _where(need),
                    f"{need['id']} spec fragment '{fragment}' does not occur in {path}",
                ))
    return findings
