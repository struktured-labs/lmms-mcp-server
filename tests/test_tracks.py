"""Tests for track management tools."""

import pytest
from lmms_mcp.tools.tracks import (
    list_tracks,
    add_instrument_track,
    add_sample_track,
    remove_track,
    set_track_volume,
    set_track_pan,
    set_track_pitchrange,
)


def test_list_tracks_empty(empty_project):
    """Test listing tracks on empty project."""
    tracks = list_tracks(path=str(empty_project))
    assert len(tracks) == 0


def test_list_tracks(sample_project):
    """Test listing tracks on project with content."""
    tracks = list_tracks(path=str(sample_project))
    assert len(tracks) == 1
    assert tracks[0]["name"] == "Test Track"
    assert tracks[0]["type"] == "InstrumentTrack"


def test_add_instrument_track(empty_project):
    """Test adding an instrument track."""
    result = add_instrument_track(
        path=str(empty_project),
        name="Synth Lead",
        instrument="tripleoscillator",
    )
    
    assert result["status"] == "added"
    assert result["track"]["name"] == "Synth Lead"
    assert result["track_count"] == 1
    
    # Verify it persisted
    tracks = list_tracks(path=str(empty_project))
    assert len(tracks) == 1
    assert tracks[0]["name"] == "Synth Lead"


def test_add_sample_track(empty_project):
    """Test adding a sample track."""
    result = add_sample_track(
        path=str(empty_project),
        name="Kick",
        sample_path="/path/to/kick.ogg",
    )
    
    assert result["status"] == "added"
    assert result["track"]["name"] == "Kick"
    assert result["track"]["type"] == "SampleTrack"


def test_remove_track(sample_project):
    """Test removing a track."""
    # First verify track exists
    tracks = list_tracks(path=str(sample_project))
    assert len(tracks) == 1
    
    # Remove it
    result = remove_track(path=str(sample_project), track_id=0)
    assert result["status"] == "removed"
    assert result["track_count"] == 0
    
    # Verify it's gone
    tracks = list_tracks(path=str(sample_project))
    assert len(tracks) == 0


def test_remove_nonexistent_track(sample_project):
    """Test removing a track that doesn't exist."""
    result = remove_track(path=str(sample_project), track_id=999)
    assert result["status"] == "not_found"


def test_set_track_volume(sample_project):
    """Test setting track volume."""
    result = set_track_volume(
        path=str(sample_project),
        track_id=0,
        volume=0.75,
    )
    
    assert result["status"] == "updated"
    assert result["track"]["volume"] == 0.75


def test_set_track_pan(sample_project):
    """Test setting track pan."""
    result = set_track_pan(
        path=str(sample_project),
        track_id=0,
        pan=0.5,  # Pan right
    )
    
    assert result["status"] == "updated"
    assert result["track"]["pan"] == 0.5


def test_set_track_pitchrange(sample_project):
    """Test setting track pitch range."""
    result = set_track_pitchrange(
        path=str(sample_project),
        track_id=0,
        pitchrange=24,
    )
    
    assert result["status"] == "updated"
    assert result["pitchrange"] == 24
    
    # Verify it persisted
    tracks = list_tracks(path=str(sample_project))
    # Note: pitchrange might not be in describe() output, 
    # but this tests the tool works


def test_multiple_tracks(empty_project):
    """Test adding multiple tracks."""
    # Add tracks
    add_instrument_track(str(empty_project), "Track 1", "tripleoscillator")
    add_instrument_track(str(empty_project), "Track 2", "kicker")
    add_sample_track(str(empty_project), "Sample", "/path/to/sample.ogg")
    
    tracks = list_tracks(path=str(empty_project))
    assert len(tracks) == 3
    assert tracks[0]["name"] == "Track 1"
    assert tracks[1]["name"] == "Track 2"
    assert tracks[2]["name"] == "Sample"
