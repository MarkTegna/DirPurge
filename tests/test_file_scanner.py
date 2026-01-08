"""Tests for file scanning functionality"""

import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime
from hypothesis import given, strategies as st, settings
from src.file_scanner import FileScanner
from src.models import FileInfo


class TestFileScanner:
    """Test cases for FileScanner"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.scanner = FileScanner()
    
    @given(
        prefixes=st.lists(st.text(min_size=1, max_size=10).filter(lambda x: x.isalnum()), min_size=1, max_size=5),
        suffixes=st.lists(st.text(min_size=1, max_size=10).filter(lambda x: x.isalnum()), min_size=1, max_size=3)
    )
    @settings(max_examples=20)  # Reduced for faster execution
    def test_property_1_file_grouping_correctness(self, prefixes, suffixes):
        """
        Property 1: File Grouping Correctness
        For any directory containing files, files with "__" delimiter should be grouped by their prefix, 
        and files without "__" should be ignored entirely.
        **Feature: dir-purge, Property 1: File Grouping Correctness**
        **Validates: Requirements 1.1, 1.2**
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            created_files = []
            expected_groups = {}
            
            # Create files with prefixes
            for prefix in prefixes:
                for suffix in suffixes:
                    filename = f"{prefix}__{suffix}.dat"
                    file_path = Path(temp_dir) / filename
                    file_path.write_text("test content")
                    created_files.append(filename)
                    
                    if prefix not in expected_groups:
                        expected_groups[prefix] = []
                    expected_groups[prefix].append(filename)
            
            # Create files without "__" (should be ignored)
            ignored_file = Path(temp_dir) / "no_delimiter.dat"
            ignored_file.write_text("ignored")
            
            # Scan directory
            groups = self.scanner.scan_directory(temp_dir)
            
            # Verify grouping correctness
            assert len(groups) == len(expected_groups)
            
            for prefix, expected_files in expected_groups.items():
                assert prefix in groups
                actual_files = [f.name for f in groups[prefix]]
                assert set(actual_files) == set(expected_files)
            
            # Verify ignored files are not included
            all_scanned_files = []
            for file_list in groups.values():
                all_scanned_files.extend([f.name for f in file_list])
            assert "no_delimiter.dat" not in all_scanned_files
    
    def test_empty_directory(self):
        """Test scanning empty directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            groups = self.scanner.scan_directory(temp_dir)
            assert groups == {}
    
    def test_nonexistent_directory(self):
        """Test error handling for nonexistent directory"""
        with pytest.raises(ValueError, match="Directory does not exist"):
            self.scanner.scan_directory("/nonexistent/path")
    
    def test_file_info_extraction(self):
        """Test that FileInfo objects contain correct information"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test file
            test_file = Path(temp_dir) / "test__file.dat"
            test_content = "test content"
            test_file.write_text(test_content)
            
            groups = self.scanner.scan_directory(temp_dir)
            
            assert "test" in groups
            file_info = groups["test"][0]
            
            assert file_info.name == "test__file.dat"
            assert file_info.prefix == "test"
            assert file_info.size == len(test_content)
            assert file_info.extension == ".DAT"
            assert isinstance(file_info.modified_time, datetime)
            assert file_info.path == test_file
    
    @given(
        included_extensions=st.lists(st.sampled_from(['.DAT', '.LOG', '.BAK']), min_size=1, max_size=3),
        excluded_extensions=st.lists(st.sampled_from(['.PL', '.TXT', '.CSV', '.ZIP']), min_size=1, max_size=4)
    )
    @settings(max_examples=15)  # Reduced for faster execution
    def test_property_2_extension_filtering(self, included_extensions, excluded_extensions):
        """
        Property 2: Extension Filtering
        For any configured exclusion list and file collection, all files with excluded extensions 
        should be filtered out before processing.
        **Feature: dir-purge, Property 2: Extension Filtering**
        **Validates: Requirements 1.3, 1.4**
        """
        scanner = FileScanner(excluded_extensions=excluded_extensions)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create files with included extensions (should be processed)
            included_files = []
            for i, ext in enumerate(included_extensions):
                filename = f"test__{i}{ext.lower()}"  # Use lowercase to test case insensitivity
                file_path = Path(temp_dir) / filename
                file_path.write_text("content")
                included_files.append(filename)
            
            # Create files with excluded extensions (should be filtered out)
            excluded_files = []
            for i, ext in enumerate(excluded_extensions):
                filename = f"excluded__{i}{ext.lower()}"
                file_path = Path(temp_dir) / filename
                file_path.write_text("content")
                excluded_files.append(filename)
            
            # Scan directory
            groups = scanner.scan_directory(temp_dir)
            
            # Collect all scanned files
            all_scanned_files = []
            for file_list in groups.values():
                all_scanned_files.extend([f.name for f in file_list])
            
            # Verify included files are present
            for included_file in included_files:
                assert included_file in all_scanned_files
            
            # Verify excluded files are not present
            for excluded_file in excluded_files:
                assert excluded_file not in all_scanned_files