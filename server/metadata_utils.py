# from typing import Dict, Any, List
# import asyncpg

# async def connect_to_metadata_source(metadata_source: Dict[str, Any]):
#     conn = await asyncpg.connect(
#         host=metadata_source["host"],
#         port=metadata_source["port"],
#         database=metadata_source["database"],
#         user=metadata_source["user"],
#         password=metadata_source["password"]
#     )
#     return conn

# from typing import List, Dict

# async def get_column_descriptions(
#     conn,
#     datasource_ids: List[str]
# ) -> Dict[str, str]:
#     sql = """
#         SELECT column_name, description
#         FROM public."column"            
#         WHERE datasource_id = ANY($1::uuid[])
#     """
#     # one round-trip, driver does the UUID array binding safely
#     rows = await conn.fetch(sql, datasource_ids)

#     # turn the list[Record] into a single dict[column_name -> description]
#     return {row['column_name']: row['description'] for row in rows}
              


# def resolve_column_descriptions(column_list,column_descriptions: List[Dict[str, Any]]):
#     resolved_column_descriptions = []
#     for column in column_list:
#         if column in column_descriptions:
#             resolved_column_descriptions.append({"column_name": column, "description": column_descriptions[column]})
#     return resolved_column_descriptions


# server/metadata_utils.py
from typing import List, Dict, Any, Optional
import asyncio
import asyncpg

RETRYABLE_META_EXC = (
    asyncpg.InterfaceError,                 # "connection is closed"
    asyncpg.ConnectionDoesNotExistError,
    asyncpg.PostgresConnectionError,
)

async def connect_to_metadata_source(metadata_source: Dict[str, Any]) -> asyncpg.Pool:
    # Neon/managed PG: use TLS
    pool = await asyncpg.create_pool(
        host=metadata_source["host"],
        port=metadata_source.get("port", 5432),
        database=metadata_source["database"],
        user=metadata_source["user"],
        password=metadata_source["password"],
        ssl=True,
        min_size=1,
        max_size=5,
        command_timeout=15,
    )
    return pool

async def _fetch_columns_once(pool: asyncpg.Pool, datasource_ids: List[str]) -> Dict[str, str]:
    async with pool.acquire() as conn:
        # Health check: avoid "connection is closed" on recycled/idle conns
        await conn.execute("SELECT 1")
        sql = """
            SELECT column_name, description
            FROM public."column"
            WHERE datasource_id = ANY($1::uuid[])
        """
        rows = await conn.fetch(sql, datasource_ids)
        return {row['column_name']: row['description'] for row in rows}

async def get_column_descriptions(
    pool: asyncpg.Pool,
    datasource_ids: List[str]
) -> Dict[str, str]:
    try:
        return await _fetch_columns_once(pool, datasource_ids)
    except RETRYABLE_META_EXC:
        # short backoff + one retry on broken/closed connection
        await asyncio.sleep(0.15)
        return await _fetch_columns_once(pool, datasource_ids)


def resolve_column_descriptions(column_list: List[str], column_descriptions: Dict[str, str]):
    # Only include descriptions for columns we actually have in the result
    return [
        {"column_name": col, "description": column_descriptions[col]}
        for col in column_list
        if col in column_descriptions
    ]
