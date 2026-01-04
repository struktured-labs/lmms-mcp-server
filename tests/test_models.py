"""Tests for LMMS models."""

import pytest

from lmms_mcp.models.note import Note, parse_pitch
from lmms_mcp.models.pattern import Pattern
from lmms_mcp.models.track import InstrumentTrack
from lmms_mcp.models.project import Project


class TestNote:
    def test_parse_pitch_midi(self):
        assert parse_pitch(60) == 60
        assert parse_pitch(127) == 127
        assert parse_pitch(0) == 0

    def test_parse_pitch_name(self):
        assert parse_pitch("C4") == 60
        assert parse_pitch("A4") == 69
        assert parse_pitch("C#4") == 61
        assert parse_pitch("D#5") == 75

    def test_pitch_to_name(self):
        assert Note.pitch_to_name(60) == "C4"
        assert Note.pitch_to_name(69) == "A4"
        assert Note.pitch_to_name(61) == "C#4"

    def test_note_creation(self):
        note = Note(pitch=60, start=0.0, length=1.0)
        assert note.pitch == 60
        assert note.start == 0.0
        assert note.length == 1.0
        assert note.velocity == 100
        assert note.name == "C4"


class TestPattern:
    def test_pattern_creation(self):
        pattern = Pattern(name="Test Pattern", position=0, length=4)
        assert pattern.name == "Test Pattern"
        assert pattern.position == 0
        assert pattern.length == 4
        assert len(pattern.notes) == 0

    def test_add_note(self):
        pattern = Pattern(name="Test")
        note = Note(pitch=60, start=0.0, length=1.0)
        pattern.add_note(note)
        assert len(pattern.notes) == 1
        assert pattern.notes[0].pitch == 60

    def test_clear(self):
        pattern = Pattern(name="Test")
        pattern.add_note(Note(pitch=60, start=0.0, length=1.0))
        pattern.add_note(Note(pitch=64, start=1.0, length=1.0))
        assert len(pattern.notes) == 2
        pattern.clear()
        assert len(pattern.notes) == 0


class TestTrack:
    def test_instrument_track_creation(self):
        track = InstrumentTrack(name="Lead", instrument="tripleoscillator")
        assert track.name == "Lead"
        assert track.instrument == "tripleoscillator"
        assert track.volume == 1.0
        assert len(track.patterns) == 0

    def test_add_pattern(self):
        track = InstrumentTrack(name="Lead")
        pattern = Pattern(name="Intro")
        track.add_pattern(pattern)
        assert len(track.patterns) == 1
        assert track.patterns[0].id == 0


class TestProject:
    def test_project_creation(self):
        project = Project(name="Test Song", bpm=140)
        assert project.name == "Test Song"
        assert project.bpm == 140
        assert project.time_sig_num == 4
        assert project.time_sig_den == 4
        assert len(project.tracks) == 0

    def test_add_track(self):
        project = Project(name="Test")
        track = InstrumentTrack(name="Lead")
        project.add_track(track)
        assert len(project.tracks) == 1
        assert project.tracks[0].id == 0
        assert project.get_track(0) == track

    def test_remove_track(self):
        project = Project(name="Test")
        project.add_track(InstrumentTrack(name="Lead"))
        project.add_track(InstrumentTrack(name="Bass"))
        assert len(project.tracks) == 2
        assert project.remove_track(0)
        assert len(project.tracks) == 1
        assert project.tracks[0].name == "Bass"
        assert project.tracks[0].id == 0  # Reindexed

    def test_describe(self):
        project = Project(name="Test", bpm=120)
        project.add_track(InstrumentTrack(name="Lead"))
        desc = project.describe()
        assert desc["name"] == "Test"
        assert desc["bpm"] == 120
        assert desc["track_count"] == 1
