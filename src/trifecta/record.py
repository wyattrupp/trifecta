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
#: What a process made and wrote, which its parent leaves out of its own inputs.
MADE = "made.json"
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
    # No byte code from the tree, the recorder's own included.
    sys.dont_write_bytecode = True
    sys.pycache_prefix = os.path.join(_d, "pycache")
    _s = importlib.util.spec_from_file_location("_trifecta_record", _c["recorder"])
    _m = importlib.util.module_from_spec(_s)
    sys.modules["_trifecta_record"] = _m
    _s.loader.exec_module(_m)
    _m.start(_d, _c)
"""
#: The .pth file setup installs, and its one line, which imports nothing while ENV is unset.
#: Named to sort first, so no other .pth file in the environment runs before the recorder.
PTH_NAME = "00-trifecta-record.pth"
PTH_LINE = ('import os; os.environ.get("TRIFECTA_RECORD") and exec(open(os.path.join('
            'os.environ["TRIFECTA_RECORD"], "start.py"), encoding="utf-8").read())\n')
SECTIONS = ("files", "probes", "listings", "lookups", "environment", "outside")
KINDS = ("file", "directory", "link", "absent")

#: The functions the recorder itself calls, taken before any is wrapped.
_lstat, _scandir, _getcwd, _open = os.lstat, os.scandir, os.getcwd, io.open
_realpath = os.path.realpath


def prepare(directory: str, root: str, ignore=(), recorder: str | None = None) -> None:
    """Make ``directory`` one a process records into: the repository root, the recorder
    file to load, and the run's own control files, which are not inputs. The directory is
    a new one, or an empty one the caller made, such as by ``tempfile.mkdtemp``: what it
    holds is run by the processes that record into it."""
    if os.path.islink(directory) or os.path.isdir(directory) and os.listdir(directory):
        raise ValueError(f"{directory} is a link or is not empty")
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


#: The system's time zone, which belongs with the clock that RFC_0008 leaves out of scope,
#: as the Windows registry's time-zone key does.
_ZONES = () if os.name == "nt" else tuple(
    os.path.normpath(p) for p in ("/etc/localtime", "/etc/timezone", "/usr/share/zoneinfo",
                                  "/usr/lib/zoneinfo", "/usr/share/lib/zoneinfo"))

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
        #: Each child's directory, with how many inputs had been seen when it started.
        self.children: list[tuple[str, int]] = []
        #: Variables the run gave a child through ``env=``: the child's reads of them are
        #: the run's own.
        self.child_env: set[str] = set()
        self.registry: set[int] = set()
        self.seq = 0
        self.first: dict[tuple[str, str], int] = {}

    def in_rmtree(self) -> bool:
        """Whether this thread is inside shutil.rmtree, whose own calls are no input."""
        return getattr(self.local, "rmtree", 0) > 0

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
                or any(_under(n, p) for p in self.prefixes) \
                or any(_under(n, z) for z in _ZONES):
            return None
        if _under(n, self.nroot):
            rel = absolute[len(self.root):].lstrip("\\/").replace(os.sep, "/")
            return "repo", rel or ".", absolute
        if _under(self.nroot, n):
            return None  # an ancestor of the root is a directory wherever the root is
        return "outside", absolute, absolute

    # -- inputs -------------------------------------------------------------------

    def read(self, raw) -> None:
        path = _text(raw)
        if path is None:
            return
        absolute = self.through(os.path.abspath(os.path.join(_getcwd(), path)), "reads")
        if absolute is None:
            return
        found = self.where(absolute)
        if found is None:
            return
        section, key, absolute = found
        name = "files" if section == "repo" else "outside"
        if key in getattr(self, name):
            return
        digest = file_hash(absolute) if kind(absolute) == "file" else None
        if digest is None:
            self.probe(absolute)
        else:
            self.note(name, key, digest)

    def through(self, absolute: str, what: str) -> str | None:
        """The path a call that follows links reaches: a link the run made is followed to
        its target; one it did not make is refused, since what it points to could change
        unseen. None when refused."""
        if kind(absolute) != "link":
            return absolute
        if self.where(absolute) is not None:
            self.refuse(f"{what} through a link: {self.where(absolute)[1]}")
            return None
        return _realpath(absolute)

    def note(self, name: str, key: str, value) -> None:
        """Record an input once, with when it was first seen."""
        section = getattr(self, name)
        if key not in section:
            section[key] = value
            self.seq += 1
            self.first[(name, key)] = self.seq

    def probe(self, raw, follows: bool = False) -> None:
        path = _text(raw)
        if path is None:
            return
        absolute = os.path.abspath(os.path.join(_getcwd(), path))
        if follows:
            absolute = self.through(absolute, "probes")
            if absolute is None:
                return
        found = self.where(absolute)
        if found is not None:
            self.note("probes", found[1], kind(found[2]))

    def list(self, raw) -> None:
        if isinstance(raw, int):
            self.refuse("lists a directory by descriptor")
            return
        path = "." if raw is None else _text(raw)
        n = _norm(os.path.abspath(os.path.join(_getcwd(), path or ".")))
        if n != self.nroot and _under(self.nroot, n):
            # The root's ancestors hold its siblings, which differ wherever it is copied.
            self.refuse("lists a directory that holds the repository")
            return
        followed = self.through(os.path.abspath(os.path.join(_getcwd(), path)), "lists")
        found = None if followed is None else self.where(followed)
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
        self.note("listings", key, keep)

    def wrote(self, raw, directory: bool = False) -> None:
        path = _text(raw)
        if path is None:
            return
        n = _norm(os.path.abspath(os.path.join(_getcwd(), path)))
        (self.created if directory else self.written).add(n)

    # -- the audit hook -----------------------------------------------------------

    def hook(self, event: str, args: tuple) -> None:
        if self.quiet() or self.in_rmtree():
            return  # rmtree's calls name entries by descriptor; its tree is written
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
            for child, started in self.children:
                self._merge(child, started)
            data = {"version": VERSION, "storable": self.why is None}
            if self.why is not None:
                data["why"] = self.why
            for name in SECTIONS:
                data[name] = dict(sorted(getattr(self, name).items()))
            return data

    def _merge(self, child: str, started: int) -> None:
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
        try:
            with _open(os.path.join(child, MADE), encoding="utf-8") as f:
                made = json.load(f)
            created = {str(p) for p in made["created"]}
            written = {str(p) for p in made["written"]}
        except (OSError, ValueError, KeyError, TypeError):
            self.refuse("a Python child left no record of what it made")
            return
        self._drop_made(created, written, started)
        for name in SECTIONS:
            for key, value in data[name].items():
                if name == "environment" and key in self.env_set | self.child_env:
                    continue  # a variable the run set is its own, in its children too
                if getattr(self, name).get(key, value) != value:
                    self.refuse(f"a Python child and its parent saw {key} differently")
                self.note(name, key, value)

    def _drop_made(self, created: set, written: set, started: int) -> None:
        """Leave out what the parent first saw after a child started, under what that
        child made or wrote: such a path was the child's output when the parent read it.
        What the parent saw before is an input, and so is a path found absent."""
        def made(key: str) -> bool:
            n = _norm(key if os.path.isabs(key) else os.path.join(self.root, key))
            return n in written or any(_under(n, c) for c in created)
        for name in ("files", "outside", "probes", "listings"):
            section = getattr(self, name)
            for key in [k for k, v in section.items() if v != "absent" and made(k)
                        and self.first.get((name, k), 0) > started]:
                del section[key]

    def finish(self) -> None:
        data = self.manifest()
        target = os.path.join(self.directory, MANIFEST)
        if os.path.exists(target):  # another process wrote here: whose reads is unknown
            data = {**data, "storable": False, "why": "two processes recorded into one place"}
        _write(os.path.join(self.directory, MADE),
               json.dumps({"created": sorted(self.created), "written": sorted(self.written)}))
        _write(target + ".tmp", json.dumps(data, sort_keys=True))
        os.replace(target + ".tmp", target)


#: Bounds on what a manifest read from a store may hold, which is data from another run.
MAX_ENTRIES, MAX_TEXT = 200_000, 4096
_HEX = frozenset("0123456789abcdef")
_SPECIAL = ("(namespace)", "(elsewhere)")


def _digest(v) -> bool:
    return isinstance(v, str) and len(v) == 64 and set(v) <= _HEX


def _relative(key) -> bool:
    """A repository-relative path as IF_MANIFEST writes it: forward slashes, no root, no
    drive, no ``..``, no empty part."""
    if not isinstance(key, str) or not key or len(key) > MAX_TEXT or "\\" in key \
            or "\0" in key:
        return False
    if key == ".":
        return True
    parts = key.split("/")
    return not (key.startswith("/") or (len(key) > 1 and key[1] == ":")
                or any(p in ("", ".", "..") for p in parts))


def _absolute(key) -> bool:
    return (isinstance(key, str) and 0 < len(key) <= MAX_TEXT and "\0" not in key
            and os.path.isabs(key) and ".." not in key.replace("\\", "/").split("/"))


def _path(key) -> bool:
    return _relative(key) or _absolute(key)


def _lookup_key(key) -> bool:
    if not isinstance(key, str):
        return False
    directory, _, name = key.rpartition("/")
    return name.isidentifier() and _path(directory)


def valid(data) -> bool:
    """Whether ``data`` has exactly the shape IF_MANIFEST states, within bounds: what a
    store holds came from another run, so it is checked before anything reads it."""
    if not (isinstance(data, dict) and type(data.get("version")) is int
            and data["version"] == VERSION and type(data.get("storable")) is bool
            and set(data) <= {"version", "storable", "why", *SECTIONS}
            and all(isinstance(data.get(s), dict) for s in SECTIONS)):
        return False
    if "why" in data and (data["storable"] or not isinstance(data["why"], str)
                          or len(data["why"]) > MAX_TEXT):
        return False
    if sum(len(data[s]) for s in SECTIONS) + sum(
            len(v) if isinstance(v, list) else 0 for v in data["listings"].values()) \
            > MAX_ENTRIES:
        return False
    entry = lambda e: (isinstance(e, list) and len(e) == 2 and isinstance(e[0], str)
                       and 0 < len(e[0]) <= MAX_TEXT and "/" not in e[0] and e[1] in KINDS)
    found = lambda v: v is None or v in _SPECIAL or _relative(v)
    name = lambda k: (isinstance(k, str) and 0 < len(k) <= MAX_TEXT and "=" not in k
                      and "\0" not in k)
    return (all(_relative(k) and _digest(v) for k, v in data["files"].items())
            and all(_absolute(k) and _digest(v) for k, v in data["outside"].items())
            and all(_path(k) and v in KINDS for k, v in data["probes"].items())
            and all(_path(k) and isinstance(v, list) and all(map(entry, v))
                    for k, v in data["listings"].items())
            and all(_lookup_key(k) and found(v) for k, v in data["lookups"].items())
            and all(name(k) and (v is None or _digest(v))
                    for k, v in data["environment"].items()))


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


#: Where each event carries its directory descriptors: a path relative to a descriptor
#: names a file the recorder cannot place.
DIR_FD_AT = {"os.remove": (1,), "os.rmdir": (1,), "os.rename": (2, 3), "os.replace": (2, 3),
             "os.mkdir": (2,), "os.chmod": (2,), "os.chown": (3,), "os.utime": (3,),
             "os.link": (2, 3), "os.symlink": (2,)}


def _by_descriptor(r: Recorder, event: str, args) -> bool:
    if any(i < len(args) and args[i] not in (None, -1) for i in DIR_FD_AT.get(event, ())):
        r.refuse("names a path relative to a directory descriptor")
        return True
    return False


def _rename(r: Recorder, args) -> None:
    if _by_descriptor(r, "os.rename", args):
        return
    src, dst = args[0], args[1]
    if kind(os.path.join(_getcwd(), _text(src) or "")) == "directory":
        if r.where(src) is not None:
            # What is under it would be read under a name the run made.
            r.refuse("moves a directory it did not make")
            return
        r.wrote(dst, directory=True)
        return
    r.read(src)
    r.wrote(src)
    r.wrote(dst)


def _remove(r: Recorder, args) -> None:
    if _by_descriptor(r, "os.remove", args):
        return
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


def _modifying(event: str):
    def handler(r: Recorder, args) -> None:
        if not _by_descriptor(r, event, args):
            r.probe(args[0])
            r.wrote(args[0])
    return handler


def _symlink(r: Recorder, args) -> None:
    # Reading the link later reads its target, which the read records then.
    if not _by_descriptor(r, "os.symlink", args):
        r.wrote(args[1])


def _xattr(r: Recorder, args) -> None:
    if args and not isinstance(args[0], int):
        r.probe(args[0])


def _hardlink(r: Recorder, args) -> None:
    # A hard link is another name for the same content: the run reads its source.
    if not _by_descriptor(r, "os.link", args):
        r.read(args[0])
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


def _in_popen(r: Recorder, args) -> None:
    if getattr(r.local, "popen", False) is False:
        r.refuse("starts a process other than through subprocess")


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
    **{event: _modifying(event) for event in (
        "os.chmod", "os.chown", "os.chflags", "os.lchflags", "os.lchmod", "os.lchown",
        "os.utime", "os.truncate", "os.setxattr", "os.removexattr")},
    "os.link": _hardlink, "os.symlink": _symlink,
    # shutil.copy2 copies extended attributes on Linux: a probe of its source.
    "os.listxattr": _xattr, "os.getxattr": _xattr,
    "os.listdir": _listing, "os.scandir": _listing,
    "os.chdir": _chdir,
    "subprocess.Popen": _popen,
    # The calls subprocess makes for a child it starts: elsewhere, a process the recorder
    # does not follow, as multiprocessing starts.
    "_winapi.CreateProcess": _in_popen, "os.posix_spawn": _in_popen,
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
    "os.kill", "os.killpg", "signal.pthread_kill", "_winapi.CreatePipe", "_winapi.CreateNamedPipe", "_winapi.OpenProcess",
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
    "os.fork": "forks", "os.forkpty": "forks", "os.mkfifo": "makes a special file",
    "os.mknod": "makes a special file",
    "os.startfile": "starts a program", "os.fchdir": "changes the working directory",
}


# --- probes, imports, children, the environment ---------------------------------------

def _probing(r: Recorder, function, hashes: bool, follows: bool):
    """``function`` with every path it is given recorded as a probe; a file whose status
    ``os.stat`` or ``os.lstat`` returns, size included, is recorded as read. A function that
    follows links probes what the link reaches."""

    def wrapped(path, *args, **kwargs):
        if kwargs.get("dir_fd") is not None and not r.in_rmtree():
            r.guarded(lambda: r.refuse("names a path relative to a directory descriptor"))
        elif not isinstance(path, int) and not r.in_rmtree():
            following = follows and kwargs.get("follow_symlinks", True)
            def note():
                text = _text(path)
                absolute = os.path.abspath(os.path.join(_getcwd(), text))
                r.probe(path, follows=following)
                k = kind(absolute)
                if hashes and (k == "file" or k == "link" and following):
                    r.read(path)
            r.guarded(note)
        return function(path, *args, **kwargs)

    return _wrapping(wrapped, function)


def _wrapping(wrapped, function):
    """``wrapped`` standing in for ``function``, in the os.supports_* sets too, which
    shutil reads to decide whether its descriptor-based, link-safe paths are open."""
    wrapped.__wrapped__ = function
    wrapped.__name__ = getattr(function, "__name__", "wrapped")
    wrapped.__doc__ = getattr(function, "__doc__", None)
    for name in ("supports_dir_fd", "supports_fd", "supports_follow_symlinks",
                 "supports_effective_ids"):
        support = getattr(os, name, None)
        if isinstance(support, set) and function in support:
            support.add(wrapped)
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
                result = hit[1] if hit and hit[0] == "repo" else "(elsewhere)"
            r.lookups.setdefault(f"{found[1]}/{fullname.rpartition('.')[2]}", result)
        r.guarded(note)
        return spec

    finder.find_spec = find_spec


def _python_child(argv: list[str]) -> str | None:
    """Why a child started with ``sys.executable`` cannot record itself, or None."""
    options = iter(argv[1:])
    for a in options:
        if a in ("-c", "-m", "-") or not a.startswith("-"):
            return None
        if a in ("-X", "-W", "--check-hash-based-pycs"):
            next(options, None)  # the option's value, in the next argument
            continue
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
            why = _python_child([os.fsdecode(a) for a in argv])
            if env is not None and ENV in env:
                # The recorder took ENV out of the process: the run named one itself.
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
                    if env is not None:
                        # What the run puts in a child's environment is its own.
                        with r.lock:
                            r.child_env.update(
                                _name(k) for k in set(env) | set(os.environ)
                                if env.get(k) != os.environ.get(k))
                    env = dict(os.environ if env is None else env)
                    env[ENV] = child
                    args[env_at] = env
                    with r.lock:
                        r.children.append((child, r.seq))
                finally:
                    r.local.busy = False
        r.local.child, r.local.popen = python, True
        try:
            return original(self, *args)
        finally:
            r.local.child, r.local.popen = False, False

    subprocess.Popen._execute_child = execute_child
    try:
        import _posixsubprocess
    except ImportError:
        return
    fork_exec = _posixsubprocess.fork_exec

    def guarded_fork_exec(*args, **kwargs):
        # subprocess binds fork_exec when it is imported; any other caller, such as
        # multiprocessing, starts a process that leaves no manifest the run can find.
        if not getattr(r.local, "popen", False):
            r.guarded(lambda: r.refuse("starts a process other than through subprocess"))
        return fork_exec(*args, **kwargs)

    _posixsubprocess.fork_exec = guarded_fork_exec


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
        r.local.rmtree = getattr(r.local, "rmtree", 0) + 1  # this thread's calls only
        try:
            return original(path, *args, **kwargs)
        finally:
            r.local.rmtree -= 1

    rmtree.avoids_symlink_attacks = getattr(original, "avoids_symlink_attacks", False)
    shutil.rmtree = rmtree


def _watch_open(r: Recorder) -> None:
    """os.open's audit event leaves out ``dir_fd``: a path relative to a descriptor is
    refused here, where the argument is seen."""
    original = os.open

    def open_(path, flags, mode=0o777, *, dir_fd=None):
        if dir_fd is not None and not r.in_rmtree():
            r.guarded(lambda: r.refuse("names a path relative to a directory descriptor"))
        return original(path, flags, mode, dir_fd=dir_fd)

    os.open = _wrapping(open_, original)


class _Entry:
    """A DirEntry whose ``stat()``, which reports a file's size, is recorded as a read."""

    __slots__ = ("_entry", "_recorder")

    def __init__(self, entry, recorder: Recorder):
        self._entry, self._recorder = entry, recorder

    def __getattr__(self, name):
        return getattr(self._entry, name)

    def __fspath__(self):
        return self._entry.__fspath__()

    def __repr__(self):
        return repr(self._entry)

    def stat(self, *, follow_symlinks=True):
        r, path = self._recorder, os.fsdecode(self._entry.path)
        if not r.in_rmtree():
            def note():
                r.probe(path, follows=follow_symlinks)
                k = kind(os.path.abspath(os.path.join(_getcwd(), path)))
                if k == "file" or k == "link" and follow_symlinks:
                    r.read(path)
            r.guarded(note)
        return self._entry.stat(follow_symlinks=follow_symlinks)


class _Scandir:
    """os.scandir's iterator, handing out recorded entries."""

    def __init__(self, it, recorder: Recorder):
        self._it, self._recorder = it, recorder

    def __iter__(self):
        return self

    def __next__(self):
        return _Entry(next(self._it), self._recorder)

    def __enter__(self):
        self._it.__enter__()
        return self

    def __exit__(self, *exc):
        return self._it.__exit__(*exc)

    def close(self):
        self._it.close()


def _watch_scandir(r: Recorder) -> None:
    original = os.scandir

    def scandir(path="."):
        it = original(path)
        return it if isinstance(path, int) else _Scandir(it, r)

    os.scandir = _wrapping(scandir, original)


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
    # (function, hashes a file, follows a link): readlink reveals where a link points, so
    # it counts as following one.
    for name, hashes, follows in (("stat", True, True), ("lstat", True, False),
                                  ("access", False, True), ("readlink", False, True)):
        setattr(os, name, _probing(r, getattr(os, name), hashes, follows))
    for name, follows in (("exists", True), ("isfile", True), ("isdir", True),
                          ("realpath", True), ("lexists", False), ("islink", False),
                          ("isjunction", False)):
        if hasattr(os.path, name):
            setattr(os.path, name, _probing(r, getattr(os.path, name), False, follows))
    # Only a child the recorder starts gets a directory: one that inherits this one, as a
    # process started some other way would, would write over this manifest.
    os.environ.pop(ENV, None)
    # The interpreter read these before the recorder started: the module search path, its
    # warnings, hash seed, encodings and locale. Named before the mapping records.
    startup = [n for n in os.environ
               if n.upper().startswith(("PYTHON", "LC_")) or n.upper() in ("LANG", "LANGUAGE")]
    os.environ.__class__ = _recording_environ(r, type(os.environ))
    if hasattr(os, "environb"):
        os.environb.__class__ = _recording_environ(r, type(os.environb))
    for name in startup:
        os.environ.get(name)
    _watch_imports(r)
    _watch_children(r)
    _watch_rmtree(r)
    _watch_open(r)
    _watch_scandir(r)
    sys.addaudithook(r.hook)
    atexit.register(r.finish)
    return r
