"""Tests for pattern management tools."""

import pytest
from lmms_mcp.tools.patterns import (
    create_pattern,
    list_patterns,
    describe_pattern,
    add_notes,
    clear_pattern,
    extend_pattern,
)


def test_create_pattern(sample_project):
    """Test creating a new pattern."""
    result = create_pattern(
        path=str(sample_project),
        track_id=0,
        name="New Pattern",
        position=0,
        length=4,
    )
    
    assert result["status"] == "created"
    assert result["pattern"]["name"] == "New Pattern"
    assert result["pattern"]["length"] == 4


def test_list_patterns(sample_project):
    """Test listing patterns on a track."""
    patterns = list_patterns(path=str(sample_project), track_id=0)
    
    assert len(patterns) == 1
    assert patterns[0]["name"] == "Test Pattern"


def test_describe_pattern(sample_project):
    """Test describing a pattern."""
    result = describe_pattern(
        path=str(sample_project),
        track_id=0,
        pattern_id=0,
    )
    
    assert "pattern" in result
    assert "notes" in result
    assert result["pattern"]["name"] == "Test Pattern"
    assert len(result["notes"]) == 3  # From fixture


def test_add_notes(sample_project):
    """Test adding notes to a pattern."""
    notes = [
        {"pitch": 72, "start": 3.0, "length": 1.0, "velocity": 100},
        {"pitch": 76, "start": 4.0, "length": 1.0, "velocity": 90},
    ]
    
    result = add_notes(
        path=str(sample_project),
        track_id=0,
        pattern_id=0,
        notes=notes,
    )
    
    assert result["status"] == "added"
    assert result["notes_added"] == 2
    assert result["pattern"]["note_count"] == 5  # 3 original + 2 new


def test_clear_pattern(sample_project):
    """Test clearing all notes from a pattern."""
    result = clear_pattern(
        path=str(sample_project),
        track_id=0,
        pattern_id=0,
    )
    
    assert result["status"] == "cleared"
    
    # Verify notes are gone
    desc = describe_pattern(str(sample_project), 0, 0)
    assert len(desc["notes"]) == 0


def test_extend_pattern(sample_project):
    """Test extending a pattern length."""
    # Original length is 4 bars
    result = extend_pattern(
        path=str(sample_project),
        track_id=0,
        pattern_id=0,
        new_length=8,
    )
    
    assert result["status"] == "extended"
    assert result["old_length"] == 4
    assert result["new_length"] == 8
    
    # Verify it persisted
    desc = describe_pattern(str(sample_project), 0, 0)
    assert desc["pattern"]["length"] == 8


def test_pattern_with_beats_notation(sample_project):
    """Test that notes use beats (not ticks) for timing."""
    notes = [
        {"pitch": 60, "start": 0.0, "length": 0.5, "velocity": 100},
        {"pitch": 64, "start": 0.5, "length": 0.5, "velocity": 100},
    ]
    
    add_notes(str(sample_project), 0, 0, notes)
    
    desc = describe_pattern(str(sample_project), 0, 0)
    # Check that timing is in beats, not ticks
    assert all(note["start"] < 100 for note in desc["notes"])  # Should be beats, not ticks


def test_invalid_pattern_id(sample_project):
    """Test operations with invalid pattern ID."""
    result = describe_pattern(str(sample_project), 0, 999)
    # Should handle gracefully (might return None or error)
    assert result is None or "error" in result or result.get("status") == "not_found"
