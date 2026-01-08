"""Tests for purge engine functionality"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from hypothesis import given, strategies as st, settings
from src.purge_engine import PurgeEngine
from src.models import FileInfo


class TestPurgeEngine:
    """Test cases for PurgeEngine"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.engine = PurgeEngine(min_files_to_keep=5, max_age_days=30)
    
    @given(
        file_count=st.integers(min_value=1, max_value=20),
        min_keep=st.integers(min_value=1, max_value=10),
        max_age_days=st.integers(min_value=1, max_value=100)
    )
    @settings(max_examples=15)  # Reduced for faster execution
    def test_property_3_file_preservation_rules(self, file_count, min_keep, max_age_days):
        """
        Property 3: File Preservation Rules
        For any file set, the system should preserve the newest N files and all files younger 
        than the age threshold, where N is the minimum count setting.
        **Feature: dir-purge, Property 3: File Preservation Rules**
        **Validates: Requirements 2.1, 2.2, 2.4**
        """
        engine = PurgeEngine(min_files_to_keep=min_keep, max_age_days=max_age_days)
        
        # Create files with different ages
        files = []
        now = datetime.now()
        age_threshold = now - timedelta(days=max_age_days)
        
        for i in range(file_count):
            # Create files with varying ages
            days_old = i * 2  # Each file is 2 days older than the previous
            modified_time = now - timedelta(days=days_old)
            
            file_info = FileInfo(
                path=Path(f"test_file_{i}.dat"),
                name=f"test_file_{i}.dat",
                prefix="test",
                size=1000,
                modified_time=modified_time,
                extension=".DAT"
            )
            files.append(file_info)
        
        # Apply preservation rules
        preserved, to_delete = engine._apply_preservation_rules(files)
        
        # Verify preservation rules
        # 1. At least min_keep files should be preserved (if available)
        expected_min_preserved = min(min_keep, file_count)
        assert len(preserved) >= expected_min_preserved
        
        # 2. All files newer than age threshold should be preserved
        for file_info in files:
            if file_info.modified_time > age_threshold:
                assert file_info in preserved
        
        # 3. Files should be sorted by date (newest first in preserved list)
        if len(preserved) > 1:
            for i in range(len(preserved) - 1):
                assert preserved[i].modified_time >= preserved[i + 1].modified_time
        
        # 4. Total files should equal preserved + to_delete
        assert len(preserved) + len(to_delete) == file_count
    
    @given(
        file_count=st.integers(min_value=2, max_value=15)
    )
    @settings(max_examples=10)  # Reduced for faster execution
    def test_property_4_file_ordering_consistency(self, file_count):
        """
        Property 4: File Ordering Consistency
        For any collection of files with timestamps, the system should consistently 
        order them by modification time with newest first.
        **Feature: dir-purge, Property 4: File Ordering Consistency**
        **Validates: Requirements 2.3**
        """
        # Create files with random timestamps
        files = []
        base_time = datetime.now()
        
        for i in range(file_count):
            # Create files with different timestamps
            modified_time = base_time - timedelta(hours=i * 3, minutes=i * 7)
            
            file_info = FileInfo(
                path=Path(f"file_{i}.dat"),
                name=f"file_{i}.dat",
                prefix="test",
                size=1000,
                modified_time=modified_time,
                extension=".DAT"
            )
            files.append(file_info)
        
        # Sort files
        sorted_files = self.engine._sort_files_by_date(files)
        
        # Verify ordering (newest first)
        for i in range(len(sorted_files) - 1):
            assert sorted_files[i].modified_time >= sorted_files[i + 1].modified_time
        
        # Verify all files are included
        assert len(sorted_files) == file_count
        assert set(f.name for f in sorted_files) == set(f.name for f in files)
    
    def test_empty_file_list(self):
        """Test behavior with empty file list"""
        preserved, to_delete = self.engine._apply_preservation_rules([])
        assert preserved == []
        assert to_delete == []
    
    def test_single_file(self):
        """Test behavior with single file"""
        file_info = FileInfo(
            path=Path("single.dat"),
            name="single.dat",
            prefix="test",
            size=1000,
            modified_time=datetime.now(),
            extension=".DAT"
        )
        
        preserved, to_delete = self.engine._apply_preservation_rules([file_info])
        assert len(preserved) == 1
        assert len(to_delete) == 0
        assert preserved[0] == file_info
    
    @given(
        file_count=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=10)  # Reduced for faster execution
    def test_property_8_dry_run_safety(self, file_count):
        """
        Property 8: Dry Run Safety
        For any purge operation in dry run mode, no files should be deleted and 
        all reporting should function normally.
        **Feature: dir-purge, Property 8: Dry Run Safety**
        **Validates: Requirements 4.1, 4.2, 4.3, 4.4**
        """
        import tempfile
        
        # Create temporary files for testing
        files_to_delete = []
        temp_files = []
        
        with tempfile.TemporaryDirectory() as temp_dir:
            for i in range(file_count):
                # Create actual temporary files
                temp_file = Path(temp_dir) / f"test_file_{i}.dat"
                temp_file.write_text("test content")
                temp_files.append(temp_file)
                
                file_info = FileInfo(
                    path=temp_file,
                    name=f"test_file_{i}.dat",
                    prefix="test",
                    size=12,  # "test content" length
                    modified_time=datetime.now(),
                    extension=".DAT"
                )
                files_to_delete.append(file_info)
            
            # Execute dry run
            result = self.engine.execute_purge(files_to_delete, dry_run=True)
            
            # Verify dry run safety
            # 1. All files should still exist
            for temp_file in temp_files:
                assert temp_file.exists(), f"File {temp_file} was deleted in dry run mode"
            
            # 2. Reporting should work normally
            assert result.actual_deletions == file_count  # Would delete this many
            assert len(result.files_to_delete) == file_count
            assert isinstance(result.execution_time, float)
            assert result.execution_time >= 0
            
            # 3. No errors should occur in dry run
            assert len(result.errors) == 0