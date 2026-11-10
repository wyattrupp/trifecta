"""Where Vale lives, and how Vale names its release files (REQ_PLATFORM_TOOLCHAIN).

Shared by the setup script, which fetches Vale, and the check, which runs it and checks
the setup script's table. Holds no table of its own.
"""

from __future__ import annotations

import os
import platform
from pathlib import Path

#: Platform key -> the suffix of the file Vale releases for it, after ``vale_<version>_``.
VALE_SUFFIXES = {
    "linux-x86_64": "Linux_64-bit.tar.gz",
    "linux-arm64": "Linux_arm64.tar.gz",
    "macos-x86_64": "macOS_64-bit.tar.gz",
    "macos-arm64": "macOS_arm64.tar.gz",
    "windows-x86_64": "Windows_64-bit.zip",
}


#: The package's own directory, which holds its data: the Vale configurations and styles.
PACKAGE_DIR = Path(__file__).resolve().parent


class OutsideRepository(Exception):
    """A path argument that resolves outside the repository (IF_CLI)."""


def corpus_root() -> Path:
    """The corpus every command reads: the working directory (IF_CLI)."""
    return Path.cwd().resolve()


def inside(path: Path, root: Path) -> Path:
    """``path`` resolved, refused when it resolves outside ``root``."""
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root):
        raise OutsideRepository(f"{path} resolves outside the repository")
    return resolved


#: Names the Vale executable in place of the repository's own; the fixture runner sets it,
#: so each repository copy runs the Vale its original set up.
VALE_ENV = "TRIFECTA_VALE"


def bin_vale(root: Path) -> Path:
    """Where setup writes Vale: the repository's own ``bin/``."""
    return root / "bin" / ("vale.exe" if platform.system() == "Windows" else "vale")


def vale_path(root: Path) -> Path:
    """The one executable the check runs."""
    if override := os.environ.get(VALE_ENV):
        return Path(override)
    return bin_vale(root)
