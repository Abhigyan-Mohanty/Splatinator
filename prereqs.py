"""Prerequisite detection and installation for Splatinator.

Standard library only - this module must be importable before anything has been
installed, and it is also used from inside the frozen (PyInstaller) build where
there is no venv and no pip.

Windows is the primary target; macOS/Linux paths are kept working but the
auto-install steps there fall back to printing the right package-manager
command instead of downloading binaries that upstream does not publish.
"""

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.error
import urllib.request
import zipfile

# --------------------------------------------------------------------------
# Locations
# --------------------------------------------------------------------------

def _base_dir():
    """Folder that holds brush/, gaussiansplat/ and outputs/.

    When frozen by PyInstaller the code lives in a temp folder (sys._MEIPASS)
    but the downloaded binaries must sit next to the .exe so they survive
    across runs.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


BASE_DIR = _base_dir()
BRUSH_DIR = os.path.join(BASE_DIR, "brush")
COLMAP_DIR = os.path.join(BASE_DIR, "gaussiansplat")
VENV_DIR = os.path.join(BASE_DIR, ".venv")
CACHE_DIR = os.path.join(BASE_DIR, ".cache")
STATE_FILE = os.path.join(BASE_DIR, ".splatinator_setup.json")

IS_WINDOWS = platform.system().lower() == "windows"
IS_MACOS = platform.system().lower() == "darwin"
IS_FROZEN = getattr(sys, "frozen", False)

MIN_PYTHON = (3, 9)
REQUIRED_PACKAGES = ["opencv-python>=4.8.0", "requests>=2.28.0", "tqdm>=4.65.0"]
# ~1.1 GB extracted COLMAP-CUDA + ~0.5 GB Brush + working room for a project.
REQUIRED_FREE_BYTES = 8 * 1024 ** 3

REPOS = {"brush": "ArthurBrussee/brush", "colmap": "colmap/colmap"}

# Used only if the GitHub API is unreachable or rate limited.
FALLBACK_ASSETS = {
    ("colmap", "cuda"): "https://github.com/colmap/colmap/releases/download/4.1.1/colmap-x64-windows-cuda.zip",
    ("colmap", "nocuda"): "https://github.com/colmap/colmap/releases/download/4.1.1/colmap-x64-windows-nocuda.zip",
    ("brush", "windows"): "https://github.com/ArthurBrussee/brush/releases/download/v0.3.0/brush-app-x86_64-pc-windows-msvc.zip",
}


def _noop(msg):
    print(msg, flush=True)


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------

def _no_window_kwargs():
    """Keep helper processes from flashing a console window on Windows."""
    if IS_WINDOWS:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return {"startupinfo": si, "creationflags": 0x08000000}  # CREATE_NO_WINDOW
    return {}


def run_quiet(args, timeout=60):
    """Run a command, return (returncode, combined output). Never raises."""
    try:
        p = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            timeout=timeout,
            **_no_window_kwargs()
        )
        return p.returncode, (p.stdout or "")
    except FileNotFoundError:
        return 127, ""
    except Exception as exc:  # timeout, permissions, ...
        return 1, str(exc)


def human(nbytes):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if nbytes < 1024 or unit == "TB":
            return "%.1f %s" % (nbytes, unit)
        nbytes /= 1024.0


def find_executable(root, names, max_depth=4):
    """Depth-limited search for any of `names` under `root`.

    Binaries end up in different layouts depending on which archive version was
    unpacked (colmap-x64-windows-cuda/bin/colmap.exe vs bin/colmap.exe), so we
    look rather than guess.
    """
    if not os.path.isdir(root):
        return None
    wanted = {n.lower() for n in names}
    root_depth = root.rstrip(os.sep).count(os.sep)
    best = None
    for dirpath, dirnames, filenames in os.walk(root):
        if dirpath.count(os.sep) - root_depth >= max_depth:
            dirnames[:] = []
        for fn in filenames:
            if fn.lower() in wanted:
                path = os.path.join(dirpath, fn)
                # Prefer the earliest name in `names` (callers order by preference).
                rank = [n.lower() for n in names].index(fn.lower())
                if best is None or rank < best[0]:
                    best = (rank, path)
                if rank == 0:
                    return path
    return best[1] if best else None


# --------------------------------------------------------------------------
# Detection
# --------------------------------------------------------------------------

def find_colmap():
    """Path to a usable colmap executable, or None."""
    if IS_WINDOWS:
        found = find_executable(COLMAP_DIR, ["colmap.exe"])
        if found:
            return found
    else:
        found = find_executable(COLMAP_DIR, ["colmap"])
        if found and os.access(found, os.X_OK):
            return found
    return shutil.which("colmap")


def find_brush():
    """Path to a usable Brush executable, or None."""
    names = ["brush_app.exe", "brush.exe"] if IS_WINDOWS else ["brush_app", "brush"]
    found = find_executable(BRUSH_DIR, names)
    if found:
        return found
    return shutil.which("brush_app") or shutil.which("brush")


def colmap_is_cuda_build(colmap_path):
    """True when the installed COLMAP folder is the CUDA variant."""
    if not colmap_path:
        return False
    parts = os.path.abspath(colmap_path).lower().split(os.sep)
    if any("nocuda" in p for p in parts):
        return False
    if any("cuda" in p for p in parts):
        return True
    # Layouts without a telltale folder name: look for the CUDA runtime DLLs.
    bin_dir = os.path.dirname(colmap_path)
    try:
        return any(f.lower().startswith(("cudart64", "libcudart")) for f in os.listdir(bin_dir))
    except OSError:
        return False


def detect_gpu():
    """Return (has_nvidia, description). Falls back to WMI/wmic on Windows."""
    code, out = run_quiet(["nvidia-smi", "--query-gpu=name,memory.total,driver_version",
                           "--format=csv,noheader"], timeout=30)
    if code == 0 and out.strip():
        first = out.strip().splitlines()[0].strip()
        return True, first

    if IS_WINDOWS:
        code, out = run_quiet(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             "(Get-CimInstance Win32_VideoController).Name -join '; '"], timeout=60)
        if code == 0 and out.strip():
            desc = out.strip()
            return ("nvidia" in desc.lower()), desc
    return False, "unknown"


def detect_arch():
    machine = (os.environ.get("PROCESSOR_ARCHITEW6432")
               or platform.machine() or "").lower()
    if machine in ("amd64", "x64", "x86_64"):
        return "x86_64"
    if machine in ("arm64", "aarch64"):
        return "arm64"
    if machine in ("x86", "i386", "i686"):
        return "x86"
    return machine or "unknown"


def has_vc_redist():
    """COLMAP's Qt6 build needs the MSVC 2015-2022 x64 runtime."""
    if not IS_WINDOWS:
        return True
    system32 = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32")
    return all(os.path.exists(os.path.join(system32, dll))
               for dll in ("vcruntime140.dll", "vcruntime140_1.dll", "msvcp140.dll"))


def free_bytes(path=None):
    try:
        return shutil.disk_usage(path or BASE_DIR).free
    except Exception:
        return -1


def venv_python():
    if IS_WINDOWS:
        return os.path.join(VENV_DIR, "Scripts", "python.exe")
    return os.path.join(VENV_DIR, "bin", "python")


def venv_pythonw():
    """Windows GUI interpreter - launches the app without a console window."""
    p = os.path.join(VENV_DIR, "Scripts", "pythonw.exe")
    return p if os.path.exists(p) else venv_python()


def venv_ready():
    """True when the venv exists and already imports every runtime dependency."""
    py = venv_python()
    if not os.path.exists(py):
        return False
    code, _ = run_quiet([py, "-c", "import cv2, requests, tqdm, tkinter"], timeout=180)
    return code == 0


def current_python_has_deps():
    try:
        import cv2  # noqa: F401
        import requests  # noqa: F401
        import tkinter  # noqa: F401
        return True
    except Exception:
        return False


def status():
    """Snapshot of every prerequisite, for display and for gating the run."""
    colmap = find_colmap()
    brush = find_brush()
    has_gpu, gpu_desc = detect_gpu()
    return {
        "os": platform.system(),
        "os_version": platform.version(),
        "arch": detect_arch(),
        "python": "%d.%d.%d" % sys.version_info[:3],
        "python_ok": sys.version_info[:2] >= MIN_PYTHON,
        "frozen": IS_FROZEN,
        "colmap": colmap,
        "colmap_cuda": colmap_is_cuda_build(colmap),
        "brush": brush,
        "gpu": has_gpu,
        "gpu_desc": gpu_desc,
        "vc_redist": has_vc_redist(),
        "free": free_bytes(),
        "deps": True if IS_FROZEN else (current_python_has_deps() or venv_ready()),
    }


def missing_from(st):
    missing = []
    if not st["python_ok"]:
        missing.append("Python %d.%d+" % MIN_PYTHON)
    if not st["deps"]:
        missing.append("Python packages")
    if not st["colmap"]:
        missing.append("COLMAP")
    if not st["brush"]:
        missing.append("Brush")
    if not st["vc_redist"]:
        missing.append("Visual C++ runtime")
    return missing


# --------------------------------------------------------------------------
# Download / extract
# --------------------------------------------------------------------------

_UA = {"User-Agent": "Splatinator-Setup/2.0"}


def _open_url(url, extra_headers=None):
    headers = dict(_UA)
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, headers=headers)
    return urllib.request.urlopen(req, timeout=60)


def download(url, dest, log=_noop, attempts=3):
    """Download with progress, resume and retry. Returns True on success."""
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    part = dest + ".part"

    for attempt in range(1, attempts + 1):
        have = os.path.getsize(part) if os.path.exists(part) else 0
        headers = {"Range": "bytes=%d-" % have} if have else None
        try:
            with _open_url(url, headers) as resp:
                resuming = resp.status == 206 and have
                if not resuming:
                    have = 0
                total = int(resp.headers.get("content-length", 0)) + have
                mode = "ab" if resuming else "wb"
                log("    %s (%s)" % (os.path.basename(dest),
                                     human(total) if total else "size unknown"))
                done = have
                last = time.time()
                with open(part, mode) as fh:
                    while True:
                        chunk = resp.read(1024 * 256)
                        if not chunk:
                            break
                        fh.write(chunk)
                        done += len(chunk)
                        if time.time() - last > 1.0:
                            last = time.time()
                            if total:
                                log("      %5.1f%%  %s / %s" %
                                    (done * 100.0 / total, human(done), human(total)))
                            else:
                                log("      %s" % human(done))
            os.replace(part, dest)
            log("      done.")
            return True
        except Exception as exc:
            log("    download failed (attempt %d/%d): %s" % (attempt, attempts, exc))
            if attempt == attempts:
                return False
            time.sleep(2 * attempt)
    return False


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_members(names, target_dir):
    """Reject archive entries that would escape the target directory."""
    target = os.path.abspath(target_dir)
    for name in names:
        dest = os.path.abspath(os.path.join(target, name))
        if not (dest == target or dest.startswith(target + os.sep)):
            raise ValueError("unsafe path in archive: %s" % name)


def extract(archive, target_dir, log=_noop):
    log("    extracting %s ..." % os.path.basename(archive))
    os.makedirs(target_dir, exist_ok=True)
    try:
        low = archive.lower()
        if low.endswith(".zip"):
            with zipfile.ZipFile(archive) as z:
                _safe_members(z.namelist(), target_dir)
                z.extractall(target_dir)
        elif low.endswith((".tar.gz", ".tgz", ".tar.xz", ".txz", ".xz")):
            mode = "r:gz" if low.endswith((".tar.gz", ".tgz")) else "r:xz"
            with tarfile.open(archive, mode) as t:
                _safe_members(t.getnames(), target_dir)
                t.extractall(target_dir)
        else:
            log("    unsupported archive type: %s" % archive)
            return False
    except Exception as exc:
        log("    extraction failed: %s" % exc)
        return False

    if not IS_WINDOWS:
        for dirpath, _dirs, files in os.walk(target_dir):
            for fn in files:
                if fn in ("brush", "brush_app", "colmap"):
                    p = os.path.join(dirpath, fn)
                    os.chmod(p, os.stat(p).st_mode | 0o111)
    log("    extracted.")
    return True


def latest_release(repo, log=_noop):
    """(assets, tag) for a repo's latest release; ([], None) if unavailable."""
    url = "https://api.github.com/repos/%s/releases/latest" % repo
    try:
        with _open_url(url, {"Accept": "application/vnd.github+json"}) as resp:
            data = json.load(resp)
        return data.get("assets", []), data.get("tag_name")
    except urllib.error.HTTPError as exc:
        log("    GitHub API returned %s for %s (using pinned fallback)." % (exc.code, repo))
    except Exception as exc:
        log("    Could not reach GitHub API for %s: %s (using pinned fallback)." % (repo, exc))
    return [], None


# --------------------------------------------------------------------------
# Install steps
# --------------------------------------------------------------------------

def install_brush(log=_noop, force=False):
    if not force and find_brush():
        log("[Brush]  already installed: %s" % find_brush())
        return True

    log("[Brush]  installing ...")
    system = "windows" if IS_WINDOWS else ("macos" if IS_MACOS else "linux")
    pattern = {"windows": "pc-windows-msvc.zip",
               "macos": "apple-darwin.tar.xz",
               "linux": "unknown-linux-gnu.tar.xz"}[system]

    assets, tag = latest_release(REPOS["brush"], log)
    url = checksum_url = None
    for asset in assets:
        name = asset.get("name", "")
        if name.endswith(pattern):
            url = asset["browser_download_url"]
        elif name.endswith(pattern + ".sha256"):
            checksum_url = asset["browser_download_url"]
    if not url:
        url = FALLBACK_ASSETS.get(("brush", system))
        tag = "pinned"
    if not url:
        log("[Brush]  no download available for %s. Build from source: %s"
            % (system, "https://github.com/" + REPOS["brush"]))
        return False

    os.makedirs(CACHE_DIR, exist_ok=True)
    archive = os.path.join(CACHE_DIR, os.path.basename(url))
    if not download(url, archive, log):
        return False

    if checksum_url:
        try:
            with _open_url(checksum_url) as resp:
                expected = resp.read().decode().split()[0].strip()
            actual = sha256_of(archive)
            if expected.lower() != actual.lower():
                log("[Brush]  checksum mismatch - discarding download.")
                os.remove(archive)
                return False
            log("    checksum verified.")
        except Exception as exc:
            log("    checksum check skipped: %s" % exc)

    if not extract(archive, BRUSH_DIR, log):
        return False
    try:
        os.remove(archive)
    except OSError:
        pass

    found = find_brush()
    log("[Brush]  installed %s -> %s" % (tag or "", found))
    return bool(found)


def install_colmap(log=_noop, force=False, variant=None):
    if not force and find_colmap():
        path = find_colmap()
        log("[COLMAP] already installed: %s (%s build)"
            % (path, "CUDA" if colmap_is_cuda_build(path) else "CPU"))
        return True

    if not IS_WINDOWS:
        log("[COLMAP] Upstream publishes binaries for Windows only.")
        log("[COLMAP] macOS:  brew install colmap")
        log("[COLMAP] Ubuntu: sudo apt install colmap")
        return False

    if variant is None:
        has_gpu, desc = detect_gpu()
        variant = "cuda" if has_gpu else "nocuda"
        log("[COLMAP] GPU detected: %s" % desc)
        log("[COLMAP] Choosing the %s build." % variant)

    arch = detect_arch()
    if arch != "x86_64":
        log("[COLMAP] Note: only x64 builds exist; on %s Windows they run under "
            "emulation and CUDA will not work." % arch)
        variant = "nocuda"

    assets, tag = latest_release(REPOS["colmap"], log)
    url = None
    for asset in assets:
        if asset.get("name", "").endswith("windows-%s.zip" % variant):
            url = asset["browser_download_url"]
            break
    if not url:
        url = FALLBACK_ASSETS.get(("colmap", variant))
        tag = "pinned"
    if not url:
        log("[COLMAP] No %s asset found in the latest release." % variant)
        return False

    log("[COLMAP] installing %s build (this is a large download) ..." % variant)
    os.makedirs(CACHE_DIR, exist_ok=True)
    archive = os.path.join(CACHE_DIR, os.path.basename(url))
    if not download(url, archive, log):
        return False
    if not extract(archive, COLMAP_DIR, log):
        return False
    try:
        os.remove(archive)
    except OSError:
        pass

    found = find_colmap()
    log("[COLMAP] installed %s -> %s" % (tag or "", found))
    return bool(found)


def install_vc_redist(log=_noop):
    """Install the MSVC 2015-2022 x64 runtime that COLMAP's Qt build needs."""
    if has_vc_redist():
        log("[VC++]   runtime present.")
        return True
    if not IS_WINDOWS:
        return True

    log("[VC++]   Microsoft Visual C++ runtime missing - installing ...")
    if shutil.which("winget"):
        code, out = run_quiet(
            ["winget", "install", "--id", "Microsoft.VCRedist.2015+.x64",
             "-e", "--silent", "--accept-package-agreements",
             "--accept-source-agreements"], timeout=600)
        if code == 0 and has_vc_redist():
            log("[VC++]   installed via winget.")
            return True

    os.makedirs(CACHE_DIR, exist_ok=True)
    installer = os.path.join(CACHE_DIR, "vc_redist.x64.exe")
    if download("https://aka.ms/vs/17/release/vc_redist.x64.exe", installer, log):
        log("[VC++]   running installer (a UAC prompt may appear) ...")
        run_quiet(["powershell", "-NoProfile", "-Command",
                   "Start-Process -FilePath '%s' -ArgumentList '/install','/quiet','/norestart' "
                   "-Verb RunAs -Wait" % installer], timeout=900)
    if has_vc_redist():
        log("[VC++]   installed.")
        return True
    log("[VC++]   could not install automatically. Get it from "
        "https://aka.ms/vs/17/release/vc_redist.x64.exe")
    return False


def install_python_packages(log=_noop):
    """Make sure cv2/requests/tqdm are importable, using a venv when needed."""
    if IS_FROZEN:
        log("[Python] packages are bundled in the executable.")
        return True

    if current_python_has_deps():
        log("[Python] all packages already available in %s" % sys.executable)
        return True

    py = venv_python()
    if not os.path.exists(py):
        log("[Python] creating virtual environment in .venv ...")
        code, out = run_quiet([sys.executable, "-m", "venv", VENV_DIR], timeout=600)
        if code != 0 or not os.path.exists(py):
            log("[Python] venv creation failed: %s" % out.strip()[:500])
            log("[Python] falling back to installing into %s" % sys.executable)
            py = sys.executable

    log("[Python] installing packages (opencv-python, requests, tqdm) ...")
    args = [py, "-m", "pip", "install", "--disable-pip-version-check"]
    if py == sys.executable:
        args.append("--user")
    code, out = run_quiet(args + ["--upgrade", "pip"], timeout=900)
    code, out = run_quiet(args + REQUIRED_PACKAGES, timeout=1800)
    for line in out.strip().splitlines()[-12:]:
        log("    " + line)
    if code != 0:
        log("[Python] package installation failed.")
        return False

    if not (venv_ready() or current_python_has_deps()):
        log("[Python] packages installed but still not importable.")
        return False
    log("[Python] packages ready.")
    return True


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------

def print_report(log=_noop, st=None):
    st = st or status()
    tick = lambda ok: "OK     " if ok else "MISSING"
    log("=" * 62)
    log(" Splatinator - system check")
    log("=" * 62)
    log("  System        : %s (%s)" % (st["os"], st["arch"]))
    log("  Python        : %-8s [%s]" % (st["python"], tick(st["python_ok"])))
    log("  Packages      : %s" % tick(st["deps"]))
    log("  GPU           : %s" % st["gpu_desc"])
    log("  VC++ runtime  : %s" % tick(st["vc_redist"]))
    log("  COLMAP        : %s" % (("%s (%s)" % (st["colmap"], "CUDA" if st["colmap_cuda"] else "CPU"))
                                  if st["colmap"] else "MISSING"))
    log("  Brush         : %s" % (st["brush"] or "MISSING"))
    if st["free"] >= 0:
        log("  Free disk     : %s" % human(st["free"]))
    log("=" * 62)
    return st


def ensure_all(log=_noop, force=False, colmap_variant=None, skip_packages=False):
    """Run every setup step. Returns True when the app can run afterwards."""
    st = print_report(log)

    if st["os"].lower() == "windows" and st["arch"] not in ("x86_64", "arm64"):
        log("WARNING: unsupported architecture %s - 32-bit Windows cannot run "
            "COLMAP or Brush." % st["arch"])

    if not st["python_ok"] and not IS_FROZEN:
        log("ERROR: Python %d.%d+ is required, this is %s."
            % (MIN_PYTHON[0], MIN_PYTHON[1], st["python"]))
        return False

    need_download = force or not (st["colmap"] and st["brush"])
    if need_download and st["free"] >= 0 and st["free"] < REQUIRED_FREE_BYTES:
        log("WARNING: only %s free on this drive; the COLMAP CUDA build alone "
            "needs about 1.5 GB." % human(st["free"]))

    ok = True
    if not skip_packages:
        ok &= install_python_packages(log)
    install_vc_redist(log)          # advisory: COLMAP may still start without it
    ok &= install_colmap(log, force=force, variant=colmap_variant)
    ok &= install_brush(log, force=force)

    log("")
    final = print_report(log)
    missing = missing_from(final)
    if missing:
        log("Setup incomplete. Still missing: %s" % ", ".join(missing))
    else:
        log("All prerequisites are installed. Splatinator is ready.")
        save_state(final)
    return ok and not missing


def save_state(st=None):
    try:
        st = st or status()
        with open(STATE_FILE, "w", encoding="utf-8") as fh:
            json.dump({"checked_at": time.time(), "status": st}, fh, indent=2)
    except Exception:
        pass


def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def setup_completed_before():
    state = load_state()
    return bool(state and not missing_from(state.get("status", {"python_ok": False,
                                                               "deps": False,
                                                               "colmap": None,
                                                               "brush": None,
                                                               "vc_redist": False})))


def colmap_env(colmap_path):
    """Environment that lets COLMAP find its Qt plugins and DLLs."""
    env = os.environ.copy()
    if not colmap_path:
        return env
    bin_dir = os.path.dirname(os.path.abspath(colmap_path))
    root = os.path.dirname(bin_dir)
    for plugins in (os.path.join(root, "plugins"), os.path.join(bin_dir, "plugins")):
        if os.path.isdir(plugins):
            env["QT_PLUGIN_PATH"] = plugins + os.pathsep + env.get("QT_PLUGIN_PATH", "")
            break
    env["PATH"] = bin_dir + os.pathsep + env.get("PATH", "")
    return env


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(
        description="Check and install everything Splatinator needs.")
    parser.add_argument("--check", action="store_true",
                        help="only report what is present, install nothing")
    parser.add_argument("--force", action="store_true",
                        help="re-download COLMAP and Brush even if present")
    parser.add_argument("--colmap-variant", choices=["cuda", "nocuda"], default=None,
                        help="override GPU auto-detection")
    parser.add_argument("--skip-packages", action="store_true",
                        help="do not touch pip / the virtual environment")
    args = parser.parse_args(argv)

    if args.check:
        st = print_report()
        missing = missing_from(st)
        print("\nMissing: %s" % (", ".join(missing) if missing else "nothing"))
        return 0 if not missing else 1

    ok = ensure_all(force=args.force, colmap_variant=args.colmap_variant,
                    skip_packages=args.skip_packages)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
