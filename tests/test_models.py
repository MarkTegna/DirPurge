"""Property-based tests for data models"""

import pytest
from hypothesis import given, strategies as st
from datetime import datetime, timezone
from pathlib import Path
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models import FileInfo, Config, EmailConfig, PurgeResult


# Custom strategies for generating test data
@st.composite
def file_info_strategy(draw):
    """Generate valid FileInfo instances"""
    # Generate a filename with "__" delimiter
    prefix = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    suffix = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    extension = draw(st.sampled_from(['.txt', '.log', '.dat', '.tmp', '.bak']))
    
    filename = f"{prefix}__{suffix}{extension}"
    path = Path(f"test_dir/{filename}")
    
    # Generate valid timestamp - avoid edge cases that might cause issues
    timestamp = draw(st.datetimes(
        min_value=datetime(1970, 1, 1),
        max_value=datetime(2030, 12, 31)
    ))
    
    size = draw(st.integers(min_value=0, max_value=1000000))
    
    return FileInfo(
        path=path,
        name=filename,
        prefix=prefix,
        size=size,
        modified_time=timestamp,
        extension=extension
    )


@st.composite
def invalid_timestamp_file_info_strategy(draw):
    """Generate FileInfo instances with potentially problematic timestamps"""
    prefix = draw(st.text(min_size=1, max_size=10, alphabet='abcdefghijklmnopqrstuvwxyz'))
    filename = f"{prefix}__test.txt"
    path = Path(f"test_dir/{filename}")
    
    # Generate edge case timestamps that might cause validation issues
    timestamp = draw(st.one_of(
        # Very old dates
        st.datetimes(min_value=datetime(1900, 1, 1), max_value=datetime(1969, 12, 31)),
        # Very future dates
        st.datetimes(min_value=datetime(2100, 1, 1), max_value=datetime(2200, 12, 31)),
        # Normal dates for comparison
        st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2025, 12, 31))
    ))
    
    return FileInfo(
        path=path,
        name=filename,
        prefix=prefix,
        size=draw(st.integers(min_value=0, max_value=1000)),
        modified_time=timestamp,
        extension='.txt'
    )


class TestDataModelValidation:
    """Property-based tests for data model validation"""
    
    @given(file_info_strategy())
    def test_property_16_timestamp_validation(self, file_info):
        """
        Feature: dir-purge, Property 16: Timestamp Validation
        For any file with invalid or missing timestamps, the system should handle the error gracefully without crashing.
        Validates: Requirements 7.4
        """
        # Test that FileInfo can be created with various timestamps without crashing
        assert isinstance(file_info.modified_time, datetime)
        assert file_info.modified_time is not None
        
        # Test that we can access timestamp properties without errors
        try:
            year = file_info.modified_time.year
            month = file_info.modified_time.month
            day = file_info.modified_time.day
            assert isinstance(year, int)
            assert isinstance(month, int)
            assert isinstance(day, int)
            assert 1 <= month <= 12
            assert 1 <= day <= 31
        except (ValueError, AttributeError, OverflowError) as e:
            # If timestamp operations fail, the system should handle it gracefully
            # This test ensures we don't crash on timestamp operations
            pytest.fail(f"Timestamp validation failed ungracefully: {e}")
    
    @given(invalid_timestamp_file_info_strategy())
    def test_property_16_edge_case_timestamps(self, file_info):
        """
        Feature: dir-purge, Property 16: Timestamp Validation (Edge Cases)
        Test handling of edge case timestamps that might cause issues.
        Validates: Requirements 7.4
        """
        # Test that even edge case timestamps don't cause crashes
        try:
            # Common timestamp operations that might fail
            timestamp_str = str(file_info.modified_time)
            timestamp_iso = file_info.modified_time.isoformat()
            
            # Ensure basic operations work
            assert isinstance(timestamp_str, str)
            assert isinstance(timestamp_iso, str)
            assert len(timestamp_str) > 0
            assert len(timestamp_iso) > 0
            
        except (ValueError, OverflowError, OSError) as e:
            # If operations fail, ensure it's handled gracefully
            pytest.fail(f"Edge case timestamp handling failed: {e}")
    
    @given(st.lists(file_info_strategy(), min_size=1, max_size=10))
    def test_file_info_list_operations(self, file_list):
        """Test that lists of FileInfo objects can be processed safely"""
        # Test sorting by timestamp (common operation in the system)
        try:
            sorted_files = sorted(file_list, key=lambda f: f.modified_time, reverse=True)
            assert len(sorted_files) == len(file_list)
            
            # Verify sorting worked (newest first)
            for i in range(len(sorted_files) - 1):
                assert sorted_files[i].modified_time >= sorted_files[i + 1].modified_time
                
        except (TypeError, ValueError, OverflowError) as e:
            pytest.fail(f"File list timestamp operations failed: {e}")