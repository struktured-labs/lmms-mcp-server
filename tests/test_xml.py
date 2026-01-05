"""Tests for XML parsing and writing."""

import tempfile
from pathlib import Path

import pytest

from lmms_mcp.models.project import Project
from lmms_mcp.models.track import InstrumentTrack
from lmms_mcp.models.pattern import Pattern
from lmms_mcp.models.note import Note
from lmms_mcp.xml.parser import parse_project, TICKS_PER_BAR, TICKS_PER_BEAT
from lmms_mcp.xml.writer import write_project


class TestXmlRoundTrip:
    """Test XML parsing and writing round-trip."""

    def test_empty_project_roundtrip(self, tmp_path):
        """Test creating and parsing an empty project."""
        # Create project
        project = Project(name="Test", bpm=140)

        # Write to file
        filepath = tmp_path / "test.mmp"
        write_project(project, filepath)

        # Parse back
        parsed = parse_project(filepath)

        assert parsed.name == "test"  # Name comes from filename
        assert parsed.bpm == 140
        assert parsed.time_sig_num == 4
        assert parsed.time_sig_den == 4
        assert len(parsed.tracks) == 0

    def test_project_with_track_roundtrip(self, tmp_path):
        """Test project with an instrument track."""
        project = Project(name="Test", bpm=120)
        track = InstrumentTrack(name="Lead", instrument="tripleoscillator")
        project.add_track(track)

        filepath = tmp_path / "test.mmp"
        write_project(project, filepath)
        parsed = parse_project(filepath)

        assert len(parsed.tracks) == 1
        assert parsed.tracks[0].name == "Lead"
        assert parsed.tracks[0].instrument == "tripleoscillator"

    def test_project_with_pattern_roundtrip(self, tmp_path):
        """Test project with patterns and notes."""
        project = Project(name="Test", bpm=120)
        track = InstrumentTrack(name="Lead")
        pattern = Pattern(name="Intro", position=0, length=4)
        pattern.add_note(Note(pitch=60, start=0.0, length=1.0, velocity=100))
        pattern.add_note(Note(pitch=64, start=1.0, length=1.0, velocity=80))
        pattern.add_note(Note(pitch=67, start=2.0, length=2.0, velocity=100))
        track.add_pattern(pattern)
        project.add_track(track)

        filepath = tmp_path / "test.mmp"
        write_project(project, filepath)
        parsed = parse_project(filepath)

        assert len(parsed.tracks) == 1
        assert len(parsed.tracks[0].patterns) == 1
        parsed_pattern = parsed.tracks[0].patterns[0]
        assert parsed_pattern.name == "Intro"
        assert parsed_pattern.position == 0
        assert parsed_pattern.length == 4
        assert len(parsed_pattern.notes) == 3

        # Check notes
        notes = sorted(parsed_pattern.notes, key=lambda n: n.start)
        assert notes[0].pitch == 60
        assert notes[0].start == 0.0
        assert notes[0].length == 1.0

        assert notes[1].pitch == 64
        assert notes[1].start == 1.0

        assert notes[2].pitch == 67
        assert notes[2].start == 2.0
        assert notes[2].length == 2.0

    def test_mmpz_compression(self, tmp_path):
        """Test compressed .mmpz format."""
        project = Project(name="Test", bpm=128)
        track = InstrumentTrack(name="Synth")
        project.add_track(track)

        filepath = tmp_path / "test.mmpz"
        write_project(project, filepath)

        # Verify file is compressed (starts with size header)
        data = filepath.read_bytes()
        assert len(data) > 4  # Has size header

        parsed = parse_project(filepath)
        assert parsed.bpm == 128
        assert len(parsed.tracks) == 1

    def test_multiple_tracks(self, tmp_path):
        """Test project with multiple tracks."""
        project = Project(name="Song", bpm=90)

        for i, name in enumerate(["Bass", "Lead", "Pad"]):
            track = InstrumentTrack(name=name, instrument="tripleoscillator")
            track.volume = 0.8 - (i * 0.1)
            project.add_track(track)

        filepath = tmp_path / "test.mmp"
        write_project(project, filepath)
        parsed = parse_project(filepath)

        assert len(parsed.tracks) == 3
        assert parsed.tracks[0].name == "Bass"
        assert parsed.tracks[1].name == "Lead"
        assert parsed.tracks[2].name == "Pad"


class TestTickConversions:
    """Test tick/beat/bar conversions."""

    def test_tick_constants(self):
        """Verify tick constants are correct."""
        assert TICKS_PER_BAR == 192
        assert TICKS_PER_BEAT == 48
        assert TICKS_PER_BAR == TICKS_PER_BEAT * 4  # 4 beats per bar

    def test_note_timing_precision(self, tmp_path):
        """Test that note timing survives round-trip."""
        project = Project(name="Test", bpm=120)
        track = InstrumentTrack(name="Lead")
        pattern = Pattern(name="Test", position=0, length=2)

        # Add notes at various positions
        test_positions = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]
        for i, pos in enumerate(test_positions):
            pattern.add_note(Note(pitch=60 + i, start=pos, length=0.5))

        track.add_pattern(pattern)
        project.add_track(track)

        filepath = tmp_path / "test.mmp"
        write_project(project, filepath)
        parsed = parse_project(filepath)

        parsed_notes = sorted(parsed.tracks[0].patterns[0].notes, key=lambda n: n.start)
        for i, note in enumerate(parsed_notes):
            assert note.start == test_positions[i], f"Note {i} position mismatch"
            assert note.length == 0.5


class TestXmlGeneration:
    """Test XML output structure."""

    def test_xml_has_required_elements(self, tmp_path):
        """Verify generated XML has all required elements."""
        project = Project(name="Test", bpm=120)
        track = InstrumentTrack(name="Lead", instrument="tripleoscillator")
        project.add_track(track)

        filepath = tmp_path / "test.mmp"
        write_project(project, filepath)

        # Read and check XML structure
        content = filepath.read_text()
        assert '<?xml version' in content
        assert '<lmms-project' in content
        assert '<head' in content
        assert 'bpm="120"' in content
        assert '<song>' in content
        assert '<trackcontainer' in content
        assert '<track' in content
        assert '<instrumenttrack' in content
        assert '<instrument' in content
        assert '<tripleoscillator' in content

    def test_tripleoscillator_has_all_params(self, tmp_path):
        """Verify TripleOscillator has expected parameters."""
        project = Project(name="Test", bpm=120)
        track = InstrumentTrack(name="Lead", instrument="tripleoscillator")
        project.add_track(track)

        filepath = tmp_path / "test.mmp"
        write_project(project, filepath)

        content = filepath.read_text()

        # Check for oscillator parameters
        for i in range(3):
            assert f'vol{i}=' in content
            assert f'pan{i}=' in content
            assert f'coarse{i}=' in content
            assert f'wavetype{i}=' in content
