import json
import re
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from string import Template
from urllib.parse import urljoin
from tools.base import Tool, ToolConfig
from tools.registry import register_tool
from tools.parameters import ParameterSet, create_parameter_set, Parameter, ParameterType
from sources.http.source import HttpSource
from sources.base import Source

@dataclass
class HttpToolConfig(ToolConfig):
    path: str
    method: str = "GET"
    headers: Optional[Dict[str, str]] = None
    request_body: Optional[str] = None
    path_params: Optional[List[Parameter]] = None
    query_params: Optional[List[Parameter]] = None
    body_params: Optional[List[Parameter]] = None
    header_params: Optional[List[Parameter]] = None

    def __post_init__(self):
        # Validate HTTP method
        valid_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
        if self.method.upper() not in valid_methods:
            raise ValueError(f"{self.method} is not a valid http method")
        
        # Set defaults
        if self.headers is None:
            self.headers = {}
        if self.path_params is None:
            self.path_params = []
        if self.query_params is None:
            self.query_params = []
        if self.body_params is None:
            self.body_params = []
        if self.header_params is None:
            self.header_params = []

    def create_tool(self, sources: Dict[str, Source]) -> 'HttpTool':
        if self.source not in sources:
            raise ValueError(f"Source '{self.source}' not found")
        
        source = sources[self.source]
        if not isinstance(source, HttpSource):
            raise ValueError(f"Source '{self.source}' must be an HTTP source")
        
        # Combine all parameters
        all_params = self.path_params + self.query_params + self.body_params + self.header_params
        
        # Check for duplicate parameter names
        param_names = [p.name for p in all_params]
        if len(param_names) != len(set(param_names)):
            duplicates = [name for name in param_names if param_names.count(name) > 1]
            raise ValueError(f"Parameter name must be unique across pathParams, queryParams, bodyParams, and headerParams. Duplicate parameters: {', '.join(set(duplicates))}")
        
        parameter_set = ParameterSet(all_params)
        
        return HttpTool(
            name=self.name,
            description=self.description,
            source=source,
            path=self.path,
            method=self.method.upper(),
            headers=self.headers,
            request_body=self.request_body,
            path_params=self.path_params,
            query_params=self.query_params,
            body_params=self.body_params,
            header_params=self.header_params,
            parameter_set=parameter_set,
            auth_required=self.auth_required
        )

class HttpTool(Tool):
    """Tool for making HTTP requests with support for dynamic paths."""
    
    def __init__(self, name: str, description: str, source: HttpSource,
                 path: str, method: str = "GET", 
                 headers: Optional[Dict[str, str]] = None,
                 request_body: Optional[str] = None,
                 path_params: Optional[List[Parameter]] = None,
                 query_params: Optional[List[Parameter]] = None,
                 body_params: Optional[List[Parameter]] = None,
                 header_params: Optional[List[Parameter]] = None,
                 parameter_set: Optional[ParameterSet] = None,
                 auth_required: Optional[List[str]] = None):
        
        all_params = (path_params or []) + (query_params or []) + (body_params or []) + (header_params or [])
        super().__init__(name, "http", description, all_params, auth_required)
        
        self.source = source
        self.path = path
        self.method = method
        self.headers = headers or {}
        self.request_body = request_body
        self.path_params = path_params or []
        self.query_params = query_params or []
        self.body_params = body_params or []
        self.header_params = header_params or []
        self.parameter_set = parameter_set or ParameterSet([])
    
    def _build_url(self, validated_params: Dict[str, Any]) -> str:
        """Build the complete URL with path parameter substitution."""
        # Handle path parameter templating
        templated_path = self.path
        
        # Extract path parameters and substitute them
        for param in self.path_params:
            if param.name in validated_params:
                value = validated_params[param.name]
                # Use safe template substitution - convert Go template syntax {{.param}} to Python ${param}
                go_template_pattern = r'\{\{\s*\.' + re.escape(param.name) + r'\s*\}\}'
                python_template_var = f"${{{param.name}}}"
                templated_path = re.sub(go_template_pattern, python_template_var, templated_path)
        
        # Now use Python Template for safe substitution
        path_values = {}
        for param in self.path_params:
            if param.name in validated_params:
                path_values[param.name] = str(validated_params[param.name])
        
        try:
            template = Template(templated_path)
            final_path = template.safe_substitute(path_values)
        except KeyError as e:
            raise ValueError(f"Missing required path parameter: {e}")
        
        # Build the complete URL
        base_url = self.source.base_url.rstrip('/')
        clean_path = final_path.lstrip('/')
        full_url = f"{base_url}/{clean_path}"
        
        print(f"Full URL: {full_url}")

        return full_url
    
    def _get_query_params(self, validated_params: Dict[str, Any]) -> Dict[str, Any]:
        """Extract query parameters from validated params."""
        query_params = {}
        for param in self.query_params:
            if param.name in validated_params:
                query_params[param.name] = validated_params[param.name]
        return query_params
    
    def _get_header_params(self, validated_params: Dict[str, Any]) -> Dict[str, str]:
        """Extract header parameters from validated params."""
        header_params = {}
        for param in self.header_params:
            if param.name in validated_params:
                header_params[param.name] = str(validated_params[param.name])
        return header_params
    
    def _build_request_body(self, validated_params: Dict[str, Any]) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Build request body, returning (data, json) tuple."""
        request_data = None
        request_json = None
        
        if self.request_body and self.body_params:
            # Use template substitution for request body
            body_values = {}
            for param in self.body_params:
                if param.name in validated_params:
                    value = validated_params[param.name]
                    # Convert Go template syntax {{.param}} to Python ${param}
                    if isinstance(value, (dict, list)):
                        body_values[param.name] = json.dumps(value)
                    elif isinstance(value, bool):
                        body_values[param.name] = 'true' if value else 'false'
                    else:
                        body_values[param.name] = value
            
            # Convert Go template syntax to Python template syntax
            python_template_body = re.sub(r'\{\{\s*\.(\w+)\s*\}\}', r'${\1}', self.request_body)
            
            try:
                template = Template(python_template_body)
                request_data = template.safe_substitute(body_values)
            except KeyError as e:
                raise ValueError(f"Missing required body parameter in template: {e}")
            request_json = json.loads(request_data)
            request_data = None
        elif self.body_params:
            # No template, use params as JSON body
            body_data = {}
            for param in self.body_params:
                if param.name in validated_params:
                    body_data[param.name] = validated_params[param.name]
            request_json = body_data
        
        return request_data, request_json
    
    async def invoke(self, params: Dict[str, Any]) -> List[Any]:
        """Execute the HTTP request with parameters."""
        # Validate parameters
        validated_params = self.parameter_set.validate_values(params)

        print(f"Validated params: {validated_params}")
        
        # Build URL with path parameter substitution
        url = self._build_url(validated_params)

        print(f"Url: {url}")
        
        # Extract query parameters
        query_params = self._get_query_params(validated_params)

        print(f"Query params: {query_params}")
        # Extract header parameters and merge with default headers
        header_params = self._get_header_params(validated_params)
        merged_headers = {**self.headers, **header_params}

        print(f"Merged headers: {merged_headers}")
        # Build request body
        request_data, request_json = self._build_request_body(validated_params)

        print(f"Request data: {request_data}, Request json: {request_json}")
        # Make the HTTP request
        print(f"Url : {url}, Method : {self.method}, Headers : {merged_headers}, Params : {query_params}, Data : {request_data}, Json : {request_json}")
        try:
            response = await self.source.request(
                method=self.method,
                path=url,  # Pass full URL since we built it ourselves
                headers=merged_headers if merged_headers else None,
                params=query_params if query_params else None,
                data=request_data,
                json=request_json
            )
            print("HTTP response: ", response)
            
            # Return response data
            data = response.get("data")
            if isinstance(data, list):
                return data
            else:
                return [data]
                
        except Exception as e:
            raise RuntimeError(f"HTTP request failed: {e}")
    
    def get_mcp_manifest(self) -> Dict[str, Any]:
        """Return MCP-compatible tool manifest."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.parameter_set.to_mcp_schema()
        }

def _parse_parameters(param_configs: Optional[List[Dict[str, Any]]]) -> List[Parameter]:
    """Parse parameter configurations into Parameter objects."""
    if not param_configs:
        return []
    
    parameters = []
    for config in param_configs:
        param = Parameter(
            name=config["name"],
            type=ParameterType(config["type"]),
            description=config["description"],
            required=config.get("required", True),
            default=config.get("default"),
            enum=config.get("enum"),
            minimum=config.get("minimum"),
            maximum=config.get("maximum"),
            min_length=config.get("minLength"),
            max_length=config.get("maxLength"),
            pattern=config.get("pattern")
        )
        parameters.append(param)
    
    return parameters

@register_tool("http")
def create_http_tool_config(name: str, config_data: Dict) -> HttpToolConfig:
    """Factory function for HTTP tool."""
    return HttpToolConfig(
        name=name,
        kind="http",
        source=config_data["source"],
        description=config_data["description"],
        path=config_data["path"],
        method=config_data.get("method", "GET"),
        headers=config_data.get("headers", {}),
        request_body=config_data.get("requestBody"),
        path_params=_parse_parameters(config_data.get("pathParams")),
        query_params=_parse_parameters(config_data.get("queryParams")),
        body_params=_parse_parameters(config_data.get("bodyParams")),
        header_params=_parse_parameters(config_data.get("headerParams")),
        auth_required=config_data.get("authRequired")
    )