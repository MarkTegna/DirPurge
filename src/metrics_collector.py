"""
Performance metrics collection for DirPurge
Provides comprehensive application performance monitoring
"""

import time
import threading
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from contextlib import contextmanager
import statistics

from .logger import get_logger

logger = get_logger()


@dataclass
class MetricValue:
    """Individual metric value with timestamp"""
    value: Union[int, float]
    timestamp: datetime = field(default_factory=datetime.now)
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class MetricSummary:
    """Summary statistics for a metric"""
    count: int
    sum: float
    min: float
    max: float
    mean: float
    median: float
    p95: float
    p99: float
    last_value: float
    last_timestamp: datetime


class MetricType:
    """Metric type constants"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class Metric:
    """Base metric class"""
    
    def __init__(self, name: str, metric_type: str, description: str = "", max_samples: int = 1000):
        self.name = name
        self.metric_type = metric_type
        self.description = description
        self.max_samples = max_samples
        self.values: deque = deque(maxlen=max_samples)
        self.labels: Dict[str, str] = {}
        self._lock = threading.Lock()
        self.created_at = datetime.now()
    
    def add_value(self, value: Union[int, float], labels: Optional[Dict[str, str]] = None):
        """Add a value to the metric"""
        with self._lock:
            metric_value = MetricValue(value=value, labels=labels or {})
            self.values.append(metric_value)
    
    def get_summary(self) -> Optional[MetricSummary]:
        """Get summary statistics for the metric"""
        with self._lock:
            if not self.values:
                return None
            
            values = [v.value for v in self.values]
            
            return MetricSummary(
                count=len(values),
                sum=sum(values),
                min=min(values),
                max=max(values),
                mean=statistics.mean(values),
                median=statistics.median(values),
                p95=self._percentile(values, 95),
                p99=self._percentile(values, 99),
                last_value=values[-1],
                last_timestamp=self.values[-1].timestamp
            )
    
    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile value"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = (percentile / 100) * (len(sorted_values) - 1)
        
        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower = sorted_values[int(index)]
            upper = sorted_values[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))
    
    def reset(self):
        """Reset metric values"""
        with self._lock:
            self.values.clear()


class Counter(Metric):
    """Counter metric - monotonically increasing value"""
    
    def __init__(self, name: str, description: str = ""):
        super().__init__(name, MetricType.COUNTER, description)
        self._value = 0
    
    def increment(self, amount: Union[int, float] = 1, labels: Optional[Dict[str, str]] = None):
        """Increment counter by amount"""
        with self._lock:
            self._value += amount
            self.add_value(self._value, labels)
    
    def get_value(self) -> Union[int, float]:
        """Get current counter value"""
        return self._value


class Gauge(Metric):
    """Gauge metric - value that can go up and down"""
    
    def __init__(self, name: str, description: str = ""):
        super().__init__(name, MetricType.GAUGE, description)
        self._value = 0
    
    def set(self, value: Union[int, float], labels: Optional[Dict[str, str]] = None):
        """Set gauge value"""
        with self._lock:
            self._value = value
            self.add_value(self._value, labels)
    
    def increment(self, amount: Union[int, float] = 1, labels: Optional[Dict[str, str]] = None):
        """Increment gauge by amount"""
        with self._lock:
            self._value += amount
            self.add_value(self._value, labels)
    
    def decrement(self, amount: Union[int, float] = 1, labels: Optional[Dict[str, str]] = None):
        """Decrement gauge by amount"""
        with self._lock:
            self._value -= amount
            self.add_value(self._value, labels)
    
    def get_value(self) -> Union[int, float]:
        """Get current gauge value"""
        return self._value


class Histogram(Metric):
    """Histogram metric - distribution of values"""
    
    def __init__(self, name: str, description: str = "", buckets: Optional[List[float]] = None):
        super().__init__(name, MetricType.HISTOGRAM, description)
        self.buckets = buckets or [0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 25.0, 50.0, 100.0]
        self.bucket_counts = defaultdict(int)
    
    def observe(self, value: Union[int, float], labels: Optional[Dict[str, str]] = None):
        """Observe a value"""
        with self._lock:
            self.add_value(value, labels)
            
            # Update bucket counts
            for bucket in self.buckets:
                if value <= bucket:
                    self.bucket_counts[bucket] += 1
    
    def get_bucket_counts(self) -> Dict[float, int]:
        """Get bucket counts"""
        return dict(self.bucket_counts)


class Timer(Metric):
    """Timer metric - measures duration of operations"""
    
    def __init__(self, name: str, description: str = ""):
        super().__init__(name, MetricType.TIMER, description)
    
    def time(self, labels: Optional[Dict[str, str]] = None):
        """Context manager for timing operations"""
        return TimerContext(self, labels)
    
    def record(self, duration: float, labels: Optional[Dict[str, str]] = None):
        """Record a duration"""
        self.add_value(duration, labels)


class TimerContext:
    """Context manager for timer operations"""
    
    def __init__(self, timer: Timer, labels: Optional[Dict[str, str]] = None):
        self.timer = timer
        self.labels = labels
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration = time.time() - self.start_time
            self.timer.record(duration, self.labels)


class MetricsCollector:
    """
    Central metrics collection and management
    """
    
    def __init__(self):
        self.metrics: Dict[str, Metric] = {}
        self._lock = threading.Lock()
        self.collection_start_time = datetime.now()
        
        # Initialize default metrics
        self._initialize_default_metrics()
        
        logger.info("MetricsCollector initialized")
    
    def _initialize_default_metrics(self):
        """Initialize default application metrics"""
        # Application metrics
        self.register_counter("app_operations_total", "Total number of operations")
        self.register_counter("app_errors_total", "Total number of errors")
        self.register_gauge("app_active_operations", "Number of active operations")
        
        # File operation metrics
        self.register_counter("files_scanned_total", "Total files scanned")
        self.register_counter("files_deleted_total", "Total files deleted")
        self.register_counter("files_preserved_total", "Total files preserved")
        self.register_timer("file_scan_duration", "Time taken to scan files")
        self.register_timer("file_delete_duration", "Time taken to delete files")
        
        # System metrics
        self.register_gauge("memory_usage_mb", "Memory usage in MB")
        self.register_gauge("cpu_usage_percent", "CPU usage percentage")
        self.register_gauge("disk_usage_percent", "Disk usage percentage")
        
        # Email metrics
        self.register_counter("emails_sent_total", "Total emails sent")
        self.register_counter("email_failures_total", "Total email failures")
        self.register_timer("email_send_duration", "Time taken to send emails")
    
    def register_counter(self, name: str, description: str = "") -> Counter:
        """Register a counter metric"""
        with self._lock:
            if name in self.metrics:
                if not isinstance(self.metrics[name], Counter):
                    raise ValueError(f"Metric {name} already exists with different type")
                return self.metrics[name]
            
            counter = Counter(name, description)
            self.metrics[name] = counter
            logger.debug(f"Registered counter metric: {name}")
            return counter
    
    def register_gauge(self, name: str, description: str = "") -> Gauge:
        """Register a gauge metric"""
        with self._lock:
            if name in self.metrics:
                if not isinstance(self.metrics[name], Gauge):
                    raise ValueError(f"Metric {name} already exists with different type")
                return self.metrics[name]
            
            gauge = Gauge(name, description)
            self.metrics[name] = gauge
            logger.debug(f"Registered gauge metric: {name}")
            return gauge
    
    def register_histogram(self, name: str, description: str = "", buckets: Optional[List[float]] = None) -> Histogram:
        """Register a histogram metric"""
        with self._lock:
            if name in self.metrics:
                if not isinstance(self.metrics[name], Histogram):
                    raise ValueError(f"Metric {name} already exists with different type")
                return self.metrics[name]
            
            histogram = Histogram(name, description, buckets)
            self.metrics[name] = histogram
            logger.debug(f"Registered histogram metric: {name}")
            return histogram
    
    def register_timer(self, name: str, description: str = "") -> Timer:
        """Register a timer metric"""
        with self._lock:
            if name in self.metrics:
                if not isinstance(self.metrics[name], Timer):
                    raise ValueError(f"Metric {name} already exists with different type")
                return self.metrics[name]
            
            timer = Timer(name, description)
            self.metrics[name] = timer
            logger.debug(f"Registered timer metric: {name}")
            return timer
    
    def get_metric(self, name: str) -> Optional[Metric]:
        """Get metric by name"""
        return self.metrics.get(name)
    
    def increment_counter(self, name: str, amount: Union[int, float] = 1, labels: Optional[Dict[str, str]] = None):
        """Increment a counter metric"""
        metric = self.get_metric(name)
        if isinstance(metric, Counter):
            metric.increment(amount, labels)
        else:
            logger.warning(f"Counter metric not found: {name}")
    
    def set_gauge(self, name: str, value: Union[int, float], labels: Optional[Dict[str, str]] = None):
        """Set a gauge metric value"""
        metric = self.get_metric(name)
        if isinstance(metric, Gauge):
            metric.set(value, labels)
        else:
            logger.warning(f"Gauge metric not found: {name}")
    
    def observe_histogram(self, name: str, value: Union[int, float], labels: Optional[Dict[str, str]] = None):
        """Observe a value in a histogram metric"""
        metric = self.get_metric(name)
        if isinstance(metric, Histogram):
            metric.observe(value, labels)
        else:
            logger.warning(f"Histogram metric not found: {name}")
    
    def time_operation(self, name: str, labels: Optional[Dict[str, str]] = None):
        """Get timer context for an operation"""
        metric = self.get_metric(name)
        if isinstance(metric, Timer):
            return metric.time(labels)
        else:
            logger.warning(f"Timer metric not found: {name}")
            return TimerContext(Timer("dummy"), labels)
    
    def record_operation_metrics(self, operation_name: str, duration: float, success: bool, **labels):
        """Record standard operation metrics"""
        operation_labels = {"operation": operation_name, **labels}
        
        # Record operation count
        self.increment_counter("app_operations_total", labels=operation_labels)
        
        # Record errors if failed
        if not success:
            self.increment_counter("app_errors_total", labels=operation_labels)
        
        # Record duration if timer exists
        timer_name = f"{operation_name}_duration"
        if timer_name in self.metrics:
            self.get_metric(timer_name).record(duration, operation_labels)
    
    def get_all_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics"""
        summary = {
            'collection_start_time': self.collection_start_time.isoformat(),
            'total_metrics': len(self.metrics),
            'metrics': {}
        }
        
        for name, metric in self.metrics.items():
            metric_summary = metric.get_summary()
            if metric_summary:
                summary['metrics'][name] = {
                    'type': metric.metric_type,
                    'description': metric.description,
                    'count': metric_summary.count,
                    'last_value': metric_summary.last_value,
                    'mean': metric_summary.mean,
                    'min': metric_summary.min,
                    'max': metric_summary.max,
                    'p95': metric_summary.p95,
                    'p99': metric_summary.p99
                }
        
        return summary
    
    def export_prometheus_format(self) -> str:
        """Export metrics in Prometheus format"""
        lines = []
        
        for name, metric in self.metrics.items():
            # Add help line
            if metric.description:
                lines.append(f"# HELP {name} {metric.description}")
            
            # Add type line
            lines.append(f"# TYPE {name} {metric.metric_type}")
            
            # Add metric values
            summary = metric.get_summary()
            if summary:
                if metric.metric_type == MetricType.COUNTER:
                    lines.append(f"{name} {summary.last_value}")
                elif metric.metric_type == MetricType.GAUGE:
                    lines.append(f"{name} {summary.last_value}")
                elif metric.metric_type == MetricType.HISTOGRAM:
                    # Add histogram buckets
                    if isinstance(metric, Histogram):
                        bucket_counts = metric.get_bucket_counts()
                        for bucket, count in bucket_counts.items():
                            lines.append(f"{name}_bucket{{le=\"{bucket}\"}} {count}")
                        lines.append(f"{name}_count {summary.count}")
                        lines.append(f"{name}_sum {summary.sum}")
                elif metric.metric_type == MetricType.TIMER:
                    lines.append(f"{name}_count {summary.count}")
                    lines.append(f"{name}_sum {summary.sum}")
                    lines.append(f"{name}_mean {summary.mean}")
                    lines.append(f"{name}_p95 {summary.p95}")
                    lines.append(f"{name}_p99 {summary.p99}")
            
            lines.append("")  # Empty line between metrics
        
        return "\n".join(lines)
    
    def reset_all_metrics(self):
        """Reset all metrics"""
        for metric in self.metrics.values():
            metric.reset()
        logger.info("Reset all metrics")


# Global metrics collector instance
metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance"""
    return metrics_collector


def timed(metric_name: str, labels: Optional[Dict[str, str]] = None):
    """
    Decorator to time function execution
    
    Args:
        metric_name: Name of the timer metric
        labels: Additional labels for the metric
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            with metrics_collector.time_operation(metric_name, labels):
                return func(*args, **kwargs)
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    
    return decorator


def counted(metric_name: str, labels: Optional[Dict[str, str]] = None):
    """
    Decorator to count function calls
    
    Args:
        metric_name: Name of the counter metric
        labels: Additional labels for the metric
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            metrics_collector.increment_counter(metric_name, labels=labels)
            return func(*args, **kwargs)
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    
    return decorator