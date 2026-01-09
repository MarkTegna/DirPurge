"""
Input validation and sanitization for DirPurge
Provides secure validation for all user inputs
"""

import os
import re
from pathlib import Path, PurePath
from typing import List, Optional, Tuple, Union
from urllib.parse import urlparse
import ipaddress

from .logger import get_logger

logger = get_logger()


class ValidationError(Exception):
    """Raised when input validation fails"""
    pass


class PathValidator:
    """Secure path validation and sanitization"""
    
    # Dangerous path patterns
    DANGEROUS_PATTERNS = [
        r'\.\.[\\/]',  # Directory traversal
        r'^[\\/]',     # Absolute paths starting with / or \
        r'[\x00-\x1f]',  # Control characters
        r'[<>:"|?*]',  # Windows forbidden characters
        r'^\s+|\s+$',  # Leading/trailing whitespace
    ]
    
    # Reserved Windows names
    WINDOWS_RESERVED = {
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }
    
    @classmethod
    def validate_directory_path(cls, path: str, must_exist: bool = True) -> str:
        """
        Validate and sanitize directory path
        
        Args:
            path: Directory path to validate
            must_exist: Whether directory must exist
            
        Returns:
            Sanitized absolute path
            
        Raises:
            ValidationError: If path is invalid or unsafe
        """
        if not path or not isinstance(path, str):
            raise ValidationError("Directory path cannot be empty")
        
        # Check for dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, path, re.IGNORECASE):
                logger.security_event(f"Dangerous path pattern detected: {pattern}", severity="ERROR")
                raise ValidationError(f"Path contains dangerous pattern: {path}")
        
        # Convert to Path object for normalization
        try:
            path_obj = Path(path).resolve()
        except (OSError, ValueError) as e:
            raise ValidationError(f"Invalid path format: {path} - {e}")
        
        # Check path length (Windows MAX_PATH limitation)
        if len(str(path_obj)) > 260:
            raise ValidationError(f"Path too long (max 260 characters): {path}")
        
        # Check for reserved names
        for part in path_obj.parts:
            if part.upper().split('.')[0] in cls.WINDOWS_RESERVED:
                raise ValidationError(f"Path contains reserved name: {part}")
        
        # Existence check
        if must_exist:
            if not path_obj.exists():
                raise ValidationError(f"Directory does not exist: {path_obj}")
            if not path_obj.is_dir():
                raise ValidationError(f"Path is not a directory: {path_obj}")
        
        # Permission check
        if path_obj.exists():
            try:
                # Test read access
                list(path_obj.iterdir())
            except PermissionError:
                raise ValidationError(f"Permission denied accessing directory: {path_obj}")
            except OSError as e:
                raise ValidationError(f"Cannot access directory: {path_obj} - {e}")
        
        return str(path_obj)
    
    @classmethod
    def validate_file_path(cls, path: Union[str, Path]) -> Path:
        """
        Validate file path for safety
        
        Args:
            path: File path to validate
            
        Returns:
            Validated Path object
            
        Raises:
            ValidationError: If path is invalid or unsafe
        """
        if not path:
            raise ValidationError("File path cannot be empty")
        
        path_str = str(path)
        
        # Check for dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, path_str, re.IGNORECASE):
                logger.security_event(f"Dangerous file path pattern: {pattern}", severity="ERROR")
                raise ValidationError(f"File path contains dangerous pattern: {path_str}")
        
        try:
            path_obj = Path(path_str).resolve()
        except (OSError, ValueError) as e:
            raise ValidationError(f"Invalid file path format: {path_str} - {e}")
        
        # Check path length
        if len(str(path_obj)) > 260:
            raise ValidationError(f"File path too long (max 260 characters): {path_str}")
        
        return path_obj


class ConfigValidator:
    """Configuration value validation"""
    
    @staticmethod
    def validate_integer(value: Union[str, int], min_val: int = 0, max_val: int = 2**31-1, name: str = "value") -> int:
        """
        Validate integer configuration value
        
        Args:
            value: Value to validate
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            name: Name for error messages
            
        Returns:
            Validated integer
            
        Raises:
            ValidationError: If value is invalid
        """
        try:
            int_val = int(value)
        except (ValueError, TypeError):
            raise ValidationError(f"{name} must be a valid integer: {value}")
        
        if int_val < min_val:
            raise ValidationError(f"{name} must be >= {min_val}: {int_val}")
        
        if int_val > max_val:
            raise ValidationError(f"{name} must be <= {max_val}: {int_val}")
        
        return int_val
    
    @staticmethod
    def validate_boolean(value: Union[str, bool], name: str = "value") -> bool:
        """
        Validate boolean configuration value
        
        Args:
            value: Value to validate
            name: Name for error messages
            
        Returns:
            Validated boolean
            
        Raises:
            ValidationError: If value is invalid
        """
        if isinstance(value, bool):
            return value
        
        if isinstance(value, str):
            lower_val = value.lower().strip()
            if lower_val in ('true', '1', 'yes', 'on'):
                return True
            elif lower_val in ('false', '0', 'no', 'off'):
                return False
        
        raise ValidationError(f"{name} must be a valid boolean: {value}")
    
    @staticmethod
    def validate_extensions(extensions: Union[str, List[str]]) -> List[str]:
        """
        Validate file extensions list
        
        Args:
            extensions: Extensions to validate
            
        Returns:
            Validated extensions list
            
        Raises:
            ValidationError: If extensions are invalid
        """
        if isinstance(extensions, str):
            if not extensions.strip():
                return []
            ext_list = [ext.strip() for ext in extensions.split(',')]
        elif isinstance(extensions, list):
            ext_list = [str(ext).strip() for ext in extensions]
        else:
            raise ValidationError(f"Extensions must be string or list: {type(extensions)}")
        
        validated = []
        for ext in ext_list:
            if not ext:
                continue
            
            # Ensure extension starts with dot
            if not ext.startswith('.'):
                ext = '.' + ext
            
            # Validate extension format
            if not re.match(r'^\.[a-zA-Z0-9]+$', ext):
                raise ValidationError(f"Invalid file extension format: {ext}")
            
            # Convert to uppercase for consistency
            validated.append(ext.upper())
        
        return validated


class EmailValidator:
    """Email configuration validation"""
    
    @staticmethod
    def validate_email_address(email: str, name: str = "email") -> str:
        """
        Validate email address format
        
        Args:
            email: Email address to validate
            name: Name for error messages
            
        Returns:
            Validated email address
            
        Raises:
            ValidationError: If email is invalid
        """
        if not email or not isinstance(email, str):
            raise ValidationError(f"{name} cannot be empty")
        
        email = email.strip()
        
        # Basic email format validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValidationError(f"Invalid {name} format: {email}")
        
        # Check length limits
        if len(email) > 254:  # RFC 5321 limit
            raise ValidationError(f"{name} too long (max 254 characters): {email}")
        
        local, domain = email.rsplit('@', 1)
        if len(local) > 64:  # RFC 5321 limit
            raise ValidationError(f"{name} local part too long (max 64 characters): {local}")
        
        return email
    
    @staticmethod
    def validate_smtp_server(server: str) -> str:
        """
        Validate SMTP server hostname/IP
        
        Args:
            server: SMTP server to validate
            
        Returns:
            Validated server
            
        Raises:
            ValidationError: If server is invalid
        """
        if not server or not isinstance(server, str):
            raise ValidationError("SMTP server cannot be empty")
        
        server = server.strip()
        
        # Check if it's an IP address
        try:
            ipaddress.ip_address(server)
            return server
        except ValueError:
            pass
        
        # Validate hostname format
        hostname_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
        if not re.match(hostname_pattern, server):
            raise ValidationError(f"Invalid SMTP server format: {server}")
        
        # Check length
        if len(server) > 253:  # RFC 1035 limit
            raise ValidationError(f"SMTP server name too long (max 253 characters): {server}")
        
        return server
    
    @staticmethod
    def validate_smtp_port(port: Union[str, int]) -> int:
        """
        Validate SMTP port number
        
        Args:
            port: Port to validate
            
        Returns:
            Validated port number
            
        Raises:
            ValidationError: If port is invalid
        """
        try:
            port_int = int(port)
        except (ValueError, TypeError):
            raise ValidationError(f"SMTP port must be a valid integer: {port}")
        
        if port_int < 1 or port_int > 65535:
            raise ValidationError(f"SMTP port must be between 1 and 65535: {port_int}")
        
        # Warn about non-standard ports
        standard_ports = {25, 465, 587, 2525}
        if port_int not in standard_ports:
            logger.warning(f"Non-standard SMTP port: {port_int}")
        
        return port_int


def validate_all_inputs(config_dict: dict) -> dict:
    """
    Validate all configuration inputs
    
    Args:
        config_dict: Configuration dictionary to validate
        
    Returns:
        Validated configuration dictionary
        
    Raises:
        ValidationError: If any validation fails
    """
    validated = {}
    
    # Validate target directory
    if 'target_directory' in config_dict:
        validated['target_directory'] = PathValidator.validate_directory_path(
            config_dict['target_directory'], must_exist=True
        )
    
    # Validate numeric values
    if 'min_files_to_keep' in config_dict:
        validated['min_files_to_keep'] = ConfigValidator.validate_integer(
            config_dict['min_files_to_keep'], min_val=0, max_val=10000, name="min_files_to_keep"
        )
    
    if 'max_age_days' in config_dict:
        validated['max_age_days'] = ConfigValidator.validate_integer(
            config_dict['max_age_days'], min_val=0, max_val=36500, name="max_age_days"
        )
    
    # Validate boolean values
    if 'dry_run' in config_dict:
        validated['dry_run'] = ConfigValidator.validate_boolean(
            config_dict['dry_run'], name="dry_run"
        )
    
    if 'generate_xlsx' in config_dict:
        validated['generate_xlsx'] = ConfigValidator.validate_boolean(
            config_dict['generate_xlsx'], name="generate_xlsx"
        )
    
    # Validate extensions
    if 'excluded_extensions' in config_dict:
        validated['excluded_extensions'] = ConfigValidator.validate_extensions(
            config_dict['excluded_extensions']
        )
    
    # Validate reports directory
    if 'reports_directory' in config_dict:
        validated['reports_directory'] = PathValidator.validate_directory_path(
            config_dict['reports_directory'], must_exist=False
        )
    
    # Validate email settings
    if 'email_settings' in config_dict and config_dict['email_settings']:
        email_config = config_dict['email_settings']
        validated_email = {}
        
        if hasattr(email_config, 'send_email'):
            validated_email['send_email'] = ConfigValidator.validate_boolean(
                email_config.send_email, name="send_email"
            )
        
        if hasattr(email_config, 'smtp_server') and email_config.smtp_server:
            validated_email['smtp_server'] = EmailValidator.validate_smtp_server(
                email_config.smtp_server
            )
        
        if hasattr(email_config, 'smtp_port'):
            validated_email['smtp_port'] = EmailValidator.validate_smtp_port(
                email_config.smtp_port
            )
        
        if hasattr(email_config, 'from_email') and email_config.from_email:
            validated_email['from_email'] = EmailValidator.validate_email_address(
                email_config.from_email, name="from_email"
            )
        
        if hasattr(email_config, 'to_email') and email_config.to_email:
            validated_email['to_email'] = EmailValidator.validate_email_address(
                email_config.to_email, name="to_email"
            )
        
        # Copy other email settings
        for attr in ['smtp_use_tls', 'smtp_username', 'smtp_password']:
            if hasattr(email_config, attr):
                validated_email[attr] = getattr(email_config, attr)
        
        validated['email_settings'] = validated_email
    
    # Copy other settings
    for key, value in config_dict.items():
        if key not in validated:
            validated[key] = value
    
    return validated