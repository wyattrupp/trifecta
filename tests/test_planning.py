"""The planning files init adds for Claude Code: REQ_PLANNING_DEFAULT, REQ_HOOK_FAILS_CLOSED,
and the CLAUDE.md append and the settings merge under REQ_INIT_SAFE."""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.test_init import SHA, URL, Repo, snapshot
from trifecta import init as init_module
from trifecta.init import CLAUDE_MD, COMMAND, ENTRY, HOOK, MATCHER, NEW, SETTINGS, SKILL
from trifecta.testing import only_on, proves

SECTION = init_module.section()
HEADING = SECTION.splitlines()[0]
GUARD = init_module.PACKAGE_DIR / "claude" / "trifecta_guard.py"


def run_init(root: Path) -> tuple[list[str], list[str]]:
    return init_module.init(root, "@someone", URL, SHA)


def write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def refused(test: unittest.TestCase, root: Path, contains: str = "") -> str:
    before = snapshot(root)
    with test.assertRaises(init_module.Refused) as caught:
        run_init(root)
    test.assertEqual(snapshot(root), before, "a refused run wrote something")
    test.assertIn(contains, str(caught.exception))
    return str(caught.exception)


# --- CLAUDE.md -------------------------------------------------------------------------

class ClaudeMdAppend(unittest.TestCase):
    def appended(self, original: bytes) -> bytes:
        with Repo() as root:
            write(root / CLAUDE_MD, original)
            _, changed = run_init(root)
            self.assertEqual(changed, [CLAUDE_MD])
            return (root / CLAUDE_MD).read_bytes()

    @proves("REQ_INIT_SAFE", "REQ_PLANNING_DEFAULT")
    def test_existing_keeps_every_byte_and_gains_the_section_once(self):
        got = self.appended(b"# Mine\n\nkeep this\n")
        self.assertEqual(got, b"# Mine\n\nkeep this\n\n" + SECTION.encode())
        self.assertEqual(got.decode().count(HEADING), 1)

    @proves("REQ_INIT_SAFE")
    def test_crlf_file_gets_crlf(self):
        got = self.appended(b"# Mine\r\nkeep\r\n")
        self.assertEqual(got, b"# Mine\r\nkeep\r\n\r\n" + SECTION.replace("\n", "\r\n").encode())

    @proves("REQ_INIT_SAFE")
    def test_last_line_without_a_break_gets_one(self):
        self.assertEqual(self.appended(b"keep"), b"keep\n\n" + SECTION.encode())

    @proves("REQ_INIT_SAFE")
    def test_empty_file_gets_the_section_alone(self):
        self.assertEqual(self.appended(b""), SECTION.encode())

    @proves("REQ_INIT_SAFE")
    def test_file_already_holding_the_section_is_left_alone(self):
        for original in (b"x\n\n" + SECTION.encode(),
                         b"x\r\n\r\n" + SECTION.replace("\n", "\r\n").encode(),
                         b"\xef\xbb\xbf" + SECTION.encode()):
            with self.subTest(original[:6]), Repo() as root:
                write(root / CLAUDE_MD, original)
                written, changed = run_init(root)
                self.assertNotIn(CLAUDE_MD, written + changed)
                self.assertEqual((root / CLAUDE_MD).read_bytes(), original)

    @proves("REQ_INIT_SAFE")
    def test_unreadable_or_altered_file_is_refused(self):
        altered = SECTION.replace("A plan implements", "A plan implemented")
        for name, data, why in (
                ("not UTF-8", b"\xff\xfe x", "not UTF-8"),
                ("stray heading beside the section",
                 SECTION.encode() + b"\n" + HEADING.encode() + b"\n", "without the rest"),
                ("altered body", altered.encode(), "without the rest"),
                ("missing body", (HEADING + "\n").encode(), "without the rest")):
            with self.subTest(name), Repo() as root:
                write(root / CLAUDE_MD, data)
                refused(self, root, why)

    @proves("REQ_INIT_SAFE")
    def test_link_directory_and_leftover_are_refused(self):
        with Repo() as root, tempfile.TemporaryDirectory() as outside:
            (Path(outside) / "theirs.md").write_text("theirs", encoding="utf-8")
            os.symlink(Path(outside) / "theirs.md", root / CLAUDE_MD)
            refused(self, root, "link")
        with Repo() as root:
            (root / CLAUDE_MD).mkdir()
            refused(self, root, "not a regular file")
        with Repo() as root:
            write(root / CLAUDE_MD, b"mine\n")
            write(root / (CLAUDE_MD + NEW), b"left")
            refused(self, root, "left from an earlier run")

    @proves("REQ_INIT_SAFE")
    def test_read_only_file_init_leaves_alone_is_not_refused(self):
        with Repo() as root:
            write(root / CLAUDE_MD, SECTION.encode())
            os.chmod(root / CLAUDE_MD, stat.S_IREAD)
            try:
                written, changed = run_init(root)
                self.assertNotIn(CLAUDE_MD, written + changed)
            finally:
                os.chmod(root / CLAUDE_MD, stat.S_IREAD | stat.S_IWRITE)

    @proves("REQ_INIT_SAFE")
    def test_read_only_original_is_refused(self):
        for rel in (CLAUDE_MD, SETTINGS):
            with self.subTest(rel), Repo() as root:
                write(root / rel, b"{}\n" if rel == SETTINGS else b"mine\n")
                os.chmod(root / rel, stat.S_IREAD)
                try:
                    refused(self, root, "read-only")
                finally:
                    os.chmod(root / rel, stat.S_IREAD | stat.S_IWRITE)

    @proves("REQ_INIT_SAFE")
    @only_on("posix")
    def test_fifo_is_refused(self):
        with Repo() as root:
            os.mkfifo(root / CLAUDE_MD)
            refused(self, root, "not a regular file")

    def race(self, change) -> str:
        with Repo() as root:
            write(root / CLAUDE_MD, b"mine\n")

            def before(rel: str) -> None:
                if rel == CLAUDE_MD:
                    change(root / CLAUDE_MD)
            with mock.patch.object(init_module, "before_move", before):
                with self.assertRaises(init_module.Refused) as caught:
                    run_init(root)
            self.assertEqual(sorted(p.name for p in root.iterdir()), [".git", CLAUDE_MD])
            return str(caught.exception)

    @proves("REQ_INIT_SAFE")
    def test_claude_md_changed_between_validation_and_move_is_refused(self):
        def touch(path: Path) -> None:
            st = path.stat()
            os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + 10**9))

        def swap(path: Path) -> None:
            st = path.stat()
            path.unlink()
            path.write_bytes(b"mine\n")
            os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns))
        self.assertIn("changed after init read it", self.race(touch))
        self.assertIn("changed after init read it", self.race(swap))

    @proves("REQ_INIT_SAFE")
    def test_failed_merge_after_the_append_restores_claude_md(self):
        with Repo() as root:
            write(root / CLAUDE_MD, b"mine\n")
            write(root / SETTINGS, b'{"model": "x"}\n')

            def fail(rel: str) -> None:
                if rel == SETTINGS:
                    raise OSError("the disk is full")
            with mock.patch.object(init_module, "before_move", fail):
                with self.assertRaises(init_module.Refused) as caught:
                    run_init(root)
            self.assertEqual((root / CLAUDE_MD).read_bytes(), b"mine\n")
            self.assertEqual((root / SETTINGS).read_bytes(), b'{"model": "x"}\n')
            self.assertIn(f"restored {CLAUDE_MD}", str(caught.exception))
            self.assertEqual(sorted(p.name for p in root.iterdir()), [".claude", ".git", CLAUDE_MD])

    @proves("REQ_INIT_SAFE")
    def test_restore_that_fails_or_is_refused_reports_the_section(self):
        for how in ("replaced", "touched", "fails"):
            with self.subTest(how), Repo() as root:
                write(root / CLAUDE_MD, b"mine\n")
                write(root / SETTINGS, b'{"model": "x"}\n')
                calls = []

                def after(rel: str) -> None:
                    if rel == CLAUDE_MD and how == "replaced":
                        (root / CLAUDE_MD).unlink()
                        (root / CLAUDE_MD).write_bytes(b"someone else's\n")
                    elif rel == CLAUDE_MD and how == "touched":
                        st = (root / CLAUDE_MD).stat()
                        os.utime(root / CLAUDE_MD, ns=(st.st_atime_ns, st.st_mtime_ns + 10**9))

                def before(rel: str) -> None:
                    calls.append(rel)
                    if rel == SETTINGS:
                        raise OSError("the disk is full")
                    if rel == CLAUDE_MD and how == "fails" and calls.count(CLAUDE_MD) == 2:
                        raise OSError("the restore failed")
                with mock.patch.object(init_module, "after_move", after), \
                        mock.patch.object(init_module, "before_move", before):
                    with self.assertRaises(init_module.Refused) as caught:
                        run_init(root)
                self.assertIn(f"{CLAUDE_MD} still holds the section", str(caught.exception))
                if how == "replaced":
                    self.assertEqual((root / CLAUDE_MD).read_bytes(), b"someone else's\n")
                self.assertFalse((root / (CLAUDE_MD + NEW)).exists())

    @proves("REQ_INIT_SAFE")
    def test_cli_exits_non_zero_when_the_restore_fails(self):
        with Repo() as root, mock.patch.object(init_module, "corpus_root", return_value=root):
            write(root / CLAUDE_MD, b"mine\n")
            write(root / SETTINGS, b'{"model": "x"}\n')

            def before(rel: str) -> None:
                if rel == SETTINGS:
                    raise OSError("the disk is full")

            def after(rel: str) -> None:
                if rel == CLAUDE_MD:
                    (root / CLAUDE_MD).unlink()
                    (root / CLAUDE_MD).write_bytes(b"someone else's\n")
            with mock.patch.object(init_module, "after_move", after), \
                    mock.patch.object(init_module, "before_move", before), \
                    mock.patch("sys.stderr"):
                code = init_module.main(["--codeowner", "@someone", "--wheel-url", URL,
                                         "--wheel-sha256", SHA])
            self.assertNotEqual(code, 0)


class ModeBits(unittest.TestCase):
    @proves("REQ_INIT_SAFE")
    @only_on("posix")
    def test_changed_files_keep_their_mode_and_new_files_start_0600(self):
        modes = []
        real_fchmod = os.fchmod

        def watch(fd, mode):
            modes.append(stat.S_IMODE(os.fstat(fd).st_mode))
            return real_fchmod(fd, mode)
        with Repo() as root:
            write(root / CLAUDE_MD, b"mine\n")
            write(root / SETTINGS, b"{}\n")
            os.chmod(root / CLAUDE_MD, 0o640)
            os.chmod(root / SETTINGS, 0o604)
            with mock.patch("os.fchmod", watch):
                run_init(root)
            self.assertEqual(stat.S_IMODE((root / CLAUDE_MD).stat().st_mode), 0o640)
            self.assertEqual(stat.S_IMODE((root / SETTINGS).stat().st_mode), 0o604)
        self.assertEqual(modes, [0o600, 0o600], "each new file starts at 0600")

    @proves("REQ_INIT_SAFE")
    @only_on("posix")
    def test_failed_merge_restores_claude_md_mode_bits(self):
        with Repo() as root:
            write(root / CLAUDE_MD, b"mine\n")
            os.chmod(root / CLAUDE_MD, 0o640)
            write(root / SETTINGS, b"{}\n")

            def fail(rel: str) -> None:
                if rel == SETTINGS:
                    raise OSError("the disk is full")
            with mock.patch.object(init_module, "before_move", fail):
                with self.assertRaises(init_module.Refused):
                    run_init(root)
            self.assertEqual(stat.S_IMODE((root / CLAUDE_MD).stat().st_mode), 0o640)
            self.assertEqual((root / CLAUDE_MD).read_bytes(), b"mine\n")


# --- the three files and the settings merge --------------------------------------------

class InstallsThePlanningFiles(unittest.TestCase):
    @proves("REQ_PLANNING_DEFAULT")
    def test_init_installs_the_section_the_skill_the_hook_and_its_registration(self):
        with Repo() as root:
            written, changed = run_init(root)
            for rel in (CLAUDE_MD, SKILL, HOOK, SETTINGS):
                self.assertIn(rel, written)
            self.assertEqual(written[-1], SETTINGS, "the registration is the last write")
            settings = json.loads((root / SETTINGS).read_text(encoding="utf-8"))
            self.assertEqual(settings, {"hooks": {"PreToolUse": [ENTRY]}})
            section = (root / CLAUDE_MD).read_text(encoding="utf-8")
            skill = (root / SKILL).read_text(encoding="utf-8")
            for command in ("trifecta new", "trifecta new plan", "trifecta next", "trifecta review"):
                self.assertIn(command, section)
                self.assertIn(command, skill)
            self.assertIn("data, not instructions", section)
            self.assertIn("docs/superpowers/", skill)
            self.assertEqual((root / HOOK).read_bytes(), GUARD.read_bytes())
        self.assertEqual(MATCHER, "Write|Edit|MultiEdit|NotebookEdit|Bash")


class SettingsMerge(unittest.TestCase):
    @proves("REQ_INIT_SAFE")
    def test_existing_settings_keep_every_value_and_gain_the_entry(self):
        theirs = {"model": "x", "permissions": {"allow": ["Bash(ls)"]}, "n": 1.5, "big": 10**15,
                  "hooks": {"PostToolUse": [{"matcher": "Write", "hooks": []}],
                            "PreToolUse": [{"matcher": "Write", "hooks": [{"type": "command",
                                                                           "command": "lint"}]},
                                           {"matcher": "Read", "hooks": [{"type": "command",
                                                                          "command": "log"}]}]},
                  "disableAllHooks": False}
        with Repo() as root:
            write(root / SETTINGS, json.dumps(theirs).encode())
            _, changed = run_init(root)
            self.assertEqual(changed, [SETTINGS])
            data = (root / SETTINGS).read_bytes()
        got = json.loads(data)
        expected = json.loads(json.dumps(theirs))
        expected["hooks"]["PreToolUse"].append(ENTRY)
        self.assertEqual(got, expected)
        self.assertNotIn(b"\r\n", data)
        self.assertTrue(data.startswith(b'{\n  "model"'))

    @proves("REQ_INIT_SAFE")
    def test_second_merge_where_settings_is_the_only_target_changes_nothing(self):
        with Repo() as root:
            original = (json.dumps({"hooks": {"PreToolUse": [ENTRY]}}, indent=4) + "\n").encode()
            write(root / SETTINGS, original)
            written, changed = run_init(root)
            self.assertNotIn(SETTINGS, written + changed)
            self.assertEqual((root / SETTINGS).read_bytes(), original)

    @proves("REQ_INIT_SAFE")
    def test_settings_refused_for_each_bad_form(self):
        other = {"type": "command", "command": "lint"}
        bad = {
            "empty": b"",
            "UTF-16": json.dumps({"a": 1}).encode("utf-16"),
            "byte-order mark": b"\xef\xbb\xbf{}",
            "comment": b'{"a": 1 // no\n}',
            "NaN": b'{"a": NaN}',
            "Infinity": b'{"a": Infinity}',
            "1e400": b'{"a": 1e400}',
            "400-digit integer": b'{"a": ' + b"9" * 400 + b"}",
            "repeated key": b'{"a": 1, "a": 2}',
            "not an object": b"[]",
            "entry not an object": json.dumps({"hooks": {"PreToolUse": [1]}}).encode(),
            "entry hooks not an array": json.dumps({"hooks": {"PreToolUse": [{"hooks": {}}]}}).encode(),
            "disableAllHooks true": b'{"disableAllHooks": true}',
            "disableAllHooks 1": b'{"disableAllHooks": 1}',
            'disableAllHooks "true"': b'{"disableAllHooks": "true"}',
            "hooks not an object": b'{"hooks": []}',
            "PreToolUse not an array": b'{"hooks": {"PreToolUse": {}}}',
            "lone surrogate": b'{"a": "\\ud800"}',
        }
        for field, value in (("async", True), ("timeout", 5)):
            entry = json.loads(json.dumps(ENTRY))
            entry["hooks"][0][field] = value
            bad[f"init's command with {field}"] = json.dumps({"hooks": {"PreToolUse": [entry]}}).encode()
        entry = json.loads(json.dumps(ENTRY))
        entry["matcher"] = "Write"
        bad["init's command with another matcher"] = json.dumps({"hooks": {"PreToolUse": [entry]}}).encode()
        entry = json.loads(json.dumps(ENTRY))
        entry["hooks"].append(other)
        bad["init's command beside a second handler"] = json.dumps({"hooks": {"PreToolUse": [entry]}}).encode()
        for name, data in bad.items():
            with self.subTest(name), Repo() as root:
                write(root / SETTINGS, data)
                refused(self, root, SETTINGS)

    @proves("REQ_INIT_SAFE")
    def test_settings_link_leftover_and_linked_directory_are_refused(self):
        with Repo() as root, tempfile.TemporaryDirectory() as outside:
            write(Path(outside) / "settings.json", b"{}")
            (root / ".claude").mkdir()
            os.symlink(Path(outside) / "settings.json", root / SETTINGS)
            refused(self, root, "link")
        with Repo() as root:
            write(root / SETTINGS, b"{}")
            write(root / (SETTINGS + NEW), b"left")
            refused(self, root, "left from an earlier run")
        with Repo() as root, tempfile.TemporaryDirectory() as outside:
            write(Path(outside) / "settings.json", b"{}")
            os.symlink(outside, root / ".claude", target_is_directory=True)
            refused(self, root, ".claude/ is a link")
            self.assertEqual(os.listdir(outside), ["settings.json"])

    @proves("REQ_INIT_SAFE")
    @only_on("nt")
    def test_settings_in_a_junctioned_directory_is_refused(self):
        import _winapi
        with Repo() as root, tempfile.TemporaryDirectory() as outside:
            write(Path(outside) / "settings.json", b"{}")
            _winapi.CreateJunction(outside, str(root / ".claude"))
            refused(self, root, ".claude/ is a link")

    @proves("REQ_INIT_SAFE")
    @only_on("posix")
    def test_settings_fifo_is_refused(self):
        with Repo() as root:
            (root / ".claude").mkdir()
            os.mkfifo(root / SETTINGS)
            refused(self, root, "not a regular file")

    def settings_race(self, change, junction: bool = False) -> None:
        with Repo() as root, tempfile.TemporaryDirectory() as outside:
            write(root / SETTINGS, b'{"model": "x"}\n')
            write(Path(outside) / "settings.json", b"theirs")

            def before(rel: str) -> None:
                if rel == SETTINGS:
                    change(root, outside)
            with mock.patch.object(init_module, "before_move", before):
                with self.assertRaises(init_module.Refused):
                    run_init(root)
            self.assertEqual((Path(outside) / "settings.json").read_bytes(), b"theirs")
            self.assertEqual(sorted(os.listdir(outside)), ["settings.json"])
            self.assertFalse((root / CLAUDE_MD).exists())

    @proves("REQ_INIT_SAFE")
    def test_settings_changed_or_its_directory_swapped_before_the_move_is_refused(self):
        def touch(root, outside):
            p = root / SETTINGS
            st = p.stat()
            os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns + 10**9))

        def replace(root, outside):
            p = root / SETTINGS
            st = p.stat()
            p.unlink()
            p.write_bytes(b'{"model": "x"}\n')
            os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))

        def link(root, outside):
            (root / ".claude").rename(root / ".claude-moved")
            os.symlink(outside, root / ".claude", target_is_directory=True)
        for change in (touch, replace, link):
            with self.subTest(change.__name__):
                self.settings_race(change)

    @proves("REQ_INIT_SAFE")
    @only_on("nt")
    def test_settings_directory_swapped_for_a_junction_before_the_move_is_refused(self):
        import _winapi

        def junction(root, outside):
            (root / ".claude").rename(root / ".claude-moved")
            _winapi.CreateJunction(outside, str(root / ".claude"))
        self.settings_race(junction)

    @proves("REQ_INIT_SAFE")
    def test_failed_merge_leaves_settings_and_removes_what_the_run_created(self):
        with Repo() as root:
            original = b'{"model": "x"}\n'
            write(root / SETTINGS, original)
            before = snapshot(root)

            def fail(rel: str) -> None:
                if rel == SETTINGS:
                    raise OSError("the disk is full")
            with mock.patch.object(init_module, "before_move", fail):
                with self.assertRaises(init_module.Refused):
                    run_init(root)
            self.assertEqual(snapshot(root), before)


def git_bash() -> str:
    """The bash a hook runs under: Git for Windows' on nt, never the System32 launcher."""
    if os.name == "nt":
        git = shutil.which("git")
        if git:
            for base in Path(git).resolve().parents:
                candidate = base / "bin" / "bash.exe"
                if candidate.is_file():
                    return str(candidate)
        raise AssertionError("no Git for Windows bash next to git")
    found = shutil.which("bash")
    if not found:
        raise AssertionError("no bash on PATH")
    return found


class HookCommand(unittest.TestCase):
    @proves("REQ_INIT_SAFE", "REQ_HOOK_FAILS_CLOSED")
    def test_command_with_a_space_in_the_path_and_no_interpreter_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve() / "my repo"
            root.mkdir()
            subprocess.run(["git", "init", "-q", str(root)], check=True)
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


# --- the hook --------------------------------------------------------------------------

def hook(root: Path, call: object, raw: str | None = None, env: dict | None = None) -> int:
    data = raw if raw is not None else json.dumps(call)
    done = subprocess.run([sys.executable, str(GUARD)], input=data, capture_output=True,
                          encoding="utf-8", env={**os.environ, "CLAUDE_PROJECT_DIR": str(root),
                                                 **(env or {})})
    return done.returncode


def write_call(path: str, tool: str = "Write") -> dict:
    key = "notebook_path" if tool == "NotebookEdit" else "file_path"
    return {"tool_name": tool, "tool_input": {key: path}}


class Hook(unittest.TestCase):
    @proves("REQ_HOOK_FAILS_CLOSED", "REQ_PLANNING_DEFAULT")
    def test_refuses_writes_under_docs_superpowers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            (root / "docs" / "superpowers").mkdir(parents=True)
            (root / "docs" / "rfcs").mkdir()
            for path in ("docs/superpowers/x.md", "docs/rfcs/../superpowers/x.md",
                         str(root / "docs" / "superpowers" / "x.md"), "docs\\superpowers\\x.md",
                         "Docs/Superpowers/x.md", "docs/superpowers./x.md",
                         "docs/superpowers /x.md"):
                with self.subTest(path):
                    self.assertEqual(hook(root, write_call(path)), 2)
            for tool in ("Edit", "MultiEdit", "NotebookEdit"):
                with self.subTest(tool):
                    self.assertEqual(hook(root, write_call("docs/superpowers/x.md", tool)), 2)
            for command in ("echo x > docs/superpowers/x.md", "cp a DOCS\\SUPERPOWERS\\x.md",
                            "tee 'docs/superpowers/x.md'"):
                with self.subTest(command):
                    self.assertEqual(hook(root, {"tool_name": "Bash",
                                                 "tool_input": {"command": command}}), 2)
            self.assertEqual(hook(root, write_call("docs/rfcs/x.md")), 0)
            self.assertEqual(hook(root, {"tool_name": "Bash", "tool_input": {"command": "ls docs"}}), 0)

    @proves("REQ_HOOK_FAILS_CLOSED")
    def test_stream_names_share_paths_and_the_sessions_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            root = base / "proj"
            (root / "docs").mkdir(parents=True)
            for path in ("docs/superpowers::$INDEX_ALLOCATION/x.md",
                         "docs\\superpowers:$I30:$INDEX_ALLOCATION\\x.md",
                         "docs/superpowers:stream"):
                with self.subTest(path):
                    self.assertEqual(hook(root, write_call(path)), 2)
            home = {"HOME": str(base), "USERPROFILE": str(base)}
            self.assertEqual(hook(root, write_call("~/proj/docs/superpowers/x.md"), env=home), 2)
            relative = {**write_call("superpowers/x.md"), "cwd": str(root / "docs")}
            self.assertEqual(hook(root, relative), 2)
            (base / "docs" / "superpowers").mkdir(parents=True)
            outside = str(base / "docs" / "superpowers" / "a.md")
            self.assertEqual(hook(root, write_call(outside)), 0)

    @proves("REQ_HOOK_FAILS_CLOSED")
    @only_on("nt")
    def test_refuses_a_share_path_it_cannot_relate_to_the_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            share = "\\\\localhost\\c$\\work\\docs\\superpowers\\y.md"
            self.assertEqual(hook(Path(tmp).resolve(), write_call(share)), 2)

    @proves("REQ_HOOK_FAILS_CLOSED")
    def test_resolves_a_link_into_docs_superpowers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            (root / "docs" / "superpowers").mkdir(parents=True)
            os.symlink(root / "docs" / "superpowers", root / "notes", target_is_directory=True)
            self.assertEqual(hook(root, write_call("notes/x.md")), 2)

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

    @proves("REQ_HOOK_FAILS_CLOSED")
    def test_refuses_input_it_cannot_read_and_any_exception(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            for raw in ("not json", "[]", '{"tool_name": "Write"}',
                        '{"tool_name": "Write", "tool_input": {"file_path": 3}}'):
                with self.subTest(raw):
                    self.assertEqual(hook(root, None, raw=raw), 2)
            shadow = root / "shadow"
            shadow.mkdir()
            (shadow / "json.py").write_text("raise RuntimeError('broken import')\n", encoding="utf-8")
            self.assertEqual(hook(root, write_call("docs/rfcs/x.md"),
                                  env={"PYTHONPATH": str(shadow)}), 2)


if __name__ == "__main__":
    unittest.main()
