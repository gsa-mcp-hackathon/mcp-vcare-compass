"""Custom HTTP routes for the MCP server.

These are only active when the server runs over HTTP (streamable-http). They
sit alongside the `/mcp` endpoint on the same app.

The `/health` route matters for cloud deploys: Databricks Apps, IBM Code
Engine, and cloud.gov use an HTTP health check to decide the app started
correctly. Keep it fast and dependency-free.
"""

from __future__ import annotations

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse

from mcp_vcare_compass import __version__

TOOL_NAMES = (
    "get_consult_pathway_checklist",
    "flag_high_risk_case",
    "ask_vcare_case_data",
)


def register_routes(mcp: FastMCP) -> None:
    """Register custom HTTP routes with the server."""

    @mcp.custom_route("/", methods=["GET"])
    async def home(request: Request) -> PlainTextResponse:
        """Landing page: open the app URL in a browser to confirm the server is up."""
        return PlainTextResponse(
            f"VCARE CC Compass MCP server is running (version {__version__}).\n"
            f"Tools: {', '.join(TOOL_NAMES)}\n"
            "MCP endpoint: /mcp\n"
        )

    @mcp.custom_route("/health", methods=["GET"])
    async def health_check(request: Request) -> JSONResponse:
        return JSONResponse({"status": "healthy", "service": "mcp-vcare-compass"})

    @mcp.custom_route("/version", methods=["GET"])
    async def version(request: Request) -> JSONResponse:
        return JSONResponse({"version": __version__})
