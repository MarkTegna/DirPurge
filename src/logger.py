"""
Secure logging framework for DirPurge
Replaces print statements with structured, secure logging
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from enum import Enum


class LogLevel(Enum):
    """Log levels for DirPurge operations"""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class SecureLogger:
    """
    Secure logging implementation with:
    - Structured logging
    - Log rotation
    - Sensitive data filtering
    - Performance monitoring
    """
    
    _instance: Optional['SecureLogger'] = None
    _logger: Optional[logging.Logger] = None
    
    def __new__(cls) -> 'SecureLogger':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._logger is not None:
            return
            
        self._setup_logger()
        self._sensitive_patterns = [
            'password', 'passwd', 'pwd', 'secret', 'key', 'token',
            'credential', 'auth', 'smtp_password', 'smtp_username'
        ]
    
    def _setup_logger(self) -> None:
        """Initialize secure logger with rotation and formatting"""
        self._logger = logging.getLogger('dirpurge')
        self._logger.setLevel(logging.INFO)
        
        # Prevent duplicate handlers
        if self._logger.handlers:
            return
        
        # Create logs directory
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        # File handler with rotation
        log_file = log_dir / 'dirpurge.log'
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        
        # Secure formatter
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self._logger.addHandler(file_handler)
        self._logger.addHandler(console_handler)
    
    def _sanitize_message(self, message: str, extra: Optional[Dict[str, Any]] = None) -> str:
        """Remove sensitive information from log messages"""
        sanitized = message
        
        # Sanitize message content
        for pattern in self._sensitive_patterns:
            if pattern.lower() in sanitized.lower():
                # Replace sensitive values with [REDACTED]
                import re
                pattern_regex = rf'{pattern}["\s]*[:=]["\s]*[^"\s,}}\]]+["\s]*'
                sanitized = re.sub(pattern_regex, f'{pattern}=[REDACTED]', sanitized, flags=re.IGNORECASE)
        
        # Sanitize extra data
        if extra:
            for key, value in extra.items():
                if any(pattern.lower() in key.lower() for pattern in self._sensitive_patterns):
                    extra[key] = '[REDACTED]'
        
        return sanitized
    
    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log debug message"""
        if self._logger:
            sanitized = self._sanitize_message(message, extra)
            self._logger.debug(sanitized, extra=extra or {})
    
    def info(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log info message"""
        if self._logger:
            sanitized = self._sanitize_message(message, extra)
            self._logger.info(sanitized, extra=extra or {})
    
    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log warning message"""
        if self._logger:
            sanitized = self._sanitize_message(message, extra)
            self._logger.warning(sanitized, extra=extra or {})
    
    def error(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log error message"""
        if self._logger:
            sanitized = self._sanitize_message(message, extra)
            self._logger.error(sanitized, extra=extra or {})
    
    def critical(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log critical message"""
        if self._logger:
            sanitized = self._sanitize_message(message, extra)
            self._logger.critical(sanitized, extra=extra or {})
    
    def operation_start(self, operation: str, **kwargs) -> None:
        """Log operation start with context"""
        context = {k: v for k, v in kwargs.items() if k not in self._sensitive_patterns}
        self.info(f"OPERATION_START: {operation}", extra=context)
    
    def operation_end(self, operation: str, success: bool, duration: float, **kwargs) -> None:
        """Log operation completion with metrics"""
        status = "SUCCESS" if success else "FAILURE"
        context = {
            'duration_seconds': duration,
            'success': success,
            **{k: v for k, v in kwargs.items() if k not in self._sensitive_patterns}
        }
        self.info(f"OPERATION_END: {operation} | {status} | {duration:.2f}s", extra=context)
    
    def security_event(self, event: str, severity: str = "WARNING", **kwargs) -> None:
        """Log security-related events"""
        context = {
            'event_type': 'SECURITY',
            'severity': severity,
            **{k: v for k, v in kwargs.items() if k not in self._sensitive_patterns}
        }
        
        if severity == "CRITICAL":
            self.critical(f"SECURITY: {event}", extra=context)
        elif severity == "ERROR":
            self.error(f"SECURITY: {event}", extra=context)
        else:
            self.warning(f"SECURITY: {event}", extra=context)


# Global logger instance
logger = SecureLogger()


def get_logger() -> SecureLogger:
    """Get the global secure logger instance"""
    return logger