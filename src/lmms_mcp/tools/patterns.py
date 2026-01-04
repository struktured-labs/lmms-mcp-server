"""Pattern and note editing tools for LMMS."""

from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from lmms_mcp.xml.parser import parse_project
from lmms_mcp.xml.writer import write_project
from lmms_mcp.models.pattern import Pattern
from lmms_mcp.models.note import Note, parse_pitch


def register(mcp: FastMCP) -> None:
    """Register pattern tools with the MCP server."""

    @mcp.tool()
    def create_pattern(
        path: str,
        track_id: int,
        name: str,
        position: int = 0,
        length: int = 4,
    ) -> dict[str, Any]:
        """Create an empty pattern on a track.

        Args:
            path: Path to .mmp or .mmpz file
            track_id: ID of track to add pattern to
            name: Pattern name
            position: Start position in bars (default 0)
            length: Pattern length in bars (default 4)

        Returns:
            New pattern info
        """
        project = parse_project(Path(path))
        track = project.get_track(track_id)
        if not track:
            return {"status": "error", "message": f"Track {track_id} not found"}

        pattern = Pattern(name=name, position=position, length=length)
        track.add_pattern(pattern)
        write_project(project, Path(path))
        return {
            "status": "created",
            "pattern": pattern.describe(),
            "track_id": track_id,
        }

    @mcp.tool()
    def add_notes(
        path: str,
        track_id: int,
        pattern_id: int,
        notes: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Add notes to a pattern.

        Args:
            path: Path to .mmp or .mmpz file
            track_id: ID of track containing the pattern
            pattern_id: ID of pattern to add notes to
            notes: List of note dicts with keys:
                - pitch: MIDI note number (0-127) or note name (e.g., "C4", "D#5")
                - start: Start time in beats
                - length: Duration in beats
                - velocity: Velocity 0-127 (default 100)

        Returns:
            Updated pattern info with note count
        """
        project = parse_project(Path(path))
        track = project.get_track(track_id)
        if not track:
            return {"status": "error", "message": f"Track {track_id} not found"}

        pattern = track.get_pattern(pattern_id)
        if not pattern:
            return {"status": "error", "message": f"Pattern {pattern_id} not found"}

        for note_data in notes:
            pitch = parse_pitch(note_data["pitch"])
            note = Note(
                pitch=pitch,
                start=note_data["start"],
                length=note_data["length"],
                velocity=note_data.get("velocity", 100),
            )
            pattern.add_note(note)

        write_project(project, Path(path))
        return {
            "status": "added",
            "notes_added": len(notes),
            "pattern": pattern.describe(),
        }

    @mcp.tool()
    def add_chord(
        path: str,
        track_id: int,
        pattern_id: int,
        root: str,
        chord_type: str,
        start: float,
        length: float,
        velocity: int = 100,
    ) -> dict[str, Any]:
        """Add a chord to a pattern.

        Args:
            path: Path to .mmp or .mmpz file
            track_id: ID of track containing the pattern
            pattern_id: ID of pattern to add chord to
            root: Root note (e.g., "C4", "F#3")
            chord_type: Chord type: maj, min, dim, aug, maj7, min7, dom7, etc.
            start: Start time in beats
            length: Duration in beats
            velocity: Note velocity 0-127 (default 100)

        Returns:
            Chord info with notes added
        """
        from lmms_mcp.theory import build_chord

        project = parse_project(Path(path))
        track = project.get_track(track_id)
        if not track:
            return {"status": "error", "message": f"Track {track_id} not found"}

        pattern = track.get_pattern(pattern_id)
        if not pattern:
            return {"status": "error", "message": f"Pattern {pattern_id} not found"}

        chord_notes = build_chord(root, chord_type)
        for pitch in chord_notes:
            note = Note(pitch=pitch, start=start, length=length, velocity=velocity)
            pattern.add_note(note)

        write_project(project, Path(path))
        return {
            "status": "added",
            "chord": f"{root} {chord_type}",
            "notes": [Note.pitch_to_name(p) for p in chord_notes],
            "pattern": pattern.describe(),
        }

    @mcp.tool()
    def describe_pattern(path: str, track_id: int, pattern_id: int) -> dict[str, Any]:
        """Get a detailed description of a pattern's contents.

        Args:
            path: Path to .mmp or .mmpz file
            track_id: ID of track containing the pattern
            pattern_id: ID of pattern to describe

        Returns:
            Pattern description with notes listed
        """
        project = parse_project(Path(path))
        track = project.get_track(track_id)
        if not track:
            return {"status": "error", "message": f"Track {track_id} not found"}

        pattern = track.get_pattern(pattern_id)
        if not pattern:
            return {"status": "error", "message": f"Pattern {pattern_id} not found"}

        return {
            "pattern": pattern.describe(),
            "notes": [note.describe() for note in pattern.notes],
            "description": pattern.to_description(),
        }

    @mcp.tool()
    def clear_pattern(path: str, track_id: int, pattern_id: int) -> dict[str, Any]:
        """Remove all notes from a pattern.

        Args:
            path: Path to .mmp or .mmpz file
            track_id: ID of track containing the pattern
            pattern_id: ID of pattern to clear

        Returns:
            Status message
        """
        project = parse_project(Path(path))
        track = project.get_track(track_id)
        if not track:
            return {"status": "error", "message": f"Track {track_id} not found"}

        pattern = track.get_pattern(pattern_id)
        if not pattern:
            return {"status": "error", "message": f"Pattern {pattern_id} not found"}

        pattern.clear()
        write_project(project, Path(path))
        return {
            "status": "cleared",
            "pattern_id": pattern_id,
        }
