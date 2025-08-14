from cli.commands import cli
from sources.postgres.source import create_postgres_config
from tools.postgres.sql_tool import create_postgres_sql_config
from sources.http.source import create_http_config
from tools.http.http_tool import create_http_tool_config
from sources.bigquery.source import create_bigquery_config
from tools.bigquery.sql_tool import create_bigquery_sql_config
from sources.mysql.source import create_mysql_config
from tools.mysql.sql_tool import create_mysql_sql_config
from sources.oracle.source import create_oracle_config
from tools.oracle.sql_tool import create_oracle_sql_config
from sources.mssql.source import create_mssql_config
from tools.mssql.sql_tool import create_mssql_sql_config


if __name__ == "__main__":
    cli()