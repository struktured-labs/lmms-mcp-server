"""FastMCP server for LMMS music production."""

from mcp.server.fastmcp import FastMCP

from lmms_mcp.tools import project, tracks, patterns, bb, automation, sf2, voice, filters, effects, synths

# Create FastMCP server
mcp = FastMCP("lmms-mcp")


# Register tools from modules
project.register(mcp)
tracks.register(mcp)
patterns.register(mcp)
bb.register(mcp)
automation.register(mcp)
sf2.register(mcp)
voice.register(mcp)
filters.register(mcp)
effects.register(mcp)
synths.register(mcp)


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
