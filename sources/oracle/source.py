import oracledb
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from sources.base import Source, SourceConfig
from sources.registry import register_source

@dataclass
class OracleConfig(SourceConfig):
    user: str
    password: str
    host: str
    service_name: str
    port: int = 1521

    def create_source(self) -> 'OracleSource':
        return OracleSource(
            name=self.name,
            kind=self.kind,
            user=self.user,
            password=self.password,
            host=self.host,
            service_name=self.service_name,
            port=self.port
        )

class OracleSource(Source):
    """Oracle database source."""

    def __init__(self, name: str, kind: str, user: str, password: str,
                 host: str, service_name: str, port: int = 1521):
        super().__init__(name, kind)
        self.user = user
        self.password = password
        self.host = host
        self.service_name = service_name
        self.port = port

    async def initialize(self) -> None:
        """Initialize the Oracle connection."""
        self.conn = oracledb.connect(
                user=self.user,
                password=self.password,
                host=self.host,
                port=self.port,
                service_name=self.service_name
            )
        
    async def cleanup(self):
        if self.conn:
            await self.conn.close()
            self.conn = None

    async def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute a query and return the results."""
        if not self.conn:
            raise RuntimeError("Connection not initialized. Call initialize() first.")
        
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            cols = [d[0].lower() for d in cur.description]
            return [dict(zip(cols, row)) for row in cur]
        
@register_source("oracle")
def create_oracle_config(name: str, config_data: Dict) -> OracleConfig:
    """Create an Oracle configuration from the provided data."""
    return OracleConfig(
        name=name,
        kind="oracle",
        user=config_data["user"],
        password=config_data["password"],
        host=config_data["host"],
        service_name=config_data["service_name"],
        port=config_data.get("port", 1521)
    )
