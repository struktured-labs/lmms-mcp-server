"""Note model for LMMS patterns."""

from pydantic import BaseModel, Field
from typing import Any


# MIDI note name mapping
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def parse_pitch(pitch: int | str) -> int:
    """Convert pitch to MIDI note number.

    Args:
        pitch: MIDI number (0-127) or note name like "C4", "D#5"

    Returns:
        MIDI note number
    """
    if isinstance(pitch, int):
        return pitch

    # Parse note name like "C4", "D#5", "Bb3"
    pitch = pitch.strip().upper()

    # Handle flats by converting to sharps
    pitch = pitch.replace("BB", "A#").replace("DB", "C#").replace("EB", "D#")
    pitch = pitch.replace("FB", "E").replace("GB", "F#").replace("AB", "G#")

    # Extract note and octave
    if len(pitch) >= 2:
        if pitch[1] == "#":
            note = pitch[:2]
            octave = int(pitch[2:]) if len(pitch) > 2 else 4
        else:
            note = pitch[0]
            octave = int(pitch[1:]) if len(pitch) > 1 else 4
    else:
        note = pitch
        octave = 4

    # Calculate MIDI number (C4 = 60)
    try:
        note_index = NOTE_NAMES.index(note)
    except ValueError:
        raise ValueError(f"Invalid note name: {note}")

    return (octave + 1) * 12 + note_index


class Note(BaseModel):
    """A single note in a pattern."""

    pitch: int = Field(ge=0, le=127, description="MIDI note number")
    start: float = Field(ge=0, description="Start time in beats")
    length: float = Field(gt=0, description="Duration in beats")
    velocity: int = Field(default=100, ge=0, le=127, description="Note velocity")
    pan: float = Field(default=0.0, ge=-1.0, le=1.0, description="Pan position")

    @staticmethod
    def pitch_to_name(pitch: int) -> str:
        """Convert MIDI pitch to note name."""
        octave = (pitch // 12) - 1
        note = NOTE_NAMES[pitch % 12]
        return f"{note}{octave}"

    @property
    def name(self) -> str:
        """Get note name like 'C4'."""
        return self.pitch_to_name(self.pitch)

    def describe(self) -> dict[str, Any]:
        """Return a description dict."""
        return {
            "pitch": self.pitch,
            "name": self.name,
            "start": self.start,
            "length": self.length,
            "velocity": self.velocity,
        }

    def to_description(self) -> str:
        """Human-readable description."""
        return f"{self.name} at beat {self.start} for {self.length} beats (vel: {self.velocity})"
