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

    @mcp.tool()
    def quantize_pattern(
        path: str,
        track_id: int,
        pattern_id: int,
        grid: float = 0.5,
        swing: float = 0.0,
        remove_duplicates: bool = True,
        trim_to_length: bool = True,
    ) -> dict[str, Any]:
        """Quantize notes in a pattern to a grid.

        Args:
            path: Path to .mmp or .mmpz file
            track_id: ID of track containing the pattern
            pattern_id: ID of pattern to quantize
            grid: Grid size in beats (0.25=16th, 0.5=8th, 1.0=quarter, default 0.5)
            swing: Swing/groove offset in beats (e.g., 0.03 for slight behind-beat feel)
            remove_duplicates: Remove notes that land on same grid position (default True)
            trim_to_length: Remove notes beyond pattern length (default True)

        Returns:
            Quantization results with before/after note counts
        """
        project = parse_project(Path(path))
        track = project.get_track(track_id)
        if not track:
            return {"status": "error", "message": f"Track {track_id} not found"}

        pattern = track.get_pattern(pattern_id)
        if not pattern:
            return {"status": "error", "message": f"Pattern {pattern_id} not found"}

        original_count = len(pattern.notes)
        max_beat = pattern.length * 4  # bars to beats

        # Collect note data
        notes_data = []
        for note in pattern.notes:
            # Quantize to grid
            quantized_start = round(note.start / grid) * grid

            # Skip if beyond pattern length
            if trim_to_length and quantized_start >= max_beat:
                continue

            notes_data.append({
                "pitch": note.pitch,
                "start": quantized_start,
                "length": note.length,
                "velocity": note.velocity,
                "pan": note.pan,
            })

        # Remove duplicates (same pitch on same grid position)
        if remove_duplicates:
            seen = set()
            unique_notes = []
            for nd in sorted(notes_data, key=lambda x: x["start"]):
                key = (nd["pitch"], nd["start"])
                if key not in seen:
                    seen.add(key)
                    unique_notes.append(nd)
            notes_data = unique_notes

        # Clear and rebuild with quantized notes + swing
        pattern.clear()
        for nd in notes_data:
            note = Note(
                pitch=nd["pitch"],
                start=nd["start"] + swing,
                length=nd["length"],
                velocity=nd["velocity"],
                pan=nd["pan"],
            )
            pattern.add_note(note)

        write_project(project, Path(path))
        return {
            "status": "quantized",
            "grid": grid,
            "swing": swing,
            "notes_before": original_count,
            "notes_after": len(pattern.notes),
            "removed": original_count - len(pattern.notes),
            "pattern": pattern.describe(),
        }

    @mcp.tool()
    def extend_pattern(
        path: str,
        track_id: int,
        pattern_id: int,
        new_length: int,
    ) -> dict[str, Any]:
        """Extend or shrink a pattern to a new length.

        Args:
            path: Path to .mmp or .mmpz file
            track_id: ID of track containing the pattern
            pattern_id: ID of pattern to extend
            new_length: New length in bars

        Returns:
            Updated pattern info
        """
        project = parse_project(Path(path))

        if track_id >= len(project.tracks):
            return {"status": "error", "error": f"Track {track_id} not found"}

        track = project.tracks[track_id]

        if pattern_id >= len(track.patterns):
            return {"status": "error", "error": f"Pattern {pattern_id} not found"}

        pattern = track.patterns[pattern_id]
        old_length = pattern.length
        pattern.length = new_length

        write_project(project, Path(path))

        return {
            "status": "extended",
            "track_id": track_id,
            "pattern_id": pattern_id,
            "old_length": old_length,
            "new_length": new_length,
            "note_count": len(pattern.notes),
        }

    @mcp.tool()
    def copy_notes(
        path: str,
        track_id: int,
        pattern_id: int,
        time_offset: float,
        filter_callback: str | None = None,
    ) -> dict[str, Any]:
        """Copy all notes in a pattern with a time offset.

        Useful for duplicating sections. Copies all existing notes and adds
        them again at start + time_offset.

        Args:
            path: Path to .mmp or .mmpz file
            track_id: ID of track containing the pattern
            pattern_id: ID of pattern
            time_offset: Time offset in beats to shift copied notes
            filter_callback: Optional filter (not implemented yet)

        Returns:
            Copy results
        """
        project = parse_project(Path(path))

        if track_id >= len(project.tracks):
            return {"status": "error", "error": f"Track {track_id} not found"}

        track = project.tracks[track_id]

        if pattern_id >= len(track.patterns):
            return {"status": "error", "error": f"Pattern {pattern_id} not found"}

        pattern = track.patterns[pattern_id]
        original_count = len(pattern.notes)
        original_notes = list(pattern.notes)  # Copy to avoid modifying while iterating

        # Copy each note with offset
        copied_count = 0
        for note in original_notes:
            new_note = Note(
                pitch=note.pitch,
                start=note.start + time_offset,
                length=note.length,
                velocity=note.velocity,
                pan=note.pan,
            )
            pattern.add_note(new_note)
            copied_count += 1

        write_project(project, Path(path))

        return {
            "status": "copied",
            "track_id": track_id,
            "pattern_id": pattern_id,
            "time_offset": time_offset,
            "notes_original": original_count,
            "notes_copied": copied_count,
            "notes_total": len(pattern.notes),
        }
