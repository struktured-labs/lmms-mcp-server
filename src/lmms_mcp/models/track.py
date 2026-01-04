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
