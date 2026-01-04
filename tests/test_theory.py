"""Tests for music theory helpers."""

import pytest

from lmms_mcp.theory import (
    build_chord,
    build_scale,
    get_chord_in_key,
    get_chord_progression,
)


class TestChords:
    def test_major_chord(self):
        # C major = C, E, G
        chord = build_chord("C4", "maj")
        assert chord == [60, 64, 67]

    def test_minor_chord(self):
        # A minor = A, C, E
        chord = build_chord("A4", "min")
        assert chord == [69, 72, 76]

    def test_major_7th(self):
        # Cmaj7 = C, E, G, B
        chord = build_chord("C4", "maj7")
        assert chord == [60, 64, 67, 71]

    def test_dominant_7th(self):
        # G7 = G, B, D, F
        chord = build_chord("G4", "dom7")
        assert chord == [67, 71, 74, 77]

    def test_chord_from_midi_number(self):
        # C4 = 60
        chord = build_chord(60, "maj")
        assert chord == [60, 64, 67]


class TestScales:
    def test_major_scale(self):
        # C major = C, D, E, F, G, A, B
        scale = build_scale("C4", "major")
        assert scale == [60, 62, 64, 65, 67, 69, 71]

    def test_minor_scale(self):
        # A minor = A, B, C, D, E, F, G
        scale = build_scale("A4", "minor")
        assert scale == [69, 71, 72, 74, 76, 77, 79]

    def test_minor_pentatonic(self):
        # A minor pentatonic = A, C, D, E, G
        scale = build_scale("A4", "minor_pentatonic")
        assert scale == [69, 72, 74, 76, 79]

    def test_two_octaves(self):
        scale = build_scale("C4", "major", octaves=2)
        assert len(scale) == 14
        assert scale[7] == 72  # C5


class TestChordProgressions:
    def test_chord_in_key(self):
        # ii chord in C major = D minor
        chord = get_chord_in_key("C4", "major", 2)
        # D, F, A
        assert chord == [62, 65, 69]

    def test_i_v_vi_iv(self):
        # Classic pop progression in C major
        progression = get_chord_progression("C4", "major", [1, 5, 6, 4])
        assert len(progression) == 4
        # I = C major
        assert progression[0] == [60, 64, 67]
        # V = G major
        assert progression[1] == [67, 71, 74]
        # vi = A minor
        assert progression[2] == [69, 72, 76]
        # IV = F major
        assert progression[3] == [65, 69, 72]
