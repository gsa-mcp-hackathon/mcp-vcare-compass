"""Resources submodule — static/semi-static data the client can read directly.

Resources are addressable by URI and don't require a tool call. VCARE CC
Compass ships none yet; this aggregator keeps the template's extension point.

To add a resource:
  1. Create `resources/<group>.py` with a `register(mcp)` function.
  2. Import it below and call `<group>.register(mcp)` inside register_resources.
"""

from __future__ import annotations


def register_resources(mcp) -> None:
    """Register all resources with the MCP server (none yet)."""


__all__ = ["register_resources"]
