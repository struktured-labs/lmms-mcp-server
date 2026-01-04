"""Project management tools for LMMS."""

from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from lmms_mcp.xml.parser import parse_project
from lmms_mcp.xml.writer import write_project
from lmms_mcp.models.project import Project
from lmms_mcp.cli import LMMSCli


def register(mcp: FastMCP) -> None:
    """Register project tools with the MCP server."""

    @mcp.tool()
    def create_project(
        name: str,
        path: str,
        bpm: int = 120,
        time_sig_num: int = 4,
        time_sig_den: int = 4,
    ) -> dict[str, Any]:
        """Create a new LMMS project with basic settings.

        Args:
            name: Project name
            path: Path to save the .mmp file
            bpm: Beats per minute (default 120)
            time_sig_num: Time signature numerator (default 4)
            time_sig_den: Time signature denominator (default 4)

        Returns:
            Project info dict with path and settings
        """
        project = Project(
            name=name,
            bpm=bpm,
            time_sig_num=time_sig_num,
            time_sig_den=time_sig_den,
        )
        filepath = Path(path)
        write_project(project, filepath)
        return {
            "status": "created",
            "path": str(filepath),
            "name": name,
            "bpm": bpm,
            "time_signature": f"{time_sig_num}/{time_sig_den}",
        }

    @mcp.tool()
    def load_project(path: str) -> dict[str, Any]:
        """Load an existing LMMS project and return its summary.

        Args:
            path: Path to .mmp or .mmpz file

        Returns:
            Project summary with tracks, patterns, and settings
        """
        filepath = Path(path)
        project = parse_project(filepath)
        return project.describe()

    @mcp.tool()
    def describe_project(path: str) -> dict[str, Any]:
        """Get a human-readable description of an LMMS project.

        Args:
            path: Path to .mmp or .mmpz file

        Returns:
            Detailed description of project structure
        """
        filepath = Path(path)
        project = parse_project(filepath)
        return {
            "description": project.to_description(),
            "summary": project.describe(),
        }

    @mcp.tool()
    def render_preview(
        path: str,
        output_path: str | None = None,
        format: str = "flac",
    ) -> dict[str, Any]:
        """Render an LMMS project to audio using headless mode.

        Args:
            path: Path to .mmp or .mmpz file
            output_path: Output audio file path (optional, auto-generated if not provided)
            format: Audio format: flac, wav, ogg (default: flac)

        Returns:
            Path to rendered audio file and render info
        """
        cli = LMMSCli()
        result = cli.render(Path(path), output_path=output_path, format=format)
        return result

    @mcp.tool()
    def render_and_describe(
        path: str,
        output_path: str | None = None,
    ) -> dict[str, Any]:
        """Render project and return both audio path and description.

        This is the core feedback loop tool - renders audio for listening
        and provides text description of what's in the project.

        Args:
            path: Path to .mmp or .mmpz file
            output_path: Output audio file path (optional)

        Returns:
            Audio path, project description, and summary
        """
        filepath = Path(path)
        project = parse_project(filepath)
        cli = LMMSCli()
        render_result = cli.render(filepath, output_path=output_path, format="flac")
        return {
            "audio_path": render_result["output_path"],
            "description": project.to_description(),
            "summary": project.describe(),
            "render_info": render_result,
        }
