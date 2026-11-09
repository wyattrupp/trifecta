"""Set up the toolchain (COMP_VALE_SETUP): the hashed Python lock, then Vale for this platform.

Vale comes from one table of release files and hashes (REQ_PLATFORM_TOOLCHAIN). The
check reads the table as data, so it holds literals only.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import os
import platform
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

VALE_VERSION = "3.13.0"
#: Platform key -> (release file, SHA-256, size in bytes), compared with Vale's checksum file.
VALE_FILES = {
    "linux-x86_64": ("vale_3.13.0_Linux_64-bit.tar.gz", "4378ee4bc7c2493760826270e55d5569cda35d7c89582e9fdc3070e2a1089193", 10236227),
    "linux-arm64": ("vale_3.13.0_Linux_arm64.tar.gz", "2134f23e7afbdf70b44272e6d3b5f26e85972340faa1e2a2b194358cf2892d84", 9554104),
    "macos-x86_64": ("vale_3.13.0_macOS_64-bit.tar.gz", "9f2991092579e85dd5be082c691b7b14ddbcd7c65477a6ff44b5f5e8dc3a9079", 10249040),
    "macos-arm64": ("vale_3.13.0_macOS_arm64.tar.gz", "2e89bd82cadfffa6abebda80a141529db2799df5d4197e6aa0489a4d711d8a3b", 9852125),
    "windows-x86_64": ("vale_3.13.0_Windows_64-bit.zip", "fb1141183d783ef1b9278ea5b1cc04e85801256b1539fc47147b90f6bf082341", 10464855),
}

SYSTEMS = {"Linux": "linux", "Darwin": "macos", "Windows": "windows"}
MACHINES = {"x86_64": "x86_64", "amd64": "x86_64", "aarch64": "arm64", "arm64": "arm64"}
RELEASES = f"https://github.com/errata-ai/vale/releases/download/v{VALE_VERSION}/"
#: The only hosts a download may be redirected to.
HOSTS = {"github.com", "objects.githubusercontent.com", "release-assets.githubusercontent.com"}


class SetupError(Exception):
    pass


def vale_path(root: Path) -> Path:
    """The one executable the check runs."""
    return root / "bin" / ("vale.exe" if platform.system() == "Windows" else "vale")


def platform_key() -> str:
    system = SYSTEMS.get(platform.system())
    machine = MACHINES.get(platform.machine().lower())
    if not system or not machine or f"{system}-{machine}" not in VALE_FILES:
        raise SetupError(f"no Vale release for {platform.system()} {platform.machine()}")
    return f"{system}-{machine}"


def _is_link(path: Path) -> bool:
    st = os.lstat(path)
    reparse = getattr(st, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return stat.S_ISLNK(st.st_mode) or bool(reparse)


def bin_dir(root: Path) -> Path:
    path = root / "bin"
    if os.path.lexists(path):
        if _is_link(path) or not path.is_dir():
            raise SetupError(f"{path} is a link or not a directory")
    else:
        path.mkdir()
    if not path.resolve().is_relative_to(root.resolve()):
        raise SetupError(f"{path} resolves outside the repository")
    return path


class _GitHubOnly(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        url = urllib.parse.urlsplit(newurl)
        if url.scheme != "https" or url.hostname not in HOSTS:
            raise SetupError(f"refused redirect to {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download(name: str, sha256: str, size: int) -> bytes:
    opener = urllib.request.build_opener(_GitHubOnly)
    with opener.open(RELEASES + name, timeout=60) as response:
        data = response.read(2 * size + 1)
    if len(data) > 2 * size:
        raise SetupError(f"{name} is larger than twice its expected {size} bytes")
    digest = hashlib.sha256(data).hexdigest()
    if digest != sha256:
        raise SetupError(f"{name} has SHA-256 {digest}, expected {sha256}")
    return data


def executable(name: str, data: bytes, member: str) -> bytes:
    """Read the one top-level regular file called ``member``; never extract by the archive's paths."""
    if name.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            found = [i for i in archive.infolist() if i.filename == member]
            if len(found) != 1 or found[0].is_dir() or stat.S_ISLNK(found[0].external_attr >> 16):
                raise SetupError(f"{name} does not hold exactly one regular file {member}")
            return archive.read(found[0])
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        found = [m for m in archive.getmembers() if m.name == member]
        if len(found) != 1 or not found[0].isreg():
            raise SetupError(f"{name} does not hold exactly one regular file {member}")
        return archive.extractfile(found[0]).read()


def install_vale(root: Path) -> Path:
    name, sha256, size = VALE_FILES[platform_key()]
    target = vale_path(root)
    directory = bin_dir(root)
    stamp = directory / ".vale-stamp"
    want = f"{VALE_VERSION} {sha256}\n"
    if not (target.is_file() and stamp.is_file() and stamp.read_text(encoding="utf-8") == want):
        stamp.unlink(missing_ok=True)
        binary = executable(name, download(name, sha256, size), target.name)
        fd, tmp = tempfile.mkstemp(dir=directory, prefix=".vale-")
        try:
            with os.fdopen(fd, "wb") as out:
                out.write(binary)
            os.chmod(tmp, 0o755)
            os.replace(tmp, target)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
        stamp.write_text(want, encoding="utf-8")
    version = subprocess.run([str(target), "--version"], capture_output=True,
                             encoding="utf-8", errors="replace", check=True).stdout
    if VALE_VERSION not in version:
        raise SetupError(f"{target} reports {version.strip()!r}, expected {VALE_VERSION}")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vale-only", action="store_true", help="skip the Python install")
    args = parser.parse_args(argv)
    try:
        if not args.vale_only:
            subprocess.run([sys.executable, "-m", "pip", "install", "--require-hashes",
                            "-r", str(ROOT / "requirements.lock")], check=True)
        print(f"vale {VALE_VERSION} at {install_vale(ROOT)}")
    except (SetupError, OSError, subprocess.CalledProcessError) as exc:
        print(f"setup failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
