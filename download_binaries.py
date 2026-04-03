import os
import sys
import zipfile
import tarfile
import requests
import argparse
import platform
import shutil
from tqdm import tqdm

# Constants
REPOS = {
    "brush": "ArthurBrussee/brush",
    "colmap": "colmap/colmap"
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_latest_release_assets(repo_name):
    """Fetch the latest release's assets for a given GitHub repo."""
    url = f"https://api.github.com/repos/{repo_name}/releases/latest"
    print(f"Fetching latest release info for {repo_name}...")
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data.get("assets", []), data.get("tag_name", "unknown")
    except Exception as e:
        print(f"Error fetching release for {repo_name}: {e}")
        return [], None

def download_file(url, target_path):
    """Download a file with a progress bar."""
    print(f"Downloading from {url}...")
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        total_size = int(response.headers.get('content-length', 0))
        
        with open(target_path, 'wb') as file, tqdm(
            desc="Downloading",
            total=total_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for data in response.iter_content(chunk_size=4096):
                size = file.write(data)
                bar.update(size)
        return True
    except Exception as e:
        print(f"Failed to download: {e}")
        return False

def extract_file(file_path, target_dir):
    """Extract .zip, .tar.gz, or .tar.xz files."""
    print(f"Extracting {os.path.basename(file_path)} to {target_dir}...")
    os.makedirs(target_dir, exist_ok=True)
    
    try:
        if file_path.endswith(".zip"):
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(target_dir)
        elif file_path.endswith((".tar.gz", ".tgz")):
            with tarfile.open(file_path, "r:gz") as tar_ref:
                tar_ref.extractall(target_dir)
        elif file_path.endswith((".tar.xz", ".xz")):
            with tarfile.open(file_path, "r:xz") as tar_ref:
                tar_ref.extractall(target_dir)
        else:
            print(f"Unsupported archive format: {file_path}")
            return False
        return True
    except Exception as e:
        print(f"Extraction failed: {e}")
        return False

def setup_binaries(target_os, target_arch, colmap_variant="cuda"):
    """Download and setup binaries based on the target OS and arch."""
    
    # 1. Brush Setup
    brush_assets, brush_tag = get_latest_release_assets(REPOS["brush"])
    brush_asset = None
    
    # Matching pattern for Brush
    if target_os == "windows":
        pattern = "pc-windows-msvc.zip"
    elif target_os == "macos":
        pattern = "apple-darwin.tar.xz" # Assume arm64/aarch64 for newer macs
    else: # linux
        pattern = "unknown-linux-gnu.tar.xz"
        
    for asset in brush_assets:
        if pattern in asset["name"]:
            brush_asset = asset
            break
            
    if brush_asset:
        target_dir = os.path.join(BASE_DIR, "brush")
        temp_zip = os.path.join(BASE_DIR, brush_asset["name"])
        if download_file(brush_asset["browser_download_url"], temp_zip):
            if extract_file(temp_zip, target_dir):
                print(f"Brush {brush_tag} installed successfully.")
            os.remove(temp_zip)
    else:
        print(f"Could not find Brush asset for {target_os}.")

    print("-" * 30)

    # 2. COLMAP Setup
    if target_os == "windows":
        colmap_assets, colmap_tag = get_latest_release_assets(REPOS["colmap"])
        colmap_asset = None
        variant_pattern = f"windows-{colmap_variant}.zip"
        
        for asset in colmap_assets:
            if variant_pattern in asset["name"]:
                colmap_asset = asset
                break
                
        if colmap_asset:
            target_dir = os.path.join(BASE_DIR, "gaussiansplat")
            temp_zip = os.path.join(BASE_DIR, colmap_asset["name"])
            if download_file(colmap_asset["browser_download_url"], temp_zip):
                if extract_file(temp_zip, target_dir):
                    print(f"COLMAP {colmap_tag} installed successfully.")
                os.remove(temp_zip)
        else:
            print(f"Could not find COLMAP asset for {target_os} ({colmap_variant}).")
    else:
        print(f"NOTICE: Official COLMAP binaries for {target_os} are not available on GitHub.")
        if target_os == "macos":
            print("To install COLMAP on macOS, use: brew install colmap")
        elif target_os == "linux":
            print("To install COLMAP on Linux (Ubuntu/Debian), use: sudo apt install colmap")

def main():
    parser = argparse.ArgumentParser(description="Splatinator Binary Downloader")
    parser.add_argument("--os", choices=["windows", "macos", "linux"], default=None,
                        help="Target OS for binaries")
    parser.add_argument("--arch", choices=["x86_64", "arm64"], default=None,
                        help="Target architecture (default: auto)")
    parser.add_argument("--colmap_variant", choices=["cuda", "nocuda"], default="cuda",
                        help="COLMAP variant for Windows (default: cuda)")
    
    args = parser.parse_args()
    
    # Auto-detect if not provided
    target_os = args.os or platform.system().lower()
    if target_os == "darwin": target_os = "macos"
    
    target_arch = args.arch or platform.machine().lower()
    if target_arch in ["amd64", "x64", "x86_64"]: target_arch = "x86_64"
    if target_arch in ["aarch64", "arm64"]: target_arch = "arm64"

    print("=" * 50)
    print(f" TARGET PLATFORM: {target_os.upper()} ({target_arch})")
    print("=" * 50)
    
    setup_binaries(target_os, target_arch, args.colmap_variant)
    print("\nSetup complete!")

if __name__ == "__main__":
    main()
