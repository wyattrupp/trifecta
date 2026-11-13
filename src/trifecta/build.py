"""Build reuse (COMP_BUILD_REUSE): the Sphinx build, run under the recorder and stored
with its standard error, exit status and output directory, and restored where every input
its manifest holds still matches.

The build runs as ``python -m trifecta.record sphinx`` from ``docs/``, since Sphinx
changes into the configuration's directory to read ``conf.py`` and the recorder refuses
any other change of working directory. Its output directory is stored as one zip archive
without ``.doctrees``; a restore refuses the whole archive when any member is absolute,
holds ``..`` or is a link, before writing anything.
"""

from __future__ import annotations

import base64
import binascii
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from . import record, store
from .findings import CHILD_ENV

#: The build's arguments, run from ``docs/``; part of the stored build's identity.
ARGS = ["-q", "-E", "-n", "-W", "--keep-going", "--no-color", "-b", "html", ".",
        "_build/html"]
OUTPUT = Path("docs") / "_build" / "html"
#: What a restored archive may unpack to, since an entry is data from another run.
MAX_UNPACKED = 1 << 28
MAX_MEMBERS = 50_000


def environment() -> dict[str, str]:
    """The build's environment: the check's, less the recorder's and the store's."""
    return {k: v for k, v in CHILD_ENV.items() if k.upper() not in record.OWN}


def archive(directory: Path) -> str:
    """The output directory as a zip, base64, without the build's doctrees; a link or a
    junction under it is neither followed nor kept."""
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w", zipfile.ZIP_DEFLATED) as z:
        for top, dirs, files in os.walk(directory):
            here = Path(top)
            dirs[:] = sorted(d for d in dirs if d != ".doctrees"
                             and not _linked(here / d))
            for name in sorted(files):
                path = here / name
                if not _linked(path) and path.is_file():
                    z.write(path, path.relative_to(directory).as_posix())
    return base64.b64encode(data.getvalue()).decode("ascii")


def _linked(path: Path) -> bool:
    return path.is_symlink() or os.path.isjunction(path)


#: Names Windows takes for devices in any directory, whatever their extension.
DEVICES = frozenset({"con", "prn", "aux", "nul", "conin$", "conout$",
                     *(f"{p}{n}" for p in ("com", "lpt") for n in "0123456789")})


def _part_ok(part: str) -> bool:
    return (part not in ("", ".", "..") and not part.endswith((".", " "))
            and part.split(".", 1)[0].rstrip(" ").lower() not in DEVICES)


def members(text: str) -> tuple[zipfile.ZipFile, list[zipfile.ZipInfo]] | None:
    """The archive and its files, or None when any member is absolute, holds ``..``, is
    a link, names a device or repeats another's name but for case, or the whole would
    unpack past MAX_UNPACKED or hold more than MAX_MEMBERS: checked from the archive's
    directory before anything is read."""
    try:
        z = zipfile.ZipFile(io.BytesIO(base64.b64decode(text, validate=True)))
    except (binascii.Error, ValueError, zipfile.BadZipFile):
        return None
    infos = z.infolist()
    files, seen, total = [], set(), 0
    for info in infos:
        name = info.filename.rstrip("/") if info.is_dir() else info.filename
        if (len(infos) > MAX_MEMBERS or not name or name.startswith("/") or "\\" in name
                or ":" in name or "\0" in name or PurePosixPath(name).is_absolute()
                or not all(_part_ok(p) for p in name.split("/"))
                or stat.S_ISLNK(info.external_attr >> 16) or name.lower() in seen):
            z.close()
            return None
        seen.add(name.lower())
        if info.is_dir():
            continue
        total += info.file_size
        if total > MAX_UNPACKED:
            z.close()
            return None
        files.append(info)
    return z, files


def _result_ok(result) -> bool:
    return (isinstance(result, dict) and set(result) == {"returncode", "stderr", "archive"}
            and type(result["returncode"]) is int and isinstance(result["stderr"], str)
            and isinstance(result["archive"], str))


def _restore(result: dict, root: Path) -> bool:
    """Write the stored output directory into the clean build directory; False, having
    written nothing, when the archive is refused. A member that fails to unpack raises,
    and the caller removes what was written."""
    found = members(result["archive"])
    if found is None:
        return False
    z, files = found
    out = root / OUTPUT
    # Unpacked beside the output directory and moved into place whole, so a member that
    # fails leaves no page of it behind.
    staging = out.with_name(out.name + ".restoring")
    shutil.rmtree(staging, ignore_errors=True)
    try:
        with z:
            for info in files:
                target = staging / info.filename
                target.parent.mkdir(parents=True, exist_ok=True)
                with z.open(info) as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst)
        staging.mkdir(parents=True, exist_ok=True)
        os.replace(staging, out)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return True


def _run(root: Path, recorded_into: Path | None, pycache: Path) -> tuple[int, str]:
    env = environment()
    # A recorded build gets an empty pycache_prefix from its recorder, which refuses the
    # option (COMP_NESTED_RECORDER).
    prefix = [] if recorded_into is not None or record.recording() else [
        "-X", f"pycache_prefix={pycache}"]
    if recorded_into is not None:
        env[record.ENV] = str(recorded_into)
    proc = subprocess.run(
        [sys.executable, "-B", "-P", *prefix, "-m", "trifecta.record", "sphinx", *ARGS],
        cwd=root / "docs", capture_output=True, encoding="utf-8", errors="replace", env=env,
    )
    return proc.returncode, proc.stderr


def run_build(root: Path, fresh: bool = False, store_at: Path | None = None,
              ) -> tuple[int, str, bool, str]:
    """The build's exit status and standard error, whether they were reused, and why not.
    The build directory must be clean. ``fresh`` reuses nothing; a run inside a recorded
    process uses no store unless ``store_at`` names one."""
    if store_at is not None:
        shelf = store.Store(store_at, root)
    elif not record.recording():
        shelf = store.Store(store.location(root), root)
    else:
        shelf = None
    unused = shelf.refused() if shelf is not None else ""
    if unused:
        shelf = None
    why = "fresh" if fresh else ((unused or "not recorded") if shelf is None else "")
    ident = shelf.identity("sphinx", {"args": ARGS}) if shelf is not None else ""
    if shelf is not None and not fresh:
        found, why = shelf.lookup(ident, environment(), store.Hashes(), _result_ok)
        if found is not None:
            try:
                if _restore(found, root):
                    return (found["returncode"], store.restored(found["stderr"], root),
                            True, "")
                why = "an archive member that is absolute, holds .. or is a link"
            except (OSError, zipfile.BadZipFile, ValueError):
                why = "the stored output could not be written"
            shutil.rmtree(root / OUTPUT, ignore_errors=True)
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        tmp_path = Path(tmp)
        directory = tmp_path / "record" if shelf is not None else None
        if directory is not None:
            record.prepare(str(directory), str(root), ignore=[str(tmp_path)])
        returncode, stderr = _run(root, directory, tmp_path / "pycache")
        if directory is not None:
            try:
                manifest = json.loads((directory / record.MANIFEST).read_text(
                    encoding="utf-8"))
            except (OSError, ValueError):
                manifest = None
            if not record.valid(manifest):
                why = f"{why}; not stored: the build left no manifest"
            elif not manifest["storable"]:
                why = f"{why}; not stored: {manifest.get('why', '')}"
            elif store.holds_placeholder(stderr):
                why = f"{why}; not stored: its output holds the store's placeholder"
            elif not shelf.put(ident, manifest, {
                    "returncode": returncode, "stderr": store.portable(stderr, root),
                    "archive": archive(root / OUTPUT)}):
                why = f"{why}; not stored: the store refused it"
    return returncode, stderr, False, why[:store.MAX_WHY]
