# py/sources/http/source.py
import asyncio
import aiohttp
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
from sources.base import Source, SourceConfig
from sources.registry import register_source

@dataclass
class HttpConfig(SourceConfig):
    base_url: str
    timeout: Optional[str] = "30s"  # Default timeout
    default_headers: Optional[Dict[str, str]] = None
    query_params: Optional[Dict[str, str]] = None

    def __post_init__(self):
        # Validate base URL
        parsed = urlparse(self.base_url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid base_url: {self.base_url}")
        
        # Set defaults
        if self.default_headers is None:
            self.default_headers = {}
        if self.query_params is None:
            self.query_params = {}

    def create_source(self) -> 'HttpSource':
        return HttpSource(
            name=self.name,
            kind=self.kind,
            base_url=self.base_url,
            timeout=self.timeout,
            default_headers=self.default_headers,
            query_params=self.query_params
        )

class HttpSource(Source):
    """HTTP client source for making web requests."""
    
    def __init__(self, name: str, kind: str, base_url: str, 
                 timeout: str = "30s", default_headers: Optional[Dict[str, str]] = None,
                 query_params: Optional[Dict[str, str]] = None):
        super().__init__(name, kind)
        self.base_url = base_url.rstrip('/')  # Remove trailing slash
        self.timeout = self._parse_timeout(timeout)
        self.default_headers = default_headers or {}
        self.query_params = query_params or {}
        self.session: Optional[aiohttp.ClientSession] = None
    
    def _parse_timeout(self, timeout_str: str) -> float:
        """Parse timeout string (e.g., '30s', '1m') to seconds."""
        if timeout_str.endswith('s'):
            return float(timeout_str[:-1])
        elif timeout_str.endswith('m'):
            return float(timeout_str[:-1]) * 60
        elif timeout_str.endswith('h'):
            return float(timeout_str[:-1]) * 3600
        else:
            try:
                return float(timeout_str)  # Assume seconds if no unit
            except ValueError:
                raise ValueError(f"Invalid timeout format: {timeout_str}")
    
    async def initialize(self) -> None:
        """Initialize the HTTP session."""
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self.session = aiohttp.ClientSession(
            headers=self.default_headers,
            timeout=timeout
        )
    
    async def cleanup(self) -> None:
        """Close the HTTP session."""
        if self.session:
            await self.session.close()
    
    async def request(self, method: str, path: str, 
                     headers: Optional[Dict[str, str]] = None,
                     params: Optional[Dict[str, Any]] = None,
                     data: Optional[Union[str, bytes, Dict[str, Any]]] = None,
                     json: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make an HTTP request."""
        if not self.session:
            raise RuntimeError("HTTP source not initialized")
        
        # Build full URL
        if path.startswith('http'):
            url = path  # Full URL provided
        else:
            url = urljoin(self.base_url + '/', path.lstrip('/'))
        
        # Merge query parameters
        merged_params = {**self.query_params}
        if params:
            merged_params.update(params)
        
        # Merge headers
        merged_headers = {}
        if headers:
            merged_headers.update(headers)
        
        try:
            async with self.session.request(
                method=method.upper(),
                url=url,
                headers=merged_headers if merged_headers else None,
                params=merged_params if merged_params else None,
                data=data,
                json=json
            ) as response:
                
                # Get response body
                content_type = response.headers.get('Content-Type', '')
                if 'application/json' in content_type:
                    response_data = await response.json()
                else:
                    response_text = await response.text()
                    try:
                        import json as json_module
                        response_data = json_module.loads(response_text)
                    except json_module.JSONDecodeError:
                        response_data = response_text
                
                # Check status
                if response.status >= 400:
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=f"HTTP {response.status}: {response_data}"
                    )
                
                return {
                    "status": response.status,
                    "headers": dict(response.headers),
                    "data": response_data
                }
        
        except aiohttp.ClientError as e:
            raise RuntimeError(f"HTTP request failed: {e}")

@register_source("http")
def create_http_config(name: str, config_data: Dict) -> HttpConfig:
    """Factory function for HTTP source."""
    return HttpConfig(
        name=name,
        kind="http",
        base_url=config_data["baseUrl"],
        timeout=config_data.get("timeout", "30s"),
        default_headers=config_data.get("headers", {}),
        query_params=config_data.get("queryParams", {})
    )