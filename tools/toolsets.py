# mcp_toolbox/tools/toolsets.py
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from .base import Tool

@dataclass
class ToolsetConfig:
    """Configuration for a toolset."""
    name: str
    tool_names: List[str]
    description: Optional[str] = None

class Toolset:
    """A collection of tools that can be exposed together."""
    
    def __init__(self, name: str, tools: Dict[str, Tool], 
                 description: Optional[str] = None):
        self.name = name
        self.tools = tools
        self.description = description
    
    def get_tool_names(self) -> List[str]:
        """Get list of tool names in this toolset."""
        return list(self.tools.keys())
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a specific tool by name."""
        return self.tools.get(name)
    
    def has_tool(self, name: str) -> bool:
        """Check if toolset contains a specific tool."""
        return name in self.tools
    
    def get_mcp_tools_list(self) -> List[Dict[str, Any]]:
        """Get MCP-compatible tools list for this toolset."""
        return [tool.get_mcp_manifest() for tool in self.tools.values()]
    
    def get_authorized_tools(self, verified_auth_services: List[str]) -> Dict[str, Tool]:
        """Get tools that are authorized for the given auth services."""
        authorized = {}
        for name, tool in self.tools.items():
            if tool.is_authorized(verified_auth_services):
                authorized[name] = tool
        return authorized

def create_toolsets(toolset_configs: Dict[str, Any], 
                   all_tools: Dict[str, Tool]) -> Dict[str, Toolset]:
    """Create toolset instances from configuration."""
    toolsets = {}
    
    for name, config in toolset_configs.items():
        if isinstance(config, list):
            # Simple list format: just tool names
            tool_names = config
            description = None
        else:
            # Object format with description
            tool_names = config.get("tools", config.get("tool_names", []))
            description = config.get("description")
        
        # Validate that all tools exist
        toolset_tools = {}
        for tool_name in tool_names:
            if tool_name not in all_tools:
                raise ValueError(f"Tool '{tool_name}' not found for toolset '{name}'")
            toolset_tools[tool_name] = all_tools[tool_name]
        
        toolsets[name] = Toolset(name, toolset_tools, description)
    
    return toolsets