from typing import Dict, Any, List
from dataclasses import dataclass
from tools.base import Tool, ToolConfig
from tools.registry import register_tool
from tools.parameters import ParameterSet, create_parameter_set
from sources.bigquery.source import BigQuerySource
from sources.base import Source


@dataclass
class BigQuerySqlConfig(ToolConfig):
    parameter_set: ParameterSet
    statement: str
    source: str


    def create_tool(self, sources: Dict[str, Source]) -> "BigQuerySqlTool":
        if self.source not in sources:
            raise ValueError(f"Source '{self.source}' not found")
        source = sources[self.source]
        if not isinstance(source, BigQuerySource):
            raise ValueError(f"Source '{self.source}' must be a BigQuery source")
        return BigQuerySqlTool(
            name=self.name,
            description=self.description,
            statement=self.statement,
            parameter_set=self.parameter_set,
            source=source,
            auth_required=self.auth_required
        )


class BigQuerySqlTool(Tool):
    """Tool for executing parameterized SQL statements on BigQuery."""

    def __init__(
        self,
        name: str,
        description: str,
        statement: str,
        parameter_set: ParameterSet,
        source: BigQuerySource,
        auth_required: List[str] = None,
    ):
        super().__init__(name, "bigquery-sql", description, parameter_set, auth_required)
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
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.parameter_set.to_mcp_schema(),
        }


@register_tool("bigquery-sql")
def create_bigquery_sql_config(
    name: str, config_data: Dict
) -> BigQuerySqlConfig:
    """Factory function for create BigQuery SQL tool."""
    parameter_set = create_parameter_set(config_data.get("parameters", []))
    return BigQuerySqlConfig(
        name=name,
        kind="bigquery-sql",
        source=config_data["source"],
        description=config_data["description"],
        statement=config_data["statement"],
        parameter_set=parameter_set,
        auth_required=config_data.get("auth_required")
    )