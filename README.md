# Splatinator

**Turn a phone video into a 3D Gaussian Splat you can fly through — in one click.**

Splatinator runs the whole Gaussian Splatting pipeline for you: it pulls frames out of your
video, reconstructs the camera positions with **COLMAP**, and opens the result in the
**Brush** real-time splat renderer. No Python knowledge, no command line, no manual setup.

---

## Download

### [⬇ Download Splatinator.exe](https://github.com/Abhigyan-Mohanty/Splatinator/releases/latest/download/Splatinator.exe)

**That's the only file you need.** Windows 10 or 11, 64-bit.

1. **Download** the file above (66 MB).
2. **Put it in its own folder** — say `Documents\Splatinator`. It will download its tools
   into that folder, so give it a home rather than leaving it in Downloads.
3. **Double-click it.**

The first launch sets everything up by itself: it detects your graphics card, downloads the
matching COLMAP build and the Brush renderer, and installs the Visual C++ runtime if your PC
doesn't have it. That's a **0.5–1.5 GB download and a few minutes, once**. Every launch after
that opens instantly.

You don't need Python. You don't need administrator rights.

> **"Windows protected your PC"?**
> Splatinator isn't code-signed (certificates cost hundreds a year), so SmartScreen warns about
> it like it does for most small open-source tools. Click **More info → Run anyway**.
> If you'd rather not, use the [run-from-source](#option-2-run-from-source) route instead —
> same program, no downloaded binary.

---

## Make your first splat

1. **Record a video.** Walk slowly all the way around your subject, keeping it in frame the
   whole time. 30–60 seconds is plenty. Slow and steady beats fast and shaky — motion blur is
   the number one cause of failed reconstructions.
2. **Open Splatinator** and type a **Project Name** (anything, e.g. `my-shoes`).
3. **Select Files…** and pick your video.
4. Leave **Extraction FPS** at **2** to start. Higher means more detail and a much slower run.
5. Hit **Start Processing** and watch the log.
6. **Brush opens by itself** when it's done. Drag to orbit, scroll to zoom.

Photos work too — pick **Multiple Photos** instead. Aim for 50+ overlapping shots.

**How long does it take?** With an NVIDIA GPU, a 2 FPS minute-long video is roughly 5–15
minutes. Without one, expect considerably longer — it still works, it just runs on the CPU.

---

## Tips for good results

| Do | Don't |
| --- | --- |
| Move slowly and steadily | Move fast — motion blur ruins reconstruction |
| Circle the subject completely | Film from one spot only |
| Keep lighting constant | Shoot into the sun or in dim rooms |
| Textured, detailed subjects | Blank walls, glass, mirrors, shiny metal |
| Start at 2 FPS, raise it if you want detail | Jump straight to 30 FPS — it'll take hours |

---

## What your PC needs

|  | Minimum | Comfortable |
| --- | --- | --- |
| **OS** | Windows 10/11 64-bit | Same |
| **GPU** | Any DirectX 12 / Vulkan card | NVIDIA (GTX 1060 / RTX or newer) |
| **RAM** | 8 GB | 16 GB |
| **Disk** | 8 GB free | 20 GB+ |

**No NVIDIA card?** It still works. Splatinator detects your GPU and picks the CPU version of
COLMAP automatically — AMD, Intel and integrated graphics are all fine, just slower. The Brush
renderer itself runs on any modern GPU.

**Got an NVIDIA card?** You automatically get the CUDA build, which is dramatically faster.
Keep your graphics driver up to date.

---

## If something goes wrong

**"COLMAP produced no reconstruction"**
Your frames don't overlap enough. Re-shoot moving more slowly, keep the subject centred, and
raise the Extraction FPS.

**A download failed or you closed it mid-setup**
Reopen Splatinator and click **Reinstall COLMAP + Brush** in the Setup panel. Downloads pick
up where they left off.

**Brush won't open**
It needs working Vulkan/DirectX 12 drivers. Update your graphics driver and try again.

**Something else**
Click **Check / Install Prerequisites** in the app's Setup panel — it prints a full report of
what's installed and repairs anything missing. The status bar at the bottom always shows the
current state.

---

## Option 2: run from source

Prefer not to run a downloaded .exe, or on macOS/Linux?

```bash
git clone https://github.com/Abhigyan-Mohanty/Splatinator
cd Splatinator
```

**Windows** — double-click **`Splatinator.bat`**. It finds Python, or offers to install it for
you (per-user, no admin), creates a private virtual environment, downloads COLMAP and Brush,
and starts the app.

**macOS / Linux**

```bash
bash install_binaries.sh    # COLMAP via brew/apt, Brush from GitHub, packages into .venv
python3 bootstrap.py        # finish setup and launch
```

COLMAP only ships prebuilt binaries for Windows, so elsewhere it comes from your package
manager (`brew install colmap` / `sudo apt install colmap`) — Splatinator then finds it on
your `PATH`.

### Command line

| Command | What it does |
| --- | --- |
| `Splatinator.bat` | Set up anything missing, then launch |
| `Splatinator.bat --check` | Print a system report, install nothing |
| `Splatinator.bat --setup` | Install prerequisites without launching |
| `Splatinator.bat --repair` | Re-download COLMAP and Brush |
| `Splatinator.bat --colmap-variant nocuda` | Force the CPU build of COLMAP |

`Splatinator.exe --check` and `--setup` work the same way.

### Build the .exe yourself

```bash
python build_exe.py     # produces dist/Splatinator.exe
```

For a conventional Windows installer with Start Menu shortcuts, compile
`installer/Splatinator.iss` with [Inno Setup 6](https://jrsoftware.org/isdl.php) afterwards.

---

## How it works

```
video / photos
      ↓  frame extraction (OpenCV)
   images
      ↓  COLMAP: feature extraction → matching → mapping → undistortion
camera poses + sparse point cloud
      ↓
   Brush: trains and renders the Gaussian Splat
```

| File | Role |
| --- | --- |
| `Splatinator.bat` | Launcher — finds or installs Python, then hands off |
| `bootstrap.py` | First-run orchestration, then starts the app |
| `prereqs.py` | Detects and installs every prerequisite (standard library only) |
| `splatinator.py` | The app and the COLMAP pipeline |
| `build_exe.py` | Builds `dist/Splatinator.exe` |
| `gaussiansplat/`, `brush/` | Downloaded tools — never committed |

---

## Credits

- **[COLMAP](https://github.com/colmap/colmap)** — structure-from-motion and multi-view stereo
- **[Brush](https://github.com/ArthurBrussee/brush)** — real-time Gaussian splat renderer and trainer
- **Splatinator** — automated pipeline by [Abhigyan Mohanty](https://github.com/Abhigyan-Mohanty)

Issues and pull requests welcome.
