import asyncio
import json
from typing import Dict, Any, Optional
from aiohttp import web, WSMsgType
from aiohttp.web_request import Request
from aiohttp.web_response import Response, StreamResponse
import uuid
import logging
from server.mcp.protocol import McpServer
import time

access_logger = logging.getLogger("httplog")


@web.middleware
async def access_middleware(request: web.Request, handler):
    t0 = time.perf_counter()
    response = await handler(request)
    elapsed = (time.perf_counter() - t0) * 1000  # ms

    access_logger.info(
        "httpRequest: url='%s' method='%s' path='%s' remoteIP='%s' proto='%s' "
        "httpResponse: status %d bytes %s elapsed=%.3fms",
        str(request.url),
        request.method,
        request.path,
        request.remote,
        f"HTTP/{request.version.major}.{request.version.minor}",
        response.status,
        response.body_length or 0,
        elapsed,
    )
    return response


class HttpMcpServer:
    """HTTP-based MCP server with SSE support."""

    def __init__(
        self, mcp_server: McpServer, host: str = "127.0.0.1", port: int = 5000
    ):
        self.mcp_server = mcp_server
        self.host = host
        self.port = port
        self.app = web.Application(middlewares=[access_middleware])
        self.sse_sessions: Dict[str, "SSESession"] = {}
        self._setup_routes()

    def _setup_routes(self):
        """Setup HTTP routes."""
        # MCP endpoints
        self.app.router.add_post("/mcp", self.handle_mcp_request)
        self.app.router.add_get("/mcp/sse", self.handle_sse_connection)

        # Toolset-specific endpoints
        self.app.router.add_post("/mcp/{toolset_name}", self.handle_mcp_request)
        self.app.router.add_get("/mcp/{toolset_name}/sse", self.handle_sse_connection)

        # Health check
        self.app.router.add_get("/health", self.handle_health)

        # CORS middleware
        self.app.middlewares.append(self._cors_handler)

    @web.middleware
    async def _cors_handler(self, request: Request, handler):
        """Handle CORS headers."""
        response = await handler(request)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response

    async def handle_health(self, request: Request) -> Response:
        """Health check endpoint."""
        return web.json_response({"status": "healthy", "service": "mcp-toolbox"})

    async def handle_mcp_request(self, request: Request) -> Response:
        """Handle MCP JSON-RPC requests."""
        try:
            session_id = request.query.get("sessionId")
            # Get toolset name if specified
            toolset_name = request.match_info.get("toolset_name", "")

            # Read request body
            body = await request.text()

            print("body ", body)

            access_logger.info("Calling.....")
            # Process MCP request
            response_data = await self.mcp_server.handle_request(body, toolset_name)

            access_logger.info(f"Response data: {response_data}")

            if session_id and session_id in self.sse_sessions and response_data:
                await self.sse_sessions[session_id].send_event(
                    "message", json.loads(response_data)
                )

            if response_data:
                return web.Response(text=response_data, content_type="application/json")
            else:
                # No response needed (notification)
                return web.Response(status=204)

        except Exception as e:
            # access_logger.error(f"Error handling MCP request: {e}")
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": "Internal error", "data": str(e)},
            }
            return web.json_response(error_response, status=500)

    async def handle_sse_connection(self, request: Request) -> StreamResponse:
        """Handle Server-Sent Events connection."""
        print("text req ", await request.text())
        session_id = str(uuid.uuid4())
        toolset_name = request.match_info.get("toolset_name", "")

        # logger.info(f"New SSE connection: {session_id}, toolset: {toolset_name}")

        # Create SSE response
        response = web.StreamResponse(
            status=200,
            reason="OK",
            headers={
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            },
        )

        await response.prepare(request)

        # Create session
        session = SSESession(session_id, response, toolset_name)
        self.sse_sessions[session_id] = session

        try:
            proto = request.headers.get(
                "X-Forwarded-Proto", "http" if request.scheme == "http" else "https"
            )
            # Get host
            host = request.host
            # Construct toolset path
            toolset_path = f"/{toolset_name}" if toolset_name else ""
            # Build endpoint URL
            message_endpoint = (
                f"{proto}://{host}/mcp{toolset_path}?sessionId={session_id}"
            )
            access_logger.debug(f"Sending endpoint event: {message_endpoint}")
            # Send initial endpoint event
            await session.send_event("endpoint", message_endpoint)
            # Send initial connection event
            # await session.send_event('connected', {'sessionId': session_id})

            # Keep connection alive
            while not session.closed:
                # Process any queued messages
                await session.process_queue()
                await asyncio.sleep(0.1)

        except Exception as e:
            access_logger.error(f"SSE session error: {e}")
        finally:
            # Clean up session
            if session_id in self.sse_sessions:
                del self.sse_sessions[session_id]
            # logger.info(f"SSE session closed: {session_id}")

        return response

    async def broadcast_to_sessions(
        self, event_type: str, data: Any, toolset_name: str = ""
    ):
        """Broadcast event to all SSE sessions for a specific toolset."""
        for session in self.sse_sessions.values():
            if session.toolset_name == toolset_name:
                await session.send_event(event_type, data)

    async def start(self):
        """Start the HTTP server."""
        runner = web.AppRunner(self.app)
        await runner.setup()

        site = web.TCPSite(runner, self.host, self.port)
        await site.start()

        # logger.info(f"HTTP MCP server started on http://{self.host}:{self.port}")
        return runner


class SSESession:
    """Server-Sent Events session."""

    def __init__(self, session_id: str, response: StreamResponse, toolset_name: str):
        self.session_id = session_id
        self.response = response
        self.toolset_name = toolset_name
        self.closed = False
        self.message_queue = asyncio.Queue()

    async def send_event(self, event_type: str, data: Any):
        """Send an SSE event."""
        if self.closed:
            return

        await self.message_queue.put({"event": event_type, "data": data})

    async def process_queue(self):
        """Process queued messages."""
        try:
            while not self.message_queue.empty():
                message = await asyncio.wait_for(self.message_queue.get(), timeout=0.1)
                access_logger.info(f"Processing SSE message: {message}")
                await self._write_sse_message(message["event"], message["data"])
        except asyncio.TimeoutError:
            pass
        except Exception as e:
            access_logger.error(f"Error processing SSE queue: {e}")
            self.closed = True

    async def _write_sse_message(self, event_type: str, data: Any):
        """Write SSE message to response stream."""
        try:
            data_str = json.dumps(data) if not isinstance(data, str) else data
            message = f"event: {event_type}\ndata: {data_str}\n\n"
            await self.response.write(message.encode("utf-8"))
            await self.response.drain()
        except Exception as e:
            access_logger.error(f"Error writing SSE message: {e}")
            self.closed = True
