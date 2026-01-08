#!/usr/bin/env python3
"""
Build script for DirPurge Windows executable
Author: Mark Oldham

This script builds a Windows executable using PyInstaller and creates a distribution ZIP.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
import zipfile


def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n{description}...")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error: {description} failed")
        print(f"Command: {command}")
        print(f"Error output: {result.stderr}")
        return False
    
    if result.stdout:
        print(result.stdout)
    
    return True


def get_current_version():
    """Get current version from version.py"""
    try:
        import version
        return version.__version__
    except ImportError:
        print("Error: Could not import version.py")
        return None


def build_executable():
    """Build Windows executable using PyInstaller"""
    print("Building DirPurge Windows executable...")
    
    # Increment build version
    if not run_command("python increment_build.py", "Incrementing build version"):
        return False
    
    # Get updated version
    current_version = get_current_version()
    if not current_version:
        return False
    
    print(f"Building version {current_version}")
    
    # Create dist directory
    dist_dir = Path("dist")
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir()
    
    # PyInstaller command
    pyinstaller_cmd = [
        "python", "-m", "PyInstaller",
        "--onefile",
        "--name=dirpurge",
        "--distpath=dist",
        "--workpath=build",
        "--specpath=build",
        "dirpurge.py"
    ]
    
    if not run_command(" ".join(pyinstaller_cmd), "Building executable with PyInstaller"):
        return False
    
    # Verify executable was created
    exe_path = dist_dir / "dirpurge.exe"
    if not exe_path.exists():
        print("Error: Executable was not created")
        return False
    
    print(f"Executable created: {exe_path}")
    
    # Copy additional files to dist
    files_to_copy = [
        "dirpurge.ini",
        "README.md" if Path("README.md").exists() else None,
        "LICENSE" if Path("LICENSE").exists() else None
    ]
    
    for file_name in files_to_copy:
        if file_name and Path(file_name).exists():
            shutil.copy2(file_name, dist_dir)
            print(f"Copied {file_name} to dist/")
    
    # Create version-specific ZIP distribution
    zip_name = f"dirpurge_v{current_version}.zip"
    zip_path = Path(zip_name)
    
    print(f"\nCreating distribution ZIP: {zip_name}")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in dist_dir.rglob('*'):
            if file_path.is_file():
                arcname = file_path.relative_to(dist_dir)
                zipf.write(file_path, arcname)
                print(f"Added to ZIP: {arcname}")
    
    print(f"\nBuild completed successfully!")
    print(f"Executable: {exe_path}")
    print(f"Distribution ZIP: {zip_path}")
    print(f"Version: {current_version}")
    
    return True


def main():
    """Main function"""
    try:
        success = build_executable()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\nBuild cancelled by user")
        return 130
    except Exception as e:
        print(f"Unexpected error during build: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())