"""Project model for LMMS."""

from pydantic import BaseModel, Field
from typing import Any

from lmms_mcp.models.track import Track, InstrumentTrack, SampleTrack


class Project(BaseModel):
    """An LMMS project."""

    name: str = Field(default="Untitled", description="Project name")
    bpm: int = Field(default=120, ge=20, le=999, description="Beats per minute")
    time_sig_num: int = Field(default=4, ge=1, le=32, description="Time signature numerator")
    time_sig_den: int = Field(default=4, ge=1, le=32, description="Time signature denominator")
    master_volume: float = Field(default=1.0, ge=0.0, le=2.0, description="Master volume")
    master_pitch: int = Field(default=0, ge=-12, le=12, description="Master pitch in semitones")
    tracks: list[Track] = Field(default_factory=list, description="Tracks in project")

    # Internal: raw XML tree for preserving unknown elements
    _raw_xml: Any = None

    def add_track(self, track: Track) -> None:
        """Add a track to the project."""
        track.id = len(self.tracks)
        self.tracks.append(track)

    def get_track(self, track_id: int) -> Track | None:
        """Get track by ID."""
        for track in self.tracks:
            if track.id == track_id:
                return track
        return None

    def remove_track(self, track_id: int) -> bool:
        """Remove track by ID. Returns True if removed."""
        for i, track in enumerate(self.tracks):
            if track.id == track_id:
                self.tracks.pop(i)
                # Reindex remaining tracks
                for j, t in enumerate(self.tracks):
                    t.id = j
                return True
        return False

    def describe(self) -> dict[str, Any]:
        """Return a summary dict."""
        track_types = {}
        for track in self.tracks:
            ttype = track.__class__.__name__
            track_types[ttype] = track_types.get(ttype, 0) + 1

        total_patterns = sum(len(t.patterns) for t in self.tracks)
        total_notes = sum(
            len(p.notes) for t in self.tracks for p in t.patterns
        )

        return {
            "name": self.name,
            "bpm": self.bpm,
            "time_signature": f"{self.time_sig_num}/{self.time_sig_den}",
            "track_count": len(self.tracks),
            "track_types": track_types,
            "pattern_count": total_patterns,
            "note_count": total_notes,
        }

    def to_description(self) -> str:
        """Human-readable description of the project."""
        lines = [
            f"Project: {self.name}",
            f"Tempo: {self.bpm} BPM, Time signature: {self.time_sig_num}/{self.time_sig_den}",
            f"Tracks: {len(self.tracks)}",
            "",
        ]

        for track in self.tracks:
            lines.append(f"  [{track.id}] {track.to_description()}")
            for pattern in track.patterns:
                lines.append(f"       - {pattern.to_description()}")

        return "\n".join(lines)
