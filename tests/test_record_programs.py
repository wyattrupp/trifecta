"""REQ_KNOWN_PROGRAM and REQ_REUSE_SOUND: git and Vale are known programs on the terms
COMP_KNOWN_PROGRAMS states (DEC_0033, DEC_0038).

Each start is judged as the recorder's wrapper of ``_execute_child`` judges it, by a
recorder this process makes and never starts: a start in a stated form is let through
with its inputs recorded, a change to one of them runs the module again, and a start
outside the terms is refused with its reason. The git these tests start on purpose is in
its forms, on directories they made, so this module's own run stays storable.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from trifecta import build, record, store, toolchain
from trifecta.testing import only_on, proves

PACKAGE = Path(record.__file__).resolve().parent
GIT = shutil.which("git")


def recorder(root: Path, made: list[Path]) -> record.Recorder:
    """A recorder this process makes and never starts, holding ``made`` as the
    directories the run made."""
    r = record.Recorder(str(root.parent / "recorder"),
                        {"root": str(root), "recorder": record.__file__, "ignore": []})
    r.created.update(record._norm(str(p)) for p in made)
    return r


def whys(r: record.Recorder) -> list[str]:
    return [reason["why"] for reason in r.reasons]


def manifest_of(r: record.Recorder) -> dict:
    return {"version": record.VERSION, "storable": not r.refused(),
            **{name: dict(getattr(r, name)) for name in record.SECTIONS}}


def final_env(env: dict) -> dict:
    """An environment as the wrapper reads it: names as the system spells them."""
    return {record._name(k): v for k, v in env.items()}


class Tree(unittest.TestCase):
    """A repository, and a directory the run made with a repository and a home in it."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        # The repository and the made directory in places apart, so the made directory's
        # parents are not the repository's.
        self.root = self.tmp / "a" / "root"
        (self.root / "bin").mkdir(parents=True)
        self.made = self.tmp / "b" / "made"
        self.target = self.made / "repo"
        self.home = self.made / "home"
        for path in (self.target, self.home):
            path.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def differs(self, r: record.Recorder, environ: dict) -> str | None:
        return store.mismatch(manifest_of(r), self.root, environ, store.Hashes())


# --- git ---------------------------------------------------------------------------------

class GitTerms(Tree):
    def setUp(self):
        super().setUp()
        self.pins = {"GIT_CEILING_DIRECTORIES": str(self.made), "GIT_CONFIG_NOSYSTEM": "1",
                     "GIT_CONFIG_GLOBAL": "", "HOME": str(self.home),
                     "XDG_CONFIG_HOME": str(self.home / ".config")}
        # As the tests start git: no other GIT_* variable, and none that moves what it or its
        # loader reads (DEC_0049).
        self.base = {k: v for k, v in toolchain.program_env().items()
                     if not k.upper().startswith("GIT_")}
        if os.name == "posix":
            # What loads git on Linux is reached through the system's links, which this
            # module's own recorder would refuse it for reading; the loader's files are
            # test_record_programs_traced's, which runs git under strace.
            for name in ("_elf_interpreter", "_loader_inputs"):
                patcher = mock.patch.object(record, name, return_value=None)
                patcher.start()
                self.addCleanup(patcher.stop)
        # A repository made as the tests make one: git init, in its form.
        subprocess.run(["git", "init", "-q", str(self.target)], check=True,
                       env={**self.base, **self.pins})

    def judge(self, argv: list[str], env: dict | None = None, inited: bool = True,
              r: record.Recorder | None = None, drop=(), shell=False, **terms,
              ) -> tuple[record.Recorder, str | None]:
        r = r or recorder(self.root, [self.made])
        if inited:
            r.git_inits.add(record._norm(str(self.target)))
        given = {**self.base, **self.pins, **(env or {})}
        for name in drop:
            given.pop(name, None)
        final = final_env(given)
        r.start_names = sorted(final)
        why, _ = record._git_start(r, argv, "git", None, final, str(self.root), shell,
                                   **terms)
        return r, why

    def form(self, *rest: str) -> list[str]:
        return ["git", "-C", str(self.target), *(rest or ("ls-files", "-z"))]

    @proves("REQ_KNOWN_PROGRAM")
    def test_git_is_let_through_in_its_forms_on_a_directory_the_run_made(self):
        for form in record.GIT_FORMS:
            with self.subTest(form):
                r, why = self.judge(self.form(*form))
                self.assertIsNone(why)
                self.assertEqual(whys(r), [])
                self.assertTrue(any(os.path.basename(k).lower().startswith("git")
                                    for k in r.programs), r.programs)
                # The made directory's parents and the whole environment are recorded.
                self.assertEqual(r.probes[str(self.made.parent)], "directory")
                self.assertIn(record.NAMES, r.environment)
        fresh = self.made / "fresh"
        fresh.mkdir()
        pins = {**self.pins, "GIT_CEILING_DIRECTORIES": str(self.made)}
        r, why = self.judge(["git", "init", "-q", str(fresh)], pins, inited=False)
        self.assertIsNone(why)
        self.assertIn(record._norm(str(fresh)), r.git_inits)
        # Its template tree is recorded.
        self.assertTrue(any("templates" in k for k in r.listings), r.listings)

    @proves("REQ_KNOWN_PROGRAM", "REQ_REUSE_SOUND")
    def test_a_start_outside_its_terms_is_refused(self):
        args = "runs git with arguments other than its forms"
        code = "runs git with code before it starts or descriptors it inherits"
        target = str(self.target)
        elsewhere = self.tmp / "elsewhere"
        elsewhere.mkdir()
        cases = {
            "-c": (["git", "-c", "core.pager=cat", "-C", target, "ls-files", "-z"], {}, args),
            "-c after -C": (["git", "-C", target, "-c", "a.b=c", "ls-files", "-z"], {}, args),
            "add": (self.form("add", "."), {}, args),
            "commit": (self.form("commit", "-q", "-m", "x"), {}, args),
            "another option": (self.form("ls-files", "-z", "--debug"), {}, args),
            "-C elsewhere": (["git", "-C", str(elsewhere), "ls-files", "-z"], {},
                             "runs git on a directory the run did not make"),
            "this repository": (["git", "-C", str(self.root), "ls-files", "-z"], {},
                                "runs git on this repository"),
            "no ceiling": (self.form(), {"drop": ["GIT_CEILING_DIRECTORIES"]},
                           "runs git without GIT_CEILING_DIRECTORIES at its directory's parent"),
            "another ceiling": (self.form(), {"env": {"GIT_CEILING_DIRECTORIES": str(self.tmp)}},
                                "runs git without GIT_CEILING_DIRECTORIES at its directory's "
                                "parent"),
            "no NOSYSTEM": (self.form(), {"drop": ["GIT_CONFIG_NOSYSTEM"]},
                            "runs git without GIT_CONFIG_NOSYSTEM=1"),
            "no GLOBAL": (self.form(), {"drop": ["GIT_CONFIG_GLOBAL"]},
                          "runs git without an empty GIT_CONFIG_GLOBAL"),
            "a GLOBAL": (self.form(), {"env": {"GIT_CONFIG_GLOBAL": str(self.home / "c")}},
                         "runs git without an empty GIT_CONFIG_GLOBAL"),
            "no HOME": (self.form(), {"drop": ["HOME"]},
                        "runs git without HOME on a directory the run made"),
            "HOME elsewhere": (self.form(), {"env": {"HOME": str(elsewhere)}},
                               "runs git without HOME on a directory the run made"),
            "no XDG_CONFIG_HOME": (self.form(), {"drop": ["XDG_CONFIG_HOME"]},
                                   "runs git without XDG_CONFIG_HOME on a directory the run "
                                   "made"),
            "XDG_CONFIG_HOME elsewhere": (self.form(), {"env": {"XDG_CONFIG_HOME": str(elsewhere)}},
                                          "runs git without XDG_CONFIG_HOME on a directory "
                                          "the run made"),
            "another GIT_ variable": (self.form(), {"env": {"GIT_DIR": str(self.target)}},
                                      f"runs git with {record._name('GIT_DIR')} set"),
            "LD_PRELOAD": (self.form(), {"env": {"LD_PRELOAD": "x.so"}},
                           "runs git with LD_PRELOAD set, which moves what it reads"),
            "before its init": (self.form(), {"inited": False},
                                "runs git on a directory before its init"),
            "init again": (["git", "init", "-q", target], {},
                           "runs git init where a repository is already"),
            "a shell": (self.form(), {"terms": {"shell": True}}, "runs git through a shell"),
            "code before it starts": (self.form(), {"terms": {"preexec_fn": print}}, code),
            "every descriptor": (self.form(), {"terms": {"close_fds": False}}, code),
            "descriptors": (self.form(), {"terms": {"pass_fds": (3,)}}, code),
        }
        for name, (argv, given, expected) in cases.items():
            with self.subTest(name):
                r, why = self.judge(argv, env=given.get("env"), drop=given.get("drop", ()),
                                    inited=given.get("inited", True),
                                    **given.get("terms", {}))
                self.assertEqual(why, expected)
                self.assertEqual(r.programs, {})

    @proves("REQ_KNOWN_PROGRAM", "REQ_REUSE_SOUND")
    def test_a_repository_that_would_run_or_read_further_is_refused(self):
        config = (self.target / ".git" / "config").read_text(encoding="utf-8")

        def with_config(extra: str):
            def change(git: Path):
                (git / "config").write_text(config + extra, encoding="utf-8")
            return change

        def plant(rel: str, text: str = "x"):
            def change(git: Path):
                (git / rel).parent.mkdir(parents=True, exist_ok=True)
                (git / rel).write_text(text, encoding="utf-8")
            return change

        def fresh(name: str) -> Path:
            """A repository of its own, made as the tests make one."""
            self.target = self.made / name
            self.target.mkdir()
            subprocess.run(["git", "init", "-q", str(self.target)], check=True,
                           env={**self.base, **self.pins})
            return self.target / ".git"

        cases = {
            "alternates": (plant("objects/info/alternates", "/elsewhere\n"),
                           "runs git on a repository with alternates"),
            "commondir": (plant("commondir", ".."), "runs git on a repository with commondir"),
            "a hook": (plant("hooks/pre-commit", "#!/bin/sh\n"),
                       "runs git on a repository with a hook"),
            "include.path": (with_config("[include]\n\tpath = /elsewhere/config\n"),
                             "runs git on a repository whose configuration sets include.path"),
            "includeIf": (with_config('[includeIf "gitdir:/x/"]\n\tpath = /elsewhere\n'),
                          "runs git on a repository whose configuration sets "
                          "includeif.gitdir:/x/.path"),
            "a key init does not write": (with_config("[core]\n\tfsmonitor = true\n"),
                                          "runs git on a repository whose configuration sets "
                                          "core.fsmonitor"),
            "a clean filter": (with_config('[filter "lfs"]\n\tclean = git-lfs clean\n'),
                               "runs git on a repository whose configuration sets "
                               "filter.lfs.clean"),
            "a line it cannot read": (with_config("[core]\n\tbare = false \\\n\ttrue\n"),
                                      "runs git on a repository whose configuration it "
                                      "cannot read"),
        }
        for i, (name, (change, expected)) in enumerate(cases.items()):
            with self.subTest(name):
                change(fresh(f"case{i}"))
                _, why = self.judge(self.form())
                self.assertEqual(why, expected)
        self.target = self.made / "gitfile"
        self.target.mkdir()
        (self.target / ".git").write_text("gitdir: /elsewhere\n", encoding="utf-8")
        _, why = self.judge(self.form())
        self.assertEqual(why, "runs git on a repository whose .git is not a directory")
        # user.name, which trifecta new reads, is allowed.
        git = fresh("named")
        (git / "config").write_text(config + "[user]\n\tname = someone\n", encoding="utf-8")
        _, why = self.judge(self.form("config", "user.name"))
        self.assertIsNone(why)

    @proves("REQ_KNOWN_PROGRAM", "REQ_REUSE_SOUND")
    def test_a_git_planted_on_path_reruns(self):
        planted = self.root / "planted"
        planted.mkdir()
        real = os.path.dirname(GIT)
        path = f"{planted}{os.pathsep}{real}"
        environ = {**{k: v for k, v in self.base.items() if k.upper() != "PATH"},
                   **self.pins, "PATH": path}
        with mock.patch.object(record, "_environment",
                               return_value=list(final_env(environ).items())):
            r, why = self.judge(self.form(), env={"PATH": path})
        self.assertIsNone(why)
        name = "planted/git.exe" if os.name == "nt" else "planted/git"
        self.assertEqual(r.probes[name], "absent")
        self.assertIsNone(self.differs(r, environ))
        shutil.copy(GIT, self.root / name)
        self.assertEqual(self.differs(r, environ), f"path {name}")
        # And the next start, which would run the planted git, is refused.
        with mock.patch.object(record, "_environment",
                               return_value=list(final_env(environ).items())):
            _, why = self.judge(self.form(), env={"PATH": path})
        self.assertEqual(why, "runs a git under the repository or one the run made")

    @proves("REQ_KNOWN_PROGRAM", "REQ_REUSE_SOUND")
    def test_what_git_reads_is_the_runs_to_change_only_once_git_is_reaped(self):
        r, why = self.judge(self.form())
        self.assertIsNone(why)
        git = object()  # the Popen the wrapper holds as running
        r.started_known(git, "git", r.local.roots)
        changed = "changes what git reads while it runs"
        # A path of the run's own outside what git reads is the run's to change.
        r.wrote(str(self.made / "other.txt"))
        self.assertNotIn(changed, whys(r))
        # Its configuration, as the repro appended core.fsmonitor to it, is not.
        r.wrote(str(self.target / ".git" / "config"))
        self.assertIn(changed, whys(r))
        for path in (self.home / ".config" / "git" / "ignore", self.target / "x.txt"):
            with self.subTest(path.name):
                r2, _ = self.judge(self.form())
                r2.started_known(git, "git", r2.local.roots)
                r2.wrote(str(path))
                self.assertIn(changed, whys(r2))
        # Once reaped, it is the run's again; a run that ends before reaping is refused.
        r, _ = self.judge(self.form())
        r.started_known(git, "git", r.local.roots)
        self.assertIn("starts git and does not wait for it",
                      [x["why"] for x in r.manifest().get("reasons", [])])
        r, _ = self.judge(self.form())
        r.started_known(git, "git", r.local.roots)
        r.reaped(git)
        r.wrote(str(self.target / ".git" / "config"))
        self.assertEqual(whys(r), [])
        self.assertTrue(r.manifest()["storable"])

    @proves("REQ_KNOWN_PROGRAM", "REQ_REUSE_SOUND")
    def test_a_repository_or_gitdir_file_inside_the_worktree_is_refused(self):
        for name, plant in (("a repository", lambda d: d.mkdir()),
                            ("a gitdir file", lambda d: d.write_text(
                                "gitdir: /elsewhere\n", encoding="utf-8"))):
            with self.subTest(name):
                inner = self.target / "sub" / name.replace(" ", "-")
                inner.mkdir(parents=True)
                plant(inner / ".git")
                _, why = self.judge(self.form())
                self.assertEqual(why, "runs git on a worktree that holds another .git")
                shutil.rmtree(self.target / "sub")
        _, why = self.judge(self.form())
        self.assertIsNone(why)

    @proves("REQ_KNOWN_PROGRAM")
    def test_the_check_starts_git_and_vale_without_the_variables_that_move_reads(self):
        moving = {name: "x" for name in record.MOVING}
        with mock.patch.dict(os.environ, moving):
            env = toolchain.program_env()
        self.assertFalse({record._name(k) for k in env} & {record._name(m) for m in moving})
        # A start that still holds one is refused.
        for name in record.MOVING:
            with self.subTest(name):
                _, why = self.judge(self.form(), env={name: "x"})
                self.assertEqual(why, f"runs git with {record._name(name)} set, which "
                                      f"moves what it reads")

    @proves("REQ_KNOWN_PROGRAM", "REQ_REUSE_SOUND")
    def test_a_change_to_tz_or_an_ld_variable_reruns(self):
        here = {**self.base, "TZ": "UTC", "LD_BIND_NOW": "1"}
        with mock.patch.object(record, "_environment",
                               return_value=list(final_env(here).items())):
            r = recorder(self.root, [self.made])
            r.git_inits.add(record._norm(str(self.target)))
            final = final_env({**here, **self.pins})
            r.start_names = sorted(final_env(here))
            # Started with env=None: the pins are the run's own, set before the start.
            r.env_set.update(final_env(self.pins))
            why, _ = record._git_start(r, self.form(), "git", None, final, str(self.root),
                                       False)
        self.assertIsNone(why)
        environ = {k: v for k, v in here.items() if k.upper() not in record.OWN}
        self.assertIsNone(self.differs(r, environ))
        self.assertEqual(self.differs(r, {**environ, "TZ": "Europe/Paris"}),
                         f"variable {record._name('TZ')}")
        self.assertEqual(self.differs(r, {**environ, "LD_BIND_NOW": ""}),
                         f"variable {record._name('LD_BIND_NOW')}")

    @proves("REQ_KNOWN_PROGRAM", "REQ_REUSE_SOUND")
    def test_a_change_to_git_reruns(self):
        r, why = self.judge(self.form())
        self.assertIsNone(why)
        key = next(k for k in r.programs if os.path.basename(k).lower().startswith("git"))
        manifest = manifest_of(r)
        manifest["programs"][key] = "0" * 64
        self.assertEqual(store.mismatch(manifest, self.root, {}, store.Hashes()),
                         f"program {key}")


# --- Vale --------------------------------------------------------------------------------

class ValeTerms(Tree):
    def setUp(self):
        super().setUp()
        self.vale = self.root / "bin" / ("vale.exe" if os.name == "nt" else "vale")
        if os.name == "nt":
            # A small program the system can start, standing for Vale: what is judged is
            # its hash against the pin, not what it does.
            shutil.copy(os.path.join(os.environ.get("SYSTEMROOT", "C:\\Windows"),
                                     "System32", "where.exe"), self.vale)
        else:
            from tests.test_record_trace import elf
            elf(self.vale)
        self.digest = record.file_hash(str(self.vale))
        # The toolchain file the pins are read from, beside a recorder in the repository.
        self.package = self.root / "src" / "trifecta"
        self.package.mkdir(parents=True)
        self.write_pins(self.digest)
        build_dir = self.made / "build"
        shutil.copytree(PACKAGE / "vale", build_dir / "vale" / "vale")
        shutil.copytree(PACKAGE / "styles", build_dir / "vale" / "styles")
        (build_dir / "vale" / "styles" / "TrifectaGenerated").mkdir()
        self.lint = build_dir / "lint" / "rfcs"
        self.lint.mkdir(parents=True)
        (self.lint / "a.html").write_text("<p>a</p>", encoding="utf-8")
        self.config = build_dir / "vale" / "vale" / "prose.ini"

    def write_pins(self, *digests: str) -> None:
        key = {"linux": "linux-x86_64", "darwin": "macos-arm64",
               "win32": "windows-x86_64"}[sys.platform if sys.platform != "cygwin" else "win32"]
        lines = "".join(f'    "{key}": "{d}",\n' for d in digests)
        (self.package / "toolchain.py").write_text(
            f"VALE_BINARIES = {{\n{lines}}}\n", encoding="utf-8")

    def recorder(self) -> record.Recorder:
        r = recorder(self.root, [self.made])
        record.take_pins(r, str(self.package / "record.py"))
        return r

    def form(self, config: Path | None = None, *dirs: Path) -> list[str]:
        return [str(self.vale), f"--config={config or self.config}", *record.VALE_FORM,
                *(str(d) for d in (dirs or (self.lint,)))]

    def judge(self, argv: list[str], r: record.Recorder | None = None, env=None,
              cwd: Path | None = None, **terms) -> tuple[record.Recorder, str | None]:
        r = r or self.recorder()
        given = {k: v for k, v in toolchain.program_env().items()
                 if k.upper() != "TERM" and not k.upper().startswith("VALE_")}
        final = final_env({**given, **(env or {})})
        r.start_names = sorted(final)
        why, _ = record._vale_start(r, argv, argv[0], None, final, str(cwd or self.target),
                                    terms.pop("shell", False), **terms)
        return r, why

    @proves("REQ_KNOWN_PROGRAM")
    def test_vale_is_let_through_in_its_two_forms_by_its_pin(self):
        for argv in (self.form(), [str(self.vale), "--version"]):
            with self.subTest(argv[1]):
                r, why = self.judge(argv)
                self.assertIsNone(why)
                self.assertEqual(whys(r), [])
                self.assertEqual(r.programs[f"bin/{self.vale.name}"], self.digest)
                self.assertEqual(r.files["src/trifecta/toolchain.py"],
                                 record.file_hash(str(self.package / "toolchain.py")))
                # Each configuration Vale looks for above its working directory is probed.
                self.assertEqual(r.probes[str(self.made.parent / ".vale.ini")], "absent")

    @proves("REQ_KNOWN_PROGRAM", "REQ_REUSE_SOUND")
    def test_the_pin_is_the_packages_as_the_run_began(self):
        r = self.recorder()
        # Rewriting the pin's file during the run changes nothing.
        self.write_pins("0" * 64)
        _, why = self.judge(self.form(), r)
        self.assertIsNone(why)
        # And a change to the pin's file runs the module again.
        self.assertEqual(self.differs(r, {}), "file src/trifecta/toolchain.py")

    @proves("REQ_KNOWN_PROGRAM", "REQ_REUSE_SOUND")
    def test_only_the_pinned_binary_is_let_through_whatever_its_stamp(self):
        stamp = self.root / "bin" / ".vale-stamp-x"
        pinned = self.vale.read_bytes()
        stamp.write_text("3.13.0 " + "a" * 64 + "\n", encoding="utf-8")
        with open(self.vale, "ab") as f:
            f.write(b"\0")
        _, why = self.judge(self.form())
        self.assertEqual(why, "runs a vale whose SHA-256 is not the toolchain's pin")
        self.vale.write_bytes(pinned)
        for name, text in (("no stamp", None), ("a wrong stamp", "0.0.0 x\n")):
            with self.subTest(name):
                stamp.unlink(missing_ok=True)
                if text is not None:
                    stamp.write_text(text, encoding="utf-8")
                _, why = self.judge(self.form())
                self.assertIsNone(why)
        r, _ = self.judge(self.form())
        with open(self.vale, "ab") as f:
            f.write(b"\0")
        self.assertEqual(self.differs(r, {}), f"program bin/{self.vale.name}")

    @proves("REQ_KNOWN_PROGRAM", "REQ_REUSE_SOUND")
    def test_a_start_outside_its_terms_is_refused(self):
        args = "runs vale with arguments other than its forms"
        code = "runs vale with code before it starts or descriptors it inherits"
        vale = str(self.vale)
        rest = [str(self.lint)]
        config = f"--config={self.config}"
        outside = self.root / "outside.ini"
        outside.write_text(self.config.read_text(encoding="utf-8"), encoding="utf-8")
        elsewhere = self.tmp / "elsewhere"
        elsewhere.mkdir()
        cases = {
            "sync": ([vale, "sync"], {}, args),
            "no --no-global": ([vale, config, "--output=line", "--no-exit", *rest], {}, args),
            "another option": ([vale, config, *record.VALE_FORM, "--glob=*", *rest], {}, args),
            "a shell": (self.form(), {}, "runs vale through a shell", {"shell": True}),
            "code before it starts": (self.form(), {}, code, {"preexec_fn": print}),
            "every descriptor": (self.form(), {}, code, {"close_fds": False}),
            "descriptors": (self.form(), {}, code, {"pass_fds": (3,)}),
            "LD_LIBRARY_PATH": (self.form(), {"LD_LIBRARY_PATH": "/usr/local/lib"},
                                f"runs vale with {record._name('LD_LIBRARY_PATH')} set, which "
                                f"moves what it reads"),
            "another output": ([vale, config, "--no-global", "--output=JSON", "--no-exit",
                                *rest], {}, args),
            "--version and more": ([vale, "--version", "--no-global"], {}, args),
            "another vale": ([str(self.made / "vale"), "--version"], {},
                             "runs a vale that is neither bin/vale nor the one TRIFECTA_VALE "
                             "names"),
            "VALE_CONFIG_PATH": (self.form(), {"VALE_CONFIG_PATH": str(outside)},
                                 f"runs vale with {record._name('VALE_CONFIG_PATH')} set"),
            "VALE_STYLES_PATH": (self.form(), {"VALE_STYLES_PATH": str(elsewhere)},
                                 f"runs vale with {record._name('VALE_STYLES_PATH')} set"),
            "TERM": (self.form(), {"TERM": "xterm"}, "runs vale with TERM set"),
            "a config outside": (self.form(outside), {},
                                 "runs vale with --config outside a directory the run made"),
            "a directory outside": (self.form(None, elsewhere), {},
                                    "runs vale on a directory outside the one the run made"),
        }
        for name, (argv, env, expected, *terms) in cases.items():
            with self.subTest(name):
                r, why = self.judge(argv, env=env, **(terms[0] if terms else {}))
                self.assertEqual(why, expected)
                self.assertEqual(r.programs, {})

    @proves("REQ_KNOWN_PROGRAM", "REQ_REUSE_SOUND")
    def test_a_configuration_outside_the_list_is_refused(self):
        text = self.config.read_text(encoding="utf-8")
        styles = self.config.parent.parent / "styles"
        written = "runs vale with a StylesPath it may not read as written"
        cases = {
            "Packages": (text.replace("MinAlertLevel", "Packages = Google\nMinAlertLevel"),
                         "runs vale with a configuration that sets Packages"),
            "StylesPath outside": (text.replace("StylesPath = ../styles", "StylesPath = " + (
                os.path.relpath(self.root, self.config.parent).replace(os.sep, "/"))),
                                   "runs vale with a StylesPath outside the directory the run "
                                   "made"),
            "a vocabulary outside": (text.replace("MinAlertLevel", "Vocab = ..\nMinAlertLevel"),
                                     "runs vale with a vocabulary outside the directory the "
                                     "run made"),
            "a formats section": (text + "\n[formats]\nmdx = md\n",
                                  "runs vale with a [formats] section"),
            "StylesPath in quotes": (text.replace("StylesPath = ../styles",
                                                  'StylesPath = "/elsewhere"'), written),
            "StylesPath in backticks": (text.replace("StylesPath = ../styles",
                                                     "StylesPath = `/elsewhere`"), written),
            "StylesPath with a ; comment": (text.replace("StylesPath = ../styles",
                                                         "StylesPath = ../styles ; x"),
                                            written),
            "StylesPath with a # comment": (text.replace("StylesPath = ../styles",
                                                         "StylesPath = ../styles # x"),
                                            written),
            "Vocab in quotes": (text.replace("MinAlertLevel", 'Vocab = "x"\nMinAlertLevel'),
                                "runs vale with a Vocab it may not read as written"),
            "a converter": (text + "\n[*.html]\nTransform = x.xsl\n",
                            "runs vale with a configuration that sets Transform"),
            "a style not under StylesPath": (text + "\n[*.html]\nBasedOnStyles = Vale\n",
                                             "runs vale with a style that is not under "
                                             "StylesPath"),
        }
        for name, (changed, expected) in cases.items():
            with self.subTest(name):
                self.config.write_text(changed, encoding="utf-8")
                _, why = self.judge(self.form())
                self.assertEqual(why, expected)
        # A vocabulary under StylesPath is let through.
        words = styles / "config" / "vocabularies" / "Ours"
        words.mkdir(parents=True)
        (words / "accept.txt").write_text("trifecta\n", encoding="utf-8")
        self.config.write_text(text.replace("MinAlertLevel", "Vocab = Ours\nMinAlertLevel"),
                               encoding="utf-8")
        _, why = self.judge(self.form())
        self.assertIsNone(why)
        # A rule that extends one that reads a file or runs a script is refused.
        (styles / "Trifecta" / "Spell.yml").write_text(
            "extends: spelling\nmessage: x\ndicpath: /elsewhere\n", encoding="utf-8")
        _, why = self.judge(self.form())
        self.assertEqual(why, "runs vale with a rule it may not run")

    @proves("REQ_KNOWN_PROGRAM", "REQ_REUSE_SOUND")
    def test_what_vale_reads_is_the_runs_to_change_only_once_vale_is_reaped(self):
        changed = "changes what vale reads while it runs"
        styles = self.config.parent.parent / "styles"
        vale = object()
        for name, change in (
                ("its configuration", lambda r: r.wrote(str(self.config))),
                ("a style", lambda r: r.wrote(str(styles / "Trifecta" / "X.yml"))),
                ("a file it lints", lambda r: r.wrote(str(self.lint / "a.html"))),
                ("its binary", lambda r: r.wrote(str(self.vale))),
                ("the styles moved", lambda r: record._rename(
                    r, (str(styles), str(self.made / "moved")))),
                ("its configuration linked", lambda r: record._hardlink(
                    r, (str(self.config), str(self.made / "alias.ini"))))):
            with self.subTest(name):
                r, why = self.judge(self.form())
                self.assertIsNone(why)
                r.started_known(vale, "vale", r.local.roots)
                change(r)
                self.assertIn(changed, whys(r))
        r, _ = self.judge(self.form())
        r.started_known(vale, "vale", r.local.roots)
        self.assertIn("starts vale and does not wait for it",
                      [x["why"] for x in r.manifest().get("reasons", [])])
        r, _ = self.judge(self.form())
        r.started_known(vale, "vale", r.local.roots)
        r.reaped(vale)
        r.wrote(str(self.config))
        self.assertEqual(whys(r), [])
        self.assertTrue(r.manifest()["storable"])

    @proves("REQ_KNOWN_PROGRAM", "REQ_REUSE_SOUND")
    @only_on("posix")
    def test_a_styles_path_through_a_link_to_outside_is_refused(self):
        # A directory in the build directory that links to one outside it: Vale cleans
        # the path to one under the build directory and reads the one outside.
        outside = self.tmp / "out"
        shutil.copytree(self.config.parent.parent / "styles", outside / "styles")
        os.symlink(outside, self.config.parent.parent / "link", target_is_directory=True)
        text = self.config.read_text(encoding="utf-8")
        self.config.write_text(text.replace("StylesPath = ../styles",
                                            "StylesPath = ../link/styles"), encoding="utf-8")
        _, why = self.judge(self.form())
        self.assertEqual(why, "runs vale with a StylesPath outside the directory the run made")

    @proves("REQ_KNOWN_PROGRAM", "REQ_REUSE_SOUND")
    def test_a_vale_changed_while_the_run_ran_is_refused(self):
        r, why = self.judge(self.form())
        self.assertIsNone(why)
        self.assertNotIn("starts vale, which changed while the run ran", whys(r))
        with open(self.vale, "ab") as f:
            f.write(b"\0")
        r.manifest()
        self.assertIn("starts vale, which changed while the run ran", whys(r))

    @proves("REQ_KNOWN_PROGRAM", "REQ_REUSE_SOUND")
    @only_on("posix")
    def test_vales_elf_interpreter_is_keyed(self):
        from tests.test_record_trace import elf
        loader = elf(self.tmp / "loader")
        elf(self.vale, str(loader))
        self.write_pins(record.file_hash(str(self.vale)))
        r, why = self.judge(self.form())
        self.assertIsNone(why)
        self.assertEqual(r.programs[str(loader)], record.file_hash(str(loader)))
        with open(loader, "ab") as f:
            f.write(b"\0")
        self.assertEqual(self.differs(r, {k: v for k, v in os.environ.items()
                                          if k.upper() not in record.OWN}),
                         f"program {loader}")

    @proves("REQ_KNOWN_PROGRAM")
    @only_on("nt")
    def test_a_dll_found_neither_beside_vale_nor_in_the_system_is_refused(self):
        # The interpreter's own program imports its DLL from its own directory, which is
        # not beside the copy.
        shutil.copy(getattr(sys, "_base_executable", sys.executable), self.vale)
        self.write_pins(record.file_hash(str(self.vale)))
        r, _ = self.judge(self.form())
        self.assertIn(f"runs <root>/bin/{self.vale.name}, which imports a DLL from neither "
                      f"its own directory nor the system's", whys(r))

    @proves("REQ_KNOWN_PROGRAM")
    def test_the_recorders_variable_is_the_toolchains(self):
        # The recorder cannot import the toolchain as it starts; the two names are one.
        self.assertEqual(record.VALE_VARIABLE, toolchain.VALE_ENV)

    @proves("REQ_KNOWN_PROGRAM", "REQ_REUSE_SOUND")
    def test_a_file_of_a_format_vale_starts_a_program_for_is_refused(self):
        for name in ("a.rst", "a.adoc", "a.xml"):
            with self.subTest(name):
                (self.lint / name).write_text("x", encoding="utf-8")
                _, why = self.judge(self.form())
                self.assertEqual(why, "runs vale on a file of a format for which it can start "
                                      "a program")
                (self.lint / name).unlink()

    @proves("REQ_KNOWN_PROGRAM", "REQ_REUSE_SOUND")
    def test_a_configuration_vale_looks_for_is_refused_and_one_appearing_reruns(self):
        r, why = self.judge(self.form())
        self.assertIsNone(why)
        found = self.made.parent / ".vale.ini"
        found.write_text("StylesPath = /\n", encoding="utf-8")
        self.assertEqual(self.differs(r, {}), f"path {found}")
        _, why = self.judge(self.form())
        self.assertEqual(why, "runs vale where a configuration it looks for is present")

    def named(self, path: Path):
        """The process's environment as the recorder reads it, TRIFECTA_VALE naming
        ``path``."""
        here = {**{k: v for k, v in toolchain.program_env().items()
                   if k.upper() not in (record.VALE_VARIABLE, "TERM")
                   and not k.upper().startswith("VALE_")}, record.VALE_VARIABLE: str(path)}
        self.here = {k: v for k, v in here.items() if k.upper() not in record.OWN}
        return mock.patch.object(record, "_environment",
                                 return_value=list(final_env(here).items()))

    @proves("REQ_KNOWN_PROGRAM", "REQ_REUSE_SOUND")
    def test_the_vale_trifecta_vale_names_is_let_through_by_its_pin(self):
        # As in a fixture copy: the original's Vale, outside this repository (DEC_0047).
        original = self.tmp / "original" / "bin"
        original.mkdir(parents=True)
        other = original / self.vale.name
        shutil.copy(self.vale, other)
        argv = [str(other), *self.form()[1:]]
        with self.named(other):
            r, why = self.judge(argv, env={record.VALE_VARIABLE: str(other)})
        self.assertIsNone(why)
        # Recorded by its path; its hash is what is trusted.
        self.assertEqual(r.programs[str(other)], self.digest)
        self.assertIsNone(self.differs(r, self.here))
        with open(other, "ab") as f:
            f.write(b"\0")
        self.assertEqual(self.differs(r, self.here), f"program {other}")
        # One that does not match the pin is refused.
        with self.named(other):
            _, why = self.judge(argv)
        self.assertEqual(why, "runs a vale whose SHA-256 is not the toolchain's pin")
        # Only the one it names, and never one the run made.
        with self.named(self.vale):
            _, why = self.judge(argv)
        self.assertEqual(why, "runs a vale that is neither bin/vale nor the one TRIFECTA_VALE "
                              "names")
        made = self.made / self.vale.name
        shutil.copy(self.vale, made)
        with self.named(made):
            _, why = self.judge([str(made), "--version"])
        self.assertEqual(why, "runs a vale the run made")

    @proves("REQ_KNOWN_PROGRAM")
    def test_only_the_runtime_reads_ruled_on_are_allowed_unkeyed(self):
        cgroup = "0::/user.slice/vale\n"
        allowed = ["/proc/self/maps", "/proc/self/mountinfo", "/proc/self/cgroup",
                   "/proc/42/maps", "/sys/kernel/mm/transparent_hugepage/hpage_pmd_size",
                   "/sys/devices/system/cpu/online", "/sys/fs/cgroup/user.slice/vale/cpu.max"]
        neighbours = ["/proc/self/status", "/proc/self/environ", "/proc/43/maps",
                      "/proc/self/task/42/maps", "/proc/version", "/proc/mounts",
                      "/sys/kernel/mm/transparent_hugepage/enabled",
                      "/sys/devices/system/cpu/possible", "/sys/fs/cgroup/other/cpu.max",
                      "/sys/fs/cgroup/user.slice/vale/memory.max", "/sys/fs/cgroup/cpu.max"]
        for path in allowed:
            with self.subTest(path):
                self.assertTrue(record.vale_runtime_read(path, {42}, cgroup))
        for path in neighbours:
            with self.subTest(path):
                self.assertFalse(record.vale_runtime_read(path, {42}, cgroup))
        # A control group the recorder cannot read as its own allows no cpu.max.
        for given in (None, "", "0::relative\n", "0::/a/../b\n"):
            with self.subTest(given=given):
                self.assertFalse(record.vale_runtime_read("/sys/fs/cgroup/b/cpu.max", {42},
                                                          given))


# --- the check's starts --------------------------------------------------------------

class CheckStarts(unittest.TestCase):
    @proves("REQ_KNOWN_PROGRAM")
    def test_the_check_starts_git_and_vale_with_the_six_variables_stripped(self):
        from trifecta import check
        root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, root, True)
        lint = root / "docs" / "_build" / "lint" / "rfcs"
        lint.mkdir(parents=True)
        done = subprocess.CompletedProcess([], 0, "", "")
        moving = {name: "x" for name in record.MOVING}
        with mock.patch.dict(os.environ, moving), \
                mock.patch.object(check.subprocess, "run", return_value=done) as run:
            check.repo_files(root)
            check.run_vale(root, root / "bin" / "vale", "prose.ini")
            check.check_vale_version(root / "bin" / "vale")
        self.assertEqual(run.call_count, 3)
        upper = {record._name(m) for m in record.MOVING}
        for call in run.call_args_list:
            with self.subTest(call.args[0][:2]):
                env = call.kwargs["env"]
                self.assertTrue(env)
                self.assertFalse({record._name(k) for k in env} & upper)


# --- the Sphinx build --------------------------------------------------------------------

class SphinxStart(unittest.TestCase):
    @proves("REQ_REUSE_SOUND")
    def test_the_checks_sphinx_build_starts_in_docs(self):
        # Sphinx changes into the configuration's directory, docs/: started there, the
        # change is no change, which the recorder lets through.
        root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, root, True)
        done = subprocess.CompletedProcess([], 0, "", "")
        with mock.patch.object(build.subprocess, "run", return_value=done) as run:
            build._run(root, None, root / "pycache")
        self.assertEqual(run.call_args.kwargs["cwd"], root / "docs")


if __name__ == "__main__":
    unittest.main()
