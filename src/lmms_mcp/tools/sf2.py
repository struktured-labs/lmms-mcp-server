"""SoundFont (SF2) instrument MCP tools."""

from pathlib import Path
from typing import Any

from lmms_mcp.xml.parser import parse_project
from lmms_mcp.xml.writer import write_project
from lmms_mcp.models.track import SF2InstrumentTrack
from lmms_mcp.models.pattern import Pattern
from lmms_mcp.models.note import Note, parse_pitch


def register(mcp):
    """Register SF2 tools with the MCP server."""

    @mcp.tool()
    def add_sf2_track(
        path: str,
        name: str,
        sf2_path: str,
        bank: int = 0,
        patch: int = 0,
        gain: float = 1.0,
        reverb_on: bool = False,
        chorus_on: bool = False,
    ) -> dict[str, Any]:
        """Add a SoundFont (SF2/SF3) instrument track to the project.

        SoundFonts provide realistic instrument sounds (piano, strings, brass, etc.)
        using sampled audio. LMMS uses FluidSynth to play SF2/SF3 files.

        Args:
            path: Path to .mmp or .mmpz file
            name: Track name (e.g., "Piano", "Strings")
            sf2_path: Path to .sf2 or .sf3 soundfont file
            bank: Bank number 0-999 (default 0)
            patch: Patch/program number 0-127 (default 0, usually piano)
            gain: Gain level 0.0-5.0 (default 1.0)
            reverb_on: Enable built-in reverb (default False)
            chorus_on: Enable built-in chorus (default False)

        Returns:
            New track info including ID and settings
        """
        project = parse_project(Path(path))

        sf2_track = SF2InstrumentTrack(
            name=name,
            sf2_path=sf2_path,
            bank=bank,
            patch=patch,
            gain=gain,
            reverb_on=reverb_on,
            chorus_on=chorus_on,
        )
        project.add_track(sf2_track)

        write_project(project, Path(path))

        return {
            "status": "added",
            "track": sf2_track.describe(),
            "track_count": len(project.tracks),
        }

    @mcp.tool()
    def set_sf2_patch(
        path: str,
        track_id: int,
        bank: int,
        patch: int,
    ) -> dict[str, Any]:
        """Change the bank and patch (instrument) of an SF2 track.

        Common General MIDI patches (bank 0):
        - 0: Acoustic Grand Piano
        - 24: Acoustic Guitar (nylon)
        - 32: Acoustic Bass
        - 40: Violin
        - 48: String Ensemble 1
        - 56: Trumpet
        - 73: Flute

        Args:
            path: Path to .mmp or .mmpz file
            track_id: ID of SF2 track to modify
            bank: Bank number 0-999
            patch: Patch/program number 0-127

        Returns:
            Updated track info
        """
        project = parse_project(Path(path))

        if track_id >= len(project.tracks):
            return {"status": "error", "error": f"Track {track_id} not found"}

        track = project.tracks[track_id]
        if not isinstance(track, SF2InstrumentTrack):
            return {"status": "error", "error": f"Track {track_id} is not an SF2 track"}

        track.bank = bank
        track.patch = patch

        write_project(project, Path(path))

        return {
            "status": "updated",
            "track": track.describe(),
        }

    @mcp.tool()
    def set_sf2_effects(
        path: str,
        track_id: int,
        reverb_on: bool | None = None,
        reverb_room_size: float | None = None,
        reverb_damping: float | None = None,
        reverb_width: float | None = None,
        reverb_level: float | None = None,
        chorus_on: bool | None = None,
        chorus_num: int | None = None,
        chorus_level: float | None = None,
        chorus_speed: float | None = None,
        chorus_depth: float | None = None,
    ) -> dict[str, Any]:
        """Configure reverb and chorus effects for an SF2 track.

        Only provided parameters are changed; others remain unchanged.

        Args:
            path: Path to .mmp or .mmpz file
            track_id: ID of SF2 track to modify
            reverb_on: Enable/disable reverb
            reverb_room_size: Room size 0.0-1.0
            reverb_damping: Damping 0.0-1.0
            reverb_width: Width 0.0-1.0
            reverb_level: Level 0.0-1.0
            chorus_on: Enable/disable chorus
            chorus_num: Chorus voices 0-10
            chorus_level: Chorus level 0.0-10.0
            chorus_speed: Chorus speed 0.29-5.0
            chorus_depth: Chorus depth 0.0-46.0

        Returns:
            Updated track info with current effect settings
        """
        project = parse_project(Path(path))

        if track_id >= len(project.tracks):
            return {"status": "error", "error": f"Track {track_id} not found"}

        track = project.tracks[track_id]
        if not isinstance(track, SF2InstrumentTrack):
            return {"status": "error", "error": f"Track {track_id} is not an SF2 track"}

        # Update only provided values
        if reverb_on is not None:
            track.reverb_on = reverb_on
        if reverb_room_size is not None:
            track.reverb_room_size = reverb_room_size
        if reverb_damping is not None:
            track.reverb_damping = reverb_damping
        if reverb_width is not None:
            track.reverb_width = reverb_width
        if reverb_level is not None:
            track.reverb_level = reverb_level
        if chorus_on is not None:
            track.chorus_on = chorus_on
        if chorus_num is not None:
            track.chorus_num = chorus_num
        if chorus_level is not None:
            track.chorus_level = chorus_level
        if chorus_speed is not None:
            track.chorus_speed = chorus_speed
        if chorus_depth is not None:
            track.chorus_depth = chorus_depth

        write_project(project, Path(path))

        return {
            "status": "updated",
            "track": track.describe(),
            "effects": {
                "reverb": {
                    "on": track.reverb_on,
                    "room_size": track.reverb_room_size,
                    "damping": track.reverb_damping,
                    "width": track.reverb_width,
                    "level": track.reverb_level,
                },
                "chorus": {
                    "on": track.chorus_on,
                    "voices": track.chorus_num,
                    "level": track.chorus_level,
                    "speed": track.chorus_speed,
                    "depth": track.chorus_depth,
                },
            },
        }

    @mcp.tool()
    def add_sf2_notes(
        path: str,
        track_id: int,
        pattern_id: int,
        notes: list[dict],
    ) -> dict[str, Any]:
        """Add notes to a pattern on an SF2 track.

        Args:
            path: Path to .mmp or .mmpz file
            track_id: ID of SF2 track
            pattern_id: ID of pattern to add notes to
            notes: List of notes, each with:
                - pitch: MIDI note number (0-127) or note name (e.g., "C4", "D#5")
                - start: Start time in beats
                - length: Duration in beats
                - velocity: Velocity 0-127 (default 100)

        Returns:
            Updated pattern info with note count
        """
        project = parse_project(Path(path))

        if track_id >= len(project.tracks):
            return {"status": "error", "error": f"Track {track_id} not found"}

        track = project.tracks[track_id]
        if not isinstance(track, SF2InstrumentTrack):
            return {"status": "error", "error": f"Track {track_id} is not an SF2 track"}

        pattern = track.get_pattern(pattern_id)
        if pattern is None:
            return {"status": "error", "error": f"Pattern {pattern_id} not found"}

        for n in notes:
            pitch = parse_pitch(n.get("pitch", 60))
            note = Note(
                pitch=pitch,
                start=float(n.get("start", 0)),
                length=float(n.get("length", 1)),
                velocity=int(n.get("velocity", 100)),
            )
            pattern.notes.append(note)

        write_project(project, Path(path))

        return {
            "status": "added",
            "pattern": pattern.describe(),
            "note_count": len(pattern.notes),
        }

    @mcp.tool()
    def describe_sf2_track(
        path: str,
        track_id: int,
    ) -> dict[str, Any]:
        """Get detailed description of an SF2 track.

        Args:
            path: Path to .mmp or .mmpz file
            track_id: ID of SF2 track

        Returns:
            Track description with SF2 settings, effects, and patterns
        """
        project = parse_project(Path(path))

        if track_id >= len(project.tracks):
            return {"status": "error", "error": f"Track {track_id} not found"}

        track = project.tracks[track_id]
        if not isinstance(track, SF2InstrumentTrack):
            return {"status": "error", "error": f"Track {track_id} is not an SF2 track"}

        return {
            "name": track.name,
            "sf2_path": track.sf2_path,
            "bank": track.bank,
            "patch": track.patch,
            "gain": track.gain,
            "volume": track.volume,
            "pan": track.pan,
            "reverb": {
                "on": track.reverb_on,
                "room_size": track.reverb_room_size,
                "damping": track.reverb_damping,
                "width": track.reverb_width,
                "level": track.reverb_level,
            },
            "chorus": {
                "on": track.chorus_on,
                "voices": track.chorus_num,
                "level": track.chorus_level,
                "speed": track.chorus_speed,
                "depth": track.chorus_depth,
            },
            "pattern_count": len(track.patterns),
            "patterns": [p.describe() for p in track.patterns],
            "visual": track.to_description(),
        }

    @mcp.tool()
    def list_gm_patches() -> dict[str, Any]:
        """List common General MIDI patch numbers.

        General MIDI (GM) defines standard instrument assignments for patches 0-127.
        Most SF2 soundfonts follow this standard in bank 0.

        Returns:
            Dictionary of patch categories with patch numbers and names
        """
        return {
            "piano": {
                0: "Acoustic Grand Piano",
                1: "Bright Acoustic Piano",
                2: "Electric Grand Piano",
                3: "Honky-tonk Piano",
                4: "Electric Piano 1",
                5: "Electric Piano 2",
                6: "Harpsichord",
                7: "Clavinet",
            },
            "chromatic_percussion": {
                8: "Celesta",
                9: "Glockenspiel",
                10: "Music Box",
                11: "Vibraphone",
                12: "Marimba",
                13: "Xylophone",
            },
            "organ": {
                16: "Drawbar Organ",
                17: "Percussive Organ",
                18: "Rock Organ",
                19: "Church Organ",
            },
            "guitar": {
                24: "Acoustic Guitar (nylon)",
                25: "Acoustic Guitar (steel)",
                26: "Electric Guitar (jazz)",
                27: "Electric Guitar (clean)",
                28: "Electric Guitar (muted)",
                29: "Overdriven Guitar",
                30: "Distortion Guitar",
            },
            "bass": {
                32: "Acoustic Bass",
                33: "Electric Bass (finger)",
                34: "Electric Bass (pick)",
                35: "Fretless Bass",
                36: "Slap Bass 1",
                37: "Slap Bass 2",
                38: "Synth Bass 1",
                39: "Synth Bass 2",
            },
            "strings": {
                40: "Violin",
                41: "Viola",
                42: "Cello",
                43: "Contrabass",
                44: "Tremolo Strings",
                45: "Pizzicato Strings",
                46: "Orchestral Harp",
                47: "Timpani",
            },
            "ensemble": {
                48: "String Ensemble 1",
                49: "String Ensemble 2",
                50: "Synth Strings 1",
                51: "Synth Strings 2",
                52: "Choir Aahs",
                53: "Voice Oohs",
            },
            "brass": {
                56: "Trumpet",
                57: "Trombone",
                58: "Tuba",
                59: "Muted Trumpet",
                60: "French Horn",
                61: "Brass Section",
            },
            "reed": {
                64: "Soprano Sax",
                65: "Alto Sax",
                66: "Tenor Sax",
                67: "Baritone Sax",
                68: "Oboe",
                69: "English Horn",
                70: "Bassoon",
                71: "Clarinet",
            },
            "pipe": {
                72: "Piccolo",
                73: "Flute",
                74: "Recorder",
                75: "Pan Flute",
            },
            "synth_lead": {
                80: "Lead 1 (square)",
                81: "Lead 2 (sawtooth)",
                82: "Lead 3 (calliope)",
                83: "Lead 4 (chiff)",
                84: "Lead 5 (charang)",
            },
            "synth_pad": {
                88: "Pad 1 (new age)",
                89: "Pad 2 (warm)",
                90: "Pad 3 (polysynth)",
                91: "Pad 4 (choir)",
                92: "Pad 5 (bowed)",
            },
        }
