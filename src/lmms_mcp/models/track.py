"""Track models for LMMS projects."""

from pydantic import BaseModel, Field
from typing import Any, Literal

from lmms_mcp.models.pattern import Pattern


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

    def describe(self) -> dict[str, Any]:
        result = super().describe()
        result.update({
            "instrument": self.instrument,
            "preset": self.preset,
        })
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
    chorus_speed: float = Field(default=0.3, ge=0.29, le=5.0)
    chorus_depth: float = Field(default=8.0, ge=0.0, le=46.0)

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
