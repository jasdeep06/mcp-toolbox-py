from dataclasses import dataclass
from typing import Optional, Dict, List, Any
from sources.base import Source, SourceConfig
from sources.registry import register_source
import mysql.connector

@dataclass
class MySQLConfig(SourceConfig):
    host: str
    user: str
    password: str
    port: int = 3306

    def create_source(self) -> 'MySQLSource':
        return MySQLSource(
            name=self.name,
            kind=self.kind,
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password
        )

class MySQLSource(Source):
    """MySQL database source."""

    def __init__(
            self, name: str, 
            kind: str, 
            host: str, 
            port: int,
            user: str, 
            password: str
            ):
        super().__init__(name, kind)
        self.host = host
        self.port = port
        self.user = user
        self.password = password

    async def initialize(self) -> None:
        """Initialize the MySQL connection."""
        self.conn = mysql.connector.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password
        )

    async def cleanup(self) -> None:
        """Close the MySQL connection."""
        if self.conn and self.conn.is_connected():
            self.conn.close()
            self.conn = None

    async def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[Any, Any]]:
        """Execute a MySQL query and return the results."""
        if not self.conn or not self.conn.is_connected():
            raise RuntimeError("MySQL connection is not initialized.")

        cursor = self.conn.cursor(dictionary=True)
        try:
            cursor.execute(query, params)
            return cursor.fetchall()
        finally:
            cursor.close()

@register_source("mysql")
def create_mysql_config(name: str, config_dict: Dict[str, Any]) -> MySQLConfig:
    """Create a MySQL source configuration."""
    return MySQLConfig(
        name=name,
        kind="mysql",
        host=config_dict.get("host", "localhost"),
        port=config_dict.get("port", 3306),
        user=config_dict["user"],
        password=config_dict["password"]
    )