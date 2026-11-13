"""The recorder (COMP_RECORDER, IF_MANIFEST, DEC_0028): every input one process reads.

A process records itself when ``TRIFECTA_RECORD`` names a directory its parent prepared
with ``prepare``: the ``.pth`` file setup installs in a virtual environment runs that
directory's ``start.py``, which loads this file by its path and calls ``start`` before any
module of the run is imported. From then on the process notes, through Python's audit
hooks and wrappers on the probing functions and ``os.environ``, every file it reads, path
it probes, directory it lists, name the import system looks up and environment variable
it reads, with the fields of ``os.uname`` but the host name, which it fixes, and at exit
writes ``manifest.json`` into the directory. Anything it cannot
follow, from an audit event it does not list to a program other than the interpreter,
makes the manifest unstorable: such a run is never reused, so a blind spot costs time,
never soundness. The one program let through is strace, a known program, on its terms and
only in test_record_trace's own process, keyed on its log (COMP_KNOWN_PROGRAMS).

A Python child that records into a directory of its own, as the recorder's and the
store's tests start, is recorded too (COMP_NESTED_RECORDER): its parent's recorder gives
it a directory under TRIFECTA_RECORD_PARENT, whose .pth file sorts first, so in the
child the parent's recorder starts before the test's, under a module name of its own, and
its wrappers are innermost. It checks at each child start and at exit that its audit hook
and wrappers are still in place.

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
import re
import stat
import sys
import threading

#: The variables the C library reads for the locale, recorded whether set or not.
LOCALE_VARIABLES = ("LC_ALL", "LC_COLLATE", "LC_CTYPE", "LC_MESSAGES", "LC_MONETARY",
                    "LC_NUMERIC", "LC_TIME", "LANG", "LANGUAGE")
#: The variable naming the directory a process records into.
ENV = "TRIFECTA_RECORD"
#: The variable naming the directory the parent's recorder records a child into, when the
#: child runs a recorder of its own under ENV (COMP_NESTED_RECORDER); the name is the
#: design's.
PARENT_ENV = "TRIFECTA_RECORD_PARENT"
#: The result store's variable: like ENV, the recorder's own, so never recorded.
STORE_ENV = "TRIFECTA_STORE"
OWN = frozenset({ENV, PARENT_ENV, STORE_ENV})
#: The ``environment`` key of the digest of every variable's name a run's whole environment
#: held, less the recorder's own: no variable's name holds ``=``, so none is this key.
#: Recorded whenever the run reads the whole environment, by iterating it or by starting a
#: known program, so a variable that appears or vanishes runs it again.
NAMES = "=names"
#: The names the recorder loads under: the test's, under ENV, and the parent's, under
#: PARENT_ENV, which loads first.
MODULE, PARENT_MODULE = "_trifecta_record", "_trifecta_record_parent"
MODULES = (MODULE, PARENT_MODULE)
MANIFEST = "manifest.json"
#: What a process made and wrote, which its parent leaves out of its own inputs.
MADE = "made.json"
CONFIG = "config.json"
START = "start.py"
VERSION = 1
#: Stands for the repository root in recorded values, so a copy elsewhere matches.
ROOT = "<root>"
#: What a reason holds in place of the home directory, the temporary directory and the
#: interpreter's prefixes (COMP_REFUSAL_REASONS); these names are the design's, not ruled.
HOME, TEMP, PREFIX, BASE_PREFIX = "<home>", "<tmp>", "<prefix>", "<base_prefix>"
#: What a .pth line runs when its variable is set: loads the recorder its parent named,
#: once, under the module name that goes with the variable.
_START = """\
import sys
if "{module}" not in sys.modules:
    import importlib.util, json, os
    _d = os.environ["{variable}"]
    with open(os.path.join(_d, "config.json"), encoding="utf-8") as _f:
        _c = json.load(_f)
    # No byte code from the tree, the recorder's own included.
    sys.dont_write_bytecode = True
    sys.pycache_prefix = os.path.join(_d, "pycache")
    _s = importlib.util.spec_from_file_location("{module}", _c["recorder"])
    _m = importlib.util.module_from_spec(_s)
    sys.modules["{module}"] = _m
    _s.loader.exec_module(_m)
    _m.start(_d, _c)
"""
START_SOURCE = _START.format(module=MODULE, variable=ENV)
PARENT_START_SOURCE = _START.format(module=PARENT_MODULE, variable=PARENT_ENV)
_PTH = ('import os; os.environ.get("{0}") and exec(open(os.path.join('
        'os.environ["{0}"], "start.py"), encoding="utf-8").read())\n')
#: The .pth file setup installs, and its one line, which imports nothing while ENV is unset.
#: Named to sort first, so no other .pth file in the environment runs before the recorder.
PTH_NAME = "00-trifecta-record.pth"
PTH_LINE = _PTH.format(ENV)
#: The parent's .pth file, whose name sorts before PTH_NAME, so ``site`` starts the
#: parent's recorder first and its wrappers are innermost (COMP_NESTED_RECORDER).
PARENT_PTH_NAME = "00-trifecta-record-parent.pth"
PARENT_PTH_LINE = _PTH.format(PARENT_ENV)
#: The .pth files setup installs, each with its line, in the order ``site`` runs them.
PTH_FILES = ((PARENT_PTH_NAME, PARENT_PTH_LINE), (PTH_NAME, PTH_LINE))
#: The audit event a recorder raises to see that its own hook still runs.
CHECK_EVENT = "trifecta.record.check"
SECTIONS = ("files", "probes", "listings", "lookups", "environment", "outside", "uname",
            "programs")
KINDS = ("file", "directory", "link", "absent")
#: The host name ``os.uname``, ``posix.uname`` and ``platform`` give inside a recorded run,
#: in place of the machine's (COMP_HOST_NAME). DEC_0039 rules a fixed host name; this
#: value is the design's, not ruled.
HOST_NAME = "localhost"
#: The ``uname`` fields a run records, each as a SHA-256: every one but the host name.
UNAME_FIELDS = ("sysname", "release", "version", "machine")
#: Variables that make an interpreter run code of the run's before ``site`` starts the
#: recorder, from another standard library or from byte code elsewhere, unless ``-E`` or
#: ``-I`` is given: refused.
PRE_SITE = ("PYTHONHOME", "PYTHONPLATLIBDIR", "PYTHONSTARTUP", "PYTHON_FROZEN_MODULES",
            "PYTHONPYCACHEPREFIX")
#: ``-X`` options that do the same, refused under ``-E`` and ``-I`` too.
PRE_SITE_X = ("frozen_modules=off", "pycache_prefix")
#: The warnings variable, whose categories, as ``-W``'s, can name a module to import
#: before ``site``: one outside the standard library is refused, under ``-E`` and ``-I``
#: too.
WARNINGS_ENV = "PYTHONWARNINGS"
#: The search path's variable, whose entries a Python child may take only from inside the
#: repository or the interpreter's prefixes, each a directory (DEC_0042).
PATH_ENV = "PYTHONPATH"
#: The configuration's keys for a child's PYTHONPATH, carried there in place of the
#: environment until its recorder has started: the resolved entries and the value.
SEARCH_PATH, SEARCH_PATH_ENV = "search_path", "search_path_value"
#: The configuration's key for the proof module whose own process records: a known program
#: started only by one module is let through only there (COMP_KNOWN_PROGRAMS).
MODULE_KEY = "module"
#: strace, under DEC_0037: started only by this module, in exactly this form, ``strace -f
#: -y -s 4096 -qq -o LOG COMMAND...``, with LOG under a directory the run made.
STRACE, STRACE_MODULE = "strace", "tests.test_record_trace"
STRACE_FORM = ("-f", "-y", "-s", "4096", "-qq", "-o")
#: The files under /dev a traced command may open; in its own /proc entries it may only list
#: ``fd`` and read the ``exe`` link (COMP_KNOWN_PROGRAMS).
TRACE_DEVICES = ("/dev/null", "/dev/urandom")
#: What a traced process may read of its own /proc entries without a key, besides listing
#: ``fd`` and reading the ``exe`` link (DEC_0043): CPython reads ``maps`` as it starts, and
#: a Rust library ``cgroup`` to count the processors it may use.
TRACE_OWN_PROC = ("maps", "cgroup")
#: The one path a traced command may read through a link the run did not make (DEC_0043):
#: the C library's locale aliases, held by the link's target and what the link reaches,
#: which a lookup takes again, following the link.
FOLLOWED_LINKS = frozenset({"/usr/share/locale/locale.alias"})
#: The families of a socket a traced command may open: a local one, and one of the
#: network's only when it is bound to a loopback address and never connects, sends to an
#: address, listens or accepts (DEC_0043).
TRACE_INET = ("AF_INET", "AF_INET6")
#: How deep a program's ``#!`` interpreters are followed, as the kernel follows them.
MAX_INTERPRETERS = 5
#: Modules other than the standard library's that may be loaded when a recorder starts.
BEFORE_START = frozenset({"__main__"})
#: How many directories above a written path the identity check walks.
MAX_DEPTH = 256

#: The functions the recorder itself calls, taken before any is wrapped. The test's
#: recorder, which loads after the parent's has wrapped them, takes the parent's: what it
#: examines of a path the run touched is its own work, not the run's.
_lstat, _stat, _scandir, _getcwd, _open = os.lstat, os.stat, os.scandir, os.getcwd, io.open
_realpath = os.path.realpath
#: The one lock every recorder in a process takes. Each recorder's hook and wrappers run
#: inside the other's work, as a path one resolves passes the other's wrapper of
#: ``os.lstat`` and an event one raises reaches the other's hook: with a lock each, two
#: threads could hold one and wait for the other.
_LOCK = threading.RLock()
if __name__ == MODULE and PARENT_MODULE in sys.modules:
    _lstat, _stat, _scandir, _realpath, _LOCK = (
        getattr(sys.modules[PARENT_MODULE], name)
        for name in ("_lstat", "_stat", "_scandir", "_realpath", "_LOCK"))


def prepare(directory: str, root: str, ignore=(), recorder: str | None = None,
            parent: bool = False, module: str | None = None) -> None:
    """Make ``directory`` one a process records into: the repository root, the recorder
    file to load, and the run's own control files, which are not inputs. The directory is
    a new one, or an empty one the caller made, such as by ``tempfile.mkdtemp``: what it
    holds is run by the processes that record into it. ``parent`` makes it one the
    parent's recorder starts from, named in PARENT_ENV. A write into it, or into a child's
    directory the recorder makes under it, by anything but a recorder is refused.
    ``module`` names the proof module whose own process records there, which a known
    program started by one module only is judged on."""
    if os.path.islink(directory) or os.path.isdir(directory) and os.listdir(directory):
        raise ValueError(f"{directory} is a link or is not empty")
    os.makedirs(directory, exist_ok=True)
    config = {"root": os.path.abspath(root),
              "recorder": os.path.abspath(recorder or __file__),
              "ignore": [os.path.abspath(p) for p in ignore],
              "top": os.path.abspath(directory),
              "prefixes": _prefixes()}
    if module is not None:
        config[MODULE_KEY] = module
    _write(os.path.join(directory, CONFIG), json.dumps(config))
    _write(os.path.join(directory, START), PARENT_START_SOURCE if parent else START_SOURCE)


def recording() -> bool:
    """Whether a recorder runs in this process, so every Python child it starts is
    recorded too."""
    return any(name in sys.modules for name in MODULES)


def _prefixes() -> list[str]:
    """This interpreter's prefixes, which a child it starts must share."""
    return sorted({os.path.abspath(p) for p in (sys.prefix, sys.base_prefix,
                                                sys.exec_prefix, sys.base_exec_prefix)})


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


_long_path_name = None


def _bind_long() -> None:
    """Bind GetLongPathNameW once, on Windows: before the audit hook, whose ctypes events
    would otherwise refuse the recorder's own call. The test's recorder, which starts
    under the parent's hook, takes the binding the parent's recorder made."""
    global _long_path_name
    if os.name != "nt" or _long_path_name is not None:
        return
    parent = sys.modules.get(PARENT_MODULE)
    if __name__ == MODULE and getattr(parent, "_long_path_name", None) is not None:
        _long_path_name = parent._long_path_name
        return
    import ctypes
    from ctypes import wintypes
    function = ctypes.WinDLL("kernel32", use_last_error=True).GetLongPathNameW
    function.argtypes = (wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD)
    function.restype = wintypes.DWORD
    _long_path_name = (function, ctypes.c_wchar * 32768)


def _long(path: str) -> str:
    """``path`` with any 8.3 short name in it spelled in full, on Windows: one directory
    has two spellings where short names are on, and a run may make it under one and read
    it under the other. The longest part that exists is expanded; the rest is kept."""
    if os.name != "nt" or "~" not in path:
        return path
    _bind_long()
    function, buffer_type = _long_path_name
    buffer = buffer_type()
    head, tail = path, []
    while "~" in head:
        if 0 < function(head, buffer, len(buffer)) < len(buffer):
            return os.path.join(buffer.value, *reversed(tail))
        parent, name = os.path.split(head)
        if parent == head or not name:
            break
        tail.append(name)
        head = parent
    return path


def _norm(path: str) -> str:
    return os.path.normcase(os.path.normpath(_long(path)))


def _root_forms(root: str) -> tuple[str, ...]:
    """The spellings of the root a value may hold: as given, and with forward slashes."""
    return tuple(dict.fromkeys((root, root.replace("\\", "/"))))


#: The placeholders in the order a tie goes: where two places are one path, as the
#: prefix and the base prefix outside a virtual environment, the first wins.
_HOLDERS = (ROOT, PREFIX, BASE_PREFIX, HOME, TEMP)


def _ordered(places: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """``places`` the longest first, a tie going to the placeholder _HOLDERS puts first,
    each path once."""
    out, seen = [], set()
    for path, holder in sorted(places, key=lambda ph: (-len(ph[0]), _HOLDERS.index(ph[1]))):
        key = os.path.normcase(path)
        if key not in seen:
            seen.add(key)
            out.append((path, holder))
    return out


def _replace_paths(text: str, places: list[tuple[str, str]]) -> str:
    """``text`` with each path in ``places`` replaced by its placeholder where no other
    path character follows it, the longest first, in either slash form, ignoring case
    where the system does."""
    forms = [(form, holder) for path, holder in _ordered(places)
             for form in _root_forms(path)]
    flags = re.IGNORECASE if os.name == "nt" else 0
    for form, holder in sorted(forms, key=lambda fh: -len(fh[0])):
        text = re.sub(re.escape(form) + r"(?![^\s'\"\\/])", lambda _, h=holder: h, text,
                      flags=flags)
    return text


#: An absolute path in a reason, of either system: from a slash no word, dot or
#: placeholder precedes, or a drive or a share, to the next space or quote.
_ABSOLUTE = re.compile(r"(?<![\w.<>~/\\-])(?:/|[A-Za-z]:[\\/]|\\\\)[^\s'\"]*")
#: A placeholder a reason holds, which no later replacement reaches into.
_PLACEHOLDER = re.compile(r"(<[^<>\s]*>)")
#: The shortest environment value the backstop searches a reason for: a shorter one, as
#: ``1`` or ``on``, is a word or a digit any reason may hold. Reasons are built from names,
#: paths and module names only, never a value (wyatt, 2026-11-13: "Never put values in
#: (Recommended)"); this bound is the design's, not ruled.
MIN_VALUE = 4
#: Values the backstop leaves alone, which any reason may hold as words.
_WORDS = frozenset({"true", "false", "yes", "no", "on", "off", "none", "null"})
#: How many raised reasons the recorder remembers, so one raised again is not cleaned again.
MAX_RAISED = 1024


def _base_name(path: str) -> str:
    return re.split(r"[\\/]", path.rstrip("\\/"))[-1] or path


def _environment() -> list[tuple[str, str]]:
    """The process environment, read past the recording mapping, so nothing is noted."""
    env = os.environ
    out = []
    for key, value in list(getattr(env, "_data", {}).items()):
        try:
            out.append((env.decodekey(key), env.decodevalue(value)))
        except (AttributeError, UnicodeError, TypeError):
            continue
    return out


def _environment_values() -> list[tuple[str, str]]:
    """Each variable's name with its value, stripped, the longest first, but the recorder's
    own, a value shorter than MIN_VALUE and a bare word such as ``true``."""
    values = ((_name(k), v.strip()) for k, v in _environment())
    return sorted(((n, v) for n, v in values
                   if n not in OWN and len(v) >= MIN_VALUE and v.lower() not in _WORDS),
                  key=lambda nv: -len(nv[1]))


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
        self.config = dict(config)
        #: The directory the chain of recorders this one belongs to was prepared in: a
        #: write under it by anything but a recorder is refused.
        self.top = _norm(config.get("top") or self.directory)
        #: The identity of each path a write's check looked at, forgotten when the run
        #: renames, removes or links.
        self._ids: dict[str, tuple | None] = {}
        #: What the recorder installed, checked at each child start and at exit: each
        #: wrapper as ``(owner, attribute, wrapper, name)``, each recording mapping of the
        #: environment as ``(owner, attribute, class, name)``, and the fixed ``uname``.
        self.installed: list[tuple] = []
        self.mappings: list[tuple] = []
        self.fixed_uname = None
        #: Whether ``start`` installed this recorder, its audit hook last.
        self.started = False
        self.root = _long(config["root"])
        self.nroot = _norm(self.root)
        self.ignore = [_norm(p) for p in config.get("ignore", ())] + [_norm(self.directory)]
        #: The interpreter's prefixes, as given and resolved: one source, ``_prefixes``.
        self.prefixes = _resolved_places(_prefixes())
        self.lock = _LOCK
        self.local = threading.local()
        self.why: str | None = None
        #: Every distinct reason the run was refused, in the order raised, the first of
        #: which is ``why``: each ``{"process": None or a child's name, "why": text}``.
        self.reasons: list[dict] = []
        self._raised: set[tuple] = set()
        self.files: dict[str, str] = {}
        self.outside: dict[str, str] = {}
        self.probes: dict[str, str] = {}
        self.listings: dict[str, list] = {}
        self.lookups: dict[str, str | None] = {}
        self.environment: dict[str, str | None] = {}
        self.uname: dict[str, str] = {}
        self.programs: dict[str, str] = {}
        #: The names of the variables the process started with, which a lookup's
        #: environment is: what NAMES digests. None until ``start`` takes them.
        self.start_names: list[str] | None = None
        #: Each strace started and not yet reaped, by its Popen's id: what its log is taken
        #: with once it has ended.
        self.traces: dict[int, tuple] = {}
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

    def refuse(self, why: str, process: str | None = None) -> None:
        """Refuse the run: the first reason is ``why``, and every distinct one is kept with
        the process that raised it, None for this one, bounded as ``why`` is
        (COMP_REFUSAL_REASONS). Naming a reason changes nothing about storing the run."""
        if process is None:
            # A reason found in a traced command's log is named for strace.
            process = getattr(self.local, "process", None)
        with self.lock:
            if len(self.reasons) >= MAX_REASONS:
                return  # full, and so already refused: nothing more is cleaned
            if (process, why) in self._raised:
                return
            if len(self._raised) < MAX_RAISED:
                self._raised.add((process, why))
            try:
                # A process is built from an executable's base name and a module name only:
                # the value backstop is for a reason's text.
                reason = {"process": None if process is None
                          else self.sanitize(process, values=False)[:MAX_TEXT],
                          "why": self.sanitize(why)[:MAX_TEXT]}
            except Exception:  # naming a reason never raises out of the hook
                reason = {"process": None, "why": "the recorder could not name a reason"}
            if self.why is None:
                self.why = reason["why"]
            if reason not in self.reasons:
                self.reasons.append(reason)

    def note_names(self) -> None:
        """Record the digest of the whole environment's names, as the process started:
        the run read every variable, so one that appears or vanishes changes what it saw.
        What the run itself set or gave a child is its own, and is not in it."""
        names = self.start_names
        if names is None:
            names = [_name(k) for k, _ in _environment()]
        self.note("environment", NAMES, names_digest(names))

    def refused(self) -> bool:
        """Whether the run is refused: from then on only reasons are noted, never inputs."""
        return self.why is not None

    def quiet(self) -> bool:
        """True while the recorder itself is at work."""
        return getattr(self.local, "busy", False)

    def sanitize(self, text: str, values: bool = True) -> str:
        """A reason as a manifest holds it: the root, the home directory, the temporary
        directory and the interpreter's prefixes replaced by their placeholders, any other
        absolute path cut to its base name, and any environment value replaced by the
        variable's name, so a reason holds no value (REQ_REFUSALS_NAMED)."""
        text = _replace_paths(text, self._places())
        text = _ABSOLUTE.sub(lambda m: _base_name(m.group(0)), text)
        if not values:
            return text
        parts = _PLACEHOLDER.split(text)
        for i in range(0, len(parts), 2):  # never inside a placeholder
            for name, value in _environment_values():
                parts[i] = re.sub(r"(?<!\w)" + re.escape(value) + r"(?!\w)",
                                  lambda _, name=name: f"<env:{name}>", parts[i])
        return "".join(parts)

    def shown(self, key: str) -> str:
        """A path as a reason names it, before the reason is formatted: a key relative to
        the root as it is, an absolute one under the root, the interpreter's prefixes, the
        home or the temporary directory as its placeholder and the rest, and any other by
        its base name alone."""
        try:
            if not os.path.isabs(key):
                return key
            n = _norm(key)
            for path, holder in _ordered(self._places()):
                if _under(n, _norm(path)):
                    rest = os.path.relpath(os.path.normpath(_long(key)), os.path.normpath(
                        _long(path)))
                    return holder if rest == "." else f"{holder}/{rest.replace(os.sep, '/')}"
            return _base_name(key)
        except Exception:  # naming a path never raises out of the hook
            return "a path"

    def _places(self) -> list[tuple[str, str]]:
        """Each path a reason holds a placeholder for, with its placeholder."""
        places = [(self.root, ROOT)]
        places += [(p, PREFIX) for p in (sys.prefix, sys.exec_prefix)]
        places += [(p, BASE_PREFIX) for p in (sys.base_prefix, sys.base_exec_prefix)]
        env = dict(_environment())
        places += [(env[n], HOME) for n in ("HOME", "USERPROFILE") if env.get(n)]
        temp = [env[n] for n in ("TMPDIR", "TEMP", "TMP") if env.get(n)]
        tempfile = sys.modules.get("tempfile")
        if isinstance(getattr(tempfile, "tempdir", None), str):
            temp.append(tempfile.tempdir)  # taken only when the run has computed it
        if os.name != "nt":
            temp += ["/tmp", "/var/tmp"]
        places += [(p, TEMP) for p in temp]
        # A place's trailing separators are ignored, as a TMPDIR ending in a slash has.
        places = [(p.rstrip("\\/") or p, h) for p, h in places if isinstance(p, str)]
        return [(p, h) for p, h in places if os.path.isabs(p) and os.path.dirname(p) != p]

    def placeholder(self, text: str) -> str:
        """``text`` with the root's absolute path replaced, ignoring case where the system
        does, in either slash form."""
        for form in _root_forms(self.root):
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
        absolute = _long(os.path.abspath(os.path.join(_getcwd(), path)))
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
        if len(absolute) > MAX_TEXT:
            self.refuse("reaches a path longer than a manifest holds")
            return None
        if not _absolute(absolute):
            # A share or a device namespace, as a long-path prefix spells: no manifest
            # holds such a key, and a lookup would reach out to it.
            self.refuse("reaches a path through a share or a device namespace")
            return None
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
        if found is None or self.refused():
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
            self.refuse(f"{what} through a link: {self.shown(self.where(absolute)[1])}")
            return None
        return _realpath(absolute)

    def note(self, name: str, key: str, value) -> None:
        """Record an input once, with when it was first seen; none once the run is
        refused."""
        if self.refused():
            return
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
        found = None if self.refused() else self.where(absolute)
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
        found = None if followed is None or self.refused() else self.where(followed)
        if found is None:
            return
        _, key, absolute = found
        if key in self.listings:
            return
        entries = listing(absolute)
        if entries is None:
            self.probe(absolute)
            return
        # A directory the run made is its output, not part of what it found: the build
        # lists docs/_build after making html in it.
        keep = [e for e in entries
                if not any(_under(_norm(os.path.join(absolute, e[0])), i)
                           for i in (*self.ignore, *self.created))]
        self.note("listings", key, keep)

    def wrote(self, raw, directory: bool = False) -> None:
        path = _text(raw)
        if path is None:
            return
        joined = os.path.join(_getcwd(), path)
        if self.in_top(joined):
            # A recorder's own writes raise no event it handles: this one is the run's,
            # which could rewrite a configuration or a manifest a recorder reads.
            self.refuse("writes into a directory the recorder prepared")
        if self.lands(joined, self.prefixes):
            # A .pth file or a module there runs in every child before the recorder.
            self.refuse("writes under the interpreter's prefixes")
        if any(_norm(os.path.abspath(joined)) == _norm(t.log) for _, t in self.traces.values()):
            # strace's log is the key of what it traced until the recorder has taken it.
            self.refuse("writes the log of a strace still running")
        (self.created if directory else self.written).add(_norm(os.path.abspath(joined)))

    def in_top(self, path: str) -> bool:
        """Whether ``path`` is in ``top`` however it is spelled, as ``lands`` judges."""
        return self.lands(path, [self.top])

    def lands(self, path: str, places: list[str]) -> bool:
        """Whether ``path``, joined to the working directory with its ``..`` not yet taken
        lexically, is under one of ``places`` however it is spelled: as written, once its
        links and ``..`` are resolved, or in a directory that is one of them by its device
        and file number, as a share, a long-path prefix or a mount reaches it."""
        if any(_under(_norm(path), place) for place in places):
            return True
        try:
            resolved = _realpath(path)
        except (OSError, ValueError):
            resolved = os.path.abspath(path)
        if any(_under(_norm(resolved), place) for place in places):
            return True
        found = {i for i in map(self.identity, places) if i is not None}
        if not found:
            return False
        current = resolved
        for _ in range(MAX_DEPTH):
            if self.identity(current) in found:
                return True
            parent = os.path.dirname(current)
            if parent == current:
                return False
            current = parent
        return True  # deeper than any path: refused rather than walked

    def identity(self, path: str) -> tuple | None:
        if path not in self._ids:
            self._ids[path] = _identity(path)
        return self._ids[path]

    def inside(self, path: str) -> bool:
        """Whether ``path``, resolved, is under the repository root or the interpreter's
        prefixes, each as given and resolved."""
        n = _norm(path)
        return any(_under(n, place) for place in self.places_inside())

    def places_inside(self) -> list[str]:
        """The repository root and the prefixes; for the test's recorder in a process the
        parent's records too, the parent's root as well, which the parent judges against:
        the test chose this one's."""
        roots = [self.root]
        parent = getattr(sys.modules.get(PARENT_MODULE), "_recorder", None)
        if __name__ == MODULE and parent is not None and hasattr(parent, "root"):
            roots.append(parent.root)
        return [*_resolved_places(roots), *self.prefixes]

    def links_into_top(self, absolute: str) -> bool:
        """Whether ``absolute`` is a file with another name in ``top``: a hard link to a
        manifest or a configuration a recorder wrote."""
        try:
            st = _stat(absolute)
        except (OSError, ValueError):
            return False
        if st.st_nlink < 2 or not stat.S_ISREG(st.st_mode):
            return False
        mine = (st.st_dev, st.st_ino)
        return any(_identity(path) == mine for path in _walk(self.top))

    def moved(self) -> None:
        """Forget what each directory a write named was: the run renamed, removed or
        linked something."""
        self._ids.clear()

    def install(self, owner, attribute: str, wrapper, name: str) -> None:
        """Put ``wrapper`` in place of ``owner.attribute``, to be checked later."""
        setattr(owner, attribute, wrapper)
        self.installed.append((owner, attribute, wrapper, name))

    def intact(self) -> str | None:
        """What of the recorder's own is no longer in place, or None: its audit hook, which
        must still see an event; each wrapper, which must be the attribute or be reached
        from it through ``__wrapped__`` by way of wrappers a recorder installed, as the
        test's recorder's reach the parent's; the environment's recording mappings; and
        the fixed ``uname``."""
        token = object()
        self.local.audited = None
        sys.audit(CHECK_EVENT, token)
        if self.local.audited is not token:
            return "its audit hook"
        known = {id(w) for r in _recorders(self) for _, _, w, _ in r.installed}
        for owner, attribute, wrapper, name in self.installed:
            current = getattr(owner, attribute, None)
            for _ in range(MAX_CHAIN):
                if current is wrapper or id(current) not in known:
                    break
                current = getattr(current, WRAPPED, None) or getattr(
                    current, "__wrapped__", None)
            if current is not wrapper:
                return name
        for owner, attribute, cls, name in self.mappings:
            if not isinstance(getattr(owner, attribute, None), cls):
                return name
        if self.fixed_uname is not None:
            import posix
            if os.uname() != self.fixed_uname or posix.uname() != self.fixed_uname:
                return "os.uname"
        return None

    def check_intact(self) -> None:
        """Refuse the run when what the recorder installed is no longer in place, or when
        it cannot tell; nothing raises out of the check."""
        try:
            what = self.intact() if self.started else None
        except Exception as exc:
            what = f"the check failed: {type(exc).__name__}"
        if what is not None:
            self.refuse(f"replaces what the recorder installed: {what}")

    # -- the audit hook -----------------------------------------------------------

    def hook(self, event: str, args: tuple) -> None:
        if event == CHECK_EVENT:  # the recorder's own check that this hook still runs
            self.local.audited = args[0] if args else None
            return
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
            if self.traces:
                # Its log may not be whole, and what it traced may still run.
                self.refuse("starts strace and does not wait for it")
            if self.why is None:
                for _, origin in _module_origins():
                    self.read(origin)
            for child, started, process in self.children:
                self._merge(child, started, process)
            data = {"version": VERSION, "storable": self.why is None}
            if self.why is not None:
                data["why"] = self.why
                data["reasons"] = list(self.reasons)
            for name in SECTIONS:
                data[name] = dict(sorted(getattr(self, name).items()))
            return data

    def _merge(self, child: str, started: int, process: str) -> None:
        """Take in a child's manifest: its reasons under its name, a reason its own child
        raised under both names, and its inputs."""
        try:
            with _open(os.path.join(child, MANIFEST), encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            self.refuse("a Python child left no manifest", process)
            return
        if not valid(data):
            self.refuse("a Python child left a malformed manifest", process)
            return
        if not data["storable"]:
            # A refused manifest with no ``why`` and so no ``reasons``, which valid allows.
            for reason in data.get("reasons") or [{"process": None, "why": data.get(
                    "why") or "a Python child was not storable"}]:
                inner = reason["process"]
                self.refuse(reason["why"], process if inner is None else f"{process} > {inner}")
        try:
            with _open(os.path.join(child, MADE), encoding="utf-8") as f:
                made = json.load(f)
            created = {str(p) for p in made["created"]}
            written = {str(p) for p in made["written"]}
        except (OSError, ValueError, KeyError, TypeError):
            self.refuse("a Python child left no record of what it made", process)
            return
        self._drop_made(created, written, started)
        for name in SECTIONS:
            for key, value in data[name].items():
                if name == "environment" and key == NAMES:
                    # The child's environment is this one's, as this one gave it: what
                    # appears or vanishes is seen in this one's names.
                    self.note_names()
                    continue
                if name == "environment" and key in self.env_set | self.child_env:
                    continue  # a variable the run set is its own, in its children too
                if getattr(self, name).get(key, value) != value:
                    # A variable's or a field's name, a path, or a directory and a name.
                    if name in ("environment", "uname"):
                        shown = key
                    elif name == "lookups":
                        directory, _, looked = key.rpartition("/")
                        shown = f"{self.shown(directory)}/{looked}"
                    else:
                        shown = self.shown(key)
                    self.refuse(f"a Python child and its parent saw {shown} differently",
                                process)
                self.note(name, key, value)

    def _drop_made(self, created: set, written: set, started: int) -> None:
        """Leave out what the parent first saw after a child started, under what that
        child made or wrote: such a path was the child's output when the parent read it.
        What the parent saw before is an input, and so is a path found absent."""
        def made(key: str) -> bool:
            n = _norm(key if os.path.isabs(key) else os.path.join(self.root, key))
            return n in written or any(_under(n, c) for c in created)
        for name in ("files", "outside", "probes", "listings", "programs"):
            section = getattr(self, name)
            for key in [k for k, v in section.items() if v != "absent" and made(k)
                        and self.first.get((name, k), 0) > started]:
                del section[key]

    def finish(self) -> None:
        self.local.busy = True
        with self.lock:
            self.check_intact()
        data = self.manifest()
        target = os.path.join(self.directory, MANIFEST)
        if os.path.exists(target):  # another process wrote here: whose reads is unknown
            why = "two processes recorded into one place"
            first = {"process": None, "why": why}
            data = {**data, "storable": False, "why": why,
                    "reasons": [first, *(r for r in data.get("reasons", [])
                                         if r != first)][:MAX_REASONS]}
        _write(os.path.join(self.directory, MADE),
               json.dumps({"created": sorted(self.created), "written": sorted(self.written)}))
        _write(target + ".tmp", json.dumps(data, sort_keys=True))
        os.replace(target + ".tmp", target)


#: Bounds on what a manifest read from a store may hold, which is data from another run.
MAX_ENTRIES, MAX_TEXT = 200_000, 4096
#: How many reasons a refused manifest keeps; the bound is the design's, not ruled.
MAX_REASONS = 64
def _recorders(r: Recorder) -> list[Recorder]:
    """``r`` and every other recorder started in this process."""
    found = [r]
    for name in MODULES:
        other = getattr(sys.modules.get(name), "_recorder", None)
        if other is not None and other is not r and hasattr(other, "installed"):
            found.append(other)
    return found


def _identity(path: str) -> tuple | None:
    """A path's device and file number, following links, or None when it is none."""
    try:
        st = _stat(path)
    except (OSError, ValueError):
        return None
    return st.st_dev, st.st_ino


def _walk(top: str):
    """The path of each file under ``top``, through the recorder's own listing, not
    following links."""
    stack = [top]
    while stack:
        directory = stack.pop()
        try:
            with _scandir(directory) as it:
                entries = list(it)
        except OSError:
            continue
        for e in entries:
            if e.is_dir(follow_symlinks=False):
                stack.append(e.path)
            else:
                yield e.path


def _resolved_places(paths) -> list[str]:
    """Each of ``paths`` normalized, as given and with its links resolved."""
    places = []
    for path in paths:
        places.append(_norm(path))
        try:
            places.append(_norm(_realpath(path)))
        except (OSError, ValueError):
            pass
    return sorted(set(places))


def _module_origins():
    """``(name, file)`` for each loaded module with a file, the recorders' own left out:
    the recorder is part of the package's identity."""
    for name, module in list(sys.modules.items()):
        if name in MODULES:
            continue
        origin = getattr(getattr(module, "__spec__", None), "origin", None)
        if isinstance(origin, str) and os.path.isabs(origin):
            yield name, origin


#: How many ``__wrapped__`` steps the check follows from an attribute to a wrapper.
MAX_CHAIN = 64
#: What a wrapper whose original ``inspect.unwrap`` must not reach names it by.
WRAPPED = "_trifecta_wrapped"
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
    """An absolute local path: never a network share or a device namespace, which a
    lookup would reach out to."""
    if not (isinstance(key, str) and 0 < len(key) <= MAX_TEXT and "\0" not in key):
        return False
    slashed = key.replace("\\", "/")
    return (os.path.isabs(key) and not slashed.startswith("//")
            and ".." not in slashed.split("/"))


def _path(key) -> bool:
    return _relative(key) or _absolute(key)


def _lookup_key(key) -> bool:
    """A directory and the name looked up in it: an identifier, or one with dashes, as
    the interpreter's own ``_sysconfigdata`` module on Linux has."""
    if not isinstance(key, str):
        return False
    directory, _, name = key.rpartition("/")
    return name.replace("-", "_").isidentifier() and _path(directory)


def _reasons(reasons, why: str) -> bool:
    """A refused manifest's reasons: at most MAX_REASONS, each a process, None for the
    run's own, and a text within MAX_TEXT, the first of which is ``why``."""
    text = lambda v: isinstance(v, str) and 0 < len(v) <= MAX_TEXT and "\0" not in v
    return (isinstance(reasons, list) and 0 < len(reasons) <= MAX_REASONS
            and all(isinstance(r, dict) and set(r) == {"process", "why"}
                    and (r["process"] is None or text(r["process"])) and text(r["why"])
                    for r in reasons)
            and reasons[0]["why"] == why)


def valid(data) -> bool:
    """Whether ``data`` has exactly the shape IF_MANIFEST states, within bounds: what a
    store holds came from another run, so it is checked before anything reads it. The
    ``uname`` requirement is read on the platform that checks: where ``os.uname`` exists,
    every field is required."""
    if not (isinstance(data, dict) and type(data.get("version")) is int
            and data["version"] == VERSION and type(data.get("storable")) is bool
            and set(data) <= {"version", "storable", "why", "reasons", *SECTIONS}
            and all(isinstance(data.get(s), dict) for s in SECTIONS)):
        return False
    if "why" in data and (data["storable"] or not isinstance(data["why"], str)
                          or len(data["why"]) > MAX_TEXT):
        return False
    if ("why" in data) != ("reasons" in data):
        return False
    if "reasons" in data and not _reasons(data["reasons"], data["why"]):
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
            and all((name(k) or k == NAMES) and (v is None or _digest(v))
                    and (k != NAMES or v is not None)
                    for k, v in data["environment"].items())
            and all(k in UNAME_FIELDS and _digest(v) for k, v in data["uname"].items())
            and all(_path(k) and _digest(v) for k, v in data["programs"].items())
            # Where os.uname exists, the recorder takes every field at the start of a run.
            and (not hasattr(os, "uname") or set(data["uname"]) == set(UNAME_FIELDS)))


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
        text = _text(path)
        if text is not None and r.links_into_top(os.path.join(_getcwd(), text)):
            r.refuse("writes into a directory the recorder prepared")


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


def _refuse_taking(r: Recorder, raw, prefixes: bool = True) -> bool:
    """Refuse moving, copying or linking a path out of a recorder's prepared directory,
    where put back or linked it could stand for what a recorder wrote, and, unless
    ``prefixes`` is False, moving or linking one out of the interpreter's prefixes, whose
    other name a write would change; True when refused."""
    text = _text(raw)
    r.moved()
    if text is None:
        return False
    path = os.path.join(_getcwd(), text)
    if r.in_top(path):
        r.refuse("writes into a directory the recorder prepared")
        return True
    if prefixes and r.lands(path, r.prefixes):
        r.refuse("writes under the interpreter's prefixes")
        return True
    return False


def _rename(r: Recorder, args) -> None:
    if _by_descriptor(r, "os.rename", args) or _refuse_taking(r, args[0]):
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
    r.moved()
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
    if _refuse_taking(r, args[0], prefixes=False):
        return
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
    r.moved()
    if not _by_descriptor(r, "os.symlink", args):
        r.wrote(args[1])


def _xattr(r: Recorder, args) -> None:
    if args and not isinstance(args[0], int):
        r.probe(args[0])


def _hardlink(r: Recorder, args) -> None:
    # A hard link is another name for the same content: the run reads its source.
    if not _by_descriptor(r, "os.link", args) and not _refuse_taking(r, args[0]):
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
    if getattr(r.local, "known", False):
        return  # a known program, let through on its terms
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


#: The modules that hold ``uname``: imported afresh, one gives the machine's host name.
UNAME_MODULES = frozenset({"posix"})


class _Named:
    """A module spec whose name is the one value the recorder checked; every other
    attribute is the spec's own."""

    def __init__(self, name, spec):
        self.name, self._spec = name, spec

    def __getattr__(self, attribute):
        return getattr(self._spec, attribute)


def _import(r: Recorder, args) -> None:
    """The ``import`` event comes only for a module not in ``sys.modules``: once the
    recorder has fixed the host name, a new ``posix`` would give the real one."""
    if r.fixed_uname is not None and args[0] in UNAME_MODULES:
        r.refuse(f"imports {args[0]} again")


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
    "import": _import,
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
    "compile", "exec", "marshal.loads", "marshal.load", "marshal.dumps",
    "code.__new__", "function.__new__", "sys._getframe", "sys._getframemodulename",
    "sys._current_frames", "sys._current_exceptions", "sys.addaudithook",
    "sys.excepthook", "sys.unraisablehook", "sys.settrace", "sys.setprofile",
    "sys.set_asyncgen_hooks_firstiter", "sys.set_asyncgen_hooks_finalizer",
    "sys.monitoring.register_callback", "sys.setrecursionlimit",
    "cpython.run_command", "cpython.run_module", "cpython.run_file", "cpython.run_startup",
    "cpython.run_interactivehook",
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
    # A new interpreter has none of the recorder's hooks or wrappers.
    "cpython.PyInterpreterState_New": "starts another interpreter",
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
            if r.refused():
                return
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

    find_spec.__wrapped__ = original
    r.install(finder, "find_spec", find_spec, "FileFinder.find_spec")


def _options(argv: list[str]) -> tuple[str, str | None, dict[str, list[str]]]:
    """The one-letter options of an interpreter's command line, up to ``-c``, ``-m``, ``-``
    or a script, the module ``-m`` names, if any, and the values of its ``-X`` and ``-W``
    options by letter: ``-Bm kid`` and ``-mkid`` name ``kid``, and a value given with
    ``-X`` or ``-W``, attached or not, is no option."""
    flags, values = "", {"X": [], "W": []}
    options = iter(argv[1:])
    for a in options:
        if a in ("-c", "-") or not a.startswith("-"):
            break
        if a == "-m":
            return flags, next(options, None), values
        if a in ("-X", "-W", "--check-hash-based-pycs"):
            value = next(options, None)  # the option's value, in the next argument
            if a[1] in values and value is not None:
                values[a[1]].append(value)
            continue
        if a.startswith("--"):
            continue
        rest = a[1:]
        for i, c in enumerate(rest):
            if c in "XW":
                value = rest[i + 1:] or next(options, None)  # attached, or the next
                if value is not None:
                    values[c].append(value)
                break
            if c == "c":
                return flags, None, values
            if c == "m":
                return flags, rest[i + 1:] or next(options, None), values
            flags += c
    return flags, None, values


def _interpreter_options(argv: list[str]) -> tuple[str, str | None]:
    """The one-letter options and the module ``-m`` names, as ``_options`` reads them."""
    return _options(argv)[:2]


def _warning_module(spec: str) -> str | None:
    """The module a warnings filter's category imports, ``action:message:category:...``,
    when it is not the standard library's or the built-ins'."""
    parts = spec.split(":")
    category = parts[2].strip() if len(parts) > 2 else ""
    module = category.rpartition(".")[0]
    if not module or module.partition(".")[0] in _standard_names():
        return None
    return module


def _standard_names() -> frozenset:
    return frozenset(getattr(sys, "stdlib_module_names", ())) | frozenset(
        sys.builtin_module_names)


def _python_child(argv: list[str], env: dict | None = None, inside=None,
                  cwd: str | None = None, prefixes: list[str] = ()) -> str | None:
    """Why a child started with ``sys.executable`` cannot record itself, or None: it
    runs no .pth file, or it can run code of the run's before ``site`` starts the
    recorder, through a variable in ``env``, its final environment by name, that ``-E``
    or ``-I`` does not cancel, through a PYTHONPATH entry that ``inside`` does not hold
    or that is not a directory, once resolved from ``cwd``, the child's working directory,
    through a warnings category outside the standard library, or through an ``-X`` option
    of PRE_SITE_X."""
    flags, _, values = _options(argv)
    if "S" in flags:
        return "starts a Python child with -S, which runs no .pth file"
    for x in values["X"]:
        for option in PRE_SITE_X:
            if x.replace(" ", "").startswith(option):
                return (f"starts a Python child with -X {option}, which can run code "
                        f"before the recorder")
    variable = os.fsdecode((env or {}).get(WARNINGS_ENV) or "")
    for spec in [*values["W"], *variable.split(",")]:
        if _warning_module(spec):
            return ("starts a Python child whose warnings filter names a category outside "
                    "the standard library, which can run code before the recorder")
    if env and not ("E" in flags or "I" in flags):
        for name in PRE_SITE:
            if env.get(name):
                return (f"starts a Python child whose environment sets {name}, which can "
                        f"run code before the recorder")
        return _search_path_refused(_search_path(env.get(PATH_ENV), cwd), inside, prefixes)
    return None


def _search_path(value, cwd: str | None) -> list[str]:
    """Each entry of a PYTHONPATH value as the interpreter reaches it: an empty one is the
    working directory, a relative one is under it, and every link is resolved."""
    if not value:
        return []
    base = cwd if cwd is not None else _getcwd()
    entries = []
    for entry in os.fsdecode(value).split(os.pathsep):
        try:
            entries.append(_realpath(os.path.join(base, entry)))
        except (OSError, ValueError):
            entries.append(os.path.abspath(os.path.join(base, entry)))
    return entries


def _search_path_refused(entries: list[str], inside, prefixes: list[str]) -> str | None:
    """Why a child with these search-path entries is refused, or None: an entry outside
    the repository and the prefixes, one that is not a directory, as a zip is, or one
    outside the prefixes that holds a name of the standard library."""
    for entry in entries:
        if inside is None or not inside(entry):
            return (f"starts a Python child whose {PATH_ENV} names a directory outside the "
                    f"repository and the interpreter")
        if kind(entry) != "directory":
            return (f"starts a Python child whose {PATH_ENV} names something that is not a "
                    f"directory")
        shadow = _shadow(entry, prefixes)
        if shadow:
            return (f"starts a Python child whose {PATH_ENV} holds {shadow}, a name of the "
                    f"standard library")
    return None


def _shadow(directory: str, prefixes: list[str]) -> str | None:
    """The first name of the standard library a search-path entry holds, outside the
    interpreter's own ``prefixes``, which would load in its place, before ``site`` or as
    the recorder starts; or None."""
    if any(_under(_norm(directory), p) for p in prefixes):
        return None
    names = {n.split(".")[0] for n, _ in listing(directory) or ()}
    found = sorted(names & set(getattr(sys, "stdlib_module_names", ())))
    return found[0] if found else None


def _child_name(argv: list[str], program: str) -> str:
    """A Python child as its reasons name it: its executable's base name, and ``-m`` with
    the module when it was started so; nothing else of its command."""
    name = os.path.basename(program)
    name = name[:-4] if name.lower().endswith(".exe") else name
    module = _interpreter_options(argv)[1]
    if module and all(part.isidentifier() for part in module.split(".")):
        return f"{name} -m {module}"
    return name


def _prepare_child(r: Recorder, env, final: dict, name: str, token: str,
                   search_path: list[str] | None = None):
    """Make a Python child's directory and give it the environment that names it: under
    PARENT_ENV when the run named one of its own under ENV, which this recorder leaves to
    the run's, and under ENV otherwise. ``search_path``, the resolved PYTHONPATH entries
    the start was judged on, goes into the child's configuration in place of the variable,
    which the child's recorder puts back once it has started. Returns the environment the
    child starts with."""
    r.local.busy = True
    try:
        child = os.path.join(r.directory, "children", token)
        nested = ENV in final
        config = dict(r.config)
        # What the parent made or wrote is no input to its child either.
        with r.lock:
            config["ignore"] = sorted({*config.get("ignore", ()), *r.created, *r.written})
        config["top"] = r.config.get("top") or r.directory
        config["prefixes"] = _prefixes()
        config.pop(SEARCH_PATH, None)
        config.pop(SEARCH_PATH_ENV, None)
        # A child is not the module's own process: a program only the module may start
        # stays refused there.
        config.pop(MODULE_KEY, None)
        given = {_name(k): v for k, v in final.items()}.get(PATH_ENV)
        if search_path is not None and given:
            config[SEARCH_PATH], config[SEARCH_PATH_ENV] = search_path, os.fsdecode(given)
        os.makedirs(child)
        _write(os.path.join(child, CONFIG), json.dumps(config))
        _write(os.path.join(child, START), PARENT_START_SOURCE if nested else START_SOURCE)
        if env is not None:
            # What the run puts in a child's environment is its own.
            here = {_name(k): v for k, v in _environment()}
            with r.lock:
                r.child_env.update(n for n in set(final) | set(here)
                                   if final.get(n) != here.get(n))
        env = dict(_environment()) if env is None else dict(env)
        if SEARCH_PATH in config:
            env = _without_search_path(env)
        env[PARENT_ENV if nested else ENV] = child
        with r.lock:
            r.children.append((child, r.seq, name))
        return env
    except (OSError, ValueError) as exc:
        if not r.refused():
            raise
        # A run already refused records its child only to name its reasons: this child
        # then starts unrecorded, and its own reasons go unnamed.
        r.refuse(f"the recorder could not prepare a Python child: {type(exc).__name__}")
        return env
    finally:
        r.local.busy = False


def _without_search_path(env: dict) -> dict:
    """``env`` without PYTHONPATH, however its name is spelled."""
    return {k: v for k, v in env.items() if _name(k) != PATH_ENV}


def carry_search_path(directory: str, env: dict) -> dict:
    """``env`` for a recorded Python child that honours the environment, started by a
    process no recorder runs in, with PYTHONPATH taken out into the configuration of
    ``directory``, which ``prepare`` made: the child's recorder puts it back once it has
    started, so nothing on it runs before the recorder (COMP_NESTED_RECORDER)."""
    value = {_name(k): v for k, v in env.items()}.get(PATH_ENV)
    if not value:
        return env
    path = os.path.join(directory, CONFIG)
    with _open(path, encoding="utf-8") as f:
        config = json.load(f)
    config[SEARCH_PATH] = _search_path(value, None)
    config[SEARCH_PATH_ENV] = os.fsdecode(value)
    _write(path, json.dumps(config))
    return _without_search_path(env)


def _restore_search_path(config: dict) -> None:
    """Put back the PYTHONPATH a parent's recorder took out of this process's start: its
    entries, as the parent resolved them, where the interpreter would have put them, ahead
    of the standard library, and the variable, for the run's own children, set past any
    recording mapping, since this is the recorder's act; the run reads it as before."""
    entries, value = config.get(SEARCH_PATH), config.get(SEARCH_PATH_ENV)
    if sys.flags.ignore_environment or not isinstance(entries, list) \
            or not isinstance(value, str):
        return
    sys.path[0:0] = [e for e in entries if isinstance(e, str)]
    os._Environ.__setitem__(os.environ, PATH_ENV, value)


# --- known programs: strace -------------------------------------------------------------

class _Trace:
    """A strace the run started on its terms: its log, which the recorder takes once strace
    has ended, and the working directory its command starts in."""

    __slots__ = ("log", "cwd")

    def __init__(self, log: str, cwd: str):
        self.log, self.cwd = log, cwd


def _program_hash(path: str) -> str | None:
    """The SHA-256 of the regular file ``path`` reaches, its links followed, as the kernel
    reaches a program; None for anything else."""
    try:
        if not stat.S_ISREG(_stat(path).st_mode):
            return None
    except (OSError, ValueError):
        return None
    return file_hash(path)


def _head(path: str, size: int = 256) -> bytes:
    """The first bytes of a program, as the kernel reads them to choose how to run it."""
    try:
        with _open(path, "rb") as f:
            return f.read(size)
    except (OSError, ValueError):
        return b""


def _elf_interpreter(path: str) -> str | None:
    """The ELF interpreter a program names in its PT_INTERP header, which the kernel opens
    with no call a trace shows; None for a program that names none. ValueError when the
    headers cannot be read."""
    import struct
    with _open(path, "rb") as f:
        head = f.read(64)
        if head[:4] != b"\x7fELF":
            return None
        if len(head) < 64 or head[4] not in (1, 2) or head[5] not in (1, 2):
            raise ValueError("an ELF header the recorder cannot read")
        end = "<" if head[5] == 1 else ">"
        wide = head[4] == 2
        if wide:
            (phoff,) = struct.unpack(end + "Q", head[32:40])
            phentsize, phnum = struct.unpack(end + "HH", head[54:58])
        else:
            (phoff,) = struct.unpack(end + "I", head[28:32])
            phentsize, phnum = struct.unpack(end + "HH", head[42:46])
        if phentsize < (56 if wide else 32) or phnum > 4096:
            raise ValueError("an ELF header the recorder cannot read")
        for i in range(phnum):
            f.seek(phoff + i * phentsize)
            ph = f.read(phentsize)
            if len(ph) < phentsize:
                raise ValueError("an ELF header the recorder cannot read")
            if struct.unpack(end + "I", ph[:4])[0] != 3:  # PT_INTERP
                continue
            if wide:
                (offset,) = struct.unpack(end + "Q", ph[8:16])
                (size,) = struct.unpack(end + "Q", ph[32:40])
            else:
                (offset,) = struct.unpack(end + "I", ph[4:8])
                (size,) = struct.unpack(end + "I", ph[16:20])
            f.seek(offset)
            raw = f.read(min(size, MAX_TEXT)).split(b"\0")[0]
            if not raw:
                raise ValueError("an ELF interpreter with no name")
            return os.fsdecode(raw)
    return None


def _script_interpreter(head: bytes) -> str | None:
    """The interpreter a ``#!`` line names, as the kernel reads it: the first word after
    ``#!`` and any blanks, in the first line."""
    if not head.startswith(b"#!"):
        return None
    line = head[2:].split(b"\n")[0].lstrip(b" \t")
    word = re.split(rb"[ \t\0]", line)[0]
    return os.fsdecode(word) if word else None


def _program_key(r: Recorder, absolute: str) -> str | None:
    """A program's key, relative to the root inside it and absolute elsewhere; None for one
    the run made or holds as its own, which is no input. Unlike a read, a program under the
    interpreter's prefixes is keyed too."""
    n = _norm(absolute)
    if n in r.written or any(_under(n, c) for c in r.created) \
            or any(_under(n, i) for i in r.ignore) or _under(n, r.top):
        return None
    if _under(n, r.nroot):
        rel = absolute[len(r.root):].lstrip("\\/").replace(os.sep, "/")
        return rel or "."
    if len(absolute) > MAX_TEXT or not _absolute(absolute):
        r.refuse("starts a program at a path no manifest holds")
        return None
    return absolute


def _note_program(r: Recorder, path: str, cwd: str, depth: int = 0) -> None:
    """Record a program started, by its path and the SHA-256 of what the path reaches, with
    its ``#!`` interpreter, followed again, and its ELF interpreter."""
    absolute = os.path.normpath(os.path.join(cwd, path))
    if depth > MAX_INTERPRETERS:
        r.refuse("starts a program through more #! interpreters than the kernel follows")
        return
    digest = _program_hash(absolute)
    if digest is None:
        r.refuse(f"starts {r.shown(absolute)}, which is not a regular file")
        return
    key = _program_key(r, absolute)
    if key is not None:
        if r.programs.get(key, digest) != digest:
            r.refuse(f"starts {r.shown(absolute)}, which changed while the run ran")
            return
        r.note("programs", key, digest)
    head = _head(absolute)
    script = _script_interpreter(head)
    if script is not None:
        _note_program(r, script, cwd, depth + 1)
        return
    if head.startswith(b"#!"):
        r.refuse(f"starts {r.shown(absolute)}, whose #! line names no interpreter")
        return
    if not head.startswith(b"\x7fELF"):
        # The kernel hands any other format to a handler it registered, which no call in
        # the log names, as WSL runs a Windows program.
        r.refuse(f"starts {r.shown(absolute)}, which is neither a script nor an ELF program")
        return
    try:
        interpreter = _elf_interpreter(absolute)
    except (OSError, ValueError):
        r.refuse(f"starts {r.shown(absolute)}, whose ELF headers the recorder cannot read")
        return
    if interpreter is not None:
        _note_program(r, interpreter, cwd, depth + 1)


def _found_program(r: Recorder, program: str, final: dict, cwd: str) -> str | None:
    """The file ``program`` names, as subprocess finds it on POSIX: a name with a directory
    from the child's working directory, any other along PATH, the first regular file that
    may be executed; each one before it is recorded as probed, whatever its place, so a
    program planted on PATH runs the module again."""
    if os.path.dirname(program):
        candidates = [program]
    else:
        value = final.get("PATH")
        value = os.defpath if value is None else os.fsdecode(value)
        candidates = [os.path.join(d or ".", program) for d in value.split(os.pathsep)]
    for candidate in candidates:
        absolute = os.path.normpath(os.path.join(cwd, candidate))
        try:
            st = _stat(absolute)
            found = stat.S_ISREG(st.st_mode) and st.st_mode & 0o111
        except (OSError, ValueError):
            found = False
        if found:
            return absolute
        key = _program_key(r, absolute)
        if key is not None:
            r.note("probes", key, kind(absolute))
    return None


def _whole_environment(r: Recorder, env, final: dict) -> None:
    """Record every variable that reaches a known program, inherited or given, as a hash,
    less the recorder's own, those the run set, and those whose value the run gave it in
    ``env``, as the recorder treats them, so a path the run made is never part of a key."""
    here = {_name(k): v for k, v in _environment()}
    for name, value in sorted(final.items()):
        if name in OWN or name in r.env_set:
            continue
        if env is not None and here.get(name) != value:
            continue  # a value the run put in the mapping is its own
        text = os.fsdecode(value) if isinstance(value, bytes) else str(value)
        r.note("environment", name, hashlib.sha256(
            r.placeholder(text).encode("utf-8", "surrogateescape")).hexdigest())
    # And which names it held, so a variable that appears or vanishes reruns the module.
    r.note_names()


def _strace_start(r: Recorder, argv: list[str], program: str, env, final: dict,
                  cwd: str, shell, preexec_fn, close_fds, pass_fds,
                  ) -> tuple[str | None, _Trace | None, str | None]:
    """Why a start of strace is refused, or None with what its log is taken with and the
    path it is executed by: strace is let through only when the module's own process is
    test_record_trace's, with exactly ``-f -y -s 4096 -qq -o LOG COMMAND...``, LOG new and
    under a directory the run made, and strace a regular ELF file outside the repository and
    the run's own directories, executed by the path it was found at. Its path and hash, its
    ELF interpreter's and the whole environment are recorded as it starts
    (COMP_KNOWN_PROGRAMS, DEC_0037)."""
    if shell:
        return "runs strace through a shell", None, None
    if r.config.get(MODULE_KEY) != STRACE_MODULE:
        return "runs strace, which only test_record_trace's own process may start", None, None
    if len(argv) < 9 or tuple(argv[1:7]) != STRACE_FORM or argv[8].startswith("-"):
        return "runs strace with arguments other than -f -y -s 4096 -qq -o LOG", None, None
    if preexec_fn is not None or not close_fds or pass_fds:
        return "runs strace with code before it starts or descriptors it inherits", None, None
    if PARENT_ENV in final:
        return f"runs strace with {PARENT_ENV} already set", None, None
    found = _found_program(r, program, final, cwd)
    if found is None:
        return "runs strace, which is not found", None, None
    resolved = _realpath(found)
    if _program_key(r, resolved) is None or _under(_norm(resolved), r.nroot):
        return "runs a strace under the repository or one the run made", None, None
    if _head(resolved, 4) != b"\x7fELF":
        return "runs a strace that is not an ELF program", None, None
    log = os.path.normpath(os.path.join(cwd, argv[7]))
    made = lambda p: any(_under(_norm(p), c) for c in r.created)
    try:
        parent = _realpath(os.path.dirname(log))
    except (OSError, ValueError):
        parent = None
    if not made(log) or parent is None or not made(parent) or r.in_top(log) \
            or r.lands(log, r.prefixes):
        return "runs strace with its log outside a directory the run made", None, None
    if kind(log) != "absent":
        return "runs strace with a log that is already there", None, None
    _note_program(r, resolved, cwd)
    _whole_environment(r, env, final)
    return None, _Trace(log, cwd), resolved


#: The calls a traced command makes that name no path, or name one only through a
#: descriptor whose open the log holds: memory, time, signals, descriptors, waits.
TRACE_HARMLESS = frozenset({
    "read", "write", "pread64", "pwrite64", "readv", "writev", "preadv", "pwritev",
    "preadv2", "pwritev2", "close", "close_range", "fstat", "fstat64", "fstatfs",
    "fstatfs64", "lseek", "_llseek", "mmap", "mmap2", "mprotect", "munmap", "mremap",
    "madvise", "mlock", "munlock", "msync", "mincore", "brk", "rt_sigaction",
    "rt_sigprocmask", "rt_sigreturn", "rt_sigsuspend", "rt_sigtimedwait",
    "sigaltstack", "ioctl", "fcntl", "fcntl64", "dup", "dup2", "dup3", "pipe", "pipe2",
    "poll", "ppoll", "select", "pselect6", "epoll_create", "epoll_create1", "epoll_ctl",
    "epoll_wait", "epoll_pwait", "epoll_pwait2", "eventfd", "eventfd2", "futex",
    "futex_waitv", "set_robust_list", "get_robust_list", "set_tid_address", "rseq",
    "arch_prctl", "prlimit64", "getrlimit", "setrlimit", "getpid", "gettid", "getppid",
    "getuid", "geteuid", "getgid", "getegid", "getgroups", "getresuid", "getresgid",
    "getpgrp", "getpgid", "setpgid", "getsid", "setsid", "clock_gettime", "clock_getres",
    "clock_nanosleep", "nanosleep", "gettimeofday", "time", "times", "getrusage",
    "getrandom", "getcwd", "umask", "sched_getaffinity", "sched_setaffinity",
    "sched_yield", "sched_getparam", "sched_getscheduler", "sched_get_priority_max",
    "sched_get_priority_min", "getpriority", "setpriority", "wait4", "waitid", "kill",
    "tkill", "tgkill", "exit", "exit_group", "restart_syscall", "prctl", "capget",
    "membarrier", "memfd_create", "timerfd_create", "timerfd_settime", "timerfd_gettime",
    "timer_create", "timer_settime", "timer_delete", "setitimer", "getitimer", "alarm",
    "pause", "signalfd", "signalfd4", "flock", "fsync", "fdatasync", "fadvise64",
    "readahead", "sendfile", "sendfile64", "copy_file_range", "splice", "tee",
    "recvfrom", "recvmsg", "recvmmsg", "shutdown", "getsockname", "getpeername",
    "getsockopt", "setsockopt", "listen", "accept", "accept4", "get_mempolicy",
    "set_mempolicy", "mbind", "personality", "sysinfo", "getcpu",
    "pidfd_open", "pidfd_send_signal", "ioprio_get", "ioprio_set", "kcmp",
    # The host name the kernel gives native code is DES_0008's native-code risk, as
    # COMP_HOST_NAME states for uuid.getnode; the other fields are the run's uname section.
    "uname",
})
#: Calls that open a path: (directory descriptor, path, flags), by argument index.
_TRACE_OPENS = {"open": (None, 0, 1), "openat": (0, 1, 2), "creat": (None, 0, None),
                "openat2": (0, 1, 2)}
#: Calls that report a path's status: (directory descriptor, path, flags).
_TRACE_STATS = {"stat": (None, 0, None), "stat64": (None, 0, None),
                "lstat": (None, 0, None), "lstat64": (None, 0, None),
                "newfstatat": (0, 1, 3), "fstatat64": (0, 1, 3), "statx": (0, 1, 2)}
_TRACE_ACCESS = {"access": (None, 0, None), "faccessat": (0, 1, None),
                 "faccessat2": (0, 1, 3)}
_TRACE_READLINK = {"readlink": (None, 0), "readlinkat": (0, 1)}
#: Other calls that learn of a path: (directory descriptor, path).
_TRACE_LEARN = {"getxattr": (None, 0), "lgetxattr": (None, 0), "listxattr": (None, 0),
                "llistxattr": (None, 0), "statfs": (None, 0), "statfs64": (None, 0),
                "inotify_add_watch": (None, 1)}
#: Calls that change a path: (directory descriptor, path) pairs, by argument index.
_TRACE_WRITES = {
    "mkdir": [(None, 0)], "mkdirat": [(0, 1)], "rmdir": [(None, 0)],
    "unlink": [(None, 0)], "unlinkat": [(0, 1)], "rename": [(None, 0), (None, 1)],
    "renameat": [(0, 1), (2, 3)], "renameat2": [(0, 1), (2, 3)],
    "link": [(None, 1)], "linkat": [(2, 3)], "symlink": [(None, 1)],
    "symlinkat": [(1, 2)], "chmod": [(None, 0)], "fchmodat": [(0, 1)],
    "fchmodat2": [(0, 1)], "chown": [(None, 0)], "lchown": [(None, 0)],
    "fchownat": [(0, 1)], "truncate": [(None, 0)], "truncate64": [(None, 0)],
    "utime": [(None, 0)], "utimes": [(None, 0)], "futimesat": [(0, 1)],
    "utimensat": [(0, 1)], "setxattr": [(None, 0)], "lsetxattr": [(None, 0)],
    "removexattr": [(None, 0)], "lremovexattr": [(None, 0)],
}
#: The source a hard link is made from, which the run reads: (directory descriptor, path).
_TRACE_LINK_FROM = {"link": (None, 0), "linkat": (0, 1)}
#: Calls that change what a descriptor names.
_TRACE_FD_WRITES = {"fchmod", "fchown", "ftruncate", "ftruncate64", "fsetxattr",
                    "fremovexattr", "fallocate"}
#: Calls that reach what no trace follows, or the network.
_TRACE_REFUSED = {
    "io_uring_setup": "works through io_uring, which no trace follows",
    "io_uring_enter": "works through io_uring, which no trace follows",
    "io_uring_register": "works through io_uring, which no trace follows",
    "open_by_handle_at": "opens a file by its handle",
    "name_to_handle_at": "opens a file by its handle",
    "mknod": "makes a special file", "mknodat": "makes a special file",
    "chroot": "changes its root", "pivot_root": "changes its root",
    "mount": "mounts a file system", "umount2": "mounts a file system",
    "unshare": "changes its namespaces", "setns": "changes its namespaces",
    "ptrace": "traces a process", "process_vm_readv": "reads another process",
    "process_vm_writev": "writes another process",
    "fanotify_init": "watches the file system", "fanotify_mark": "watches the file system",
    "uselib": "loads a library by an old call", "sethostname": "sets the host name",
}
_CLONES = ("clone", "clone3", "fork", "vfork")
#: A line of strace's log, ``PID text``; a call; a call resumed.
_TRACE_LINE = re.compile(r"(\d+) +(.*)")
_TRACE_CALL = re.compile(r"([a-z_0-9]+)\(")
_TRACE_RESUMED = re.compile(r"<\.\.\. ([a-z_0-9]+) resumed>")
_UNFINISHED = " <unfinished ...>"
_ESCAPES = {"n": b"\n", "t": b"\t", "r": b"\r", "v": b"\v", "f": b"\f", "a": b"\a",
            "b": b"\b", "\\": b"\\", '"': b'"', "'": b"'"}


#: The calls on a socket the reader judges, before the harmless and the refused.
_SOCKET_REACHING = {"listen": "listens", "accept": "accepts", "accept4": "accepts",
                    "sendto": "sends", "sendmsg": "sends", "sendmmsg": "sends"}
_SOCKET_CALLS = frozenset({"socket", "socketpair", "connect", "bind", *_SOCKET_REACHING})


def _loopback(address: str) -> bool:
    """Whether a socket address strace printed is a loopback one, as ``127.0.0.1`` or
    ``::1``, or IPv4's loopback mapped into IPv6."""
    import ipaddress
    m = re.search(r'(?:inet_addr|inet_pton)\((?:AF_INET6?, )?"([^"]+)"', address)
    if m is None:
        return False
    try:
        ip = ipaddress.ip_address(m.group(1))
    except ValueError:
        return False
    mapped = getattr(ip, "ipv4_mapped", None)
    return ip.is_loopback or mapped is not None and mapped.is_loopback


class _Unreadable(Exception):
    """A line of strace's log the recorder cannot read."""


def _unescape(text: str) -> str:
    """A string strace printed, its C escapes decoded, as the system's file name."""
    out, i = bytearray(), 0
    while i < len(text):
        c = text[i]
        if c != "\\":
            out += c.encode("utf-8", "surrogateescape")
            i += 1
            continue
        e = text[i + 1:i + 2]
        if e in _ESCAPES:
            out += _ESCAPES[e]
            i += 2
        elif e == "x" and re.match(r"[0-9a-fA-F]{2}", text[i + 2:i + 4]):
            out.append(int(text[i + 2:i + 4], 16))
            i += 4
        elif e and e in "01234567":
            digits = re.match(r"[0-7]{1,3}", text[i + 1:]).group(0)
            out.append(int(digits, 8) & 0xFF)
            i += 1 + len(digits)
        else:
            raise _Unreadable("an escape strace does not write")
    return os.fsdecode(bytes(out))


def _arguments(text: str) -> tuple[list[str], str]:
    """A call's arguments, split where no string, structure, comment or descriptor's path
    holds the comma, and what follows the closing parenthesis."""
    args, depth, start, i = [], 0, 0, 0
    while i < len(text):
        c = text[i]
        if c == '"':
            i += 1
            while i < len(text) and text[i] != '"':
                i += 2 if text[i] == "\\" else 1
            if i >= len(text):
                raise _Unreadable("a string with no end")
        elif c == "<" and i > 0 and (text[i - 1].isdigit() or text[i - 1] == "D"):
            # A descriptor's path, which -y prints with its own < and > escaped.
            end = text.find(">", i)
            if end < 0:
                raise _Unreadable("a descriptor's path with no end")
            i = end
        elif text.startswith("/*", i):
            end = text.find("*/", i)
            if end < 0:
                raise _Unreadable("a comment with no end")
            i = end + 1
        elif c in "([{":
            depth += 1
        elif c in "}]":
            depth -= 1
        elif c == ")":
            if depth == 0:
                if text[start:i].strip():
                    args.append(text[start:i].strip())
                return args, text[i + 1:]
            depth -= 1
        elif c == "," and depth == 0:
            args.append(text[start:i].strip())
            start = i + 1
        i += 1
    raise _Unreadable("a call with no end")


def _string_arg(token: str) -> str | None:
    """The path a quoted argument holds, or None when it is no string, as NULL is not; a
    string strace cut short cannot be read."""
    if not token.startswith('"'):
        return None
    end = 1
    while end < len(token) and token[end] != '"':
        end += 2 if token[end] == "\\" else 1
    if end >= len(token) or token[end + 1:].strip():
        raise _Unreadable("a path strace cut short")
    return _unescape(token[1:end])


def _fd_path(token: str) -> tuple[str, str | None]:
    """A descriptor argument, ``N``, ``AT_FDCWD`` or either with ``<path>``: the descriptor
    and its path, if strace gave one."""
    m = re.fullmatch(r"(-?\d+|AT_FDCWD)(?:<(.*)>)?", token.strip())
    if not m:
        return token.strip(), None
    path = m.group(2)
    return m.group(1), None if path is None else _unescape(path)


class _TraceReader:
    """Strace's log, followed call by call into the recorder (COMP_KNOWN_PROGRAMS): every
    path read, probed or listed outside the run's own directories, as the recorder records
    the run's own, each failed one as what is there, which for a path not found is absence;
    each program started with its interpreters; and every path written, which must be the
    run's own. A read under /proc or /dev outside the allowed list, a connection, a socket
    of a network family and a call the recorder does not list refuse the run."""

    def __init__(self, r: Recorder, trace: _Trace):
        self.r, self.trace = r, trace
        #: Each traced process's working directory, one list shared between processes
        #: that share it, as threads do.
        self.cwd: dict[int, list[str]] = {}
        #: Each process with a clone, fork or vfork not yet returned, with its arguments.
        self.cloning: dict[int, str] = {}
        self.pending: dict[int, str] = {}
        self.seen: set = set()
        #: Each socket of a network family opened, by the path -y gives it, and whether it
        #: was bound to a loopback address.
        self.inet: dict[str, bool] = {}

    def take(self, path: str) -> None:
        with _open(path, "rb") as f:
            for raw in f:
                self.line(raw.decode("utf-8", "surrogateescape").rstrip("\n"))
        if self.pending:
            raise _Unreadable("a call that never ended")
        if not all(self.inet.values()):
            self.r.refuse("opens a socket of a network family it binds to no loopback address")

    # -- lines --

    def line(self, text: str) -> None:
        m = _TRACE_LINE.fullmatch(text)
        if not m:
            raise _Unreadable("a line with no process")
        pid, body = int(m.group(1)), m.group(2)
        if body.startswith(("---", "+++")):
            return  # a signal, or a process's end
        if body.endswith(_UNFINISHED):
            body = body[:-len(_UNFINISHED)]
            call = _TRACE_CALL.match(body)
            if call is None or pid in self.pending:
                raise _Unreadable("an unfinished call the recorder cannot read")
            self.known(pid)
            self.pending[pid] = body
            if call.group(1) in _CLONES:
                self.cloning[pid] = body
            return
        resumed = _TRACE_RESUMED.match(body)
        if resumed:
            begun = self.pending.pop(pid, None)
            if begun is None or not begun.startswith(resumed.group(1) + "("):
                raise _Unreadable("a resumed call that never began")
            body = begun + body[resumed.end():]
        call = _TRACE_CALL.match(body)
        if call is None:
            raise _Unreadable("a line that is no call")
        args, rest = _arguments(body[call.end():])
        result = re.match(r"\s*=\s*(.*)", rest)
        self.call(pid, call.group(1), args, result.group(1) if result else "?")

    def known(self, pid: int) -> None:
        """Give a process seen for the first time the working directory it inherited: the
        command's own for the first, else that of the process cloning it."""
        if pid in self.cwd:
            return
        if not self.cwd:
            self.cwd[pid] = [self.trace.cwd]
            return
        parents = [p for p in self.cloning if p != pid]
        if len(parents) == 1:
            self.inherit(pid, parents[0], self.cloning[parents[0]])
            return
        # Several clone at once: only a directory they all hold, shared by none, is told.
        values = {self.cwd[p][0] for p in parents if p in self.cwd}
        if len(values) != 1 or any("CLONE_FS" in self.cloning[p] for p in parents):
            raise _Unreadable("a process whose working directory cannot be told")
        self.cwd[pid] = [values.pop()]

    def inherit(self, child: int, parent: int, flags: str) -> None:
        if parent not in self.cwd:
            raise _Unreadable("a process whose working directory cannot be told")
        self.cwd[child] = self.cwd[parent] if "CLONE_FS" in flags else [self.cwd[parent][0]]

    # -- paths --

    def path(self, pid: int, args: list[str], dirfd: int | None, at: int) -> str | None:
        """The absolute path a call names, from its descriptor's path or the process's
        working directory; None for no path, as NULL or an empty path with a descriptor,
        or for one refused."""
        if at >= len(args) or dirfd is not None and dirfd >= len(args):
            raise _Unreadable("a call with fewer arguments than it takes")
        raw = _string_arg(args[at])
        if raw is None or raw == "":
            return None
        if os.path.isabs(raw):
            base = "/"
        elif dirfd is None:
            base = self.cwd[pid][0]
        else:
            fd, base = _fd_path(args[dirfd])
            if base is None:
                if fd != "AT_FDCWD":
                    raise _Unreadable("a path relative to a descriptor strace did not name")
                base = self.cwd[pid][0]
        joined = os.path.join(base, raw)
        normal = os.path.normpath(joined)
        if ".." in raw.split("/") and _realpath(joined) != _realpath(normal):
            self.r.refuse("names a path whose .. passes through a link")
            return None
        return normal

    def special(self, path: str, op: str) -> bool:
        """Judge a path under /proc or /dev, or strace's own log: True when it is one,
        allowed or refused. ``op`` is ``read``, ``write``, ``probe``, ``list``,
        ``directory`` or ``readlink``."""
        r = self.r
        if _norm(path) == _norm(self.trace.log):
            r.refuse("opens the log strace writes")
            return True
        if path in TRACE_DEVICES and op in ("read", "write", "probe"):
            return True
        parts = path.split("/")
        if parts[1:2] == ["dev"]:
            # Named with no leading slash, which a reason's cleaning would cut away.
            r.refuse(f"reaches the device {'/'.join(parts[2:]) or 'directory'}")
            return True
        if parts[1:2] != ["proc"]:
            return False
        who = parts[2] if len(parts) > 2 else ""
        rest = parts[3:]
        if who.isdigit() and rest[:1] == ["task"]:
            rest = rest[2:]
        own = who in ("self", "thread-self") or who.isdigit() and int(who) in self.cwd
        # The fd directory opened for reading, as subprocess opens it with no O_DIRECTORY,
        # gives nothing but its listing.
        allowed = (rest == ["fd"] and op in ("list", "directory", "read")
                   or rest == ["exe"] and op == "readlink"
                   or len(rest) == 1 and rest[0] in TRACE_OWN_PROC and op == "read")
        if not (own and allowed):
            # A process's own entries by "self", another's never by its number, which
            # differs in every run.
            head = "self" if own else "another process" if who.isdigit() else who
            shown = "/".join([head, *rest]) if who else "its directory"
            r.refuse(f"reaches the proc entry {shown}")
        return True

    # -- calls --

    def call(self, pid: int, name: str, args: list[str], result: str) -> None:
        self.known(pid)
        r = self.r
        ok = not result.startswith(("-1", "?"))
        if name in _SOCKET_CALLS:
            self.socket(name, args, result, ok)
            return
        if name in TRACE_HARMLESS:
            return
        if name in _CLONES:
            flags = self.cloning.pop(pid, None) or ",".join(args)
            child = re.match(r"(\d+)", result)
            if ok and child and int(child.group(1)) not in self.cwd:
                self.inherit(int(child.group(1)), pid, flags)
            return
        if name in _TRACE_REFUSED:
            r.refuse(_TRACE_REFUSED[name])
        elif name in _TRACE_OPENS:
            self.open(pid, name, args, result, ok)
        elif name in _TRACE_STATS:
            dirfd, at, flags = _TRACE_STATS[name]
            path = self.path(pid, args, dirfd, at)
            if path is not None:
                follows = not name.startswith("lstat") and (
                    flags is None or flags >= len(args)
                    or "AT_SYMLINK_NOFOLLOW" not in args[flags])
                self.probe(path, follows, hashes=ok)
        elif name in _TRACE_ACCESS:
            dirfd, at, flags = _TRACE_ACCESS[name]
            path = self.path(pid, args, dirfd, at)
            if path is not None:
                self.probe(path, flags is None or flags >= len(args)
                           or "AT_SYMLINK_NOFOLLOW" not in args[flags])
        elif name in _TRACE_READLINK:
            path = self.path(pid, args, *_TRACE_READLINK[name])
            if path is not None and not self.special(path, "readlink"):
                self.probe(path, True)  # a link's target is learned, as by following it
        elif name in _TRACE_LEARN:
            path = self.path(pid, args, *_TRACE_LEARN[name])
            if path is not None:
                self.probe(path, name not in ("lgetxattr", "llistxattr"))
        elif name in ("getdents", "getdents64"):
            self.listing(args)
        elif name in ("execve", "execveat"):
            self.execute(pid, name, args, ok)
        elif name == "chdir":
            path = self.path(pid, args, None, 0)
            if path is not None:
                self.probe(path, True)
                if ok:
                    self.cwd[pid][0] = _realpath(path)
        elif name == "fchdir":
            path = _fd_path(args[0])[1] if args else None
            if path is None:
                raise _Unreadable("a change of directory strace did not name")
            if ok:
                self.cwd[pid][0] = path
        elif name in _TRACE_WRITES:
            self.change(pid, name, args, ok)
        elif name in _TRACE_FD_WRITES:
            path = _fd_path(args[0])[1] if args else None
            if path is None:
                raise _Unreadable("a change through a descriptor strace did not name")
            if ok:
                self.write(path)
        else:
            r.refuse(f"makes a call the recorder does not list: {name}")

    def socket(self, name: str, args: list[str], result: str, ok: bool) -> None:
        """A socket's calls: a local one is the command's own; one of a network family is
        let through only bound to a loopback address, and never connecting, sending to an
        address, listening or accepting (DEC_0043)."""
        r = self.r
        key = _fd_path(args[0])[1] if args else None
        if name in ("socket", "socketpair"):
            family = args[0] if args else ""
            if family in ("AF_UNIX", "AF_LOCAL"):
                return
            if name == "socket" and family in TRACE_INET:
                opened = _fd_path(result)[1] if ok else None
                if ok and opened is None:
                    raise _Unreadable("a socket strace did not name")
                if opened is not None:
                    self.inet[opened] = False
                return
            r.refuse("opens a socket of a network family")
        elif name == "connect":
            r.refuse("makes a connection")
        elif name == "bind":
            if key not in self.inet:
                r.refuse("binds a socket")
            elif not _loopback(args[1] if len(args) > 1 else ""):
                r.refuse("binds a socket to an address that is not loopback")
            else:
                self.inet[key] = self.inet[key] or ok
        elif name in ("sendto", "sendmsg", "sendmmsg") and "sa_family=" in ",".join(args):
            r.refuse("sends to an address")
        elif key in self.inet and name in _SOCKET_REACHING:
            r.refuse(f"{_SOCKET_REACHING[name]} on a socket of a network family")

    def open(self, pid: int, name: str, args: list[str], result: str, ok: bool) -> None:
        dirfd, at, flags_at = _TRACE_OPENS[name]
        path = self.path(pid, args, dirfd, at)
        if path is None:
            return
        flags = "O_WRONLY|O_CREAT|O_TRUNC" if name == "creat" else (
            args[flags_at] if flags_at < len(args) else "")
        writes = any(f in flags for f in ("O_WRONLY", "O_RDWR", "O_CREAT", "O_TRUNC",
                                           "O_APPEND", "O_TMPFILE"))
        follows = "O_NOFOLLOW" not in flags
        # What was opened is the path -y gives, the kernel's, its links resolved.
        opened = _fd_path(result)[1] if ok else None
        if ok and opened is None:
            raise _Unreadable("an open strace did not name")
        # Judged before anything examines it: a status of a device, as /dev/urandom, would
        # read it as a file.
        op = "write" if writes else "directory" if "O_DIRECTORY" in flags else "read"
        for place in dict.fromkeys(p for p in (path, opened) if p is not None):
            if self.special(place, op):
                return
        if writes:
            if ok:
                # Where it landed too, as through a link the run made.
                for place in dict.fromkeys((path, opened)):
                    self.write(place)
            else:
                self.probe(path, follows)
        elif ok and "O_PATH" not in flags and kind(opened) == "file":
            if path in FOLLOWED_LINKS and kind(path) == "link":
                self.once(("followed", path), lambda: self.followed(path))
            else:
                self.once(("read", path), lambda: self.r.read(path))
        else:
            self.probe(path, follows)

    def followed(self, path: str) -> None:
        """A read of one of FOLLOWED_LINKS through its link: the link is held as one, its
        target by its content, and the path by what the link reaches, which a lookup takes
        again following it (DEC_0043)."""
        r = self.r
        if r.refused() or r.where(path) is None:
            return
        digest = _program_hash(path)
        if digest is None:
            r.refuse(f"reads {r.shown(path)} through a link to what is no file")
            return
        r.note("probes", path, "link")
        r.note("outside", path, digest)
        r.read(_realpath(path))

    def listing(self, args: list[str]) -> None:
        path = _fd_path(args[0])[1] if args else None
        if path is None:
            raise _Unreadable("a listing of a descriptor strace did not name")
        if not self.special(path, "list"):
            self.once(("list", path), lambda: self.r.list(path))

    def execute(self, pid: int, name: str, args: list[str], ok: bool) -> None:
        path = self.path(pid, args, 0 if name == "execveat" else None,
                         1 if name == "execveat" else 0)
        if path is None:
            raise _Unreadable("a program started by a descriptor")
        if self.special(path, "probe"):
            return
        r = self.r
        if ok:
            cwd = self.cwd[pid][0]
            self.once(("program", path), lambda: _note_program(r, path, cwd))
            return
        key = _program_key(r, path)  # a search along PATH, wherever it looked
        if key is not None:
            r.note("probes", key, kind(path))

    def change(self, pid: int, name: str, args: list[str], ok: bool) -> None:
        for dirfd, at in _TRACE_WRITES[name]:
            path = self.path(pid, args, dirfd, at)
            if path is None:
                continue
            if ok:
                self.write(path)
            else:
                self.probe(path, False)
        if name in _TRACE_LINK_FROM and ok:
            path = self.path(pid, args, *_TRACE_LINK_FROM[name])
            if path is not None and not self.special(path, "read"):
                self.once(("read", path), lambda: self.r.read(path))

    def once(self, key, action) -> None:
        if key not in self.seen:
            self.seen.add(key)
            action()

    def probe(self, path: str, follows: bool, hashes: bool = False) -> None:
        """A path probed, as the recorder's wrapped probes record it: a status call that
        succeeds on a file reads it, since it reports its size."""
        if self.special(path, "probe"):
            return
        r = self.r

        def note():
            r.probe(path, follows=follows)
            k = kind(path)
            if hashes and (k == "file" or k == "link" and follows):
                r.read(path)
        self.once(("probe", path, follows, hashes), note)

    def write(self, path: str) -> None:
        """A path the traced command changed: it must be the run's own, under a directory
        the run made or a file it wrote, and in no directory a recorder prepared and not
        under the interpreter's prefixes."""
        if self.special(path, "write"):
            return
        r, n = self.r, _norm(path)
        own = n in r.written or any(_under(n, c) for c in r.created)
        if not own or r.in_top(path) or r.lands(path, r.prefixes):
            r.refuse(f"writes {r.shown(path)}, outside the run's own directories")


def _take_trace(r: Recorder, trace: _Trace, returncode) -> None:
    """Take a strace's log into the run's inputs once strace has ended, each reason it
    gives named for strace."""
    r.local.process = STRACE
    try:
        if not isinstance(returncode, int) or returncode < 0:
            r.refuse("strace did not finish")
            return
        try:
            _TraceReader(r, trace).take(trace.log)
        except _Unreadable as exc:
            r.refuse(f"its log holds {exc}")
        except OSError as exc:
            r.refuse(f"its log cannot be read: {type(exc).__name__}")
    finally:
        r.local.process = None


def _watch_children(r: Recorder) -> None:
    """Give each Python child a fresh directory to record into; let a known program through
    on its terms, taking strace's log once it has ended; any other program, or a Python
    child that cannot record itself, makes the run unstorable."""
    import secrets
    import subprocess

    original = subprocess.Popen._execute_child
    names = list(inspect.signature(original).parameters)
    env_at, shell_at = names.index("env") - 1, names.index("shell") - 1  # less self
    cwd_at = names.index("cwd") - 1
    executable_at, preexec_at = names.index("executable") - 1, names.index("preexec_fn") - 1
    close_at, pass_at = names.index("close_fds") - 1, names.index("pass_fds") - 1
    executable = _norm(os.path.abspath(sys.executable))

    def execute_child(self, *args):
        args = list(args)
        argv, program_arg = args[0], args[1]
        python = False
        if not isinstance(argv, (str, bytes)) and not args[shell_at] and argv:
            program = program_arg if program_arg is not None else argv[0]
            python = _norm(os.path.abspath(os.fsdecode(program))) == executable
        if python and not r.quiet():
            # A child of a run already refused records too: its reasons are named. This
            # wrapper is the innermost when another recorder started after this one, so
            # what it reads here are the final arguments and environment.
            env = args[env_at]
            decoded = [os.fsdecode(a) for a in argv]
            # The environment read past the recording mappings, so nothing is noted.
            final = {_name(k): v for k, v in (_environment() if env is None
                                              else env.items())}
            cwd = _text(args[cwd_at])
            cwd = None if cwd is None else os.path.join(_getcwd(), cwd)
            flags = _interpreter_options(decoded)[0]
            r.local.busy = True  # resolving the search path is the recorder's own work
            try:
                why = _python_child(decoded, final, r.inside, cwd, r.prefixes)
                # The entries as judged, carried to the child in place of the variable.
                entries = None if "E" in flags or "I" in flags else _search_path(
                    final.get(PATH_ENV), cwd)
            finally:
                r.local.busy = False
            if why is None and PARENT_ENV in final:
                # Only a recorder sets it, and only here, as the child starts.
                why = f"starts a Python child whose environment already holds {PARENT_ENV}"
            r.guarded(r.check_intact)
            if why:
                r.refuse(why)
            else:
                args[env_at] = _prepare_child(r, env, final, _child_name(
                    decoded, os.fsdecode(program)), secrets.token_hex(8), entries or None)
        trace = None
        if not python and not r.quiet() and os.name == "posix" and argv and not isinstance(
                argv, (str, bytes)):
            named = os.fsdecode(program_arg if program_arg is not None else argv[0])
            if os.path.basename(named) == STRACE:
                trace = _known(self, args, named)
        r.local.child, r.local.popen = python, True
        r.local.known = trace is not None
        try:
            result = original(self, *args)
        finally:
            r.local.child, r.local.popen, r.local.known = False, False, False
        if isinstance(trace, _Trace):
            with r.lock:
                r.traces[id(self)] = (self, trace)
        return result

    def _known(popen, args: list, named: str):
        """Judge a start of a known program: its _Trace, with the executable pinned in
        ``args`` to the path it was found at, when let through; False when refused, its
        reason given."""
        r.local.busy = True  # judging the start is the recorder's own work
        try:
            env = args[env_at]
            final = {_name(k): v for k, v in (_environment() if env is None
                                              else env.items())}
            cwd = _text(args[cwd_at])
            cwd = _getcwd() if cwd is None else os.path.join(_getcwd(), cwd)
            argv = [os.fsdecode(a) for a in args[0]]
            with r.lock:
                why, trace, resolved = _strace_start(
                    r, argv, named, env, final, cwd, args[shell_at], args[preexec_at],
                    args[close_at], args[pass_at])
        except Exception as exc:
            why = f"the recorder failed on a start of strace: {type(exc).__name__}"
        finally:
            r.local.busy = False
        r.guarded(r.check_intact)
        if why is not None:
            r.refuse(why)
            return False
        args[executable_at] = resolved
        return trace

    # The original's signature, which a recorder started after this one reads.
    execute_child.__wrapped__ = original
    r.install(subprocess.Popen, "_execute_child", execute_child, "Popen._execute_child")
    _watch_exits(r, subprocess)
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

    guarded_fork_exec.__wrapped__ = fork_exec
    r.install(_posixsubprocess, "fork_exec", guarded_fork_exec, "fork_exec")


def _watch_exits(r: Recorder, subprocess) -> None:
    """Take a strace's log as soon as the run reaps it, before the run can learn it ended:
    the log is the key of what it traced, and the run may remove it."""
    original = getattr(subprocess.Popen, "_handle_exitstatus", None)
    if original is None:
        return  # Windows, where no strace starts

    def handle_exitstatus(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        with r.lock:
            entry = r.traces.pop(id(self), None)
        if entry is not None and entry[0] is self:
            r.guarded(lambda: _take_trace(r, entry[1], self.returncode))
        return result

    handle_exitstatus.__wrapped__ = original
    r.install(subprocess.Popen, "_handle_exitstatus", handle_exitstatus,
              "Popen._handle_exitstatus")


def _watch_rmtree(r: Recorder) -> None:
    """shutil.rmtree works through descriptors on some systems: the tree it removes is
    recorded as written, and its own listings are not inputs."""
    import shutil

    original = shutil.rmtree

    def recorded(callback):
        """``callback`` run with the recorder listening again: it is the run's code."""
        if not callable(callback):
            return callback

        def call(*a, **k):
            depth, r.local.rmtree = r.local.rmtree, 0
            try:
                return callback(*a, **k)
            finally:
                r.local.rmtree = depth
        return call

    def rmtree(path, *args, **kwargs):
        def note():
            r.probe(path)
            r.wrote(path, directory=True)
        r.guarded(note)
        if len(args) > 1:  # rmtree(path, ignore_errors, onerror)
            args = (args[0], recorded(args[1]), *args[2:])
        for name in ("onerror", "onexc"):
            if name in kwargs:
                kwargs[name] = recorded(kwargs[name])
        r.local.rmtree = getattr(r.local, "rmtree", 0) + 1  # this thread's calls only
        try:
            return original(path, *args, **kwargs)
        finally:
            r.local.rmtree -= 1

    rmtree.avoids_symlink_attacks = getattr(original, "avoids_symlink_attacks", False)
    rmtree.__wrapped__ = original
    r.install(shutil, "rmtree", rmtree, "shutil.rmtree")


def _watch_open(r: Recorder) -> None:
    """os.open's audit event leaves out ``dir_fd``: a path relative to a descriptor is
    refused here, where the argument is seen."""
    original = os.open

    def open_(path, flags, mode=0o777, *, dir_fd=None):
        if dir_fd is not None and not r.in_rmtree():
            r.guarded(lambda: r.refuse("names a path relative to a directory descriptor"))
        return original(path, flags, mode, dir_fd=dir_fd)

    r.install(os, "open", _wrapping(open_, original), "os.open")


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

    r.install(os, "scandir", _wrapping(scandir, original), "os.scandir")


def _name(key) -> str:
    name = os.fsdecode(key) if isinstance(key, bytes) else str(key)
    return name.upper() if os.name == "nt" else name


def _recording_environ(r: Recorder, base: type) -> type:
    """A subclass of ``os._Environ`` that records each variable read, every variable when
    the mapping is iterated, sized, copied or shown, and the variables the run sets, whose
    later reads are the run's own; it sets the process environment as before."""

    def note(self, key) -> None:
        name = _name(key)
        if r.refused() or name in OWN or name in r.env_set or name in r.environment:
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
        def every():
            for k in list(base.__iter__(self)):
                note(self, k)
            r.note_names()  # a variable added later changes what the run saw
        r.guarded(every)

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


def names_digest(names) -> str:
    """The SHA-256 of a set of variables' names, sorted, the recorder's own left out."""
    return hashlib.sha256("\0".join(sorted(set(names) - OWN)).encode(
        "utf-8", "surrogateescape")).hexdigest()


def uname_digests(result) -> dict[str, str]:
    """The SHA-256 of each field of an ``os.uname`` result but the host name."""
    return {field: hashlib.sha256(getattr(result, field).encode(
        "utf-8", "surrogateescape")).hexdigest() for field in UNAME_FIELDS}


def _fix_host_name(r: Recorder) -> None:
    """``os.uname`` and ``posix.uname``, one function under two names, give the fixed host
    name, and ``platform``'s cache is filled through them, so ``platform.node()`` gives it
    whether or not ``platform.system()`` came first. The other fields are recorded here,
    since what the cache holds is read with no call. On Windows there is no ``os.uname``,
    and ``platform`` reads the host name through ``socket.gethostname``, which is refused."""
    if not hasattr(os, "uname"):
        return
    import _imp
    import posix
    real = posix.uname()
    fixed = type(real)((real.sysname, HOST_NAME, real.release, real.version, real.machine))

    def uname():
        return fixed

    # The function returns the fixed result taken once here; it holds no reference to the
    # original, which a ``__wrapped__`` or its closure would otherwise hand out.
    uname.__name__, uname.__doc__ = posix.uname.__name__, posix.uname.__doc__
    os.uname = posix.uname = uname
    r.fixed_uname = fixed
    r.guarded(lambda: [r.note("uname", field, digest)
                       for field, digest in uname_digests(fixed).items()])
    # A new posix module holds the original. The import system makes every builtin module
    # through _imp.create_builtin, which it looks up at call time, by whatever route; the
    # import event, which only a module not yet loaded raises, is checked too.
    create = _imp.create_builtin

    def create_builtin(spec):
        # The name is read once and handed on as read: a spec whose name changes between
        # two reads, or a str subclass that compares as another name, gets no new posix.
        name = getattr(spec, "name", None)
        if type(name) is not str:
            r.guarded(lambda: r.refuse("imports a builtin by a name that is not a str"))
        elif name in UNAME_MODULES:
            r.guarded(lambda: r.refuse(f"imports {name} again"))
        return create(_Named(name, spec))

    create_builtin.__name__ = create.__name__
    # Not ``__wrapped__``, which ``inspect.unwrap`` follows to an original that makes a
    # fresh posix: the check that it stays in place follows this name too.
    setattr(create_builtin, WRAPPED, create)
    r.install(_imp, "create_builtin", create_builtin, "_imp.create_builtin")
    import platform
    platform._uname_cache = None
    platform.uname()


_recorder: Recorder | None = None


def _started_clean(r: Recorder, config: dict) -> None:
    """Refuse a run whose interpreter is not its parent's, or that could have run code of
    its own before the recorder started (DEC_0042)."""
    _same_prefixes(r, config)
    _modules_before_start(r)
    _search_path_inputs(r)


def _same_prefixes(r: Recorder, config: dict) -> None:
    """Refuse prefixes other than those the parent wrote into the configuration."""
    given = config.get("prefixes")
    if given is not None and sorted(_norm(str(p)) for p in given) != sorted(
            _norm(p) for p in _prefixes()):
        r.refuse("runs under prefixes other than its parent's")


def _modules_before_start(r: Recorder) -> None:
    """Refuse a module loaded before the recorder started that is not of the standard
    library, or one of its name loaded from outside the prefixes, as one on PYTHONPATH
    named ``encodings`` would be: a module that ran and then left ``sys.modules`` is not
    seen here, and the search path's own checks are for it."""
    standard = _standard_names() | BEFORE_START
    loaded = {name: None for name in sys.modules if name not in MODULES}
    loaded.update(_module_origins())
    for name, origin in loaded.items():
        if name.partition(".")[0] not in standard:
            r.refuse(f"ran {name}, which is not of the standard library, before the "
                     f"recorder started")
            continue
        if origin is None:
            continue
        try:
            resolved = _norm(_realpath(origin))
        except (OSError, ValueError):
            r.refuse(f"could not tell where {name} was loaded from before the recorder "
                     f"started")
            continue
        if not any(_under(resolved, p) for p in r.prefixes):
            r.refuse(f"ran {name} from outside the standard library before the recorder "
                     f"started")


def _search_path_inputs(r: Recorder) -> None:
    """Refuse the search path as a child's start refuses it, in case an entry changed
    since, as a link swapped; and list each entry in the repository as an input, so a
    module added there runs the child again."""
    if sys.flags.ignore_environment:
        return
    entries = _search_path(dict(_environment()).get(PATH_ENV), None)
    why = _search_path_refused(entries, r.inside, r.prefixes)
    if why:
        r.refuse(why.replace("starts a Python child whose ", "", 1))
        return
    for entry in entries:
        if _under(_norm(entry), r.nroot):
            r.list(entry)  # one in the parent's root only, the parent's recorder lists


def start(directory: str, config: dict) -> Recorder:
    """Install the recorder in this process, once: the .pth file can run twice in one
    start on Windows. Loaded as PARENT_MODULE, it is the parent's recorder, which starts
    before the test's and leaves ENV to it (COMP_NESTED_RECORDER)."""
    global _recorder
    if _recorder is not None:
        return _recorder
    _bind_long()
    r = _recorder = Recorder(directory, config)
    _restore_search_path(config)
    # The names the process starts with, its search path put back: a lookup's environment.
    r.start_names = sorted({_name(k) for k, _ in _environment()} - OWN)
    _started_clean(r, config)
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
        r.install(os, name, _probing(r, getattr(os, name), hashes, follows), f"os.{name}")
    for name, follows in (("exists", True), ("isfile", True), ("isdir", True),
                          ("realpath", True), ("lexists", False), ("islink", False),
                          ("isjunction", False)):
        if hasattr(os.path, name):
            r.install(os.path, name, _probing(r, getattr(os.path, name), False, follows),
                      f"os.path.{name}")
    # Only a child the recorder starts gets a directory: one that inherits this one, as a
    # process started some other way would, would write over this manifest.
    os.environ.pop(PARENT_ENV if __name__ == PARENT_MODULE else ENV, None)
    # The interpreter read these before the recorder started: the module search path, its
    # warnings, hash seed, encodings and locale. Named before the mapping records, and
    # read past any recording mapping, as the parent's is when this is the test's recorder.
    startup = [n for n, _ in _environment()
               if n.upper().startswith(("PYTHON", "LC_")) or n.upper() in ("LANG", "LANGUAGE")]
    # The C library reads the locale's variables where the mapping cannot see, as
    # setlocale(LC_ALL, "") does: each is recorded, set or not, so one set later differs.
    startup += [n for n in LOCALE_VARIABLES if n not in startup]
    for attribute in ("environ", "environb"):
        if hasattr(os, attribute):
            mapping = getattr(os, attribute)
            mapping.__class__ = _recording_environ(r, type(mapping))
            r.mappings.append((os, attribute, mapping.__class__, f"os.{attribute}"))
    for name in startup:
        os.environ.get(name)
    _watch_imports(r)
    _watch_children(r)
    _watch_rmtree(r)
    _watch_open(r)
    _watch_scandir(r)
    # After the import watch, so a platform module on PYTHONPATH is a lookup it records.
    _fix_host_name(r)
    sys.addaudithook(r.hook)
    r.started = True
    atexit.register(r.finish)
    return r


# --- the Sphinx build under the recorder ------------------------------------------------

#: What ``python -m trifecta.record`` may run in its own process: the build alone.
PROGRAMS = {"sphinx"}


def main(argv: list[str] | None = None) -> int:
    """``python -m trifecta.record sphinx ARGS``: run Sphinx in this process, which the
    .pth file has already started recording when ENV names a directory (COMP_BUILD_REUSE).
    """
    import runpy
    args = sys.argv[1:] if argv is None else argv
    if not args or args[0] not in PROGRAMS:
        print(f"usage: python -m trifecta.record {{{','.join(sorted(PROGRAMS))}}} ARGS",
              file=sys.stderr)
        return 2
    sys.argv = [args[0], *args[1:]]
    try:
        runpy.run_module(args[0], run_name="__main__", alter_sys=True)
    except SystemExit as exc:
        code = exc.code
        if code is None or isinstance(code, int):
            return code or 0
        print(code, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
