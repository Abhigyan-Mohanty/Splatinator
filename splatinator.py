"""Splatinator - a one-window front end for the Gaussian Splatting pipeline.

Video or photos -> COLMAP structure-from-motion -> Brush viewer/trainer.
Prerequisite discovery and installation live in prereqs.py so the same logic
serves the launcher, the frozen .exe and this GUI.
"""

import os
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prereqs

BASE_DIR = prereqs.BASE_DIR
IS_WINDOWS = prereqs.IS_WINDOWS

CREATE_NO_WINDOW = 0x08000000
DETACHED_PROCESS = 0x00000008


class SplatinatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Splatinator - Gaussian Splat Utility")
        self.root.geometry("980x660")
        self.root.minsize(820, 560)

        self.input_type = tk.StringVar(value="Video")
        self.project_name = tk.StringVar()
        self.base_dir = tk.StringVar(value=os.path.join(BASE_DIR, "outputs"))
        self.input_files = []
        self.fps = tk.IntVar(value=2)
        self.status_text = tk.StringVar(value="Checking prerequisites...")

        self.colmap_path = None
        self.brush_path = None
        self.current_proc = None
        self.cancelled = False
        self.busy = False

        self.setup_ui()
        self.root.after(200, lambda: self.run_in_thread(self.refresh_status, quiet=False))

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def setup_ui(self):
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 0))

        left_frame = ttk.Frame(main_paned, width=320)
        right_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=1)
        main_paned.add(right_frame, weight=3)

        ttk.Label(left_frame, text="Project Details",
                  font=("TkDefaultFont", 12, "bold")).pack(anchor=tk.W, pady=(0, 10))

        ttk.Label(left_frame, text="Project Name:").pack(anchor=tk.W)
        ttk.Entry(left_frame, textvariable=self.project_name, width=30).pack(
            anchor=tk.W, fill=tk.X, pady=(0, 10))

        ttk.Label(left_frame, text="Output Directory:").pack(anchor=tk.W)
        dir_frame = ttk.Frame(left_frame)
        dir_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Entry(dir_frame, textvariable=self.base_dir).pack(
            side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(dir_frame, text="Browse", command=self.browse_base_dir, width=8).pack(
            side=tk.LEFT, padx=(5, 0))

        ttk.Separator(left_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        ttk.Label(left_frame, text="Input Selection",
                  font=("TkDefaultFont", 12, "bold")).pack(anchor=tk.W, pady=(0, 10))

        type_frame = ttk.Frame(left_frame)
        type_frame.pack(anchor=tk.W, pady=(0, 10))
        ttk.Radiobutton(type_frame, text="Video File", variable=self.input_type,
                        value="Video", command=self.on_type_change).pack(side=tk.LEFT)
        ttk.Radiobutton(type_frame, text="Multiple Photos", variable=self.input_type,
                        value="Photos", command=self.on_type_change).pack(
                            side=tk.LEFT, padx=(10, 0))

        self.file_label = ttk.Label(left_frame, text="No file(s) selected", foreground="gray")
        self.file_label.pack(anchor=tk.W)
        ttk.Button(left_frame, text="Select Files...", command=self.select_files).pack(
            anchor=tk.W, pady=(5, 10))

        self.fps_label = ttk.Label(left_frame, text="Extraction FPS:")
        self.fps_label.pack(anchor=tk.W)
        self.fps_spinbox = ttk.Spinbox(left_frame, from_=1, to=60,
                                       textvariable=self.fps, width=10)
        self.fps_spinbox.pack(anchor=tk.W, pady=(0, 10))

        ttk.Separator(left_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=15)

        self.start_btn = ttk.Button(left_frame, text="Start Processing",
                                    command=self.start_processing)
        self.start_btn.pack(fill=tk.X, pady=(0, 5))

        self.cancel_btn = ttk.Button(left_frame, text="Stop", command=self.cancel_processing,
                                     state="disabled")
        self.cancel_btn.pack(fill=tk.X, pady=(0, 5))

        self.brush_btn = ttk.Button(left_frame, text="Launch Brush Viewer",
                                    command=self.launch_brush)
        self.brush_btn.pack(fill=tk.X, pady=(0, 5))

        ttk.Separator(left_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=15)

        ttk.Label(left_frame, text="Setup", font=("TkDefaultFont", 12, "bold")).pack(
            anchor=tk.W, pady=(0, 5))
        self.setup_btn = ttk.Button(left_frame, text="Check / Install Prerequisites",
                                    command=lambda: self.run_in_thread(self.do_setup))
        self.setup_btn.pack(fill=tk.X, pady=(0, 5))
        self.repair_btn = ttk.Button(left_frame, text="Reinstall COLMAP + Brush",
                                     command=self.confirm_repair)
        self.repair_btn.pack(fill=tk.X)

        # --- Right: log ---
        header = ttk.Frame(right_frame)
        header.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(header, text="Console Log",
                  font=("TkDefaultFont", 12, "bold")).pack(side=tk.LEFT)
        ttk.Button(header, text="Clear", width=8, command=self.clear_log).pack(side=tk.RIGHT)

        self.log_text = scrolledtext.ScrolledText(
            right_frame, state='disabled', bg="black", fg="lightgray",
            font=("Consolas", 9), wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # --- Bottom: status bar ---
        status_bar = ttk.Frame(self.root)
        status_bar.pack(fill=tk.X, padx=10, pady=6)
        self.progress = ttk.Progressbar(status_bar, mode="indeterminate", length=140)
        self.progress.pack(side=tk.RIGHT)
        ttk.Label(status_bar, textvariable=self.status_text).pack(side=tk.LEFT)

    def clear_log(self):
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')

    def log(self, message):
        """Thread-safe logging to the UI."""
        try:
            self.root.after(0, self._log_internal, message)
        except tk.TclError:
            pass  # window closed mid-run

    def _log_internal(self, message):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

    def set_status(self, text):
        self.root.after(0, self.status_text.set, text)

    def set_busy(self, busy):
        self.busy = busy

        def apply():
            state = "disabled" if busy else "normal"
            for btn in (self.start_btn, self.setup_btn, self.repair_btn, self.brush_btn):
                btn.config(state=state)
            self.cancel_btn.config(state="normal" if busy else "disabled")
            if busy:
                self.progress.start(12)
            else:
                self.progress.stop()

        self.root.after(0, apply)

    def run_in_thread(self, fn, *args, **kwargs):
        if self.busy:
            return
        threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True).start()

    # ------------------------------------------------------------------
    # Prerequisites
    # ------------------------------------------------------------------
    def refresh_status(self, quiet=True):
        self.colmap_path = prereqs.find_colmap()
        self.brush_path = prereqs.find_brush()
        st = prereqs.status()
        missing = prereqs.missing_from(st)

        if missing:
            self.set_status("Missing: %s  -  click 'Check / Install Prerequisites'"
                            % ", ".join(missing))
        else:
            self.set_status("Ready  |  COLMAP: %s  |  GPU: %s"
                            % ("CUDA" if st["colmap_cuda"] else "CPU", st["gpu_desc"]))

        if not quiet:
            prereqs.print_report(self.log, st)
            if missing:
                self.log("")
                self.log("Some prerequisites are missing: %s" % ", ".join(missing))
                self.log("Click 'Check / Install Prerequisites' to download them "
                         "automatically.")
        return st

    def do_setup(self, force=False):
        self.set_busy(True)
        self.set_status("Installing prerequisites - this may take several minutes...")
        self.log("")
        try:
            ok = prereqs.ensure_all(self.log, force=force)
            self.refresh_status()
            if ok:
                self.root.after(0, lambda: messagebox.showinfo(
                    "Setup complete", "Splatinator is ready to use."))
            else:
                self.root.after(0, lambda: messagebox.showwarning(
                    "Setup incomplete",
                    "Some components could not be installed. See the log for details."))
        except Exception as exc:
            self.log("Setup error: %s" % exc)
        finally:
            self.set_busy(False)

    def confirm_repair(self):
        if messagebox.askyesno(
                "Reinstall binaries",
                "This re-downloads COLMAP and Brush (roughly 0.5-1.5 GB).\n\nContinue?"):
            self.run_in_thread(self.do_setup, force=True)

    # ------------------------------------------------------------------
    # Input selection
    # ------------------------------------------------------------------
    def browse_base_dir(self):
        d = filedialog.askdirectory(initialdir=self.base_dir.get())
        if d:
            self.base_dir.set(d)

    def on_type_change(self):
        self.input_files = []
        self.file_label.config(text="No file(s) selected")
        if self.input_type.get() == "Video":
            self.fps_spinbox.state(["!disabled"])
        else:
            self.fps_spinbox.state(["disabled"])

    def select_files(self):
        if self.input_type.get() == "Video":
            f = filedialog.askopenfilename(
                title="Select Video",
                filetypes=[("Video Files", "*.mp4 *.avi *.mkv *.mov"), ("All files", "*.*")])
            if f:
                self.input_files = [f]
                self.file_label.config(text=os.path.basename(f))
        else:
            fs = filedialog.askopenfilenames(
                title="Select Photos",
                filetypes=[("Image Files", "*.jpg *.jpeg *.png"), ("All files", "*.*")])
            if fs:
                self.input_files = list(fs)
                self.file_label.config(text="%d photos selected" % len(self.input_files))

    # ------------------------------------------------------------------
    # Processing
    # ------------------------------------------------------------------
    def start_processing(self):
        if not self.project_name.get().strip():
            messagebox.showerror("Error", "Please enter a project name.")
            return
        if not self.input_files:
            messagebox.showerror("Error", "Please select input file(s).")
            return

        self.colmap_path = prereqs.find_colmap()
        self.brush_path = prereqs.find_brush()
        if not self.colmap_path:
            if messagebox.askyesno(
                    "COLMAP missing",
                    "COLMAP is not installed yet. Download and install it now?"):
                self.run_in_thread(self.do_setup)
            return

        self.cancelled = False
        self.clear_log()
        self.run_in_thread(self.run_pipeline)

    def cancel_processing(self):
        self.cancelled = True
        self.log("\nStopping after the current step...")
        proc = self.current_proc
        if proc and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass

    def launch_brush(self, proj_dir=None):
        """Start the Brush viewer, detached from this app."""
        self.brush_path = prereqs.find_brush()
        if not self.brush_path:
            if messagebox.askyesno(
                    "Brush missing",
                    "The Brush viewer is not installed yet. Download it now?"):
                self.run_in_thread(self.do_setup)
            return

        if proj_dir is None:
            if not self.project_name.get().strip():
                messagebox.showerror("Error", "Please enter a project name.")
                return
            proj_dir = os.path.abspath(os.path.join(
                self.base_dir.get().strip(), self.project_name.get().strip()))
        if not os.path.isdir(proj_dir):
            messagebox.showerror("Error", "Project directory does not exist:\n%s" % proj_dir)
            return

        try:
            brush_exec = os.path.abspath(self.brush_path)
            cmd = [brush_exec, proj_dir, "--with-viewer"]
            flags = DETACHED_PROCESS if IS_WINDOWS else 0
            subprocess.Popen(cmd, cwd=os.path.dirname(brush_exec), creationflags=flags)
            self.log("\nLaunched Brush for %s" % proj_dir)
        except Exception as exc:
            self.log("Failed to launch Brush: %s" % exc)
            messagebox.showerror("Brush failed to start", str(exc))

    def run_cmd(self, args, cwd=None):
        """Run a child process, streaming its output into the log."""
        self.log("> %s" % " ".join(args))
        env = prereqs.colmap_env(args[0]) if os.path.basename(
            args[0]).lower().startswith("colmap") else os.environ.copy()
        flags = CREATE_NO_WINDOW if IS_WINDOWS else 0
        self.current_proc = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            errors="replace", bufsize=1, cwd=cwd, env=env, creationflags=flags)
        try:
            for line in self.current_proc.stdout:
                self.log(line.rstrip())
                if self.cancelled:
                    break
            self.current_proc.wait()
            return self.current_proc.returncode
        finally:
            proc, self.current_proc = self.current_proc, None
            if proc.poll() is None:
                proc.terminate()

    def _check_cancel(self):
        if self.cancelled:
            raise RuntimeError("Cancelled by user.")

    def extract_frames(self, video_file, input_dir):
        import cv2  # imported late so the GUI still opens without OpenCV

        target_fps = max(1, self.fps.get())
        self.log("--- Extracting frames at %d FPS ---" % target_fps)
        cap = cv2.VideoCapture(video_file)
        if not cap.isOpened():
            raise RuntimeError("Could not open video: %s" % video_file)

        video_fps = cap.get(cv2.CAP_PROP_FPS)
        if not video_fps or video_fps <= 0:
            video_fps = 30.0
        frame_interval = max(1, int(round(video_fps / target_fps)))

        count = saved = 0
        while cap.isOpened() and not self.cancelled:
            ret, frame = cap.read()
            if not ret:
                break
            if count % frame_interval == 0:
                cv2.imwrite(os.path.join(input_dir, "%05d.jpg" % saved), frame)
                saved += 1
                if saved % 50 == 0:
                    self.log("Extracted %d frames..." % saved)
            count += 1
        cap.release()
        self._check_cancel()

        if saved == 0:
            raise RuntimeError("No frames were extracted - is the video readable?")
        if saved < 20:
            self.log("WARNING: only %d frames. Gaussian splatting usually needs 50+ "
                     "views; try a higher extraction FPS." % saved)
        self.log("Done extracting. Total %d frames." % saved)
        return saved

    def run_pipeline(self):
        self.set_busy(True)
        try:
            colmap = self.colmap_path
            proj_name = self.project_name.get().strip()
            proj_dir = os.path.abspath(os.path.join(
                self.base_dir.get().strip(), proj_name))

            self.set_status("Processing '%s'..." % proj_name)
            self.log("--- Setting up project directories in %s ---" % proj_dir)
            input_dir = os.path.join(proj_dir, "input")
            distorted = os.path.join(proj_dir, "distorted")
            for d in (proj_dir, input_dir, distorted,
                      os.path.join(distorted, "sparse"),
                      os.path.join(proj_dir, "sparse"),
                      os.path.join(proj_dir, "sparse", "0")):
                os.makedirs(d, exist_ok=True)

            # --- 1. Frames or photos -------------------------------------
            if self.input_type.get() == "Video":
                self.extract_frames(self.input_files[0], input_dir)
            else:
                self.log("--- Copying input photos ---")
                for i, img_path in enumerate(self.input_files):
                    ext = os.path.splitext(img_path)[1]
                    shutil.copy(img_path, os.path.join(input_dir, "%05d%s" % (i, ext)))
                self.log("Copied %d photos." % len(self.input_files))
                if len(self.input_files) < 20:
                    self.log("WARNING: fewer than 20 photos - reconstruction may fail.")
            self._check_cancel()

            db_path = os.path.join(distorted, "database.db")

            # --- 2. Feature extraction -----------------------------------
            self.set_status("Step 1/5: feature extraction")
            self.log("\n--- STEP 1: Feature Extraction ---")
            if self.run_cmd([colmap, "feature_extractor",
                             "--image_path", input_dir,
                             "--database_path", db_path,
                             "--ImageReader.single_camera", "1",
                             "--ImageReader.camera_model", "PINHOLE"]) != 0:
                raise RuntimeError("Feature extraction failed.")
            self._check_cancel()

            # --- 3. Matching ---------------------------------------------
            self.set_status("Step 2/5: feature matching")
            self.log("\n--- STEP 2: Feature Matching ---")
            matcher = ("sequential_matcher" if self.input_type.get() == "Video"
                       else "exhaustive_matcher")
            if self.run_cmd([colmap, matcher, "--database_path", db_path]) != 0:
                raise RuntimeError("Feature matching failed.")
            self._check_cancel()

            # --- 4. Mapping ----------------------------------------------
            self.set_status("Step 3/5: sparse reconstruction (slowest step)")
            self.log("\n--- STEP 3: Mapper ---")
            if self.run_cmd([colmap, "mapper",
                             "--database_path", db_path,
                             "--image_path", input_dir,
                             "--output_path", os.path.join(distorted, "sparse")]) != 0:
                raise RuntimeError("Mapper failed.")
            self._check_cancel()

            model_dir = os.path.join(distorted, "sparse", "0")
            if not os.path.isdir(model_dir):
                raise RuntimeError(
                    "COLMAP produced no reconstruction. This usually means the images "
                    "do not overlap enough - try more frames or slower camera motion.")

            # --- 5. Undistortion -----------------------------------------
            self.set_status("Step 4/5: undistortion")
            self.log("\n--- STEP 4: Undistortion ---")
            if self.run_cmd([colmap, "image_undistorter",
                             "--image_path", input_dir,
                             "--input_path", model_dir,
                             "--output_path", proj_dir,
                             "--output_type", "COLMAP"]) != 0:
                raise RuntimeError("Image undistorter failed.")
            self._check_cancel()

            # --- 6. Layout Brush expects ---------------------------------
            self.set_status("Step 5/5: organizing output")
            self.log("\n--- STEP 5: Organizing Output ---")
            for bf in ("cameras.bin", "images.bin", "points3D.bin"):
                src = os.path.join(proj_dir, "sparse", bf)
                dst = os.path.join(proj_dir, "sparse", "0", bf)
                if os.path.exists(src):
                    shutil.move(src, dst)
                    self.log("Moved %s" % bf)

            # --- 7. Brush -------------------------------------------------
            self.log("\n--- STEP 6: Launching Brush ---")
            if prereqs.find_brush():
                self.root.after(0, self.launch_brush, proj_dir)
            else:
                self.log("Brush is not installed - run 'Check / Install Prerequisites' "
                         "to add it, then use 'Launch Brush Viewer'.")

            self.log("\n!!! Pipeline Complete !!!")
            self.set_status("Done - project at %s" % proj_dir)

        except Exception as exc:
            self.log("\nERROR: %s" % exc)
            self.set_status("Failed: %s" % exc)
        finally:
            self.cancelled = False
            self.set_busy(False)


def main():
    root = tk.Tk()
    SplatinatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
