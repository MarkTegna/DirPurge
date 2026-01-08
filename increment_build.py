#!/usr/bin/env python3
"""
Increment build version script for DirPurge
Author: Mark Oldham

This script automatically increments the PATCH version number before each build.
"""

import re
from datetime import datetime
from pathlib import Path


def increment_patch_version():
    """Increment the PATCH version in version.py"""
    version_file = Path("version.py")
    
    if not version_file.exists():
        print("Error: version.py not found")
        return False
    
    # Read current version file
    content = version_file.read_text()
    
    # Find version line
    version_pattern = r'__version__ = "(\d+)\.(\d+)\.(\d+)"'
    match = re.search(version_pattern, content)
    
    if not match:
        print("Error: Could not find version string in version.py")
        return False
    
    major, minor, patch = match.groups()
    new_patch = int(patch) + 1
    new_version = f"{major}.{minor}.{new_patch}"
    
    print(f"Incrementing version from {major}.{minor}.{patch} to {new_version}")
    
    # Update version string
    new_content = re.sub(
        version_pattern,
        f'__version__ = "{new_version}"',
        content
    )
    
    # Update compile date
    compile_date = datetime.now().strftime("%Y-%m-%d")
    new_content = re.sub(
        r'__compile_date__ = "[^"]*"',
        f'__compile_date__ = "{compile_date}"',
        new_content
    )
    
    # Write updated content
    version_file.write_text(new_content)
    
    print(f"Version updated to {new_version}")
    print(f"Compile date updated to {compile_date}")
    
    return True


if __name__ == "__main__":
    success = increment_patch_version()
    exit(0 if success else 1)