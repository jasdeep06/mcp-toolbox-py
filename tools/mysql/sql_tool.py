from typing import Dict, Any, List
from dataclasses import dataclass
from tools.base import Tool, ToolConfig
from tools.registry import register_tool
from tools.parameters import ParameterSet, create_parameter_set
from sources.mysql.source import MySQLSource
from sources.base import Source

@dataclass
class MySQLSqlConfig(ToolConfig):
    parameter_set: ParameterSet
    statement: str

    
    def create_tool(self, sources: Dict[str, Source]) -> 'MySQLSqlTool':
        if self.source not in sources:
            raise ValueError(f"Source '{self.source}' not found")
        
        source = sources[self.source]
        if not isinstance(source, MySQLSource):
            raise ValueError(f"Source '{self.source}' must be a MySQL source")
        
        return MySQLSqlTool(
            name=self.name,
            description=self.description,
            statement=self.statement,
            parameter_set=self.parameter_set,
            source=source,
            auth_required=self.auth_required
        )
    
class MySQLSqlTool(Tool):
    """Tool for executing parameterized SQL statements on MySQL."""
    
    def __init__(self, name: str, description: str, statement: str,
                 parameter_set: ParameterSet, source: MySQLSource,
                 auth_required: List[str] = None):
        super().__init__(name, "mysql-sql", description, parameter_set, auth_required)
        self.statement = statement
        self.source = source
        self.parameter_set = parameter_set
    
    async def invoke(self, params: Dict[str, Any]) -> List[Any]:
        """Execute the SQL statement with parameters."""

        validated_params = self.parameter_set.validate_values(params)

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
            "inputSchema": self.parameter_set.to_mcp_schema(),
        }
    
@register_tool("mysql-sql")
def create_mysql_sql_config(name: str, config_data: Dict) -> MySQLSqlConfig:
    """Factory function for MySQL SQL tool configuration."""
    parameter_set = create_parameter_set(config_data.get("parameters", []))
    
    return MySQLSqlConfig(
        name=name,
        kind="mysql-sql",
        source=config_data["source"],
        statement=config_data["statement"],
        parameter_set=parameter_set,
        description=config_data.get("description", ""),
        auth_required=config_data.get("authRequired", [])
    )