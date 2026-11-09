"""Where Vale lives, and how Vale names its release files (REQ_PLATFORM_TOOLCHAIN).

Shared by the setup script, which fetches Vale, and the check, which runs it and checks
the setup script's table. Holds no table of its own.
"""

from __future__ import annotations

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


def vale_path(root: Path) -> Path:
    """The one executable the check runs."""
    return root / "bin" / ("vale.exe" if platform.system() == "Windows" else "vale")
