"""Pytest fixtures for LMMS MCP tests."""

import tempfile
from pathlib import Path
import pytest
from lmms_mcp.models.project import Project
from lmms_mcp.xml.writer import write_project


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def empty_project(temp_dir):
    """Create an empty LMMS project for testing."""
    project = Project(
        bpm=140,
        time_sig_num=4,
        time_sig_den=4,
        master_volume=1.0,
        master_pitch=0,
    )
    project_path = temp_dir / "test.mmp"
    write_project(project, project_path)
    return project_path


@pytest.fixture
def sample_project(temp_dir):
    """Create a sample LMMS project with basic content."""
    from lmms_mcp.models.track import InstrumentTrack
    from lmms_mcp.models.pattern import Pattern
    from lmms_mcp.models.note import Note
    
    project = Project(
        bpm=140,
        time_sig_num=4,
        time_sig_den=4,
        master_volume=1.0,
        master_pitch=0,
    )
    
    # Add a basic instrument track with a pattern
    track = InstrumentTrack(
        name="Test Track",
        instrument="tripleoscillator",
        volume=1.0,
        pan=0.0,
    )
    
    pattern = Pattern(
        name="Test Pattern",
        position=0,
        length=4,
    )
    pattern.notes = [
        Note(pitch=60, start=0.0, length=1.0, velocity=100),
        Note(pitch=64, start=1.0, length=1.0, velocity=100),
        Note(pitch=67, start=2.0, length=1.0, velocity=100),
    ]
    track.patterns.append(pattern)
    project.add_track(track)
    
    project_path = temp_dir / "sample.mmp"
    write_project(project, project_path)
    return project_path
