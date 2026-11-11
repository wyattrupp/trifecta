"""The result store (COMP_RESULT_STORE, DEC_0028, DEC_0030): results kept with the
manifest of the run that made them, and reused only where every input it recorded still
matches.

An entry is filed under its identity: a hash of the stage, what the stage ran (for a test
module, its name and the tests left out of it), the environment key, and a hash of every
file of the package that runs the stage. Under one identity the store keeps entries
newest first; a lookup takes the first whose manifest matches the tree and environment
the run would see. The store holds results, never verdicts: what a result means is
decided by the running package every time.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import sys
import sysconfig
import time
from importlib import _bootstrap_external, machinery, metadata
from pathlib import Path

from . import record

ENV = record.STORE_ENV
#: The store a check uses when ENV names none; kept out of the clean before the build.
DEFAULT = Path("docs") / "_build" / "cache"
VERSION = 1
PACKAGE_DIR = Path(__file__).resolve().parent
#: What a reason for a miss may hold, so a profile stays short.
MAX_WHY = 300


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def location(root: Path) -> Path:
    """The store ENV names, or DEFAULT under the root."""
    given = os.environ.get(ENV)
    return Path(given) if given else root / DEFAULT


def package_hash(package: Path = PACKAGE_DIR) -> str:
    """Every file of the package that runs the stage, which an editable install's RECORD
    does not cover."""
    h = hashlib.sha256()
    for path in sorted(p for p in package.rglob("*")
                       if p.is_file() and "__pycache__" not in p.parts):
        h.update(path.relative_to(package).as_posix().encode("utf-8", "surrogateescape"))
        h.update(b"\0" + _sha(path.read_bytes()).encode() + b"\0")
    return h.hexdigest()


def _placeholder(root: Path):
    """The recorder's own replacement of the root's path, so values hash as it hashes them."""
    holder = record.Recorder.__new__(record.Recorder)
    holder.root = str(root)
    return holder.placeholder


def environment_key(root: Path) -> dict:
    """The system, the interpreter, the recorder's .pth file and every installed
    distribution: what a manifest leaves to the environment, under the interpreter's
    prefixes."""
    dists = []
    for dist in metadata.distributions():
        files = dist.read_text("RECORD") or ""
        dists.append([dist.metadata["Name"] or "", dist.version or "",
                      _sha(files.encode("utf-8", "surrogateescape"))])
    pth = Path(sysconfig.get_paths()["purelib"]) / record.PTH_NAME
    return {"os": os.name, "python": sys.version,
            "executable": _placeholder(root)(sys.executable),
            "runner": os.environ.get("RUNNER_OS"),
            "pth": record.file_hash(str(pth)),
            "distributions": sorted(dists)}


class Hashes:
    """What one check learns of the tree, so many manifests read each file and directory
    once."""

    def __init__(self):
        self.files: dict[str, str | None] = {}
        self.finders: dict[str, machinery.FileFinder] = {}

    def file(self, path: str) -> str | None:
        if path not in self.files:
            self.files[path] = record.file_hash(path) if record.kind(path) == "file" else None
        return self.files[path]

    def lookup(self, directory: str, name: str, root: Path) -> str | None:
        """What the import system finds for ``name`` in ``directory``, as the recorder
        writes it."""
        finder = self.finders.get(directory)
        if finder is None:
            finder = self.finders[directory] = machinery.FileFinder(
                directory, *_bootstrap_external._get_supported_file_loaders())
        spec = finder.find_spec(name)
        if spec is None:
            return None
        if spec.origin is None or not os.path.isabs(spec.origin):
            return "(namespace)"
        origin = Path(spec.origin)
        if origin.is_relative_to(root):
            return origin.relative_to(root).as_posix()
        return "(elsewhere)"


def _get(environ: dict, name: str) -> str | None:
    if os.name == "nt":
        for key, value in environ.items():
            if key.upper() == name:
                return value
        return None
    return environ.get(name)


def mismatch(manifest: dict, root: Path, environ: dict, hashes: Hashes) -> str | None:
    """The kind and path, or the variable's name, of the first input that differs; None
    when every input the manifest holds is as it was. Never a variable's value."""
    def at(key: str) -> str:
        return str(root if key == "." else root / key)

    for key, digest in manifest["files"].items():
        if hashes.file(at(key)) != digest:
            return f"file {key}"
    for key, digest in manifest["outside"].items():
        if hashes.file(key) != digest:
            return f"file {key}"
    for key, kind in manifest["probes"].items():
        if record.kind(key if os.path.isabs(key) else at(key)) != kind:
            return f"path {key}"
    for key, entries in manifest["listings"].items():
        if record.listing(key if os.path.isabs(key) else at(key)) != entries:
            return f"directory {key}"
    for key, found in manifest["lookups"].items():
        directory, _, name = key.rpartition("/")
        base = directory if os.path.isabs(directory) else at(directory)
        if hashes.lookup(base, name, root) != found:
            return f"import {key}"
    placeholder = _placeholder(root)
    for name, digest in manifest["environment"].items():
        value = _get(environ, name)
        now = None if value is None else _sha(
            placeholder(value).encode("utf-8", "surrogateescape"))
        if now != digest:
            return f"variable {name}"
    return None


class Store:
    """A directory of entries, one directory per identity."""

    def __init__(self, path: Path, root: Path):
        self.path, self.root = path, root
        self._base: dict | None = None

    def identity(self, stage: str, what: dict) -> str:
        if self._base is None:
            self._base = {"environment": environment_key(self.root),
                          "package": package_hash()}
        return _sha(json.dumps({"version": VERSION, "stage": stage, "what": what,
                                **self._base}, sort_keys=True).encode())

    def _dir(self, ident: str) -> Path:
        return self.path / ident[:2] / ident

    def lookup(self, ident: str, environ: dict, hashes: Hashes,
               result_ok) -> tuple[object | None, str]:
        """The newest stored result whose manifest matches, with ``""``; or None and why
        none did."""
        directory = self._dir(ident)
        try:
            names = sorted((p.name for p in directory.iterdir()
                            if p.suffix == ".json" and p.is_file()), reverse=True)
        except OSError:
            names = []
        why = "no stored result"
        for name in names:
            try:
                entry = json.loads((directory / name).read_text(encoding="utf-8"))
            except (OSError, ValueError, RecursionError):
                why = "a malformed entry"
                continue
            if not (isinstance(entry, dict) and set(entry) == {"version", "identity",
                                                                "manifest", "result"}
                    and type(entry["version"]) is int and entry["version"] == VERSION
                    and entry["identity"] == ident and record.valid(entry["manifest"])
                    and entry["manifest"]["storable"] and result_ok(entry["result"])):
                why = "a malformed entry"
                continue
            try:
                differs = mismatch(entry["manifest"], self.root, environ, hashes)
            except (OSError, ValueError, ImportError):
                differs = "an entry whose inputs cannot be read"
            if differs is None:
                return entry["result"], ""
            why = differs
        return None, why[:MAX_WHY]

    def put(self, ident: str, manifest: dict, result) -> bool:
        """Store a result; False, storing nothing, when the manifest is not a valid,
        storable one or the store cannot be written."""
        if not (record.valid(manifest) and manifest["storable"]):
            return False
        directory = self._dir(ident)
        name = f"{time.time_ns():020d}-{secrets.token_hex(4)}.json"
        tmp = directory / (name + ".tmp")
        try:
            directory.mkdir(parents=True, exist_ok=True)
            tmp.write_text(json.dumps({"version": VERSION, "identity": ident,
                                       "manifest": manifest, "result": result}),
                           encoding="utf-8")
            os.replace(tmp, directory / name)
        except OSError:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            return False
        return True
