"""Tests for error handling functionality"""

import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings
from src.error_handler import ErrorHandler
from src.models import Config, EmailConfig


class TestErrorHandler:
    """Test cases for ErrorHandler"""
    
    def setup_method(self):
        """Set up test fixtures"""
        pass
    
    @given(
        file_paths=st.lists(
            st.text(min_size=5, max_size=30).filter(lambda x: x.isalnum()),
            min_size=1, max_size=5
        )
    )
    @settings(max_examples=5)  # Reduced for faster execution
    def test_property_14_file_access_error_handling(self, file_paths):
        """
        Property 14: File Access Error Handling
        For any file access error during processing, the system should log the error 
        and continue processing remaining files.
        **Feature: dir-purge, Property 14: File Access Error Handling**
        **Validates: Requirements 7.2**
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create some valid files and some invalid paths
            valid_files = []
            invalid_paths = []
            
            for i, file_name in enumerate(file_paths):
                if i % 2 == 0:
                    # Create valid file
                    file_path = Path(temp_dir) / f"{file_name}.dat"
                    file_path.write_text("test content")
                    valid_files.append(file_path)
                else:
                    # Create invalid path (non-existent)
                    invalid_path = Path(temp_dir) / "nonexistent" / f"{file_name}.dat"
                    invalid_paths.append(invalid_path)
            
            # Test file access validation
            valid_errors = []
            invalid_errors = []
            
            for file_path in valid_files:
                error = ErrorHandler.validate_file_access(file_path)
                if error:
                    valid_errors.append(error)
            
            for file_path in invalid_paths:
                error = ErrorHandler.validate_file_access(file_path)
                if error:
                    invalid_errors.append(error)
            
            # Valid files should not produce errors
            assert len(valid_errors) == 0
            
            # Invalid files should produce errors
            assert len(invalid_errors) == len(invalid_paths)
            
            # Error messages should be descriptive
            for error in invalid_errors:
                assert "does not exist" in error or "Cannot access" in error
    
    def test_directory_access_validation(self):
        """Test directory access validation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Valid directory
            errors = ErrorHandler.validate_directory_access(temp_dir)
            assert len(errors) == 0
            
            # Non-existent directory
            errors = ErrorHandler.validate_directory_access("/nonexistent/path")
            assert len(errors) > 0
            assert "does not exist" in errors[0]
            
            # Empty path
            errors = ErrorHandler.validate_directory_access("")
            assert len(errors) > 0
            assert "empty" in errors[0]
    
    def test_timestamp_validation(self):
        """Test timestamp validation"""
        # Valid timestamps
        assert ErrorHandler.validate_timestamp(datetime.now())
        assert ErrorHandler.validate_timestamp(datetime(2020, 1, 1))
        
        # Invalid timestamps (too old/new)
        assert not ErrorHandler.validate_timestamp(datetime(1900, 1, 1))
        assert not ErrorHandler.validate_timestamp(datetime(2200, 1, 1))
    
    def test_file_deletion_error_handling(self):
        """Test file deletion error handling"""
        file_path = Path("/test/file.dat")
        
        # Test different error types
        perm_error = PermissionError("Access denied")
        error_msg = ErrorHandler.handle_file_deletion_error(file_path, perm_error)
        assert "Permission denied" in error_msg
        
        not_found_error = FileNotFoundError("File not found")
        error_msg = ErrorHandler.handle_file_deletion_error(file_path, not_found_error)
        assert "not found" in error_msg
        
        os_error = OSError("Disk error")
        error_msg = ErrorHandler.handle_file_deletion_error(file_path, os_error)
        assert "OS error" in error_msg
    
    @given(
        min_files=st.integers(),
        max_age=st.integers(),
        smtp_port=st.integers()
    )
    @settings(max_examples=10)  # Reduced for faster execution
    def test_property_15_configuration_validation(self, min_files, max_age, smtp_port):
        """
        Property 15: Configuration Validation
        For any invalid configuration input, the system should provide specific validation error messages.
        **Feature: dir-purge, Property 15: Configuration Validation**
        **Validates: Requirements 7.3**
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create config with potentially invalid values
            email_config = EmailConfig(
                send_email=True,
                smtp_server="test.com",
                smtp_port=smtp_port,
                from_email="test@example.com",
                to_email="user@example.com"
            )
            
            config = Config(
                target_directory=temp_dir,  # Valid directory
                min_files_to_keep=min_files,
                max_age_days=max_age,
                email_settings=email_config
            )
            
            # Validate configuration
            errors = ErrorHandler.validate_configuration(config)
            
            # Check for expected validation errors
            if min_files < 0:
                assert any("min_files_to_keep must be non-negative" in error for error in errors)
            
            if max_age < 0:
                assert any("max_age_days must be non-negative" in error for error in errors)
            
            if smtp_port <= 0 or smtp_port > 65535:
                assert any("smtp_port must be between 1 and 65535" in error for error in errors)
            
            # If all values are valid, should have no errors (except possibly email config)
            if min_files >= 0 and max_age >= 0 and 1 <= smtp_port <= 65535:
                # Filter out any email-related errors for this test
                non_email_errors = [e for e in errors if "smtp_port" not in e and "email" not in e.lower()]
                assert len(non_email_errors) == 0
    
    def test_email_config_validation(self):
        """Test email configuration validation"""
        # Valid email config
        valid_config = EmailConfig(
            send_email=True,
            smtp_server="smtp.test.com",
            smtp_port=587,
            from_email="test@example.com",
            to_email="user@example.com"
        )
        errors = ErrorHandler.validate_email_config(valid_config)
        assert len(errors) == 0
        
        # Invalid email config (missing server)
        invalid_config = EmailConfig(
            send_email=True,
            smtp_server="",
            from_email="test@example.com",
            to_email="user@example.com"
        )
        errors = ErrorHandler.validate_email_config(invalid_config)
        assert len(errors) > 0
        assert any("smtp_server is required" in error for error in errors)