"""Filter, envelope, and LFO MCP tools for LMMS."""

from pathlib import Path
from typing import Any

from lmms_mcp.xml.parser import parse_project
from lmms_mcp.xml.writer import write_project
from lmms_mcp.models.track import (
    FILTER_TYPES, FilterSettings, FilterEnvelope, FilterLFO,
    TripleOscillatorTrack, MonstroTrack, KickerTrack, SF2InstrumentTrack,
    InstrumentTrack,
)


def _get_track_with_filter(project, track_id: int):
    """Get a track that supports filter settings."""
    if track_id >= len(project.tracks):
        return None, f"Track {track_id} not found"

    track = project.tracks[track_id]
    filter_types = (TripleOscillatorTrack, MonstroTrack, SF2InstrumentTrack, InstrumentTrack)

    if not isinstance(track, filter_types):
        return None, f"Track {track_id} does not support filter settings"

    # Ensure filter settings exist
    if not hasattr(track, 'filter') or track.filter is None:
        track.filter = FilterSettings()

    return track, None


def register(mcp):
    """Register filter tools with the MCP server."""

    @mcp.tool()
    def set_track_filter(
        path: str,
        track_id: int,
        filter_type: str | int = "lowpass",
        cutoff: float = 14000,
        resonance: float = 0.5,
        wet: float = 1.0,
    ) -> dict[str, Any]:
        """Set the filter settings for a track.

        Filter types: lowpass, hipass, bandpass_csg, bandpass_czpg, notch,
        allpass, moog, doublelowpass, lowpass_rc12, bandpass_rc12, highpass_rc12,
        lowpass_rc24, bandpass_rc24, highpass_rc24, formant, doublemoog,
        lowpass_sv, bandpass_sv, highpass_sv, notch_sv, fastformant, tripole

        Args:
            path: Path to .mmp or .mmpz file
            track_id: ID of track to modify
            filter_type: Filter type name or number (0-21)
            cutoff: Filter cutoff frequency in Hz (default 14000)
            resonance: Filter resonance 0.0-1.0 (default 0.5)
            wet: Filter wet/dry mix 0.0-1.0 (default 1.0)

        Returns:
            Updated filter settings
        """
        project = parse_project(Path(path))
        track, error = _get_track_with_filter(project, track_id)
        if error:
            return {"status": "error", "error": error}

        # Parse filter type
        if isinstance(filter_type, str):
            ftype = FILTER_TYPES.get(filter_type.lower(), 0)
        else:
            ftype = int(filter_type)

        track.filter.filter_type = ftype
        track.filter.cutoff = cutoff
        track.filter.resonance = resonance
        track.filter.wet = wet

        write_project(project, Path(path))

        return {
            "status": "updated",
            "track_id": track_id,
            "filter": {
                "type": ftype,
                "type_name": [k for k, v in FILTER_TYPES.items() if v == ftype][0] if ftype in FILTER_TYPES.values() else "unknown",
                "cutoff": cutoff,
                "resonance": resonance,
                "wet": wet,
            },
        }

    @mcp.tool()
    def set_filter_lfo(
        path: str,
        track_id: int,
        speed: float = 1.0,
        amount: float = 50.0,
        shape: int = 0,
        x100: bool = False,
    ) -> dict[str, Any]:
        """Set the filter cutoff LFO for wobble effects.

        This is THE WOBBLE - modulates filter cutoff at a rate.

        LFO shapes:
        - 0: Sine (smooth wobble)
        - 1: Triangle (linear wobble)
        - 2: Saw (rising sweep)
        - 3: Square (choppy)
        - 4: User defined
        - 5: Random (chaotic)

        Args:
            path: Path to .mmp or .mmpz file
            track_id: ID of track to modify
            speed: LFO speed (default 1.0, use x100 for faster)
            amount: LFO amount 0-100 (default 50)
            shape: LFO waveform shape 0-5 (default 0=Sine)
            x100: Multiply speed by 100 (default False)

        Returns:
            Updated LFO settings
        """
        project = parse_project(Path(path))
        track, error = _get_track_with_filter(project, track_id)
        if error:
            return {"status": "error", "error": error}

        # Set cutoff envelope LFO
        track.filter.cut_env.lfo.speed = speed
        track.filter.cut_env.lfo.amount = amount
        track.filter.cut_env.lfo.shape = shape
        track.filter.cut_env.lfo.x100 = x100

        write_project(project, Path(path))

        shapes = ["sine", "triangle", "saw", "square", "user", "random"]
        return {
            "status": "updated",
            "track_id": track_id,
            "cutoff_lfo": {
                "speed": speed,
                "amount": amount,
                "shape": shape,
                "shape_name": shapes[shape] if shape < len(shapes) else "unknown",
                "x100": x100,
                "effective_speed": speed * (100 if x100 else 1),
            },
        }

    @mcp.tool()
    def set_filter_envelope(
        path: str,
        track_id: int,
        target: str = "cutoff",
        attack: float = 0.0,
        decay: float = 0.5,
        sustain: float = 0.5,
        release: float = 0.1,
        amount: float = 0.0,
        predelay: float = 0.0,
    ) -> dict[str, Any]:
        """Set the filter envelope (ADSR) for a track.

        Args:
            path: Path to .mmp or .mmpz file
            track_id: ID of track to modify
            target: Envelope target: "cutoff", "resonance", or "volume"
            attack: Attack time (default 0.0)
            decay: Decay time (default 0.5)
            sustain: Sustain level 0-1 (default 0.5)
            release: Release time (default 0.1)
            amount: Envelope amount/depth (default 0.0)
            predelay: Pre-delay time (default 0.0)

        Returns:
            Updated envelope settings
        """
        project = parse_project(Path(path))
        track, error = _get_track_with_filter(project, track_id)
        if error:
            return {"status": "error", "error": error}

        # Select target envelope
        if target == "cutoff":
            env = track.filter.cut_env
        elif target == "resonance":
            env = track.filter.res_env
        elif target == "volume":
            env = track.filter.vol_env
        else:
            return {"status": "error", "error": f"Unknown target: {target}"}

        env.attack = attack
        env.decay = decay
        env.sustain = sustain
        env.release = release
        env.amount = amount
        env.predelay = predelay

        write_project(project, Path(path))

        return {
            "status": "updated",
            "track_id": track_id,
            "envelope": {
                "target": target,
                "attack": attack,
                "decay": decay,
                "sustain": sustain,
                "release": release,
                "amount": amount,
                "predelay": predelay,
            },
        }

    @mcp.tool()
    def set_track_pitch(
        path: str,
        track_id: int,
        semitones: int = 0,
    ) -> dict[str, Any]:
        """Set the pitch transpose for a track.

        Args:
            path: Path to .mmp or .mmpz file
            track_id: ID of track to modify
            semitones: Pitch shift in semitones (-24 to +24)

        Returns:
            Updated track pitch
        """
        project = parse_project(Path(path))

        if track_id >= len(project.tracks):
            return {"status": "error", "error": f"Track {track_id} not found"}

        track = project.tracks[track_id]

        # Only synth tracks have pitch attribute
        if hasattr(track, 'pitch'):
            track.pitch = max(-24, min(24, semitones))
            write_project(project, Path(path))
            return {
                "status": "updated",
                "track_id": track_id,
                "pitch": track.pitch,
            }
        else:
            return {
                "status": "error",
                "error": f"Track {track_id} does not support pitch control",
            }

    @mcp.tool()
    def list_filter_types() -> dict[str, Any]:
        """List all available filter types.

        Returns:
            Dictionary of filter types with numbers and descriptions
        """
        descriptions = {
            "lowpass": "Standard low-pass filter",
            "hipass": "Standard high-pass filter",
            "bandpass_csg": "Band-pass filter (CSG)",
            "bandpass_czpg": "Band-pass filter (CZPG)",
            "notch": "Notch/band-reject filter",
            "allpass": "All-pass filter (phase shift)",
            "moog": "Moog-style resonant low-pass (GREAT FOR WOBBLE)",
            "doublelowpass": "Double low-pass for steeper rolloff",
            "lowpass_rc12": "RC low-pass 12dB/oct",
            "bandpass_rc12": "RC band-pass 12dB/oct",
            "highpass_rc12": "RC high-pass 12dB/oct",
            "lowpass_rc24": "RC low-pass 24dB/oct (steeper)",
            "bandpass_rc24": "RC band-pass 24dB/oct",
            "highpass_rc24": "RC high-pass 24dB/oct",
            "formant": "Formant filter (vowel sounds)",
            "doublemoog": "Double Moog filter (VERY AGGRESSIVE)",
            "lowpass_sv": "State-variable low-pass",
            "bandpass_sv": "State-variable band-pass",
            "highpass_sv": "State-variable high-pass",
            "notch_sv": "State-variable notch",
            "fastformant": "Fast formant filter",
            "tripole": "3-pole filter",
        }

        return {
            "filter_types": {
                name: {"number": num, "description": descriptions.get(name, "")}
                for name, num in FILTER_TYPES.items()
            },
            "recommended_for_dubstep": ["moog", "doublemoog", "lowpass_rc24"],
        }
