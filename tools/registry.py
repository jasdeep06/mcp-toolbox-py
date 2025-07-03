# mcp_toolbox/tools/registry.py
from typing import Dict, Callable, Type
from .base import ToolConfig

class ToolRegistry:
    """Registry for tool types."""
    
    def __init__(self):
        self._factories: Dict[str, Callable] = {}
    
    def register(self, kind: str, factory: Callable[[str, Dict], ToolConfig]) -> bool:
        """Register a tool factory function."""
        if kind in self._factories:
            return False
        self._factories[kind] = factory
        return True
    
    def create_config(self, kind: str, name: str, config_data: Dict) -> ToolConfig:
        """Create a tool config instance."""
        if kind not in self._factories:
            raise ValueError(f"Unknown tool kind: {kind}")
        return self._factories[kind](name, config_data)

# Global registry instance  
tool_registry = ToolRegistry()

# Decorator for easy registration
def register_tool(kind: str):
    def decorator(factory_func):
        tool_registry.register(kind, factory_func)
        return factory_func
    return decorator