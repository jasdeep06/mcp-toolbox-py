# mcp_toolbox/tools/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from .parameters import Parameter, ParameterValue
from sources.base import Source

@dataclass(kw_only=True)
class ToolConfig(ABC):
    name: str
    kind: str
    source: str
    description: str
    auth_required: Optional[List[str]] = None
    
    @abstractmethod
    def create_tool(self, sources: Dict[str, Source]) -> 'Tool':
        """Create a tool instance from this configuration."""
        pass

class Tool(ABC):
    """Base class for all tools."""
    
    def __init__(self, name: str, kind: str, description: str, 
                 parameters: List[Parameter], auth_required: Optional[List[str]] = None):
        self.name = name
        self.kind = kind
        self.description = description
        self.parameters = parameters
        self.auth_required = auth_required or []
    
    @abstractmethod
    async def invoke(self, params: Dict[str, ParameterValue]) -> List[Any]:
        """Execute the tool with given parameters."""
        pass
    
    @abstractmethod
    def get_mcp_manifest(self) -> Dict[str, Any]:
        """Return MCP-compatible tool manifest."""
        pass
    
    def is_authorized(self, verified_auth_services: List[str]) -> bool:
        """Check if tool invocation is authorized."""
        if not self.auth_required:
            return True
        return any(auth in verified_auth_services for auth in self.auth_required)