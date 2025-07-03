# mcp_toolbox/sources/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from dataclasses import dataclass

@dataclass
class SourceConfig(ABC):
    name: str
    kind: str
    
    @abstractmethod
    def create_source(self) -> 'Source':
        """Create a source instance from this configuration."""
        pass

class Source(ABC):
    """Base class for all data sources."""
    
    def __init__(self, name: str, kind: str):
        self.name = name
        self.kind = kind
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the source connection."""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up source resources."""
        pass