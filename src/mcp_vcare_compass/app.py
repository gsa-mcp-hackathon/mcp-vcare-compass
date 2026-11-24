"""VCARE CC Compass MCP server entry point.

Keep this file THIN. It only:
  1. creates the FastMCP instance,
  2. registers tools / prompts / resources / routes from the submodules, and
  3. decides which transport to run (stdio locally vs. HTTP when deployed).

All real logic lives in the submodules:
  - tools/      one file per tool (each exposes `register(mcp)`)
  - pathway.py  GEMBA consult-pathway checklist content
  - rules.py    flag_high_risk_case screening rules and thresholds
  - genie.py    Genie agent client for ask_vcare_case_data
  - notices.py  boundary notices returned with every result
  - routes.py   HTTP-only infrastructure (/, /health, /version)
  - config.py   settings loaded from env vars / .env
  - models.py   Pydantic models & enums for tool parameters

Data posture: synthetic only. No PHI/PII. Not a clinical
determination.
"""

from __future__ import annotations

import os

from fastmcp import FastMCP

from mcp_vcare_compass.config import settings
from mcp_vcare_compass.prompts import register_prompts
from mcp_vcare_compass.resources import register_resources
from mcp_vcare_compass.routes import register_routes
from mcp_vcare_compass.tools import register_tools

mcp = FastMCP(
    name="VCARE CC Compass",
    instructions=(
        "VCARE CC Compass supports Community Care consult and care coordination "
        "review. get_consult_pathway_checklist explains what to observe at each "
        "pathway step. flag_high_risk_case screens one synthetic case for "
        "timeliness and patient-safety flags. ask_vcare_case_data answers "
        "questions about the synthetic consult case data (risk, compliance, "
        "reviewer actions, facilities) via a Genie agent. No tool certifies "
        "compliance or makes a clinical determination."
    ),
)

# Wire up everything the server exposes. Each aggregator lives in its submodule.
register_tools(mcp)
register_prompts(mcp)
register_resources(mcp)
register_routes(mcp)

# Read-only tools with no per-session state: serve stateless, plain-JSON
# responses, which behave best behind the Databricks Apps proxy.
HTTP_OPTIONS = {"stateless_http": True, "json_response": True}


def main() -> None:
    """Start the server, choosing a transport based on the environment.

    Precedence:
      1. A platform-injected port (Databricks `DATABRICKS_APP_PORT` or a generic
         `PORT`) → run HTTP on that port. Cloud hosts set this for you.
      2. `MCP_TRANSPORT=streamable-http` in the environment → run HTTP on
         `MCP_HOST`:`MCP_PORT` (see config.py / .env).
      3. Otherwise → stdio, which is how local clients (Claude Desktop, Claude
         Code, Zed) launch the server as a subprocess.
    """
    platform_port = os.getenv("DATABRICKS_APP_PORT") or os.getenv("PORT")

    if platform_port:
        mcp.run(
            transport="http", host="0.0.0.0", port=int(platform_port), **HTTP_OPTIONS
        )
    elif settings.mcp_transport == "streamable-http":
        mcp.run(
            transport="streamable-http",
            host=settings.mcp_host,
            port=settings.mcp_port,
            **HTTP_OPTIONS,
        )
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
