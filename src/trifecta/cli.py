"""The `trifecta` command (IF_CLI): one subcommand per tool, each reading the corpus from the
working directory."""

from __future__ import annotations

import importlib
import sys

#: Subcommand -> the module whose ``main(argv)`` runs it.
COMMANDS = {
    "setup": "setup",
    "check": "check",
    "fixtures": "run_fixtures",
    "new": "new",
    "next": "next",
    "review": "review",
    "init": "init",
    "profile": "profiler",
}

USAGE = f"usage: trifecta {{{','.join(COMMANDS)}}} [args...]"


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not args or args[0] in ("-h", "--help"):
        print(USAGE)
        return 0 if args else 2
    command, rest = args[0], args[1:]
    if command not in COMMANDS:
        print(f"{USAGE}\ntrifecta: unknown command {command!r}", file=sys.stderr)
        return 2
    module = importlib.import_module(f".{COMMANDS[command]}", __package__)
    return module.main(rest)
