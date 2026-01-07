"""Automation track MCP tools."""

from pathlib import Path
from typing import Any

from lmms_mcp.xml.parser import parse_project
from lmms_mcp.xml.writer import write_project
from lmms_mcp.models.track import AutomationTrack, AutomationClip, AutomationPoint


def register(mcp):
    """Register automation tools with the MCP server."""

    @mcp.tool()
    def add_automation_track(
        path: str,
        name: str = "Automation",
    ) -> dict[str, Any]:
        """Add an automation track to the project.

        Args:
            path: Path to .mmp or .mmpz file
            name: Track name

        Returns:
            New automation track info
        """
        project = parse_project(Path(path))

        auto_track = AutomationTrack(name=name)
        project.add_track(auto_track)

        write_project(project, Path(path))

        return {
            "status": "added",
            "track": auto_track.describe(),
            "track_count": len(project.tracks),
        }

    @mcp.tool()
    def add_automation_clip(
        path: str,
        track_id: int,
        name: str = "Automation",
        position: int = 0,
        length: int = 4,
        progression: int = 1,
    ) -> dict[str, Any]:
        """Add an automation clip to an automation track.

        Args:
            path: Path to .mmp or .mmpz file
            track_id: ID of automation track
            name: Clip name (e.g., "Volume", "Filter Cutoff")
            position: Start position in bars (default 0)
            length: Length in bars (default 4)
            progression: Curve type: 0=Discrete, 1=Linear, 2=Cubic (default 1)

        Returns:
            New clip info
        """
        project = parse_project(Path(path))

        if track_id >= len(project.tracks):
            return {"status": "error", "error": f"Track {track_id} not found"}

        track = project.tracks[track_id]
        if not isinstance(track, AutomationTrack):
            return {"status": "error", "error": f"Track {track_id} is not an automation track"}

        clip = AutomationClip(
            name=name,
            position=position,
            length=length,
            progression=progression,
        )
        track.add_clip(clip)

        write_project(project, Path(path))

        return {
            "status": "added",
            "clip": clip.describe(),
            "track_id": track_id,
            "clip_count": len(track.clips),
        }

    @mcp.tool()
    def set_automation_points(
        path: str,
        track_id: int,
        clip_id: int,
        points: list[dict],
    ) -> dict[str, Any]:
        """Set automation points for a clip.

        Args:
            path: Path to .mmp or .mmpz file
            track_id: ID of automation track
            clip_id: ID of automation clip
            points: List of points, each with:
                - time: Time position in beats
                - value: Automation value (typically 0-100 or 0-1)

        Returns:
            Updated clip info
        """
        project = parse_project(Path(path))

        if track_id >= len(project.tracks):
            return {"status": "error", "error": f"Track {track_id} not found"}

        track = project.tracks[track_id]
        if not isinstance(track, AutomationTrack):
            return {"status": "error", "error": f"Track {track_id} is not an automation track"}

        clip = track.get_clip(clip_id)
        if clip is None:
            return {"status": "error", "error": f"Clip {clip_id} not found"}

        # Clear existing points and add new ones
        clip.clear()
        for p in points:
            point = AutomationPoint(
                time=float(p.get("time", 0)),
                value=float(p.get("value", 0)),
            )
            clip.points.append(point)
        clip.points.sort(key=lambda x: x.time)

        write_project(project, Path(path))

        return {
            "status": "updated",
            "clip": clip.describe(),
            "point_count": len(clip.points),
        }

    @mcp.tool()
    def add_automation_point(
        path: str,
        track_id: int,
        clip_id: int,
        time: float,
        value: float,
    ) -> dict[str, Any]:
        """Add a single automation point to a clip.

        Args:
            path: Path to .mmp or .mmpz file
            track_id: ID of automation track
            clip_id: ID of automation clip
            time: Time position in beats
            value: Automation value

        Returns:
            Updated clip info
        """
        project = parse_project(Path(path))

        if track_id >= len(project.tracks):
            return {"status": "error", "error": f"Track {track_id} not found"}

        track = project.tracks[track_id]
        if not isinstance(track, AutomationTrack):
            return {"status": "error", "error": f"Track {track_id} is not an automation track"}

        clip = track.get_clip(clip_id)
        if clip is None:
            return {"status": "error", "error": f"Clip {clip_id} not found"}

        clip.add_point(time, value)

        write_project(project, Path(path))

        return {
            "status": "added",
            "clip": clip.describe(),
            "point_count": len(clip.points),
        }

    @mcp.tool()
    def create_automation_ramp(
        path: str,
        track_id: int,
        clip_id: int,
        start_value: float,
        end_value: float,
        start_time: float = 0,
        end_time: float | None = None,
    ) -> dict[str, Any]:
        """Create a linear ramp automation from start to end value.

        Args:
            path: Path to .mmp or .mmpz file
            track_id: ID of automation track
            clip_id: ID of automation clip
            start_value: Starting value
            end_value: Ending value
            start_time: Start time in beats (default 0)
            end_time: End time in beats (default: clip length)

        Returns:
            Updated clip info
        """
        project = parse_project(Path(path))

        if track_id >= len(project.tracks):
            return {"status": "error", "error": f"Track {track_id} not found"}

        track = project.tracks[track_id]
        if not isinstance(track, AutomationTrack):
            return {"status": "error", "error": f"Track {track_id} is not an automation track"}

        clip = track.get_clip(clip_id)
        if clip is None:
            return {"status": "error", "error": f"Clip {clip_id} not found"}

        # Set progression to linear
        clip.progression = 1

        # Calculate end time if not provided
        if end_time is None:
            end_time = clip.length * 4  # 4 beats per bar

        # Clear and add ramp points
        clip.clear()
        clip.add_point(start_time, start_value)
        clip.add_point(end_time, end_value)

        write_project(project, Path(path))

        return {
            "status": "created",
            "ramp": {
                "start_value": start_value,
                "end_value": end_value,
                "start_time": start_time,
                "end_time": end_time,
            },
            "clip": clip.describe(),
        }

    @mcp.tool()
    def create_automation_lfo(
        path: str,
        track_id: int,
        clip_id: int,
        min_value: float,
        max_value: float,
        frequency: float = 1.0,
        num_cycles: int | None = None,
    ) -> dict[str, Any]:
        """Create an LFO-style automation (sine wave pattern).

        Args:
            path: Path to .mmp or .mmpz file
            track_id: ID of automation track
            clip_id: ID of automation clip
            min_value: Minimum value
            max_value: Maximum value
            frequency: Cycles per bar (default 1.0)
            num_cycles: Number of cycles (default: based on clip length)

        Returns:
            Updated clip info
        """
        import math

        project = parse_project(Path(path))

        if track_id >= len(project.tracks):
            return {"status": "error", "error": f"Track {track_id} not found"}

        track = project.tracks[track_id]
        if not isinstance(track, AutomationTrack):
            return {"status": "error", "error": f"Track {track_id} is not an automation track"}

        clip = track.get_clip(clip_id)
        if clip is None:
            return {"status": "error", "error": f"Clip {clip_id} not found"}

        # Set progression to cubic for smooth curves
        clip.progression = 2

        # Calculate number of cycles
        if num_cycles is None:
            num_cycles = int(clip.length * frequency)
        num_cycles = max(1, num_cycles)

        # Clear existing points
        clip.clear()

        # Generate sine wave points
        points_per_cycle = 8  # Enough points for smooth curve
        total_points = num_cycles * points_per_cycle
        beats_per_bar = 4
        total_beats = clip.length * beats_per_bar

        amplitude = (max_value - min_value) / 2
        center = (max_value + min_value) / 2

        for i in range(total_points + 1):
            time = (i / total_points) * total_beats
            phase = (i / points_per_cycle) * 2 * math.pi
            value = center + amplitude * math.sin(phase)
            clip.add_point(time, value)

        write_project(project, Path(path))

        return {
            "status": "created",
            "lfo": {
                "min_value": min_value,
                "max_value": max_value,
                "frequency": frequency,
                "num_cycles": num_cycles,
            },
            "clip": clip.describe(),
            "point_count": len(clip.points),
        }

    @mcp.tool()
    def describe_automation_track(
        path: str,
        track_id: int,
    ) -> dict[str, Any]:
        """Get detailed description of an automation track.

        Args:
            path: Path to .mmp or .mmpz file
            track_id: ID of automation track

        Returns:
            Track description with clips and points
        """
        project = parse_project(Path(path))

        if track_id >= len(project.tracks):
            return {"status": "error", "error": f"Track {track_id} not found"}

        track = project.tracks[track_id]
        if not isinstance(track, AutomationTrack):
            return {"status": "error", "error": f"Track {track_id} is not an automation track"}

        clips = []
        for clip in track.clips:
            clip_info = clip.describe()
            clip_info["points"] = [
                {"time": p.time, "value": p.value}
                for p in clip.points
            ]
            clips.append(clip_info)

        return {
            "name": track.name,
            "clip_count": len(track.clips),
            "clips": clips,
            "visual": track.to_description(),
        }

    @mcp.tool()
    def clear_automation_clip(
        path: str,
        track_id: int,
        clip_id: int,
    ) -> dict[str, Any]:
        """Clear all points from an automation clip.

        Args:
            path: Path to .mmp or .mmpz file
            track_id: ID of automation track
            clip_id: ID of automation clip

        Returns:
            Updated clip info
        """
        project = parse_project(Path(path))

        if track_id >= len(project.tracks):
            return {"status": "error", "error": f"Track {track_id} not found"}

        track = project.tracks[track_id]
        if not isinstance(track, AutomationTrack):
            return {"status": "error", "error": f"Track {track_id} is not an automation track"}

        clip = track.get_clip(clip_id)
        if clip is None:
            return {"status": "error", "error": f"Clip {clip_id} not found"}

        clip.clear()

        write_project(project, Path(path))

        return {
            "status": "cleared",
            "clip": clip.describe(),
        }

    @mcp.tool()
    def link_automation(
        path: str,
        automation_track_id: int,
        clip_id: int,
        target_track_id: int,
        parameter: str,
    ) -> dict[str, Any]:
        """Link an automation clip to control a track parameter.

        Common parameters:
        - "pitch": Track pitch (-24 to +24 semitones)
        - "vol": Track volume (0-100)
        - "pan": Track pan (-100 to +100)
        - "cutoff": Filter cutoff frequency
        - "reso": Filter resonance

        Args:
            path: Path to .mmp or .mmpz file
            automation_track_id: ID of automation track containing the clip
            clip_id: ID of automation clip to link
            target_track_id: ID of track to control
            parameter: Parameter name to automate

        Returns:
            Link status
        """
        project = parse_project(Path(path))

        if automation_track_id >= len(project.tracks):
            return {"status": "error", "error": f"Automation track {automation_track_id} not found"}

        automation_track = project.tracks[automation_track_id]
        if not isinstance(automation_track, AutomationTrack):
            return {"status": "error", "error": f"Track {automation_track_id} is not an automation track"}

        if target_track_id >= len(project.tracks):
            return {"status": "error", "error": f"Target track {target_track_id} not found"}

        clip = automation_track.get_clip(clip_id)
        if clip is None:
            return {"status": "error", "error": f"Clip {clip_id} not found"}

        # Generate unique object ID for the target parameter
        # Format: trackID/parameter (using track index as pseudo-ID)
        object_id = f"{target_track_id * 1000000}/{parameter}"
        clip.object_id = object_id

        write_project(project, Path(path))

        return {
            "status": "linked",
            "automation_track": automation_track_id,
            "clip_id": clip_id,
            "target_track": target_track_id,
            "parameter": parameter,
            "object_id": object_id,
        }
