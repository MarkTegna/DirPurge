"""Centralized error handling and validation for DirPurge"""

import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from .models import Config, EmailConfig
from .logger import get_logger
from .validators import ValidationError

logger = get_logger()


class SecurityError(Exception):
    """Raised when security validation fails"""
    pass


class ErrorHandler:
    """Centralized error handling and validation with security enhancements"""
    
    @staticmethod
    def validate_directory_access(directory_path: str) -> List[str]:
        """Validate directory exists and is accessible"""
        errors = []
        
        if not directory_path:
            errors.append("Target directory path is empty")
            return errors
        
        try:
            path = Path(directory_path).resolve()
        except (OSError, ValueError) as e:
            errors.append(f"Invalid directory path: {directory_path} - {e}")
            return errors
        
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
                logger.security_event(f"Permission denied: {directory_path}", severity="WARNING")
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
            logger.security_event(f"File permission denied: {file_path}", severity="WARNING")
            return f"Permission denied accessing file: {file_path}"
        except OSError as e:
            return f"Cannot access file {file_path}: {e}"
    
    @staticmethod
    def validate_configuration(config: Config) -> List[str]:
        """
        Validate complete configuration object with security checks
        
        Args:
            config: Configuration to validate
            
        Returns:
            List of validation errors
        """
        errors = []
        
        try:
            # Validate target directory
            if not config.target_directory:
                errors.append("Target directory is required")
            else:
                dir_errors = ErrorHandler.validate_directory_access(config.target_directory)
                errors.extend(dir_errors)
            
            # Validate numeric values
            if config.min_files_to_keep < 0:
                errors.append("Minimum files to keep must be non-negative")
            elif config.min_files_to_keep > 10000:
                errors.append("Minimum files to keep is unreasonably high (max 10000)")
                logger.security_event(f"Suspicious min_files_to_keep value: {config.min_files_to_keep}")
            
            if config.max_age_days < 0:
                errors.append("Maximum age days must be non-negative")
            elif config.max_age_days > 36500:  # 100 years
                errors.append("Maximum age days is unreasonably high (max 36500)")
                logger.security_event(f"Suspicious max_age_days value: {config.max_age_days}")
            
            # Validate reports directory
            if config.reports_directory:
                try:
                    reports_path = Path(config.reports_directory).resolve()
                    # Check if parent directory exists and is writable
                    parent = reports_path.parent
                    if not parent.exists():
                        errors.append(f"Reports directory parent does not exist: {parent}")
                    elif not os.access(parent, os.W_OK):
                        errors.append(f"Cannot write to reports directory parent: {parent}")
                        logger.security_event(f"Reports directory not writable: {parent}")
                except (OSError, ValueError) as e:
                    errors.append(f"Invalid reports directory path: {config.reports_directory} - {e}")
            
            # Validate email configuration
            if config.email_settings and config.email_settings.send_email:
                email_errors = ErrorHandler._validate_email_config(config.email_settings)
                errors.extend(email_errors)
            
            # Validate extensions
            if config.excluded_extensions:
                for ext in config.excluded_extensions:
                    if not isinstance(ext, str) or not ext.startswith('.'):
                        errors.append(f"Invalid file extension format: {ext}")
                    elif len(ext) > 10:  # Reasonable extension length limit
                        errors.append(f"File extension too long: {ext}")
                        logger.security_event(f"Suspicious file extension: {ext}")
        
        except Exception as e:
            errors.append(f"Configuration validation error: {e}")
            logger.error(f"Unexpected error during configuration validation: {e}")
        
        return errors
    
    @staticmethod
    def _validate_email_config(email_config: EmailConfig) -> List[str]:
        """
        Validate email configuration with security checks
        
        Args:
            email_config: Email configuration to validate
            
        Returns:
            List of validation errors
        """
        errors = []
        
        if not email_config.smtp_server:
            errors.append("SMTP server is required when email is enabled")
        elif len(email_config.smtp_server) > 253:
            errors.append("SMTP server name too long")
            logger.security_event(f"Suspicious SMTP server length: {len(email_config.smtp_server)}")
        
        if not email_config.from_email:
            errors.append("From email is required when email is enabled")
        elif len(email_config.from_email) > 254:
            errors.append("From email address too long")
            logger.security_event(f"Suspicious from_email length: {len(email_config.from_email)}")
        
        if not email_config.to_email:
            errors.append("To email is required when email is enabled")
        elif len(email_config.to_email) > 254:
            errors.append("To email address too long")
            logger.security_event(f"Suspicious to_email length: {len(email_config.to_email)}")
        
        if email_config.smtp_port <= 0 or email_config.smtp_port > 65535:
            errors.append("SMTP port must be between 1 and 65535")
        
        # Security checks for email credentials
        if email_config.smtp_username and len(email_config.smtp_username) > 256:
            errors.append("SMTP username too long")
            logger.security_event("Suspicious SMTP username length")
        
        if email_config.smtp_password and len(email_config.smtp_password) > 256:
            errors.append("SMTP password too long")
            logger.security_event("Suspicious SMTP password length")
        
        return errors
    
    @staticmethod
    def log_error(message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """
        Log error message with security context
        
        Args:
            message: Error message
            extra: Additional context
        """
        logger.error(message, extra=extra)
    
    @staticmethod
    def log_warning(message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """
        Log warning message with security context
        
        Args:
            message: Warning message
            extra: Additional context
        """
        logger.warning(message, extra=extra)
    
    @staticmethod
    def log_security_event(event: str, severity: str = "WARNING", **kwargs) -> None:
        """
        Log security-related events
        
        Args:
            event: Security event description
            severity: Event severity level
            **kwargs: Additional context
        """
        logger.security_event(event, severity=severity, **kwargs)
    
    @staticmethod
    def handle_file_operation_error(operation: str, file_path: Union[str, Path], error: Exception) -> str:
        """
        Handle file operation errors with security logging
        
        Args:
            operation: Operation being performed
            file_path: File path involved
            error: Exception that occurred
            
        Returns:
            Formatted error message
        """
        error_msg = f"Failed to {operation} file {file_path}: {error}"
        
        # Log security events for suspicious errors
        if isinstance(error, PermissionError):
            logger.security_event(f"Permission denied during {operation}: {file_path}")
        elif "access" in str(error).lower() or "denied" in str(error).lower():
            logger.security_event(f"Access denied during {operation}: {file_path}")
        
        logger.error(error_msg)
        return error_msg
    
    @staticmethod
    def create_safe_error_context(operation: str, **context) -> Dict[str, Any]:
        """
        Create error context with sensitive data filtering
        
        Args:
            operation: Operation being performed
            **context: Context data
            
        Returns:
            Filtered context dictionary
        """
        safe_context = {'operation': operation}
        
        # Filter sensitive keys
        sensitive_keys = {'password', 'passwd', 'secret', 'key', 'token', 'credential'}
        
        for key, value in context.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                safe_context[key] = '[REDACTED]'
            else:
                safe_context[key] = value
        
        return safe_context
    
    @staticmethod
    def validate_operation_safety(operation: str, target_path: Union[str, Path], **context) -> None:
        """
        Validate that an operation is safe to perform
        
        Args:
            operation: Operation to validate
            target_path: Target path for operation
            **context: Additional context
            
        Raises:
            SecurityError: If operation is deemed unsafe
        """
        try:
            path_obj = Path(target_path).resolve()
        except (OSError, ValueError) as e:
            raise SecurityError(f"Invalid path for {operation}: {target_path} - {e}")
        
        # Check for dangerous paths
        dangerous_patterns = [
            'system32', 'windows', 'program files', 'boot', 'recovery'
        ]
        
        path_str = str(path_obj).lower()
        for pattern in dangerous_patterns:
            if pattern in path_str:
                logger.security_event(
                    f"Dangerous path detected for {operation}: {path_obj}",
                    severity="CRITICAL"
                )
                raise SecurityError(f"Operation {operation} not allowed on system path: {path_obj}")
        
        # Log the operation for audit trail
        logger.info(f"Operation validated: {operation}", extra={
            'target_path': str(path_obj),
            **ErrorHandler.create_safe_error_context(operation, **context)
        })
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