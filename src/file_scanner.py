"""File scanning and grouping functionality for DirPurge"""

import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from .models import FileInfo


class FileScanner:
    """Efficiently scans directories and groups files by prefix"""
    
    def __init__(self, excluded_extensions: List[str] = None):
        """Initialize scanner with optional extension exclusions"""
        self.excluded_extensions = excluded_extensions or ['.PL', '.TXT', '.CSV', '.ZIP']
        # Normalize extensions to uppercase for case-insensitive matching
        self.excluded_extensions = [ext.upper() for ext in self.excluded_extensions]
    
    def scan_directory(self, directory_path: str) -> Dict[str, List[FileInfo]]:
        """Scan directory and return files grouped by prefix"""
        if not Path(directory_path).exists():
            raise ValueError(f"Directory does not exist: {directory_path}")
        
        if not Path(directory_path).is_dir():
            raise ValueError(f"Path is not a directory: {directory_path}")
        
        # Scan files and extract information
        files = self._extract_file_info(directory_path)
        
        # Filter by extensions
        filtered_files = self._filter_by_extensions(files)
        
        # Group by prefix
        return self._group_files_by_prefix(filtered_files)
    
    def _extract_file_info(self, directory_path: str) -> List[FileInfo]:
        """Extract file information using os.scandir for efficiency"""
        files = []
        
        try:
            with os.scandir(directory_path) as entries:
                for entry in entries:
                    if entry.is_file():
                        try:
                            stat_info = entry.stat()
                            file_path = Path(entry.path)
                            
                            # Extract prefix (part before "__")
                            name = entry.name
                            if "__" in name:
                                prefix = name.split("__")[0]
                            else:
                                # Skip files without "__" delimiter
                                continue
                            
                            file_info = FileInfo(
                                path=file_path,
                                name=name,
                                prefix=prefix,
                                size=stat_info.st_size,
                                modified_time=datetime.fromtimestamp(stat_info.st_mtime),
                                extension=file_path.suffix.upper()
                            )
                            files.append(file_info)
                            
                        except (OSError, PermissionError) as e:
                            # Log error but continue processing other files
                            print(f"Warning: Could not access file {entry.path}: {e}")
                            continue
                            
        except (OSError, PermissionError) as e:
            raise ValueError(f"Cannot access directory {directory_path}: {e}")
        
        return files
    
    def _filter_by_extensions(self, files: List[FileInfo]) -> List[FileInfo]:
        """Filter out files with excluded extensions"""
        return [f for f in files if f.extension not in self.excluded_extensions]
    
    def _group_files_by_prefix(self, files: List[FileInfo]) -> Dict[str, List[FileInfo]]:
        """Group files by their prefix"""
        groups = {}
        
        for file_info in files:
            prefix = file_info.prefix
            if prefix not in groups:
                groups[prefix] = []
            groups[prefix].append(file_info)
        
        return groups