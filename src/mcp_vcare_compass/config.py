"""Server configuration loaded from environment variables or a .env file.

Every field can be overridden by an environment variable of the same name
(upper- or lower-case). Copy `.env.example` to `.env` for local development.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """MCP server settings. Override any field via environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Transport ─────────────────────────────────────────────────────────────────────
    # "stdio"           — local subprocess (Claude Desktop / Claude Code / Zed)
    # "streamable-http" — remote HTTP server (containers, cloud deploys)
    #
    # NOTE: app.py also auto-selects HTTP when a platform injects DATABRICKS_APP_PORT
    # or PORT, so you usually do NOT need to set this on a cloud host.
    mcp_transport: str = "stdio"
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8000

    # ── Genie agent (ask_vcare_case_data) ─────────────────────────────────────────
    # Space ID of the "Healthcare Risk and Coordination Analysis" Genie agent.
    # On Databricks Apps this comes from the `genie-space` app resource via
    # app.yaml (GENIE_SPACE_ID). Databricks credentials are read by the SDK from
    # the environment (the app service principal when deployed).
    genie_space_id: str = ""
    genie_timeout_seconds: int = 120
    genie_preview_rows: int = 20


settings = Settings()
