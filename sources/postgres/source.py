# mcp_toolbox/sources/postgres/source.py
import asyncio
import asyncpg
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from sources.base import Source, SourceConfig
from sources.registry import register_source

RETRYABLE_EXC = (
    asyncpg.InterfaceError,                 # "connection is closed"
    asyncpg.ConnectionDoesNotExistError,
    asyncpg.PostgresConnectionError,
)

@dataclass
class PostgresConfig(SourceConfig):
    host: str
    database: str
    user: str
    password: str
    port: int = 5432
    # For asyncpg, ssl should be bool or SSLContext; Neon requires TLS, so default True
    ssl: bool = True
    pool_size: int = 10
    command_timeout: float = 30.0

    def create_source(self) -> 'PostgresSource':
        return PostgresSource(
            name=self.name,
            kind=self.kind,
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password,
            ssl=self.ssl,
            pool_size=self.pool_size,
            command_timeout=self.command_timeout,
        )

class PostgresSource(Source):
    """PostgreSQL database source."""

    def __init__(
        self,
        name: str,
        kind: str,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        ssl: bool = True,
        pool_size: int = 10,
        command_timeout: float = 30.0,
    ):
        super().__init__(name, kind)
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.ssl = ssl
        self.pool_size = pool_size
        self.command_timeout = command_timeout
        self.pool: Optional[asyncpg.Pool] = None

    async def _init_conn(self, conn: asyncpg.Connection) -> None:
        # Optional tweaks; harmless if you remove them
        await conn.set_type_codec(
            'json', encoder=lambda v: v, decoder=lambda v: v, schema='pg_catalog', format='text'
        )
        # Set application name for observability
        await conn.execute("SET application_name = 'mcp-toolbox'")

    async def initialize(self) -> None:
        """Initialize the connection pool."""
        self.pool = await asyncpg.create_pool(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password,
            ssl=self.ssl,  # <- bool or SSLContext; True is fine for Neon
            min_size=1,
            max_size=self.pool_size,
            command_timeout=self.command_timeout,
            init=self._init_conn,
            # Slightly smaller cache helps on serverless backends that recycle connections
            statement_cache_size=256,
            # Optional: server_settings={"search_path": "public"},
        )

    async def cleanup(self) -> None:
        """Close the connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def _fetch_once(self, query: str, params: Optional[tuple]) -> List[Dict[str, Any]]:
        if not self.pool:
            raise RuntimeError("Source not initialized")

        async with self.pool.acquire() as conn:
            # Health check: make sure this connection is alive (avoids "connection is closed")
            try:
                await conn.execute("SELECT 1")
            except RETRYABLE_EXC:
                # Try to reconnect this connection
                # Release conn and let the pool hand us a fresh one
                raise

            # Execute the actual query
            rows = await (conn.fetch(query, *params) if params else conn.fetch(query))
            return [dict(row) for row in rows]

    async def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute a SQL query and return results with one automatic retry on broken connections."""
        # First try
        try:
            return await self._fetch_once(query, params)
        except RETRYABLE_EXC:
            # Short backoff, then retry once
            await asyncio.sleep(0.2)
            return await self._fetch_once(query, params)

@register_source("postgres")
def create_postgres_config(name: str, config_data: Dict) -> PostgresConfig:
    """Factory function for PostgreSQL source."""
    return PostgresConfig(
        name=name,
        kind="postgres",
        host=config_data["host"],
        port=config_data.get("port, 5432") if isinstance(config_data.get("port"), str) else config_data.get("port", 5432),
        database=config_data["database"],
        user=config_data["user"],
        password=config_data["password"],
        # For asyncpg: use bool/SSLContext; default to True for Neon
        ssl=config_data.get("ssl", True),
        pool_size=config_data.get("pool_size", 10),
        command_timeout=config_data.get("command_timeout", 30.0),
    )
