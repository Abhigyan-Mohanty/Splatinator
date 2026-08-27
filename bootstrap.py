"""Splatinator first-run bootstrapper.

Run by Splatinator.bat once a Python interpreter is available. It installs
every prerequisite (packages, COLMAP, Brush, MSVC runtime) and then starts the
GUI with the interpreter that actually has the packages - normally the .venv
one, so the user never has to think about environments.

Stdlib only: this runs before pip has installed anything.
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prereqs  # noqa: E402


def launch_gui(force_console=False):
    """Start splatinator.py with an interpreter that has the dependencies."""
    app = os.path.join(prereqs.BASE_DIR, "splatinator.py")
    if not os.path.exists(app):
        print("ERROR: splatinator.py not found next to bootstrap.py")
        return 1

    if prereqs.current_python_has_deps():
        python = sys.executable
    elif prereqs.venv_ready():
        python = prereqs.venv_python()
    else:
        print("ERROR: no interpreter with the required packages. "
              "Run Splatinator.bat again, or `python bootstrap.py --setup`.")
        return 1

    if not force_console and prereqs.IS_WINDOWS:
        # pythonw.exe runs the GUI with no console window attached.
        gui_python = os.path.join(os.path.dirname(python), "pythonw.exe")
        if os.path.exists(gui_python):
            python = gui_python

    print("Starting Splatinator ...")
    if force_console:
        return subprocess.call([python, app], cwd=prereqs.BASE_DIR)
    creationflags = 0x00000008 if prereqs.IS_WINDOWS else 0  # DETACHED_PROCESS
    subprocess.Popen([python, app], cwd=prereqs.BASE_DIR, creationflags=creationflags)
    return 0


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Splatinator bootstrapper")
    parser.add_argument("--setup", action="store_true",
                        help="run setup only, do not launch the app")
    parser.add_argument("--check", action="store_true",
                        help="print the system check and exit")
    parser.add_argument("--force", action="store_true",
                        help="re-download COLMAP and Brush")
    parser.add_argument("--repair", action="store_true",
                        help="same as --force, then launch")
    parser.add_argument("--colmap-variant", choices=["cuda", "nocuda"], default=None)
    parser.add_argument("--console", action="store_true",
                        help="keep the app attached to this console (for debugging)")
    args = parser.parse_args(argv)

    if args.check:
        return prereqs.main(["--check"])

    st = prereqs.status()
    missing = prereqs.missing_from(st)
    force = args.force or args.repair

    if missing or force:
        if missing:
            print("First-time setup needed: %s" % ", ".join(missing))
            print("This downloads about 0.5-1.5 GB and can take several minutes.\n")
        ok = prereqs.ensure_all(force=force, colmap_variant=args.colmap_variant)
        if not ok and not args.setup:
            print("\nSetup did not complete. Starting the app anyway so you can "
                  "retry from the Setup tab.\n")
    else:
        print("All prerequisites present.")
        prereqs.save_state(st)

    if args.setup:
        return 0
    return launch_gui(force_console=args.console)


if __name__ == "__main__":
    sys.exit(main())
