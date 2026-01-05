#!/usr/bin/env python3
"""Create a demo LMMS project with a simple melody and chord progression."""

from pathlib import Path

from lmms_mcp.models.project import Project
from lmms_mcp.models.track import InstrumentTrack
from lmms_mcp.models.pattern import Pattern
from lmms_mcp.models.note import Note
from lmms_mcp.theory import build_chord, get_chord_progression
from lmms_mcp.xml.writer import write_project


def create_demo_project(output_path: Path) -> None:
    """Create a demo project with melody and chords."""
    # Create project at 120 BPM
    project = Project(name="Demo Song", bpm=120)

    # Create lead track
    lead = InstrumentTrack(name="Lead Synth", instrument="tripleoscillator")
    lead.volume = 0.8

    # Create melody pattern (4 bars)
    melody = Pattern(name="Melody", position=0, length=4)

    # Simple ascending melody
    melody_notes = [
        # Bar 1
        (60, 0.0, 1.0),  # C4
        (62, 1.0, 1.0),  # D4
        (64, 2.0, 1.0),  # E4
        (65, 3.0, 1.0),  # F4
        # Bar 2
        (67, 4.0, 2.0),  # G4 (held)
        (65, 6.0, 1.0),  # F4
        (64, 7.0, 1.0),  # E4
        # Bar 3
        (62, 8.0, 2.0),  # D4 (held)
        (64, 10.0, 1.0),  # E4
        (60, 11.0, 1.0),  # C4
        # Bar 4
        (60, 12.0, 4.0),  # C4 (whole note)
    ]

    for pitch, start, length in melody_notes:
        melody.add_note(Note(pitch=pitch, start=start, length=length, velocity=100))

    lead.add_pattern(melody)
    project.add_track(lead)

    # Create pad track for chords
    pad = InstrumentTrack(name="Pad", instrument="tripleoscillator")
    pad.volume = 0.5

    # Create chord pattern
    chords = Pattern(name="Chords", position=0, length=4)

    # I-V-vi-IV progression in C major (each chord is 1 bar = 4 beats)
    progression = get_chord_progression("C3", "major", [1, 5, 6, 4])

    for bar, chord_notes in enumerate(progression):
        start_beat = bar * 4
        for pitch in chord_notes:
            chords.add_note(Note(pitch=pitch, start=start_beat, length=4.0, velocity=70))

    pad.add_pattern(chords)
    project.add_track(pad)

    # Create bass track
    bass = InstrumentTrack(name="Bass", instrument="tripleoscillator")
    bass.volume = 0.9

    # Bass pattern following chord roots
    bass_pattern = Pattern(name="Bass", position=0, length=4)
    bass_roots = [48, 55, 57, 53]  # C3, G3, A3, F3 (chord roots, octave down)

    for bar, root in enumerate(bass_roots):
        start_beat = bar * 4
        # Root on beat 1 and 3
        bass_pattern.add_note(Note(pitch=root, start=start_beat, length=1.5, velocity=100))
        bass_pattern.add_note(Note(pitch=root, start=start_beat + 2, length=1.5, velocity=90))

    bass.add_pattern(bass_pattern)
    project.add_track(bass)

    # Write project
    write_project(project, output_path)
    print(f"Created demo project: {output_path}")

    # Print description
    print("\n" + project.to_description())


if __name__ == "__main__":
    import sys

    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("demo.mmp")
    create_demo_project(output)
