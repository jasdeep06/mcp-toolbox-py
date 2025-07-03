# mcp_toolbox/server/config.py
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from sources.registry import source_registry
from tools.registry import tool_registry
from utils.yaml_parser import YamlConfigParser

@dataclass
class ServerConfig:
    """Server configuration."""
    sources: Dict[str, Any]
    tools: Dict[str, Any]
    toolsets: Dict[str, List[str]]
    auth_services: Optional[Dict[str, Any]] = None
    metadata_source: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_yaml(cls, file_path: str) -> 'ServerConfig':
        """Create configuration from YAML file."""
        config_data = YamlConfigParser.load_config(file_path)

        
        return cls(
            sources=config_data.get("sources", {}),
            tools=config_data.get("tools", {}),
            toolsets=config_data.get("toolsets", {}),
            auth_services=config_data.get("authServices", {}),
            metadata_source=config_data.get("metadata_source", {})
        )
    
    def create_sources(self) -> Dict[str, Any]:
        """Create source instances from configuration."""
        sources = {}
        for name, config_data in self.sources.items():
            kind = config_data["kind"]
            source_config = source_registry.create_config(kind, name, config_data)
            sources[name] = source_config.create_source()
        return sources
    
    def create_tools(self, sources: Dict[str, Any]) -> Dict[str, Any]:
        """Create tool instances from configuration."""
        tools = {}
        for name, config_data in self.tools.items():
            kind = config_data["kind"]
            tool_config = tool_registry.create_config(kind, name, config_data)
            tools[name] = tool_config.create_tool(sources)
        return tools