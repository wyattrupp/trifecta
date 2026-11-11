"""The recorder (COMP_RECORDER, IF_MANIFEST, DEC_0028): every input one process reads.

A process records itself when ``TRIFECTA_RECORD`` names a directory its parent prepared
with ``prepare``: the ``.pth`` file setup installs in a virtual environment runs that
directory's ``start.py``, which loads this file by its path and calls ``start`` before any
module of the run is imported. From then on the process notes, through Python's audit
hooks and wrappers on the probing functions and ``os.environ``, every file it reads, path
it probes, directory it lists, name the import system looks up and environment variable
it reads, and at exit writes ``manifest.json`` into the directory. Anything it cannot
follow, from an audit event it does not list to a program other than the interpreter,
makes the manifest unstorable: such a run is never reused, so a blind spot costs time,
never soundness.

The module imports only the standard library and loads under its own name, so the
package a run imports is the run's own, never the recorder's.
"""

from __future__ import annotations

import atexit
import hashlib
import inspect
import io
import json
import os
import stat
import sys
import threading

#: The variable naming the directory a process records into.
ENV = "TRIFECTA_RECORD"
#: The result store's variable: like ENV, the recorder's own, so never recorded.
STORE_ENV = "TRIFECTA_STORE"
OWN = frozenset({ENV, STORE_ENV})
MANIFEST = "manifest.json"
CONFIG = "config.json"
START = "start.py"
VERSION = 1
#: Stands for the repository root in recorded values, so a copy elsewhere matches.
ROOT = "<root>"
#: What the .pth line runs when ENV is set: loads the recorder its parent named, once.
START_SOURCE = """\
import sys
if "_trifecta_record" not in sys.modules:
    import importlib.util, json, os
    _d = os.environ["TRIFECTA_RECORD"]
    with open(os.path.join(_d, "config.json"), encoding="utf-8") as _f:
        _c = json.load(_f)
    _s = importlib.util.spec_from_file_location("_trifecta_record", _c["recorder"])
    _m = importlib.util.module_from_spec(_s)
    sys.modules["_trifecta_record"] = _m
    _s.loader.exec_module(_m)
    _m.start(_d, _c)
"""
#: The .pth file setup installs, and its one line, which imports nothing while ENV is unset.
PTH_NAME = "trifecta-record.pth"
PTH_LINE = ('import os; os.environ.get("TRIFECTA_RECORD") and exec(open(os.path.join('
            'os.environ["TRIFECTA_RECORD"], "start.py"), encoding="utf-8").read())\n')
SECTIONS = ("files", "probes", "listings", "lookups", "environment", "outside")
KINDS = ("file", "directory", "link", "absent")

#: The functions the recorder itself calls, taken before any is wrapped.
_lstat, _scandir, _getcwd, _open = os.lstat, os.scandir, os.getcwd, io.open


def prepare(directory: str, root: str, ignore=(), recorder: str | None = None) -> None:
    """Make ``directory`` one a process records into: the repository root, the recorder
    file to load, and the run's own control files, which are not inputs."""
    os.makedirs(directory, exist_ok=True)
    config = {"root": os.path.abspath(root),
              "recorder": os.path.abspath(recorder or __file__),
              "ignore": [os.path.abspath(p) for p in ignore]}
    _write(os.path.join(directory, CONFIG), json.dumps(config))
    _write(os.path.join(directory, START), START_SOURCE)


def _write(path: str, text: str) -> None:
    with _open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


# --- what is at a path ----------------------------------------------------------------

def kind(path: str) -> str:
    """``file``, ``directory``, ``link`` or ``absent``, not following a link or junction."""
    try:
        st = _lstat(path)
    except (OSError, ValueError):
        return "absent"
    if stat.S_ISLNK(st.st_mode) or getattr(st, "st_reparse_tag", 0):
        return "link"
    return "directory" if stat.S_ISDIR(st.st_mode) else "file"


def file_hash(path: str) -> str | None:
    h = hashlib.sha256()
    try:
        with _open(path, "rb") as f:
            for block in iter(lambda: f.read(1 << 20), b""):
                h.update(block)
    except (OSError, ValueError):
        return None
    return h.hexdigest()


def listing(path: str) -> list[list[str]] | None:
    """The sorted ``[name, kind]`` entries of a directory, or None when it is none."""
    if kind(path) != "directory":
        return None
    try:
        with _scandir(path) as it:
            names = [e.name for e in it]
    except OSError:
        return None
    return sorted([n, kind(os.path.join(path, n))] for n in names)


def _norm(path: str) -> str:
    return os.path.normcase(os.path.normpath(path))


#: The null device, which holds nothing to read, in the spellings subprocess uses.
_DEVNULL = {_norm(os.devnull), _norm("\\\\.\\nul"), _norm("nul")} if os.name == "nt" \
    else {_norm(os.devnull)}


def _under(path: str, base: str) -> bool:
    return path == base or path.startswith(base.rstrip(os.sep) + os.sep)


def _text(raw) -> str | None:
    if raw is None or isinstance(raw, int):
        return None
    try:
        return os.fsdecode(os.fspath(raw))
    except TypeError:
        return None


# --- the recorder ---------------------------------------------------------------------

class Recorder:
    def __init__(self, directory: str, config: dict):
        self.directory = os.path.abspath(directory)
        self.root = config["root"]
        self.nroot = _norm(self.root)
        self.ignore = [_norm(p) for p in config.get("ignore", ())] + [_norm(self.directory)]
        self.prefixes = sorted({_norm(p) for p in (sys.prefix, sys.base_prefix,
                                                   sys.exec_prefix, sys.base_exec_prefix)})
        self.lock = threading.RLock()
        self.local = threading.local()
        self.why: str | None = None
        self.files: dict[str, str] = {}
        self.outside: dict[str, str] = {}
        self.probes: dict[str, str] = {}
        self.listings: dict[str, list] = {}
        self.lookups: dict[str, str | None] = {}
        self.environment: dict[str, str | None] = {}
        self.env_set: set[str] = set()
        self.created: set[str] = set()   # directories the run made: nothing under them is read
        self.written: set[str] = set()   # files the run wrote, moved or removed
        self.children: list[str] = []
        self.registry: set[int] = set()
        self.in_rmtree = 0

    # -- state ------------------------------------------------------------------

    def refuse(self, why: str) -> None:
        if self.why is None:
            self.why = why

    def quiet(self) -> bool:
        """True while the recorder itself is at work, or once nothing more need be noted."""
        return getattr(self.local, "busy", False) or self.why is not None

    def placeholder(self, text: str) -> str:
        """``text`` with the root's absolute path replaced, ignoring case where the system
        does, in either slash form."""
        for form in dict.fromkeys((self.root, self.root.replace("\\", "/"))):
            if os.name == "nt":
                low, needle, out, i = text.lower(), form.lower(), [], 0
                while (j := low.find(needle, i)) >= 0:
                    out += [text[i:j], ROOT]
                    i = j + len(form)
                text = "".join(out) + text[i:]
            else:
                text = text.replace(form, ROOT)
        return text

    def where(self, raw) -> tuple[str, str, str] | None:
        """``(section, key, absolute path)`` for a path, or None when it is no input: the
        run made it, wrote it or owns it, it is the interpreter's, or it holds the root.
        The section is ``repo``, keyed relative to the root, or ``outside``."""
        path = _text(raw)
        if path is None or _norm(path) in _DEVNULL:
            return None
        absolute = os.path.abspath(os.path.join(_getcwd(), path))
        n = _norm(absolute)
        if n in self.written or any(_under(n, c) for c in self.created) \
                or any(_under(n, i) for i in self.ignore) \
                or any(_under(n, p) for p in self.prefixes):
            return None
        if _under(n, self.nroot):
            rel = absolute[len(self.root):].lstrip("\\/").replace(os.sep, "/")
            return "repo", rel or ".", absolute
        if _under(self.nroot, n):
            return None  # an ancestor of the root is a directory wherever the root is
        return "outside", absolute, absolute

    # -- inputs -------------------------------------------------------------------

    def read(self, raw) -> None:
        found = self.where(raw)
        if found is None:
            return
        section, key, absolute = found
        target = self.files if section == "repo" else self.outside
        if key in target:
            return
        digest = file_hash(absolute) if kind(absolute) == "file" else None
        if digest is None:
            self.probe(raw)
        else:
            target[key] = digest

    def probe(self, raw) -> None:
        found = self.where(raw)
        if found is not None:
            self.probes.setdefault(found[1], kind(found[2]))

    def list(self, raw) -> None:
        if isinstance(raw, int):
            if not self.in_rmtree:
                self.refuse("lists a directory by descriptor")
            return
        found = self.where("." if raw is None else raw)
        if found is None:
            return
        _, key, absolute = found
        if key in self.listings:
            return
        entries = listing(absolute)
        if entries is None:
            self.probe(absolute)
            return
        keep = [e for e in entries
                if not any(_under(_norm(os.path.join(absolute, e[0])), i) for i in self.ignore)]
        self.listings[key] = keep

    def wrote(self, raw, directory: bool = False) -> None:
        path = _text(raw)
        if path is None:
            return
        n = _norm(os.path.abspath(os.path.join(_getcwd(), path)))
        (self.created if directory else self.written).add(n)

    # -- the audit hook -----------------------------------------------------------

    def hook(self, event: str, args: tuple) -> None:
        if self.quiet():
            return
        self.local.busy = True
        try:
            with self.lock:
                handler = HANDLERS.get(event)
                if handler is not None:
                    handler(self, args)
                elif event in REFUSED:
                    self.refuse(REFUSED[event])
                elif event not in HARMLESS:
                    self.refuse(f"raises an audit event the recorder does not list: {event}")
        except Exception as exc:  # a recorder that cannot follow an event stores nothing
            self.refuse(f"the recorder failed on {event}: {type(exc).__name__}")
        finally:
            self.local.busy = False

    def guarded(self, action) -> None:
        """Run ``action`` as the recorder, when the run is still being recorded."""
        if self.quiet():
            return
        self.local.busy = True
        try:
            with self.lock:
                action()
        except Exception as exc:
            self.refuse(f"the recorder failed: {type(exc).__name__}")
        finally:
            self.local.busy = False

    # -- the end ------------------------------------------------------------------

    def manifest(self) -> dict:
        self.local.busy = True
        with self.lock:
            if self.why is None:
                for name, module in list(sys.modules.items()):
                    if name == "_trifecta_record":
                        continue  # the recorder is part of the package's identity
                    origin = getattr(getattr(module, "__spec__", None), "origin", None)
                    if isinstance(origin, str) and os.path.isabs(origin):
                        self.read(origin)
            for child in self.children:
                self._merge(child)
            data = {"version": VERSION, "storable": self.why is None}
            if self.why is not None:
                data["why"] = self.why
            for name in SECTIONS:
                data[name] = dict(sorted(getattr(self, name).items()))
            return data

    def _merge(self, child: str) -> None:
        try:
            with _open(os.path.join(child, MANIFEST), encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            self.refuse("a Python child left no manifest")
            return
        if not valid(data):
            self.refuse("a Python child left a malformed manifest")
            return
        if not data["storable"]:
            self.refuse(data.get("why") or "a Python child was not storable")
        for name in SECTIONS:
            mine = getattr(self, name)
            for key, value in data[name].items():
                if mine.setdefault(key, value) != value:
                    self.refuse(f"a Python child and its parent saw {key} differently")

    def finish(self) -> None:
        data = self.manifest()
        target = os.path.join(self.directory, MANIFEST)
        _write(target + ".tmp", json.dumps(data, sort_keys=True))
        os.replace(target + ".tmp", target)


def valid(data) -> bool:
    """Whether ``data`` has the shape IF_MANIFEST states."""
    if not (isinstance(data, dict) and data.get("version") == VERSION
            and isinstance(data.get("storable"), bool)
            and set(data) <= {"version", "storable", "why", *SECTIONS}
            and all(isinstance(data.get(s), dict) for s in SECTIONS)):
        return False
    str_or_none = lambda v: v is None or isinstance(v, str)
    return (all(isinstance(v, str) for v in data["files"].values())
            and all(isinstance(v, str) for v in data["outside"].values())
            and all(v in KINDS for v in data["probes"].values())
            and all(isinstance(v, list) and all(isinstance(e, list) and len(e) == 2
                                                and isinstance(e[0], str) and e[1] in KINDS
                                                for e in v)
                    for v in data["listings"].values())
            and all(str_or_none(v) for v in data["lookups"].values())
            and all(str_or_none(v) for v in data["environment"].values()))


# --- the events -----------------------------------------------------------------------

def _open_event(r: Recorder, args) -> None:
    path, mode, flags = args
    if isinstance(path, int):
        return  # an open descriptor: its file was recorded when it was opened
    if mode is None:  # os.open: the flags say what it does
        access = flags & (os.O_RDONLY | os.O_WRONLY | os.O_RDWR)
        reads = access != os.O_WRONLY
        writes = access != os.O_RDONLY or flags & (os.O_CREAT | os.O_TRUNC | os.O_APPEND)
        fresh = flags & (os.O_TRUNC | getattr(os, "O_EXCL", 0))
    else:
        reads = "r" in mode or "+" in mode or "a" in mode
        writes = any(c in mode for c in "wax+")
        fresh = "w" in mode or "x" in mode
    if reads and not fresh:
        r.read(path)
    elif writes:
        r.probe(path)  # whether it was there decides what the write does
    if writes:
        r.wrote(path)


def _rename(r: Recorder, args) -> None:
    src, dst = args[0], args[1]
    src_kind = kind(_text(src) or "")
    r.read(src)
    r.wrote(src, directory=src_kind == "directory")
    r.wrote(dst, directory=src_kind == "directory")


def _remove(r: Recorder, args) -> None:
    r.probe(args[0])
    r.wrote(args[0])


def _mkdir(r: Recorder, args) -> None:
    path = _text(args[0])
    if path is None or (len(args) > 2 and args[2] not in (-1, None)):
        r.refuse("makes a directory relative to a descriptor")
        return
    if kind(os.path.join(_getcwd(), path)) != "absent":
        r.probe(path)  # making a directory that is there tells the run it is there
    else:
        r.wrote(path, directory=True)


def _copy(r: Recorder, args) -> None:
    r.read(args[0])
    r.wrote(args[1])


def _modify(r: Recorder, args) -> None:
    r.probe(args[0])
    r.wrote(args[0])


def _link(r: Recorder, args) -> None:
    r.probe(args[0])
    r.wrote(args[1])


def _listing(r: Recorder, args) -> None:
    # The import system's own listings are recorded as the names it looked up. Frames:
    # this handler, the hook, then the code that listed.
    caller = sys._getframe(2)
    if caller is not None and caller.f_code in _IMPORT_CODES:
        return
    r.list(args[0] if args else None)


def _chdir(r: Recorder, args) -> None:
    path = _text(args[0])
    if path is None or _norm(os.path.abspath(path)) != _norm(_getcwd()):
        r.refuse("changes the working directory")


def _popen(r: Recorder, args) -> None:
    if not getattr(r.local, "child", False):
        program = args[0]
        if program is None:
            argv = args[1]
            if isinstance(argv, (list, tuple)):
                program = argv[0] if argv else None
            else:  # on Windows the command line is one string by now
                text = _text(argv) or ""
                program = text[1:].split('"')[0] if text.startswith('"') else text.split(" ")[0]
        name = os.path.basename(_text(program) or "")
        name = name[:-4] if name.lower().endswith(".exe") else name
        r.refuse(f"runs {name or 'a program'}")


def _registry_open(r: Recorder, args) -> None:
    r.local.registry_ok = len(args) > 1 and isinstance(args[1], str) \
        and args[1].lower() in REGISTRY_KEYS
    if not r.local.registry_ok:
        r.refuse("reads the registry")


def _registry_opened(r: Recorder, args) -> None:
    if getattr(r.local, "registry_ok", False):
        r.registry.add(int(args[0]))
    r.local.registry_ok = False


def _registry_read(r: Recorder, args) -> None:
    if not args or int(args[0]) not in r.registry:
        r.refuse("reads the registry")


def _dlopen(r: Recorder, args) -> None:
    if not (args and isinstance(args[0], str) and args[0].lower() in CONSOLE_LIBRARIES):
        r.refuse("loads native code through ctypes")


def _dlsym(r: Recorder, args) -> None:
    library, name = args[0], args[1]
    if not (str(getattr(library, "_name", "")).lower() in CONSOLE_LIBRARIES
            and name in CONSOLE_FUNCTIONS):
        r.refuse("loads native code through ctypes")


HANDLERS = {
    "open": _open_event,
    "os.rename": _rename, "os.replace": _rename,
    "os.remove": _remove, "os.rmdir": _remove,
    "os.mkdir": _mkdir,
    "shutil.copyfile": _copy, "_winapi.CopyFile2": _copy,
    "shutil.copymode": _copy, "shutil.copystat": _copy,
    "os.chmod": _modify, "os.chown": _modify, "os.chflags": _modify, "os.lchflags": _modify,
    "os.lchmod": _modify, "os.lchown": _modify, "os.utime": _modify, "os.truncate": _modify,
    "os.setxattr": _modify, "os.removexattr": _modify, "os.mkfifo": _modify,
    "os.mknod": _modify,
    "os.link": _link, "os.symlink": _link,
    "os.listdir": _listing, "os.scandir": _listing,
    "os.chdir": _chdir,
    "subprocess.Popen": _popen,
    "winreg.OpenKey": _registry_open, "winreg.OpenKeyEx": _registry_open,
    "winreg.OpenKey/result": _registry_opened,
    "winreg.EnumValue": _registry_read, "winreg.QueryInfoKey": _registry_read,
    "winreg.QueryValue": _registry_read, "winreg.EnumKey": _registry_read,
    "ctypes.dlopen": _dlopen, "ctypes.dlsym": _dlsym,
}
#: Registry keys a run may read: the system's time zone, which belongs with the clock
#: that RFC_0008 leaves out of scope.
REGISTRY_KEYS = {r"system\currentcontrolset\control\timezoneinformation"}
#: colorama binds these console functions from kernel32 on Windows; none reads a file.
CONSOLE_LIBRARIES = {"kernel32", "kernel32.dll"}
CONSOLE_FUNCTIONS = {
    "GetLastError", "GetStdHandle", "GetConsoleScreenBufferInfo", "SetConsoleTextAttribute",
    "SetConsoleCursorPosition", "FillConsoleOutputCharacterA", "FillConsoleOutputAttribute",
    "SetConsoleTitleW", "GetConsoleMode", "SetConsoleMode",
}
#: Events that read nothing the manifest keys on: code objects and frames, the import
#: machinery, whose lookups are recorded by name, writes to the environment, which the
#: mapping notes, threads and handles, and operations whose reads and writes raise their
#: own events.
HARMLESS = frozenset({
    "builtins.id", "object.__getattr__", "object.__setattr__", "object.__delattr__",
    "compile", "exec", "import", "marshal.loads", "marshal.load", "marshal.dumps",
    "code.__new__", "function.__new__", "sys._getframe", "sys._getframemodulename",
    "sys._current_frames", "sys._current_exceptions", "sys.addaudithook",
    "sys.excepthook", "sys.unraisablehook", "sys.settrace", "sys.setprofile",
    "sys.set_asyncgen_hooks_firstiter", "sys.set_asyncgen_hooks_finalizer",
    "sys.monitoring.register_callback", "sys.setrecursionlimit",
    "cpython.run_command", "cpython.run_module", "cpython.run_file", "cpython.run_startup",
    "cpython.run_interactivehook", "cpython.PyInterpreterState_New",
    "cpython.PyInterpreterState_Clear", "cpython._PySys_ClearAuditHooks",
    "pickle.find_class", "array.__new__", "gc.get_objects", "gc.get_referrers",
    "gc.get_referents", "gc.freeze", "time.sleep", "_thread.start_new_thread",
    "os.putenv", "os.unsetenv", "os.walk", "os.fwalk", "glob.glob", "glob.glob/2",
    "pathlib.Path.glob", "pathlib.Path.rglob", "pathlib.Path.walk", "shutil.copytree",
    "shutil.move", "shutil.make_archive", "shutil.unpack_archive", "shutil.rmtree",
    "shutil.chown", "tempfile.mkstemp", "tempfile.mkdtemp", "os.add_dll_directory",
    "os.kill", "os.killpg", "signal.pthread_kill", "_winapi.CreateProcess",
    "_winapi.CreatePipe", "_winapi.CreateNamedPipe", "_winapi.OpenProcess",
    "_winapi.TerminateProcess", "msvcrt.get_osfhandle", "msvcrt.open_osfhandle",
    "msvcrt.locking", "fcntl.fcntl", "fcntl.ioctl", "fcntl.flock", "fcntl.lockf",
    "mmap.__new__", "socket.__new__", "socket.bind", "builtins.breakpoint",
    "winreg.ConnectRegistry",
})
REFUSED = {
    "socket.connect": "makes a network connection", "socket.getaddrinfo": "looks up a host",
    "socket.gethostname": "reads the host name", "socket.gethostbyname": "looks up a host",
    "socket.gethostbyaddr": "looks up a host", "socket.getnameinfo": "looks up a host",
    "socket.sendto": "makes a network connection",
    "socket.sendmsg": "makes a network connection",
    "urllib.Request": "makes a network request", "os.system": "runs a shell",
    "os.exec": "replaces the process", "os.spawn": "runs a program",
    "os.posix_spawn": "runs a program", "os.fork": "forks", "os.forkpty": "forks",
    "os.startfile": "starts a program", "os.fchdir": "changes the working directory",
}


# --- probes, imports, children, the environment ---------------------------------------

def _probing(r: Recorder, function, hashes: bool):
    """``function`` with every path it is given recorded as a probe; a file whose status
    ``os.stat`` or ``os.lstat`` returns, size included, is recorded as read."""

    def wrapped(path, *args, **kwargs):
        if not isinstance(path, int) and kwargs.get("dir_fd") is None:
            def note():
                r.probe(path)
                if hashes:
                    found = r.where(path)
                    if found and kind(found[2]) == "file":
                        r.read(path)
            r.guarded(note)
        return function(path, *args, **kwargs)

    wrapped.__wrapped__ = function
    wrapped.__name__ = getattr(function, "__name__", "probe")
    wrapped.__doc__ = getattr(function, "__doc__", None)
    return wrapped


_IMPORT_CODES: set = set()


def _watch_imports(r: Recorder) -> None:
    """Record each name a FileFinder looks for in a directory, and what it found, in place
    of the directory's whole listing."""
    from importlib import machinery

    finder = machinery.FileFinder
    _IMPORT_CODES.add(finder._fill_cache.__code__)
    original = finder.find_spec

    def find_spec(self, fullname, target=None):
        spec = original(self, fullname, target)

        def note():
            found = r.where(self.path)
            if found is None:
                return
            if spec is None:
                result = None
            elif spec.origin is None or not os.path.isabs(spec.origin):
                result = "(namespace)"
            else:
                hit = r.where(spec.origin)
                result = hit[1] if hit else "(elsewhere)"
            r.lookups.setdefault(f"{found[1]}/{fullname.rpartition('.')[2]}", result)
        r.guarded(note)
        return spec

    finder.find_spec = find_spec


def _python_child(argv: list[str]) -> str | None:
    """Why a child started with ``sys.executable`` cannot record itself, or None."""
    for a in argv[1:]:
        if a in ("-c", "-m", "-") or not a.startswith("-"):
            return None
        if a.startswith("--"):
            continue
        for c in a[1:]:
            if c in "XW":
                break  # the rest is the option's value
            if c == "S":
                return "starts a Python child with -S, which runs no .pth file"
    return None


def _watch_children(r: Recorder) -> None:
    """Give each Python child a fresh directory to record into; any other program, or a
    Python child that cannot record itself, makes the run unstorable."""
    import secrets
    import subprocess

    original = subprocess.Popen._execute_child
    names = list(inspect.signature(original).parameters)
    env_at, shell_at = names.index("env") - 1, names.index("shell") - 1  # less self
    executable = _norm(os.path.abspath(sys.executable))

    def execute_child(self, *args):
        args = list(args)
        argv, program_arg = args[0], args[1]
        python = False
        if not isinstance(argv, (str, bytes)) and not args[shell_at] and argv:
            program = program_arg if program_arg is not None else argv[0]
            python = _norm(os.path.abspath(os.fsdecode(program))) == executable
        if python and not r.quiet():
            env = args[env_at]
            given = None if env is None else env.get(ENV)
            why = _python_child([os.fsdecode(a) for a in argv])
            if given is not None and _norm(os.path.abspath(given)) != _norm(r.directory):
                why = "starts a Python child that records into a directory of its own"
            if why:
                r.refuse(why)
            else:
                r.local.busy = True
                try:
                    child = os.path.join(r.directory, "children", secrets.token_hex(8))
                    with _open(os.path.join(r.directory, CONFIG), encoding="utf-8") as f:
                        config = json.load(f)
                    # What the parent made or wrote is no input to its child either.
                    with r.lock:
                        config["ignore"] = sorted({*config.get("ignore", ()), *r.created,
                                                   *r.written})
                    os.makedirs(child)
                    _write(os.path.join(child, CONFIG), json.dumps(config))
                    _write(os.path.join(child, START), START_SOURCE)
                    env = dict(os.environ if env is None else env)
                    env[ENV] = child
                    args[env_at] = env
                    with r.lock:
                        r.children.append(child)
                finally:
                    r.local.busy = False
        r.local.child = python
        try:
            return original(self, *args)
        finally:
            r.local.child = False

    subprocess.Popen._execute_child = execute_child


def _watch_rmtree(r: Recorder) -> None:
    """shutil.rmtree works through descriptors on some systems: the tree it removes is
    recorded as written, and its own listings are not inputs."""
    import shutil

    original = shutil.rmtree

    def rmtree(path, *args, **kwargs):
        def note():
            r.probe(path)
            r.wrote(path, directory=True)
        r.guarded(note)
        with r.lock:
            r.in_rmtree += 1
        try:
            return original(path, *args, **kwargs)
        finally:
            with r.lock:
                r.in_rmtree -= 1

    rmtree.avoids_symlink_attacks = getattr(original, "avoids_symlink_attacks", False)
    shutil.rmtree = rmtree


def _name(key) -> str:
    name = os.fsdecode(key) if isinstance(key, bytes) else str(key)
    return name.upper() if os.name == "nt" else name


def _recording_environ(r: Recorder, base: type) -> type:
    """A subclass of ``os._Environ`` that records each variable read, every variable when
    the mapping is iterated, sized, copied or shown, and the variables the run sets, whose
    later reads are the run's own; it sets the process environment as before."""

    def note(self, key) -> None:
        name = _name(key)
        if name in OWN or name in r.env_set or name in r.environment:
            return
        try:
            value = base.__getitem__(self, key)
        except KeyError:
            value = None
        if isinstance(value, bytes):
            value = os.fsdecode(value)
        r.environment[name] = None if value is None else hashlib.sha256(
            r.placeholder(value).encode("utf-8", "surrogateescape")).hexdigest()

    def note_all(self) -> None:
        r.guarded(lambda: [note(self, k) for k in list(base.__iter__(self))])

    class Recording(base):
        def __getitem__(self, key):
            r.guarded(lambda: note(self, key))
            return base.__getitem__(self, key)

        def __contains__(self, key):
            r.guarded(lambda: note(self, key))
            return base.__contains__(self, key)

        def __iter__(self):
            note_all(self)
            return base.__iter__(self)

        def __len__(self):
            note_all(self)
            return base.__len__(self)

        def __setitem__(self, key, value):
            r.guarded(lambda: r.env_set.add(_name(key)))
            base.__setitem__(self, key, value)

        def __delitem__(self, key):
            r.guarded(lambda: r.env_set.add(_name(key)))
            base.__delitem__(self, key)

        def copy(self):
            note_all(self)
            return base.copy(self)

        def __repr__(self):
            note_all(self)
            return base.__repr__(self)

    Recording.__name__ = base.__name__
    return Recording


_recorder: Recorder | None = None


def start(directory: str, config: dict) -> Recorder:
    """Install the recorder in this process, once: the .pth file can run twice in one
    start on Windows."""
    global _recorder
    if _recorder is not None:
        return _recorder
    r = _recorder = Recorder(directory, config)
    # No byte code is read or written: every module compiles from its source, which the
    # recorder hashes, into an empty prefix the run made.
    sys.dont_write_bytecode = True
    prefix = os.path.join(r.directory, "pycache")
    os.makedirs(prefix, exist_ok=True)
    sys.pycache_prefix = prefix
    for name, hashes in (("stat", True), ("lstat", True), ("access", False),
                         ("readlink", False)):
        setattr(os, name, _probing(r, getattr(os, name), hashes))
    for name in ("exists", "lexists", "isfile", "isdir", "islink", "isjunction", "realpath"):
        if hasattr(os.path, name):
            setattr(os.path, name, _probing(r, getattr(os.path, name), False))
    os.environ.__class__ = _recording_environ(r, type(os.environ))
    if hasattr(os, "environb"):
        os.environb.__class__ = _recording_environ(r, type(os.environb))
    _watch_imports(r)
    _watch_children(r)
    _watch_rmtree(r)
    sys.addaudithook(r.hook)
    atexit.register(r.finish)
    return r
