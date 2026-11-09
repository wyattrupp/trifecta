"""Print where an active plan stands (COMP_NEXT_COMMAND).

    python tools/next.py docs/plans/NNNN-slug.md

Prints the plan's "Rules for every task" and the whole task holding the next open
step, with that step marked. Task numbers are build order, so the next step is the
first open checkbox. It does not check the plan; ``make check`` does.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ext"))

import plans  # noqa: E402

MARK = ">>> "


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("plan", type=Path)
    args = parser.parse_args(argv)
    lines = args.plan.read_text(encoding="utf-8").splitlines()
    status = plans.frontmatter(lines).get("status")
    plan = plans.parse(lines)
    found = plan.next_step()

    if status == "done" and found is None:
        print(f"{args.plan.as_posix()} is done")
        return 0
    if status != "active":
        reason = {"draft": "is a draft: review it, then set status: active",
                  "done": "is marked done but has open steps; run make check",
                  "abandoned": "is abandoned"}.get(status, "has no status")
        print(f"{args.plan.as_posix()} {reason}")
        return 1
    if found is None:
        print(f"{args.plan.as_posix()} has no open step: write the As built entries "
              f"and set status: done")
        return 0
    task, step = found
    if "Rules for every task" in plan.sections:
        start, stop = plan.sections["Rules for every task"]
        print("\n".join(lines[start:stop]).rstrip(), end="\n\n")
    for i in range(task.line, min(task.end, len(lines) - 1) + 1):
        print((MARK if i == step.line else "") + lines[i])
    return 0


if __name__ == "__main__":
    sys.exit(main())
