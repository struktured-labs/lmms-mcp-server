"""XML parsing and writing for LMMS project files."""

from lmms_mcp.xml.parser import parse_project
from lmms_mcp.xml.writer import write_project

__all__ = ["parse_project", "write_project"]
