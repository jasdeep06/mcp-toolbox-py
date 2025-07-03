# import asyncio
# from toolbox_core import ToolboxClient

# async def main():
#     # Replace with the actual URL where your Toolbox service is running
#     async with ToolboxClient("http://127.0.0.1:8002") as toolbox:
#         tools = await toolbox.load_toolset()
#         print(tools)

# if __name__ == "__main__":
#     asyncio.run(main())

from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession
import asyncio

async def main():
    # Connect to a streamable HTTP server
    async with streamablehttp_client("http://127.0.0.1:8002/mcp/user-workspace-server/sse") as (
        read_stream,
        write_stream,
        _,
    ):
        # Create a session using the client streams
        async with ClientSession(read_stream, write_stream) as session:
            # Initialize the connection
            await session.initialize()
            # Call a tool
            # tool_result = await session.call_tool("echo", {"message": "hello"})
            tools = await session.list_tools()

            print(tools)

if __name__ == "__main__":
    asyncio.run(main())
