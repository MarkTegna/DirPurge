"""
Dependency injection container for DirPurge
Provides loose coupling and testability improvements
"""

from typing import Dict, Any, Type, TypeVar, Callable, Optional, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import inspect

from .logger import get_logger

logger = get_logger()

T = TypeVar('T')


class LifetimeScope(Enum):
    """Dependency lifetime scopes"""
    SINGLETON = "singleton"  # Single instance for entire application
    TRANSIENT = "transient"  # New instance every time
    SCOPED = "scoped"        # Single instance per operation scope


@dataclass
class DependencyRegistration:
    """Dependency registration information"""
    interface: Type
    implementation: Union[Type, Callable]
    lifetime: LifetimeScope
    factory: Optional[Callable] = None
    instance: Optional[Any] = None


class DependencyContainer:
    """
    Dependency injection container with lifetime management
    """
    
    def __init__(self):
        self._registrations: Dict[Type, DependencyRegistration] = {}
        self._singletons: Dict[Type, Any] = {}
        self._scoped_instances: Dict[Type, Any] = {}
        self._scope_active = False
        
        logger.debug("DependencyContainer initialized")
    
    def register_singleton(self, interface: Type[T], implementation: Union[Type[T], Callable[[], T]]) -> 'DependencyContainer':
        """
        Register a singleton dependency
        
        Args:
            interface: Interface type
            implementation: Implementation type or factory function
            
        Returns:
            Self for method chaining
        """
        self._registrations[interface] = DependencyRegistration(
            interface=interface,
            implementation=implementation,
            lifetime=LifetimeScope.SINGLETON
        )
        
        logger.debug(f"Registered singleton: {interface.__name__} -> {implementation}")
        return self
    
    def register_transient(self, interface: Type[T], implementation: Union[Type[T], Callable[[], T]]) -> 'DependencyContainer':
        """
        Register a transient dependency
        
        Args:
            interface: Interface type
            implementation: Implementation type or factory function
            
        Returns:
            Self for method chaining
        """
        self._registrations[interface] = DependencyRegistration(
            interface=interface,
            implementation=implementation,
            lifetime=LifetimeScope.TRANSIENT
        )
        
        logger.debug(f"Registered transient: {interface.__name__} -> {implementation}")
        return self
    
    def register_scoped(self, interface: Type[T], implementation: Union[Type[T], Callable[[], T]]) -> 'DependencyContainer':
        """
        Register a scoped dependency
        
        Args:
            interface: Interface type
            implementation: Implementation type or factory function
            
        Returns:
            Self for method chaining
        """
        self._registrations[interface] = DependencyRegistration(
            interface=interface,
            implementation=implementation,
            lifetime=LifetimeScope.SCOPED
        )
        
        logger.debug(f"Registered scoped: {interface.__name__} -> {implementation}")
        return self
    
    def register_instance(self, interface: Type[T], instance: T) -> 'DependencyContainer':
        """
        Register a specific instance
        
        Args:
            interface: Interface type
            instance: Instance to register
            
        Returns:
            Self for method chaining
        """
        self._registrations[interface] = DependencyRegistration(
            interface=interface,
            implementation=type(instance),
            lifetime=LifetimeScope.SINGLETON,
            instance=instance
        )
        
        self._singletons[interface] = instance
        
        logger.debug(f"Registered instance: {interface.__name__} -> {type(instance).__name__}")
        return self
    
    def register_factory(self, interface: Type[T], factory: Callable[[], T], lifetime: LifetimeScope = LifetimeScope.TRANSIENT) -> 'DependencyContainer':
        """
        Register a factory function
        
        Args:
            interface: Interface type
            factory: Factory function
            lifetime: Dependency lifetime
            
        Returns:
            Self for method chaining
        """
        self._registrations[interface] = DependencyRegistration(
            interface=interface,
            implementation=factory,
            lifetime=lifetime,
            factory=factory
        )
        
        logger.debug(f"Registered factory: {interface.__name__} -> {factory.__name__}")
        return self
    
    def resolve(self, interface: Type[T]) -> T:
        """
        Resolve a dependency
        
        Args:
            interface: Interface type to resolve
            
        Returns:
            Resolved instance
            
        Raises:
            ValueError: If dependency is not registered or cannot be resolved
        """
        if interface not in self._registrations:
            raise ValueError(f"Dependency not registered: {interface.__name__}")
        
        registration = self._registrations[interface]
        
        # Handle different lifetime scopes
        if registration.lifetime == LifetimeScope.SINGLETON:
            return self._resolve_singleton(registration)
        elif registration.lifetime == LifetimeScope.SCOPED:
            return self._resolve_scoped(registration)
        else:  # TRANSIENT
            return self._resolve_transient(registration)
    
    def _resolve_singleton(self, registration: DependencyRegistration) -> Any:
        """Resolve singleton dependency"""
        if registration.interface in self._singletons:
            return self._singletons[registration.interface]
        
        instance = self._create_instance(registration)
        self._singletons[registration.interface] = instance
        
        logger.debug(f"Created singleton instance: {registration.interface.__name__}")
        return instance
    
    def _resolve_scoped(self, registration: DependencyRegistration) -> Any:
        """Resolve scoped dependency"""
        if not self._scope_active:
            raise ValueError(f"Cannot resolve scoped dependency outside of scope: {registration.interface.__name__}")
        
        if registration.interface in self._scoped_instances:
            return self._scoped_instances[registration.interface]
        
        instance = self._create_instance(registration)
        self._scoped_instances[registration.interface] = instance
        
        logger.debug(f"Created scoped instance: {registration.interface.__name__}")
        return instance
    
    def _resolve_transient(self, registration: DependencyRegistration) -> Any:
        """Resolve transient dependency"""
        instance = self._create_instance(registration)
        logger.debug(f"Created transient instance: {registration.interface.__name__}")
        return instance
    
    def _create_instance(self, registration: DependencyRegistration) -> Any:
        """Create instance from registration"""
        if registration.instance is not None:
            return registration.instance
        
        if registration.factory is not None:
            return registration.factory()
        
        implementation = registration.implementation
        
        # Handle callable (factory function)
        if callable(implementation) and not inspect.isclass(implementation):
            return implementation()
        
        # Handle class with dependency injection
        if inspect.isclass(implementation):
            return self._create_instance_with_injection(implementation)
        
        raise ValueError(f"Cannot create instance for: {registration.interface.__name__}")
    
    def _create_instance_with_injection(self, cls: Type) -> Any:
        """Create instance with constructor dependency injection"""
        try:
            # Get constructor signature
            sig = inspect.signature(cls.__init__)
            
            # Resolve constructor parameters
            kwargs = {}
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                
                # Try to resolve parameter type
                if param.annotation != inspect.Parameter.empty:
                    try:
                        kwargs[param_name] = self.resolve(param.annotation)
                    except ValueError:
                        # Parameter not registered, use default if available
                        if param.default != inspect.Parameter.empty:
                            kwargs[param_name] = param.default
                        else:
                            logger.warning(f"Cannot resolve parameter {param_name} for {cls.__name__}")
            
            return cls(**kwargs)
            
        except Exception as e:
            logger.error(f"Failed to create instance of {cls.__name__}: {e}")
            # Fallback to parameterless constructor
            try:
                return cls()
            except Exception as fallback_error:
                raise ValueError(f"Cannot create instance of {cls.__name__}: {fallback_error}")
    
    def create_scope(self):
        """Create a new dependency scope"""
        return DependencyScope(self)
    
    def _enter_scope(self):
        """Enter dependency scope"""
        self._scope_active = True
        self._scoped_instances.clear()
        logger.debug("Entered dependency scope")
    
    def _exit_scope(self):
        """Exit dependency scope"""
        self._scope_active = False
        
        # Dispose scoped instances if they implement IDisposable
        for instance in self._scoped_instances.values():
            if hasattr(instance, 'dispose'):
                try:
                    instance.dispose()
                except Exception as e:
                    logger.warning(f"Error disposing scoped instance: {e}")
        
        self._scoped_instances.clear()
        logger.debug("Exited dependency scope")
    
    def is_registered(self, interface: Type) -> bool:
        """Check if interface is registered"""
        return interface in self._registrations
    
    def get_registrations(self) -> Dict[Type, DependencyRegistration]:
        """Get all registrations (for debugging)"""
        return self._registrations.copy()


class DependencyScope:
    """Context manager for dependency scopes"""
    
    def __init__(self, container: DependencyContainer):
        self.container = container
    
    def __enter__(self):
        self.container._enter_scope()
        return self.container
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.container._exit_scope()


# Interfaces for dependency injection
class IFileScanner(ABC):
    """File scanner interface"""
    
    @abstractmethod
    def scan_directory(self, directory_path: str) -> Dict[str, Any]:
        pass


class IPurgeEngine(ABC):
    """Purge engine interface"""
    
    @abstractmethod
    def determine_files_to_purge(self, file_groups: Dict[str, Any]) -> tuple:
        pass
    
    @abstractmethod
    def execute_purge(self, files_to_delete: list, dry_run: bool) -> Any:
        pass


class IReporter(ABC):
    """Reporter interface"""
    
    @abstractmethod
    def generate_report(self, purge_result: Any, config: Any, file_groups: Dict[str, Any]) -> str:
        pass
    
    @abstractmethod
    def save_report(self, report_content: str) -> Any:
        pass


class IEmailService(ABC):
    """Email service interface"""
    
    @abstractmethod
    def send_report(self, report_content: str) -> bool:
        pass


class IConfigManager(ABC):
    """Configuration manager interface"""
    
    @abstractmethod
    def load_config_from_ini(self, ini_path: str) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def parse_cli_args(self, args: list) -> Dict[str, Any]:
        pass


# Global container instance
container = DependencyContainer()


def configure_dependencies(container: DependencyContainer) -> None:
    """
    Configure default dependencies
    
    Args:
        container: Dependency container to configure
    """
    from .file_scanner import FileScanner
    from .purge_engine import PurgeEngine
    from .reporter import Reporter
    from .email_service import EmailService
    from .config_manager import ConfigManager
    from .resource_manager import ResourceManager, ResourceLimits
    
    # Register core services
    container.register_transient(IFileScanner, FileScanner)
    container.register_transient(IPurgeEngine, PurgeEngine)
    container.register_transient(IReporter, Reporter)
    container.register_transient(IEmailService, EmailService)
    container.register_singleton(IConfigManager, ConfigManager)
    
    # Register resource manager as singleton
    container.register_singleton(ResourceManager, lambda: ResourceManager(ResourceLimits()))
    
    logger.info("Dependencies configured")


def get_container() -> DependencyContainer:
    """Get the global dependency container"""
    return container