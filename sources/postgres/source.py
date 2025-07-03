# mcp_toolbox/sources/postgres/source.py
# import sys
#add /Users/codecaffiene/Desktop/jas-proj/mcp-toolbox/py to sys.path
# sys.path.append("/Users/codecaffiene/Desktop/jas-proj/mcp-toolbox/py")
# import os
# import asyncio
import asyncpg
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from sources.base import Source, SourceConfig
from sources.registry import register_source

@dataclass
class PostgresConfig(SourceConfig):
    host: str
    database: str
    user: str
    password: str
    port: int = 5432
    ssl_mode: str = "prefer"
    pool_size: int = 10
    
    
    def create_source(self) -> 'PostgresSource':
        return PostgresSource(
            name=self.name,
            kind=self.kind,
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password,
            ssl_mode=self.ssl_mode,
            pool_size=self.pool_size
        )

class PostgresSource(Source):
    """PostgreSQL database source."""
    
    def __init__(self, name: str, kind: str, host: str, port: int, 
                 database: str, user: str, password: str, 
                 ssl_mode: str = "prefer", pool_size: int = 10):
        super().__init__(name, kind)
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.ssl_mode = ssl_mode
        self.pool_size = pool_size
        self.pool: Optional[asyncpg.Pool] = None
    
    async def initialize(self) -> None:
        """Initialize the connection pool."""
        self.pool = await asyncpg.create_pool(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password,
            ssl=self.ssl_mode,
            min_size=1,
            max_size=self.pool_size
        )
    
    async def cleanup(self) -> None:
        """Close the connection pool."""
        if self.pool:
            await self.pool.close()
    
    async def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute a SQL query and return results."""
        if not self.pool:
            raise RuntimeError("Source not initialized")
        
        async with self.pool.acquire() as conn:
            if params:
                rows = await conn.fetch(query, *params)
            else:
                rows = await conn.fetch(query)
            return [dict(row) for row in rows]

@register_source("postgres")
def create_postgres_config(name: str, config_data: Dict) -> PostgresConfig:
    """Factory function for PostgreSQL source."""
    return PostgresConfig(
        name=name,
        kind="postgres",
        host=config_data["host"],
        port=config_data.get("port", 5432),
        database=config_data["database"],
        user=config_data["user"],
        password=config_data["password"],
        ssl_mode=config_data.get("ssl_mode", "prefer"),
        pool_size=config_data.get("pool_size", 10)
    )

# # Example usage
# if __name__ == "__main__":
#     #"postgresql://neondb_owner:npg_OqZYgaH46CQb@ep-ancient-shape-a1kjibq3-pooler.ap-southeast-1.aws.neon.tech/neondb"
#     async def main():

#         config = create_postgres_config("my_postgres_source", {
#             "host": "ep-ancient-shape-a1kjibq3-pooler.ap-southeast-1.aws.neon.tech",
#             "database": "neondb",
#             "user": "neondb_owner",
#             "password": "npg_OqZYgaH46CQb"
#         })

#         source = config.create_source()
#         await source.initialize()
#         try:
#             results = await source.execute_query("SELECT * FROM public.user")
#         finally:
#             await source.cleanup()

#     asyncio.run(main())