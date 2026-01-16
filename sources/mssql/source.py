import pyodbc
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from sources.base import Source, SourceConfig
from sources.registry import register_source

@dataclass
class MSSQLConfig(SourceConfig):
    server: str 
    database: str
    user: str
    password: str
    trust_server_certificate: str = "yes"
    encrypt: str = "yes"
    driver: str = "ODBC Driver 17 for SQL Server"

    def create_source(self) -> 'MSSQLSource':
        return MSSQLSource(
            name=self.name,
            kind=self.kind,
            server=self.server,
            database=self.database,
            user=self.user,
            password=self.password,
            trust_server_certificate=self.trust_server_certificate,
            encrypt=self.encrypt,
            driver=self.driver
        )
    
class MSSQLSource(Source):
    """MSSQL database source."""
    
    def __init__(self, name: str, kind: str, server: str, 
                 database: str, user: str, password: str, 
                 trust_server_certificate: str = "yes", 
                 encrypt: str = "yes", driver: str = "ODBC Driver 17 for SQL Server"):
        super().__init__(name, kind)
        self.server = server
        self.database = database
        self.user = user
        self.password = password
        self.trust_server_certificate = trust_server_certificate
        self.encrypt = encrypt
        self.driver = driver
    
    async def initialize(self) -> None:
        """Initialize the connection."""
        
        if self.driver not in pyodbc.drivers():
            raise RuntimeError(
                f"ODBC driver not installed: {self.driver}. Installed: {pyodbc.drivers()}"
            )
        connection_string = (
            f"DRIVER={self.driver};"
            f"SERVER={self.server};"
            f"DATABASE={self.database};"
            f"UID={self.user};"
            f"PWD={self.password};"
            f"Encrypt={self.encrypt};TrustServerCertificate={self.trust_server_certificate};"
        )
        self.conn = pyodbc.connect(connection_string)

    async def cleanup(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a SQL query and return results."""
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        cursor.close()
        return results
    
@register_source("mssql")
def create_mssql_config(name: str, config_data: Dict) -> MSSQLConfig:
    """Create a MSSQL configuration from the provided data."""
    return MSSQLConfig(
        name=name,
        kind="mssql",
        server=config_data["server"],
        database=config_data["database"],
        user=config_data["user"],
        password=config_data["password"],
        trust_server_certificate=config_data.get("trust_server_certificate", "yes"),
        encrypt=config_data.get("encrypt", "yes"),
        driver=config_data.get("driver", "ODBC Driver 17 for SQL Server")
    )