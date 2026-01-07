"""Track models for LMMS projects."""

from pydantic import BaseModel, Field
from typing import Any, Literal

from lmms_mcp.models.pattern import Pattern


# =============================================================================
# Effects Models
# =============================================================================


class Effect(BaseModel):
    """An effect in the FX chain."""

    name: str = Field(description="Effect plugin name")
    enabled: bool = Field(default=True, description="Effect enabled")
    wet: float = Field(default=1.0, ge=0.0, le=1.0, description="Wet/dry mix")
    gate: float = Field(default=0.0, description="Gate threshold")
    params: dict[str, Any] = Field(default_factory=dict, description="Effect-specific parameters")

    # LADSPA/LV2/VST plugin info
    plugin_file: str | None = Field(default=None, description="Plugin file (for LADSPA)")
    plugin_name: str | None = Field(default=None, description="Plugin name within file")

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "enabled": self.enabled,
            "wet": self.wet,
            "params": self.params,
            "plugin_file": self.plugin_file,
            "plugin_name": self.plugin_name,
        }


# Common built-in effects with their default parameters
BUILTIN_EFFECTS = {
    "dualfilter": {
        "cut1": 14000, "res1": 0.5, "gain1": 1.0, "enabled1": 1,
        "cut2": 14000, "res2": 0.5, "gain2": 1.0, "enabled2": 0,
        "mix": 0,  # 0=filter1, 1=filter2, 0.5=both
    },
    "waveshaper": {
        "input": 1.0, "output": 1.0, "clip": 0,
    },
    "bassbooster": {
        "freq": 100, "gain": 1.0, "ratio": 2.0,
    },
    "delay": {
        "delay": 200, "feedback": 0.5, "lfotime": 2000, "lfoamt": 0,
        "outgain": 1.0,
    },
    "flanger": {
        "delay": 3.0, "lfofreq": 0.5, "lfoamt": 0.5, "lfophase": 0.0,
        "feedback": 0.5, "whitenoise": 0.0, "invertfb": 0,
    },
    "reverbsc": {
        "input": 0.5, "size": 0.8, "color": 0.5, "output": 0.5,
    },
    "compressor": {
        "threshold": -20, "ratio": 4.0, "attack": 10, "release": 100,
        "knee": 6.0, "makeupgain": 0.0,
    },
    "bitcrush": {
        "indep": 0, "depth": 8, "rate": 44100,
    },
    "stereoenhancer": {
        "width": 0.5,
    },
    "amplifier": {
        "volume": 1.0, "pan": 0.0, "left": 1.0, "right": 1.0,
    },
    "eq": {
        "lowgain": 0.0, "midgain": 0.0, "highgain": 0.0,
        "lowfreq": 200, "highfreq": 4000,
    },
}


# =============================================================================
# Filter Envelope Model (eldata)
# =============================================================================


class FilterLFO(BaseModel):
    """LFO settings for filter modulation."""

    speed: float = Field(default=0.1, ge=0.0, description="LFO speed")
    amount: float = Field(default=0.0, ge=0.0, le=100.0, description="LFO amount")
    shape: int = Field(default=0, ge=0, le=5, description="0=Sine,1=Tri,2=Saw,3=Sqr,4=User,5=Rand")
    x100: bool = Field(default=False, description="100x speed multiplier")
    sync_mode: int = Field(default=0, description="Tempo sync mode")


class FilterEnvelope(BaseModel):
    """ADSR envelope for filter."""

    predelay: float = Field(default=0.0, ge=0.0, description="Pre-delay")
    attack: float = Field(default=0.0, ge=0.0, description="Attack time")
    hold: float = Field(default=0.5, ge=0.0, description="Hold time")
    decay: float = Field(default=0.5, ge=0.0, description="Decay time")
    sustain: float = Field(default=0.5, ge=0.0, le=1.0, description="Sustain level")
    release: float = Field(default=0.1, ge=0.0, description="Release time")
    amount: float = Field(default=0.0, description="Envelope amount")
    lfo: FilterLFO = Field(default_factory=FilterLFO, description="LFO settings")


class FilterSettings(BaseModel):
    """Filter settings (eldata element)."""

    filter_type: int = Field(default=0, ge=0, le=21, description="Filter type")
    cutoff: float = Field(default=14000, ge=0.0, description="Filter cutoff frequency")
    resonance: float = Field(default=0.5, ge=0.0, le=1.0, description="Filter resonance")
    wet: float = Field(default=0.0, ge=0.0, le=1.0, description="Filter wet/dry")

    # Envelopes for volume, cutoff, resonance
    vol_env: FilterEnvelope = Field(default_factory=FilterEnvelope, description="Volume envelope")
    cut_env: FilterEnvelope = Field(default_factory=FilterEnvelope, description="Cutoff envelope")
    res_env: FilterEnvelope = Field(default_factory=FilterEnvelope, description="Resonance envelope")


# Filter type constants
FILTER_TYPES = {
    "lowpass": 0, "hipass": 1, "bandpass_csg": 2, "bandpass_czpg": 3,
    "notch": 4, "allpass": 5, "moog": 6, "doublelowpass": 7,
    "lowpass_rc12": 8, "bandpass_rc12": 9, "highpass_rc12": 10,
    "lowpass_rc24": 11, "bandpass_rc24": 12, "highpass_rc24": 13,
    "formant": 14, "doublemoog": 15, "lowpass_sv": 16, "bandpass_sv": 17,
    "highpass_sv": 18, "notch_sv": 19, "fastformant": 20, "tripole": 21,
}


# =============================================================================
# Waveform Constants
# =============================================================================


WAVE_SHAPES = {
    "sine": 0, "triangle": 1, "saw": 2, "square": 3,
    "moogsaw": 4, "exp": 5, "noise": 6, "user": 7,
}


MODULATION_ALGOS = {
    "phase": 0, "amplitude": 1, "mix": 2, "sync": 3, "fm": 4,
    # Aliases
    "pm": 0, "am": 1,
}


class Track(BaseModel):
    """Base class for LMMS tracks."""

    id: int = Field(default=0, description="Track ID")
    name: str = Field(default="Track", description="Track name")
    volume: float = Field(default=1.0, ge=0.0, description="Track volume")
    pan: float = Field(default=0.0, ge=-1.0, le=1.0, description="Pan position")
    muted: bool = Field(default=False, description="Track muted")
    solo: bool = Field(default=False, description="Track solo")
    patterns: list[Pattern] = Field(default_factory=list, description="Patterns on track")

    def add_pattern(self, pattern: Pattern) -> None:
        """Add a pattern to the track."""
        pattern.id = len(self.patterns)
        self.patterns.append(pattern)

    def get_pattern(self, pattern_id: int) -> Pattern | None:
        """Get pattern by ID."""
        for pattern in self.patterns:
            if pattern.id == pattern_id:
                return pattern
        return None

    def remove_pattern(self, pattern_id: int) -> Pattern | None:
        """Remove pattern by ID."""
        for i, pattern in enumerate(self.patterns):
            if pattern.id == pattern_id:
                return self.patterns.pop(i)
        return None

    def describe(self) -> dict[str, Any]:
        """Return a description dict."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.__class__.__name__,
            "volume": self.volume,
            "pan": self.pan,
            "muted": self.muted,
            "pattern_count": len(self.patterns),
        }

    def to_description(self) -> str:
        """Human-readable description."""
        status = []
        if self.muted:
            status.append("muted")
        if self.solo:
            status.append("solo")
        status_str = f" ({', '.join(status)})" if status else ""
        return f"Track '{self.name}'{status_str}: {len(self.patterns)} patterns"


class InstrumentTrack(Track):
    """An instrument (synthesizer) track."""

    track_type: Literal["instrument"] = "instrument"
    instrument: str = Field(default="tripleoscillator", description="Instrument plugin")
    preset: str | None = Field(default=None, description="Preset name")
    sample_path: str | None = Field(default=None, description="Sample path for audiofileprocessor")

    def describe(self) -> dict[str, Any]:
        result = super().describe()
        result.update({
            "instrument": self.instrument,
            "preset": self.preset,
        })
        if self.sample_path:
            result["sample_path"] = self.sample_path
        return result

    def to_description(self) -> str:
        preset_str = f" ({self.preset})" if self.preset else ""
        return f"Instrument '{self.name}' [{self.instrument}{preset_str}]: {len(self.patterns)} patterns"


class SampleTrack(Track):
    """A sample-based track (AudioFileProcessor)."""

    track_type: Literal["sample"] = "sample"
    sample_path: str = Field(default="", description="Path to audio sample")

    def describe(self) -> dict[str, Any]:
        result = super().describe()
        result["sample_path"] = self.sample_path
        return result

    def to_description(self) -> str:
        return f"Sample '{self.name}' [{self.sample_path}]: {len(self.patterns)} patterns"


class SF2InstrumentTrack(Track):
    """A SoundFont (SF2) instrument track using sf2player plugin."""

    track_type: Literal["sf2"] = "sf2"
    sf2_path: str = Field(description="Path to .sf2/.sf3 soundfont file")
    bank: int = Field(default=0, ge=0, le=999, description="Bank number")
    patch: int = Field(default=0, ge=0, le=127, description="Patch/program number")
    gain: float = Field(default=1.0, ge=0.0, le=5.0, description="Gain level")
    pitch: int = Field(default=0, ge=-24, le=24, description="Track pitch (semitones)")
    # Reverb settings
    reverb_on: bool = Field(default=False, description="Enable reverb")
    reverb_room_size: float = Field(default=0.2, ge=0.0, le=1.0)
    reverb_damping: float = Field(default=0.0, ge=0.0, le=1.0)
    reverb_width: float = Field(default=0.5, ge=0.0, le=1.0)
    reverb_level: float = Field(default=0.9, ge=0.0, le=1.0)
    # Chorus settings
    chorus_on: bool = Field(default=False, description="Enable chorus")
    chorus_num: int = Field(default=3, ge=0, le=10, description="Chorus voices")
    chorus_level: float = Field(default=2.0, ge=0.0, le=10.0)
    chorus_speed: float = Field(default=0.3, ge=0.0, le=5.0)  # relaxed from 0.29 for float precision
    chorus_depth: float = Field(default=8.0, ge=0.0, le=46.0)
    # Filter settings
    filter: FilterSettings | None = Field(default=None, description="Filter settings")
    # Effects chain
    effects: list[Effect] = Field(default_factory=list, description="Effects chain")

    def describe(self) -> dict[str, Any]:
        result = super().describe()
        result.update({
            "instrument": "sf2player",
            "sf2_path": self.sf2_path,
            "bank": self.bank,
            "patch": self.patch,
            "gain": self.gain,
            "reverb_on": self.reverb_on,
            "chorus_on": self.chorus_on,
        })
        return result

    def to_description(self) -> str:
        import os
        sf2_name = os.path.basename(self.sf2_path) if self.sf2_path else "none"
        effects = []
        if self.reverb_on:
            effects.append("reverb")
        if self.chorus_on:
            effects.append("chorus")
        effects_str = f" +{'+'.join(effects)}" if effects else ""
        return f"SF2 '{self.name}' [{sf2_name} bank:{self.bank} patch:{self.patch}{effects_str}]: {len(self.patterns)} patterns"


class AutomationPoint(BaseModel):
    """A single automation point."""

    time: float = Field(description="Time position in beats")
    value: float = Field(description="Automation value (0.0-1.0 normalized)")
    out_value: float | None = Field(default=None, description="Output value (for discrete jumps)")
    in_tan: float = Field(default=0.0, description="Incoming tangent")
    out_tan: float = Field(default=0.0, description="Outgoing tangent")


class AutomationClip(BaseModel):
    """An automation clip/pattern."""

    id: int = Field(default=0, description="Clip ID")
    name: str = Field(default="Automation", description="Clip name")
    position: int = Field(default=0, description="Start position in bars")
    length: int = Field(default=4, description="Length in bars")
    progression: int = Field(default=0, description="0=Discrete, 1=Linear, 2=Cubic")
    tension: float = Field(default=1.0, ge=0.0, le=1.0, description="Curve tension")
    muted: bool = Field(default=False, description="Clip muted")
    points: list[AutomationPoint] = Field(default_factory=list, description="Automation points")
    # Legacy format (runtime memory addresses - doesn't work for external creation)
    object_id: str | None = Field(default=None, description="Object ID to automate (legacy format)")
    # New trackref/param format (works for external creation)
    trackref: int | None = Field(default=None, description="Track index to automate")
    param: str | None = Field(default=None, description="Parameter name (pitch, vol, pan)")

    def add_point(self, time: float, value: float) -> None:
        """Add an automation point."""
        # Remove existing point at same time
        self.points = [p for p in self.points if p.time != time]
        self.points.append(AutomationPoint(time=time, value=value))
        self.points.sort(key=lambda p: p.time)

    def clear(self) -> None:
        """Clear all points."""
        self.points = []

    def describe(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "position": self.position,
            "length": self.length,
            "progression": ["discrete", "linear", "cubic"][min(self.progression, 2)],
            "tension": self.tension,
            "point_count": len(self.points),
        }


class AutomationTrack(Track):
    """An automation track."""

    track_type: Literal["automation"] = "automation"
    clips: list[AutomationClip] = Field(default_factory=list, description="Automation clips")

    def add_clip(self, clip: AutomationClip) -> None:
        """Add an automation clip."""
        clip.id = len(self.clips)
        self.clips.append(clip)

    def get_clip(self, clip_id: int) -> AutomationClip | None:
        """Get clip by ID."""
        for clip in self.clips:
            if clip.id == clip_id:
                return clip
        return None

    def describe(self) -> dict[str, Any]:
        result = super().describe()
        result.update({
            "clip_count": len(self.clips),
            "clips": [c.describe() for c in self.clips],
        })
        return result

    def to_description(self) -> str:
        """Human-readable description."""
        lines = [f"Automation Track '{self.name}': {len(self.clips)} clips"]
        for clip in self.clips:
            prog = ["discrete", "linear", "cubic"][min(clip.progression, 2)]
            lines.append(f"    {clip.name}: {len(clip.points)} points ({prog})")
        return "\n".join(lines)


class BBStep(BaseModel):
    """A single step in a Beat+Bassline pattern."""

    step: int = Field(description="Step number (0-based)")
    enabled: bool = Field(default=True, description="Whether step is active")
    velocity: int = Field(default=100, ge=0, le=127, description="Step velocity")


class BBInstrument(BaseModel):
    """An instrument row in the Beat+Bassline editor."""

    id: int = Field(default=0, description="Instrument ID")
    name: str = Field(default="Drum", description="Instrument name")
    instrument: str = Field(default="audiofileprocessor", description="Instrument plugin")
    sample_path: str | None = Field(default=None, description="Sample path for audiofileprocessor")
    volume: float = Field(default=1.0, ge=0.0, description="Instrument volume")
    pan: float = Field(default=0.0, ge=-1.0, le=1.0, description="Pan position")
    muted: bool = Field(default=False, description="Instrument muted")
    steps: list[BBStep] = Field(default_factory=list, description="Steps in the pattern")
    num_steps: int = Field(default=16, description="Number of steps in pattern")

    def set_step(self, step: int, enabled: bool = True, velocity: int = 100) -> None:
        """Set a step in the pattern."""
        # Remove existing step if any
        self.steps = [s for s in self.steps if s.step != step]
        if enabled:
            self.steps.append(BBStep(step=step, enabled=enabled, velocity=velocity))
        self.steps.sort(key=lambda s: s.step)

    def clear_steps(self) -> None:
        """Clear all steps."""
        self.steps = []

    def get_step_string(self) -> str:
        """Return a visual representation of steps (e.g., 'x...x...x...x...')."""
        active_steps = {s.step for s in self.steps if s.enabled}
        return "".join("x" if i in active_steps else "." for i in range(self.num_steps))

    def describe(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "instrument": self.instrument,
            "sample_path": self.sample_path,
            "volume": self.volume,
            "pan": self.pan,
            "muted": self.muted,
            "num_steps": self.num_steps,
            "active_steps": len([s for s in self.steps if s.enabled]),
            "pattern": self.get_step_string(),
        }


class BBTrack(Track):
    """A Beat+Bassline track with step sequencer."""

    track_type: Literal["bb"] = "bb"
    instruments: list[BBInstrument] = Field(default_factory=list, description="BB instruments (drum rows)")
    num_steps: int = Field(default=16, description="Steps per bar")
    bb_position: int = Field(default=0, description="Position in song timeline (bars)")
    bb_length: int = Field(default=4, description="Length in song timeline (bars)")

    def add_instrument(self, instrument: BBInstrument) -> None:
        """Add an instrument to the BB track."""
        instrument.id = len(self.instruments)
        instrument.num_steps = self.num_steps
        self.instruments.append(instrument)

    def get_instrument(self, instrument_id: int) -> BBInstrument | None:
        """Get instrument by ID."""
        for inst in self.instruments:
            if inst.id == instrument_id:
                return inst
        return None

    def get_instrument_by_name(self, name: str) -> BBInstrument | None:
        """Get instrument by name."""
        for inst in self.instruments:
            if inst.name.lower() == name.lower():
                return inst
        return None

    def remove_instrument(self, instrument_id: int) -> BBInstrument | None:
        """Remove instrument by ID."""
        for i, inst in enumerate(self.instruments):
            if inst.id == instrument_id:
                return self.instruments.pop(i)
        return None

    def describe(self) -> dict[str, Any]:
        result = super().describe()
        result.update({
            "num_steps": self.num_steps,
            "instrument_count": len(self.instruments),
            "bb_position": self.bb_position,
            "bb_length": self.bb_length,
        })
        return result

    def to_description(self) -> str:
        """Human-readable description."""
        lines = [f"BB Track '{self.name}': {len(self.instruments)} instruments, {self.num_steps} steps"]
        for inst in self.instruments:
            lines.append(f"    {inst.name}: {inst.get_step_string()}")
        return "\n".join(lines)


# =============================================================================
# Synthesizer Track Types
# =============================================================================


class Oscillator(BaseModel):
    """Single oscillator settings for Triple Oscillator."""

    volume: float = Field(default=100, ge=0, le=200, description="Oscillator volume")
    pan: float = Field(default=0, ge=-100, le=100, description="Pan position")
    coarse: int = Field(default=0, ge=-24, le=24, description="Coarse detune (semitones)")
    fine_left: float = Field(default=0, ge=-100, le=100, description="Fine detune left (cents)")
    fine_right: float = Field(default=0, ge=-100, le=100, description="Fine detune right (cents)")
    phase_offset: float = Field(default=0, ge=0, le=360, description="Phase offset (degrees)")
    stereo_phase: float = Field(default=0, ge=0, le=360, description="Stereo phase detuning")
    wave_shape: int = Field(default=2, ge=0, le=7, description="Wave shape (0-7)")
    user_wave: str | None = Field(default=None, description="User wave file path")


class TripleOscillatorTrack(Track):
    """A Triple Oscillator synthesizer track."""

    track_type: Literal["tripleoscillator"] = "tripleoscillator"
    instrument: str = Field(default="tripleoscillator", description="Instrument plugin")
    pitch: int = Field(default=0, ge=-24, le=24, description="Track pitch (semitones)")

    # Three oscillators
    osc1: Oscillator = Field(default_factory=lambda: Oscillator(wave_shape=2))  # Saw
    osc2: Oscillator = Field(default_factory=lambda: Oscillator(wave_shape=2, coarse=-12))  # Saw -1oct
    osc3: Oscillator = Field(default_factory=lambda: Oscillator(wave_shape=3, volume=50))  # Square

    # Modulation algorithms (how osc2/osc3 interact with osc1)
    mod_algo1: int = Field(default=2, ge=0, le=4, description="Osc1 modulation (2=mix)")
    mod_algo2: int = Field(default=2, ge=0, le=4, description="Osc2 modulation")
    mod_algo3: int = Field(default=2, ge=0, le=4, description="Osc3 modulation")

    # Filter settings
    filter: FilterSettings = Field(default_factory=FilterSettings, description="Filter settings")

    # Effects chain
    effects: list[Effect] = Field(default_factory=list, description="Effects chain")

    def describe(self) -> dict[str, Any]:
        result = super().describe()
        result.update({
            "instrument": "tripleoscillator",
            "pitch": self.pitch,
            "osc1_wave": self.osc1.wave_shape,
            "osc2_wave": self.osc2.wave_shape,
            "osc3_wave": self.osc3.wave_shape,
            "filter_type": self.filter.filter_type,
            "filter_cutoff": self.filter.cutoff,
            "effect_count": len(self.effects),
        })
        return result

    def to_description(self) -> str:
        waves = ["sine", "tri", "saw", "sqr", "moog", "exp", "noise", "user"]
        w1 = waves[min(self.osc1.wave_shape, 7)]
        w2 = waves[min(self.osc2.wave_shape, 7)]
        w3 = waves[min(self.osc3.wave_shape, 7)]
        fx = f" +{len(self.effects)}fx" if self.effects else ""
        return f"TripleOsc '{self.name}' [{w1}+{w2}+{w3}]{fx}: {len(self.patterns)} patterns"


class KickerTrack(Track):
    """A Kicker synthesizer track for bass drums and sub bass."""

    track_type: Literal["kicker"] = "kicker"
    pitch: int = Field(default=0, ge=-24, le=24, description="Track pitch (semitones)")

    # Kicker-specific parameters
    start_freq: float = Field(default=150, ge=5, le=1000, description="Start frequency (Hz)")
    end_freq: float = Field(default=40, ge=5, le=1000, description="End frequency (Hz)")
    decay: float = Field(default=300, ge=5, le=5000, description="Decay time (ms)")
    distortion: float = Field(default=50, ge=0, le=100, description="Distortion amount")
    dist_end: float = Field(default=50, ge=0, le=100, description="End distortion")
    gain: float = Field(default=1.0, ge=0.1, le=5.0, description="Output gain")
    env_slope: float = Field(default=0.5, ge=0.01, le=1.0, description="Envelope slope")
    noise: float = Field(default=0.0, ge=0.0, le=1.0, description="Noise amount")
    click: float = Field(default=0.0, ge=0.0, le=1.0, description="Click amount")
    freq_slope: float = Field(default=0.2, ge=0.001, le=1.0, description="Frequency slope")
    start_from_note: bool = Field(default=False, description="Start from MIDI note")
    end_to_note: bool = Field(default=False, description="End to MIDI note")

    # Effects chain
    effects: list[Effect] = Field(default_factory=list, description="Effects chain")

    def describe(self) -> dict[str, Any]:
        result = super().describe()
        result.update({
            "instrument": "kicker",
            "start_freq": self.start_freq,
            "end_freq": self.end_freq,
            "decay": self.decay,
            "distortion": self.distortion,
            "effect_count": len(self.effects),
        })
        return result

    def to_description(self) -> str:
        fx = f" +{len(self.effects)}fx" if self.effects else ""
        return f"Kicker '{self.name}' [{self.start_freq}→{self.end_freq}Hz, {self.decay}ms]{fx}: {len(self.patterns)} patterns"


class MonstroTrack(Track):
    """A Monstro synthesizer track - powerful modular synth."""

    track_type: Literal["monstro"] = "monstro"
    pitch: int = Field(default=0, ge=-24, le=24, description="Track pitch (semitones)")

    # Oscillator volumes
    osc1_vol: float = Field(default=100, ge=0, le=200)
    osc2_vol: float = Field(default=100, ge=0, le=200)
    osc3_vol: float = Field(default=100, ge=0, le=200)

    # Oscillator waveforms (Monstro has 15 waveforms)
    osc1_wave: int = Field(default=4, ge=0, le=14, description="Osc1 wave (square)")
    osc2_wave: int = Field(default=2, ge=0, le=14, description="Osc2 wave (saw)")
    osc3_wave1: int = Field(default=0, ge=0, le=14, description="Osc3 wave1")
    osc3_wave2: int = Field(default=0, ge=0, le=14, description="Osc3 wave2")

    # Oscillator 1 pulse width
    osc1_pw: float = Field(default=50, ge=0.25, le=75.75, description="Osc1 pulse width")

    # Oscillator 3 sub
    osc3_sub: float = Field(default=0, ge=-100, le=100, description="Osc3 sub oscillator")

    # LFO 1
    lfo1_wave: int = Field(default=0, ge=0, le=10, description="LFO1 wave")
    lfo1_rate: float = Field(default=1.0, ge=0.01, le=20, description="LFO1 rate (Hz)")
    lfo1_amount: float = Field(default=0, ge=0, le=100, description="LFO1 amount")

    # LFO 2
    lfo2_wave: int = Field(default=0, ge=0, le=10, description="LFO2 wave")
    lfo2_rate: float = Field(default=1.0, ge=0.01, le=20, description="LFO2 rate (Hz)")
    lfo2_amount: float = Field(default=0, ge=0, le=100, description="LFO2 amount")

    # Filter settings
    filter: FilterSettings = Field(default_factory=FilterSettings, description="Filter settings")

    # Effects chain
    effects: list[Effect] = Field(default_factory=list, description="Effects chain")

    def describe(self) -> dict[str, Any]:
        result = super().describe()
        result.update({
            "instrument": "monstro",
            "osc1_wave": self.osc1_wave,
            "osc2_wave": self.osc2_wave,
            "lfo1_rate": self.lfo1_rate,
            "lfo2_rate": self.lfo2_rate,
            "filter_type": self.filter.filter_type,
            "effect_count": len(self.effects),
        })
        return result

    def to_description(self) -> str:
        fx = f" +{len(self.effects)}fx" if self.effects else ""
        return f"Monstro '{self.name}' [LFO1:{self.lfo1_rate}Hz LFO2:{self.lfo2_rate}Hz]{fx}: {len(self.patterns)} patterns"
