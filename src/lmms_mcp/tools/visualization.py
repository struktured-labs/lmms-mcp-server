"""Visualization tools for LMMS projects."""

import subprocess
import os
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from lmms_mcp.xml.parser import parse_project

# Default LMMS binary path
LMMS_BIN = os.environ.get("LMMS_BIN", "/home/struktured/projects/lmms-ai/lmms-install/bin/lmms")


def register(mcp: FastMCP) -> None:
    """Register visualization tools with the MCP server."""

    @mcp.tool()
    def show_drum_grid(
        path: str,
        tracks: list[str] | None = None,
        bars: int | None = None,
    ) -> dict[str, Any]:
        """Show an ASCII drum grid visualization of patterns.

        Args:
            path: Path to .mmp or .mmpz file
            tracks: Optional list of track names to show (default: all)
            bars: Optional number of bars to show (default: auto-detect)

        Returns:
            ASCII grid visualization of drum patterns
        """
        project = parse_project(Path(path))

        # Parser uses 48 ticks per unit (which is actually per 16th note)
        # So 16 parser units = 1 bar, 4 parser units = 1 beat
        units_per_bar = 16  # 16 sixteenths per bar

        # Collect track data
        track_data = []
        max_len = 0

        for track in project.tracks:
            if tracks and track.name not in tracks:
                continue

            if not track.patterns:
                continue

            # Get volume from track (multiply by 100 for display since parser normalizes to 0-1.5)
            vol = getattr(track, 'volume', 1.0)
            vol_display = int(vol * 100)

            # Collect all notes from all patterns
            notes = []
            pattern_len_16ths = 0
            for pattern in track.patterns:
                # Pattern length is in beats, convert to 16ths (* 4)
                pattern_len_16ths = max(pattern_len_16ths, int(pattern.length * 4))
                for note in pattern.notes:
                    # note.start is already in 16th notes
                    grid_pos = int(note.start)
                    notes.append((grid_pos, note.velocity))

            if notes:
                max_len = max(max_len, pattern_len_16ths)
                track_data.append({
                    'name': track.name,
                    'vol': vol_display,
                    'notes': notes,
                    'len': pattern_len
                })

        if not track_data:
            return {"status": "error", "message": "No tracks with patterns found"}

        # Calculate grid dimensions - each char is 1/16th note
        # pattern_len is already in 16th notes
        if bars:
            grid_width = bars * 16
        else:
            grid_width = max(16, max_len)

        num_bars = max(1, grid_width // 16)

        # Build ASCII output
        lines = []
        lines.append("=" * 60)
        lines.append(f"DRUM GRID - {project.bpm} BPM - {num_bars} bars")
        lines.append("=" * 60)
        lines.append("Each character = 1/16th note")
        lines.append("Legend: █=loud(>100) ▓=medium(70-100) ░=soft(<70) ·=empty")
        lines.append("=" * 60)
        lines.append("")

        # Header with beat markers
        header = "              │"
        for bar in range(num_bars):
            header += f"{bar+1}···2···3···4···│"
        lines.append(header)
        lines.append("──────────────┼" + "────────────────┼" * num_bars)

        for track in track_data:
            # Create grid line
            grid = ['·'] * grid_width

            for grid_pos, vel in track['notes']:
                if 0 <= grid_pos < grid_width:
                    if vel > 100:
                        grid[grid_pos] = '█'
                    elif vel > 70:
                        grid[grid_pos] = '▓'
                    else:
                        grid[grid_pos] = '░'

            # Format name and volume
            name = track['name'][:10].ljust(10)
            vol = f"v{track['vol']}".rjust(4)

            # Add bar separators
            line = ""
            for i, char in enumerate(grid):
                if i % 16 == 0 and i > 0:
                    line += "│"
                line += char
            line += "│"

            lines.append(f"{name}{vol}│{line}")

        lines.append("──────────────┼" + "────────────────┼" * num_bars)

        grid_text = "\n".join(lines)

        return {
            "status": "ok",
            "bpm": project.bpm,
            "bars": num_bars,
            "tracks": len(track_data),
            "grid": grid_text
        }

    @mcp.tool()
    def show_track_params(path: str, track_id: int | None = None) -> dict[str, Any]:
        """Show detailed parameters for tracks (volumes, synth settings, etc).

        Args:
            path: Path to .mmp or .mmpz file
            track_id: Optional specific track ID (default: show all)

        Returns:
            Track parameters in readable format
        """
        project = parse_project(Path(path))

        tracks_info = []
        for track in project.tracks:
            if track_id is not None and track.id != track_id:
                continue

            info = {
                "id": track.id,
                "name": track.name,
                "type": track.type,
                "volume": getattr(track, 'volume', 100),
                "pan": getattr(track, 'pan', 0),
                "muted": getattr(track, 'muted', False),
            }

            # Add instrument-specific info
            if hasattr(track, 'instrument_name'):
                info["instrument"] = track.instrument_name

            if hasattr(track, 'instrument_params'):
                info["params"] = track.instrument_params

            tracks_info.append(info)

        return {
            "status": "ok",
            "project": Path(path).name,
            "tracks": tracks_info
        }

    @mcp.tool()
    def launch_lmms(path: str | None = None) -> dict[str, Any]:
        """Launch LMMS GUI, optionally with a project file.

        Args:
            path: Optional path to .mmp or .mmpz file to open

        Returns:
            Status message
        """
        cmd = [LMMS_BIN]
        if path:
            cmd.append(str(Path(path).absolute()))

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            return {
                "status": "launched",
                "pid": proc.pid,
                "project": path if path else None,
                "message": "LMMS GUI launched. Edit and save your project, then use render tools."
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to launch LMMS: {e}"
            }
