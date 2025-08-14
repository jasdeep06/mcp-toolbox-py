from typing import Dict, Any, List
from dataclasses import dataclass
from tools.base import Tool, ToolConfig
from tools.registry import register_tool
from tools.parameters import ParameterSet, create_parameter_set
from sources.oracle.source import OracleSource
from sources.base import Source

@dataclass
class OracleSqlConfig(ToolConfig): 
    parameter_set: ParameterSet
    statement: str

    def create_tool(self, sources: Dict[str, Source]) -> 'OracleSqlTool':
        if self.source not in sources:
            raise ValueError(f"Source '{self.source}' not found")
        
        source = sources[self.source]
        if not isinstance(source, OracleSource):
            raise ValueError(f"Source '{self.source}' must be an Oracle source")
        
        return OracleSqlTool(
            name=self.name,
            description=self.description,
            statement=self.statement,
            parameter_set=self.parameter_set,
            source=source,
            auth_required=self.auth_required
        )
    
class OracleSqlTool(Tool):
    """Tool for executing parameterized SQL statements on Oracle databases."""
    
    def __init__(self, name: str, description: str, statement: str,
                 parameter_set: ParameterSet, source: OracleSource,
                 auth_required: List[str] = None):
        super().__init__(name, "oracle-sql", description, parameter_set, auth_required)
        self.statement = statement
        self.source = source
        self.parameter_set = parameter_set
    
    async def invoke(self, params: Dict[str, Any]) -> List[Any]:
        """Execute the SQL statement with parameters."""
        # Validate parameters
        validated_params = self.parameter_set.validate_values(params)
        
        # Convert to list for SQL execution (assuming positional parameters)
        param_values = []
        for param in self.parameter_set._parameter_list:
            param_values.append(validated_params[param.name])
        
        results = await self.source.execute_query(self.statement, tuple(param_values))
        return [{"data": results}]
    
    def get_mcp_manifest(self) -> Dict[str, Any]:
        """Return MCP-compatible tool manifest."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.parameter_set.to_mcp_schema()
        }
    
@register_tool("oracle-sql")
def create_oracle_sql_config(name: str, config_data: Dict) -> OracleSqlConfig:
    """Create an Oracle SQL tool configuration."""
    parameter_set = create_parameter_set(config_data.get("parameters", []))
    
    return OracleSqlConfig(
        name=name,
        kind="oracle-sql",
        source=config_data.get("source"),
        description=config_data.get("description", ""),
        statement=config_data.get("statement", ""),
        parameter_set=parameter_set,
        auth_required=config_data.get("auth_required")
    )