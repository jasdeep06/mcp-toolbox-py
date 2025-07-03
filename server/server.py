import server.logging_setup
import asyncio
import sys
from typing import Dict, Any, Optional
from server.config import ServerConfig
from server.mcp.protocol import McpServer
from server.http_server import HttpMcpServer
from tools.toolsets import create_toolsets
import logging
from server.hook_utils import load_hook_from_path, run_hook
from server.metadata_utils import connect_to_metadata_source, get_column_descriptions, resolve_column_descriptions

access_logger = logging.getLogger("httplog")

class ToolboxServer:
    """Main MCP Toolbox server with HTTP and STDIO support."""
    
    def __init__(self, config: ServerConfig):
        self.config = config
        self.sources: Dict[str, Any] = {}
        self.tools: Dict[str, Any] = {}
        self.toolsets: Dict[str, Any] = {}
        self.mcp_server: Optional[McpServer] = None
        self.http_server: Optional[HttpMcpServer] = None
    
    async def initialize(self):
        """Initialize the server."""
        # Create and initialize sources
        self.sources = self.config.create_sources()
        for source in self.sources.values():
            await source.initialize()
        
        # Create tools
        self.tools = self.config.create_tools(self.sources)

        #connect to metadata source
        self.metadata_source = await connect_to_metadata_source(self.config.metadata_source)

        # attach pre_hook to tools invoke
        self.attach_pre_hook()
                

        # Create toolsets
        self.toolsets = create_toolsets(self.config.toolsets, self.tools)
        
        # Create MCP server
        self.mcp_server = McpServer(self.tools, self.toolsets)
    
    
    
    
    def attach_pre_hook(self):
        for tool,tool_config in self.config.tools.items():
            if tool_config.get("pre_hook") or tool_config.get("datasource_ids"):
                pre_hook = tool_config.get("pre_hook")
                if pre_hook:
                    hook = load_hook_from_path(pre_hook)
                else:
                    hook = None
                datasource_ids = tool_config.get("datasource_ids")
                if datasource_ids:
                    datasource_ids = datasource_ids.split(",")

                orig_invoke = self.tools[tool].invoke
                async def wrapped_invoke(params, _hook=hook, _datasource_ids=datasource_ids, _orig_invoke=orig_invoke):
                    if hook:
                        await run_hook(_hook, params)
                    result = await _orig_invoke(params)
                    if _datasource_ids and result[0]['data']:
                        column_descriptions = await get_column_descriptions(self.metadata_source, _datasource_ids)
                        column_list = list(result[0]['data'][0].keys())
                        column_descriptions = resolve_column_descriptions(column_list, column_descriptions)
                        result.append({"column_descriptions": column_descriptions})
                    return result

                self.tools[tool].invoke = wrapped_invoke
                    
                    
    
    async def serve_stdio(self):
        """Serve using STDIO transport."""
        print("MCP server ready (STDIO mode)", file=sys.stderr)
        
        while True:
            try:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )
                if not line:
                    break
                
                response = await self.mcp_server.handle_request(line.strip())
                if response:
                    print(response, flush=True)
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error in STDIO mode: {e}", file=sys.stderr)
    
    async def serve_http(self, host: str = "127.0.0.1", port: int = 5000):
        """Serve using HTTP transport."""
        self.http_server = HttpMcpServer(self.mcp_server, host, port)
        runner = await self.http_server.start()
        
        try:
            print(f"MCP server ready at http://{host}:{port}", file=sys.stderr)
            # Keep server running
            while True:
                await asyncio.sleep(3600)  # Sleep for 1 hour, then check again
        except KeyboardInterrupt:
            print("Shutting down HTTP server...", file=sys.stderr)
        finally:
            await runner.cleanup()
    
    async def cleanup(self):
        """Clean up server resources."""
        for source in self.sources.values():
            await source.cleanup()