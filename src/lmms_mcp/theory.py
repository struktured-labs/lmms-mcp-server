"""Music theory helpers for chord and scale generation."""

from lmms_mcp.models.note import parse_pitch, NOTE_NAMES


# Chord intervals (semitones from root)
CHORD_INTERVALS: dict[str, list[int]] = {
    "maj": [0, 4, 7],
    "min": [0, 3, 7],
    "dim": [0, 3, 6],
    "aug": [0, 4, 8],
    "sus2": [0, 2, 7],
    "sus4": [0, 5, 7],
    "maj7": [0, 4, 7, 11],
    "min7": [0, 3, 7, 10],
    "dom7": [0, 4, 7, 10],
    "7": [0, 4, 7, 10],  # Alias for dom7
    "dim7": [0, 3, 6, 9],
    "m7b5": [0, 3, 6, 10],  # Half-diminished
    "maj9": [0, 4, 7, 11, 14],
    "min9": [0, 3, 7, 10, 14],
    "dom9": [0, 4, 7, 10, 14],
    "add9": [0, 4, 7, 14],
    "6": [0, 4, 7, 9],
    "min6": [0, 3, 7, 9],
}

# Scale intervals (semitones from root)
SCALE_INTERVALS: dict[str, list[int]] = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
    "melodic_minor": [0, 2, 3, 5, 7, 9, 11],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "lydian": [0, 2, 4, 6, 7, 9, 11],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "locrian": [0, 1, 3, 5, 6, 8, 10],
    "minor_pentatonic": [0, 3, 5, 7, 10],
    "major_pentatonic": [0, 2, 4, 7, 9],
    "blues": [0, 3, 5, 6, 7, 10],
    "chromatic": list(range(12)),
    "whole_tone": [0, 2, 4, 6, 8, 10],
}


def build_chord(root: str | int, chord_type: str) -> list[int]:
    """Build a chord from root note and chord type.

    Args:
        root: Root note (MIDI number or note name like "C4")
        chord_type: Chord type (maj, min, dim, aug, maj7, etc.)

    Returns:
        List of MIDI note numbers for the chord
    """
    root_pitch = parse_pitch(root) if isinstance(root, str) else root
    chord_type = chord_type.lower().replace("-", "").replace("_", "")

    if chord_type not in CHORD_INTERVALS:
        raise ValueError(f"Unknown chord type: {chord_type}")

    intervals = CHORD_INTERVALS[chord_type]
    return [root_pitch + interval for interval in intervals]


def build_scale(root: str | int, scale_type: str, octaves: int = 1) -> list[int]:
    """Build a scale from root note and scale type.

    Args:
        root: Root note (MIDI number or note name like "C4")
        scale_type: Scale type (major, minor, pentatonic, etc.)
        octaves: Number of octaves to span

    Returns:
        List of MIDI note numbers for the scale
    """
    root_pitch = parse_pitch(root) if isinstance(root, str) else root
    scale_type = scale_type.lower().replace("-", "_")

    if scale_type not in SCALE_INTERVALS:
        raise ValueError(f"Unknown scale type: {scale_type}")

    intervals = SCALE_INTERVALS[scale_type]
    notes = []

    for octave in range(octaves):
        for interval in intervals:
            notes.append(root_pitch + interval + (octave * 12))

    return notes


def get_scale_degree(root: str | int, scale_type: str, degree: int) -> int:
    """Get a specific scale degree.

    Args:
        root: Root note
        scale_type: Scale type
        degree: Scale degree (1-indexed, 1 = root)

    Returns:
        MIDI note number for that scale degree
    """
    scale = build_scale(root, scale_type, octaves=2)
    # Adjust for 1-indexed degrees
    index = degree - 1
    if index < 0 or index >= len(scale):
        raise ValueError(f"Degree {degree} out of range for {scale_type} scale")
    return scale[index]


def get_chord_in_key(
    root: str | int,
    scale_type: str,
    degree: int,
    chord_type: str | None = None,
) -> list[int]:
    """Get a diatonic chord on a scale degree.

    Args:
        root: Root note of the scale
        scale_type: Scale type (major, minor, etc.)
        degree: Scale degree (1-7)
        chord_type: Override chord type (auto-detected if None)

    Returns:
        List of MIDI note numbers for the chord
    """
    scale = build_scale(root, scale_type)

    # Get chord root from scale degree
    chord_root = scale[degree - 1]

    # Auto-detect chord type from scale
    if chord_type is None:
        if scale_type == "major":
            # I=maj, ii=min, iii=min, IV=maj, V=maj, vi=min, vii=dim
            major_chords = {1: "maj", 2: "min", 3: "min", 4: "maj", 5: "maj", 6: "min", 7: "dim"}
            chord_type = major_chords.get(degree, "maj")
        elif scale_type == "minor":
            # i=min, ii=dim, III=maj, iv=min, v=min, VI=maj, VII=maj
            minor_chords = {1: "min", 2: "dim", 3: "maj", 4: "min", 5: "min", 6: "maj", 7: "maj"}
            chord_type = minor_chords.get(degree, "min")
        else:
            chord_type = "maj"  # Default

    return build_chord(chord_root, chord_type)


def get_chord_progression(
    root: str | int,
    scale_type: str,
    degrees: list[int],
) -> list[list[int]]:
    """Build a chord progression from scale degrees.

    Args:
        root: Root note of the scale
        scale_type: Scale type
        degrees: List of scale degrees (e.g., [1, 5, 6, 4] for I-V-vi-IV)

    Returns:
        List of chords (each chord is a list of MIDI note numbers)
    """
    return [get_chord_in_key(root, scale_type, d) for d in degrees]
