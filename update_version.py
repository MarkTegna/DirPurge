#!/usr/bin/env python3
"""
Manual version update script for DirPurge
Author: Mark Oldham

This script allows manual updates of MAJOR and MINOR version numbers.
"""

import re
import sys
from datetime import datetime
from pathlib import Path


def update_version(new_version):
    """Update version in version.py"""
    version_file = Path("version.py")
    
    if not version_file.exists():
        print("Error: version.py not found")
        return False
    
    # Validate version format
    if not re.match(r'^\d+\.\d+\.\d+$', new_version):
        print("Error: Version must be in format MAJOR.MINOR.PATCH (e.g., 1.2.3)")
        return False
    
    # Read current version file
    content = version_file.read_text()
    
    # Find current version
    version_pattern = r'__version__ = "(\d+)\.(\d+)\.(\d+)"'
    match = re.search(version_pattern, content)
    
    if not match:
        print("Error: Could not find version string in version.py")
        return False
    
    old_version = f"{match.group(1)}.{match.group(2)}.{match.group(3)}"
    print(f"Updating version from {old_version} to {new_version}")
    
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


def main():
    """Main function"""
    if len(sys.argv) != 2:
        print("Usage: python update_version.py <version>")
        print("Example: python update_version.py 1.2.0")
        return 1
    
    new_version = sys.argv[1]
    success = update_version(new_version)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())