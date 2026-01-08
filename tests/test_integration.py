"""Integration tests for DirPurge application"""

import pytest
import tempfile
import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from src.main import main


class TestIntegration:
    """Comprehensive integration tests for DirPurge"""
    
    def create_test_files(self, target_dir: Path, file_sets: dict):
        """Create test files with specified timestamps"""
        for prefix, file_configs in file_sets.items():
            for i, (days_old, extension) in enumerate(file_configs):
                filename = f"{prefix}__{i:03d}{extension}"
                file_path = target_dir / filename
                
                # Create file with content
                file_path.write_text(f"Test content for {filename}")
                
                # Set modification time
                timestamp = datetime.now() - timedelta(days=days_old)
                mod_time = timestamp.timestamp()
                os.utime(file_path, (mod_time, mod_time))
    
    def test_end_to_end_dry_run(self):
        """Test complete end-to-end workflow in dry run mode"""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir) / "target"
            target_dir.mkdir()
            
            # Create test file sets
            file_sets = {
                "backup": [
                    (1, ".log"),    # 1 day old - should be preserved
                    (10, ".log"),   # 10 days old - should be preserved
                    (100, ".log"),  # 100 days old - should be preserved
                    (500, ".log"),  # 500 days old - should be deleted
                ],
                "report": [
                    (5, ".dat"),    # 5 days old - should be preserved
                    (400, ".dat"),  # 400 days old - should be deleted
                ],
                "archive": [
                    (2, ".zip"),    # Should be ignored (excluded extension)
                ]
            }
            
            self.create_test_files(target_dir, file_sets)
            
            # Create files without "__" delimiter (should be ignored)
            ignored_file = target_dir / "no_delimiter.txt"
            ignored_file.write_text("Should be ignored")
            
            # Run DirPurge in dry run mode
            args = [
                '--target-directory', str(target_dir),
                '--min-files', '2',
                '--max-age', '365',
                '--dry-run',
                '--reports-directory', str(temp_dir)
            ]
            
            result = main(args)
            
            # Should succeed
            assert result == 0
            
            # All files should still exist (dry run)
            assert len(list(target_dir.glob("*"))) == 8  # 7 test files + 1 ignored
            
            # Report should be generated
            reports_dir = Path(temp_dir)
            report_files = list(reports_dir.glob("dirpurge_*.txt"))
            assert len(report_files) == 1
            
            # Check report content
            report_content = report_files[0].read_text()
            assert "DirPurge Operation Report" in report_content
            assert "Dry Run Mode: Yes" in report_content
            assert "Total files scanned: 6" in report_content  # Excludes .zip and no delimiter
    
    def test_end_to_end_actual_purge(self):
        """Test complete end-to-end workflow with actual file deletion"""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir) / "target"
            target_dir.mkdir()
            
            # Create test file sets
            file_sets = {
                "test": [
                    (1, ".dat"),    # Recent - should be preserved
                    (2, ".dat"),    # Recent - should be preserved  
                    (400, ".dat"),  # Old - should be deleted
                    (500, ".dat"),  # Old - should be deleted
                ]
            }
            
            self.create_test_files(target_dir, file_sets)
            
            # Verify initial file count
            initial_files = list(target_dir.glob("test__*"))
            assert len(initial_files) == 4
            
            # Run DirPurge with actual deletion
            args = [
                '--target-directory', str(target_dir),
                '--min-files', '2',
                '--max-age', '365',
                '--reports-directory', str(temp_dir)
            ]
            
            result = main(args)
            
            # Should succeed
            assert result == 0
            
            # Should have 2 files remaining (preserved)
            remaining_files = list(target_dir.glob("test__*"))
            assert len(remaining_files) == 2
            
            # Verify the correct files were preserved (newest ones)
            remaining_names = [f.name for f in remaining_files]
            assert "test__000.dat" in remaining_names  # 1 day old
            assert "test__001.dat" in remaining_names  # 2 days old
    
    def test_multiple_file_sets(self):
        """Test handling of multiple file sets with different preservation rules"""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir) / "target"
            target_dir.mkdir()
            
            # Create multiple file sets
            file_sets = {
                "logs": [
                    (1, ".log"), (5, ".log"), (10, ".log"), (400, ".log"), (500, ".log")
                ],
                "backups": [
                    (2, ".bak"), (300, ".bak"), (600, ".bak")
                ],
                "reports": [
                    (1, ".rpt"), (200, ".rpt")
                ]
            }
            
            self.create_test_files(target_dir, file_sets)
            
            # Run with min_files=2, max_age=365
            args = [
                '--target-directory', str(target_dir),
                '--min-files', '2',
                '--max-age', '365',
                '--dry-run'
            ]
            
            result = main(args)
            assert result == 0
            
            # All files should still exist (dry run)
            all_files = list(target_dir.glob("*__*"))
            assert len(all_files) == 10
    
    def test_configuration_file_integration(self):
        """Test integration with INI configuration file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir) / "target"
            target_dir.mkdir()
            
            # Create test files
            file_sets = {
                "test": [(1, ".dat"), (400, ".dat")]
            }
            self.create_test_files(target_dir, file_sets)
            
            # Create INI file
            ini_file = Path(temp_dir) / "dirpurge.ini"
            ini_content = f"""[general]
target_directory = {target_dir}
min_files_to_keep = 1
max_age_days = 365
dry_run = true
reports_directory = {temp_dir}/reports

[email]
send_email = false
"""
            ini_file.write_text(ini_content)
            
            # Change to temp directory and run
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                # Use a dummy CLI arg to avoid help display
                result = main(['--dry-run'])  # Use INI for other settings
                assert result == 0
            finally:
                os.chdir(original_cwd)
    
    def test_error_handling_integration(self):
        """Test error handling in integration scenarios"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test with non-existent directory
            result = main([
                '--target-directory', '/nonexistent/path',
                '--dry-run'
            ])
            assert result == 1  # Should fail
            
            # Test with invalid configuration
            result = main([
                '--target-directory', str(temp_dir),
                '--min-files', '-5',  # Invalid
                '--dry-run'
            ])
            assert result == 1  # Should fail
    
    def test_extension_filtering_integration(self):
        """Test extension filtering in complete workflow"""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir) / "target"
            target_dir.mkdir()
            
            # Create files with various extensions
            file_sets = {
                "test": [
                    (1, ".dat"),   # Should be processed
                    (1, ".log"),   # Should be processed
                    (1, ".txt"),   # Should be excluded (default)
                    (1, ".zip"),   # Should be excluded (default)
                ]
            }
            
            self.create_test_files(target_dir, file_sets)
            
            args = [
                '--target-directory', str(target_dir),
                '--dry-run'
            ]
            
            result = main(args)
            assert result == 0
            
            # Should only process .dat and .log files (2 files)
            # The output should indicate 2 files scanned
    
    def test_cli_override_integration(self):
        """Test CLI arguments overriding INI file settings"""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir) / "target"
            target_dir.mkdir()
            
            # Create test files
            file_sets = {
                "test": [(1, ".dat"), (400, ".dat")]
            }
            self.create_test_files(target_dir, file_sets)
            
            # Create INI file with different settings
            ini_file = Path(temp_dir) / "dirpurge.ini"
            ini_content = f"""[general]
target_directory = {target_dir}
min_files_to_keep = 5
max_age_days = 30
dry_run = false
"""
            ini_file.write_text(ini_content)
            
            # Override with CLI arguments
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                result = main([
                    '--min-files', '1',     # Override INI
                    '--max-age', '365',     # Override INI
                    '--dry-run'             # Override INI
                ])
                assert result == 0
            finally:
                os.chdir(original_cwd)
    
    def test_empty_directory_integration(self):
        """Test handling of empty directories"""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir) / "empty_target"
            target_dir.mkdir()
            
            args = [
                '--target-directory', str(target_dir),
                '--dry-run'
            ]
            
            result = main(args)
            assert result == 0  # Should handle empty directory gracefully
    
    def test_large_file_set_integration(self):
        """Test with larger number of files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir) / "target"
            target_dir.mkdir()
            
            # Create larger file set
            file_sets = {
                "bulk": [(i * 10, ".dat") for i in range(20)]  # 20 files with varying ages
            }
            
            self.create_test_files(target_dir, file_sets)
            
            args = [
                '--target-directory', str(target_dir),
                '--min-files', '5',
                '--max-age', '100',
                '--dry-run'
            ]
            
            result = main(args)
            assert result == 0
            
            # Should process all 20 files
            all_files = list(target_dir.glob("bulk__*"))
            assert len(all_files) == 20