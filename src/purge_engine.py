"""Purge engine with file preservation rules for DirPurge"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from .models import FileInfo, PurgeResult


class PurgeEngine:
    """Determines which files to delete based on age and count criteria"""
    
    def __init__(self, min_files_to_keep: int = 50, max_age_days: int = 366):
        """Initialize purge engine with preservation rules"""
        self.min_files_to_keep = min_files_to_keep
        self.max_age_days = max_age_days
    
    def determine_files_to_purge(self, file_groups: Dict[str, List[FileInfo]]) -> Tuple[List[FileInfo], List[FileInfo]]:
        """Determine which files to delete and which to preserve"""
        files_to_delete = []
        files_to_preserve = []
        
        for prefix, files in file_groups.items():
            preserve, delete = self._apply_preservation_rules(files)
            files_to_preserve.extend(preserve)
            files_to_delete.extend(delete)
        
        return files_to_delete, files_to_preserve
    
    def _apply_preservation_rules(self, files: List[FileInfo]) -> Tuple[List[FileInfo], List[FileInfo]]:
        """Apply preservation rules to a group of files"""
        if not files:
            return [], []
        
        # Sort files by modification time (newest first)
        sorted_files = self._sort_files_by_date(files)
        
        # Calculate age threshold
        age_threshold = datetime.now() - timedelta(days=self.max_age_days)
        
        files_to_preserve = []
        files_to_delete = []
        
        for i, file_info in enumerate(sorted_files):
            # Preserve if within count limit OR newer than age threshold
            if i < self.min_files_to_keep or file_info.modified_time > age_threshold:
                files_to_preserve.append(file_info)
            else:
                files_to_delete.append(file_info)
        
        return files_to_preserve, files_to_delete
    
    def _sort_files_by_date(self, files: List[FileInfo]) -> List[FileInfo]:
        """Sort files by modification time with newest first"""
        return sorted(files, key=lambda f: f.modified_time, reverse=True)
    
    def execute_purge(self, files_to_delete: List[FileInfo], dry_run: bool = False) -> PurgeResult:
        """Execute the purge operation"""
        start_time = datetime.now()
        actual_deletions = 0
        errors = []
        total_files = len(files_to_delete)
        
        # Show progress for large operations
        show_progress = total_files > 1000
        if show_progress:
            print(f"Deleting {total_files} files...")
        
        if not dry_run:
            for i, file_info in enumerate(files_to_delete, 1):
                try:
                    os.remove(file_info.path)
                    actual_deletions += 1
                    
                    # Show progress every 5% or every 1000 files, whichever is more frequent
                    if show_progress:
                        progress_interval = max(1, min(total_files // 20, 1000))  # 5% or 1000 files
                        if i % progress_interval == 0 or i == total_files:
                            percent = (i * 100) // total_files
                            print(f"Progress: {percent}% ({i}/{total_files} files deleted)")
                            
                except (OSError, PermissionError) as e:
                    error_msg = f"Failed to delete {file_info.path}: {e}"
                    errors.append(error_msg)
                    print(f"Warning: {error_msg}")
        else:
            # In dry run mode, we would delete all files (no actual deletion)
            actual_deletions = len(files_to_delete)
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        return PurgeResult(
            total_files_scanned=0,  # Will be set by caller
            file_sets_found=0,      # Will be set by caller
            files_to_delete=files_to_delete,
            files_preserved=[],     # Will be set by caller
            actual_deletions=actual_deletions,
            errors=errors,
            execution_time=execution_time
        )