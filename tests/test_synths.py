"""Tests for synthesizer models."""

import pytest
from pathlib import Path
import tempfile

from lmms_mcp.models.project import Project
from lmms_mcp.models.track import (
    TripleOscillatorTrack, KickerTrack, MonstroTrack,
    Oscillator, FilterSettings,
    WAVE_SHAPES, MODULATION_ALGOS,
)
from lmms_mcp.models.pattern import Pattern
from lmms_mcp.xml.writer import write_project
from lmms_mcp.xml.parser import parse_project


@pytest.fixture
def test_project():
    """Create a test project."""
    with tempfile.NamedTemporaryFile(suffix=".mmp", delete=False) as f:
        path = Path(f.name)

    project = Project(name="Test", bpm=140)
    write_project(project, path)

    yield str(path)

    path.unlink(missing_ok=True)


class TestOscillator:
    """Test Oscillator model."""

    def test_oscillator_defaults(self):
        """Test default oscillator settings."""
        osc = Oscillator()

        assert osc.wave_shape == 2  # saw
        assert osc.volume == 100
        assert osc.pan == 0
        assert osc.coarse == 0

    def test_oscillator_custom(self):
        """Test custom oscillator settings."""
        osc = Oscillator(
            wave_shape=WAVE_SHAPES["moogsaw"],
            volume=80,
            pan=-50,
            coarse=-12,
            fine_left=0.1,
            fine_right=-0.1,
        )

        assert osc.wave_shape == 4  # moogsaw
        assert osc.volume == 80
        assert osc.pan == -50
        assert osc.coarse == -12


class TestWaveShapes:
    """Test waveform constants."""

    def test_all_waveforms_defined(self):
        """Test all expected waveforms are defined."""
        expected = ["sine", "triangle", "saw", "square", "moogsaw", "exp", "noise"]
        for wave in expected:
            assert wave in WAVE_SHAPES

    def test_waveform_values(self):
        """Test waveform numeric values."""
        assert WAVE_SHAPES["sine"] == 0
        assert WAVE_SHAPES["triangle"] == 1
        assert WAVE_SHAPES["saw"] == 2
        assert WAVE_SHAPES["square"] == 3
        assert WAVE_SHAPES["moogsaw"] == 4


class TestModulationAlgos:
    """Test modulation algorithm constants."""

    def test_all_algos_defined(self):
        """Test all expected algorithms are defined."""
        expected = ["pm", "am", "mix", "sync", "fm"]
        for algo in expected:
            assert algo in MODULATION_ALGOS


class TestTripleOscillatorTrack:
    """Test Triple Oscillator synth track."""

    def test_tripleoscillator_defaults(self):
        """Test default Triple Oscillator settings."""
        track = TripleOscillatorTrack(
            name="Synth",
            osc1=Oscillator(),
            osc2=Oscillator(),
            osc3=Oscillator(),
        )

        assert track.name == "Synth"
        assert track.osc1.wave_shape == 2  # saw
        assert track.osc2.wave_shape == 2
        assert track.osc3.wave_shape == 2

    def test_tripleoscillator_custom(self):
        """Test custom Triple Oscillator settings."""
        track = TripleOscillatorTrack(
            name="Fat Bass",
            osc1=Oscillator(wave_shape=WAVE_SHAPES["saw"], volume=100, coarse=0),
            osc2=Oscillator(wave_shape=WAVE_SHAPES["saw"], volume=100, coarse=-12),
            osc3=Oscillator(wave_shape=WAVE_SHAPES["square"], volume=50, coarse=0),
            mod_algo1=MODULATION_ALGOS["pm"],
            mod_algo2=MODULATION_ALGOS["pm"],
        )

        assert track.osc1.volume == 100
        assert track.osc2.coarse == -12
        assert track.osc3.wave_shape == 3

    def test_tripleoscillator_with_filter(self):
        """Test Triple Oscillator with filter settings."""
        track = TripleOscillatorTrack(
            name="Wobble",
            osc1=Oscillator(),
            osc2=Oscillator(),
            osc3=Oscillator(),
            filter=FilterSettings(
                filter_type=6,  # moog
                cutoff=500,
                resonance=0.8,
            ),
        )

        assert track.filter.filter_type == 6
        assert track.filter.cutoff == 500


class TestKickerTrack:
    """Test Kicker synth track."""

    def test_kicker_defaults(self):
        """Test default Kicker settings."""
        track = KickerTrack(name="Kick")

        assert track.name == "Kick"
        assert track.start_freq == 150
        assert track.end_freq == 40
        assert track.decay == 300
        assert track.distortion == 50

    def test_kicker_808_style(self):
        """Test 808-style sub bass settings."""
        track = KickerTrack(
            name="808 Sub",
            start_freq=100,
            end_freq=30,
            decay=500,
            distortion=20,
            gain=1.2,
        )

        assert track.start_freq == 100
        assert track.end_freq == 30
        assert track.decay == 500
        assert track.gain == 1.2

    def test_kicker_punchy_kick(self):
        """Test punchy kick drum settings."""
        track = KickerTrack(
            name="Punchy Kick",
            start_freq=500,
            end_freq=50,
            decay=100,
            distortion=80,
        )

        assert track.start_freq == 500
        assert track.decay == 100


class TestMonstroTrack:
    """Test Monstro synth track."""

    def test_monstro_defaults(self):
        """Test default Monstro settings."""
        track = MonstroTrack(name="Pad")

        assert track.name == "Pad"
        assert track.lfo1_rate == 1.0
        assert track.lfo2_rate == 1.0

    def test_monstro_custom_oscillators(self):
        """Test Monstro with custom oscillator waves."""
        track = MonstroTrack(
            name="Growl",
            osc1_wave=2,  # saw
            osc2_wave=2,  # saw
            osc3_wave1=0,  # sine for sub (Monstro uses wave1/wave2 for osc3)
        )

        assert track.osc1_wave == 2
        assert track.osc2_wave == 2
        assert track.osc3_wave1 == 0

    def test_monstro_with_lfo(self):
        """Test Monstro with LFO rates."""
        track = MonstroTrack(
            name="Evolving",
            lfo1_rate=4.0,
            lfo2_rate=0.25,
        )

        assert track.lfo1_rate == 4.0
        assert track.lfo2_rate == 0.25


class TestSynthProjectRoundtrip:
    """Test synth tracks survive project save/load."""

    def test_tripleoscillator_roundtrip(self, test_project):
        """Test Triple Oscillator survives save/load."""
        project = Project(name="Synth Test", bpm=140)

        track = TripleOscillatorTrack(
            name="Bass",
            osc1=Oscillator(wave_shape=2, volume=100),
            osc2=Oscillator(wave_shape=2, volume=80, coarse=-12),
            osc3=Oscillator(wave_shape=3, volume=50),
        )
        pattern = Pattern(name="Test", position=0, length=4)
        track.add_pattern(pattern)
        project.add_track(track)

        # Save
        write_project(project, Path(test_project))

        # Load and verify
        reloaded = parse_project(Path(test_project))
        assert len(reloaded.tracks) == 1
        assert reloaded.tracks[0].name == "Bass"

    def test_kicker_roundtrip(self, test_project):
        """Test Kicker survives save/load."""
        project = Project(name="Kick Test", bpm=140)

        track = KickerTrack(
            name="Sub Kick",
            start_freq=200,
            end_freq=40,
            decay=400,
        )
        pattern = Pattern(name="Kicks", position=0, length=4)
        track.add_pattern(pattern)
        project.add_track(track)

        write_project(project, Path(test_project))

        reloaded = parse_project(Path(test_project))
        assert len(reloaded.tracks) == 1
        assert reloaded.tracks[0].name == "Sub Kick"


class TestSynthForDubstep:
    """Test typical dubstep synth configurations."""

    def test_reese_bass(self):
        """Test Reese bass configuration - two detuned saws."""
        track = TripleOscillatorTrack(
            name="Reese Bass",
            osc1=Oscillator(wave_shape=WAVE_SHAPES["saw"], volume=100, coarse=0, fine_left=-0.1),
            osc2=Oscillator(wave_shape=WAVE_SHAPES["saw"], volume=100, coarse=0, fine_right=0.1),
            osc3=Oscillator(wave_shape=WAVE_SHAPES["sine"], volume=80, coarse=-12),  # sub
            mod_algo1=MODULATION_ALGOS["mix"],
        )

        assert track.osc1.wave_shape == 2
        assert track.osc2.wave_shape == 2
        assert track.osc3.coarse == -12  # octave down for sub

    def test_808_sub(self):
        """Test 808-style sub bass."""
        track = KickerTrack(
            name="808 Sub",
            start_freq=60,
            end_freq=35,
            decay=800,  # long decay
            distortion=10,  # minimal distortion
            gain=1.5,  # boost it
        )

        assert track.decay == 800
        assert track.distortion == 10
