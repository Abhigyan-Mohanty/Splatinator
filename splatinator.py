import os
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import cv2
import platform

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_binary_paths():
    """Determine paths for colmap and brush based on OS."""
    system = platform.system().lower()
    
    # Defaults (Windows)
    colmap_path = os.path.join(BASE_DIR, "gaussiansplat", "colmap-x64-windows-cuda", "bin", "colmap.exe")
    brush_path = os.path.join(BASE_DIR, "brush", "brush.exe")
    
    if system == "darwin": # macOS
        # Try local first, then system path
        local_brush = os.path.join(BASE_DIR, "brush", "brush")
        brush_path = local_brush if os.path.exists(local_brush) else (shutil.which("brush") or "brush")
        colmap_path = shutil.which("colmap") or "/usr/local/bin/colmap"
        
    elif system == "linux":
        local_brush = os.path.join(BASE_DIR, "brush", "brush")
        brush_path = local_brush if os.path.exists(local_brush) else (shutil.which("brush") or "brush")
        colmap_path = shutil.which("colmap") or "/usr/bin/colmap"
        
    return colmap_path, brush_path

COLMAP_PATH, BRUSH_PATH = get_binary_paths()

class SplatinatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Splatinator - Gaussian Splat Utility")
        self.root.geometry("900x600")
        
        # Variables
        self.input_type = tk.StringVar(value="Video")
        self.project_name = tk.StringVar()
        self.base_dir = tk.StringVar(value=os.path.join(BASE_DIR, "outputs"))
        self.input_files = [] # list of paths (either 1 video or multiple images)
        self.fps = tk.IntVar(value=2)
        
        self.setup_ui()
        
    def setup_ui(self):
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        left_frame = ttk.Frame(main_paned, width=300)
        right_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=1)
        main_paned.add(right_frame, weight=3)
        
        # --- Left Frame (Controls) ---
        ttk.Label(left_frame, text="Project Details", font=("TkDefaultFont", 12, "bold")).pack(anchor=tk.W, pady=(0, 10))
        
        ttk.Label(left_frame, text="Project Name:").pack(anchor=tk.W)
        ttk.Entry(left_frame, textvariable=self.project_name, width=30).pack(anchor=tk.W, pady=(0, 10))
        
        ttk.Label(left_frame, text="Output Directory:").pack(anchor=tk.W)
        dir_frame = ttk.Frame(left_frame)
        dir_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Entry(dir_frame, textvariable=self.base_dir).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(dir_frame, text="Browse", command=self.browse_base_dir, width=8).pack(side=tk.LEFT, padx=(5,0))
        
        ttk.Separator(left_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        ttk.Label(left_frame, text="Input Selection", font=("TkDefaultFont", 12, "bold")).pack(anchor=tk.W, pady=(0, 10))
        
        type_frame = ttk.Frame(left_frame)
        type_frame.pack(anchor=tk.W, pady=(0, 10))
        ttk.Radiobutton(type_frame, text="Video File", variable=self.input_type, value="Video", command=self.on_type_change).pack(side=tk.LEFT)
        ttk.Radiobutton(type_frame, text="Multiple Photos", variable=self.input_type, value="Photos", command=self.on_type_change).pack(side=tk.LEFT, padx=(10, 0))
        
        self.file_label = ttk.Label(left_frame, text="No file(s) selected", foreground="gray")
        self.file_label.pack(anchor=tk.W)
        ttk.Button(left_frame, text="Select Files...", command=self.select_files).pack(anchor=tk.W, pady=(5, 10))
        
        self.fps_label = ttk.Label(left_frame, text="Extraction FPS:")
        self.fps_label.pack(anchor=tk.W)
        self.fps_spinbox = ttk.Spinbox(left_frame, from_=1, to_=60, textvariable=self.fps, width=10)
        self.fps_spinbox.pack(anchor=tk.W, pady=(0, 10))
        
        ttk.Separator(left_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=20)
        
        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        self.start_btn = ttk.Button(btn_frame, text="Start Processing", command=self.start_processing)
        self.start_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        self.brush_btn = ttk.Button(btn_frame, text="Launch Brush", command=self.launch_brush)
        self.brush_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # --- Right Frame (Logs) ---
        ttk.Label(right_frame, text="Console Log", font=("TkDefaultFont", 12, "bold")).pack(anchor=tk.W, pady=(0, 10))
        self.log_text = scrolledtext.ScrolledText(right_frame, state='disabled', bg="black", fg="lightgray", font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def log(self, message):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        self.root.update_idletasks()
        
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
            f = filedialog.askopenfilename(title="Select Video", filetypes=[("Video Files", "*.mp4 *.avi *.mkv *.mov")])
            if f:
                self.input_files = [f]
                self.file_label.config(text=os.path.basename(f))
        else:
            fs = filedialog.askopenfilenames(title="Select Photos", filetypes=[("Image Files", "*.jpg *.jpeg *.png")])
            if fs:
                self.input_files = list(fs)
                self.file_label.config(text=f"{len(self.input_files)} photos selected")
                
    def start_processing(self):
        if not self.project_name.get():
            messagebox.showerror("Error", "Please enter a project name.")
            return
        if not self.input_files:
            messagebox.showerror("Error", "Please select input file(s).")
            return
            
        self.start_btn.config(state="disabled")
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')
        
        thread = threading.Thread(target=self.run_pipeline, daemon=True)
        thread.start()
        
    def launch_brush(self):
        if not self.project_name.get():
            messagebox.showerror("Error", "Please enter a project name.")
            return
        proj_dir = os.path.join(self.base_dir.get().strip(), self.project_name.get().strip())
        if not os.path.exists(proj_dir):
            messagebox.showerror("Error", f"Project directory does not exist: {proj_dir}")
            return
        brush_cmd = [BRUSH_PATH, proj_dir, "--with-viewer"]
        # Use shell=True for non-windows to handle path resolution better if needed
        creation_flags = subprocess.CREATE_NEW_CONSOLE if platform.system() == "Windows" else 0
        subprocess.Popen(brush_cmd, creationflags=creation_flags)
        self.log(f"\nLaunched Brush for {proj_dir}")
        
    def run_cmd(self, args, cwd=None):
        self.log(f"> {' '.join(args)}")
        # On some platforms, creationflags don't exist or differ
        creation_flags = subprocess.CREATE_NEW_CONSOLE if platform.system() == "Windows" else 0
        process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=cwd, creationflags=creation_flags)
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                self.log(line.rstrip())
        return process.returncode
        
    def run_pipeline(self):
        try:
            proj_name = self.project_name.get().strip()
            base = self.base_dir.get().strip()
            proj_dir = os.path.join(base, proj_name)
            
            # --- 1. Setup Dirs ---
            self.log(f"--- Setting up project directories in {proj_dir} ---")
            dirs_to_make = [
                proj_dir,
                os.path.join(proj_dir, "input"),
                os.path.join(proj_dir, "distorted"),
                os.path.join(proj_dir, "distorted", "sparse"),
                os.path.join(proj_dir, "sparse"),
                os.path.join(proj_dir, "sparse", "0"),
            ]
            for d in dirs_to_make:
                os.makedirs(d, exist_ok=True)
                
            input_dir = os.path.join(proj_dir, "input")
            
            # --- 2. Extract or Copy ---
            if self.input_type.get() == "Video":
                video_file = self.input_files[0]
                target_fps = self.fps.get()
                self.log(f"--- Extracting frames from video at {target_fps} FPS ---")
                cap = cv2.VideoCapture(video_file)
                video_fps = cap.get(cv2.CAP_PROP_FPS)
                if video_fps <= 0: video_fps = 30 # fallback
                
                frame_interval = max(1, int(video_fps / target_fps))
                
                count = 0
                saved = 0
                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret: break
                    if count % frame_interval == 0:
                        out_path = os.path.join(input_dir, f"{saved:05d}.jpg")
                        cv2.imwrite(out_path, frame)
                        saved += 1
                        if saved % 50 == 0:
                            self.log(f"Extracted {saved} frames...")
                    count += 1
                cap.release()
                self.log(f"Done extracting. Total {saved} frames.")
            else:
                self.log("--- Copying input photos ---")
                for i, img_path in enumerate(self.input_files):
                    ext = os.path.splitext(img_path)[1]
                    dest = os.path.join(input_dir, f"{i:05d}{ext}")
                    shutil.copy(img_path, dest)
                self.log(f"Copied {len(self.input_files)} photos.")

            db_path = os.path.join(proj_dir, "distorted", "database.db")
            
            # --- 3. Feature Extractor ---
            self.log("\n--- STEP 1: Feature Extraction ---")
            ret = self.run_cmd([COLMAP_PATH, "feature_extractor", 
                                "--image_path", input_dir, 
                                "--database_path", db_path,
                                "--ImageReader.single_camera", "1",
                                "--ImageReader.camera_model", "PINHOLE"])
            if ret != 0: raise Exception("Feature extraction failed.")
            
            # --- 4. Matcher ---
            self.log("\n--- STEP 2: Feature Matching ---")
            matcher = "sequential_matcher" if self.input_type.get() == "Video" else "exhaustive_matcher"
            ret = self.run_cmd([COLMAP_PATH, matcher, 
                                "--database_path", db_path])
            if ret != 0: raise Exception("Feature matching failed.")
            
            # --- 5. Mapper ---
            self.log("\n--- STEP 3: Mapper ---")
            ret = self.run_cmd([COLMAP_PATH, "mapper", 
                                "--database_path", db_path,
                                "--image_path", input_dir,
                                "--output_path", os.path.join(proj_dir, "distorted", "sparse")])
            if ret != 0: raise Exception("Mapper failed.")
            
            # --- 6. Undistortion ---
            self.log("\n--- STEP 4: Undistortion ---")
            ret = self.run_cmd([COLMAP_PATH, "image_undistorter", 
                                "--image_path", input_dir,
                                "--input_path", os.path.join(proj_dir, "distorted", "sparse", "0"),
                                "--output_path", proj_dir,
                                "--output_type", "COLMAP"])
            if ret != 0: raise Exception("Image undistorter failed.")
            
            # --- 7. Organize Output ---
            self.log("\n--- STEP 5: Organizing Output ---")
            for bf in ["cameras.bin", "images.bin", "points3D.bin"]:
                src = os.path.join(proj_dir, "sparse", bf)
                dst = os.path.join(proj_dir, "sparse", "0", bf)
                if os.path.exists(src):
                    shutil.move(src, dst)
                    self.log(f"Moved {bf}")
                    
            # --- 8. Brush ---
            self.log("\n--- STEP 6: Launching Brush ---")
            
            brush_cmd = [BRUSH_PATH, proj_dir, "--with-viewer"]
            self.log(f"Starting Brush in detached mode: {' '.join(brush_cmd)}")
            creation_flags = subprocess.CREATE_NEW_CONSOLE if platform.system() == "Windows" else 0
            subprocess.Popen(brush_cmd, creationflags=creation_flags)
            
            self.log("\n!!! Pipeline Complete !!!")
            
        except Exception as e:
            self.log(f"\nERROR: {str(e)}")
        finally:
            self.start_btn.config(state="normal")

if __name__ == "__main__":
    root = tk.Tk()
    app = SplatinatorApp(root)
    
    missing_files = []
    if not os.path.exists(COLMAP_PATH):
        print(f"ERROR: colmap not found at {COLMAP_PATH}")
        missing_files.append("COLMAP")
    if not os.path.exists(BRUSH_PATH):
        print(f"ERROR: brush not found at {BRUSH_PATH}")
        missing_files.append("Brush")
        
    if missing_files:
        msg = f"The following heavy binaries are missing: {', '.join(missing_files)}.\n\n"
        msg += "Please run 'download_binaries.py' to download and extract them before starting."
        messagebox.showwarning("Missing Binaries", msg)

    root.mainloop()
