"""Build a single .exe into dist/ with PyInstaller. Leaves only the .exe."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NAME = "GitScript"
DIST = ROOT / "dist"
BUILD = ROOT / "build"


def _clean_work() -> None:
    for path in (DIST, BUILD):
        if path.exists():
            shutil.rmtree(path)
    for spec in ROOT.glob("*.spec"):
        spec.unlink()


def _keep_only_exe() -> Path:
    if BUILD.exists():
        shutil.rmtree(BUILD)
    for spec in ROOT.glob("*.spec"):
        spec.unlink()

    if not DIST.exists():
        raise SystemExit("dist/ missing after build")

    preferred = DIST / f"{NAME}.exe"
    fallback = DIST / NAME
    keep = preferred if preferred.exists() else fallback if fallback.exists() else None
    if keep is None:
        raise SystemExit(f"expected {NAME}.exe in dist/")

    for item in list(DIST.iterdir()):
        if item.resolve() == keep.resolve():
            continue
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()
    return keep


def main() -> None:
    _clean_work()
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--noconfirm",
        "--clean",
        f"--name={NAME}",
        "--paths",
        str(ROOT / "src"),
        "--console",
        str(ROOT / "main.py"),
    ]
    subprocess.check_call(cmd, cwd=ROOT)
    exe = _keep_only_exe()
    print(f"ok  {exe}")


if __name__ == "__main__":
    main()
