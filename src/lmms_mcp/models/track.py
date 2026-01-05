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


class AutomationTrack(Track):
    """An automation track."""

    track_type: Literal["automation"] = "automation"
    target_track: int | None = Field(default=None, description="Target track ID")
    target_param: str | None = Field(default=None, description="Target parameter")

    def describe(self) -> dict[str, Any]:
        result = super().describe()
        result.update({
            "target_track": self.target_track,
            "target_param": self.target_param,
        })
        return result


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
