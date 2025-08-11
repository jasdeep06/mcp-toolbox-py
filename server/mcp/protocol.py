# mcp_toolbox/server/mcp/protocol.py (updated)
import json
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from tools.toolsets import Toolset
import logging

logger = logging.getLogger(__name__)

@dataclass
class McpRequest:
    """MCP request structure."""
    jsonrpc: str
    method: str
    id: Optional[Any] = 999
    params: Optional[Dict[str, Any]] = None

@dataclass 
class McpResponse:
    """MCP response structure."""
    jsonrpc: str
    id: Any
    # error: Optional[Dict[str, Any]] = {}
    result: Optional[Any] = None

class McpServer:
    """MCP protocol server implementation with toolset support."""
    
    def __init__(self, tools: Dict[str, Any], toolsets: Dict[str, Toolset]):
        self.tools = tools
        self.toolsets = toolsets
        self.initialized = False
        
        # Create default toolset with all tools if not exists
        if "" not in self.toolsets:
            self.toolsets[""] = Toolset("", self.tools, "Default toolset with all tools")
    
    async def handle_request(self, request_data: str, toolset_name: str = "") -> Optional[str]:
        """Handle incoming MCP request for a specific toolset."""
        try:
            logger.info(f"Request {request_data}")
            request_json = json.loads(request_data)
            request = McpRequest(**request_json)
            logger.info(f"Listing :")
            response = await self._process_request(request, toolset_name)
            logger.info(f"Response: {response}")
            if response:
                return json.dumps(response.__dict__)
            return None
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            error_response = McpResponse(
                jsonrpc="2.0",
                id=None,
                error={"code": -32603, "message": str(e)}
            )
            return json.dumps(error_response.__dict__)
    
    async def _process_request(self, request: McpRequest, toolset_name: str) -> Optional[McpResponse]:
        """Process specific MCP request types for a toolset."""
        if request.method == "initialize":
            initialize_response = await self._handle_initialize(request)
            logger.info(f"Initialize response: {initialize_response}")
            return initialize_response
        elif request.method == "notifications/initialized":
            return await self._handle_notifications(request)

        elif request.method == "tools/list":
            logger.info(f"Listing :")
            return await self._handle_list_tools(request, toolset_name)
        elif request.method == "tools/call":
            return await self._handle_call_tool(request, toolset_name)
        else:
            return McpResponse(
                jsonrpc="2.0",
                id=request.id,
                error={"code": -32601, "message": f"Method not found: {request.method}"}
            )
    
    async def _handle_initialize(self, request: McpRequest) -> McpResponse:
        """Handle initialization request."""
        logger.info(f"Initializing MCP server")
        self.initialized = True
        return McpResponse(
            jsonrpc="2.0",
            id=request.id,
            result={
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "Python MCP Toolbox", "version": "1.0.0"}
            }
        )

    async def _handle_notifications(self, request: McpRequest) -> McpResponse:
        return McpResponse(
            jsonrpc="2.0",
            id=request.id,
            result={}
        )
    
    async def _handle_list_tools(self, request: McpRequest, toolset_name: str) -> McpResponse:
        """Handle tools list request for a specific toolset."""
        print(self.toolsets)
        if toolset_name not in self.toolsets:
            return McpResponse(
                jsonrpc="2.0",
                id=request.id,
                error={"code": -32602, "message": f"Toolset not found: {toolset_name}"}
            )
        
        toolset = self.toolsets[toolset_name]
        tools_list = toolset.get_mcp_tools_list()
        
        return McpResponse(
            jsonrpc="2.0",
            id=request.id,
            result={"tools": tools_list}
        )
    
    async def _handle_call_tool(self, request: McpRequest, toolset_name: str) -> McpResponse:
        """Handle tool call request for a specific toolset."""
        params = request.params or {}
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        # Get the appropriate toolset
        if toolset_name not in self.toolsets:
            return McpResponse(
                jsonrpc="2.0",
                id=request.id,
                error={"code": -32602, "message": f"Toolset not found: {toolset_name}"}
            )
        
        toolset = self.toolsets[toolset_name]
        
        if not toolset.has_tool(tool_name):
            return McpResponse(
                jsonrpc="2.0",
                id=request.id,
                error={"code": -32602, "message": f"Tool not found in toolset: {tool_name}"}
            )
        
        tool = toolset.get_tool(tool_name)
        try:
            results = await tool.invoke(arguments)
            logger.info(f"Results: {results}")
            return McpResponse(
                jsonrpc="2.0",
                id=request.id,
                result={
                    "content": [{"type": "text", "text": json.dumps(results, default=str)}]
                }
            )
        except Exception as e:
            return McpResponse(
                jsonrpc="2.0",
                id=request.id,
                result={
                    "content": [{"type": "text", "text": str(e)}],
                    "isError": True
                }
            )