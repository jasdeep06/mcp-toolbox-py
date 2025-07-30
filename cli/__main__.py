from cli.commands import cli
from sources.postgres.source import create_postgres_config
from tools.postgres.sql_tool import create_postgres_sql_config
from sources.http.source import create_http_config
from tools.http.http_tool import create_http_tool_config



if __name__ == "__main__":
    cli()