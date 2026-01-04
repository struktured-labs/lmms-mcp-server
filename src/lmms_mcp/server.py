"""FastMCP server for LMMS music production."""

from mcp.server.fastmcp import FastMCP

from lmms_mcp.tools import project, tracks, patterns

# Create FastMCP server
mcp = FastMCP("lmms-mcp")


# Register tools from modules
project.register(mcp)
tracks.register(mcp)
patterns.register(mcp)


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
