from typing import Dict, Any, List
import asyncpg

async def connect_to_metadata_source(metadata_source: Dict[str, Any]):
    conn = await asyncpg.connect(
        host=metadata_source["host"],
        port=metadata_source["port"],
        database=metadata_source["database"],
        user=metadata_source["user"],
        password=metadata_source["password"]
    )
    return conn

from typing import List, Dict

async def get_column_descriptions(
    conn,
    datasource_ids: List[str]
) -> Dict[str, str]:
    sql = """
        SELECT column_name, description
        FROM public."column"            
        WHERE datasource_id = ANY($1::uuid[])
    """
    # one round-trip, driver does the UUID array binding safely
    rows = await conn.fetch(sql, datasource_ids)

    # turn the list[Record] into a single dict[column_name -> description]
    return {row['column_name']: row['description'] for row in rows}
              


def resolve_column_descriptions(column_list,column_descriptions: List[Dict[str, Any]]):
    resolved_column_descriptions = []
    for column in column_list:
        if column in column_descriptions:
            resolved_column_descriptions.append({"column_name": column, "description": column_descriptions[column]})
    return resolved_column_descriptions


