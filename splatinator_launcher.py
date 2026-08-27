"""Entry point for the packaged Splatinator.exe.

Inside the frozen build Python and every package are already bundled, so the
only prerequisites left to handle are COLMAP, Brush and the MSVC runtime. The
GUI checks for those on startup and can install them from its Setup panel, so
this launcher mostly just forwards to it - with a small first-run window for
the case where nothing is installed yet.
"""

import os
import sys

if getattr(sys, "frozen", False):
    sys.path.insert(0, os.path.dirname(os.path.abspath(sys.executable)))
else:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import prereqs  # noqa: E402


def attach_console():
    """The exe is built windowed; when started from a terminal, reuse that
    console so --check / --setup output is actually visible."""
    if not (getattr(sys, "frozen", False) and os.name == "nt"):
        return
    try:
        import ctypes
        if ctypes.windll.kernel32.AttachConsole(-1):
            sys.stdout = open("CONOUT$", "w", buffering=1)
            sys.stderr = open("CONOUT$", "w", buffering=1)
    except Exception:
        pass


def cli():
    """Support Splatinator.exe --check / --setup for scripted installs."""
    if not any(a.startswith("--") for a in sys.argv[1:]):
        return None
    attach_console()

    if "--check" in sys.argv:
        st = prereqs.print_report()
        missing = prereqs.missing_from(st)
        print("\nMissing: %s" % (", ".join(missing) if missing else "nothing"))
        return 0 if not missing else 1
    if "--setup" in sys.argv:
        force = "--force" in sys.argv
        return 0 if prereqs.ensure_all(force=force, skip_packages=True) else 1
    print("Unknown option. Supported: --check, --setup [--force]")
    return 2


def main():
    rc = cli()
    if rc is not None:
        return rc

    os.makedirs(os.path.join(prereqs.BASE_DIR, "outputs"), exist_ok=True)

    import splatinator
    splatinator.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
