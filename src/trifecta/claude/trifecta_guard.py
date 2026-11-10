"""Claude Code PreToolUse hook: refuse a write under docs/superpowers/ (REQ_HOOK_FAILS_CLOSED).

Specs and plans here are typed documents that `trifecta new` writes under docs/. This
hook reads the tool call as JSON from standard input, never hands any of it to a shell,
resolves the path a tool would write, and exits 2, the code Claude Code reads as a
refusal, when that path is under docs/superpowers/, when a shell command names a path
there, when the input cannot be read, and on any exception at all. Only an allowed call
exits 0.
"""

import sys  # built into the interpreter: it cannot fail to import


def _refuse(message):
    """Block: write the message if possible, then exit 2 whatever happens."""
    try:
        sys.stderr.write(message + "\n")
        sys.stderr.flush()
    except BaseException:
        pass
    try:
        import os
        os._exit(2)
    except BaseException:
        pass
    sys.exit(2)


_allowed = False
_message = ("refused: this repository keeps specs and plans as typed documents under "
            "docs/; start one with `trifecta new rfc|decision|design <slug>` or "
            "`trifecta new plan <slug> --implements DES_NNNN`, never under docs/superpowers/")
try:
    import json
    import os
    import re

    PATH_KEYS = {"Write": "file_path", "Edit": "file_path", "MultiEdit": "file_path",
                 "NotebookEdit": "notebook_path"}
    GUARDED = ["docs", "superpowers"]
    #: A shell command that names docs/superpowers, however its separators, case or
    #: trailing dots and spaces are written.
    NAMED = re.compile(r"docs/+superpowers[. ]*(?:/|$|[\s'\"`;&|<>()])")

    def _segments(path):
        """Path segments as Windows compares them: no case, no trailing dots or spaces."""
        out = []
        for part in path.replace("\\", "/").split("/"):
            if part == "..":
                if out and out[-1] != "..":
                    out.pop()
                else:
                    out.append(part)
                continue
            # A stream name (``x:y``, ``x::$INDEX_ALLOCATION``) still names the file or
            # directory before the colon; a drive letter is not a segment here.
            if ":" in part and not re.fullmatch(r"[A-Za-z]:", part):
                part = part.split(":")[0]
            part = part.rstrip(". ").casefold()
            if part not in ("", "."):
                out.append(part)
        return out

    def _names_guarded(segments):
        """Whether ``docs`` then ``superpowers`` appear anywhere in a path's segments."""
        return any(segments[i:i + 2] == GUARDED for i in range(len(segments)))

    def _plain(path):
        """A Windows path without the ``\\\\?\\`` prefix realpath can return, so it compares
        with a path that has none."""
        if path.startswith("\\\\?\\UNC\\"):
            return "\\\\" + path[8:]
        if path.startswith("\\\\?\\"):
            return path[4:]
        return path

    def _guarded(raw, project, cwd):
        """Whether ``raw``, resolved against the session's directory, is under the
        project's docs/superpowers."""
        text = raw.replace("\\", "/")
        if text == "~" or text.startswith("~/"):
            text = os.path.expanduser(text)  # as the file tools read a leading ~
        if not (os.path.isabs(text) or re.match(r"^[A-Za-z]:/", text) or text.startswith("//")):
            text = os.path.join(cwd, text)
        real = _plain(os.path.realpath(text))
        base = _plain(os.path.realpath(project))
        try:
            rel = os.path.relpath(real, base)
        except ValueError:
            # Not relatable to the project, as a UNC or loopback share path is not: refuse
            # when it names docs/superpowers anywhere, rather than guess it is elsewhere.
            return _names_guarded(_segments(real))
        segments = _segments(rel)
        if segments[:1] == [".."]:
            return False
        return segments[:2] == GUARDED

    def _decide():
        data = json.loads(sys.stdin.buffer.read().decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("the input is not a JSON object")
        tool, given = data.get("tool_name"), data.get("tool_input")
        if not isinstance(tool, str) or not isinstance(given, dict):
            raise ValueError("the input names no tool and its input")
        project = os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd()
        cwd = data.get("cwd") or project  # where the session resolves a relative path
        if not isinstance(project, str) or not isinstance(cwd, str):
            raise ValueError("no project directory")
        if tool in PATH_KEYS:
            path = given.get(PATH_KEYS[tool])
            if not isinstance(path, str):
                raise ValueError(f"{tool} names no path")
            return not _guarded(path, project, cwd)
        if tool == "Bash":
            command = given.get("command")
            if not isinstance(command, str):
                raise ValueError("Bash names no command")
            if NAMED.search(command.replace("\\", "/").casefold()):
                return False
            for token in re.split(r"[\s;&|<>()`'\"=]+", command):
                if "superpowers" in token.casefold() and _guarded(token, project, cwd):
                    return False
        return True

    _allowed = _decide()
except BaseException as exc:
    _allowed = False
    _message = f"refused: the hook could not read the tool call ({type(exc).__name__}); " + _message

if _allowed:
    sys.exit(0)
_refuse(_message)
