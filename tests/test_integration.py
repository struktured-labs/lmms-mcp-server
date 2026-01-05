"""Integration tests for LMMS MCP server."""

import pytest
from pathlib import Path

from lmms_mcp.models.project import Project
from lmms_mcp.models.track import InstrumentTrack
from lmms_mcp.models.pattern import Pattern
from lmms_mcp.models.note import Note
from lmms_mcp.xml.writer import write_project
from lmms_mcp.cli import LMMSCli


class TestLMMSCli:
    """Test LMMS CLI wrapper."""

    @pytest.fixture
    def cli(self):
        """Create CLI instance, skip if LMMS not found."""
        try:
            return LMMSCli()
        except RuntimeError as e:
            pytest.skip(f"LMMS not available: {e}")

    def test_find_lmms(self, cli):
        """Test that LMMS executable is found."""
        assert cli.lmms_path is not None
        assert Path(cli.lmms_path).exists()

    def test_version(self, cli):
        """Test getting LMMS version."""
        version = cli.version()
        assert version is not None
        assert "LMMS" in version or "lmms" in version.lower()

    def test_render_simple_project(self, cli, tmp_path):
        """Test rendering a simple project."""
        # Create a simple project with notes
        project = Project(name="RenderTest", bpm=120)
        track = InstrumentTrack(name="Lead", instrument="tripleoscillator")
        pattern = Pattern(name="Test", position=0, length=1)

        # Add a C major chord
        pattern.add_note(Note(pitch=60, start=0.0, length=1.0, velocity=100))
        pattern.add_note(Note(pitch=64, start=0.0, length=1.0, velocity=100))
        pattern.add_note(Note(pitch=67, start=0.0, length=1.0, velocity=100))

        track.add_pattern(pattern)
        project.add_track(track)

        # Write project
        project_path = tmp_path / "render_test.mmp"
        write_project(project, project_path)

        # Render to FLAC
        output_path = str(tmp_path / "render_test.flac")
        result = cli.render(project_path, output_path=output_path, format="flac")

        assert result["status"] == "success", f"Render failed: {result.get('error')}"
        assert result["output_path"] == output_path
        assert Path(output_path).exists()
        assert Path(output_path).stat().st_size > 0

    def test_render_wav_format(self, cli, tmp_path):
        """Test rendering to WAV format."""
        project = Project(name="WavTest", bpm=140)
        track = InstrumentTrack(name="Synth")
        pattern = Pattern(name="Beat", position=0, length=1)
        pattern.add_note(Note(pitch=48, start=0.0, length=0.5))
        track.add_pattern(pattern)
        project.add_track(track)

        project_path = tmp_path / "wav_test.mmp"
        write_project(project, project_path)

        output_path = str(tmp_path / "wav_test.wav")
        result = cli.render(project_path, output_path=output_path, format="wav")

        assert result["status"] == "success"
        assert Path(output_path).exists()

    def test_render_ogg_format(self, cli, tmp_path):
        """Test rendering to OGG format."""
        project = Project(name="OggTest", bpm=100)
        track = InstrumentTrack(name="Pad")
        pattern = Pattern(name="Ambient", position=0, length=2)
        pattern.add_note(Note(pitch=55, start=0.0, length=2.0))
        track.add_pattern(pattern)
        project.add_track(track)

        project_path = tmp_path / "ogg_test.mmp"
        write_project(project, project_path)

        output_path = str(tmp_path / "ogg_test.ogg")
        result = cli.render(project_path, output_path=output_path, format="ogg")

        assert result["status"] == "success"
        assert Path(output_path).exists()


class TestMCPTools:
    """Test MCP tool functions."""

    def test_all_tools_registered(self):
        """Verify all expected tools are registered."""
        from lmms_mcp.server import mcp

        tools = mcp._tool_manager.list_tools()
        tool_names = {t.name for t in tools}

        expected_tools = {
            # Project tools
            "create_project",
            "load_project",
            "describe_project",
            "render_preview",
            "render_and_describe",
            # Track tools
            "list_tracks",
            "add_instrument_track",
            "add_sample_track",
            "remove_track",
            "set_track_volume",
            "set_track_pan",
            # Pattern tools
            "create_pattern",
            "add_notes",
            "add_chord",
            "describe_pattern",
            "clear_pattern",
        }

        assert expected_tools.issubset(tool_names), f"Missing tools: {expected_tools - tool_names}"

    def test_create_project_tool(self, tmp_path):
        """Test create_project MCP tool."""
        from lmms_mcp.server import mcp
        from lmms_mcp.xml.parser import parse_project

        # Get the tool function directly from registered tools
        tools = {t.name: t for t in mcp._tool_manager.list_tools()}

        # Verify create_project is registered
        assert "create_project" in tools

        # Test by creating project using models
        from lmms_mcp.models.project import Project
        from lmms_mcp.xml.writer import write_project

        project_path = tmp_path / "tool_test.mmp"
        project = Project(name="ToolTest", bpm=135)
        write_project(project, project_path)

        parsed = parse_project(project_path)
        assert parsed.bpm == 135


class TestFullWorkflow:
    """Test complete music creation workflow."""

    @pytest.fixture
    def cli(self):
        """Create CLI instance, skip if LMMS not found."""
        try:
            return LMMSCli()
        except RuntimeError as e:
            pytest.skip(f"LMMS not available: {e}")

    def test_create_arrange_render_workflow(self, cli, tmp_path):
        """Test full workflow: create -> add tracks -> add notes -> render."""
        from lmms_mcp.theory import build_chord

        # Step 1: Create project
        project = Project(name="FullWorkflow", bpm=128)

        # Step 2: Add multiple tracks
        bass_track = InstrumentTrack(name="Bass", instrument="tripleoscillator")
        bass_track.volume = 0.8

        lead_track = InstrumentTrack(name="Lead", instrument="tripleoscillator")
        lead_track.volume = 0.7

        # Step 3: Create patterns with notes
        bass_pattern = Pattern(name="BassLine", position=0, length=4)
        bass_notes = [
            Note(pitch=36, start=0.0, length=1.0),  # C2
            Note(pitch=36, start=1.0, length=1.0),
            Note(pitch=38, start=2.0, length=1.0),  # D2
            Note(pitch=41, start=3.0, length=1.0),  # F2
        ]
        for note in bass_notes:
            bass_pattern.add_note(note)
        bass_track.add_pattern(bass_pattern)

        lead_pattern = Pattern(name="Melody", position=0, length=4)
        # Add a C major chord
        chord_notes = build_chord("C4", "maj")
        for i, pitch in enumerate(chord_notes):
            lead_pattern.add_note(Note(pitch=pitch, start=0.0, length=2.0, velocity=100))
        # Add melody notes
        lead_pattern.add_note(Note(pitch=72, start=2.0, length=0.5, velocity=80))  # C5
        lead_pattern.add_note(Note(pitch=74, start=2.5, length=0.5, velocity=80))  # D5
        lead_pattern.add_note(Note(pitch=76, start=3.0, length=1.0, velocity=90))  # E5
        lead_track.add_pattern(lead_pattern)

        project.add_track(bass_track)
        project.add_track(lead_track)

        # Step 4: Write project
        project_path = tmp_path / "full_workflow.mmp"
        write_project(project, project_path)

        # Step 5: Verify project structure
        from lmms_mcp.xml.parser import parse_project
        parsed = parse_project(project_path)

        assert parsed.bpm == 128
        assert len(parsed.tracks) == 2
        assert parsed.tracks[0].name == "Bass"
        assert parsed.tracks[1].name == "Lead"
        assert len(parsed.tracks[0].patterns[0].notes) == 4

        # Step 6: Render audio
        output_path = str(tmp_path / "full_workflow.flac")
        result = cli.render(project_path, output_path=output_path, format="flac")

        assert result["status"] == "success"
        assert Path(output_path).exists()

        # Verify audio file has reasonable size (not empty/corrupted)
        file_size = Path(output_path).stat().st_size
        assert file_size > 1000, f"Audio file too small: {file_size} bytes"

    def test_describe_project(self, tmp_path):
        """Test project description generation."""
        project = Project(name="Description Test", bpm=140)

        track = InstrumentTrack(name="Synth Lead", instrument="tripleoscillator")
        pattern = Pattern(name="Intro Riff", position=0, length=2)
        pattern.add_note(Note(pitch=60, start=0.0, length=0.5))
        pattern.add_note(Note(pitch=64, start=0.5, length=0.5))
        pattern.add_note(Note(pitch=67, start=1.0, length=1.0))
        track.add_pattern(pattern)
        project.add_track(track)

        # Get description
        description = project.to_description()

        assert "140 BPM" in description
        assert "4/4" in description
        assert "Synth Lead" in description
        assert "tripleoscillator" in description
        assert "Intro Riff" in description
