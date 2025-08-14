from pathlib import Path
import json
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import requests
import os
import google.auth
from google.cloud import bigquery
import threading
from sources.base import Source, SourceConfig
from sources.registry import register_source


@dataclass
class BigQueryConfig(SourceConfig):
    client_id: str
    client_secret: str
    project_id: str
    sso_login_url: str
    google_application_credentials: str

    def create_source(self):
        return BigQuerySource(
            name=self.name,
            kind=self.kind,
            client_id=self.client_id,
            client_secret=self.client_secret,
            project_id=self.project_id,
            sso_login_url=self.sso_login_url,
            google_application_credentials=self.google_application_credentials,
        )



class BigQuerySource(Source):
    """BigQuery database source."""

    def __init__(
        self,
        name: str,
        kind: str,
        client_id: str,
        client_secret: str,
        project_id: str,
        sso_login_url: str,
        google_application_credentials: str,
    ):
        super().__init__(name, kind)
        self.client_id = client_id
        self.client_secret = client_secret
        self.project_id = project_id
        self.sso_login_url = sso_login_url
        self.google_application_credentials = google_application_credentials
        self.bq_client: Optional[bigquery.Client] = None

    async def initialize(self):
        """Initialize the Bigquery source."""
        try:
            threading.Thread(target=self.activate_client_periodically, daemon=True).start()
        except Exception as e:
            print(f"Error initializing BigQuery client: {e}")
            raise e

    def activate_client(self) -> None:
        """Initialize the Bigquery client."""
        client_lock = threading.Lock()
        with client_lock:
            try:
                self.client_id = self.client_id
                self.client_secret = self.client_secret
                sso_login_url = self.sso_login_url

                output = Path(__file__).parent.parent.with_name(self.google_application_credentials)
                with output.open('r') as f:
                    contents = json.load(f)
                if contents.get("type") != "service_account":
                    self.exchange_and_save_oidc_token_for_jwt(
                        client_id=self.client_id,
                        client_secret=self.client_secret,
                        sso_login_url=sso_login_url
                    )
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.google_application_credentials
                os.environ["GOOGLE_CLOUD_PROJECT"] = self.project_id
                credentials, gcp_project = google.auth.default()
                self.bq_client = bigquery.Client(credentials=credentials, project=gcp_project)
                self.bq_client.query("SELECT 1")
                print("*************************************")
            except Exception as e:
                raise e

    def activate_client_periodically(self):
        """Function to refresh the Bigquery client every 5 minutes."""
        while True:
            try:
                self.activate_client()
                print(f"Bigquery client activated/refreshed at {datetime.now()}.")
            except Exception as e:
                print(f"Failed to activate Bigquery client: {e}")
            time.sleep(300) # Wait for 5 minutes (300 seconds)

    def exchange_and_save_oidc_token_for_jwt(
        self,
        client_id: str,
        client_secret: str,
        sso_login_url: str
    ) -> None:
        sso_login_url = sso_login_url
        payload = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "read"
        }
        try:
            response = requests.post(url=sso_login_url, params=payload)
            response.raise_for_status()
            token = response.json()
            output = Path(__file__).parent.parent.with_name('oidc_token.json')
            with output.open('w') as f:
                json.dump(token, f)
        except Exception as e:
            raise Exception("Failed to exchange OIDC token for JWT: {e}") from e

    async def cleanup(self) -> None:
        """Cleanup resources."""
        if self.bq_client:
            self.bq_client.close()
            print("BigQuery client resources cleaned up.")

    async def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute a query against BigQuery."""
        if self.bq_client is None:
            raise RuntimeError("BigQuery client is not initialized.")
        job_config = bigquery.QueryJobConfig()
        if params:
            job_config.query_parameters = [
                bigquery.ScalarQueryParameter(None, self.bq_type_cast(val), val)
                for val in params
            ]
        query_job = self.bq_client.query(query, job_config=job_config)
        rows = query_job.result()
        return [dict(row) for row in rows]

    def bq_type_cast(self, val):
        import decimal
        import datetime
        if isinstance(val, int):
            return "INT64"
        elif isinstance(val, float):
            return "FLOAT64"
        elif isinstance(val, bytes):
            return "BYTES"
        elif isinstance(val, bool):
            return "BOOL"
        elif isinstance(val, decimal.Decimal):
            return "NUMERIC"
        elif isinstance(val, datetime.date):
            return "DATE"
        elif isinstance(val, datetime.datetime):
            return "TIMESTAMP"
        return "STRING"

@register_source("bigquery")
def create_bigquery_config(name: str, config_data: Dict) -> BigQueryConfig:
    """Create a BigQueryConfig from the provided configuration data."""
    return BigQueryConfig(
        name=name,
        kind="bigquery",
        client_id=config_data.get("client_id"),
        client_secret=config_data.get("client_secret"),
        project_id=config_data.get("project_id"),
        sso_login_url=config_data.get("sso_login_url"),
        google_application_credentials=config_data.get("google_application_credentials"),
    )