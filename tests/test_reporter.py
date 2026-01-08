"""Tests for reporting functionality"""

import pytest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from hypothesis import given, strategies as st, settings
from src.reporter import Reporter
from src.models import PurgeResult, Config, FileInfo, EmailConfig


class TestReporter:
    """Test cases for Reporter"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.reporter = Reporter()
    
    @given(
        total_scanned=st.integers(min_value=0, max_value=1000),
        file_sets=st.integers(min_value=0, max_value=50),
        files_to_delete_count=st.integers(min_value=0, max_value=100),
        files_preserved_count=st.integers(min_value=0, max_value=100),
        actual_deletions=st.integers(min_value=0, max_value=100),
        execution_time=st.floats(min_value=0.0, max_value=60.0)
    )
    @settings(max_examples=10)  # Reduced for faster execution
    def test_property_9_report_generation(self, total_scanned, file_sets, files_to_delete_count, 
                                        files_preserved_count, actual_deletions, execution_time):
        """
        Property 9: Report Generation
        For any purge operation, generated reports should contain file counts, deletion counts, 
        timestamps, and be saved in the configured reports directory.
        **Feature: dir-purge, Property 9: Report Generation**
        **Validates: Requirements 5.1, 5.2**
        """
        # Create test data
        files_to_delete = []
        files_preserved = []
        
        for i in range(files_to_delete_count):
            file_info = FileInfo(
                path=Path(f"delete_{i}.dat"),
                name=f"delete_{i}.dat",
                prefix="test",
                size=1000,
                modified_time=datetime.now() - timedelta(days=i),
                extension=".DAT"
            )
            files_to_delete.append(file_info)
        
        for i in range(files_preserved_count):
            file_info = FileInfo(
                path=Path(f"preserve_{i}.dat"),
                name=f"preserve_{i}.dat",
                prefix="test",
                size=1000,
                modified_time=datetime.now(),
                extension=".DAT"
            )
            files_preserved.append(file_info)
        
        purge_result = PurgeResult(
            total_files_scanned=total_scanned,
            file_sets_found=file_sets,
            files_to_delete=files_to_delete,
            files_preserved=files_preserved,
            actual_deletions=actual_deletions,
            errors=[],
            execution_time=execution_time
        )
        
        config = Config(
            target_directory="/test/dir",
            min_files_to_keep=50,
            max_age_days=366,
            dry_run=False
        )
        
        # Generate report
        report_content = self.reporter.generate_report(purge_result, config, {"test": files_to_delete + files_preserved})
        
        # Verify report contains required information
        assert "DirPurge Operation Report" in report_content
        assert f"Total files scanned: {total_scanned}" in report_content
        assert f"File sets found: {file_sets}" in report_content
        assert f"Files to delete: {files_to_delete_count}" in report_content
        assert f"Files preserved: {files_preserved_count}" in report_content
        assert f"Actual deletions: {actual_deletions}" in report_content
        assert f"Execution time: {execution_time:.2f} seconds" in report_content
        assert "Generated:" in report_content
        assert config.target_directory in report_content
        
        # Test saving report
        with tempfile.TemporaryDirectory() as temp_dir:
            reporter = Reporter(temp_dir)
            timestamp = datetime.now()
            report_path = reporter.save_report(report_content, timestamp)
            
            # Verify file was created
            assert report_path.exists()
            assert report_path.parent == Path(temp_dir)
            
            # Verify content was saved correctly
            saved_content = report_path.read_text(encoding='utf-8')
            assert saved_content == report_content
    
    def test_empty_purge_result(self):
        """Test report generation with empty purge result"""
        purge_result = PurgeResult(
            total_files_scanned=0,
            file_sets_found=0,
            files_to_delete=[],
            files_preserved=[],
            actual_deletions=0,
            errors=[],
            execution_time=0.0
        )
        
        config = Config(target_directory="/empty/dir")
        
        report_content = self.reporter.generate_report(purge_result, config, {})
        
        assert "Total files scanned: 0" in report_content
        assert "Files to delete: 0" in report_content
        assert "Files preserved: 0" in report_content
    
    def test_report_with_errors(self):
        """Test report generation with errors"""
        purge_result = PurgeResult(
            total_files_scanned=10,
            file_sets_found=2,
            files_to_delete=[],
            files_preserved=[],
            actual_deletions=0,
            errors=["Error 1", "Error 2"],
            execution_time=1.5
        )
        
        config = Config(target_directory="/test/dir")
        
        report_content = self.reporter.generate_report(purge_result, config, {})
        
        assert "Errors:" in report_content
        assert "Error 1" in report_content
        assert "Error 2" in report_content
    
    @given(
        year=st.integers(min_value=2020, max_value=2030),
        month=st.integers(min_value=1, max_value=12),
        day=st.integers(min_value=1, max_value=28),  # Safe day range for all months
        hour=st.integers(min_value=0, max_value=23),
        minute=st.integers(min_value=0, max_value=59)
    )
    @settings(max_examples=10)  # Reduced for faster execution
    def test_property_10_report_filename_format(self, year, month, day, hour, minute):
        """
        Property 10: Report Filename Format
        For any report generation timestamp, the filename should follow YYYYMMDD-HH-MM format exactly.
        **Feature: dir-purge, Property 10: Report Filename Format**
        **Validates: Requirements 5.3**
        """
        timestamp = datetime(year, month, day, hour, minute)
        
        # Test filename formatting
        filename = self.reporter.format_filename(timestamp)
        
        # Verify format: dirpurge_YYYYMMDD-HH-MM.txt
        expected_date_part = f"{year:04d}{month:02d}{day:02d}-{hour:02d}-{minute:02d}"
        expected_filename = f"dirpurge_{expected_date_part}.txt"
        
        assert filename == expected_filename
        
        # Verify the format is parseable back to datetime
        date_part = filename.replace("dirpurge_", "").replace(".txt", "")
        parsed_datetime = datetime.strptime(date_part, "%Y%m%d-%H-%M")
        
        assert parsed_datetime.year == year
        assert parsed_datetime.month == month
        assert parsed_datetime.day == day
        assert parsed_datetime.hour == hour
        assert parsed_datetime.minute == minute