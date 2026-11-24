"""Root entry point for local development.

Run locally:
    uv run python main.py

Or via the installed script:
    uv run mcp-vcare-compass
"""

from mcp_vcare_compass.app import main

if __name__ == "__main__":
    main()
