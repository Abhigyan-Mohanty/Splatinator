#  Splatinator

**Splatinator** is a streamlined, utility-focused desktop application designed to automate the **Gaussian Splatting** pipeline. It handles everything from video frame extraction and COLMAP photogrammetry to real-time 3D visualization using the Brush engine.

Designed for simplicity and portability, Splatinator stays under the 25MB GitHub limit by dynamically downloading heavy binaries upon setup.

---

##  Key Features

- **Cross-Platform Support**: Works on Windows, macOS (Apple Silicon), and Linux.
- **Automated Pipeline**: 
  1. Extract frames from video or copy photos.
  2. Automatic COLMAP feature extraction, matching, and mapping.
  3. Image undistortion for Gaussian Splatting.
  4. Detached launch for the **Brush** rendering engine.
- **No-Bloat**: Only downloads the necessary tools for your specific OS.

---

##  Installation & Setup

### 1. Prerequisites
- **Python 3.9+** installed and added to your PATH.
- **NVIDIA GPU** (Recommended for Windows/Linux) for faster COLMAP processing.

### 2. Install Python Packages
Run the following script to install required libraries like OpenCV and Requests:
- **Windows**: Double-click `install_requirements.bat`
- **macOS / Linux**: `pip install -r requirements.txt`

### 3. Download Heavy Binaries
Because GitHub has a 25MB file limit, you must download the latest versions of **COLMAP** and **Brush** using our automated installer:
- **Windows**: Run `install_binaries.bat` and follow the prompts.
- **macOS / Linux**: Run `bash install_binaries.sh` in your terminal.

---

##  How to Use

1. **Launch Splatinator**:
   - **Windows**: Run `start_splatinator.bat`
   - **macOS / Linux**: `python3 splatinator.py`
2. **Setup Project**:
   - Enter a **Project Name**.
   - Select your **Output Directory**.
3. **Select Input**:
   - Choose **Video File** or **Multiple Photos**.
   - For video, set your desired **Extraction FPS** (higher FPS = more detail but slower processing).
4. **Start Processing**:
   - Click **Start Processing** and watch the logs. Splatinator will handle the multi-step COLMAP pipeline automatically.
5. **Visualize**:
   - Once complete, **Brush** will launch automatically, allowing you to view and refine your Gaussian Splat in real-time.

---

##  Technical Info

- **COLMAP**: Used for Structure-from-Motion (SfM).
- **Brush**: A high-performance Gaussian Splat renderer and editor.
- **Storage**: Heavy binaries are stored in `gaussiansplat/` and `brush/` (automatically excluded from GitHub via `.gitignore`).

---

##  Credits
- **COLMAP**: [github.com/colmap/colmap](https://github.com/colmap/colmap)
- **Brush**: [github.com/ArthurBrussee/brush](https://github.com/ArthurBrussee/brush)
- **Splatinator**: Automated pipeline by [User/Abhigyan Mohanty]

---

> [!TIP]
> If you encounter any issues with missing binaries, simply rerun `install_binaries.bat` or `install_binaries.sh` to ensure everything is correctly placed.
