"""REQ_INIT_SAFE, REQ_HOOK_FAILS_CLOSED: the tests of the planning files that do what the
recorder refuses, moved from ``test_planning`` unchanged (COMP_LIFTED_REASONS): its bash
test, which runs the hook's command through bash (DEC_0034), and its Windows junction and
ctypes tests.

Each refuses the run of this module under its own recorder, so this module is never
stored, and ``test_planning``, which keeps the rest, is.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests import test_planning
from tests.test_init import Repo
from tests.test_planning import SETTINGS, git_bash, hook, refused, run_init, write, write_call
from trifecta.init import COMMAND
from trifecta.testing import only_on, proves
from trifecta.toolchain import program_env


class SettingsMerge(unittest.TestCase):
    settings_race = test_planning.SettingsMerge.settings_race

    @proves("REQ_INIT_SAFE")
    @only_on("nt")
    def test_settings_in_a_junctioned_directory_is_refused(self):
        import _winapi
        with Repo() as root, tempfile.TemporaryDirectory() as outside:
            write(Path(outside) / "settings.json", b"{}")
            _winapi.CreateJunction(outside, str(root / ".claude"))
            refused(self, root, ".claude/ is a link")

    @proves("REQ_INIT_SAFE")
    @only_on("nt")
    def test_settings_directory_swapped_for_a_junction_before_the_move_is_refused(self):
        import _winapi

        def junction(root, outside):
            (root / ".claude").rename(root / ".claude-moved")
            _winapi.CreateJunction(outside, str(root / ".claude"))
        self.settings_race(junction)


class HookCommand(unittest.TestCase):
    @proves("REQ_INIT_SAFE", "REQ_HOOK_FAILS_CLOSED")
    def test_command_with_a_space_in_the_path_and_no_interpreter_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve() / "my repo"
            root.mkdir()
            subprocess.run(["git", "init", "-q", str(root)], check=True, env=program_env())
            run_init(root)
            settings = json.loads((root / SETTINGS).read_bytes())
            command = settings["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
            self.assertEqual(command, COMMAND)
            bash = git_bash()
            empty = Path(tmp) / "empty-path"
            empty.mkdir()
            env = {**os.environ, "CLAUDE_PROJECT_DIR": str(root), "PATH": str(empty)}
            call = json.dumps({"tool_name": "Write", "tool_input": {"file_path": "docs/rfcs/x.md"}})
            done = subprocess.run([bash, "-c", command], input=call, env=env,
                                  capture_output=True, encoding="utf-8")
            self.assertEqual(done.returncode, 2, done.stderr)
            # With an interpreter on PATH the same command allows an allowed write.
            shim = Path(tmp) / "shim"
            shim.mkdir()
            exe = Path(sys.executable).as_posix()
            script = "#!/bin/sh\n" + f'exec "{exe}" "$@"' + "\n"
            (shim / "python3").write_text(script, encoding="utf-8", newline="\n")
            os.chmod(shim / "python3", 0o755)
            env["PATH"] = str(shim)
            done = subprocess.run([bash, "-c", command], input=call, env=env,
                                  capture_output=True, encoding="utf-8")
            self.assertEqual(done.returncode, 0, done.stderr)


class Hook(unittest.TestCase):
    @proves("REQ_HOOK_FAILS_CLOSED")
    @only_on("nt")
    def test_resolves_a_junction_and_a_short_name(self):
        import ctypes
        import _winapi
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            target = root / "docs" / "superpowers"
            target.mkdir(parents=True)
            _winapi.CreateJunction(str(target), str(root / "notes"))
            self.assertEqual(hook(root, write_call("notes/x.md")), 2)
            buf = ctypes.create_unicode_buffer(1024)
            ctypes.windll.kernel32.GetShortPathNameW(str(target), buf, 1024)
            short = Path(buf.value).name
            self.assertNotEqual(short.casefold(), "superpowers", "8.3 names are off here")
            self.assertEqual(hook(root, write_call(f"docs/{short}/x.md")), 2)


if __name__ == "__main__":
    unittest.main()
