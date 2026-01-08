"""Tests for automation tools."""

import pytest
from lmms_mcp.tools.automation import (
    create_automation_track,
    create_automation_clip,
    set_automation_points,
    describe_automation_track,
)


def test_create_automation_track(sample_project):
    """Test creating an automation track."""
    result = create_automation_track(
        path=str(sample_project),
        name="Volume Automation",
    )
    
    assert result["status"] == "created"
    assert result["track"]["name"] == "Volume Automation"
    assert result["track"]["type"] == "AutomationTrack"


def test_create_automation_clip(sample_project):
    """Test creating an automation clip."""
    # First create automation track
    create_automation_track(str(sample_project), "Automation")
    
    # Get the track ID (should be 1, since sample has 1 track already)
    from lmms_mcp.tools.tracks import list_tracks
    tracks = list_tracks(str(sample_project))
    auto_track_id = next(t["id"] for t in tracks if t["type"] == "AutomationTrack")
    
    result = create_automation_clip(
        path=str(sample_project),
        track_id=auto_track_id,
        name="Test Clip",
        position=0,
        length=16,
        target_track=0,
        target_param="volume",
    )
    
    assert result["status"] == "created"
    assert result["clip"]["name"] == "Test Clip"
    assert result["clip"]["length"] == 16


def test_set_automation_points(sample_project):
    """Test setting automation points."""
    # Create automation track and clip
    create_automation_track(str(sample_project), "Automation")
    from lmms_mcp.tools.tracks import list_tracks
    tracks = list_tracks(str(sample_project))
    auto_track_id = next(t["id"] for t in tracks if t["type"] == "AutomationTrack")
    
    create_automation_clip(
        str(sample_project),
        auto_track_id,
        "Test Clip",
        0,
        16,
        0,
        "volume",
    )
    
    # Set automation points
    points = [
        {"time": 0, "value": 0.0},
        {"time": 8, "value": 1.0},
        {"time": 16, "value": 0.5},
    ]
    
    result = set_automation_points(
        path=str(sample_project),
        track_id=auto_track_id,
        clip_id=0,
        points=points,
    )
    
    assert result["status"] == "updated"
    assert result["point_count"] == 3


def test_describe_automation_track(sample_project):
    """Test describing an automation track."""
    # Create automation track with clip
    create_automation_track(str(sample_project), "Automation")
    from lmms_mcp.tools.tracks import list_tracks
    tracks = list_tracks(str(sample_project))
    auto_track_id = next(t["id"] for t in tracks if t["type"] == "AutomationTrack")
    
    create_automation_clip(
        str(sample_project),
        auto_track_id,
        "Test Clip",
        0,
        16,
        0,
        "volume",
    )
    
    result = describe_automation_track(
        path=str(sample_project),
        track_id=auto_track_id,
    )
    
    assert result["name"] == "Automation"
    assert result["clip_count"] == 1
    assert len(result["clips"]) == 1
