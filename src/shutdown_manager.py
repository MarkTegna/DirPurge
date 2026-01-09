"""
Graceful shutdown management for DirPurge
Handles clean application shutdown with resource cleanup
"""

import signal
import threading
import time
import atexit
from typing import List, Callable, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
from contextlib import contextmanager

from .logger import get_logger

logger = get_logger()


class ShutdownReason(Enum):
    """Reasons for application shutdown"""
    USER_REQUEST = "user_request"
    SIGNAL_INTERRUPT = "signal_interrupt"
    SIGNAL_TERMINATE = "signal_terminate"
    SYSTEM_ERROR = "system_error"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    TIMEOUT = "timeout"


@dataclass
class ShutdownContext:
    """Context information for shutdown"""
    reason: ShutdownReason
    message: str
    timeout_seconds: int = 30
    force_after_timeout: bool = True


class ShutdownManager:
    """
    Manages graceful application shutdown with cleanup
    """
    
    def __init__(self, default_timeout: int = 30):
        self.default_timeout = default_timeout
        self.shutdown_handlers: List[Callable[[], None]] = []
        self.cleanup_handlers: List[Callable[[], None]] = []
        self.is_shutting_down = False
        self.shutdown_complete = False
        self.shutdown_event = threading.Event()
        self._lock = threading.Lock()
        self._active_operations: Dict[str, threading.Thread] = {}
        
        # Register signal handlers
        self._register_signal_handlers()
        
        # Register atexit handler
        atexit.register(self._atexit_handler)
        
        logger.info("ShutdownManager initialized")
    
    def _register_signal_handlers(self):
        """Register system signal handlers"""
        try:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            logger.debug("Signal handlers registered")
        except (AttributeError, ValueError) as e:
            # Some signals may not be available on all platforms
            logger.warning(f"Could not register all signal handlers: {e}")
    
    def _signal_handler(self, signum: int, frame):
        """Handle system signals"""
        if signum == signal.SIGINT:
            reason = ShutdownReason.SIGNAL_INTERRUPT
            message = "Received SIGINT (Ctrl+C)"
        elif signum == signal.SIGTERM:
            reason = ShutdownReason.SIGNAL_TERMINATE
            message = "Received SIGTERM"
        else:
            reason = ShutdownReason.SYSTEM_ERROR
            message = f"Received signal {signum}"
        
        logger.info(f"Signal received: {message}")
        self.initiate_shutdown(ShutdownContext(reason=reason, message=message))
    
    def _atexit_handler(self):
        """Handle application exit"""
        if not self.shutdown_complete:
            logger.info("Application exiting, performing cleanup")
            self._perform_cleanup()
    
    def register_shutdown_handler(self, handler: Callable[[], None]):
        """
        Register a shutdown handler
        
        Args:
            handler: Function to call during shutdown
        """
        with self._lock:
            self.shutdown_handlers.append(handler)
        logger.debug(f"Registered shutdown handler: {handler.__name__}")
    
    def register_cleanup_handler(self, handler: Callable[[], None]):
        """
        Register a cleanup handler
        
        Args:
            handler: Function to call during cleanup
        """
        with self._lock:
            self.cleanup_handlers.append(handler)
        logger.debug(f"Registered cleanup handler: {handler.__name__}")
    
    def register_operation(self, operation_name: str, thread: threading.Thread):
        """
        Register an active operation
        
        Args:
            operation_name: Name of the operation
            thread: Thread running the operation
        """
        with self._lock:
            self._active_operations[operation_name] = thread
        logger.debug(f"Registered active operation: {operation_name}")
    
    def unregister_operation(self, operation_name: str):
        """
        Unregister an active operation
        
        Args:
            operation_name: Name of the operation to unregister
        """
        with self._lock:
            if operation_name in self._active_operations:
                del self._active_operations[operation_name]
        logger.debug(f"Unregistered operation: {operation_name}")
    
    @contextmanager
    def operation_context(self, operation_name: str):
        """
        Context manager for tracking operations
        
        Args:
            operation_name: Name of the operation
        """
        current_thread = threading.current_thread()
        self.register_operation(operation_name, current_thread)
        
        try:
            yield
        finally:
            self.unregister_operation(operation_name)
    
    def initiate_shutdown(self, context: ShutdownContext):
        """
        Initiate graceful shutdown
        
        Args:
            context: Shutdown context information
        """
        with self._lock:
            if self.is_shutting_down:
                logger.warning("Shutdown already in progress")
                return
            
            self.is_shutting_down = True
        
        logger.info(f"Initiating graceful shutdown: {context.message}")
        
        # Start shutdown in separate thread to avoid blocking
        shutdown_thread = threading.Thread(
            target=self._perform_shutdown,
            args=(context,),
            name="shutdown_thread"
        )
        shutdown_thread.start()
    
    def _perform_shutdown(self, context: ShutdownContext):
        """
        Perform the actual shutdown process
        
        Args:
            context: Shutdown context
        """
        try:
            logger.info("Starting shutdown process")
            
            # Step 1: Call shutdown handlers
            self._call_shutdown_handlers()
            
            # Step 2: Wait for active operations to complete
            self._wait_for_operations(context.timeout_seconds)
            
            # Step 3: Perform cleanup
            self._perform_cleanup()
            
            # Step 4: Mark shutdown complete
            with self._lock:
                self.shutdown_complete = True
            
            self.shutdown_event.set()
            logger.info("Graceful shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            if context.force_after_timeout:
                logger.warning("Forcing shutdown due to error")
                self._force_shutdown()
    
    def _call_shutdown_handlers(self):
        """Call all registered shutdown handlers"""
        logger.debug("Calling shutdown handlers")
        
        for handler in self.shutdown_handlers:
            try:
                logger.debug(f"Calling shutdown handler: {handler.__name__}")
                handler()
            except Exception as e:
                logger.error(f"Error in shutdown handler {handler.__name__}: {e}")
    
    def _wait_for_operations(self, timeout_seconds: int):
        """
        Wait for active operations to complete
        
        Args:
            timeout_seconds: Maximum time to wait
        """
        if not self._active_operations:
            logger.debug("No active operations to wait for")
            return
        
        logger.info(f"Waiting for {len(self._active_operations)} active operations to complete")
        
        start_time = time.time()
        
        while self._active_operations and (time.time() - start_time) < timeout_seconds:
            # Check which operations are still running
            with self._lock:
                completed_operations = []
                for name, thread in self._active_operations.items():
                    if not thread.is_alive():
                        completed_operations.append(name)
                
                # Remove completed operations
                for name in completed_operations:
                    del self._active_operations[name]
                    logger.debug(f"Operation completed: {name}")
            
            if self._active_operations:
                time.sleep(0.1)  # Brief pause before checking again
        
        # Log any operations that didn't complete
        if self._active_operations:
            remaining = list(self._active_operations.keys())
            logger.warning(f"Operations did not complete within timeout: {remaining}")
    
    def _perform_cleanup(self):
        """Perform cleanup operations"""
        logger.debug("Performing cleanup")
        
        for handler in self.cleanup_handlers:
            try:
                logger.debug(f"Calling cleanup handler: {handler.__name__}")
                handler()
            except Exception as e:
                logger.error(f"Error in cleanup handler {handler.__name__}: {e}")
    
    def _force_shutdown(self):
        """Force immediate shutdown"""
        logger.warning("Forcing immediate shutdown")
        
        # Attempt to terminate remaining operations
        with self._lock:
            for name, thread in self._active_operations.items():
                if thread.is_alive():
                    logger.warning(f"Forcibly terminating operation: {name}")
                    # Note: Python doesn't have a clean way to force-kill threads
                    # This is a limitation of the threading model
        
        self.shutdown_complete = True
        self.shutdown_event.set()
    
    def wait_for_shutdown(self, timeout: Optional[int] = None) -> bool:
        """
        Wait for shutdown to complete
        
        Args:
            timeout: Maximum time to wait (None for indefinite)
            
        Returns:
            True if shutdown completed, False if timeout
        """
        return self.shutdown_event.wait(timeout)
    
    def is_shutdown_requested(self) -> bool:
        """Check if shutdown has been requested"""
        return self.is_shutting_down
    
    def get_shutdown_status(self) -> Dict[str, Any]:
        """
        Get current shutdown status
        
        Returns:
            Shutdown status information
        """
        with self._lock:
            active_ops = list(self._active_operations.keys())
        
        return {
            'is_shutting_down': self.is_shutting_down,
            'shutdown_complete': self.shutdown_complete,
            'active_operations': active_ops,
            'shutdown_handlers_count': len(self.shutdown_handlers),
            'cleanup_handlers_count': len(self.cleanup_handlers)
        }


class ShutdownAware:
    """
    Mixin class for components that need shutdown awareness
    """
    
    def __init__(self, shutdown_manager: ShutdownManager):
        self.shutdown_manager = shutdown_manager
        self.shutdown_manager.register_shutdown_handler(self._on_shutdown)
        self.shutdown_manager.register_cleanup_handler(self._on_cleanup)
    
    def _on_shutdown(self):
        """Override this method to handle shutdown"""
        pass
    
    def _on_cleanup(self):
        """Override this method to handle cleanup"""
        pass
    
    def check_shutdown_requested(self):
        """Check if shutdown has been requested and raise exception if so"""
        if self.shutdown_manager.is_shutdown_requested():
            raise KeyboardInterrupt("Shutdown requested")


# Global shutdown manager instance
shutdown_manager = ShutdownManager()


def get_shutdown_manager() -> ShutdownManager:
    """Get the global shutdown manager instance"""
    return shutdown_manager


def shutdown_on_error(reason: str = "System error"):
    """
    Decorator to initiate shutdown on unhandled errors
    
    Args:
        reason: Reason for shutdown
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Unhandled error in {func.__name__}: {e}")
                shutdown_manager.initiate_shutdown(ShutdownContext(
                    reason=ShutdownReason.SYSTEM_ERROR,
                    message=f"Unhandled error in {func.__name__}: {e}"
                ))
                raise
        return wrapper
    return decorator