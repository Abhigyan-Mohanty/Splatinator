"""Download COLMAP and Brush.

Kept for backwards compatibility with the old install_binaries scripts; the
actual work now lives in prereqs.py, which uses only the standard library and
so runs before pip has installed anything.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prereqs


def main():
    parser = argparse.ArgumentParser(description="Splatinator Binary Downloader")
    parser.add_argument("--os", choices=["windows", "macos", "linux"], default=None,
                        help="ignored - the running OS is detected automatically")
    parser.add_argument("--arch", default=None,
                        help="ignored - the architecture is detected automatically")
    parser.add_argument("--colmap_variant", "--colmap-variant", dest="colmap_variant",
                        choices=["cuda", "nocuda"], default=None,
                        help="override GPU auto-detection")
    parser.add_argument("--force", action="store_true",
                        help="re-download even if the binaries are already present")
    args = parser.parse_args()

    if args.os and args.os != ("windows" if prereqs.IS_WINDOWS else
                               ("macos" if prereqs.IS_MACOS else "linux")):
        print("NOTE: --os is ignored; binaries are always fetched for the running system.")

    prereqs.print_report()
    ok = prereqs.install_colmap(force=args.force, variant=args.colmap_variant)
    ok &= prereqs.install_brush(force=args.force)
    print("\nSetup complete!" if ok else "\nSetup finished with errors - see above.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
