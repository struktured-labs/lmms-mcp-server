"""Tests for voice-to-track tools."""

import pytest
import numpy as np
from lmms_mcp.tools.voice import (
    midi_to_freq,
    freq_to_midi,
    midi_to_note_name,
    pitch_to_notes,
    suggest_instrument,
)


class TestMidiConversions:
    """Test MIDI/frequency conversion functions."""

    def test_midi_to_freq_a440(self):
        """A4 = 440 Hz."""
        assert abs(midi_to_freq(69) - 440.0) < 0.01

    def test_midi_to_freq_c4(self):
        """C4 (middle C) = 261.63 Hz."""
        assert abs(midi_to_freq(60) - 261.63) < 0.1

    def test_freq_to_midi_440(self):
        """440 Hz = A4 = MIDI 69."""
        assert freq_to_midi(440.0) == 69

    def test_freq_to_midi_roundtrip(self):
        """Roundtrip conversion should be consistent."""
        for midi in [36, 48, 60, 72, 84]:
            freq = midi_to_freq(midi)
            result = freq_to_midi(freq)
            assert result == midi

    def test_midi_to_note_name(self):
        """Test note name conversion."""
        assert midi_to_note_name(60) == "C4"
        assert midi_to_note_name(69) == "A4"
        assert midi_to_note_name(61) == "C#4"
        assert midi_to_note_name(48) == "C3"


class TestPitchToNotes:
    """Test pitch data to note conversion."""

    def test_empty_data(self):
        """Empty pitch data returns empty notes."""
        assert pitch_to_notes([]) == []

    def test_single_note(self):
        """Single sustained pitch becomes one note."""
        pitch_data = [
            {"time": 0.0, "frequency": 440.0, "confidence": 0.9},
            {"time": 0.1, "frequency": 440.0, "confidence": 0.9},
            {"time": 0.2, "frequency": 440.0, "confidence": 0.9},
        ]
        notes = pitch_to_notes(pitch_data, bpm=120, quantize=False)
        assert len(notes) >= 1
        assert notes[0]["pitch"] == 69  # A4

    def test_low_confidence_filtered(self):
        """Low confidence pitches are filtered out."""
        pitch_data = [
            {"time": 0.0, "frequency": 440.0, "confidence": 0.1},
            {"time": 0.1, "frequency": 440.0, "confidence": 0.1},
        ]
        notes = pitch_to_notes(pitch_data, confidence_threshold=0.5)
        assert len(notes) == 0

    def test_quantization(self):
        """Notes are quantized to 16th notes."""
        pitch_data = [
            {"time": 0.0, "frequency": 440.0, "confidence": 0.9},
            {"time": 0.11, "frequency": 440.0, "confidence": 0.9},
            {"time": 0.22, "frequency": 440.0, "confidence": 0.9},
        ]
        notes = pitch_to_notes(pitch_data, bpm=120, quantize=True)
        if notes:
            # Start should be quantized to 16th note (0.25 beat increments)
            assert notes[0]["start"] % 0.25 == 0


class TestInstrumentSuggestion:
    """Test instrument suggestion based on note range."""

    def test_bass_range(self):
        """Low notes suggest cello."""
        notes = [{"pitch": 40}]  # E2
        suggested = suggest_instrument(notes)
        assert suggested["patch"] == 42  # Cello

    def test_tenor_range(self):
        """Mid-low notes suggest sax."""
        notes = [{"pitch": 55}]  # G3
        suggested = suggest_instrument(notes)
        assert suggested["patch"] == 66  # Tenor Sax

    def test_alto_range(self):
        """Mid-high notes suggest violin."""
        notes = [{"pitch": 65}]  # F4
        suggested = suggest_instrument(notes)
        assert suggested["patch"] == 40  # Violin

    def test_soprano_range(self):
        """High notes suggest flute."""
        notes = [{"pitch": 80}]  # G#5
        suggested = suggest_instrument(notes)
        assert suggested["patch"] == 73  # Flute

    def test_empty_notes(self):
        """Empty notes default to piano."""
        suggested = suggest_instrument([])
        assert suggested["patch"] == 0  # Piano
