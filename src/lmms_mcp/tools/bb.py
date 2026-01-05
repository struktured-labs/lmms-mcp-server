"""Beat+Bassline Editor MCP tools."""

from pathlib import Path
from typing import Any

from lmms_mcp.xml.parser import parse_project
from lmms_mcp.xml.writer import write_project
from lmms_mcp.models.track import BBTrack, BBInstrument


def register(mcp):
    """Register BB Editor tools with the MCP server."""

    @mcp.tool()
    def add_bb_track(
        path: str,
        name: str = "Drums",
        num_steps: int = 16,
        position: int = 0,
        length: int = 4,
    ) -> dict[str, Any]:
        """Add a Beat+Bassline track to the project.

        Args:
            path: Path to .mmp or .mmpz file
            name: Track name
            num_steps: Number of steps per bar (default 16)
            position: Start position in bars (default 0)
            length: Length in song timeline (bars, default 4)

        Returns:
            New BB track info
        """
        project = parse_project(Path(path))

        bb_track = BBTrack(
            name=name,
            num_steps=num_steps,
            bb_position=position,
            bb_length=length,
        )
        project.add_track(bb_track)

        write_project(project, Path(path))

        return {
            "status": "added",
            "track": bb_track.describe(),
            "track_count": len(project.tracks),
        }

    @mcp.tool()
    def add_bb_instrument(
        path: str,
        track_id: int,
        name: str,
        instrument: str = "tripleoscillator",
        sample_path: str | None = None,
    ) -> dict[str, Any]:
        """Add an instrument (drum row) to a BB track.

        Args:
            path: Path to .mmp or .mmpz file
            track_id: ID of BB track to add instrument to
            name: Instrument name (e.g., "Kick", "Snare", "Hi-hat")
            instrument: Instrument plugin (tripleoscillator, audiofileprocessor)
            sample_path: Path to sample file (for audiofileprocessor)

        Returns:
            New instrument info
        """
        project = parse_project(Path(path))

        if track_id >= len(project.tracks):
            return {"status": "error", "error": f"Track {track_id} not found"}

        track = project.tracks[track_id]
        if not isinstance(track, BBTrack):
            return {"status": "error", "error": f"Track {track_id} is not a BB track"}

        bb_inst = BBInstrument(
            name=name,
            instrument=instrument,
            sample_path=sample_path,
            num_steps=track.num_steps,
        )
        track.add_instrument(bb_inst)

        write_project(project, Path(path))

        return {
            "status": "added",
            "instrument": bb_inst.describe(),
            "track_id": track_id,
            "instrument_count": len(track.instruments),
        }

    @mcp.tool()
    def set_bb_steps(
        path: str,
        track_id: int,
        instrument_id: int,
        steps: list[int],
        velocity: int = 100,
    ) -> dict[str, Any]:
        """Set which steps are active for a BB instrument.

        Args:
            path: Path to .mmp or .mmpz file
            track_id: ID of BB track
            instrument_id: ID of instrument within BB track
            steps: List of step numbers to activate (0-based)
            velocity: Velocity for all steps (default 100)

        Returns:
            Updated instrument info with pattern
        """
        project = parse_project(Path(path))

        if track_id >= len(project.tracks):
            return {"status": "error", "error": f"Track {track_id} not found"}

        track = project.tracks[track_id]
        if not isinstance(track, BBTrack):
            return {"status": "error", "error": f"Track {track_id} is not a BB track"}

        bb_inst = track.get_instrument(instrument_id)
        if bb_inst is None:
            return {"status": "error", "error": f"Instrument {instrument_id} not found"}

        # Clear existing steps and set new ones
        bb_inst.clear_steps()
        for step in steps:
            if 0 <= step < bb_inst.num_steps:
                bb_inst.set_step(step, enabled=True, velocity=velocity)

        write_project(project, Path(path))

        return {
            "status": "updated",
            "instrument": bb_inst.describe(),
            "track_id": track_id,
        }

    @mcp.tool()
    def set_bb_pattern(
        path: str,
        track_id: int,
        instrument_id: int,
        pattern: str,
        velocity: int = 100,
    ) -> dict[str, Any]:
        """Set BB pattern using a string representation.

        Args:
            path: Path to .mmp or .mmpz file
            track_id: ID of BB track
            instrument_id: ID of instrument within BB track
            pattern: Pattern string where 'x' or 'X' = hit, '.' or '-' = rest
                     e.g., "x...x...x...x..." for 4-on-the-floor kick
            velocity: Velocity for hits (default 100)

        Returns:
            Updated instrument info
        """
        project = parse_project(Path(path))

        if track_id >= len(project.tracks):
            return {"status": "error", "error": f"Track {track_id} not found"}

        track = project.tracks[track_id]
        if not isinstance(track, BBTrack):
            return {"status": "error", "error": f"Track {track_id} is not a BB track"}

        bb_inst = track.get_instrument(instrument_id)
        if bb_inst is None:
            return {"status": "error", "error": f"Instrument {instrument_id} not found"}

        # Parse pattern string
        bb_inst.clear_steps()
        for i, char in enumerate(pattern):
            if i >= bb_inst.num_steps:
                break
            if char.lower() == 'x':
                bb_inst.set_step(i, enabled=True, velocity=velocity)

        write_project(project, Path(path))

        return {
            "status": "updated",
            "instrument": bb_inst.describe(),
            "track_id": track_id,
        }

    @mcp.tool()
    def describe_bb_track(
        path: str,
        track_id: int,
    ) -> dict[str, Any]:
        """Get a detailed description of a BB track.

        Args:
            path: Path to .mmp or .mmpz file
            track_id: ID of BB track

        Returns:
            BB track description with all instruments and patterns
        """
        project = parse_project(Path(path))

        if track_id >= len(project.tracks):
            return {"status": "error", "error": f"Track {track_id} not found"}

        track = project.tracks[track_id]
        if not isinstance(track, BBTrack):
            return {"status": "error", "error": f"Track {track_id} is not a BB track"}

        instruments = []
        for inst in track.instruments:
            instruments.append({
                "id": inst.id,
                "name": inst.name,
                "pattern": inst.get_step_string(),
                "active_steps": len([s for s in inst.steps if s.enabled]),
                "volume": inst.volume,
                "muted": inst.muted,
            })

        return {
            "name": track.name,
            "num_steps": track.num_steps,
            "bb_position": track.bb_position,
            "bb_length": track.bb_length,
            "instrument_count": len(track.instruments),
            "instruments": instruments,
            "visual": track.to_description(),
        }

    @mcp.tool()
    def list_bb_instruments(
        path: str,
        track_id: int,
    ) -> dict[str, Any]:
        """List all instruments in a BB track.

        Args:
            path: Path to .mmp or .mmpz file
            track_id: ID of BB track

        Returns:
            List of instruments with their patterns
        """
        project = parse_project(Path(path))

        if track_id >= len(project.tracks):
            return {"status": "error", "error": f"Track {track_id} not found"}

        track = project.tracks[track_id]
        if not isinstance(track, BBTrack):
            return {"status": "error", "error": f"Track {track_id} is not a BB track"}

        return {
            "track_id": track_id,
            "track_name": track.name,
            "num_steps": track.num_steps,
            "instruments": [inst.describe() for inst in track.instruments],
        }

    @mcp.tool()
    def remove_bb_instrument(
        path: str,
        track_id: int,
        instrument_id: int,
    ) -> dict[str, Any]:
        """Remove an instrument from a BB track.

        Args:
            path: Path to .mmp or .mmpz file
            track_id: ID of BB track
            instrument_id: ID of instrument to remove

        Returns:
            Removal status
        """
        project = parse_project(Path(path))

        if track_id >= len(project.tracks):
            return {"status": "error", "error": f"Track {track_id} not found"}

        track = project.tracks[track_id]
        if not isinstance(track, BBTrack):
            return {"status": "error", "error": f"Track {track_id} is not a BB track"}

        removed = track.remove_instrument(instrument_id)
        if removed is None:
            return {"status": "error", "error": f"Instrument {instrument_id} not found"}

        write_project(project, Path(path))

        return {
            "status": "removed",
            "removed_instrument": removed.name,
            "remaining_count": len(track.instruments),
        }

    @mcp.tool()
    def set_bb_instrument_volume(
        path: str,
        track_id: int,
        instrument_id: int,
        volume: float,
    ) -> dict[str, Any]:
        """Set the volume of a BB instrument.

        Args:
            path: Path to .mmp or .mmpz file
            track_id: ID of BB track
            instrument_id: ID of instrument
            volume: Volume level (0.0 to 1.0)

        Returns:
            Updated instrument info
        """
        project = parse_project(Path(path))

        if track_id >= len(project.tracks):
            return {"status": "error", "error": f"Track {track_id} not found"}

        track = project.tracks[track_id]
        if not isinstance(track, BBTrack):
            return {"status": "error", "error": f"Track {track_id} is not a BB track"}

        bb_inst = track.get_instrument(instrument_id)
        if bb_inst is None:
            return {"status": "error", "error": f"Instrument {instrument_id} not found"}

        bb_inst.volume = volume

        write_project(project, Path(path))

        return {
            "status": "updated",
            "instrument": bb_inst.describe(),
        }
