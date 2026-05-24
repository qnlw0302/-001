"""Build the desktop bundle: SPA build, then PyInstaller package of desktop.py.

Outputs (relative to repo root):
  build/desktop/InventoryManagement.app   (macOS)
  build/desktop/InventoryManagement.exe   (Windows, one-file)
  build/pyi/                              (PyInstaller workdir, safe to delete)

Usage:
  python scripts/build_desktop.py
  python scripts/build_desktop.py --skip-frontend   # if dist/ is already up to date
  python scripts/build_desktop.py --clean-frontend  # wipe node_modules + lockfile before npm install

Note on Python environment:
  PyInstaller follows transitive imports and runs per-package hooks for everything
  reachable from the interpreter's site-packages. Running this script from a "kitchen
  sink" Python (Anaconda, system Python with many libs) will produce a huge bundle
  and can crash on unrelated package hooks (e.g. matplotlib). For best results,
  build from a clean venv that has only `pip install -r requirements.txt` installed.
  This script also passes --exclude-module for common heavyweights as a safety net.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "inventory-management-web"
FRONTEND_DIST = WEB_DIR / "dist"
DESKTOP_ENTRY = ROOT / "desktop.py"
OUT_DIR = ROOT / "build" / "desktop"
WORK_DIR = ROOT / "build" / "pyi"
SPEC_DIR = ROOT / "build"
APP_NAME = "InventoryManagement"

# Tell PyInstaller not to chase these — desktop.py doesn't import them, but they
# may be transitively reachable from a kitchen-sink Python (Anaconda etc.) and
# their hooks bloat the bundle or crash the build (matplotlib hook in particular).
EXCLUDED_MODULES = [
    "matplotlib",
    "numpy",
    "pandas",
    "scipy",
    "sklearn",
    "IPython",
    "ipykernel",
    "jupyter",
    "jupyter_client",
    "jupyter_core",
    "notebook",
    "nbformat",
    "nbconvert",
    "mistune",
    "zmq",
    "tornado",
    "PIL",
    "PyQt5",
    "PyQt6",
    "PySide2",
    "PySide6",
    "tkinter",
    "test",
    "unittest",
    "pytest",
]


def run(cmd: list[str], **kwargs) -> None:
    printable = " ".join(str(arg) for arg in cmd)
    print(f">> {printable}", flush=True)
    subprocess.run(cmd, check=True, **kwargs)


def _native_arm64_prefix() -> list[str]:
    """On Apple Silicon, prepend `arch -arm64` so child node/npm don't inherit x86_64
    from a Rosetta-translated parent (e.g. Anaconda Python). Without this, vite asks
    for @rollup/rollup-darwin-x64 even though only the arm64 binary is installed."""
    if sys.platform != "darwin":
        return []
    try:
        result = subprocess.run(
            ["sysctl", "-n", "hw.optional.arm64"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return []
    if result.stdout.strip() == "1":
        return ["arch", "-arm64"]
    return []


def _wipe_frontend_install() -> None:
    """Apply the documented fix for npm bug #4828 (missing rollup optional native dep)."""
    node_modules = WEB_DIR / "node_modules"
    lockfile = WEB_DIR / "package-lock.json"
    if node_modules.is_dir():
        print(f">> rm -rf {node_modules}", flush=True)
        shutil.rmtree(node_modules)
    if lockfile.is_file():
        print(f">> rm {lockfile}", flush=True)
        lockfile.unlink()


def build_frontend(clean: bool = False) -> None:
    npm = shutil.which("npm")
    if npm is None:
        raise SystemExit("npm not found on PATH. Install Node.js before running this script.")
    arch_prefix = _native_arm64_prefix()
    if clean:
        _wipe_frontend_install()
    if not (WEB_DIR / "node_modules").is_dir():
        run(arch_prefix + [npm, "install"], cwd=WEB_DIR)
    try:
        run(arch_prefix + [npm, "run", "build"], cwd=WEB_DIR)
    except subprocess.CalledProcessError:
        sys.stderr.write(
            "\nFrontend build failed. If the error mentions @rollup/rollup-* "
            "(npm optional-deps bug), re-run:\n"
            "    python scripts/build_desktop.py --clean-frontend\n\n"
        )
        raise
    if not (FRONTEND_DIST / "index.html").is_file():
        raise SystemExit(
            f"Frontend build did not produce {FRONTEND_DIST / 'index.html'}"
        )


def build_app() -> None:
    if not DESKTOP_ENTRY.is_file():
        raise SystemExit(f"Missing entrypoint: {DESKTOP_ENTRY}")
    if not (FRONTEND_DIST / "index.html").is_file():
        raise SystemExit(
            "Frontend dist/ not found. Run without --skip-frontend or rebuild the SPA."
        )

    # PyInstaller uses ':' on POSIX, ';' on Windows for --add-data SRC<sep>DEST.
    sep = ";" if sys.platform.startswith("win") else ":"
    add_data = f"{FRONTEND_DIST}{sep}inventory-management-web/dist"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        APP_NAME,
        "--add-data",
        add_data,
        "--distpath",
        str(OUT_DIR),
        "--workpath",
        str(WORK_DIR),
        "--specpath",
        str(SPEC_DIR),
    ]
    for mod in EXCLUDED_MODULES:
        cmd.extend(["--exclude-module", mod])
    cmd.append(str(DESKTOP_ENTRY))
    run(cmd, cwd=ROOT)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the desktop bundle.")
    parser.add_argument(
        "--skip-frontend",
        action="store_true",
        help="Skip the npm build step (use existing inventory-management-web/dist).",
    )
    parser.add_argument(
        "--clean-frontend",
        action="store_true",
        help="Wipe inventory-management-web/{node_modules,package-lock.json} before npm install.",
    )
    args = parser.parse_args()

    if not args.skip_frontend:
        build_frontend(clean=args.clean_frontend)
    build_app()

    print(f"\nBuild complete. Output in: {OUT_DIR}")


if __name__ == "__main__":
    main()
