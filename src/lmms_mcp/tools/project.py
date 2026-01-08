"""Project management tools for LMMS."""

import subprocess
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
    def render(
        path: str,
        output_path: str | None = None,
        format: str = "flac",
        start_bar: int | None = None,
        end_bar: int | None = None,
        play: bool = False,
    ) -> dict[str, Any]:
        """Render an LMMS project to audio.

        Can render full project or specific bar range (segment).

        Args:
            path: Path to .mmp or .mmpz file
            output_path: Output audio file path (optional, auto-generated if not provided)
            format: Audio format: flac, wav, ogg (default: flac)
            start_bar: Starting bar number for segment (0-indexed, optional)
            end_bar: Ending bar number for segment (exclusive, optional)
            play: If True, play the audio after rendering (default False)

        Returns:
            Render info with audio path and timing details
        """
        filepath = Path(path)
        cli = LMMSCli()

        # If no segment specified, do a simple full render
        if start_bar is None and end_bar is None:
            result = cli.render(filepath, output_path=output_path, format=format)
            if play and result.get("status") == "success":
                play_result = play_audio(result["output_path"], wait=True)
                result["playback"] = play_result
            return result

        # Otherwise, render segment
        project = parse_project(filepath)

        # Default start_bar to 0 if not specified
        if start_bar is None:
            start_bar = 0

        # Calculate time positions based on BPM and time signature
        bpm = project.bpm
        beats_per_bar = project.time_sig_num
        seconds_per_beat = 60.0 / bpm
        seconds_per_bar = seconds_per_beat * beats_per_bar

        start_time = start_bar * seconds_per_bar

        if end_bar is None:
            duration = None
            duration_str = "to end"
        else:
            end_time = end_bar * seconds_per_bar
            duration = end_time - start_time
            duration_str = f"{duration:.2f}s"

        # First, render the full project to a temp file
        temp_render_path = filepath.with_suffix(".flac")
        full_render = cli.render(filepath, output_path=str(temp_render_path), format="flac")

        if full_render.get("status") != "success":
            return {
                "status": "error",
                "error": "Failed to render project",
                "details": full_render,
            }

        # Generate output path for segment
        if output_path is None:
            segment_name = filepath.stem + f"_bars_{start_bar}-{end_bar if end_bar else 'end'}.flac"
            output_path = str(filepath.parent / segment_name)

        # Extract segment using ffmpeg
        ffmpeg_cmd = [
            "ffmpeg",
            "-y",  # Overwrite output
            "-ss", str(start_time),  # Start time
        ]

        if duration is not None:
            ffmpeg_cmd.extend(["-t", str(duration)])  # Duration

        ffmpeg_cmd.extend([
            "-i", str(temp_render_path),  # Input file
            "-c", "copy",  # Copy codec (no re-encoding)
            output_path,
        ])

        try:
            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                return {
                    "status": "error",
                    "error": "Failed to extract segment",
                    "ffmpeg_error": result.stderr,
                }

            segment_info = {
                "status": "success",
                "output_path": output_path,
                "start_bar": start_bar,
                "end_bar": end_bar,
                "start_time": f"{start_time:.2f}s",
                "duration": duration_str,
                "bpm": bpm,
                "time_signature": f"{project.time_sig_num}/{project.time_sig_den}",
            }

            # Play the segment if requested
            if play:
                play_result = play_audio(output_path, wait=True)
                segment_info["playback"] = play_result

            return segment_info

        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "error": "Segment extraction timed out",
            }

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

        result = {
            "description": project.to_description(),
            "summary": project.describe(),
            "render_info": render_result,
        }

        if render_result.get("status") == "success":
            result["audio_path"] = render_result["output_path"]
        else:
            result["audio_path"] = None
            result["render_error"] = render_result.get("error", "Unknown error")

        return result

    @mcp.tool()
    def play_audio(
        path: str,
        wait: bool = True,
    ) -> dict[str, Any]:
        """Play an audio file through the system audio player.

        Args:
            path: Path to audio file (flac, wav, ogg, mp3)
            wait: If True, wait for playback to complete (default True)

        Returns:
            Status of playback
        """
        audio_path = Path(path)
        if not audio_path.exists():
            return {"status": "error", "message": f"File not found: {path}"}

        # Try different audio players in order of preference
        players = [
            ["ffplay", "-nodisp", "-autoexit", str(audio_path)],
            ["paplay", str(audio_path)],
            ["aplay", str(audio_path)],
        ]

        for player_cmd in players:
            try:
                if wait:
                    result = subprocess.run(
                        player_cmd,
                        capture_output=True,
                        timeout=300,  # 5 minute max
                    )
                    return {
                        "status": "played",
                        "file": str(audio_path),
                        "player": player_cmd[0],
                    }
                else:
                    subprocess.Popen(
                        player_cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    return {
                        "status": "playing",
                        "file": str(audio_path),
                        "player": player_cmd[0],
                    }
            except FileNotFoundError:
                continue
            except subprocess.TimeoutExpired:
                return {"status": "timeout", "file": str(audio_path)}
            except Exception as e:
                continue

        return {
            "status": "error",
            "message": "No audio player found (tried ffplay, paplay, aplay)",
        }
