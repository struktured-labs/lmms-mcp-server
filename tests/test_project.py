"""Tests for project management tools."""

import pytest
from pathlib import Path
from lmms_mcp.tools.project import (
    create_project,
    load_project,
    get_project_info,
    set_project_bpm,
    set_project_time_signature,
)


def test_create_project(temp_dir):
    """Test creating a new LMMS project."""
    project_path = str(temp_dir / "new.mmp")
    result = create_project(
        path=project_path,
        bpm=140,
        time_sig_num=4,
        time_sig_den=4,
    )
    
    assert result["status"] == "created"
    assert Path(project_path).exists()
    assert result["bpm"] == 140


def test_load_project(sample_project):
    """Test loading an existing project."""
    result = load_project(path=str(sample_project))
    
    assert result["status"] == "loaded"
    assert result["bpm"] == 140
    assert result["track_count"] == 1


def test_get_project_info(sample_project):
    """Test getting project information."""
    info = get_project_info(path=str(sample_project))
    
    assert info["bpm"] == 140
    assert info["time_signature"] == "4/4"
    assert info["track_count"] == 1
    assert "tracks" in info


def test_set_project_bpm(sample_project):
    """Test changing project BPM."""
    result = set_project_bpm(path=str(sample_project), bpm=120)
    
    assert result["status"] == "updated"
    assert result["bpm"] == 120
    
    # Verify it persisted
    info = get_project_info(path=str(sample_project))
    assert info["bpm"] == 120


def test_set_project_time_signature(sample_project):
    """Test changing project time signature."""
    result = set_project_time_signature(
        path=str(sample_project),
        numerator=3,
        denominator=4,
    )
    
    assert result["status"] == "updated"
    assert result["time_signature"] == "3/4"
    
    # Verify it persisted
    info = get_project_info(path=str(sample_project))
    assert info["time_signature"] == "3/4"


def test_invalid_bpm(sample_project):
    """Test that invalid BPM values are rejected."""
    with pytest.raises((ValueError, Exception)):
        set_project_bpm(path=str(sample_project), bpm=0)
    
    with pytest.raises((ValueError, Exception)):
        set_project_bpm(path=str(sample_project), bpm=1000)
