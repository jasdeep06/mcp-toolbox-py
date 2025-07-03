# mcp_toolbox/sources/registry.py
from typing import Dict, Callable, List
from .base import SourceConfig

class SourceRegistry:
    """Registry for source types."""
    
    def __init__(self):
        self._factories: Dict[str, Callable] = {}
    
    def register(self, kind: str, factory: Callable[[str, Dict], SourceConfig]) -> bool:
        """Register a source factory function."""
        if kind in self._factories:
            return False
        self._factories[kind] = factory
        return True
    
    def create_config(self, kind: str, name: str, config_data: Dict) -> SourceConfig:
        """Create a source config instance."""
        if kind not in self._factories:
            raise ValueError(f"Unknown source kind: {kind}")
        return self._factories[kind](name, config_data)
    
    def get_available_kinds(self) -> List[str]:
        """Get list of registered source kinds."""
        return list(self._factories.keys())

# Global registry instance
source_registry = SourceRegistry()

# Decorator for easy registration
def register_source(kind: str):
    def decorator(factory_func):
        source_registry.register(kind, factory_func)
        return factory_func
    return decorator