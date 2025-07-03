import asyncio
import click
from server.config import ServerConfig
from server.server import ToolboxServer


import logging, sys
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
@click.command()
@click.option('--tools-file', default='tools.yaml', 
              help='Path to tools configuration file')
@click.option('--stdio', is_flag=True, 
              help='Use STDIO transport instead of HTTP')
@click.option('--host', default='127.0.0.1',
              help='Host to bind HTTP server to')
@click.option('--port', default=5000, type=int,
              help='Port to bind HTTP server to')
def serve(tools_file: str, stdio: bool, host: str, port: int):
    """Start the MCP server."""


    config = ServerConfig.from_yaml(tools_file)
    server = ToolboxServer(config)
    
    async def run_server():
        await server.initialize()
        try:
            if stdio:
                await server.serve_stdio()
            else:
                await server.serve_http(host, port)
        finally:
            await server.cleanup()
    
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        print("\nServer stopped")

@click.group()
def cli():
    """Python MCP Toolbox CLI."""
    pass

cli.add_command(serve)