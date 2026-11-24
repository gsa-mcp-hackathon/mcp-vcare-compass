"""Prompts submodule — reusable conversation starters.

Prompts appear in the client UI as slash commands / preset starters. VCARE CC
Compass ships none yet; this aggregator keeps the template's extension point.

To add a prompt:
  1. Create `prompts/<group>.py` with a `register(mcp)` function.
  2. Import it below and call `<group>.register(mcp)` inside register_prompts.
"""

from __future__ import annotations


def register_prompts(mcp) -> None:
    """Register all prompts with the MCP server (none yet)."""


__all__ = ["register_prompts"]
