"""The plan shape (DEC_0009): tasks in build order, steps as checkboxes, linear execution.

Pure functions over a plan's source lines. The Sphinx extension reports what
``problems`` finds; ``tools/next.py`` and ``tools/new.py`` read and write the same
shape through the constants here, so the shape has one home.

A task is a ``:::{task}`` need under ``## Tasks`` with ``:id: TASK_<plan>_<NN>``,
``:builds:`` and ``:gate:``. Its steps are top-level checkboxes in its body::

    - [ ] **2.1** open
    - [x] **2.2** done
    - [-] **2.3** dropped (the As built entry says why)

A task is resolved when it has steps and none is open. ``## As built`` holds one
``### Task N (YYYY-MM-DD)`` entry per resolved task, in task order.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

OPEN, DONE, DROPPED = " ", "x", "-"
#: Statuses whose plans make the linear promise. An abandoned plan is past changing.
HELD = ("draft", "active", "done")

TASK_OPEN_RE = re.compile(r"^:::\{task\}(?:[ \t]+(?P<title>.*?))?[ \t]*$")
TASK_ID_RE = re.compile(r"^TASK_(?P<plan>\d{4})_(?P<n>\d{2,})$")
OPTION_RE = re.compile(r"^:(?P<key>[A-Za-z_][\w-]*):(?P<value>.*)$")
STEP_RE = re.compile(r"^- \[(?P<state>[ x-])\] \*\*(?P<n>\d+)\.(?P<k>\d+)\*\* \S")
#: Anything that looks like a checkbox, so a malformed step is reported, not ignored.
STEP_LIKE_RE = re.compile(r"^\s*[-*+] \[.?\]")
AS_BUILT_RE = re.compile(r"^### Task (?P<n>\d+) \((?P<date>\d{4}-\d{2}-\d{2})\)[ \t]*$")
H2_RE = re.compile(r"^ {0,3}##(?:[ \t]+(?P<title>.*?))?(?:[ \t]+#+)?[ \t]*$")
H3_RE = re.compile(r"^ {0,3}###(?:[ \t]|$)")
FENCE_RE = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})")


def step_line(n: int, k: int, text: str, state: str = OPEN) -> str:
    return f"- [{state}] **{n}.{k}** {text}"


def task_id(plan: str, n: int) -> str:
    return f"TASK_{plan}_{n:02d}"


@dataclass
class Step:
    n: int
    k: int
    state: str
    line: int  # 0-based index into the source lines


@dataclass
class Task:
    title: str
    line: int
    end: int
    in_tasks_section: bool
    options: dict[str, tuple[str, int]] = field(default_factory=dict)
    steps: list[Step] = field(default_factory=list)
    malformed: list[int] = field(default_factory=list)

    @property
    def id(self) -> str | None:
        return self.options.get("id", ("", 0))[0] or None

    @property
    def number(self) -> int | None:
        m = TASK_ID_RE.match(self.id or "")
        return int(m.group("n")) if m else None

    @property
    def resolved(self) -> bool:
        return bool(self.steps) and all(s.state != OPEN for s in self.steps)


@dataclass
class Plan:
    tasks: list[Task]
    sections: dict[str, tuple[int, int]]  # H2 title -> (heading index, end index)
    as_built: list[tuple[int, int]]  # (task number, line) per well-formed entry
    as_built_bad: list[int]  # lines of other H3 headings under As built

    def steps(self) -> list[tuple[Task, Step]]:
        return [(t, s) for t in self.tasks for s in t.steps]

    def next_step(self) -> tuple[Task, Step] | None:
        return next(((t, s) for t, s in self.steps() if s.state == OPEN), None)


def fenced(lines: list[str]) -> list[bool]:
    """True for every line inside a backtick or tilde code fence, fences included."""
    mask, closer = [], None
    for line in lines:
        m = FENCE_RE.match(line)
        if closer is None:
            if m:
                closer = m.group("fence")
            mask.append(closer is not None)
        else:
            mask.append(True)
            if m and m.group("fence")[0] == closer[0] and len(m.group("fence")) >= len(closer) \
                    and not line.strip()[len(m.group("fence")):].strip():
                closer = None
    return mask


def parse(lines: list[str]) -> Plan:
    code = fenced(lines)
    heads = [(i, H2_RE.match(l).group("title") or "") for i, l in enumerate(lines)
             if not code[i] and H2_RE.match(l)]
    sections = {
        title: (i, heads[j + 1][0] if j + 1 < len(heads) else len(lines))
        for j, (i, title) in enumerate(heads)
    }
    tasks_span = sections.get("Tasks", (-1, -1))

    tasks: list[Task] = []
    i = 0
    while i < len(lines):
        m = None if code[i] else TASK_OPEN_RE.match(lines[i])
        if not m:
            i += 1
            continue
        end = next((j for j in range(i + 1, len(lines)) if not code[j]
                    and lines[j].rstrip() == ":::"), len(lines))
        task = Task(m.group("title") or "", i, end, tasks_span[0] < i < tasks_span[1])
        j = i + 1
        while j < end and (o := OPTION_RE.match(lines[j])):
            task.options[o.group("key")] = (o.group("value").strip(), j)
            j += 1
        for j in range(j, end):
            if code[j]:
                continue
            if s := STEP_RE.match(lines[j]):
                task.steps.append(Step(int(s.group("n")), int(s.group("k")), s.group("state"), j))
            elif STEP_LIKE_RE.match(lines[j]):
                task.malformed.append(j)
        tasks.append(task)
        i = end + 1

    as_built, bad = [], []
    if "As built" in sections:
        start, stop = sections["As built"]
        for j in range(start + 1, stop):
            if code[j] or not H3_RE.match(lines[j]):
                continue
            if e := AS_BUILT_RE.match(lines[j]):
                as_built.append((int(e.group("n")), j))
            else:
                bad.append(j)
    return Plan(tasks, sections, as_built, bad)


def problems(plan: Plan, plan_number: str, status: str | None) -> list[tuple[str, str, int]]:
    """Every violation as (requirement, message, 1-based line)."""
    out: list[tuple[str, str, int]] = []

    def add(req: str, msg: str, line: int) -> None:
        out.append((req, msg, line + 1))

    # REQ_TASK_ORDER: IDs carry this plan's number and run 01..N in document order.
    for expected, task in enumerate(plan.tasks, 1):
        m = TASK_ID_RE.match(task.id or "")
        if not m or m.group("plan") != plan_number:
            add("REQ_TASK_ORDER", f"task ID must be {task_id(plan_number, expected)}, "
                                  f"got {task.id or 'none'}", task.line)
        elif task.number != expected:
            add("REQ_TASK_ORDER", f"tasks must run 1..N in build order without gaps; "
                                  f"expected {task_id(plan_number, expected)}, got {task.id}",
                task.line)

    # REQ_TASK_SHAPE: where a task lives, what it builds, its gate, and its steps.
    for task in plan.tasks:
        name = task.id or task.title or "task"
        if not task.in_tasks_section:
            add("REQ_TASK_SHAPE", f"{name} is outside '## Tasks'", task.line)
        for key in ("builds", "gate"):
            if not task.options.get(key, ("", 0))[0]:
                add("REQ_TASK_SHAPE", f"{name} has no ':{key}:'", task.line)
        if not task.steps:
            add("REQ_TASK_SHAPE", f"{name} has no steps", task.line)
        for line in task.malformed:
            add("REQ_TASK_SHAPE", f"malformed step; write '{step_line(task.number or 0, 1, '...')}'",
                line)
        for k, step in enumerate(task.steps, 1):
            if task.number is not None and (step.n, step.k) != (task.number, k):
                add("REQ_TASK_SHAPE", f"step must be numbered {task.number}.{k}, "
                                      f"got {step.n}.{step.k}", step.line)

    if status not in HELD:
        return out

    # REQ_LINEAR_EXECUTION: nothing is ticked in a draft, and nothing after an open step.
    first_open = None
    for task, step in plan.steps():
        if step.state == OPEN:
            first_open = first_open or step
        elif status == "draft":
            add("REQ_LINEAR_EXECUTION", "a draft plan has no done or dropped steps; "
                                        "review it and make it active first", step.line)
        elif first_open is not None:
            add("REQ_LINEAR_EXECUTION", f"step {step.n}.{step.k} is resolved while "
                                        f"{first_open.n}.{first_open.k} is still open", step.line)

    # REQ_AS_BUILT: one entry per resolved task, in order; a done plan resolves all.
    resolved = [t.number for t in plan.tasks if t.resolved and t.number is not None]
    for line in plan.as_built_bad:
        add("REQ_AS_BUILT", "an As built heading must read '### Task N (YYYY-MM-DD)'", line)
    entries = [n for n, _ in plan.as_built]
    if entries != resolved:
        at = plan.sections.get("As built", (0, 0))[0]
        add("REQ_AS_BUILT", f"As built must hold exactly the resolved tasks in order, "
                            f"{resolved}; found {entries}", at)
    if status == "done":
        for task in plan.tasks:
            if not task.resolved:
                add("REQ_AS_BUILT", f"a done plan has every task resolved; "
                                    f"{task.id or task.title} is not", task.line)
    return out
