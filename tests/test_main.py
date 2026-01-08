"""Tests for main application functionality"""

import pytest
import tempfile
import os
from pathlib import Path
from hypothesis import given, strategies as st, settings
from src.main import main


class TestMain:
    """Test cases for main application"""
    
    @given(
        target_dir_name=st.text(min_size=5, max_size=20).filter(lambda x: x.isalnum()),
        min_files=st.integers(min_value=1, max_value=10),
        max_age=st.integers(min_value=1, max_value=100)
    )
    @settings(max_examples=3)  # Reduced for faster execution
    def test_property_7_ini_file_immutability(self, target_dir_name, min_files, max_age):
        """
        Property 7: INI File Immutability
        For any CLI operation, the original INI file content should remain unchanged after program execution.
        **Feature: dir-purge, Property 7: INI File Immutability**
        **Validates: Requirements 3.4**
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create target directory for scanning
            target_dir = Path(temp_dir) / target_dir_name
            target_dir.mkdir()
            
            # Create some test files
            for i in range(3):
                test_file = target_dir / f"test__{i}.dat"
                test_file.write_text("test content")
            
            # Create INI file
            ini_file = Path(temp_dir) / "dirpurge.ini"
            original_ini_content = f"""[general]
target_directory = {target_dir}
min_files_to_keep = {min_files}
max_age_days = {max_age}
excluded_extensions = .PL,.TXT,.CSV,.ZIP
dry_run = true
reports_directory = {temp_dir}/reports

[email]
send_email = false
smtp_server = smtp.test.com
smtp_port = 587
"""
            ini_file.write_text(original_ini_content)
            
            # Store original content and modification time
            original_content = ini_file.read_text()
            original_mtime = ini_file.stat().st_mtime
            
            # Run application with CLI arguments that override INI values
            args = [
                '--target-directory', str(target_dir),
                '--min-files', str(min_files + 5),  # Different from INI
                '--max-age', str(max_age + 10),     # Different from INI
                '--dry-run'
            ]
            
            # Change working directory to temp_dir so it finds the INI file
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                result = main(args)
                
                # Application should succeed
                assert result == 0
                
                # Verify INI file content is unchanged
                final_content = ini_file.read_text()
                assert final_content == original_content
                
                # Verify INI file was not modified (allowing small time differences)
                final_mtime = ini_file.stat().st_mtime
                assert abs(final_mtime - original_mtime) < 1.0  # Less than 1 second difference
                
            finally:
                os.chdir(original_cwd)
    
    def test_no_arguments_shows_help(self):
        """Test that no arguments shows help"""
        # This should show help and exit with code 0
        result = main([])
        assert result == 0
    
    def test_help_argument(self):
        """Test --help argument"""
        result = main(['--help'])
        assert result == 0
    
    def test_version_argument(self):
        """Test --version argument"""
        result = main(['--version'])
        assert result == 0
    
    def test_invalid_directory(self):
        """Test behavior with invalid target directory"""
        result = main(['--target-directory', '/nonexistent/path', '--dry-run'])
        assert result == 1  # Should fail with error code
    
    def test_missing_configuration(self):
        """Test behavior when no configuration is provided"""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)  # No INI file here
                result = main([])  # No CLI args either
                assert result == 0  # Shows help
            finally:
                os.chdir(original_cwd)
    
    def test_property_17_cli_argument_coverage(self):
        """
        Property 17: CLI Argument Coverage
        For any configuration option available in INI files, there should be a corresponding CLI argument.
        **Feature: dir-purge, Property 17: CLI Argument Coverage**
        **Validates: Requirements 8.1**
        """
        from src.config_manager import ConfigManager
        
        config_manager = ConfigManager()
        
        # Get default INI configuration structure
        default_config = config_manager.default_config
        
        # Test CLI arguments by parsing help
        try:
            config_manager.parse_cli_args(['--help'])
        except SystemExit:
            pass  # Expected for --help
        
        # Test that all major INI options have CLI equivalents
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test directory
            target_dir = Path(temp_dir) / "test_target"
            target_dir.mkdir()
            
            # Test CLI arguments for all major configuration options
            cli_args = [
                '--target-directory', str(target_dir),
                '--min-files', '25',
                '--max-age', '180',
                '--excluded-extensions', '.LOG,.BAK',
                '--dry-run',
                '--reports-directory', str(temp_dir),
                '--send-email',
                '--smtp-server', 'smtp.test.com',
                '--smtp-port', '587',
                '--smtp-tls',
                '--smtp-username', 'testuser',
                '--smtp-password', 'testpass',
                '--from-email', 'from@test.com',
                '--to-email', 'to@test.com'
            ]
            
            # Parse CLI arguments - should not raise exception
            cli_config = config_manager.parse_cli_args(cli_args)
            
            # Verify all major configuration areas are covered
            assert 'target_directory' in cli_config
            assert 'min_files_to_keep' in cli_config
            assert 'max_age_days' in cli_config
            assert 'excluded_extensions' in cli_config
            assert 'dry_run' in cli_config
            assert 'reports_directory' in cli_config
            assert 'email_settings' in cli_config
            
            # Verify email settings are properly parsed
            email_config = cli_config['email_settings']
            assert email_config.send_email == True
            assert email_config.smtp_server == 'smtp.test.com'
            assert email_config.smtp_port == 587
            assert email_config.smtp_use_tls == True
    
    def test_property_19_argument_format_support(self):
        """
        Property 19: Argument Format Support
        For any CLI argument that supports both formats, both short and long forms should work identically.
        **Feature: dir-purge, Property 19: Argument Format Support**
        **Validates: Requirements 8.4**
        """
        from src.config_manager import ConfigManager
        
        config_manager = ConfigManager()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = Path(temp_dir) / "test_target"
            target_dir.mkdir()
            
            # Test short form arguments
            short_args = [
                '-t', str(target_dir),
                '-m', '30',
                '-a', '200',
                '-e', '.LOG,.BAK',
                '-d',
                '-r', str(temp_dir)
            ]
            
            # Test long form arguments
            long_args = [
                '--target-directory', str(target_dir),
                '--min-files', '30',
                '--max-age', '200',
                '--excluded-extensions', '.LOG,.BAK',
                '--dry-run',
                '--reports-directory', str(temp_dir)
            ]
            
            # Parse both forms
            short_config = config_manager.parse_cli_args(short_args)
            long_config = config_manager.parse_cli_args(long_args)
            
            # Both forms should produce identical results
            assert short_config['target_directory'] == long_config['target_directory']
            assert short_config['min_files_to_keep'] == long_config['min_files_to_keep']
            assert short_config['max_age_days'] == long_config['max_age_days']
            assert short_config['excluded_extensions'] == long_config['excluded_extensions']
            assert short_config['dry_run'] == long_config['dry_run']
            assert short_config['reports_directory'] == long_config['reports_directory']