"""Build Splatinator.exe - a standalone Windows executable.

    python build_exe.py

Produces dist/Splatinator.exe. The exe bundles Python, tkinter and OpenCV, so
the end user needs nothing preinstalled; COLMAP and Brush are still downloaded
on first launch into the folder the exe lives in.
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENTRY = os.path.join(HERE, "splatinator_launcher.py")
ICON = os.path.join(HERE, "assets", "splatinator.ico")


def ensure_pyinstaller():
    try:
        import PyInstaller  # noqa: F401
        return True
    except ImportError:
        print("Installing PyInstaller...")
        code = subprocess.call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        return code == 0


def main():
    if os.name != "nt":
        print("This build script targets Windows.")
    if not ensure_pyinstaller():
        print("Could not install PyInstaller.")
        return 1

    try:
        import cv2  # noqa: F401
    except ImportError:
        print("Installing opencv-python so it can be bundled...")
        subprocess.call([sys.executable, "-m", "pip", "install", "opencv-python"])

    args = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--name", "Splatinator",
        "--onefile",
        "--windowed",
        "--hidden-import", "prereqs",
        "--hidden-import", "splatinator",
        "--collect-submodules", "cv2",
        "--paths", HERE,
    ]
    if os.path.exists(ICON):
        args += ["--icon", ICON]
    args.append(ENTRY)

    print(" ".join(args))
    code = subprocess.call(args, cwd=HERE)
    if code != 0:
        return code

    exe = os.path.join(HERE, "dist", "Splatinator.exe")
    print("\nBuilt: %s (%.1f MB)" % (exe, os.path.getsize(exe) / 1024.0 / 1024.0))
    print("Ship dist/Splatinator.exe on its own - it downloads COLMAP and Brush")
    print("into whatever folder it is run from, on first launch.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
