"""
Health monitoring and system checks for DirPurge
Provides comprehensive system health monitoring and diagnostics
"""

import time
import psutil
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from .logger import get_logger

logger = get_logger()


class HealthStatus(Enum):
    """Health check status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check"""
    name: str
    status: HealthStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: float = 0.0


@dataclass
class SystemMetrics:
    """System performance metrics"""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_free_gb: float
    process_count: int
    uptime_seconds: float
    timestamp: datetime = field(default_factory=datetime.now)


class HealthCheck:
    """Base class for health checks"""
    
    def __init__(self, name: str, timeout_seconds: int = 30):
        self.name = name
        self.timeout_seconds = timeout_seconds
    
    def execute(self) -> HealthCheckResult:
        """Execute the health check"""
        start_time = time.time()
        
        try:
            result = self._perform_check()
            duration_ms = (time.time() - start_time) * 1000
            result.duration_ms = duration_ms
            return result
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.CRITICAL,
                message=f"Health check failed: {e}",
                duration_ms=duration_ms
            )
    
    def _perform_check(self) -> HealthCheckResult:
        """Override this method to implement specific health check logic"""
        raise NotImplementedError


class SystemResourcesHealthCheck(HealthCheck):
    """Health check for system resources"""
    
    def __init__(self, cpu_warning_threshold: float = 80.0, memory_warning_threshold: float = 85.0):
        super().__init__("system_resources")
        self.cpu_warning_threshold = cpu_warning_threshold
        self.memory_warning_threshold = memory_warning_threshold
    
    def _perform_check(self) -> HealthCheckResult:
        """Check system resource usage"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        status = HealthStatus.HEALTHY
        messages = []
        
        # Check CPU usage
        if cpu_percent > self.cpu_warning_threshold:
            status = HealthStatus.WARNING
            messages.append(f"High CPU usage: {cpu_percent:.1f}%")
        
        # Check memory usage
        if memory.percent > self.memory_warning_threshold:
            if status != HealthStatus.CRITICAL:
                status = HealthStatus.WARNING
            messages.append(f"High memory usage: {memory.percent:.1f}%")
        
        # Critical thresholds
        if cpu_percent > 95:
            status = HealthStatus.CRITICAL
        if memory.percent > 95:
            status = HealthStatus.CRITICAL
        
        message = "; ".join(messages) if messages else "System resources normal"
        
        return HealthCheckResult(
            name=self.name,
            status=status,
            message=message,
            details={
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_used_gb': memory.used / (1024**3),
                'memory_available_gb': memory.available / (1024**3)
            }
        )


class DiskSpaceHealthCheck(HealthCheck):
    """Health check for disk space"""
    
    def __init__(self, path: str = ".", warning_threshold_percent: float = 85.0):
        super().__init__("disk_space")
        self.path = path
        self.warning_threshold_percent = warning_threshold_percent
    
    def _perform_check(self) -> HealthCheckResult:
        """Check disk space availability"""
        try:
            disk_usage = psutil.disk_usage(self.path)
            usage_percent = (disk_usage.used / disk_usage.total) * 100
            free_gb = disk_usage.free / (1024**3)
            
            status = HealthStatus.HEALTHY
            message = f"Disk usage normal: {usage_percent:.1f}% used"
            
            if usage_percent > self.warning_threshold_percent:
                status = HealthStatus.WARNING
                message = f"Low disk space: {usage_percent:.1f}% used, {free_gb:.1f}GB free"
            
            if usage_percent > 95:
                status = HealthStatus.CRITICAL
                message = f"Critical disk space: {usage_percent:.1f}% used, {free_gb:.1f}GB free"
            
            return HealthCheckResult(
                name=self.name,
                status=status,
                message=message,
                details={
                    'usage_percent': usage_percent,
                    'free_gb': free_gb,
                    'total_gb': disk_usage.total / (1024**3),
                    'path': self.path
                }
            )
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.CRITICAL,
                message=f"Cannot check disk space: {e}"
            )


class DirectoryAccessHealthCheck(HealthCheck):
    """Health check for directory access"""
    
    def __init__(self, directory_path: str):
        super().__init__(f"directory_access_{Path(directory_path).name}")
        self.directory_path = directory_path
    
    def _perform_check(self) -> HealthCheckResult:
        """Check directory accessibility"""
        try:
            path = Path(self.directory_path)
            
            if not path.exists():
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.CRITICAL,
                    message=f"Directory does not exist: {self.directory_path}"
                )
            
            if not path.is_dir():
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.CRITICAL,
                    message=f"Path is not a directory: {self.directory_path}"
                )
            
            # Test read access
            file_count = len(list(path.iterdir()))
            
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.HEALTHY,
                message=f"Directory accessible: {file_count} items",
                details={
                    'path': str(path),
                    'file_count': file_count
                }
            )
            
        except PermissionError:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.CRITICAL,
                message=f"Permission denied accessing directory: {self.directory_path}"
            )
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.CRITICAL,
                message=f"Cannot access directory: {e}"
            )


class EmailConnectivityHealthCheck(HealthCheck):
    """Health check for email connectivity"""
    
    def __init__(self, smtp_server: str, smtp_port: int, use_tls: bool = False):
        super().__init__("email_connectivity")
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.use_tls = use_tls
    
    def _perform_check(self) -> HealthCheckResult:
        """Check SMTP server connectivity"""
        try:
            import smtplib
            import socket
            
            # Test connection
            if self.use_tls:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=10)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10)
            
            server.quit()
            
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.HEALTHY,
                message=f"SMTP server accessible: {self.smtp_server}:{self.smtp_port}",
                details={
                    'smtp_server': self.smtp_server,
                    'smtp_port': self.smtp_port,
                    'use_tls': self.use_tls
                }
            )
            
        except socket.timeout:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.WARNING,
                message=f"SMTP server timeout: {self.smtp_server}:{self.smtp_port}"
            )
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.WARNING,
                message=f"SMTP server not accessible: {e}"
            )


class HealthMonitor:
    """
    Comprehensive health monitoring system
    """
    
    def __init__(self):
        self.health_checks: List[HealthCheck] = []
        self.metrics_history: List[SystemMetrics] = []
        self.max_history_size = 100
        self.last_check_time: Optional[datetime] = None
        self.last_results: List[HealthCheckResult] = []
        self._lock = threading.Lock()
        
        # Add default health checks
        self._add_default_checks()
        
        logger.info("HealthMonitor initialized")
    
    def _add_default_checks(self):
        """Add default system health checks"""
        self.add_health_check(SystemResourcesHealthCheck())
        self.add_health_check(DiskSpaceHealthCheck())
    
    def add_health_check(self, health_check: HealthCheck):
        """Add a health check to the monitor"""
        with self._lock:
            self.health_checks.append(health_check)
        logger.debug(f"Added health check: {health_check.name}")
    
    def remove_health_check(self, name: str):
        """Remove a health check by name"""
        with self._lock:
            self.health_checks = [hc for hc in self.health_checks if hc.name != name]
        logger.debug(f"Removed health check: {name}")
    
    def run_health_checks(self) -> List[HealthCheckResult]:
        """
        Run all health checks
        
        Returns:
            List of health check results
        """
        results = []
        
        logger.debug("Running health checks")
        
        for health_check in self.health_checks:
            try:
                result = health_check.execute()
                results.append(result)
                
                # Log significant health issues
                if result.status == HealthStatus.CRITICAL:
                    logger.error(f"Health check CRITICAL: {result.name} - {result.message}")
                elif result.status == HealthStatus.WARNING:
                    logger.warning(f"Health check WARNING: {result.name} - {result.message}")
                else:
                    logger.debug(f"Health check OK: {result.name}")
                    
            except Exception as e:
                logger.error(f"Health check failed: {health_check.name} - {e}")
                results.append(HealthCheckResult(
                    name=health_check.name,
                    status=HealthStatus.CRITICAL,
                    message=f"Health check execution failed: {e}"
                ))
        
        with self._lock:
            self.last_results = results
            self.last_check_time = datetime.now()
        
        return results
    
    def get_overall_health_status(self) -> HealthStatus:
        """
        Get overall system health status
        
        Returns:
            Overall health status
        """
        if not self.last_results:
            return HealthStatus.UNKNOWN
        
        # Determine overall status based on worst individual status
        has_critical = any(r.status == HealthStatus.CRITICAL for r in self.last_results)
        has_warning = any(r.status == HealthStatus.WARNING for r in self.last_results)
        
        if has_critical:
            return HealthStatus.CRITICAL
        elif has_warning:
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY
    
    def collect_system_metrics(self) -> SystemMetrics:
        """
        Collect current system metrics
        
        Returns:
            Current system metrics
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('.')
            
            metrics = SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_mb=memory.used / (1024**2),
                memory_available_mb=memory.available / (1024**2),
                disk_usage_percent=(disk.used / disk.total) * 100,
                disk_free_gb=disk.free / (1024**3),
                process_count=len(psutil.pids()),
                uptime_seconds=time.time() - psutil.boot_time()
            )
            
            # Store in history
            with self._lock:
                self.metrics_history.append(metrics)
                if len(self.metrics_history) > self.max_history_size:
                    self.metrics_history.pop(0)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            return SystemMetrics(
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_mb=0.0,
                memory_available_mb=0.0,
                disk_usage_percent=0.0,
                disk_free_gb=0.0,
                process_count=0,
                uptime_seconds=0.0
            )
    
    def get_health_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive health summary
        
        Returns:
            Health summary dictionary
        """
        overall_status = self.get_overall_health_status()
        current_metrics = self.collect_system_metrics()
        
        summary = {
            'overall_status': overall_status.value,
            'last_check_time': self.last_check_time.isoformat() if self.last_check_time else None,
            'health_checks': [
                {
                    'name': result.name,
                    'status': result.status.value,
                    'message': result.message,
                    'duration_ms': result.duration_ms,
                    'details': result.details
                }
                for result in self.last_results
            ],
            'system_metrics': {
                'cpu_percent': current_metrics.cpu_percent,
                'memory_percent': current_metrics.memory_percent,
                'memory_used_mb': current_metrics.memory_used_mb,
                'memory_available_mb': current_metrics.memory_available_mb,
                'disk_usage_percent': current_metrics.disk_usage_percent,
                'disk_free_gb': current_metrics.disk_free_gb,
                'process_count': current_metrics.process_count,
                'uptime_seconds': current_metrics.uptime_seconds
            }
        }
        
        return summary
    
    def configure_for_application(self, target_directory: Optional[str] = None, 
                                 smtp_server: Optional[str] = None, 
                                 smtp_port: Optional[int] = None,
                                 smtp_use_tls: bool = False):
        """
        Configure health checks for specific application settings
        
        Args:
            target_directory: Target directory to monitor
            smtp_server: SMTP server to check
            smtp_port: SMTP port to check
            smtp_use_tls: Whether SMTP uses TLS
        """
        # Add directory access check if specified
        if target_directory:
            self.add_health_check(DirectoryAccessHealthCheck(target_directory))
        
        # Add email connectivity check if specified
        if smtp_server and smtp_port:
            self.add_health_check(EmailConnectivityHealthCheck(smtp_server, smtp_port, smtp_use_tls))
        
        logger.info("Health monitor configured for application")
    
    def start_background_monitoring(self, interval_seconds: int = 60):
        """
        Start background health monitoring
        
        Args:
            interval_seconds: Monitoring interval in seconds
        """
        def monitor_loop():
            while True:
                try:
                    self.run_health_checks()
                    self.collect_system_metrics()
                    time.sleep(interval_seconds)
                except Exception as e:
                    logger.error(f"Background monitoring error: {e}")
                    time.sleep(interval_seconds)
        
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        
        logger.info(f"Background health monitoring started (interval: {interval_seconds}s)")


# Global health monitor instance
health_monitor = HealthMonitor()


def get_health_monitor() -> HealthMonitor:
    """Get the global health monitor instance"""
    return health_monitor