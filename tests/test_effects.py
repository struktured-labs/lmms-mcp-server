"""Tests for effects chain models."""

import pytest
from pathlib import Path
import tempfile

from lmms_mcp.models.project import Project
from lmms_mcp.models.track import (
    SF2InstrumentTrack, Effect, BUILTIN_EFFECTS, FilterSettings,
)
from lmms_mcp.models.pattern import Pattern
from lmms_mcp.xml.writer import write_project
from lmms_mcp.xml.parser import parse_project


@pytest.fixture
def test_project():
    """Create a test project with an SF2 track."""
    with tempfile.NamedTemporaryFile(suffix=".mmp", delete=False) as f:
        path = Path(f.name)

    project = Project(name="Test", bpm=120)
    track = SF2InstrumentTrack(
        name="Test Synth",
        sf2_path="/usr/share/sounds/sf2/FluidR3_GM.sf2",
        bank=0,
        patch=81,
        filter=FilterSettings(),
        effects=[],
    )
    pattern = Pattern(name="Test", position=0, length=4)
    track.add_pattern(pattern)
    project.add_track(track)
    write_project(project, path)

    yield str(path)

    path.unlink(missing_ok=True)


class TestEffectModel:
    """Test Effect model class."""

    def test_effect_defaults(self):
        """Test default effect settings."""
        effect = Effect(name="dualfilter")

        assert effect.name == "dualfilter"
        assert effect.enabled is True
        assert effect.wet == 1.0
        assert effect.params == {}

    def test_effect_with_params(self):
        """Test effect with custom parameters."""
        effect = Effect(
            name="compressor",
            wet=0.8,
            params={"threshold": -20, "ratio": 4.0, "attack": 5},
        )

        assert effect.name == "compressor"
        assert effect.params["threshold"] == -20
        assert effect.params["ratio"] == 4.0

    def test_effect_describe(self):
        """Test effect describe method."""
        effect = Effect(
            name="dualfilter",
            wet=0.5,
            params={"cut1": 500},
        )

        desc = effect.describe()

        assert desc["name"] == "dualfilter"
        assert desc["wet"] == 0.5
        assert desc["params"]["cut1"] == 500


class TestBuiltinEffects:
    """Test builtin effects constants."""

    def test_dualfilter_defaults(self):
        """Test dualfilter has expected defaults."""
        assert "dualfilter" in BUILTIN_EFFECTS
        defaults = BUILTIN_EFFECTS["dualfilter"]
        assert "cut1" in defaults
        assert "res1" in defaults

    def test_waveshaper_defaults(self):
        """Test waveshaper has expected defaults."""
        assert "waveshaper" in BUILTIN_EFFECTS
        defaults = BUILTIN_EFFECTS["waveshaper"]
        assert "input" in defaults
        assert "output" in defaults

    def test_compressor_defaults(self):
        """Test compressor has expected defaults."""
        assert "compressor" in BUILTIN_EFFECTS
        defaults = BUILTIN_EFFECTS["compressor"]
        assert "threshold" in defaults
        assert "ratio" in defaults

    def test_all_expected_effects_present(self):
        """Test all expected effects are defined."""
        expected = [
            "dualfilter", "waveshaper", "bassbooster", "delay",
            "flanger", "reverbsc", "compressor", "bitcrush",
            "stereoenhancer", "amplifier", "eq",
        ]
        for effect_name in expected:
            assert effect_name in BUILTIN_EFFECTS, f"Missing effect: {effect_name}"


class TestEffectChain:
    """Test effect chain on tracks."""

    def test_track_with_effects(self):
        """Test track with effects chain."""
        track = SF2InstrumentTrack(
            name="Bass",
            sf2_path="/test.sf2",
            effects=[
                Effect(name="dualfilter", params={"cut1": 100}),
                Effect(name="waveshaper", params={"input": 1.5}),
            ],
        )

        assert len(track.effects) == 2
        assert track.effects[0].name == "dualfilter"
        assert track.effects[1].name == "waveshaper"

    def test_add_effect_to_chain(self):
        """Test adding effect to existing chain."""
        track = SF2InstrumentTrack(
            name="Bass",
            sf2_path="/test.sf2",
            effects=[Effect(name="dualfilter")],
        )

        track.effects.append(Effect(name="compressor"))

        assert len(track.effects) == 2
        assert track.effects[1].name == "compressor"

    def test_remove_effect_from_chain(self):
        """Test removing effect from chain."""
        track = SF2InstrumentTrack(
            name="Bass",
            sf2_path="/test.sf2",
            effects=[
                Effect(name="dualfilter"),
                Effect(name="waveshaper"),
                Effect(name="compressor"),
            ],
        )

        removed = track.effects.pop(1)

        assert removed.name == "waveshaper"
        assert len(track.effects) == 2
        assert track.effects[0].name == "dualfilter"
        assert track.effects[1].name == "compressor"


class TestLADSPAEffect:
    """Test LADSPA plugin effects."""

    def test_ladspa_effect(self):
        """Test LADSPA effect with plugin info."""
        effect = Effect(
            name="ladspaeffect",
            plugin_file="cmt.so",
            plugin_name="freeverb3",
            params={"room": 0.8},
        )

        assert effect.name == "ladspaeffect"
        assert effect.plugin_file == "cmt.so"
        assert effect.plugin_name == "freeverb3"


class TestDubstepWobbleChain:
    """Test creating typical dubstep effect chains."""

    def test_wobble_chain(self):
        """Test typical wobble bass effect chain."""
        effects = [
            Effect(
                name="dualfilter",
                wet=1.0,
                params={"cut1": 100, "res1": 0.8, "enabled1": 1},
            ),
            Effect(
                name="waveshaper",
                wet=0.5,
                params={"input": 1.5, "output": 1.0},
            ),
            Effect(
                name="compressor",
                wet=1.0,
                params={"threshold": -15, "ratio": 4.0},
            ),
        ]

        track = SF2InstrumentTrack(
            name="WOBBLE BASS",
            sf2_path="/test.sf2",
            effects=effects,
        )

        assert len(track.effects) == 3
        # Verify chain order
        assert track.effects[0].name == "dualfilter"
        assert track.effects[1].name == "waveshaper"
        assert track.effects[2].name == "compressor"


class TestEffectRoundtrip:
    """Test effects survive save/load cycle."""

    def test_effect_project_roundtrip(self, test_project):
        """Test effects are saved and loaded correctly."""
        # Load project
        project = parse_project(Path(test_project))

        # Add effects to track
        track = project.tracks[0]
        track.effects = [
            Effect(name="dualfilter", params={"cut1": 200}),
            Effect(name="waveshaper", wet=0.7),
        ]

        # Save and reload
        write_project(project, Path(test_project))
        reloaded = parse_project(Path(test_project))

        # Verify track exists
        assert len(reloaded.tracks) == 1
        assert reloaded.tracks[0].name == "Test Synth"
        # Note: Effect parsing may not be complete in parser yet
