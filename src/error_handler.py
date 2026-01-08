"""Centralized error handling and validation for DirPurge"""

import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from .models import Config, EmailConfig


class ErrorHandler:
    """Centralized error handling and validation"""
    
    @staticmethod
    def validate_directory_access(directory_path: str) -> List[str]:
        """Validate directory exists and is accessible"""
        errors = []
        
        if not directory_path:
            errors.append("Target directory path is empty")
            return errors
        
        path = Path(directory_path)
        
        if not path.exists():
            errors.append(f"Target directory does not exist: {directory_path}")
        elif not path.is_dir():
            errors.append(f"Path is not a directory: {directory_path}")
        else:
            # Test read access
            try:
                list(path.iterdir())
            except PermissionError:
                errors.append(f"Permission denied accessing directory: {directory_path}")
            except OSError as e:
                errors.append(f"Cannot access directory {directory_path}: {e}")
        
        return errors
    
    @staticmethod
    def validate_file_access(file_path: Path) -> str:
        """Validate file access and return error message if any"""
        try:
            if not file_path.exists():
                return f"File does not exist: {file_path}"
            
            # Test read access
            file_path.stat()
            return ""
            
        except PermissionError:
            return f"Permission denied accessing file: {file_path}"
        except OSError as e:
            return f"Cannot access file {file_path}: {e}"
    
    @staticmethod
    def validate_timestamp(timestamp: datetime) -> bool:
        """Validate timestamp is reasonable"""
        try:
            # Check if timestamp is within reasonable range
            min_date = datetime(1970, 1, 1)
            max_date = datetime(2100, 1, 1)
            
            return min_date <= timestamp <= max_date
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def handle_file_deletion_error(file_path: Path, error: Exception) -> str:
        """Handle file deletion errors and return formatted error message"""
        if isinstance(error, PermissionError):
            return f"Permission denied deleting file: {file_path}"
        elif isinstance(error, FileNotFoundError):
            return f"File not found during deletion: {file_path}"
        elif isinstance(error, OSError):
            return f"OS error deleting file {file_path}: {error}"
        else:
            return f"Unexpected error deleting file {file_path}: {error}"
    
    @staticmethod
    def validate_configuration(config: Config) -> List[str]:
        """Comprehensive configuration validation"""
        errors = []
        
        # Validate target directory
        if not config.target_directory:
            errors.append("target_directory is required")
        else:
            dir_errors = ErrorHandler.validate_directory_access(config.target_directory)
            errors.extend(dir_errors)
        
        # Validate numeric values
        if config.min_files_to_keep < 0:
            errors.append("min_files_to_keep must be non-negative")
        
        if config.max_age_days < 0:
            errors.append("max_age_days must be non-negative")
        
        # Validate reports directory
        if config.reports_directory:
            reports_path = Path(config.reports_directory)
            if reports_path.exists() and not reports_path.is_dir():
                errors.append(f"Reports path exists but is not a directory: {config.reports_directory}")
        
        # Validate email configuration
        if config.email_settings:
            email_errors = ErrorHandler.validate_email_config(config.email_settings)
            errors.extend(email_errors)
        
        return errors
    
    @staticmethod
    def validate_email_config(email_config: EmailConfig) -> List[str]:
        """Validate email configuration"""
        errors = []
        
        if not email_config.send_email:
            return errors  # No validation needed if email is disabled
        
        if not email_config.smtp_server:
            errors.append("smtp_server is required when email is enabled")
        
        if not email_config.from_email:
            errors.append("from_email is required when email is enabled")
        
        if not email_config.to_email:
            errors.append("to_email is required when email is enabled")
        
        if email_config.smtp_port <= 0 or email_config.smtp_port > 65535:
            errors.append("smtp_port must be between 1 and 65535")
        
        # Basic email format validation
        if email_config.from_email and '@' not in email_config.from_email:
            errors.append("from_email must be a valid email address")
        
        if email_config.to_email and '@' not in email_config.to_email:
            errors.append("to_email must be a valid email address")
        
        return errors
    
    @staticmethod
    def log_error(error_message: str, print_to_console: bool = True) -> None:
        """Log error message"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        formatted_error = f"[{timestamp}] ERROR: {error_message}"
        
        if print_to_console:
            print(formatted_error)
    
    @staticmethod
    def log_warning(warning_message: str, print_to_console: bool = True) -> None:
        """Log warning message"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        formatted_warning = f"[{timestamp}] WARNING: {warning_message}"
        
        if print_to_console:
            print(formatted_warning)