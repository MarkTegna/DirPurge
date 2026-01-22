"""
Resource management and limits for DirPurge
Provides protection against resource exhaustion and runaway operations
"""

import time
import threading
import psutil
from contextlib import contextmanager
from typing import Optional, Callable, Any, Dict
from dataclasses import dataclass
from pathlib import Path

from .logger import get_logger

logger = get_logger()


@dataclass
class ResourceLimits:
    """Resource limit configuration"""
    max_memory_mb: int = 512  # Maximum memory usage in MB
    max_files_per_scan: int = 200000  # Maximum files to process in one scan
    max_operation_time_seconds: int = 3600  # Maximum operation time (1 hour)
    max_concurrent_operations: int = 1  # Maximum concurrent file operations
    scan_timeout_seconds: int = 300  # Directory scan timeout (5 minutes)
    email_timeout_seconds: int = 30  # Email send timeout
    file_operation_timeout_seconds: int = 10  # Individual file operation timeout


class ResourceExhaustionError(Exception):
    """Raised when resource limits are exceeded"""
    pass


class OperationTimeoutError(Exception):
    """Raised when operation times out"""
    pass


class ResourceManager:
    """
    Manages system resources and enforces limits
    """
    
    def __init__(self, limits: Optional[ResourceLimits] = None):
        self.limits = limits or ResourceLimits()
        self._operation_count = 0
        self._operation_lock = threading.Lock()
        self._start_time = time.time()
        self._initial_memory = self._get_memory_usage()
        
        logger.info("ResourceManager initialized", extra={
            'max_memory_mb': self.limits.max_memory_mb,
            'max_files_per_scan': self.limits.max_files_per_scan,
            'max_operation_time_seconds': self.limits.max_operation_time_seconds
        })
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return 0.0
    
    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage"""
        try:
            return psutil.cpu_percent(interval=0.1)
        except Exception:
            return 0.0
    
    def check_memory_limit(self) -> None:
        """
        Check if memory usage is within limits
        
        Raises:
            ResourceExhaustionError: If memory limit exceeded
        """
        current_memory = self._get_memory_usage()
        memory_increase = current_memory - self._initial_memory
        
        if memory_increase > self.limits.max_memory_mb:
            logger.security_event(
                f"Memory limit exceeded: {memory_increase:.1f}MB > {self.limits.max_memory_mb}MB",
                severity="ERROR"
            )
            raise ResourceExhaustionError(
                f"Memory usage exceeded limit: {memory_increase:.1f}MB > {self.limits.max_memory_mb}MB"
            )
    
    def check_operation_time_limit(self) -> None:
        """
        Check if total operation time is within limits
        
        Raises:
            OperationTimeoutError: If operation time limit exceeded
        """
        elapsed = time.time() - self._start_time
        
        if elapsed > self.limits.max_operation_time_seconds:
            logger.security_event(
                f"Operation time limit exceeded: {elapsed:.1f}s > {self.limits.max_operation_time_seconds}s",
                severity="ERROR"
            )
            raise OperationTimeoutError(
                f"Operation time exceeded limit: {elapsed:.1f}s > {self.limits.max_operation_time_seconds}s"
            )
    
    def check_file_count_limit(self, file_count: int) -> None:
        """
        Check if file count is within limits
        
        Args:
            file_count: Number of files to process
            
        Raises:
            ResourceExhaustionError: If file count limit exceeded
        """
        if file_count > self.limits.max_files_per_scan:
            logger.security_event(
                f"File count limit exceeded: {file_count} > {self.limits.max_files_per_scan}",
                severity="ERROR"
            )
            raise ResourceExhaustionError(
                f"File count exceeded limit: {file_count} > {self.limits.max_files_per_scan}"
            )
    
    @contextmanager
    def operation_context(self, operation_name: str):
        """
        Context manager for tracking operations with resource limits
        
        Args:
            operation_name: Name of the operation for logging
            
        Yields:
            ResourceManager instance
            
        Raises:
            ResourceExhaustionError: If concurrent operation limit exceeded
        """
        with self._operation_lock:
            if self._operation_count >= self.limits.max_concurrent_operations:
                raise ResourceExhaustionError(
                    f"Concurrent operation limit exceeded: {self._operation_count} >= {self.limits.max_concurrent_operations}"
                )
            self._operation_count += 1
        
        start_time = time.time()
        logger.operation_start(operation_name, concurrent_operations=self._operation_count)
        
        try:
            yield self
        finally:
            with self._operation_lock:
                self._operation_count -= 1
            
            duration = time.time() - start_time
            logger.operation_end(operation_name, True, duration, concurrent_operations=self._operation_count)
    
    @contextmanager
    def timeout_context(self, timeout_seconds: int, operation_name: str = "operation"):
        """
        Context manager for operation timeouts
        
        Args:
            timeout_seconds: Timeout in seconds
            operation_name: Name of the operation for logging
            
        Yields:
            None
            
        Raises:
            OperationTimeoutError: If operation times out
        """
        start_time = time.time()
        
        def check_timeout():
            elapsed = time.time() - start_time
            if elapsed > timeout_seconds:
                raise OperationTimeoutError(
                    f"{operation_name} timed out after {elapsed:.1f}s (limit: {timeout_seconds}s)"
                )
        
        try:
            yield check_timeout
        except OperationTimeoutError:
            logger.error(f"Operation timeout: {operation_name} after {timeout_seconds}s")
            raise
    
    def monitor_resources(self) -> Dict[str, Any]:
        """
        Get current resource usage metrics
        
        Returns:
            Dictionary with resource usage information
        """
        current_memory = self._get_memory_usage()
        memory_increase = current_memory - self._initial_memory
        elapsed_time = time.time() - self._start_time
        cpu_usage = self._get_cpu_usage()
        
        metrics = {
            'memory_usage_mb': current_memory,
            'memory_increase_mb': memory_increase,
            'memory_limit_mb': self.limits.max_memory_mb,
            'memory_usage_percent': (memory_increase / self.limits.max_memory_mb) * 100,
            'elapsed_time_seconds': elapsed_time,
            'time_limit_seconds': self.limits.max_operation_time_seconds,
            'time_usage_percent': (elapsed_time / self.limits.max_operation_time_seconds) * 100,
            'cpu_usage_percent': cpu_usage,
            'concurrent_operations': self._operation_count,
            'max_concurrent_operations': self.limits.max_concurrent_operations
        }
        
        return metrics
    
    def log_resource_status(self) -> None:
        """Log current resource usage status"""
        metrics = self.monitor_resources()
        
        logger.info("Resource status", extra=metrics)
        
        # Warn if approaching limits
        if metrics['memory_usage_percent'] > 80:
            logger.warning(f"Memory usage high: {metrics['memory_usage_percent']:.1f}%")
        
        if metrics['time_usage_percent'] > 80:
            logger.warning(f"Operation time high: {metrics['time_usage_percent']:.1f}%")
    
    def enforce_periodic_checks(self) -> None:
        """
        Perform periodic resource checks
        Should be called regularly during long operations
        """
        self.check_memory_limit()
        self.check_operation_time_limit()
        
        # Log status every 10% of time limit
        elapsed = time.time() - self._start_time
        time_percent = (elapsed / self.limits.max_operation_time_seconds) * 100
        
        if int(time_percent) % 10 == 0 and int(time_percent) > 0:
            self.log_resource_status()


class RateLimiter:
    """
    Rate limiter for file operations to prevent system overload
    """
    
    def __init__(self, max_operations_per_second: int = 100):
        self.max_ops_per_second = max_operations_per_second
        self.min_interval = 1.0 / max_operations_per_second
        self.last_operation_time = 0.0
        self._lock = threading.Lock()
    
    def wait_if_needed(self) -> None:
        """Wait if necessary to respect rate limit"""
        with self._lock:
            current_time = time.time()
            time_since_last = current_time - self.last_operation_time
            
            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                time.sleep(sleep_time)
            
            self.last_operation_time = time.time()


def with_resource_limits(limits: Optional[ResourceLimits] = None):
    """
    Decorator to add resource limits to functions
    
    Args:
        limits: Resource limits to enforce
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            resource_manager = ResourceManager(limits)
            
            with resource_manager.operation_context(func.__name__):
                try:
                    result = func(*args, **kwargs)
                    resource_manager.log_resource_status()
                    return result
                except Exception as e:
                    logger.error(f"Function {func.__name__} failed: {e}")
                    resource_manager.log_resource_status()
                    raise
        
        return wrapper
    return decorator


def with_timeout(timeout_seconds: int):
    """
    Decorator to add timeout to functions
    
    Args:
        timeout_seconds: Timeout in seconds
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            resource_manager = ResourceManager()
            
            with resource_manager.timeout_context(timeout_seconds, func.__name__):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator