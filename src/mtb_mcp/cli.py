"""CLI entry point for the MTB MCP Server."""

from mtb_mcp.server import mcp


def main() -> None:
    """Run the MCP server with stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
