"""Track management tools for LMMS."""

from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from lmms_mcp.xml.parser import parse_project
from lmms_mcp.xml.writer import write_project
from lmms_mcp.models.track import InstrumentTrack, SampleTrack


def register(mcp: FastMCP) -> None:
    """Register track tools with the MCP server."""

    @mcp.tool()
    def list_tracks(path: str) -> list[dict[str, Any]]:
        """List all tracks in an LMMS project.

        Args:
            path: Path to .mmp or .mmpz file

        Returns:
            List of track info dicts with id, name, type, and settings
        """
        project = parse_project(Path(path))
        return [track.describe() for track in project.tracks]

    @mcp.tool()
    def add_instrument_track(
        path: str,
        name: str,
        instrument: str = "tripleoscillator",
        preset: str | None = None,
    ) -> dict[str, Any]:
        """Add an instrument track to the project.

        Args:
            path: Path to .mmp or .mmpz file
            name: Track name
            instrument: Instrument plugin name (default: tripleoscillator)
            preset: Optional preset name to load

        Returns:
            New track info
        """
        project = parse_project(Path(path))
        # For audiofileprocessor, preset is the sample path
        sample_path = preset if instrument == "audiofileprocessor" else None
        track = InstrumentTrack(
            name=name,
            instrument=instrument,
            preset=preset,
            sample_path=sample_path,
        )
        project.add_track(track)
        write_project(project, Path(path))
        return {
            "status": "added",
            "track": track.describe(),
            "track_count": len(project.tracks),
        }

    @mcp.tool()
    def add_sample_track(
        path: str,
        name: str,
        sample_path: str,
    ) -> dict[str, Any]:
        """Add a sample-based track to the project.

        Args:
            path: Path to .mmp or .mmpz file
            name: Track name
            sample_path: Path to audio sample file

        Returns:
            New track info
        """
        project = parse_project(Path(path))
        track = SampleTrack(
            name=name,
            sample_path=sample_path,
        )
        project.add_track(track)
        write_project(project, Path(path))
        return {
            "status": "added",
            "track": track.describe(),
            "track_count": len(project.tracks),
        }

    @mcp.tool()
    def remove_track(path: str, track_id: int) -> dict[str, Any]:
        """Remove a track from the project.

        Args:
            path: Path to .mmp or .mmpz file
            track_id: ID of track to remove

        Returns:
            Removal status and remaining track count
        """
        project = parse_project(Path(path))
        removed = project.remove_track(track_id)
        if removed:
            write_project(project, Path(path))
            return {
                "status": "removed",
                "track_id": track_id,
                "track_count": len(project.tracks),
            }
        return {
            "status": "not_found",
            "track_id": track_id,
            "track_count": len(project.tracks),
        }

    @mcp.tool()
    def set_track_volume(path: str, track_id: int, volume: float) -> dict[str, Any]:
        """Set the volume of a track.

        Args:
            path: Path to .mmp or .mmpz file
            track_id: ID of track to modify
            volume: Volume level (0.0 to 1.0, can exceed for boost)

        Returns:
            Updated track info
        """
        project = parse_project(Path(path))
        track = project.get_track(track_id)
        if track:
            track.volume = volume
            write_project(project, Path(path))
            return {
                "status": "updated",
                "track": track.describe(),
            }
        return {"status": "not_found", "track_id": track_id}

    @mcp.tool()
    def set_track_pan(path: str, track_id: int, pan: float) -> dict[str, Any]:
        """Set the pan position of a track.

        Args:
            path: Path to .mmp or .mmpz file
            track_id: ID of track to modify
            pan: Pan position (-1.0 = left, 0.0 = center, 1.0 = right)

        Returns:
            Updated track info
        """
        project = parse_project(Path(path))
        track = project.get_track(track_id)
        if track:
            track.pan = pan
            write_project(project, Path(path))
            return {
                "status": "updated",
                "track": track.describe(),
            }
        return {"status": "not_found", "track_id": track_id}

    @mcp.tool()
    def set_track_pitchrange(path: str, track_id: int, pitchrange: int) -> dict[str, Any]:
        """Set the pitch range of an instrument track.

        The pitch range determines how far pitch automation can bend the track.
        For example, pitchrange=24 allows ±24 semitones (±2 octaves).

        Args:
            path: Path to .mmp or .mmpz file
            track_id: ID of track to modify
            pitchrange: Pitch range in semitones (typically 1-24)

        Returns:
            Updated track info
        """
        project = parse_project(Path(path))
        track = project.get_track(track_id)
        if track:
            if isinstance(track, InstrumentTrack):
                track.pitchrange = pitchrange
                write_project(project, Path(path))
                return {
                    "status": "updated",
                    "track_id": track_id,
                    "pitchrange": pitchrange,
                    "track": track.describe(),
                }
            else:
                return {
                    "status": "error",
                    "error": f"Track {track_id} is not an instrument track",
                }
        return {"status": "not_found", "track_id": track_id}
