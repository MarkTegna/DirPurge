"""
Circuit breaker pattern implementation for DirPurge
Provides fault tolerance for external service calls
"""

import time
import threading
from typing import Callable, Any, Optional, Dict, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

from .logger import get_logger

logger = get_logger()


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, blocking calls
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5  # Number of failures before opening
    recovery_timeout: int = 60  # Seconds before trying half-open
    success_threshold: int = 3  # Successes needed to close from half-open
    timeout: int = 30  # Call timeout in seconds
    expected_exceptions: tuple = (Exception,)  # Exceptions that count as failures


@dataclass
class CircuitBreakerMetrics:
    """Circuit breaker metrics"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    timeouts: int = 0
    circuit_opened_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    current_state: CircuitState = CircuitState.CLOSED
    consecutive_failures: int = 0
    consecutive_successes: int = 0


class CircuitBreakerOpenException(Exception):
    """Raised when circuit breaker is open"""
    pass


class CircuitBreakerTimeoutException(Exception):
    """Raised when circuit breaker call times out"""
    pass


class CircuitBreaker:
    """
    Circuit breaker implementation for fault tolerance
    """
    
    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.metrics = CircuitBreakerMetrics()
        self.last_failure_time: Optional[float] = None
        self._lock = threading.Lock()
        
        logger.info(f"CircuitBreaker '{name}' initialized", extra={
            'failure_threshold': self.config.failure_threshold,
            'recovery_timeout': self.config.recovery_timeout,
            'success_threshold': self.config.success_threshold
        })
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpenException: If circuit is open
            CircuitBreakerTimeoutException: If call times out
            Exception: Original exception from function
        """
        with self._lock:
            self.metrics.total_calls += 1
            
            # Check if circuit should transition states
            self._update_state()
            
            # Block calls if circuit is open
            if self.state == CircuitState.OPEN:
                self.metrics.failed_calls += 1
                logger.warning(f"CircuitBreaker '{self.name}' is OPEN, blocking call")
                raise CircuitBreakerOpenException(f"Circuit breaker '{self.name}' is open")
        
        # Execute the call
        start_time = time.time()
        
        try:
            # Set up timeout if configured
            if self.config.timeout > 0:
                result = self._call_with_timeout(func, *args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Record success
            self._record_success()
            
            duration = time.time() - start_time
            logger.debug(f"CircuitBreaker '{self.name}' call succeeded", extra={
                'duration_seconds': duration
            })
            
            return result
            
        except self.config.expected_exceptions as e:
            # Record failure
            self._record_failure(e)
            
            duration = time.time() - start_time
            logger.warning(f"CircuitBreaker '{self.name}' call failed", extra={
                'duration_seconds': duration,
                'error': str(e)
            })
            
            raise
    
    def _call_with_timeout(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with timeout"""
        import concurrent.futures
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(func, *args, **kwargs)
            
            try:
                return future.result(timeout=self.config.timeout)
            except concurrent.futures.TimeoutError:
                self.metrics.timeouts += 1
                raise CircuitBreakerTimeoutException(
                    f"Call to '{self.name}' timed out after {self.config.timeout} seconds"
                )
    
    def _record_success(self):
        """Record a successful call"""
        with self._lock:
            self.metrics.successful_calls += 1
            self.metrics.consecutive_successes += 1
            self.metrics.consecutive_failures = 0
            self.metrics.last_success_time = datetime.now()
            
            # Transition from half-open to closed if enough successes
            if (self.state == CircuitState.HALF_OPEN and 
                self.metrics.consecutive_successes >= self.config.success_threshold):
                self._transition_to_closed()
    
    def _record_failure(self, exception: Exception):
        """Record a failed call"""
        with self._lock:
            self.metrics.failed_calls += 1
            self.metrics.consecutive_failures += 1
            self.metrics.consecutive_successes = 0
            self.metrics.last_failure_time = datetime.now()
            self.last_failure_time = time.time()
            
            # Transition to open if failure threshold reached
            if (self.state == CircuitState.CLOSED and 
                self.metrics.consecutive_failures >= self.config.failure_threshold):
                self._transition_to_open()
            elif self.state == CircuitState.HALF_OPEN:
                # Go back to open on any failure in half-open state
                self._transition_to_open()
    
    def _update_state(self):
        """Update circuit breaker state based on current conditions"""
        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if (self.last_failure_time and 
                time.time() - self.last_failure_time >= self.config.recovery_timeout):
                self._transition_to_half_open()
    
    def _transition_to_open(self):
        """Transition circuit breaker to open state"""
        self.state = CircuitState.OPEN
        self.metrics.current_state = CircuitState.OPEN
        self.metrics.circuit_opened_count += 1
        
        logger.warning(f"CircuitBreaker '{self.name}' transitioned to OPEN", extra={
            'consecutive_failures': self.metrics.consecutive_failures,
            'failure_threshold': self.config.failure_threshold
        })
    
    def _transition_to_half_open(self):
        """Transition circuit breaker to half-open state"""
        self.state = CircuitState.HALF_OPEN
        self.metrics.current_state = CircuitState.HALF_OPEN
        self.metrics.consecutive_successes = 0
        
        logger.info(f"CircuitBreaker '{self.name}' transitioned to HALF_OPEN")
    
    def _transition_to_closed(self):
        """Transition circuit breaker to closed state"""
        self.state = CircuitState.CLOSED
        self.metrics.current_state = CircuitState.CLOSED
        self.metrics.consecutive_failures = 0
        
        logger.info(f"CircuitBreaker '{self.name}' transitioned to CLOSED", extra={
            'consecutive_successes': self.metrics.consecutive_successes
        })
    
    def get_state(self) -> CircuitState:
        """Get current circuit breaker state"""
        return self.state
    
    def get_metrics(self) -> CircuitBreakerMetrics:
        """Get circuit breaker metrics"""
        with self._lock:
            return CircuitBreakerMetrics(
                total_calls=self.metrics.total_calls,
                successful_calls=self.metrics.successful_calls,
                failed_calls=self.metrics.failed_calls,
                timeouts=self.metrics.timeouts,
                circuit_opened_count=self.metrics.circuit_opened_count,
                last_failure_time=self.metrics.last_failure_time,
                last_success_time=self.metrics.last_success_time,
                current_state=self.metrics.current_state,
                consecutive_failures=self.metrics.consecutive_failures,
                consecutive_successes=self.metrics.consecutive_successes
            )
    
    def reset(self):
        """Reset circuit breaker to initial state"""
        with self._lock:
            self.state = CircuitState.CLOSED
            self.metrics = CircuitBreakerMetrics()
            self.last_failure_time = None
        
        logger.info(f"CircuitBreaker '{self.name}' reset to initial state")
    
    def force_open(self):
        """Force circuit breaker to open state"""
        with self._lock:
            self._transition_to_open()
        
        logger.warning(f"CircuitBreaker '{self.name}' forced to OPEN state")
    
    def force_closed(self):
        """Force circuit breaker to closed state"""
        with self._lock:
            self._transition_to_closed()
        
        logger.info(f"CircuitBreaker '{self.name}' forced to CLOSED state")


class CircuitBreakerRegistry:
    """
    Registry for managing multiple circuit breakers
    """
    
    def __init__(self):
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._lock = threading.Lock()
        
        logger.debug("CircuitBreakerRegistry initialized")
    
    def get_or_create(self, name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """
        Get existing circuit breaker or create new one
        
        Args:
            name: Circuit breaker name
            config: Configuration for new circuit breaker
            
        Returns:
            Circuit breaker instance
        """
        with self._lock:
            if name not in self._circuit_breakers:
                self._circuit_breakers[name] = CircuitBreaker(name, config)
                logger.debug(f"Created new circuit breaker: {name}")
            
            return self._circuit_breakers[name]
    
    def get(self, name: str) -> Optional[CircuitBreaker]:
        """
        Get circuit breaker by name
        
        Args:
            name: Circuit breaker name
            
        Returns:
            Circuit breaker instance or None
        """
        return self._circuit_breakers.get(name)
    
    def remove(self, name: str) -> bool:
        """
        Remove circuit breaker
        
        Args:
            name: Circuit breaker name
            
        Returns:
            True if removed, False if not found
        """
        with self._lock:
            if name in self._circuit_breakers:
                del self._circuit_breakers[name]
                logger.debug(f"Removed circuit breaker: {name}")
                return True
            return False
    
    def get_all_metrics(self) -> Dict[str, CircuitBreakerMetrics]:
        """
        Get metrics for all circuit breakers
        
        Returns:
            Dictionary of circuit breaker metrics
        """
        metrics = {}
        for name, cb in self._circuit_breakers.items():
            metrics[name] = cb.get_metrics()
        return metrics
    
    def reset_all(self):
        """Reset all circuit breakers"""
        for cb in self._circuit_breakers.values():
            cb.reset()
        logger.info("Reset all circuit breakers")
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of all circuit breakers
        
        Returns:
            Summary information
        """
        summary = {
            'total_circuit_breakers': len(self._circuit_breakers),
            'states': {'closed': 0, 'open': 0, 'half_open': 0},
            'circuit_breakers': {}
        }
        
        for name, cb in self._circuit_breakers.items():
            metrics = cb.get_metrics()
            state = cb.get_state()
            
            summary['states'][state.value] += 1
            summary['circuit_breakers'][name] = {
                'state': state.value,
                'total_calls': metrics.total_calls,
                'success_rate': (metrics.successful_calls / max(metrics.total_calls, 1)) * 100,
                'consecutive_failures': metrics.consecutive_failures
            }
        
        return summary


# Global circuit breaker registry
circuit_breaker_registry = CircuitBreakerRegistry()


def circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None):
    """
    Decorator to add circuit breaker protection to functions
    
    Args:
        name: Circuit breaker name
        config: Circuit breaker configuration
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        cb = circuit_breaker_registry.get_or_create(name, config)
        
        def wrapper(*args, **kwargs):
            return cb.call(func, *args, **kwargs)
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        wrapper.circuit_breaker = cb
        
        return wrapper
    
    return decorator


def get_circuit_breaker_registry() -> CircuitBreakerRegistry:
    """Get the global circuit breaker registry"""
    return circuit_breaker_registry