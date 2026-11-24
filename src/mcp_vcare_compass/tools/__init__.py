"""Tools submodule — one tool per file.

Each tool module exposes a `register(mcp)` function that attaches its
`@mcp.tool`-decorated function to the server. This file aggregates them into a
single `register_tools(mcp)` that `app.py` calls.

To add a tool:
  1. Create `tools/<your_tool>.py` with a `register(mcp)` function.
  2. Import it below and call `<your_tool>.register(mcp)` inside register_tools.
  3. Add its name to `routes.TOOL_NAMES` and the server instructions in app.py.
"""

from __future__ import annotations

from mcp_vcare_compass.tools import case_data, flag_case, pathway_checklist


def register_tools(mcp) -> None:
    """Register all tools with the MCP server."""
    pathway_checklist.register(mcp)
    flag_case.register(mcp)
    case_data.register(mcp)


__all__ = ["register_tools"]
